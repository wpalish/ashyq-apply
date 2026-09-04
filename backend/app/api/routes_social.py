"""The social module's endpoints: joining, posting, threads, feed and Discover.

Two rules run through the whole module.

**Joining is an act.** Registering creates an account; it does not create a
social profile. Until someone writes one, they are not in Discover and cannot
post. That is why `POST /posts` answers 409 rather than quietly creating a
profile on their behalf.

**Discover crosses organizations; nothing else does.** Every other route in this
API filters by `principal.organization_id`. These do not, because a social graph
scoped to a workspace of one would be empty. What replaces that boundary is the
shape of what is returned: `PersonCard` carries only what its owner typed, so
there is no query here that can reach an applicant case.
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db import get_session
from app.domain.social import extract_tags, normalize_key
from app.models import Post, PostReply, PostTag, SocialProfile, SocialProfileUniversity, User
from app.models.base import ensure_utc
from app.schemas.social import (
    AuthorRef,
    MyProfileView,
    PeoplePage,
    PersonCard,
    PostIn,
    PostPage,
    PostView,
    ProfileIn,
    ReplyIn,
    ReplyPage,
    ReplyView,
)
from app.security import Principal, get_principal

router = APIRouter(prefix="/api/social", tags=["social"])

DEFAULT_PAGE = 20
MAX_PAGE = 50


# --- Cursors ------------------------------------------------------------


def _encode_cursor(moment: datetime, row_id: str) -> str:
    """A cursor is the sort key of the last row returned.

    Both halves are needed: two posts written in the same millisecond sort by
    id, and an offset-based page would show one of them twice or neither.
    """
    raw = f"{(ensure_utc(moment) or moment).isoformat()}|{row_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        moment, separator, row_id = base64.urlsafe_b64decode(padded).decode().partition("|")
        if not separator:
            raise ValueError("no separator")
        return datetime.fromisoformat(moment), row_id
    except (ValueError, UnicodeDecodeError, binascii.Error) as error:
        raise HTTPException(400, "That page cursor is not valid.") from error


def _older_than(moment_column, id_column, cursor: str):
    moment, row_id = _decode_cursor(cursor)
    return or_(
        moment_column < moment,
        and_(moment_column == moment, id_column < row_id),
    )


def _newer_than(moment_column, id_column, cursor: str):
    moment, row_id = _decode_cursor(cursor)
    return or_(
        moment_column > moment,
        and_(moment_column == moment, id_column > row_id),
    )


# --- Views --------------------------------------------------------------


def _account(session: Session, user_id: str) -> User:
    """The account behind a post, a reply or the caller.

    Every author column is a foreign key to `users` with ON DELETE CASCADE, so
    a post cannot outlive the account that wrote it. Reaching this raise means
    the database has lost that constraint, and the honest answer is a 500 with
    a traceback rather than a post rendered with a blank name.
    """
    user = session.get(User, user_id)
    if user is None:
        raise RuntimeError(f"social row references user {user_id}, which does not exist")
    return user


def _author(user: User, profile: SocialProfile | None) -> AuthorRef:
    return AuthorRef(
        user_id=user.id,
        display_name=user.display_name,
        status=profile.status if profile else None,
    )


def _card(profile: SocialProfile) -> PersonCard:
    return PersonCard(
        user_id=profile.user_id,
        display_name=profile.user.display_name,
        status=profile.status,
        target_city=profile.target_city,
        target_major=profile.target_major,
        universities=[row.name for row in profile.universities],
        bio=profile.bio,
    )


def _post_view(post: Post, author: User, profile: SocialProfile | None, replies: int) -> PostView:
    return PostView(
        id=post.id,
        author=_author(author, profile),
        body=post.body,
        tags=[tag.label for tag in post.tags],
        reply_count=replies,
        created_at=(ensure_utc(post.created_at) or post.created_at).isoformat(),
    )


# --- Joining ------------------------------------------------------------


def _own_profile(session: Session, principal: Principal) -> SocialProfile | None:
    return (
        session.query(SocialProfile)
        .options(joinedload(SocialProfile.user), selectinload(SocialProfile.universities))
        .filter(SocialProfile.user_id == principal.user_id)
        .first()
    )


@router.get("/me", response_model=MyProfileView)
def my_profile(
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> MyProfileView:
    profile = _own_profile(session, principal)
    return MyProfileView(joined=profile is not None, profile=_card(profile) if profile else None)


@router.put("/me", response_model=PersonCard)
def join_or_update(
    payload: ProfileIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PersonCard:
    """Create the social profile, or replace it. The first call is joining."""
    profile = session.get(SocialProfile, principal.user_id)
    if profile is None:
        profile = SocialProfile(user_id=principal.user_id)
        session.add(profile)

    profile.status = payload.status.value if payload.status else None
    profile.target_city = payload.target_city
    profile.target_major = payload.target_major
    profile.bio = payload.bio

    # Two spellings of one university are one university. Deduplicating here
    # rather than letting the unique constraint fire turns a 500 into the
    # obvious behaviour: the first spelling wins and the list is what the
    # person meant.
    wanted: dict[str, str] = {}
    for name in payload.universities:
        key = normalize_key(name)
        if key:
            wanted.setdefault(key, name)

    # Reconcile the rows rather than replacing the collection. Replacing it
    # made SQLAlchemy insert the new rows before deleting the old ones, so
    # saving a profile without changing its universities — editing a bio, the
    # commonest edit there is — collided with `uq_profile_university` and
    # failed with a 500.
    existing = {row.name_key: row for row in profile.universities}
    for key, row in existing.items():
        if key not in wanted:
            profile.universities.remove(row)
    for key, name in wanted.items():
        current = existing.get(key)
        if current is None:
            profile.universities.append(SocialProfileUniversity(name=name))
        else:
            current.name = name  # same university, possibly a new spelling

    session.commit()
    session.refresh(profile)
    return _card(profile)


def _require_membership(session: Session, principal: Principal) -> SocialProfile:
    profile = session.get(SocialProfile, principal.user_id)
    if profile is None:
        raise HTTPException(
            409,
            "Create your social profile before posting. "
            "Registering an account does not publish one.",
        )
    return profile


# --- Discover -----------------------------------------------------------


@router.get("/people", response_model=PeoplePage)
def discover(
    city: str | None = None,
    university: str | None = None,
    major: str | None = None,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = DEFAULT_PAGE,
    cursor: str | None = None,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PeoplePage:
    """People who joined, narrowed by what they are aiming at.

    Every text filter is matched on the normalized key, so "KBTU", "kbtu" and
    "K.B.T.U." are one search.
    """
    query = (
        session.query(SocialProfile)
        .options(joinedload(SocialProfile.user), selectinload(SocialProfile.universities))
        .join(User, User.id == SocialProfile.user_id)
        .filter(User.is_active.is_(True))
    )
    if city:
        query = query.filter(SocialProfile.target_city_key == normalize_key(city))
    if major:
        query = query.filter(SocialProfile.target_major_key == normalize_key(major))
    if status:
        query = query.filter(SocialProfile.status == status)
    if university:
        query = query.join(
            SocialProfileUniversity,
            SocialProfileUniversity.profile_id == SocialProfile.user_id,
        ).filter(SocialProfileUniversity.name_key == normalize_key(university))
    if cursor:
        query = query.filter(_older_than(SocialProfile.created_at, SocialProfile.user_id, cursor))

    rows = (
        query.order_by(SocialProfile.created_at.desc(), SocialProfile.user_id.desc())
        .limit(limit + 1)
        .all()
    )
    page, next_cursor = _split(rows, limit, lambda row: (row.created_at, row.user_id))
    return PeoplePage(items=[_card(row) for row in page], next_cursor=next_cursor)


@router.get("/people/{user_id}", response_model=PersonCard)
def person(
    user_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PersonCard:
    profile = (
        session.query(SocialProfile)
        .options(joinedload(SocialProfile.user), selectinload(SocialProfile.universities))
        .filter(SocialProfile.user_id == user_id)
        .first()
    )
    if profile is None:
        raise HTTPException(404, "This applicant has no social profile.")
    return _card(profile)


def _split(rows: list, limit: int, key) -> tuple[list, str | None]:
    """Trim the lookahead row and turn it into the next cursor."""
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    moment, row_id = key(page[-1])
    return page, _encode_cursor(moment, row_id)


# --- Posts and the feed -------------------------------------------------


@router.post("/posts", response_model=PostView, status_code=201)
def create_post(
    payload: PostIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PostView:
    profile = _require_membership(session, principal)
    post = Post(author_id=principal.user_id, body=payload.body)
    # Tags come out of the text the person wrote. There is no separate tag
    # field to disagree with the body.
    post.tags = [PostTag(label=label) for label in extract_tags(payload.body)]
    session.add(post)
    session.commit()
    session.refresh(post)
    return _post_view(post, _account(session, principal.user_id), profile, 0)


@router.get("/feed", response_model=PostPage)
def feed(
    tag: str | None = None,
    author: str | None = None,
    city: str | None = None,
    university: str | None = None,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = DEFAULT_PAGE,
    cursor: str | None = None,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PostPage:
    """Newest first. Replies are a different table, so none can appear here.

    The people filters read the *author's* profile, which is what makes "posts
    from people going to my city" a single query.
    """
    reply_count = func.count(PostReply.id)
    query = (
        session.query(Post, User, SocialProfile, reply_count)
        .options(selectinload(Post.tags))
        .join(User, User.id == Post.author_id)
        .outerjoin(SocialProfile, SocialProfile.user_id == Post.author_id)
        .outerjoin(PostReply, PostReply.post_id == Post.id)
        .group_by(Post.id, User.id, SocialProfile.user_id)
    )
    if author:
        query = query.filter(Post.author_id == author)
    if city:
        query = query.filter(SocialProfile.target_city_key == normalize_key(city))
    if status:
        query = query.filter(SocialProfile.status == status)
    if university:
        query = query.join(
            SocialProfileUniversity,
            SocialProfileUniversity.profile_id == SocialProfile.user_id,
        ).filter(SocialProfileUniversity.name_key == normalize_key(university))
    if tag:
        query = query.join(PostTag, PostTag.post_id == Post.id).filter(
            PostTag.key == normalize_key(tag)
        )
    if cursor:
        query = query.filter(_older_than(Post.created_at, Post.id, cursor))

    rows = query.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit + 1).all()
    page, next_cursor = _split(rows, limit, lambda row: (row[0].created_at, row[0].id))
    return PostPage(
        items=[_post_view(post, user, profile, int(count)) for post, user, profile, count in page],
        next_cursor=next_cursor,
    )


def _load_post(session: Session, post_id: str) -> Post:
    post = session.query(Post).options(selectinload(Post.tags)).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(404, "This post does not exist.")
    return post


@router.get("/posts/{post_id}", response_model=PostView)
def read_post(
    post_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PostView:
    """One post, so a thread can be opened from a link rather than the feed."""
    post = _load_post(session, post_id)
    replies = session.query(func.count(PostReply.id)).filter(PostReply.post_id == post.id).scalar()
    return _post_view(
        post,
        _account(session, post.author_id),
        session.get(SocialProfile, post.author_id),
        int(replies or 0),
    )


# --- Threads ------------------------------------------------------------


@router.post("/posts/{post_id}/replies", response_model=ReplyView, status_code=201)
def create_reply(
    post_id: str,
    payload: ReplyIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ReplyView:
    profile = _require_membership(session, principal)
    post = _load_post(session, post_id)
    reply = PostReply(post_id=post.id, author_id=principal.user_id, body=payload.body)
    session.add(reply)
    session.commit()
    session.refresh(reply)
    return ReplyView(
        id=reply.id,
        post_id=post.id,
        author=_author(_account(session, principal.user_id), profile),
        body=reply.body,
        created_at=(ensure_utc(reply.created_at) or reply.created_at).isoformat(),
    )


@router.get("/posts/{post_id}/replies", response_model=ReplyPage)
def read_thread(
    post_id: str,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = DEFAULT_PAGE,
    cursor: str | None = None,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ReplyPage:
    """Oldest first: a thread is read in the order it was written."""
    _load_post(session, post_id)
    query = (
        session.query(PostReply, User, SocialProfile)
        .join(User, User.id == PostReply.author_id)
        .outerjoin(SocialProfile, SocialProfile.user_id == PostReply.author_id)
        .filter(PostReply.post_id == post_id)
    )
    if cursor:
        query = query.filter(_newer_than(PostReply.created_at, PostReply.id, cursor))

    rows = query.order_by(PostReply.created_at.asc(), PostReply.id.asc()).limit(limit + 1).all()
    page, next_cursor = _split(rows, limit, lambda row: (row[0].created_at, row[0].id))
    return ReplyPage(
        items=[
            ReplyView(
                id=reply.id,
                post_id=post_id,
                author=_author(user, profile),
                body=reply.body,
                created_at=(ensure_utc(reply.created_at) or reply.created_at).isoformat(),
            )
            for reply, user, profile in page
        ],
        next_cursor=next_cursor,
    )

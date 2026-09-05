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

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

# The module rather than the function: `get_settings` is replaced per test and
# per deployment, and binding the name at import would freeze whichever object
# existed when this module was first imported.
from app import config
from app.db import get_session
from app.domain.enums import (
    DirectMessagePolicy,
    ReportStatus,
    ReportTarget,
)
from app.domain.social import extract_tags, normalize_key
from app.models import (
    Block,
    ContentReport,
    Conversation,
    DirectMessage,
    Post,
    PostReply,
    PostTag,
    SocialProfile,
    SocialProfileUniversity,
    User,
)
from app.models.base import ensure_utc, utcnow
from app.schemas.social import (
    AuthorRef,
    BlockedPage,
    ConversationPage,
    ConversationView,
    MessageIn,
    MessagePage,
    MessageView,
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
    ReporterRef,
    ReportIn,
    ReportPage,
    ReportView,
    ResolveIn,
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
        dm_policy=profile.dm_policy,
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
    profile.dm_policy = payload.dm_policy.value

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


@router.delete("/me", status_code=204)
def leave(
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> Response:
    """Leave the community, keeping the account.

    Joining is a choice, so leaving has to be one too — and the only other way
    out was closing the whole account, which would destroy the applicant
    research the account was opened for.

    Posts and replies go with the profile. Someone who has left a public
    directory has not agreed to leave their name on it, and a post whose author
    is no longer here is exactly that. The deletes are issued by the ORM for the
    same reason account closure issues its own: SQLite's foreign-key pragma is
    per-connection, and this is a privacy promise rather than a best effort.

    Private conversations stay. What is published is addressed to everyone, and
    leaving withdraws it; a private thread was addressed to one person, and
    deleting it would take away their record of a conversation they were half
    of. Leaving still ends being reachable — with no profile there is nobody to
    write to. Closing the account, which is the stronger act, does erase them.
    """
    profile = session.get(SocialProfile, principal.user_id)
    if profile is None:
        raise HTTPException(404, "You are not a member of the community.")

    user = _account(session, principal.user_id)
    for reply in list(user.post_replies):
        session.delete(reply)
    for own_post in list(user.posts):
        session.delete(own_post)
    session.delete(profile)
    session.commit()
    return Response(status_code=204)


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
        .filter(SocialProfile.user_id.notin_(_hidden_from(session, principal.user_id)))
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
        # A block is mutual silence: neither side appears to the other.
        .filter(Post.author_id.notin_(_hidden_from(session, principal.user_id)))
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


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(
    post_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> Response:
    """Retract one post, rather than everything you ever wrote.

    Leaving the community deletes the lot; without this, taking back a single
    sentence meant doing that. The thread goes with the post, as it does
    everywhere else in this module.

    A stranger gets 403, not the 404 the tenant-scoped routes use. There the
    404 hides whether an identifier exists; here the feed has already shown
    them the post, so pretending otherwise would be a lie they can disprove by
    scrolling.
    """
    target = _load_post(session, post_id)
    if target.author_id != principal.user_id:
        raise HTTPException(403, "Only the person who wrote a post can delete it.")
    session.delete(target)
    session.commit()
    return Response(status_code=204)


@router.delete("/posts/{post_id}/replies/{reply_id}", status_code=204)
def delete_reply(
    post_id: str,
    reply_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> Response:
    """Retract one answer. Owning the post does not extend to its answers."""
    reply = (
        session.query(PostReply)
        .filter(PostReply.id == reply_id, PostReply.post_id == post_id)
        .first()
    )
    if reply is None:
        raise HTTPException(404, "This reply does not exist.")
    if reply.author_id != principal.user_id:
        raise HTTPException(403, "Only the person who wrote a reply can delete it.")
    session.delete(reply)
    session.commit()
    return Response(status_code=204)


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
    # Answering someone's post is contact, so a block stops it here too.
    # Otherwise blocking would only silence the private channel and leave the
    # public one — the louder of the two — wide open.
    if _blocked_either_way(session, principal.user_id, post.author_id):
        raise HTTPException(403, "You cannot reply to this applicant's posts.")
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


# --- Private conversations ----------------------------------------------


def _profile_or_404(session: Session, user_id: str) -> SocialProfile:
    profile = session.get(SocialProfile, user_id)
    if profile is None:
        raise HTTPException(404, "This applicant has no social profile.")
    return profile


def _shared_thread(session: Session, one: str, other: str) -> bool:
    """Did one of them answer the other in public?

    Both directions count, and only replies do: writing a post a stranger
    happened to read is not something either of them did together.
    """
    for author, poster in ((one, other), (other, one)):
        exists = (
            session.query(PostReply.id)
            .join(Post, Post.id == PostReply.post_id)
            .filter(PostReply.author_id == author, Post.author_id == poster)
            .first()
        )
        if exists is not None:
            return True
    return False


def _conversation(session: Session, one: str, other: str) -> Conversation | None:
    lower, higher = Conversation.pair(one, other)
    return (
        session.query(Conversation)
        .filter(Conversation.lower_id == lower, Conversation.higher_id == higher)
        .first()
    )


def _may_open(session: Session, sender: str, recipient: SocialProfile) -> bool:
    if recipient.dm_policy == DirectMessagePolicy.ANYONE:
        return True
    if recipient.dm_policy == DirectMessagePolicy.NOBODY:
        return False
    return _shared_thread(session, sender, recipient.user_id)


def _unread_in(session: Session, conversation: Conversation, reader: str) -> int:
    """How many of the other side's messages arrived since the reader looked."""
    query = session.query(func.count(DirectMessage.id)).filter(
        DirectMessage.conversation_id == conversation.id,
        DirectMessage.sender_id != reader,
    )
    seen = conversation.read_at_for(reader)
    if seen is not None:
        query = query.filter(DirectMessage.created_at > seen)
    return int(query.scalar() or 0)


def _departed(session: Session, user_id: str) -> PersonCard:
    """A card for someone who left the community after talking to you.

    Their messages stay — they are half of a conversation the other person is
    still entitled to read — but everything they published is gone, so the card
    carries only the name on the account.
    """
    user = _account(session, user_id)
    return PersonCard(
        user_id=user.id,
        display_name=user.display_name,
        status=None,
        target_city="",
        target_major="",
        universities=[],
        dm_policy=DirectMessagePolicy.NOBODY.value,
        bio="",
    )


def _mine(user_id: str):
    return or_(Conversation.lower_id == user_id, Conversation.higher_id == user_id)


@router.get("/messages", response_model=ConversationPage)
def conversations(
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = DEFAULT_PAGE,
    cursor: str | None = None,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ConversationPage:
    """Every conversation this person is in, most recently active first."""
    query = session.query(Conversation).filter(_mine(principal.user_id))
    if cursor:
        query = query.filter(_older_than(Conversation.last_message_at, Conversation.id, cursor))

    rows = (
        query.order_by(Conversation.last_message_at.desc(), Conversation.id.desc())
        .limit(limit + 1)
        .all()
    )
    page, next_cursor = _split(rows, limit, lambda row: (row.last_message_at, row.id))

    items = []
    for conversation in page:
        other = conversation.other_than(principal.user_id)
        profile = session.get(SocialProfile, other)
        newest = (
            session.query(DirectMessage)
            .filter(DirectMessage.conversation_id == conversation.id)
            .order_by(DirectMessage.created_at.desc())
            .first()
        )
        items.append(
            ConversationView(
                person=_card(profile) if profile else _departed(session, other),
                last_message=newest.body if newest else "",
                last_message_at=(
                    ensure_utc(conversation.last_message_at) or conversation.last_message_at
                ).isoformat(),
                unread=_unread_in(session, conversation, principal.user_id),
            )
        )
    return ConversationPage(items=items, next_cursor=next_cursor)


@router.get("/messages/unread")
def unread_total(
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> dict:
    """One number for the navigation badge, so it costs one request."""
    rows = session.query(Conversation).filter(_mine(principal.user_id)).all()
    return {"unread": sum(_unread_in(session, row, principal.user_id) for row in rows)}


@router.get("/messages/{user_id}", response_model=MessagePage)
def conversation_with(
    user_id: str,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = DEFAULT_PAGE,
    cursor: str | None = None,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> MessagePage:
    """The thread with one person, oldest first.

    Reading it marks it read. That is a write on a GET, which is worth naming:
    the alternative is a second request every screen has to remember to send,
    and a badge that lies whenever one forgets.
    """
    profile = session.get(SocialProfile, user_id)
    person = _card(profile) if profile else _departed(session, user_id)
    conversation = _conversation(session, principal.user_id, user_id)
    if conversation is None:
        return MessagePage(person=person, items=[], next_cursor=None)

    query = session.query(DirectMessage).filter(DirectMessage.conversation_id == conversation.id)
    if cursor:
        query = query.filter(_newer_than(DirectMessage.created_at, DirectMessage.id, cursor))
    rows = (
        query.order_by(DirectMessage.created_at.asc(), DirectMessage.id.asc())
        .limit(limit + 1)
        .all()
    )
    page, next_cursor = _split(rows, limit, lambda row: (row.created_at, row.id))

    if principal.user_id == conversation.lower_id:
        conversation.lower_read_at = utcnow()
    else:
        conversation.higher_read_at = utcnow()
    session.commit()

    return MessagePage(
        person=person,
        items=[
            MessageView(
                id=message.id,
                body=message.body,
                created_at=(ensure_utc(message.created_at) or message.created_at).isoformat(),
                mine=message.sender_id == principal.user_id,
            )
            for message in page
        ],
        next_cursor=next_cursor,
    )


@router.post("/messages/{user_id}", response_model=MessageView, status_code=201)
def send_message(
    user_id: str,
    payload: MessageIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> MessageView:
    """Write to someone, opening the conversation if they do not have one.

    The recipient's policy is checked only when there is no conversation yet.
    Closing an inbox stops strangers arriving; it does not silence someone you
    were already talking to, which would be a way of ending a conversation
    without saying so.
    """
    if user_id == principal.user_id:
        raise HTTPException(400, "You cannot write to yourself.")
    _require_membership(session, principal)
    # Checked before the conversation, so a block ends an existing thread too.
    # A block that only stopped new conversations would leave the person who
    # already had one able to keep writing, which is the case that matters.
    if _blocked_either_way(session, principal.user_id, user_id):
        raise HTTPException(403, "This conversation is closed.")
    recipient = _profile_or_404(session, user_id)

    conversation = _conversation(session, principal.user_id, user_id)
    if conversation is None:
        if not _may_open(session, principal.user_id, recipient):
            raise HTTPException(
                403,
                "This applicant only accepts messages from people they have answered in "
                "public, or has turned messages off.",
            )
        lower, higher = Conversation.pair(principal.user_id, user_id)
        conversation = Conversation(lower_id=lower, higher_id=higher)
        session.add(conversation)
        session.flush()

    message = DirectMessage(
        conversation_id=conversation.id, sender_id=principal.user_id, body=payload.body
    )
    session.add(message)
    session.flush()
    conversation.last_message_at = message.created_at
    # Writing is reading: a line you just sent is not unread to you.
    if principal.user_id == conversation.lower_id:
        conversation.lower_read_at = message.created_at
    else:
        conversation.higher_read_at = message.created_at
    session.commit()
    session.refresh(message)

    return MessageView(
        id=message.id,
        body=message.body,
        created_at=(ensure_utc(message.created_at) or message.created_at).isoformat(),
        mine=True,
    )


# --- Blocking ------------------------------------------------------------


def _blocked_either_way(session: Session, one: str, other: str) -> bool:
    """Whether a block stands between these two, in either direction.

    Enforced symmetrically on purpose. A one-way silence would tell the blocked
    person they had been blocked — the blocker's posts would keep appearing
    while theirs vanished — and being told is its own kind of contact.
    """
    return (
        session.query(Block.id)
        .filter(
            or_(
                and_(Block.blocker_id == one, Block.blocked_id == other),
                and_(Block.blocker_id == other, Block.blocked_id == one),
            )
        )
        .first()
        is not None
    )


def _hidden_from(session: Session, user_id: str):
    """The ids this person must not be shown, for a NOT IN."""
    return session.query(Block.blocked_id).filter(Block.blocker_id == user_id).union(
        session.query(Block.blocker_id).filter(Block.blocked_id == user_id)
    )


@router.get("/blocks", response_model=BlockedPage)
def blocked_people(
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> BlockedPage:
    """Who you have blocked. Yours to read, and the only way to undo one."""
    rows = (
        session.query(Block, User)
        .join(User, User.id == Block.blocked_id)
        .filter(Block.blocker_id == principal.user_id)
        .order_by(Block.created_at.desc())
        .all()
    )
    return BlockedPage(
        items=[ReporterRef(user_id=user.id, display_name=user.display_name) for _, user in rows]
    )


@router.post("/blocks/{user_id}", status_code=204)
def block(
    user_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> Response:
    """Stop someone reaching you. Takes effect at once and asks nobody."""
    if user_id == principal.user_id:
        raise HTTPException(400, "You cannot block yourself.")
    _account(session, user_id)
    if not _blocked_either_way(session, principal.user_id, user_id):
        session.add(Block(blocker_id=principal.user_id, blocked_id=user_id))
        session.commit()
    return Response(status_code=204)


@router.delete("/blocks/{user_id}", status_code=204)
def unblock(
    user_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> Response:
    row = (
        session.query(Block)
        .filter(Block.blocker_id == principal.user_id, Block.blocked_id == user_id)
        .first()
    )
    if row is not None:
        session.delete(row)
        session.commit()
    return Response(status_code=204)


# --- Reporting and the queue --------------------------------------------


def _subject(session: Session, kind: str, subject_id: str) -> tuple[str | None, str]:
    """The author and an excerpt of the reported thing, or a 404."""
    if kind == ReportTarget.POST:
        row = session.get(Post, subject_id)
        if row is not None:
            return row.author_id, row.body
    elif kind == ReportTarget.REPLY:
        reply = session.get(PostReply, subject_id)
        if reply is not None:
            return reply.author_id, reply.body
    elif kind == ReportTarget.MESSAGE:
        message = session.get(DirectMessage, subject_id)
        if message is not None:
            return message.sender_id, message.body
    elif kind == ReportTarget.PROFILE:
        profile = session.get(SocialProfile, subject_id)
        if profile is not None:
            return profile.user_id, profile.bio
    raise HTTPException(404, "There is nothing here to report.")


def _report_view(session: Session, report: ContentReport) -> ReportView:
    reporter = _account(session, report.reporter_id)
    author = session.get(User, report.subject_author_id) if report.subject_author_id else None
    return ReportView(
        id=report.id,
        reporter=ReporterRef(user_id=reporter.id, display_name=reporter.display_name),
        subject_type=report.subject_type,
        subject_id=report.subject_id,
        subject_author=(
            ReporterRef(user_id=author.id, display_name=author.display_name) if author else None
        ),
        reason=report.reason,
        note=report.note,
        excerpt=report.excerpt,
        status=report.status,
        created_at=(ensure_utc(report.created_at) or report.created_at).isoformat(),
        resolved_by=report.resolved_by,
        resolution_note=report.resolution_note,
    )


@router.post("/reports", response_model=ReportView, status_code=201)
def file_report(
    payload: ReportIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ReportView:
    """Ask a moderator to look at something.

    A private message can be reported, but only by one of the two people in the
    conversation. Reporting is the one thing that puts a private line in front
    of somebody else, and the person receiving harassment has to be able to do
    it; nobody else has any business naming a message id.
    """
    author, excerpt = _subject(session, payload.subject_type.value, payload.subject_id)
    if payload.subject_type == ReportTarget.MESSAGE:
        message = session.get(DirectMessage, payload.subject_id)
        conversation = session.get(Conversation, message.conversation_id) if message else None
        if conversation is None or principal.user_id not in (
            conversation.lower_id,
            conversation.higher_id,
        ):
            raise HTTPException(404, "There is nothing here to report.")

    already = (
        session.query(ContentReport)
        .filter(
            ContentReport.reporter_id == principal.user_id,
            ContentReport.subject_type == payload.subject_type.value,
            ContentReport.subject_id == payload.subject_id,
        )
        .first()
    )
    if already is not None:
        raise HTTPException(409, "You have already reported this.")

    report = ContentReport(
        reporter_id=principal.user_id,
        subject_type=payload.subject_type.value,
        subject_id=payload.subject_id,
        subject_author_id=author,
        reason=payload.reason.value,
        note=payload.note,
        excerpt=excerpt[:600],
        status=ReportStatus.OPEN.value,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return _report_view(session, report)


def require_moderator(principal: Principal = Depends(get_principal)) -> Principal:
    """The deployment names its moderators; nothing in the database grants this.

    A workspace owner administers their own tenant, and the community is not
    theirs — it spans every workspace — so no tenant role can carry this. See
    `Settings.moderator_emails` for why that is a setting rather than a table.
    """
    if principal.email.casefold() not in config.get_settings().moderator_email_list:
        raise HTTPException(403, "This is the moderation queue for this deployment.")
    return principal


@router.get("/moderation/reports", response_model=ReportPage)
def moderation_queue(
    status: str = ReportStatus.OPEN.value,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = DEFAULT_PAGE,
    cursor: str | None = None,
    principal: Principal = Depends(require_moderator),
    session: Session = Depends(get_session),
) -> ReportPage:
    """Reports in one status, oldest first: a queue, not a feed."""
    if status not in {s.value for s in ReportStatus}:
        raise HTTPException(400, f"Unknown report status {status!r}.")
    query = session.query(ContentReport).filter(ContentReport.status == status)
    if cursor:
        query = query.filter(_newer_than(ContentReport.created_at, ContentReport.id, cursor))
    rows = (
        query.order_by(ContentReport.created_at.asc(), ContentReport.id.asc())
        .limit(limit + 1)
        .all()
    )
    page, next_cursor = _split(rows, limit, lambda row: (row.created_at, row.id))
    return ReportPage(
        items=[_report_view(session, report) for report in page], next_cursor=next_cursor
    )


def _remove_subject(session: Session, report: ContentReport) -> None:
    """Delete the reported content, if it is still there.

    A profile is emptied rather than the account deleted: the person behind it
    is still applying to universities, and their research is not the
    community's to take away. This is the same operation as leaving the
    community, performed by somebody else.
    """
    kind = report.subject_type
    if kind == ReportTarget.PROFILE:
        profile = session.get(SocialProfile, report.subject_id)
        if profile is not None:
            user = _account(session, profile.user_id)
            for reply in list(user.post_replies):
                session.delete(reply)
            for own_post in list(user.posts):
                session.delete(own_post)
            session.delete(profile)
        return

    row: Post | PostReply | DirectMessage | None = None
    if kind == ReportTarget.POST:
        row = session.get(Post, report.subject_id)
    elif kind == ReportTarget.REPLY:
        row = session.get(PostReply, report.subject_id)
    elif kind == ReportTarget.MESSAGE:
        row = session.get(DirectMessage, report.subject_id)
    if row is not None:
        session.delete(row)


@router.post("/moderation/reports/{report_id}", response_model=ReportView)
def resolve_report(
    report_id: str,
    payload: ResolveIn,
    principal: Principal = Depends(require_moderator),
    session: Session = Depends(get_session),
) -> ReportView:
    """Act on a report, or close it having decided there is nothing to do.

    Removing content that has already gone still closes the report rather than
    failing: the author deleting their own post is the outcome the report asked
    for, and a queue that cannot record that fills with work nobody can finish.

    Who resolved it and what they wrote is kept on the row. Deleting somebody
    else's words is not a traceless act.
    """
    report = session.get(ContentReport, report_id)
    if report is None:
        raise HTTPException(404, "No such report.")
    if report.status != ReportStatus.OPEN.value:
        raise HTTPException(409, "This report has already been resolved.")

    if payload.action == "remove":
        _remove_subject(session, report)

    report.status = (
        ReportStatus.ACTIONED.value if payload.action == "remove" else ReportStatus.DISMISSED.value
    )
    report.resolved_by = principal.email
    report.resolved_at = utcnow()
    report.resolution_note = payload.note
    session.commit()
    session.refresh(report)
    return _report_view(session, report)

"""The social module: applicant profiles, posts and threads.

**These tables are global, not tenant-scoped, and that is deliberate.**

Everywhere else in this product an organization is the case boundary: every
query filters by `organization_id`, and knowing a UUID is never authority.
Registration gives each account its own workspace, so a social graph scoped the
same way would only ever show a person themselves. Discover is the one feature
whose whole purpose is to cross that boundary.

The boundary that replaces it is narrower and is enforced by what these tables
contain rather than by who is asking: a social row holds only what its owner
typed into their social profile or a post. Nothing here references an applicant
case, a research run, a claim or a shortlist, so no query written against these
tables — however careless — can reach one.

The second rule this module keeps is the product's own: it never converts an
unknown into a guess. A person's `status` is null until they state it, and it
is rendered as "not stated", never defaulted to `waitlist` so that a screen can
look complete.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.domain.social import (
    BIO_MAX_CHARS,
    MESSAGE_MAX_CHARS,
    POST_MAX_CHARS,
    REPLY_MAX_CHARS,
    normalize_key,
)
from app.models.base import Base, TimestampedBase, utcnow

if TYPE_CHECKING:
    from app.models.auth import User


def _body_constraints(table: str, limit: int) -> tuple[CheckConstraint, ...]:
    """Length and non-emptiness, held by the database rather than by a caller.

    Pydantic already rejects both at the API boundary. This is the second line:
    a seed script, a migration backfill or a future admin path does not get to
    write a 10 kB "post" or an empty one.
    """
    return (
        CheckConstraint(f"length(body) <= {limit}", name=f"ck_{table}_body_max_length"),
        CheckConstraint("length(trim(body)) > 0", name=f"ck_{table}_body_not_blank"),
    )


class SocialProfile(Base):
    """What an applicant chooses to show other applicants.

    Separate from `users` on purpose. `users` is the authentication record and
    exists for every account; this row exists only once someone has joined the
    social side, so "has a profile" is what puts a person in Discover. Nobody is
    listed in a public directory as a side effect of registering.
    """

    __tablename__ = "social_profiles"

    #: The user *is* the profile's identity — one row per account, no separate
    #: surrogate key to keep in sync.
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    #: `accepted` or `waitlist` from `ApplicantStatus`, or null for "not stated".
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    #: Each filterable field is stored twice: as it was typed, and folded to the
    #: key the index uses. "Astana", "astana" and "  ASTANA " are one city to
    #: the filter and still three different profiles on screen.
    target_city: Mapped[str] = mapped_column(String(120), default="")
    target_city_key: Mapped[str] = mapped_column(String(120), default="", index=True)
    target_major: Mapped[str] = mapped_column(String(120), default="")
    target_major_key: Mapped[str] = mapped_column(String(120), default="", index=True)

    bio: Mapped[str] = mapped_column(String(BIO_MAX_CHARS), default="")
    avatar_url: Mapped[str] = mapped_column(String(500), default="")

    #: Who may start a conversation with this person — `DirectMessagePolicy`.
    #: Not null and not a guess: everyone gets the narrow default until they
    #: choose otherwise. See the enum for why that is the right way round.
    dm_policy: Mapped[str] = mapped_column(String(20), default="threads")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(back_populates="social_profile")
    universities: Mapped[list[SocialProfileUniversity]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=False,
        order_by="SocialProfileUniversity.name",
    )

    @validates("target_city", "target_major")
    def _derive_key(self, field: str, value: str | None) -> str:
        """Keep the indexed key in step with the value on every assignment."""
        text = (value or "").strip()
        setattr(self, f"{field}_key", normalize_key(text))
        return text


class SocialProfileUniversity(Base):
    """One university on someone's target list.

    A row rather than a JSON array, because Discover filters by university and a
    JSON array cannot be indexed the same way in both PostgreSQL and SQLite. The
    product has no university registry — names come from the person — so the
    normalized key is what makes two spellings of one place match.
    """

    __tablename__ = "social_profile_universities"
    __table_args__ = (
        UniqueConstraint("profile_id", "name_key", name="uq_profile_university"),
        Index("ix_social_profile_universities_name_key", "name_key"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=None)
    profile_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("social_profiles.user_id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160))
    name_key: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped[SocialProfile] = relationship(back_populates="universities")

    def __init__(self, **kwargs: object) -> None:
        from app.models.base import new_id

        kwargs.setdefault("id", new_id())
        super().__init__(**kwargs)

    @validates("name")
    def _derive_key(self, _field: str, value: str) -> str:
        text = (value or "").strip()
        self.name_key = normalize_key(text)
        return text


class Post(TimestampedBase):
    """A short message in the feed.

    Replies are a different table, not a self-reference with a null parent. The
    feed is therefore `SELECT FROM posts` with nothing to filter out, which is
    the one bug this shape cannot have.
    """

    __tablename__ = "posts"
    __table_args__ = (
        *_body_constraints("posts", POST_MAX_CHARS),
        Index("ix_posts_author_created", "author_id", "created_at"),
        Index("ix_posts_created_at_id", "created_at", "id"),
    )

    author_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text)

    author: Mapped[User] = relationship(back_populates="posts")
    tags: Mapped[list[PostTag]] = relationship(
        back_populates="post", cascade="all, delete-orphan", passive_deletes=False
    )
    #: A thread belongs to its post. Deleting the post deletes the thread,
    #: including replies other people wrote — there is nowhere for an orphaned
    #: answer to a deleted question to be read in context.
    replies: Mapped[list[PostReply]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=False,
        order_by="PostReply.created_at",
    )


class PostTag(Base):
    """A `#KBTU` or `#Astana` attached to a post.

    Deliberately untyped: the product cannot tell a university from a city
    without a registry it does not have, and guessing would be a claim. A tag is
    a string somebody wrote, indexed so the feed can filter by it.
    """

    __tablename__ = "post_tags"
    __table_args__ = (
        UniqueConstraint("post_id", "key", name="uq_post_tag"),
        Index("ix_post_tags_key", "key"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=None)
    post_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    #: As typed, for display.
    label: Mapped[str] = mapped_column(String(40))
    #: Folded, for matching.
    key: Mapped[str] = mapped_column(String(40))

    post: Mapped[Post] = relationship(back_populates="tags")

    def __init__(self, **kwargs: object) -> None:
        from app.models.base import new_id

        kwargs.setdefault("id", new_id())
        super().__init__(**kwargs)

    @validates("label")
    def _derive_key(self, _field: str, value: str) -> str:
        text = (value or "").strip().lstrip("#")
        self.key = normalize_key(text)
        return text


class PostReply(TimestampedBase):
    """One answer in a post's thread. One level deep, by design."""

    __tablename__ = "post_replies"
    __table_args__ = (
        *_body_constraints("post_replies", REPLY_MAX_CHARS),
        Index("ix_post_replies_post_created", "post_id", "created_at"),
    )

    post_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text)

    post: Mapped[Post] = relationship(back_populates="replies")
    author: Mapped[User] = relationship(back_populates="post_replies")


class Conversation(TimestampedBase):
    """One private thread between exactly two people.

    The pair is stored ordered — `lower_id` is always the smaller of the two
    user ids — so a unique constraint is all it takes to stop the same two
    people ending up with two conversations from a simultaneous first message.

    Read state is two columns rather than a per-message read table. The only
    question anyone asks is "is there anything new for me here", and a
    timestamp answers it without a row per message per reader.
    """

    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("lower_id", "higher_id", name="uq_conversation_pair"),
        CheckConstraint("lower_id < higher_id", name="ck_conversations_ordered_pair"),
        Index("ix_conversations_lower_activity", "lower_id", "last_message_at"),
        Index("ix_conversations_higher_activity", "higher_id", "last_message_at"),
    )

    lower_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    higher_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    #: Kept in step with the newest message so the list can be ordered without
    #: an aggregate over every message the two have ever exchanged.
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    lower_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    higher_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list[DirectMessage]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=False,
        order_by="DirectMessage.created_at",
    )

    @staticmethod
    def pair(one: str, other: str) -> tuple[str, str]:
        """The two ids in the order this table stores them."""
        return (one, other) if one < other else (other, one)

    def read_at_for(self, user_id: str) -> datetime | None:
        return self.lower_read_at if user_id == self.lower_id else self.higher_read_at

    def other_than(self, user_id: str) -> str:
        return self.higher_id if user_id == self.lower_id else self.lower_id


class DirectMessage(TimestampedBase):
    """One message. Same limits as a post: this is a conversation, not a file transfer."""

    __tablename__ = "direct_messages"
    __table_args__ = (
        *_body_constraints("direct_messages", MESSAGE_MAX_CHARS),
        Index("ix_direct_messages_conversation_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

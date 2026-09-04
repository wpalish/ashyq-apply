"""The social API's boundary types.

Every limit here is also a database constraint. Pydantic gives the person a 422
with a reason; the CHECK constraint is what makes the limit true.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ApplicantStatus
from app.domain.social import (
    BIO_MAX_CHARS,
    MAX_TARGET_UNIVERSITIES,
    POST_MAX_CHARS,
    REPLY_MAX_CHARS,
)

UniversityName = Annotated[str, Field(min_length=1, max_length=160)]


class Base(BaseModel):
    #: `extra="forbid"` so a typo in a field name is an error rather than a
    #: silently ignored edit; whitespace is stripped before length is judged,
    #: which is what turns a post of three spaces into a 422.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- Input --------------------------------------------------------------


class ProfileIn(Base):
    #: Null is a real answer: "I have not said". There is no default status.
    status: ApplicantStatus | None = None
    target_city: Annotated[str, Field(max_length=120)] = ""
    target_major: Annotated[str, Field(max_length=120)] = ""
    bio: Annotated[str, Field(max_length=BIO_MAX_CHARS)] = ""
    universities: list[UniversityName] = Field(
        default_factory=list, max_length=MAX_TARGET_UNIVERSITIES
    )


class PostIn(Base):
    body: Annotated[str, Field(min_length=1, max_length=POST_MAX_CHARS)]


class ReplyIn(Base):
    body: Annotated[str, Field(min_length=1, max_length=REPLY_MAX_CHARS)]


# --- Output -------------------------------------------------------------


class AuthorRef(BaseModel):
    """Who wrote something. Name and stated status, nothing else."""

    user_id: str
    display_name: str
    status: str | None


class PersonCard(BaseModel):
    """A Discover card, and the whole of a public profile.

    This shape is the tenant boundary made concrete: it carries what its owner
    typed into their social profile and nothing else. No email, no organization,
    nothing from an applicant case.
    """

    user_id: str
    display_name: str
    status: str | None
    target_city: str
    target_major: str
    universities: list[str]
    bio: str


class MyProfileView(BaseModel):
    """`joined` is false for a registered account that never joined. That is a
    normal state, not an error, so it is a 200 rather than a 404."""

    joined: bool
    profile: PersonCard | None


class PostView(BaseModel):
    id: str
    author: AuthorRef
    body: str
    tags: list[str]
    reply_count: int
    created_at: str


class ReplyView(BaseModel):
    id: str
    post_id: str
    author: AuthorRef
    body: str
    created_at: str


class PeoplePage(BaseModel):
    items: list[PersonCard]
    next_cursor: str | None = None


class PostPage(BaseModel):
    items: list[PostView]
    next_cursor: str | None = None


class ReplyPage(BaseModel):
    items: list[ReplyView]
    next_cursor: str | None = None

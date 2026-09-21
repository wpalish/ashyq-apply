"""Claims: the unit of evidence.

Nothing in the result table is displayed unless it traces back to a Claim, and
every Claim carries the URL, the excerpt, the academic year and the moment it
was read. Excerpts are capped so we store proof, not copies of pages.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_serializer

from app.domain.claim_scope import ClaimScope
from app.domain.enums import ClaimStatus, ClaimType, SourceSpecificity

#: Excerpts exist to prove a value was read, not to reproduce the page.
MAX_EXCERPT_CHARS = 600


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Claim(Base):
    claim_type: ClaimType
    normalized_value: Any = Field(description="Parsed value: float, str, bool, list or dict")
    original_text_excerpt: str = ""
    source_url: str
    page_title: str = ""
    relevant_section: str = ""
    official_domain: bool = False
    program: str | None = None
    subject_key: str | None = Field(
        default=None,
        description=(
            "What the claim is about within the page, e.g. a scholarship name. Two claims of the "
            "same type only contradict each other when they describe the same subject."
        ),
    )
    intake: str | None = None
    academic_year: str | None = Field(default=None, description="e.g. '2026/27'")
    accessed_at: datetime
    #: Who and what the source says this claim is about, across the nine
    #: dimensions in ``app.domain.claim_scope``.
    #:
    #: ``None`` means **nobody recorded a scope**, which is not the same as
    #: ``ClaimScope()`` — an empty scope recorded deliberately after reading a
    #: page that stated none. The distinction matters: the first is a gap in
    #: our own pipeline, the second is a fact about the page.
    #:
    #: The flat ``program`` / ``intake`` / ``academic_year`` fields above stay
    #: as they are. Nothing reads this one yet, so nothing may depend on it,
    #: and removing them would break every extractor at once.
    #:
    #: When it is ``None`` the key is left out of the serialised claim
    #: entirely — see :meth:`_omit_unrecorded_scope`. Absent in the JSON means
    #: exactly what ``None`` means in the model, and every claim written
    #: before this field existed keeps its byte-identical payload.
    scope: ClaimScope | None = None
    source_specificity: SourceSpecificity = SourceSpecificity.UNKNOWN
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    extraction_method: Literal["structured", "html_rule", "pdf_rule", "llm_assisted", "fixture"] = (
        "html_rule"
    )
    notes: str = ""

    @model_serializer(mode="wrap")
    def _omit_unrecorded_scope(self, handler):
        """Leave ``scope`` out of the JSON when nobody recorded one.

        ``None`` here means *no scope was recorded*, and a key whose value is
        "we never looked" is worse than no key: it invites a reader to treat
        the absence as a finding. Omitting it also keeps every claim written
        before this field existed byte-identical, which a regression test in
        the suite checks against a golden hash — so this is load-bearing, not
        tidiness.
        """
        data = handler(self)
        if isinstance(data, dict) and data.get("scope") is None:
            data.pop("scope", None)
        return data

    @field_validator("original_text_excerpt", mode="before")
    @classmethod
    def _truncate(cls, v: object) -> str:
        """Truncate rather than reject.

        Extractors hand us whatever surrounds a match; clipping here means no
        caller has to remember the cap, and we never store a whole page.
        """
        text = "" if v is None else str(v)
        return text[:MAX_EXCERPT_CHARS]

    @field_validator("source_url")
    @classmethod
    def _url_shape(cls, v: str) -> str:
        if not v.startswith(("http://", "https://", "fixture://")):
            raise ValueError("source_url must be http(s) or a fixture:// reference")
        return v


class ClaimOut(Claim):
    id: str
    is_stale: bool = False
    age_days: int = 0


class Conflict(Base):
    """Two official sources disagreeing. Never resolved silently."""

    claim_type: ClaimType
    subject: str = Field(description="What the conflict is about, e.g. 'IELTS overall minimum'")
    claim_ids: list[str]
    values: list[Any]
    source_urls: list[str]
    preferred_claim_id: str | None = Field(
        default=None,
        description="Higher-specificity source, shown as 'preferred' but never as settled",
    )
    resolution_rule: str = ""
    question_for_admissions: str = Field(
        description="A ready-to-send question the applicant can email the admissions office"
    )
    unresolved: bool = True


class UnresolvedQuestion(Base):
    """Something the pipeline could not determine from official sources."""

    topic: str
    question: str
    why_it_matters: str
    university: str | None = None
    program: str | None = None
    suggested_contact: str | None = None
    blocking: bool = False

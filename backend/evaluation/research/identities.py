"""Explicit output identities, not expected answers or evidence adjudication."""

import re
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, HttpUrl, model_validator

from .metrics import canonical_url
from .schema import Strict


class Binding(Strict):
    kind: Literal["award", "document"]
    source_url: HttpUrl
    subject: str = Field(min_length=1)
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
    notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def namespace(self) -> Self:
        parts = self.key.split(".")
        if self.kind == "award" and (len(parts) != 2 or parts[0] != "scholarships"):
            raise ValueError("Award key must be scholarships.<id>")
        if self.kind == "document" and (
            len(parts) < 3
            or parts[0] != "documents"
            or parts[1] not in {"admission", "programme", "scholarship"}
        ):
            raise ValueError("Document key must specify admission/programme/scholarship purpose")
        return self


class IdentityMap(Strict):
    version: str = Field(min_length=1)
    bindings: list[Binding]

    @model_validator(mode="after")
    def no_ambiguous_bindings(self) -> Self:
        identities = [(b.kind, canonical_url(b.source_url), b.subject) for b in self.bindings]
        if len(set(identities)) != len(identities):
            raise ValueError("Duplicate or ambiguous source/subject identity")
        return self

    def resolve(self, kind: str, source_url: str, subject: object) -> str | None:
        if not isinstance(subject, str):
            return None
        for binding in self.bindings:
            if (
                binding.kind == kind
                and canonical_url(binding.source_url) == canonical_url(source_url)
                and binding.subject == subject
            ):
                return binding.key
        # ID-1: the same award page under another path of the same host. The
        # subject must still be the binding's exactly; only the URL spelling
        # may differ, and only when every binding it could be agrees. Awards
        # only: a document binding's subject names a document, not its page.
        keys = {
            binding.key
            for binding in self.bindings
            if ID1_URL_ALIAS
            and kind == "award"
            and binding.kind == kind
            and binding.subject == subject
            and same_award_page(str(binding.source_url), source_url, subject)
        }
        return keys.pop() if len(keys) == 1 else None


#: ID-1 URL alias: it widens how a signed binding URL matches. On by default
#: since the owner signed it (corpus corrections round, 02-Q1, 2026-10-18).
ID1_URL_ALIAS = True


#: Path words that name a kind of page, not an award: a final segment made of
#: these alone ("scholarships", "detail", "index.html") identifies nothing.
_GENERIC_SLUG_WORDS = frozenset(
    {
        "admissions",
        "and",
        "award",
        "awards",
        "bursaries",
        "bursary",
        "detail",
        "details",
        "financial",
        "funding",
        "grant",
        "grants",
        "index",
        "of",
        "opportunities",
        "overview",
        "page",
        "pg",
        "postgraduate",
        "scholarship",
        "scholarships",
        "the",
        "ug",
        "undergraduate",
    }
)
_PAGE_EXTENSION = re.compile(r"\.(?:html?|php|aspx?)$", re.IGNORECASE)


def _slug_words(segment: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", _PAGE_EXTENSION.sub("", segment.casefold())) if w]


def same_award_page(binding_url: str, source_url: str, subject: str) -> bool:
    """ID-1 (core-gap analysis 2026-10-18 change 3): whether ``source_url`` is
    the binding's award page under another path of the same host.

    NTU serves the Nanyang Global Scholarship at ``/admissions/ug/scholarships/
    …/detail/nanyang-scholarship``; the bindings spell it ``/admissions/
    undergraduate/scholarships/…`` and ``…/scholarships-and-awards/…``. Same
    host, same query, and the same final path segment, which must name the
    award: at least one of its words is neither generic nor a number and is a
    word of the award's own name ("nanyang"). A hub, an index or another
    award's page has another final segment and is never an alias.
    """
    ours, theirs = urlsplit(canonical_url(source_url)), urlsplit(canonical_url(binding_url))
    if ours.netloc != theirs.netloc or ours.query != theirs.query:
        return False
    segment = ours.path.rsplit("/", 1)[-1]
    if not segment or segment != theirs.path.rsplit("/", 1)[-1]:
        return False
    named = set(re.findall(r"[a-z0-9]+", subject.casefold()))
    return any(
        w not in _GENERIC_SLUG_WORDS and not w.isdigit() and w in named
        for w in _slug_words(segment)
    )

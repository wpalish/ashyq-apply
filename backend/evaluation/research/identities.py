"""Explicit output identities, not expected answers or evidence adjudication."""

from typing import Literal, Self

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
        return None

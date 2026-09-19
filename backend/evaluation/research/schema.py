"""Labels and observations are separate inputs: answers never enter the runner."""

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, JsonValue, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Scope(Strict):
    university: str
    programme: str | None = None
    degree: str | None = None
    field: str | None = None
    intake: str | None = None
    population: str | None = None
    qualification: str | None = None
    academic_year: str | None = None


class Evidence(Strict):
    url: HttpUrl
    excerpt: str = Field(min_length=1, max_length=600)
    scope: Scope
    accessed_on: date
    source_type: Literal["official", "government", "aggregator", "unknown"]


class Review(Strict):
    status: Literal["draft", "human_verified"] = "draft"
    prepared_by: str = Field(min_length=1)
    reviewer: str | None = None
    verified_on: date | None = None
    notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def human_identity(self) -> Self:
        if self.status == "human_verified" and (not self.reviewer or not self.verified_on):
            raise ValueError("Human verification needs reviewer and date")
        return self


class Label(Strict):
    # A path preserves separate subscores, fee categories and scholarship dimensions.
    # e.g. scholarships.<award>.applicability.degree, documents.admission.transcript.
    key: str = Field(min_length=1)
    status: Literal["known", "unknown", "not_applicable"]
    value: JsonValue = None
    evidence: list[Evidence] = Field(default_factory=list)
    critical: bool = True
    notes: str = ""

    @model_validator(mode="after")
    def supported_label(self) -> Self:
        if self.status == "known" and (self.value is None or not self.evidence):
            raise ValueError("Known labels require a value and evidence")
        if self.status != "known" and self.value is not None:
            raise ValueError("Unknown/N-A cannot contain a guessed value")
        return self


class Case(Strict):
    id: str
    dataset_version: str
    university: str
    domain: str
    country: str
    site_types: list[str]
    request: Scope
    programme_urls: list[HttpUrl] = Field(default_factory=list)
    programme_status: Literal["known", "unknown", "absent"] = "unknown"
    programme_evidence: list[Evidence] = Field(default_factory=list)
    labels: list[Label]
    review: Review

    @model_validator(mode="after")
    def unique_labels(self) -> Self:
        if len({label.key for label in self.labels}) != len(self.labels):
            raise ValueError("Duplicate label key")
        if self.programme_status == "known" and (
            not self.programme_urls or not self.programme_evidence
        ):
            raise ValueError("Known programme needs URLs and evidence")
        return self


class Dataset(Strict):
    schema_version: Literal["1"] = "1"
    version: str
    split: Literal["development", "validation"]
    cases: list[Case] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent_version(self) -> Self:
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("Duplicate case ID")
        if any(case.dataset_version != self.version for case in self.cases):
            raise ValueError("Case version differs from dataset version")
        return self


class Prediction(Strict):
    key: str
    value: JsonValue
    evidence: Evidence | None = None
    # null means not adjudicated, never silently classified as supported.
    supported: bool | None = None
    current: bool | None = None
    conflict_visible: bool | None = None


class Telemetry(Strict):
    http_fetches: int | None = Field(default=None, ge=0)
    browser_fetches: int | None = Field(default=None, ge=0)
    pdf_fetches: int | None = Field(default=None, ge=0)
    search_calls: int | None = Field(default=None, ge=0)
    model_input_tokens: int | None = Field(default=None, ge=0)
    jev_input_tokens: int | None = Field(default=None, ge=0)
    latency_seconds: float | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    human_review_required: bool | None = None


class Observation(Strict):
    case_id: str
    programme_urls: list[HttpUrl] = Field(default_factory=list)
    ranked_urls: list[HttpUrl] | None = None
    predictions: list[Prediction] = Field(default_factory=list)
    telemetry: Telemetry = Field(default_factory=Telemetry)
    error: str | None = None


class Capture(Strict):
    schema_version: Literal["1"] = "1"
    pipeline_sha: str
    captured_at: str
    mode: Literal["live", "synthetic", "replay"]
    config: dict[str, JsonValue]
    observations: list[Observation]

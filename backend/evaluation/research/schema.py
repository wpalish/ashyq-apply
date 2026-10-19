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
    excerpt_truncated: bool = False


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
        if self.status == "known" and any(
            e.source_type not in {"official", "government"} for e in self.evidence
        ):
            raise ValueError("Ground truth must use primary official evidence")
        if self.status != "known" and self.value is not None:
            raise ValueError("Unknown/N-A cannot contain a guessed value")
        if self.status == "not_applicable" and not self.notes.strip():
            raise ValueError("Not-applicable labels require a reason")
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
    #: v3-M2 (ticket 03 Q3): pages the reviewer labels as a related programme
    #: (a sibling specialisation, a major page, the field's bachelor in another
    #: faculty). Returned, one is neither a hit nor a wrong page. Not serialised
    #: while empty, so every corpus written before it keeps its digest.
    related_programme_urls: list[HttpUrl] = Field(
        default_factory=list, exclude_if=lambda urls: not urls
    )

    @model_validator(mode="after")
    def unique_labels(self) -> Self:
        if len({label.key for label in self.labels}) != len(self.labels):
            raise ValueError("Duplicate label key")
        if self.programme_status == "known" and (
            not self.programme_urls or not self.programme_evidence
        ):
            raise ValueError("Known programme needs URLs and evidence")
        if any(e.source_type not in {"official", "government"} for e in self.programme_evidence):
            raise ValueError("Programme ground truth must use primary official evidence")
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
    #: Every query sent to the provider, ``search`` and ``search_localized``
    #: alike: the number the 6-query budget is held against.
    search_calls: int | None = Field(default=None, ge=0)
    #: Of ``search_calls``, those sent through ``search_localized`` (R5's
    #: local-language family). Unset when none was, so every capture without
    #: one keeps its bytes.
    search_localized_calls: int | None = Field(
        default=None, ge=0, exclude_if=lambda value: value is None
    )
    model_input_tokens: int | None = Field(default=None, ge=0)
    jev_input_tokens: int | None = Field(default=None, ge=0)
    latency_seconds: float | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    human_review_required: bool | None = None
    #: D7: the documents stage, on its own clock after the decision stage.
    document_reads: int | None = Field(default=None, ge=0)
    document_seconds: float | None = Field(default=None, ge=0)
    document_stop: str | None = None
    #: Seconds on the case clock before the first search query was sent; unset
    #: when no query was sent (structural analysis 2026-10-18, section 4).
    t_first_query: float | None = Field(default=None, ge=0)
    #: Per discovery stage, seconds and page reads, copied from the discovery
    #: trace when the trace records them; unset otherwise, never estimated.
    stage_seconds: dict[str, float] | None = None
    stage_reads: dict[str, int] | None = None
    #: G-07, the gold-knockout arm only: how many gold programme URLs the
    #: harness made unreachable (0: the case has no programme label, a no-op)
    #: and how many reads it answered with a synthetic 404. Not serialised off
    #: the arm, so every other capture keeps its bytes.
    knockout_gold_urls: int | None = Field(
        default=None, ge=0, exclude_if=lambda value: value is None
    )
    knockout_refused: int | None = Field(default=None, ge=0, exclude_if=lambda value: value is None)
    #: Recorded-search replay only (``--search-provider recorded``): requests the
    #: store answered, and requests it had no answer for (answered with nothing,
    #: never sent anywhere). A rule that changes the queries shows up here. Not
    #: serialised off the replay, so every other capture keeps its bytes.
    recorded_search_hits: int | None = Field(
        default=None, ge=0, exclude_if=lambda value: value is None
    )
    recorded_search_misses: int | None = Field(
        default=None, ge=0, exclude_if=lambda value: value is None
    )


class PageOutcome(Strict):
    """Why one page produced what it produced, in the runner's own vocabulary.

    The categories are the frozen acceptance vocabulary — fetch-failed,
    unreadable, classifier-rejected, no-pattern-match, fetched-ok — and the
    point of recording them in the capture is that a case filing zero claims
    can otherwise say nothing about which of the five happened to it.
    """

    category: str
    url: str
    page_type: str = ""
    detail: str = ""
    characters: int | None = Field(default=None, ge=0)


class SiteIdentity(Strict):
    """v3-M3: what production's site-identity gate said about one case.

    Recorded only on the ``--through-identity-gate`` arm, where the case's seed
    row goes through ``CatalogueDiscoveryAdapter._identify_site`` instead of
    being handed a verified homepage (ticket 05 Q3).
    """

    #: The gate returned an entry; until it does (or if the case is killed
    #: first) this stays false.
    established: bool = False
    #: The homepage the gate established identity on, as it returned it.
    homepage: str | None = None
    #: R6 (``--site-identity-v2``): the identity branch that fired -
    #: ``official_site``, ``native_name``, ``english_alternate`` or
    #: ``title_name``. None with the rule off or when nothing was established.
    proof: str | None = None


class Observation(Strict):
    case_id: str
    programme_urls: list[HttpUrl] = Field(default_factory=list)
    ranked_urls: list[HttpUrl] | None = None
    predictions: list[Prediction] = Field(default_factory=list)
    telemetry: Telemetry = Field(default_factory=Telemetry)
    #: Defaulted, so every capture written before this field existed - the
    #: certified one included - still validates byte-for-byte unchanged.
    page_outcomes: list[PageOutcome] = Field(default_factory=list)
    #: WF-17: declared ``hreflang`` twins of each returned programme page, keyed
    #: by that page's URL as in ``programme_urls``. The scorer counts a twin of
    #: the gold page as a hit. Defaulted: older captures carry none.
    programme_url_aliases: dict[str, list[str]] = Field(default_factory=dict)
    #: v3-M2 (ticket 16 Q6): pages discovery read and refused only as a related
    #: programme (``related_programmes`` on the trace). Never returned, so never
    #: a hit or a wrong page; a case with nothing better scores ``related``.
    related_programme_urls: list[str] = Field(default_factory=list)
    #: v3-M2 (ticket 03 Q2): the ``<html lang>`` of a returned programme page as
    #: read, keyed by its URL. Only this confirms a ``?lang=`` variant; a page
    #: with no recorded language keeps ``?lang=`` as part of its identity.
    programme_page_languages: dict[str, str] = Field(default_factory=dict)
    #: v3-M3: unset unless the case ran through the identity gate.
    site_identity: SiteIdentity | None = None
    error: str | None = None


class Capture(Strict):
    schema_version: Literal["1"] = "1"
    pipeline_sha: str
    captured_at: str
    mode: Literal["live", "synthetic", "replay"]
    config: dict[str, JsonValue]
    observations: list[Observation]

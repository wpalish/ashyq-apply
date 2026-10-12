"""Closed personal case actions and supplied read projections, without I/O authority.

Server ownership, source access and persistence are explicit caller responsibilities.
These declarations never certify compliance, receipt by a university or admission.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict
from datetime import UTC, date, datetime
from enum import Enum
from typing import Annotated, Literal, Self
from urllib.parse import unquote, urlsplit
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    model_validator,
)

from app.domain.claim_scope import ClaimScope, RequestedScope
from app.schemas.claim import UnresolvedQuestion
from app.schemas.learning_schedule import LearningTaskRef
from app.schemas.preparation_graph import ChecklistLocation
from app.schemas.result import DocumentItem


def finite_wire(value: object, depth: int = 0) -> object:
    """Reject raw nonfinite/unknown values before any JSON normalization."""
    if depth > 64:
        raise ValueError("Case action values exceed the supported structure")
    if isinstance(value, BaseModel):
        return finite_wire(value.model_dump(mode="python"), depth + 1)
    if isinstance(value, Enum):
        return finite_wire(value.value, depth + 1)
    if isinstance(value, ClaimScope | RequestedScope):
        return finite_wire(asdict(value), depth + 1)
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("Case action values must be finite")
        return value
    if type(value) in {date, datetime} and isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        if any(type(key) is not str for key in value):
            raise ValueError("Case action object keys must be strings")
        return {key: finite_wire(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [finite_wire(item, depth + 1) for item in value]
    raise ValueError("Case action values must have a finite JSON representation")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        finite_wire(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def reference_digest(version: str, value: object) -> str:
    return hashlib.sha256(
        canonical_bytes({"schema_version": version, "value": value})
    ).hexdigest()


def _exact(value: object) -> object:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError("Use an exact identifier")
    return value


def _uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    if type(value) is str and re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        value,
    ):
        return UUID(value)
    raise ValueError("Use a canonical hyphenated UUID")


def _date(value: object) -> date:
    if type(value) is date:
        return value
    if type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return date.fromisoformat(value)
    raise ValueError("Use an exact local calendar date")


def _utc(value: object) -> datetime:
    if type(value) is str:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T.+(?:Z|\+00:00)", value):
            raise ValueError("Use an accepted UTC timestamp")
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if type(value) is not datetime:
        raise ValueError("Use an accepted UTC timestamp")
    offset = value.utcoffset()
    if offset is None or offset.total_seconds():
        raise ValueError("Use an accepted UTC timestamp")
    return value.astimezone(UTC)


def _zone(value: object) -> object:
    if type(value) is not str:
        raise ValueError("Use an IANA timezone")
    try:
        ZoneInfo(value)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError("Use an IANA timezone") from exc
    return value


def _confirmed(value: object) -> object:
    if value is not True:
        raise ValueError("Explicit confirmation is required")
    return value


ExactId = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=32),
    BeforeValidator(_exact),
]
ReferenceId = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=200),
    BeforeValidator(_exact),
]
Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
Label = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=200)]
Note = Annotated[str, StringConstraints(strict=True, max_length=2000)]
WriteUuid = Annotated[UUID, BeforeValidator(_uuid)]
LocalDate = Annotated[date, BeforeValidator(_date)]
UtcTimestamp = Annotated[datetime, BeforeValidator(_utc)]
IanaZone = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=80),
    BeforeValidator(_zone),
]
Confirmed = Annotated[Literal[True], BeforeValidator(_confirmed)]
Revision = Annotated[int, Field(strict=True, ge=1, le=2147483647)]
ExpectedRevision = Annotated[int, Field(strict=True, ge=0, le=2147483646)]
CommandKind = Literal[
    "create_application",
    "create_personal_task",
    "bind_source_task",
    "rebind_source_task",
    "set_document_self_report",
    "set_personal_details",
    "set_planning_status",
    "declare_submission",
    "declare_withdrawal",
    "correct_declaration",
    "import_legacy_marks",
    "select_active_preparation",
]
ReportState = Literal[
    "not_started",
    "in_progress",
    "prepared_reported",
    "sent_reported",
    "received_reported",
    "not_needed_reported",
]
ApplicationStatus = Literal[
    "planning", "preparing", "submitted_declared", "withdrawn_declared"
]
ResponsibleActor = Literal["applicant", "school", "recommender", "third_party"]


class Base(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        allow_inf_nan=False,
        validate_default=True,
        frozen=True,
        revalidate_instances="always",
    )

    @model_validator(mode="before")
    @classmethod
    def _finite_original(cls, value: object) -> object:
        finite_wire(value)
        return (
            value.model_dump(mode="python") if isinstance(value, BaseModel) else value
        )


class RawDocumentItem(DocumentItem):
    """Native fields/defaults, with exact recorded strings for reference hashing."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        allow_inf_nan=False,
        str_strip_whitespace=False,
        revalidate_instances="always",
    )


class RawDocumentChecklist(BaseModel):
    """Exact native checklist wire fields, with raw item strings retained."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        allow_inf_nan=False,
        str_strip_whitespace=False,
        revalidate_instances="always",
    )
    result_id: str
    university: str
    program: str
    admission_documents: list[RawDocumentItem] = Field(default_factory=list)
    scholarship_documents: list[RawDocumentItem] = Field(default_factory=list)
    applicant_actions: list[RawDocumentItem] = Field(default_factory=list)
    school_actions: list[RawDocumentItem] = Field(default_factory=list)
    recommender_actions: list[RawDocumentItem] = Field(default_factory=list)
    certification_actions: list[RawDocumentItem] = Field(default_factory=list)
    ordered_steps: list[str] = Field(default_factory=list)
    unresolved: list[UnresolvedQuestion] = Field(default_factory=list)
    generated_at: datetime | None = None
    completeness: Literal["official", "partial", "unavailable"] = "partial"


class EventRefV1(Base):
    event_id: ExactId
    revision: Revision
    kind: CommandKind


class ActorRefV1(Base):
    schema_version: Literal["g3-actor-reference-v1"] = "g3-actor-reference-v1"
    actor_kind: Literal["authenticated_principal", "local_development"]
    actor_ref_digest: Digest


class KnownTextV1(Base):
    state: Literal["applicant_entered"] = "applicant_entered"
    value: Label


class UnknownTextV1(Base):
    state: Literal["unknown"] = "unknown"


type EnteredOrUnknownText = Annotated[
    KnownTextV1 | UnknownTextV1, Field(discriminator="state")
]


class ApplicationTargetV1(Base):
    result_id: ExactId
    purpose: Literal["admission", "scholarship"]
    award_id: ReferenceId | None
    intake: EnteredOrUnknownText
    route: EnteredOrUnknownText
    confirmed_entered_context: Confirmed

    @model_validator(mode="after")
    def _award(self) -> Self:
        if (self.purpose == "scholarship") != (self.award_id is not None):
            raise ValueError(
                "Only an exact scholarship target carries an award reference"
            )
        return self


class EnteredDueDateV1(Base):
    origin: Literal["applicant_entered"] = "applicant_entered"
    local_date: LocalDate
    timezone: IanaZone | None
    official_deadline: Literal[False] = False


class DeclaredMomentV1(Base):
    local_date: LocalDate
    local_time: (
        Annotated[
            str,
            StringConstraints(
                strict=True,
                pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?$",
            ),
        ]
        | None
    )
    timezone: IanaZone | None
    origin: Literal["applicant_entered"] = "applicant_entered"


class PersonalDetailsV1(Base):
    due: EnteredDueDateV1 | None
    notes: Note = ""


class PersonalTaskInputV1(Base):
    label: Label
    responsible_actor: ResponsibleActor
    details: PersonalDetailsV1
    depends_on_task_ids: list[ExactId] = Field(default_factory=list, max_length=400)

    @model_validator(mode="after")
    def _dependencies(self) -> Self:
        unique(self.depends_on_task_ids)
        return self


class RawOccurrenceRefV1(Base):
    result_id: ExactId
    location: ChecklistLocation
    index: int = Field(strict=True, ge=0)
    item_digest: Digest
    item_semantics_digest: Digest
    proof_reference_digest: Digest


class G1DocumentRefV1(Base):
    action_id: ReferenceId
    source_fingerprint: Digest
    result_snapshot_digest: Digest
    authoritative_evidence_digest: Digest
    resolved_claim_ids: list[ExactId]

    @model_validator(mode="after")
    def _claims(self) -> Self:
        unique(self.resolved_claim_ids)
        return self


class BindingSelectionV1(Base):
    result_id: ExactId
    purpose: Literal["admission", "scholarship", "both"]
    award_id: ReferenceId | None
    award_relation: Literal["unknown"] = "unknown"
    checklist_digest: Digest
    procedure_digest: Digest
    occurrences: list[RawOccurrenceRefV1] = Field(min_length=1, max_length=6)
    original_claim_ids: list[ReferenceId]
    g1_document: G1DocumentRefV1 | None
    g1_relation: Literal[
        "exact_projection", "ambiguous_occurrence", "document_predicate_not_projected"
    ]

    @model_validator(mode="after")
    def _occurrences(self) -> Self:
        locations = [item.location for item in self.occurrences]
        unique(locations)
        unique(self.original_claim_ids)
        if any(item.result_id != self.result_id for item in self.occurrences):
            raise ValueError("Binding occurrences retain their exact result")
        if (self.g1_document is not None) != (self.g1_relation == "exact_projection"):
            raise ValueError("Only an exact actual projection supplies a G1 reference")
        if self.purpose == "admission" and self.award_id is not None:
            raise ValueError("Admission binding cannot borrow an award")
        return self


class ChecklistBindingReceiptV1(BindingSelectionV1):
    profile_id: ExactId
    accepted_at: UtcTimestamp
    binding_digest: Digest

    @model_validator(mode="after")
    def _digest(self) -> Self:
        if self.binding_digest != binding_digest(self):
            raise ValueError("Binding reference digest disagrees")
        return self


class SelfReportInputV1(Base):
    state: ReportState
    entered_at: DeclaredMomentV1 | None
    confirmed_personal_report: Confirmed


class DocumentSelfReportV1(Base):
    state: ReportState
    entered_at: DeclaredMomentV1 | None
    accepted_at: UtcTimestamp | None
    actor: ActorRefV1 | None
    event_ref: EventRefV1 | None
    binding_digest_at_report: Digest | None
    origin: Literal["unreported", "applicant_report", "explicit_browser_mark_import"]
    official_verification: Literal["not_performed"] = "not_performed"

    @model_validator(mode="after")
    def _reported(self) -> Self:
        if self.origin == "unreported":
            if self.state != "not_started" or any(
                value is not None
                for value in (
                    self.entered_at,
                    self.accepted_at,
                    self.actor,
                    self.event_ref,
                    self.binding_digest_at_report,
                )
            ):
                raise ValueError("An unreported task has no invented report")
        elif self.event_ref is None or self.actor is None or self.accepted_at is None:
            raise ValueError(
                "A declared report needs its original actor and accepted event"
            )
        elif self.origin == "explicit_browser_mark_import" and (
            self.state != "prepared_reported"
            or self.event_ref.kind != "import_legacy_marks"
        ):
            raise ValueError("Browser import creates only a prepared self-report")
        elif (
            self.origin == "applicant_report"
            and self.event_ref.kind != "set_document_self_report"
        ):
            raise ValueError("A personal report needs its own report event")
        return self


class SubmissionInputV1(Base):
    entered_at: DeclaredMomentV1
    channel: Label
    reference: Note = ""
    document_task_ids: list[ExactId] = Field(default_factory=list, max_length=400)
    confirmed_applicant_declaration: Confirmed

    @model_validator(mode="after")
    def _references(self) -> Self:
        unique(self.document_task_ids)
        return self


class DeclaredSubmissionV1(Base):
    kind: Literal["applicant_declared_submission"] = "applicant_declared_submission"
    application_id: ExactId
    event_ref: EventRefV1
    entered: SubmissionInputV1
    accepted_at: UtcTimestamp
    actor: ActorRefV1
    receipt_origin: Literal["applicant"] = "applicant"
    official_verification: Literal["not_performed"] = "not_performed"


class WithdrawalInputV1(Base):
    entered_at: DeclaredMomentV1 | None
    notes: Note = ""
    confirmed_applicant_declaration: Confirmed


class DeclaredWithdrawalV1(Base):
    kind: Literal["applicant_declared_withdrawal"] = "applicant_declared_withdrawal"
    application_id: ExactId
    event_ref: EventRefV1
    entered: WithdrawalInputV1
    accepted_at: UtcTimestamp
    actor: ActorRefV1
    receipt_origin: Literal["applicant"] = "applicant"
    official_verification: Literal["not_performed"] = "not_performed"


class G2HeadV1(Base):
    origin: Literal["g2"] = "g2"
    profile_id: ExactId
    native_schema_version: Literal["shared-route-v1"] = "shared-route-v1"
    revision: Revision
    client_write_uuid: WriteUuid
    snapshot_digest: Digest
    allocation_digest: Digest
    accepted_at: UtcTimestamp


class LegacyV2HeadV1(Base):
    origin: Literal["legacy_v2"] = "legacy_v2"
    profile_id: ExactId
    native_schema_version: Literal["schedule-v2"] = "schedule-v2"
    revision: Revision
    persisted_sidecar_digest: Digest
    draft_fingerprint: Digest
    legacy_fingerprint: Digest
    observed_structural_fingerprint: Digest


class LegacyV1HeadV1(Base):
    origin: Literal["legacy_v1"] = "legacy_v1"
    profile_id: ExactId
    native_schema_version: Literal["schedule-v1"] = "schedule-v1"
    revision: Revision
    saved_settings_digest: Digest
    settings_fingerprint: Digest


type NativeHeadV1 = Annotated[
    G2HeadV1 | LegacyV2HeadV1 | LegacyV1HeadV1, Field(discriminator="origin")
]


class ActivePreparationSelectionV1(Base):
    origin: Literal["g2", "legacy_v2", "legacy_v1"]
    policy: Literal["follow_current_accepted"] = "follow_current_accepted"
    observed_head: NativeHeadV1
    event_ref: EventRefV1

    @model_validator(mode="after")
    def _origin(self) -> Self:
        if (
            self.origin != self.observed_head.origin
            or self.event_ref.kind != "select_active_preparation"
        ):
            raise ValueError("Selection keeps its exact native observation and event")
        return self


class CommandBase(Base):
    schema_version: Literal["admissions-actions-v1"] = "admissions-actions-v1"
    client_write_uuid: WriteUuid
    expected_revision: ExpectedRevision


class CreateApplicationV1(CommandBase):
    kind: Literal["create_application"] = "create_application"
    target: ApplicationTargetV1
    label: Label
    details: PersonalDetailsV1


class CreatePersonalTaskV1(CommandBase):
    kind: Literal["create_personal_task"] = "create_personal_task"
    application_id: ExactId | None
    personal: PersonalTaskInputV1


class BindSourceTaskV1(CommandBase):
    kind: Literal["bind_source_task"] = "bind_source_task"
    application_id: ExactId | None
    source: BindingSelectionV1
    source_preview_digest: Digest
    personal: PersonalTaskInputV1


class RebindSourceTaskV1(CommandBase):
    kind: Literal["rebind_source_task"] = "rebind_source_task"
    task_id: ExactId
    expected_binding_digest: Digest | None
    source: BindingSelectionV1
    source_preview_digest: Digest


class SetDocumentSelfReportV1(CommandBase):
    kind: Literal["set_document_self_report"] = "set_document_self_report"
    task_id: ExactId
    report: SelfReportInputV1


class ApplicationRefV1(Base):
    kind: Literal["application"] = "application"
    id: ExactId


class DocumentTaskRefV1(Base):
    kind: Literal["document_task"] = "document_task"
    id: ExactId


type PersonalActionRef = Annotated[
    ApplicationRefV1 | DocumentTaskRefV1, Field(discriminator="kind")
]


class SetPersonalDetailsV1(CommandBase):
    kind: Literal["set_personal_details"] = "set_personal_details"
    target: PersonalActionRef
    details: PersonalDetailsV1


class SetPlanningStatusV1(CommandBase):
    kind: Literal["set_planning_status"] = "set_planning_status"
    application_id: ExactId
    status: Literal["planning", "preparing"]


class DeclareSubmissionV1(CommandBase):
    kind: Literal["declare_submission"] = "declare_submission"
    application_id: ExactId
    submission: SubmissionInputV1


class DeclareWithdrawalV1(CommandBase):
    kind: Literal["declare_withdrawal"] = "declare_withdrawal"
    application_id: ExactId
    withdrawal: WithdrawalInputV1


class CorrectedSubmissionV1(Base):
    kind: Literal["submission"] = "submission"
    submission: SubmissionInputV1


class CorrectedWithdrawalV1(Base):
    kind: Literal["withdrawal"] = "withdrawal"
    withdrawal: WithdrawalInputV1


class CorrectedPlanningV1(Base):
    kind: Literal["planning"] = "planning"
    status: Literal["planning", "preparing"]


type CorrectionValue = Annotated[
    CorrectedSubmissionV1 | CorrectedWithdrawalV1 | CorrectedPlanningV1,
    Field(discriminator="kind"),
]


class CorrectDeclarationV1(CommandBase):
    kind: Literal["correct_declaration"] = "correct_declaration"
    application_id: ExactId
    prior_declaration: EventRefV1
    replacement: CorrectionValue
    confirmed_correction: Confirmed

    @model_validator(mode="after")
    def _declaration(self) -> Self:
        if self.prior_declaration.kind not in {
            "declare_submission",
            "declare_withdrawal",
            "correct_declaration",
        }:
            raise ValueError("A correction references an accepted own declaration")
        if self.prior_declaration.revision > self.expected_revision:
            raise ValueError("A correction cannot reference a future declaration")
        return self


class LegacyImportMappingV1(Base):
    task_id: ExactId
    legacy_key_digest: Digest
    expected_binding_digest: Digest | None
    source_preview_digest: Digest | None
    legacy_value: Confirmed
    confirmed_prepared_report: Confirmed
    source_version: Literal["unknown"] = "unknown"
    original_reported_at: Literal[None] = None


class ImportLegacyMarksV1(CommandBase):
    kind: Literal["import_legacy_marks"] = "import_legacy_marks"
    legacy_snapshot_digest: Digest
    mappings: list[LegacyImportMappingV1] = Field(min_length=1, max_length=50)
    entered_at: DeclaredMomentV1 | None

    @model_validator(mode="after")
    def _tasks(self) -> Self:
        unique([item.task_id for item in self.mappings])
        unique([item.legacy_key_digest for item in self.mappings])
        return self


class SelectActivePreparationV1(CommandBase):
    kind: Literal["select_active_preparation"] = "select_active_preparation"
    origin: Literal["g2", "legacy_v2", "legacy_v1"]
    policy: Literal["follow_current_accepted"] = "follow_current_accepted"
    observed_head: NativeHeadV1

    @model_validator(mode="after")
    def _origin(self) -> Self:
        if self.origin != self.observed_head.origin:
            raise ValueError("The selected origin needs its exact own observed head")
        return self


type ActionRequestV1 = Annotated[
    CreateApplicationV1
    | CreatePersonalTaskV1
    | BindSourceTaskV1
    | RebindSourceTaskV1
    | SetDocumentSelfReportV1
    | SetPersonalDetailsV1
    | SetPlanningStatusV1
    | DeclareSubmissionV1
    | DeclareWithdrawalV1
    | CorrectDeclarationV1
    | ImportLegacyMarksV1
    | SelectActivePreparationV1,
    Field(discriminator="kind"),
]


class ApplicationRecordV1(Base):
    id: ExactId
    profile_id: ExactId
    target: ApplicationTargetV1
    label: Label
    details: PersonalDetailsV1
    status: ApplicationStatus
    created_ref: EventRefV1
    latest_ref: EventRefV1
    status_ref: EventRefV1 | None

    @model_validator(mode="after")
    def _roles(self) -> Self:
        role(self.created_ref, {"create_application"})
        role(
            self.latest_ref,
            {
                "create_application",
                "set_personal_details",
                "set_planning_status",
                "declare_submission",
                "declare_withdrawal",
                "correct_declaration",
            },
        )
        if self.status_ref is not None:
            role(
                self.status_ref,
                {
                    "set_planning_status",
                    "declare_submission",
                    "declare_withdrawal",
                    "correct_declaration",
                },
            )
        if self.status in {"submitted_declared", "withdrawn_declared"}:
            if self.status_ref is None:
                raise ValueError("Terminal state needs its own declared event")
            role(
                self.status_ref,
                {"declare_submission", "correct_declaration"}
                if self.status == "submitted_declared"
                else {"declare_withdrawal", "correct_declaration"},
            )
        if self.latest_ref.revision < self.created_ref.revision or (
            self.status_ref is not None
            and self.status_ref.revision > self.latest_ref.revision
        ):
            raise ValueError("Application event order disagrees")
        return self


class DocumentTaskV1(Base):
    id: ExactId
    profile_id: ExactId
    application_id: ExactId | None
    origin: Literal["applicant_entered", "source_reference"]
    personal: PersonalTaskInputV1
    binding: ChecklistBindingReceiptV1 | None
    report: DocumentSelfReportV1
    created_ref: EventRefV1
    latest_ref: EventRefV1
    binding_ref: EventRefV1 | None

    @model_validator(mode="after")
    def _binding(self) -> Self:
        role(self.created_ref, {"create_personal_task", "bind_source_task"})
        role(
            self.latest_ref,
            {
                "create_personal_task",
                "bind_source_task",
                "rebind_source_task",
                "set_document_self_report",
                "set_personal_details",
                "import_legacy_marks",
            },
        )
        if self.binding is None:
            if self.binding_ref is not None or self.origin != "applicant_entered":
                raise ValueError("An unbound task cannot claim a source reference")
        else:
            if self.binding.profile_id != self.profile_id or self.binding_ref is None:
                raise ValueError("Binding belongs to the exact task profile and event")
            role(self.binding_ref, {"bind_source_task", "rebind_source_task"})
            if self.origin != "source_reference":
                raise ValueError("A bound task retains reference origin")
        if (
            self.binding is not None
            and self.report.origin != "unreported"
            and self.binding_ref is not None
            and self.report.event_ref is not None
            and self.report.event_ref.revision >= self.binding_ref.revision
            and self.report.binding_digest_at_report != self.binding.binding_digest
        ):
            raise ValueError(
                "A later report must retain its then-current accepted binding"
            )
        if self.id in self.personal.depends_on_task_ids:
            raise ValueError("A task cannot depend on itself")
        refs = [self.created_ref, self.binding_ref, self.report.event_ref]
        if any(
            ref is not None and ref.revision > self.latest_ref.revision for ref in refs
        ):
            raise ValueError("Task event order disagrees")
        return self


class CaseActionsStateV1(Base):
    schema_version: Literal["admissions-actions-v1"] = "admissions-actions-v1"
    profile_id: ExactId
    revision: Revision
    head_event_id: ExactId
    applications: list[ApplicationRecordV1] = Field(max_length=20)
    document_tasks: list[DocumentTaskV1] = Field(max_length=400)
    active_preparation: ActivePreparationSelectionV1 | None

    @model_validator(mode="after")
    def _aggregate(self) -> Self:
        unique([item.id for item in self.applications])
        unique([item.id for item in self.document_tasks])
        applications = {item.id: item for item in self.applications}
        for application in self.applications:
            if application.profile_id != self.profile_id:
                raise ValueError("Applications belong to their enclosing profile")
        for task in self.document_tasks:
            if task.profile_id != self.profile_id:
                raise ValueError("Tasks belong to their enclosing profile")
            if task.application_id is not None:
                own_application = applications.get(task.application_id)
                if own_application is None:
                    raise ValueError("A task references an own current application")
                if task.binding is not None and (
                    task.binding.result_id != own_application.target.result_id
                    or task.binding.award_id != own_application.target.award_id
                    or task.binding.purpose
                    not in {own_application.target.purpose, "both"}
                ):
                    raise ValueError("A source task cannot retarget its application")
        if (
            self.active_preparation is not None
            and self.active_preparation.observed_head.profile_id != self.profile_id
        ):
            raise ValueError("A selection references its own profile")
        refs = state_references(self)
        if not any(
            ref.revision == self.revision and ref.event_id == self.head_event_id
            for ref, _, _ in refs
        ):
            raise ValueError("A current head must actually mutate its own state")
        if any(ref.revision > self.revision for ref, _, _ in refs):
            raise ValueError("State cannot reference a future event")
        if any(
            ref.revision == self.revision and ref.event_id != self.head_event_id
            for ref, _, _ in refs
        ):
            raise ValueError("Same-revision references must point to the exact head")
        if len(source_target_ids(self)) > 20:
            raise ValueError("The current target union exceeds its bound")
        return self


class EventAffectedRefsV1(Base):
    application_ids: list[ExactId] = Field(max_length=20)
    document_task_ids: list[ExactId] = Field(max_length=400)
    active_selector_changed: bool

    @model_validator(mode="after")
    def _unique(self) -> Self:
        unique(self.application_ids)
        unique(self.document_task_ids)
        return self


class AppliedDeltaV1(Base):
    applications: list[ApplicationRecordV1] = Field(max_length=20)
    document_tasks: list[DocumentTaskV1] = Field(max_length=50)
    active_preparation: ActivePreparationSelectionV1 | None
    corrected_declaration: EventRefV1 | None = None
    previous_binding_digest: Digest | None = None
    declaration: DeclaredSubmissionV1 | DeclaredWithdrawalV1 | None = None


class ActionWriteReceiptV1(Base):
    schema_version: Literal["admissions-actions-v1"] = "admissions-actions-v1"
    event_id: ExactId
    profile_id: ExactId
    kind: CommandKind
    revision: Revision
    expected_revision: ExpectedRevision
    client_write_uuid: WriteUuid
    request: ActionRequestV1
    canonical_request_digest: Digest
    accepted_at: UtcTimestamp
    actor: ActorRefV1
    predecessor_event_id: ExactId | None
    before_state_digest: Digest | None
    after_state_digest: Digest
    applied_delta: AppliedDeltaV1
    affected_refs: EventAffectedRefsV1
    receipt_digest: Digest

    @model_validator(mode="after")
    def _binding(self) -> Self:
        if (
            self.kind != self.request.kind
            or self.client_write_uuid != self.request.client_write_uuid
        ):
            raise ValueError("Receipt retains the exact original intent")
        if (
            self.expected_revision != self.request.expected_revision
            or self.revision != self.expected_revision + 1
        ):
            raise ValueError("A receipt advances exactly one case revision")
        if (self.expected_revision == 0) != (
            self.predecessor_event_id is None and self.before_state_digest is None
        ):
            raise ValueError("The first receipt has no fabricated predecessor")
        if self.expected_revision > 0 and (
            self.predecessor_event_id is None or self.before_state_digest is None
        ):
            raise ValueError("Later receipts bind their exact predecessor")
        if self.canonical_request_digest != request_digest(
            self.profile_id, self.request
        ):
            raise ValueError("Receipt request identity disagrees")
        validate_receipt_delta(self)
        if self.receipt_digest != receipt_digest(self):
            raise ValueError("Receipt self-hash disagrees")
        return self


class EventMetadataV1(Base):
    profile_id: ExactId
    event_id: ExactId
    revision: Revision
    kind: CommandKind
    accepted_at: UtcTimestamp
    affected_refs: EventAffectedRefsV1


SourceReason = Literal[
    "stale",
    "scope_unknown",
    "scope_mismatch",
    "conflict",
    "ambiguous_occurrence",
    "proof_changed_item_same",
    "item_changed",
    "procedure_order_changed",
    "award_relation_unknown",
    "document_predicate_not_projected",
    "proof_unresolved",
]


class SourceReadStatusV1(Base):
    result_id: ExactId
    target_state: Literal["eligible", "decision_changed", "result_unavailable"]
    source_state: Literal[
        "not_evaluated",
        "research_locked",
        "current_reference",
        "source_changed",
        "evidence_unknown",
    ]
    observed_at: UtcTimestamp
    current_digest: Digest | None
    reasons: list[SourceReason]

    @model_validator(mode="after")
    def _privacy(self) -> Self:
        unique(self.reasons)
        if (
            self.source_state in {"research_locked", "not_evaluated"}
            or self.target_state != "eligible"
        ):
            if self.current_digest is not None or self.reasons:
                raise ValueError(
                    "Unavailable or locked slices expose no new proof metadata"
                )
            if self.target_state != "eligible" and self.source_state != "not_evaluated":
                raise ValueError("An unavailable target is not a source observation")
        if self.source_state == "current_reference" and self.current_digest is None:
            raise ValueError("Current reference requires an actually observed identity")
        return self


class ActionLinkReadV1(Base):
    role: Literal[
        "programme_information",
        "requirements_information",
        "applicant_entered_external",
    ]
    provenance: Literal["current_source", "applicant_entered", "demo", "unknown"]
    destination_verification: Literal["not_performed"] = "not_performed"
    state: Literal["actionable_unverified", "blocked", "demo_text", "not_available"]
    href: Annotated[str, StringConstraints(strict=True, max_length=2000)] | None
    reason: Literal[
        "informational_unverified",
        "link_form_unavailable",
        "demo_reference",
        "not_available",
    ]

    @model_validator(mode="after")
    def _href(self) -> Self:
        if (self.state == "actionable_unverified") != (self.href is not None):
            raise ValueError("Only an unverified informational action carries an href")
        expected = {
            "actionable_unverified": "informational_unverified",
            "blocked": "link_form_unavailable",
            "demo_text": "demo_reference",
            "not_available": "not_available",
        }
        if self.href is not None and not safe_link_literal(self.href):
            raise ValueError("Action href must satisfy the exact lexical rule")
        if self.state == "actionable_unverified" and self.provenance not in {
            "current_source",
            "applicant_entered",
        }:
            raise ValueError("Unknown/demo references have no action href")
        if self.reason != expected[self.state]:
            raise ValueError("Action link uses its fixed public reason")
        return self


def _learning_ref(value: object) -> object:
    if value is None:
        return value
    raw = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
    finite_wire(raw)
    if not isinstance(raw, dict):
        raise ValueError("Use an exact native learning reference")
    ref: LearningTaskRef = TypeAdapter(LearningTaskRef).validate_json(
        canonical_bytes(raw), strict=True
    )
    if (
        ref.kind == "lesson"
        and ref.id != f"lesson:{ref.lesson_id}:{ref.content_version}"
    ):
        raise ValueError("Lesson identity is exact, never inferred")
    if ref.kind == "attempt_review" and ref.id != f"attempt:{ref.attempt_id}":
        raise ValueError("Review identity is exact, never inferred")
    if finite_wire(ref) != finite_wire(raw):
        raise ValueError("Reference validation cannot repair identity")
    return ref


type ExactLearningRef = Annotated[LearningTaskRef, BeforeValidator(_learning_ref)]


class StudyActionReadV1(Base):
    id: ReferenceId
    local_date: LocalDate
    timezone: IanaZone
    ref: ExactLearningRef | None
    planned_minutes: int = Field(strict=True, ge=0, le=180)
    availability: Literal["available", "unavailable", "unsupported"]
    completion: Literal["not_projected", "self_reported_complete"]


class ActivePreparationReadV1(Base):
    origin: Literal["none", "g2", "legacy_v2", "legacy_v1", "unknown"]
    selection_source: Literal[
        "accepted_g3_event", "derived_backward_default", "unavailable"
    ]
    state: Literal["available", "needs_review", "unavailable", "absent"]
    selection: ActivePreparationSelectionV1 | None
    current_observed_head: NativeHeadV1 | None
    observed_at: UtcTimestamp
    goal_result_ids: list[ExactId] = Field(max_length=20)
    study_actions: list[StudyActionReadV1] = Field(max_length=400)
    allocated_minutes: int | None = Field(default=None, strict=True, ge=0)
    needs_review: bool

    @model_validator(mode="after")
    def _one_plan(self) -> Self:
        unique(self.goal_result_ids)
        unique([item.id for item in self.study_actions])
        if self.selection_source == "accepted_g3_event":
            if self.selection is None or self.origin != self.selection.origin:
                raise ValueError(
                    "A stored selection cannot be replaced by a derived origin"
                )
        elif self.selection is not None:
            raise ValueError("A derived selection has no fabricated accepted event")
        if (
            self.current_observed_head is not None
            and self.current_observed_head.origin != self.origin
        ):
            raise ValueError("Observed head belongs to the selected origin")
        if (
            self.origin == "none"
            and self.selection_source != "derived_backward_default"
        ):
            raise ValueError("No-plan state is derived, never an accepted selector")
        if (
            self.current_observed_head is not None
            and self.selection is not None
            and self.current_observed_head.revision
            < self.selection.observed_head.revision
        ):
            raise ValueError(
                "A selected origin cannot regress its accepted observation"
            )
        if self.origin == "none" and (
            self.state != "absent" or self.current_observed_head is not None
        ):
            raise ValueError("None is only a derived no-plan read state")
        if self.origin == "unknown" and self.state != "unavailable":
            raise ValueError("Unknown presence is not proven absence")
        if self.state in {"absent", "unavailable"}:
            if self.study_actions or self.allocated_minutes is not None:
                raise ValueError("Unavailable workload is unknown, not zero")
        else:
            if (
                self.origin not in {"g2", "legacy_v2", "legacy_v1"}
                or self.current_observed_head is None
                or self.allocated_minutes
                != sum(item.planned_minutes for item in self.study_actions)
            ):
                raise ValueError("One chosen plan supplies its exact minute ledger")
        return self


class PreparationAccessReadV1(Base):
    allowed: bool
    reason: Literal["active", "expired", "not_started", "unavailable", "development"]
    starts_at: UtcTimestamp | None
    ends_at: UtcTimestamp | None
    development_only: bool
    observed_at: UtcTimestamp

    @model_validator(mode="after")
    def _observed_access(self) -> Self:
        if self.development_only:
            if not self.allowed or self.reason != "development":
                raise ValueError(
                    "Development access is an explicit separate observation"
                )
        elif self.reason == "development":
            raise ValueError("Development access requires its explicit origin")
        elif self.allowed:
            if (
                self.reason != "active"
                or self.starts_at is None
                or self.ends_at is None
                or not self.starts_at <= self.observed_at < self.ends_at
            ):
                raise ValueError("Active access is bound to its observed term")
        elif self.reason == "active":
            raise ValueError("Denied access cannot claim an active permission")
        return self


class TodayDateReadV1(Base):
    local_date: LocalDate | None
    timezone: IanaZone | None
    certainty: Literal[
        "applicant_entered",
        "date_only_timezone_unknown",
        "source_date_only",
        "previous_cycle",
        "unknown",
    ]
    comparison_zone: IanaZone
    fallback_display_only: bool
    official_closure: Literal["not_assessed"] = "not_assessed"


class TodayCardV1(Base):
    id: ReferenceId
    reason: Literal[
        "personal_document_action",
        "personal_application_action",
        "accepted_study_action",
    ]
    target: PersonalActionRef | ExactLearningRef | None
    target_result_id: ExactId | None
    date: TodayDateReadV1
    dependency_reasons: list[
        Literal[
            "dependency_missing",
            "dependency_cycle",
            "dependency_not_reported_ready",
            "report_refers_to_previous_binding",
            "not_needed_is_not_a_waiver",
        ]
    ]
    workload_origin: Literal["g2", "legacy_v2", "legacy_v1", "personal_unallocated"]
    planned_minutes: int | None = Field(default=None, strict=True, ge=0, le=180)
    source_state: Literal[
        "applicant_entered",
        "not_evaluated",
        "research_locked",
        "current_reference",
        "source_changed",
        "evidence_unknown",
    ]
    actionable: bool

    @model_validator(mode="after")
    def _minutes(self) -> Self:
        if (self.workload_origin == "personal_unallocated") != (
            self.planned_minutes is None
        ):
            raise ValueError("Personal paperwork has no invented minute allocation")
        return self


class TodayNoticeV1(Base):
    code: Literal[
        "mixed_revision",
        "actions_unavailable",
        "plan_unavailable",
        "plan_needs_review",
        "preparation_locked",
        "source_review",
        "dependency_review",
    ]
    record_id: ReferenceId | None = None


class TodayProjectionV1(Base):
    schema_version: Literal["admissions-today-v1"] = "admissions-today-v1"
    profile_id: ExactId
    as_of: UtcTimestamp
    display_timezone: IanaZone
    action_state: Literal["readable", "absent", "unavailable"]
    action_revision: int | None = Field(strict=True, ge=0, le=2147483647)
    action_digest: Digest | None
    action_observed_at: UtcTimestamp
    active_plan: ActivePreparationReadV1
    preparation_access: PreparationAccessReadV1
    current_source_statuses: list[SourceReadStatusV1] = Field(max_length=40)
    consistency: Literal["component_reads", "mixed_revision"]
    needs_refresh: bool
    notices: list[TodayNoticeV1]
    overdue_personal: list[TodayCardV1]
    today_study: list[TodayCardV1]
    today_personal: list[TodayCardV1]
    future: list[TodayCardV1]
    undated_personal: list[TodayCardV1]
    application_summaries: list[ApplicationRecordV1] = Field(max_length=20)
    workload: Literal["one_selected_plan", "unknown"]
    allocated_study_minutes: int | None = Field(default=None, strict=True, ge=0)
    personal_minutes: Literal["not_estimated"] = "not_estimated"
    readiness: Literal["not_assessed"] = "not_assessed"


def unique(values: list) -> None:
    if len(set(values)) != len(values):
        raise ValueError("Case action references must be unique")


def role(ref: EventRefV1, allowed: set[str]) -> None:
    if ref.kind not in allowed:
        raise ValueError("An event cannot be used for an unrelated role")


def source_target_ids(state: CaseActionsStateV1) -> list[str]:
    values = [item.target.result_id for item in state.applications]
    values.extend(
        item.binding.result_id
        for item in state.document_tasks
        if item.application_id is None and item.binding is not None
    )
    return list(dict.fromkeys(values))


def state_references(
    state: CaseActionsStateV1,
) -> list[
    tuple[EventRefV1, Literal["application", "document_task", "selector"], str | None]
]:
    refs: list[
        tuple[
            EventRefV1, Literal["application", "document_task", "selector"], str | None
        ]
    ] = []
    for item in state.applications:
        for ref in (item.created_ref, item.latest_ref, item.status_ref):
            if ref is not None:
                refs.append((ref, "application", item.id))
    for task in state.document_tasks:
        for ref in (
            task.created_ref,
            task.latest_ref,
            task.report.event_ref,
            task.binding_ref,
        ):
            if ref is not None:
                refs.append((ref, "document_task", task.id))
    if state.active_preparation is not None:
        refs.append((state.active_preparation.event_ref, "selector", None))
    return refs


def request_digest(profile_id: str, request: ActionRequestV1) -> str:
    return hashlib.sha256(
        canonical_bytes(
            {
                "schema_version": "g3-action-request-digest-v1",
                "profile_id": profile_id,
                "request": request,
            }
        )
    ).hexdigest()


def state_digest(state: CaseActionsStateV1) -> str:
    return hashlib.sha256(
        canonical_bytes({"schema_version": "g3-state-digest-v1", "state": state})
    ).hexdigest()


def binding_digest(value: ChecklistBindingReceiptV1) -> str:
    wire = value.model_dump(mode="python")
    wire.pop("binding_digest")
    return reference_digest("g3-checklist-binding-v1", wire)


def receipt_digest(value: ActionWriteReceiptV1) -> str:
    wire = value.model_dump(mode="python")
    wire.pop("receipt_digest")
    return hashlib.sha256(
        canonical_bytes(
            {"schema_version": "g3-action-receipt-digest-v1", "receipt": wire}
        )
    ).hexdigest()


def delta_affected(delta: AppliedDeltaV1) -> EventAffectedRefsV1:
    return EventAffectedRefsV1(
        application_ids=[item.id for item in delta.applications],
        document_task_ids=[item.id for item in delta.document_tasks],
        active_selector_changed=delta.active_preparation is not None,
    )


def validate_receipt_delta(receipt: ActionWriteReceiptV1) -> None:
    delta = receipt.applied_delta
    request = receipt.request
    event = EventRefV1(
        event_id=receipt.event_id, revision=receipt.revision, kind=receipt.kind
    )
    if receipt.affected_refs != delta_affected(delta):
        raise ValueError("Copied affected references must equal the applied mutations")
    applied_records: list[ApplicationRecordV1 | DocumentTaskV1] = [
        *delta.applications,
        *delta.document_tasks,
    ]
    for record in applied_records:
        if record.profile_id != receipt.profile_id or record.latest_ref != event:
            raise ValueError("Applied records belong to this exact own event")
    task_kinds = {
        "create_personal_task",
        "bind_source_task",
        "rebind_source_task",
        "set_document_self_report",
        "import_legacy_marks",
    }
    app_kinds = {
        "create_application",
        "set_planning_status",
        "declare_submission",
        "declare_withdrawal",
        "correct_declaration",
    }
    if request.kind in task_kinds:
        count = len(request.mappings) if isinstance(request, ImportLegacyMarksV1) else 1
        if (
            delta.applications
            or delta.active_preparation is not None
            or len(delta.document_tasks) != count
        ):
            raise ValueError("Task command mutates only its exact bounded tasks")
    elif request.kind in app_kinds:
        if (
            len(delta.applications) != 1
            or delta.document_tasks
            or delta.active_preparation is not None
        ):
            raise ValueError(
                "Application command does not mutate mentioned task references"
            )
    elif isinstance(request, SelectActivePreparationV1):
        if (
            delta.applications
            or delta.document_tasks
            or delta.active_preparation is None
        ):
            raise ValueError("Selection changes only the explicit selector")
        if (
            delta.active_preparation.observed_head != request.observed_head
            or delta.active_preparation.event_ref != event
        ):
            raise ValueError("Selection receipt retains its exact native observation")
    elif isinstance(request, SetPersonalDetailsV1):
        records = (
            delta.applications
            if request.target.kind == "application"
            else delta.document_tasks
        )
        others = (
            delta.document_tasks
            if request.target.kind == "application"
            else delta.applications
        )
        if (
            len(records) != 1
            or others
            or delta.active_preparation is not None
            or records[0].id != request.target.id
        ):
            raise ValueError("Personal details mutate only the named own record")
    if (
        request.kind != "correct_declaration"
        and delta.corrected_declaration is not None
    ):
        raise ValueError("Only a correction carries an original declaration ref")
    if (
        isinstance(request, CorrectDeclarationV1)
        and delta.corrected_declaration != request.prior_declaration
    ):
        raise ValueError("Correction retains its exact original declaration")
    if (
        isinstance(request, RebindSourceTaskV1)
        and delta.previous_binding_digest != request.expected_binding_digest
    ):
        raise ValueError("Rebinding retains the reviewed old binding reference")
    if (
        request.kind != "rebind_source_task"
        and delta.previous_binding_digest is not None
    ):
        raise ValueError("Only rebind carries a replaced binding")
    if (
        isinstance(
            request,
            SetPlanningStatusV1
            | DeclareSubmissionV1
            | DeclareWithdrawalV1
            | CorrectDeclarationV1,
        )
        and delta.applications[0].id != request.application_id
    ):
        raise ValueError("Application delta belongs to the requested record")
    if isinstance(request, CreateApplicationV1) and (
        delta.applications[0].target != request.target
        or delta.applications[0].created_ref != event
        or delta.applications[0].status != "planning"
    ):
        raise ValueError("Creation freezes exactly the entered target")
    if (
        isinstance(request, RebindSourceTaskV1 | SetDocumentSelfReportV1)
        and delta.document_tasks[0].id != request.task_id
    ):
        raise ValueError("Task delta belongs to the requested record")
    if isinstance(request, ImportLegacyMarksV1) and [
        item.id for item in delta.document_tasks
    ] != [item.task_id for item in request.mappings]:
        raise ValueError("Import order and exact task mappings remain unchanged")
    declaration = delta.declaration
    expected_submission = (
        request.submission
        if isinstance(request, DeclareSubmissionV1)
        else request.replacement.submission
        if isinstance(request, CorrectDeclarationV1)
        and isinstance(request.replacement, CorrectedSubmissionV1)
        else None
    )
    expected_withdrawal = (
        request.withdrawal
        if isinstance(request, DeclareWithdrawalV1)
        else request.replacement.withdrawal
        if isinstance(request, CorrectDeclarationV1)
        and isinstance(request.replacement, CorrectedWithdrawalV1)
        else None
    )
    if expected_submission is not None or expected_withdrawal is not None:
        if (
            declaration is None
            or declaration.event_ref != event
            or declaration.accepted_at != receipt.accepted_at
            or declaration.actor != receipt.actor
            or declaration.application_id != delta.applications[0].id
            or delta.applications[0].status_ref != event
        ):
            raise ValueError("A declaration keeps its exact accepted actor and event")
        if expected_submission is not None and (
            not isinstance(declaration, DeclaredSubmissionV1)
            or declaration.entered != expected_submission
            or delta.applications[0].status != "submitted_declared"
        ):
            raise ValueError(
                "Submission is only the exact original applicant declaration"
            )
        if expected_withdrawal is not None and (
            not isinstance(declaration, DeclaredWithdrawalV1)
            or declaration.entered != expected_withdrawal
            or delta.applications[0].status != "withdrawn_declared"
        ):
            raise ValueError(
                "Withdrawal is only the exact original applicant declaration"
            )
    elif declaration is not None:
        raise ValueError("Other commands cannot add a declaration")
    if isinstance(request, CreateApplicationV1) and (
        delta.applications[0].label != request.label
        or delta.applications[0].details != request.details
        or delta.applications[0].status_ref is not None
    ):
        raise ValueError(
            "Application creation retains only its original personal content"
        )
    if isinstance(request, CreatePersonalTaskV1 | BindSourceTaskV1):
        task = delta.document_tasks[0]
        if (
            task.created_ref != event
            or task.application_id != request.application_id
            or task.personal != request.personal
            or task.report.origin != "unreported"
        ):
            raise ValueError("Task creation retains its exact personal content")
    if isinstance(request, CreatePersonalTaskV1):
        task = delta.document_tasks[0]
        if (
            task.binding is not None
            or task.binding_ref is not None
            or task.origin != "applicant_entered"
        ):
            raise ValueError(
                "Personal creation cannot carry an unreviewed source binding"
            )
    if isinstance(request, BindSourceTaskV1 | RebindSourceTaskV1):
        task = delta.document_tasks[0]
        if (
            task.binding is None
            or task.binding_ref != event
            or task.binding.accepted_at != receipt.accepted_at
            or BindingSelectionV1.model_validate(
                task.binding.model_dump(
                    mode="python",
                    exclude={"profile_id", "accepted_at", "binding_digest"},
                )
            )
            != request.source
        ):
            raise ValueError("Binding preserves the exact reviewed reference selection")
    if isinstance(request, SetPersonalDetailsV1):
        actual = (
            delta.applications[0].details
            if request.target.kind == "application"
            else delta.document_tasks[0].personal.details
        )
        if actual != request.details:
            raise ValueError("Details retain their original personal input")
    if isinstance(request, SetPlanningStatusV1) and (
        delta.applications[0].status != request.status
        or delta.applications[0].status_ref != event
    ):
        raise ValueError("Planning status is bound to its own event")
    if (
        isinstance(request, CorrectDeclarationV1)
        and isinstance(request.replacement, CorrectedPlanningV1)
        and (
            delta.applications[0].status != request.replacement.status
            or delta.applications[0].status_ref != event
        )
    ):
        raise ValueError("A planning correction keeps its explicit replacement")
    for task in delta.document_tasks:
        if task.report.event_ref == event and (
            task.report.accepted_at != receipt.accepted_at
            or task.report.actor != receipt.actor
        ):
            raise ValueError("A current report keeps this accepted actor and time")
        if isinstance(request, SetDocumentSelfReportV1) and (
            task.report.origin != "applicant_report"
            or task.report.event_ref != event
            or task.report.state != request.report.state
            or task.report.entered_at != request.report.entered_at
            or task.report.binding_digest_at_report
            != (task.binding.binding_digest if task.binding is not None else None)
        ):
            raise ValueError(
                "A self-report is exact personal input, not official fulfillment"
            )
        if isinstance(request, ImportLegacyMarksV1) and (
            task.report.origin != "explicit_browser_mark_import"
            or task.report.event_ref != event
            or task.report.entered_at != request.entered_at
            or task.report.binding_digest_at_report
            != (task.binding.binding_digest if task.binding is not None else None)
        ):
            raise ValueError("Import retains exact declared preparation and binding")


PRIVATE_SEGMENTS = frozenset(
    {
        "login",
        "signin",
        "sign-in",
        "auth",
        "oauth",
        "callback",
        "logout",
        "session",
        "password",
        "reset",
        "reset-password",
        "verify",
        "verification",
        "invite",
        "invitation",
        "magic",
        "magic-link",
        "token",
        "access_token",
        "auth_token",
        "api_key",
        "apikey",
        "secret",
    }
)
DENY_SUFFIXES = (
    "localhost",
    "local",
    "internal",
    "lan",
    "home",
    "test",
    "invalid",
    "example",
    "onion",
)


def safe_link_literal(raw: object) -> bool:
    """Lexical only. No DNS/public-address/access/redirect/official certification."""
    if (
        type(raw) is not str
        or not 1 <= len(raw) <= 2000
        or any(
            char.isspace() or ord(char) < 32 or ord(char) == 127 or char == "\\"
            for char in raw
        )
        or not re.match(r"(?i)^https?://", raw)
        or "?" in raw
        or "#" in raw
    ):
        return False
    authority = re.split(r"[/]", raw.split("://", 1)[1], maxsplit=1)[0]
    if not authority.isascii() or "@" in authority or "%" in authority or not authority:
        return False
    try:
        parsed = urlsplit(raw)
        host = parsed.hostname
        if (
            host is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.scheme.lower() not in {"http", "https"}
            or parsed.port not in {None, 80 if parsed.scheme.lower() == "http" else 443}
        ):
            return False
        if ":" in authority and authority.rsplit(":", 1)[1] != (
            "80" if parsed.scheme.lower() == "http" else "443"
        ):
            return False
        if host.endswith(".") or any(
            host == suffix or host.endswith(f".{suffix}") for suffix in DENY_SUFFIXES
        ):
            return False
        labels = host.split(".")
        if (
            len(labels) < 2
            or any(
                not re.fullmatch(
                    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label
                )
                for label in labels
            )
            or not re.search(r"[A-Za-z]", labels[-1])
        ):
            return False
        if all(
            re.fullmatch(r"(?:[0-9]+|0[xX][0-9a-fA-F]+)", label) for label in labels
        ):
            return False
        path = parsed.path
        if re.search(r"%(?![0-9a-fA-F]{2})", path) or re.search(r"(?i)%2f", path):
            return False
        decoded = unquote(path, errors="strict")
        if any(
            char.isspace() or ord(char) < 32 or ord(char) == 127 or char == "\\"
            for char in decoded
        ):
            return False
        for segment in decoded.split("/"):
            lower = segment.casefold()
            if lower in PRIVATE_SEGMENTS or any(
                re.search(rf"{re.escape(key)}=", lower) for key in PRIVATE_SEGMENTS
            ):
                return False
        return True
    except (ValueError, UnicodeError):
        return False

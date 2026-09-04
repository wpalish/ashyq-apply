"""The frontend's copy of the vocabularies must match the backend's.

types.ts claims this file enforces it. A renamed status would otherwise reach
the UI as an unstyled chip with no tone and no tooltip, which is exactly the
kind of silent degradation this product must not have.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.domain import enums

TYPES_TS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "types.ts"
FORMAT_TS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "format.ts"

#: TypeScript alias name -> backend enum.
CONTRACT: dict[str, type] = {
    "EligibilityStatus": enums.EligibilityStatus,
    "AdmissionsFit": enums.AdmissionsFit,
    "FundingFit": enums.FundingFit,
    "FundingClassification": enums.FundingClassification,
    "ClaimStatus": enums.ClaimStatus,
    "SourceSpecificity": enums.SourceSpecificity,
    "UserDecision": enums.UserDecision,
    "PipelineStage": enums.PipelineStage,
    "CostCategory": enums.CostCategory,
    "ScholarshipType": enums.ScholarshipType,
    "ApplicationMode": enums.ApplicationMode,
    "DocumentOwner": enums.DocumentOwner,
    "DegreeLevel": enums.DegreeLevel,
    "ApplicantStatus": enums.ApplicantStatus,
}


#: Comments are stripped before matching. A `;` inside a doc comment on a union
#: member would otherwise terminate the match early and silently shorten the
#: parsed vocabulary.
_TS_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_TS_LINE_COMMENT = re.compile(r"//[^\n]*")


def strip_comments(source: str) -> str:
    return _TS_LINE_COMMENT.sub("", _TS_BLOCK_COMMENT.sub("", source))


def parse_union(source: str, alias: str) -> set[str]:
    match = re.search(rf"export type {alias} =(.*?);", strip_comments(source), re.DOTALL)
    if not match:
        raise AssertionError(f"types.ts does not declare `{alias}`")
    return set(re.findall(r"'([^']+)'", match.group(1)))


@pytest.fixture(scope="module")
def types_source() -> str:
    assert TYPES_TS.exists(), f"expected the frontend contract at {TYPES_TS}"
    return TYPES_TS.read_text()


@pytest.mark.parametrize("alias,enum_cls", CONTRACT.items())
def test_the_typescript_union_matches_the_backend_enum(alias, enum_cls, types_source):
    assert parse_union(types_source, alias) == {member.value for member in enum_cls}


def test_the_union_parser_is_not_fooled_by_comments():
    """Guards the guard: a `;` in a doc comment used to truncate the parse."""
    sample = "export type X =\n  | 'a'\n  /** something; with a semicolon */\n  | 'b';\n"
    assert parse_union(sample, "X") == {"a", "b"}


def test_every_status_the_ui_colours_is_a_real_backend_value(types_source):
    """A tone map keyed on a status that no longer exists is dead styling."""
    source = FORMAT_TS.read_text()
    known = {m.value for cls in CONTRACT.values() for m in cls}
    for map_name in (
        "eligibilityTone",
        "admissionsFitTone",
        "fundingFitTone",
        "fundingClassTone",
        "claimStatusTone",
    ):
        block = re.search(rf"export const {map_name}[^=]*= \{{(.*?)\n\}};", source, re.DOTALL)
        assert block, f"format.ts does not declare {map_name}"
        for key in re.findall(r"^\s*([A-Z_]+):", block.group(1), re.M):
            assert key in known, f"{map_name} styles unknown status {key!r}"


def test_every_shortened_label_refers_to_a_real_status():
    source = FORMAT_TS.read_text()
    known = {m.value for cls in CONTRACT.values() for m in cls}
    block = re.search(r"export const STATUS_LABEL[^=]*= \{(.*?)\n\};", source, re.DOTALL)
    assert block
    for key in re.findall(r"^\s*([A-Z_]+):", block.group(1), re.M):
        assert key in known, f"STATUS_LABEL shortens unknown status {key!r}"


def test_the_vocabulary_endpoint_covers_every_contracted_type():
    """The UI can read the vocabularies at runtime instead of hard-coding them."""
    from app.api.routes_meta import vocabulary

    exposed = vocabulary()
    for enum_cls in CONTRACT.values():
        values = {m.value for m in enum_cls}
        assert any(set(v) == values for v in exposed.values()), (
            f"{enum_cls.__name__} is not exposed by /api/vocabulary"
        )


def test_the_job_status_union_matches_the_backend(types_source):
    """The UI branches on job status; a renamed one must not slip through."""
    from app.models import JobStatus

    assert parse_union(types_source, "JobStatus") == {m.value for m in JobStatus}


def test_the_scholarship_interface_carries_every_decomposed_state(types_source):
    """The UI must be able to show *why* an award is unavailable, not just that.

    These fields exist because one flag was answering several questions at
    once; a missing one here means the UI cannot distinguish them either.
    """
    block = re.search(r"export interface Scholarship \{(.*?)\n\}", types_source, re.DOTALL)
    assert block, "types.ts does not declare `Scholarship`"
    declared = set(re.findall(r"^\s*(\w+)[?]?:", block.group(1), re.M))

    from app.schemas.result import Scholarship

    required = {
        "opportunity_exists",
        "currently_available",
        "applicant_eligible",
        "application_window_open",
        "deadline_known",
        "deadline_passed",
        "award_current_for_intake",
        "degree_applicability",
        "available_this_intake",
    }
    assert required <= declared, f"types.ts is missing {sorted(required - declared)}"
    assert declared <= set(Scholarship.model_fields), (
        f"types.ts declares fields the backend does not have: "
        f"{sorted(declared - set(Scholarship.model_fields))}"
    )


SOCIAL_TS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "social.tsx"


def test_the_composer_enforces_the_same_limits_as_the_database():
    """The composer counts characters down for the person writing a post.

    If its copy of the limit drifted above the backend's, the count would reach
    zero after the server had already started refusing the post — the person
    would be told they had room they did not have.
    """
    from app.domain import social

    source = SOCIAL_TS.read_text(encoding="utf-8")
    for name, expected in (
        ("POST_MAX_CHARS", social.POST_MAX_CHARS),
        ("BIO_MAX_CHARS", social.BIO_MAX_CHARS),
    ):
        match = re.search(rf"export const {name} = (\d+);", source)
        assert match, f"social.tsx does not declare {name}"
        assert int(match.group(1)) == expected, f"{name} disagrees with the backend"


def test_live_coverage_reaches_the_frontend_with_the_shape_it_declares(types_source):
    """The registry's real size has to survive the trip to the screen.

    Someone turning demo mode off pictures the open web and gets ten curated
    institutions. PreferencesScreen now says so, reading `live_coverage`
    straight from `capabilities` — so a renamed or dropped key here would
    quietly restore the old, flattering silence rather than break loudly.
    """
    from app.api.routes_meta import live_coverage

    payload = live_coverage()
    assert set(payload) == {"institutions", "countries", "recall_note"}
    assert isinstance(payload["institutions"], int)
    assert isinstance(payload["countries"], list)
    assert payload["recall_note"], "live mode must state its own recall"

    block = re.search(r"live_coverage: \{(.*?)\n  \};", types_source, re.DOTALL)
    assert block, "types.ts does not declare `live_coverage` on Capabilities"
    declared = set(re.findall(r"^\s*(\w+)[?]?:", block.group(1), re.M))
    assert declared == set(payload), (
        f"types.ts declares {sorted(declared)}; the API returns {sorted(payload)}"
    )

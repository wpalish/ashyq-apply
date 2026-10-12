# G1 finite-v2 controls. Direct ORM envelopes only: never persist nonfinite JSON.
# Append to test_preparation_graph_api.py; all referenced imports already exist.

_FINITE_V2_NONFINITE = [
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="positive-inf"),
    pytest.param(float("-inf"), id="negative-inf"),
]
_FINITE_V2_TIME = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)


def _finite_v2_scope():
    return {
        "university": "Synthetic University",
        "programme": "Synthetic Programme",
        "degree": "bachelor",
        "intake": "Fall 2027",
    }


def _finite_v2_claim_row(value, *, key="a" * 32):
    return ClaimRow(
        id=key,
        run_id="b" * 32,
        result_id="c" * 32,
        claim_type="ielts_min_overall",
        status="VERIFIED_CURRENT",
        source_url="https://example.edu/authoritative-synthetic",
        source_specificity="program_intake",
        accessed_at=_FINITE_V2_TIME,
        payload={
            "claim_type": "sat_min_total",
            "status": "UNVERIFIED",
            "source_url": "https://example.edu/copied-synthetic",
            "source_specificity": "aggregator",
            "accessed_at": "2000-01-01T00:00:00Z",
            "official_domain": True,
            "normalized_value": value,
            "original_text_excerpt": "Synthetic finite-control quotation only.",
            "scope": _finite_v2_scope(),
        },
    )


def _finite_v2_conflict_row(values):
    return ConflictRow(
        id="d" * 32,
        run_id="b" * 32,
        result_id="c" * 32,
        claim_type="ielts_min_overall",
        unresolved=True,
        payload={
            "claim_type": "sat_min_total",
            "unresolved": False,
            "subject": "Synthetic numeric-control conflict",
            "claim_ids": ["a" * 32],
            "values": values,
            "source_urls": ["https://example.edu/authoritative-synthetic"],
            "question_for_admissions": "Which synthetic observation is intended?",
        },
    )


def _finite_v2_checklist_row(size, *, origin="column", location="admission_documents"):
    checklist = {
        "result_id": "c" * 32,
        "university": "Synthetic University",
        "program": "Synthetic Programme",
        "generated_at": "2026-10-12T12:00:00Z",
        "completeness": "official",
        location: [
            {
                "name": "Synthetic transcript",
                "purpose": "scholarship" if location == "scholarship_documents" else "admission",
                "owner": "school" if location == "school_actions" else "applicant",
                "max_file_size_mb": size,
                "deadline": "2027-01-15",
                "scope": _finite_v2_scope(),
                "claim_ids": ["a" * 32],
                "source_url": "https://example.edu/synthetic-documents",
            }
        ],
    }
    return ProgramResultRow(
        id="c" * 32,
        run_id="b" * 32,
        university="Synthetic University",
        program="Synthetic Programme",
        payload={"checklist": checklist if origin == "payload" else None},
        checklist=checklist if origin == "column" else None,
    )


@pytest.mark.parametrize("value", _FINITE_V2_NONFINITE)
def test_finite_v2_raw_claim_nested_nonfinite_is_a_failed_read(value):
    bad = _finite_v2_claim_row({"scores": [value]})
    good = _finite_v2_claim_row({"scores": [7.5]}, key="e" * 32)
    before = bad.payload
    claims, failed = graph_api._claims([bad, good], _FINITE_V2_TIME)
    assert failed is True
    assert [claim.id for claim in claims] == [good.id]
    assert claims[0].normalized_value == {"scores": [7.5]}
    assert bad.payload is before


@pytest.mark.parametrize("value", _FINITE_V2_NONFINITE)
def test_finite_v2_raw_conflict_nested_nonfinite_is_a_failed_read(value):
    bad = _finite_v2_conflict_row([{"scores": [value]}])
    good = _finite_v2_conflict_row([6.5, 7.0])
    good.id = "f" * 32
    before = bad.payload
    conflicts, failed = graph_api._conflicts([bad, good])
    assert failed is True
    assert len(conflicts) == 1 and conflicts[0].values == [6.5, 7.0]
    assert conflicts[0].unresolved is True
    assert bad.payload is before


@pytest.mark.parametrize("value", _FINITE_V2_NONFINITE)
@pytest.mark.parametrize("location", ["admission_documents", "scholarship_documents", "school_actions"])
def test_finite_v2_authoritative_column_rejects_raw_nonfinite_document_size(value, location):
    row = _finite_v2_checklist_row(value, location=location)
    before = row.checklist
    with pytest.raises(ValueError):
        graph_api._stored_fields(row)
    assert row.checklist is before and row.payload == {"checklist": None}


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("origin", ["column", "payload"])
def test_finite_v2_numeric_string_document_size_is_rejected_after_coercion(value, origin):
    row = _finite_v2_checklist_row(value, origin=origin)
    with pytest.raises(ValueError, match="finite"):
        graph_api._stored_fields(row)


@pytest.mark.parametrize(
    "value", [None, 7.5, {"scores": [7.5, None]}, {"quote": "NaN"}, {"scores": (6.5, 7.5)}]
)
def test_finite_v2_claim_preserves_finite_value_scope_and_authoritative_columns(value):
    row = _finite_v2_claim_row(value)
    before = deepcopy(row.payload)
    claims, failed = graph_api._claims([row], _FINITE_V2_TIME)
    assert failed is False and len(claims) == 1
    claim = claims[0]
    assert claim.id == row.id and claim.normalized_value == value
    assert claim.claim_type.value == "ielts_min_overall"
    assert claim.status.value == "VERIFIED_CURRENT"
    assert claim.source_url == row.source_url
    assert claim.source_specificity.value == "program_intake"
    assert claim.accessed_at == _FINITE_V2_TIME
    assert claim.is_stale is False and claim.age_days == 0
    assert claim.scope is not None and claim.scope.university == "Synthetic University"
    assert claim.scope.programme == "Synthetic Programme"
    assert row.payload == before


def test_finite_v2_conflict_keeps_finite_values_and_authoritative_unresolved_type():
    values = [None, 6.5, {"band": 7.0}, "NaN"]
    row = _finite_v2_conflict_row(values)
    before = deepcopy(row.payload)
    conflicts, failed = graph_api._conflicts([row])
    assert failed is False and len(conflicts) == 1
    assert conflicts[0].claim_type.value == "ielts_min_overall"
    assert conflicts[0].unresolved is True and conflicts[0].values == values
    assert row.payload == before


@pytest.mark.parametrize("size,expected", [(None, None), (2.5, 2.5), ("2.5", 2.5)])
@pytest.mark.parametrize("origin", ["column", "payload"])
def test_finite_v2_document_keeps_finite_size_scope_dates_and_enums(size, expected, origin):
    row = _finite_v2_checklist_row(size, origin=origin)
    before_payload, before_column = deepcopy(row.payload), deepcopy(row.checklist)
    fields = graph_api._stored_fields(row)
    assert fields.checklist is not None
    checklist = fields.checklist
    item = checklist.admission_documents[0]
    assert item.max_file_size_mb == expected
    assert checklist.result_id == row.id and checklist.university == row.university
    assert checklist.program == row.program and checklist.completeness == "official"
    assert checklist.generated_at == _FINITE_V2_TIME
    assert item.deadline is not None and item.deadline.isoformat() == "2027-01-15"
    assert item.purpose.value == "admission" and item.owner.value == "applicant"
    assert item.scope is not None and item.scope.programme == "Synthetic Programme"
    assert item.claim_ids == ["a" * 32]
    assert row.payload == before_payload and row.checklist == before_column

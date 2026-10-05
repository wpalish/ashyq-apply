"""Conditional translation requirements retain language exceptions and source proof."""

import pytest

from app.domain.enums import ClaimType, DocumentOwner
from tests.test_ntu_scholarship_documents import _read


@pytest.fixture(autouse=True)
def _document_rules_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    """DOC-2 (Astra's PR #41 document rules) is off by default; these tests pin it on."""
    from app.adapters import document_ir
    from app.adapters.documents import web_documents

    monkeypatch.setattr(web_documents, "DOCUMENT_RULES_V2", True)
    monkeypatch.setattr(document_ir, "FORM_LABEL_HEADINGS", True)


CONDITION = (
    "If your documents are not in English, Dutch, French or German, "
    "you will need to upload the original documents and translations."
)


def test_translation_exception_never_becomes_unconditional_certified_english():
    items, builder, _ = _read(
        "<h2>Required documents</h2><ul><li>"
        + CONDITION
        + " Self-made translations are accepted for assessment purposes.</li></ul>"
    )
    assert len(items) == len(builder.claims) == 1
    item, claim = items[0], builder.claims[0]
    assert item.name == "Translation (if originals are not in English, Dutch, French, German)"
    assert item.format_notes == CONDITION
    assert item.owner is DocumentOwner.APPLICANT
    assert item.needs_translation and not item.needs_notarization
    assert claim.claim_type is ClaimType.REQUIRED_DOCUMENT
    assert claim.normalized_value == {
        "document": "Translation of application documents",
        "required_unless_language_in": ["English", "Dutch", "French", "German"],
    }


@pytest.mark.parametrize(
    "statement",
    [
        CONDITION.replace("not in", "in"),
        CONDITION.replace("French or German", "French or another accepted language"),
        CONDITION.replace("will need to", "may"),
        CONDITION.replace("French or German", "French or French"),
        "If requested by the board, you must provide a translation.",
        "Self-made translations are accepted for assessment purposes.",
    ],
)
def test_unparsed_condition_or_permission_does_not_create_required_translation(statement):
    items, builder, _ = _read("<h2>Required documents</h2><ul><li>" + statement + "</li></ul>")
    assert items == []
    assert builder.claims == []


def test_language_variants_and_repeated_clauses_preserve_conditions():
    other = "If the documents are not in Spanish or English, please also provide a translation in English."
    items, builder, _ = _read(f"<p>{CONDITION}</p><p>{CONDITION}</p><p>{other}</p>")
    assert len(items) == len(builder.claims) == 2
    assert builder.claims[1].normalized_value["required_unless_language_in"] == [
        "Spanish",
        "English",
    ]

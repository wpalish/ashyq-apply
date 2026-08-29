"""Fee tables state what flattened text cannot.

Groningen publishes tuition as a table: nationality, year, fee, programme
form. Flattened to text the label "Tuition fees" sits on its own line and the
figures several lines below, so the sentence window — which stops at a newline
— could never reach them. The first "tuition" on the page is inside a URL, and
because only the first match was tried, the whole claim type was abandoned
there. The page states €2,694 and €19,800 and the extractor returned nothing.

Proximity in flattened text is not evidence of association. A table row is:
the row is what ties €19,800 to non-EU/EEA students, and it is what the
excerpt has to show.
"""
from pathlib import Path

from app.adapters.extraction import ClaimBuilder, extract_cost_tables
from app.domain.enums import ClaimType

PAGES = Path(__file__).parent / "fixtures" / "pages"
RUG = "https://www.rug.nl/bachelors/computing-science/"


def _claims():
    html = (PAGES / "rug-computing-science.html").read_text()
    return extract_cost_tables(html, ClaimBuilder(source_url=RUG, official_domain=True))


def test_both_fee_rows_are_read() -> None:
    tuition = [c for c in _claims() if c.claim_type is ClaimType.TUITION]
    amounts = sorted(c.normalized_value["amount"] for c in tuition)
    assert amounts == [2694.0, 19800.0]


def test_each_fee_is_tied_to_who_pays_it() -> None:
    """A Kazakhstani applicant pays €19,800, not €2,694. Reporting the wrong
    row is not a rounding error — it understates the cost sevenfold."""
    by_audience = {
        c.subject_key: c.normalized_value["amount"]
        for c in _claims()
        if c.claim_type is ClaimType.TUITION
    }
    assert by_audience["EU/EEA"] == 2694.0
    assert by_audience["non-EU/EEA"] == 19800.0


def test_the_excerpt_proves_the_association() -> None:
    for c in _claims():
        if c.claim_type is not ClaimType.TUITION:
            continue
        assert str(int(c.normalized_value["amount"])) in c.original_text_excerpt.replace(",", "")
        assert c.subject_key in c.original_text_excerpt


def test_the_academic_year_comes_from_the_row() -> None:
    years = {c.academic_year for c in _claims() if c.claim_type is ClaimType.TUITION}
    assert years == {"2026/27"}


def test_a_programme_page_that_carries_its_own_fee_table_is_read() -> None:
    """Groningen states tuition on the programme page itself, not on a separate
    fees page. Wiring table reading only into the cost adapter would have left
    the figures unread on exactly the page a student is looking at."""
    from app.adapters.requirements.web_requirements import claims_from_fee_tables

    html = (PAGES / "rug-computing-science.html").read_text()
    builder = ClaimBuilder(source_url=RUG, official_domain=True)
    claims = claims_from_fee_tables(html, builder)
    amounts = sorted(c.normalized_value["amount"] for c in claims)
    assert amounts == [2694.0, 19800.0]

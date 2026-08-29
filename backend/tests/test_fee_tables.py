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


class TestACostOfAttendanceTableIsNotAFeeTable:
    """Two tables, two shapes, and reading one as the other is dangerous.

    Groningen's fee table segments *one* fee by audience:

        Nationality | Year      | Fee      | Programme form
        EU/EEA      | 2026-2027 | € 2694   | full-time
        non-EU/EEA  | 2026-2027 | € 19800  | full-time

    Aalto's cost-of-attendance table lists *different costs*:

        Item                      | Amount per year
        Tuition fee (non-domestic)| EUR 15,000
        Mandatory university fees | EUR 110
        Housing / accommodation   | EUR 7,800
        Meal plan                 | EUR 3,000
        Estimated total cost      | EUR 25,910

    Reading the second as the first made every row a tuition rate, and the
    last row won: tuition became 25,910 — the whole cost of attending. A
    full-tuition award then appeared to cover everything, and the shortlist
    told the applicant they had **0 remaining per year** when €10,910 of
    housing, meals and fees was still theirs to pay.

    That is the worst failure this product has: not a missing number, a
    confident wrong one, in the direction that costs the student money.
    """

    def _claims(self):
        html = (PAGES / "aalto-cost-of-attendance.html").read_text()
        return extract_cost_tables(
            html, ClaimBuilder(source_url="fixture://aalto/costs.html", official_domain=True)
        )

    def test_tuition_is_the_tuition_row_not_the_total(self):
        tuition = [c for c in self._claims() if c.claim_type is ClaimType.TUITION]
        assert [c.normalized_value["amount"] for c in tuition] == [15000.0], (
            "every row was read as a tuition rate, and the total won"
        )

    def test_each_row_becomes_its_own_cost_category(self):
        by_type = {
            c.claim_type: c.normalized_value["amount"] for c in self._claims()
        }
        assert by_type[ClaimType.TUITION] == 15000.0
        assert by_type[ClaimType.MANDATORY_FEES] == 110.0
        assert by_type[ClaimType.HOUSING_COST] == 7800.0
        assert by_type[ClaimType.MEALS_COST] == 3000.0

    def test_a_total_row_is_not_a_cost_category(self):
        """A total is the sum of the rows above it. Recording it as one of
        them double-counts, and recording it as tuition is how the gap
        collapsed to zero."""
        totals = [
            c for c in self._claims()
            if c.claim_type is ClaimType.TOTAL_COST_OF_ATTENDANCE
        ]
        assert [c.normalized_value["amount"] for c in totals] == [25910.0]
        for claim in self._claims():
            if claim.claim_type is not ClaimType.TOTAL_COST_OF_ATTENDANCE:
                assert claim.normalized_value["amount"] != 25910.0

    def test_the_audience_shaped_table_still_works(self):
        """The case the extractor was written for must not regress."""
        html = (PAGES / "rug-computing-science.html").read_text()
        claims = extract_cost_tables(html, ClaimBuilder(source_url=RUG, official_domain=True))
        by_audience = {
            c.subject_key: c.normalized_value["amount"]
            for c in claims
            if c.claim_type is ClaimType.TUITION
        }
        assert by_audience["EU/EEA"] == 2694.0
        assert by_audience["non-EU/EEA"] == 19800.0

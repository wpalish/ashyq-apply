"""Money written the way European universities write it.

`€ 17.310` is seventeen thousand three hundred and ten euros on a Dutch,
German, Austrian, Polish or Danish page. Read as a decimal point it becomes
€17.31 — a thousandfold understatement of a year's tuition, landing directly
in the funding gap, which is the number this product is most careful about.

Seven of the ten canary institutions publish in a dot-thousands locale.
"""

from __future__ import annotations

import pytest

from app.adapters.extraction import parse_money


class TestEuropeanFormat:
    @pytest.mark.parametrize("text,expected", [
        ("€ 17.310", 17310.0),
        ("€ 2.601", 2601.0),
        ("€2.694", 2694.0),
        ("€ 8.406", 8406.0),
        ("EUR 1.234.567", 1234567.0),
        ("€ 17.310,00", 17310.0),
        ("€ 1.234,56", 1234.56),
        ("€ 43,35", 43.35),
        ("€ 0,50", 0.5),
    ])
    def test_a_dot_is_a_thousands_separator_and_a_comma_is_the_decimal(self, text, expected):
        parsed = parse_money(text)
        assert parsed is not None, f"{text!r} was not recognised as money at all"
        assert parsed[0] == pytest.approx(expected), f"{text!r} read as {parsed[0]}"


class TestAngloFormat:
    @pytest.mark.parametrize("text,expected", [
        ("$17,310", 17310.0),
        ("$17,310.50", 17310.5),
        ("£9,250", 9250.0),
        ("USD 1,234,567", 1234567.0),
        ("$1,234.56", 1234.56),
        ("$0.50", 0.5),
    ])
    def test_a_comma_is_a_thousands_separator_and_a_dot_is_the_decimal(self, text, expected):
        parsed = parse_money(text)
        assert parsed is not None, f"{text!r} was not recognised as money at all"
        assert parsed[0] == pytest.approx(expected), f"{text!r} read as {parsed[0]}"


class TestUnseparated:
    @pytest.mark.parametrize("text,expected", [
        ("€ 15 000", 15000.0),
        ("15000 EUR", 15000.0),
        ("$15000", 15000.0),
        ("CHF 1500", 1500.0),
    ])
    def test_spaces_and_bare_numbers(self, text, expected):
        parsed = parse_money(text)
        assert parsed is not None and parsed[0] == pytest.approx(expected)


class TestTheAmbiguousCase:
    """A single separator followed by exactly three digits.

    `1.500` is fifteen hundred in Amsterdam and one-and-a-half in a physics
    paper. On a fees page it is money, and money is written in whole units far
    more often than in thousandths, so three trailing digits is read as a
    thousands separator. The choice is recorded here because it is a choice.
    """

    @pytest.mark.parametrize("text,expected", [
        ("€ 1.500", 1500.0),
        ("$1,500", 1500.0),
    ])
    def test_three_trailing_digits_are_thousands(self, text, expected):
        assert parse_money(text)[0] == pytest.approx(expected)

    @pytest.mark.parametrize("text,expected", [
        ("€ 17.31", 17.31),
        ("$0.99", 0.99),
        ("€ 5,5", 5.5),
    ])
    def test_one_or_two_trailing_digits_are_a_decimal(self, text, expected):
        assert parse_money(text)[0] == pytest.approx(expected)


class TestNotMoney:
    @pytest.mark.parametrize("text", [
        "the 2026/2027 academic year",
        "IELTS 6.5 overall",
        "180 ECTS credits",
        "no figures here at all",
    ])
    def test_ordinary_numbers_are_not_read_as_money(self, text):
        """A currency marker is required. Without one this would turn every
        year, score and credit count into a fee."""
        assert parse_money(text) is None


class TestRegression:
    def test_the_delft_statutory_fee_is_not_understated_by_a_factor_of_a_thousand(self):
        """The defect, in the words of the page it came from.

        tudelft.nl publishes "Statutory rate € 2.601 € 2.694" for 2025/2026 and
        2026/2027. Read as decimals those are €2.60 and €2.69, and a funding
        gap computed from them is worthless.
        """
        assert parse_money("Statutory rate € 2.601")[0] == pytest.approx(2601.0)
        assert parse_money("€ 19.906")[0] == pytest.approx(19906.0)


class TestCostExtractionScansTheWholePage:
    """Where the label first appears is not where the figure is.

    TU Delft's fees page says "tuition" six times in prose before any table.
    The extractor searched for the first occurrence only, found no money within
    120 characters of it, and abandoned the category — with the figures further
    down the same page.
    """

    @staticmethod
    def builder():
        from datetime import UTC, datetime

        from app.adapters.extraction import ClaimBuilder
        from app.domain.enums import SourceSpecificity

        return ClaimBuilder(
            source_url="https://uni.edu/fees", page_title="Fees",
            specificity=SourceSpecificity.UNIVERSITY_ADMISSIONS,
            academic_year="2026/27", official_domain=True,
            extraction_method="html_rule", accessed_at=datetime.now(UTC),
        )

    def test_a_dense_fee_table_does_not_attach_a_figure_to_the_wrong_label(self):
        """Scanning every occurrence of a label was tried and reverted.

        On TU Delft's fee table it reported the statutory tuition rate of
        €2,694 as the *housing* cost, because the two sat within 120 characters
        of each other once the table was flattened to text, and the excerpt it
        produced proved nothing. Proximity in a table is not evidence of
        association, and this product treats a claim whose excerpt does not
        prove its value as invalid.
        """
        from app.adapters.extraction import extract_costs

        text = (
            "Statutory rate 2025/2026 2026/2027 Statutory rate € 2.601 € 2.694 "
            "Institutional rate € 18.175 € 19.906 housing is arranged separately."
        )
        claims = extract_costs(text, self.builder())
        housing = [c for c in claims if c.claim_type.value == "housing_cost"]
        assert not housing, (
            f"a tuition figure was reported as housing: "
            f"{[c.normalized_value for c in housing]}"
        )

    def test_a_per_credit_rate_is_not_reported_as_the_annual_fee(self):
        """Delft's first money-bearing "tuition" match is "€ 43,35 per EC".

        That is a price per credit. Reporting it as the tuition fee would
        understate a year by two orders of magnitude, which is worse than
        reporting nothing.
        """
        from app.adapters.extraction import extract_costs

        text = (
            "Proof of paid tuition fee is required. "
            "Bridging and Educational module € 43,35 per EC € 44,90 per EC."
        )
        claims = extract_costs(text, self.builder())
        tuition = [c for c in claims if c.claim_type.value == "tuition"]
        assert not tuition, (
            f"a per-credit rate was reported as tuition: "
            f"{[c.normalized_value for c in tuition]}"
        )

    @pytest.mark.parametrize("qualifier", [
        "per EC", "per ECTS", "per credit", "per month", "per week", "per course",
    ])
    def test_every_per_unit_qualifier_is_refused(self, qualifier):
        from app.adapters.extraction import extract_costs

        text = f"The tuition fee is € 500 {qualifier} for this programme."
        claims = extract_costs(text, self.builder())
        assert not [c for c in claims if c.claim_type.value == "tuition"]

    def test_a_per_year_figure_is_still_accepted(self):
        from app.adapters.extraction import extract_costs

        text = "The tuition fee is € 15.000 per year for non-EU students."
        claims = extract_costs(text, self.builder())
        tuition = [c for c in claims if c.claim_type.value == "tuition"]
        assert tuition and tuition[0].normalized_value["amount"] == pytest.approx(15000.0)

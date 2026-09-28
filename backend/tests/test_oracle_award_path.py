"""The oracle measures certified award facts with the adapter's own award reader.

Synthetic page text: it exercises the plumbing (classification, parsing,
identity binding), not the real NTU page, which only live runs may read.
"""

from datetime import UTC, datetime

from evaluation.research.oracle import _award_claims

NTU = (
    "https://www.ntu.edu.sg/admissions/undergraduate/scholarships/"
    "scholarship-opportunities/detail/nanyang-scholarship"
)
PAGE = """<html><head><title>Nanyang Global Scholarship</title></head><body>
<h1>Nanyang Global Scholarship</h1>
<p>The Nanyang Global Scholarship is open to all nationalities.</p>
<p>The scholarship covers tuition fees and provides a living allowance of S$6,500 per academic year.</p>
</body></html>"""


def test_an_award_page_is_read_under_its_certified_identity():
    gated, ungated = _award_claims(NTU, PAGE, datetime(2026, 9, 28, tzinfo=UTC), "Computer Science")
    keys = {k for k, _ in ungated}
    assert "scholarships.nanyang_global.exists" in keys
    assert all(k in keys for k, _ in gated)


def test_an_unbound_page_binds_nothing_to_the_award():
    _, ungated = _award_claims(
        "https://www.ntu.edu.sg/other-award", PAGE, datetime(2026, 9, 28, tzinfo=UTC)
    )
    assert not any(k.startswith("scholarships.nanyang_global") for k, _ in ungated)

"""EXTRA-7: an FAQ page is not a scholarship, however it spells "FAQ".

In live run 35697105238 four of NTU's twelve claims — a third of every claim
the whole ten-university run produced — were an award called "FAQs on
scholarships", stamped CONFLICTING because the page's own prose then produced
a second claim saying that award did not exist.

The cause was the plural: `\\bf\\.?a\\.?q\\.?\\b` matches "FAQ" and not "FAQs",
because there is no word boundary between the q and the s. This is the third
plural bug in this repository ("waivers" and "scholarships" were the others),
so these tests cover the pattern, not only the one page.
"""

from __future__ import annotations

import pytest

from app.adapters.page_classifier import PageType, classify_page

_BODY = """
<p>The scholarship offered to you is applicable for the course indicated in the
scholarship offer. If you change your degree programme during the admissions
exercise, the scholarship will be withdrawn.</p>
<p>Eligibility: all admitted students are automatically considered. The award
covers tuition and is worth up to SGD 10,000 per year.</p>
"""


def _page(title: str) -> str:
    return f"<html><head><title>{title}</title></head><body><h1>{title}</h1>{_BODY}</body></html>"


@pytest.mark.parametrize(
    "title",
    [
        "FAQ on scholarships",
        "FAQs on scholarships",
        "faqs on scholarships",
        "F.A.Q. on scholarships",
        "Scholarships: frequently asked question",
        "Scholarships: frequently asked questions",
    ],
)
def test_every_spelling_of_faq_reads_as_an_faq(title):
    classification = classify_page(url="https://uni.edu/scholarships/faq", html=_page(title))
    assert classification.page_type is PageType.SCHOLARSHIP_FAQ, title


def test_the_failing_page_from_the_live_run_is_not_an_award():
    """The exact title and URL that produced the phantom award."""
    classification = classify_page(
        url="https://www.ntu.edu.sg/admissions/undergraduate/scholarships/faqs-on-scholarships",
        html=_page("FAQs on scholarships"),
    )
    assert classification.page_type is not PageType.SCHOLARSHIP_AWARD
    assert classification.subject is None, "an FAQ has no award name to carry"


def test_a_real_award_page_is_still_an_award():
    """The fix must not swallow the pages this classifier exists to find."""
    classification = classify_page(
        url="https://uni.edu/scholarships/global-merit",
        html=_page("Global Merit Scholarship"),
    )
    assert classification.page_type is PageType.SCHOLARSHIP_AWARD
    assert classification.subject == "Global Merit Scholarship"


def test_a_word_merely_starting_with_faq_is_not_an_faq():
    """`faqs?` must not match inside a longer word."""
    classification = classify_page(
        url="https://uni.edu/scholarships/faqir-memorial",
        html=_page("Faqir Memorial Scholarship"),
    )
    assert classification.page_type is PageType.SCHOLARSHIP_AWARD

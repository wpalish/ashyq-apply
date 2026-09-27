"""Discovery reads the applicant's subject through the ontology's strong aliases.

Run 42, Groningen: the certified programme page is ``/bachelors/computing-science``.
The ontology already records "computing science" as the same field as
"computer science"; discovery compared words literally and never scored it.
"""

from __future__ import annotations

from app.adapters.discovery.live_discovery import (
    matches_field,
    matches_field_text,
    with_strong_aliases,
)

FIELDS = ["computer science"]


def test_a_strong_alias_scores_like_the_field_itself():
    assert matches_field("https://www.rug.nl/bachelors/computing-science", FIELDS) == matches_field(
        "https://uni.edu/bachelors/computer-science", FIELDS
    )
    assert matches_field_text("Computing Science", FIELDS)


def test_a_related_concept_is_not_an_alias():
    names = [n.lower() for n in with_strong_aliases(FIELDS)]
    assert "data science" not in names
    assert "software engineering" not in names
    assert not matches_field_text("Data Science", FIELDS)


def test_an_unknown_field_is_used_verbatim_and_counted_once():
    assert with_strong_aliases(["Egyptology"]) == ["Egyptology"]
    assert matches_field("https://uni.edu/egyptology", ["Egyptology"]) == 8


def test_an_alias_inside_another_programmes_name_is_not_the_field():
    """Run 50: Vienna kept Business Informatics, HKU Computing and Data Science."""
    assert not matches_field_text("Business Informatics (bachelor's programme)", FIELDS)
    assert not matches_field_text("Computing and Data Science", FIELDS)
    assert not matches_field_text("Cloud Computing", FIELDS)
    assert matches_field_text("Informatics", FIELDS)
    assert matches_field_text("Computing Science (Bachelor)", FIELDS)


def test_the_applicants_own_words_still_match_inside_a_longer_title():
    assert matches_field_text("Data & Computer Science", FIELDS)
    assert matches_field_text("Bachelor of Computing (Hons) in Computer Science", FIELDS)


def test_a_single_course_page_is_excluded_but_a_course_list_path_is_not():
    """Run 54, Warsaw: search offered one course's page first."""
    from app.adapters.discovery.live_discovery import is_excluded_path

    assert is_excluded_path(
        "https://informatorects.uw.edu.pl/en/courses/view?prz_kod=1000-111bWI1a"
    )
    assert not is_excluded_path("https://informatorects.uw.edu.pl/en/programmes-all/IN")
    assert not is_excluded_path("https://uni.edu/study/courses/computer-science")

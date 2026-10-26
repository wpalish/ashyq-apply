"""gpa_kind: "grade point average" is a grade, not a test score (dev5 VILNIUS TECH)."""

from evaluation.research.expert.core_drafts import gpa_kind


def test_grade_point_average_is_a_grade():
    answer = {"quote": "a minimum cumulative grade point average (CGPA) of 60%", "value": "60%"}
    assert gpa_kind(answer) == "grade"


def test_points_on_an_entrance_test_stay_a_test():
    assert gpa_kind({"quote": "at least 100 points on the entrance test"}) == "test"

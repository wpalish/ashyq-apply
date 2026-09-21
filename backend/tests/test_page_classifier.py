"""Page classification: what a page is, and what it only looks like."""

from __future__ import annotations


class TestADegreeWordIsNotAProgramme:
    """V2-29 — headings a live run actually claimed a programme from.

    Groningen's "Bachelor's Open Day" and Delft's "Preparing for a bachelor"
    became `programme.exists` claims in the 2026-09-21 capture, and the
    benchmark scored them as wrong-scope claims about Computing Science and
    Computer Science and Engineering. Both contain a degree word; neither is a
    programme.
    """

    def test_an_open_day_is_not_a_programme(self):
        from app.adapters.page_classifier import _program_name

        assert _program_name("Bachelor's Open Day") is None

    def test_an_advice_page_is_not_a_programme(self):
        from app.adapters.page_classifier import _program_name

        assert _program_name("Preparing for a bachelor") is None

    def test_an_event_in_any_of_its_usual_words_is_not_a_programme(self):
        from app.adapters.page_classifier import _program_name

        for heading in (
            "Master's Information Session",
            "Bachelor Open Evening",
            "Meet us at the Bachelor Fair",
            "Bachelor taster day",
        ):
            assert _program_name(heading) is None, heading

    def test_a_real_programme_with_an_ordinary_name_still_passes(self):
        """The rule must not cost a programme its page: only headings that
        announce an event or an instruction are refused."""
        from app.adapters.page_classifier import _program_name

        for heading in (
            "BSc Computer Science",
            "Bachelor of Science in Computer Science",
            "Bachelor of Arts, Visual Studies",
            "MSc Computer Science and Engineering",
        ):
            assert _program_name(heading) == heading, heading

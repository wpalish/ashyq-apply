"""The gold set has to be trustworthy before anything measured against it is.

A benchmark is a claim about the world, and this one is assembled by hand. Every
way it could quietly become wrong is a way the extractor's score becomes wrong
in the same direction and nobody notices:

  - an answer with no URL or no excerpt cannot be re-checked, so it is not
    evidence of anything;
  - an answer taken from a rankings site measures the extractor against an
    aggregator, which the product refuses to treat as proof anywhere else;
  - a selection edited after seeing results measures the person editing it.

So the file is validated as strictly as the product validates a claim, and the
selection carries a digest: adding audited answers is expected and free, while
changing *which* programmes are in the set fails a test until it is re-frozen
in a visible commit.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date

import pytest

from app.eval.gold import (
    ABSENT,
    ANSWERED,
    GOLD_FILE,
    NOT_CHECKED,
    GoldDataError,
    parse,
    source_is_official,
)
from app.pipeline.assessment import DECISION_QUESTIONS

#: sha256 over the sorted (institution, discipline) pairs, frozen 2026-08-30
#: before any change to extraction. Adding audited answers does not move it.
SELECTION_DIGEST = "6c48915b012aa95d67ff6862784acdfd65e47effcb4432a9338f1d1da96dcfee"

QUESTION_LABELS = [label for label, _types in DECISION_QUESTIONS]


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(GOLD_FILE.read_text())


@pytest.fixture(scope="module")
def gold(raw: dict):
    return parse(raw)


class TestTheSelectionIsFrozen:
    def test_the_selection_matches_the_digest_recorded_when_it_was_frozen(
        self, raw: dict
    ):
        """A holdout chosen after seeing the result measures nothing, and the
        same is true of a gold set. Changing the selection is allowed; doing it
        silently is not."""
        pairs = sorted((p["institution"], p["discipline"]) for p in raw["programmes"])
        digest = hashlib.sha256(json.dumps(pairs).encode()).hexdigest()
        assert digest == SELECTION_DIGEST, (
            "the gold selection changed. If that is deliberate, re-freeze it "
            "here in the same commit and say why in the message"
        )

    def test_the_rule_that_produced_the_selection_is_recorded(self, gold):
        assert len(gold.selection_rule) > 80, (
            "a selection with no stated rule cannot be checked for bias"
        )

    def test_every_programme_covers_every_decision_question_exactly_once(self, gold):
        for programme in gold.programmes:
            labels = [a.question for a in programme.answers]
            assert labels == QUESTION_LABELS, (
                f"{programme.id} does not cover the decision questions in order; "
                "a missing question is silently excluded from recall"
            )

    def test_programme_ids_are_unique(self, gold):
        ids = [p.id for p in gold.programmes]
        assert len(ids) == len(set(ids))


class TestEveryAuditedAnswerCanBeRechecked:
    def test_an_answered_question_carries_evidence(self, gold):
        for programme in gold.programmes:
            for answer in programme.answered():
                assert answer.claims, f"{programme.id}/{answer.question}"
                for claim in answer.claims:
                    assert claim.source_url.startswith("https://")
                    assert len(claim.excerpt.strip()) >= 20, (
                        f"{programme.id}/{answer.question}: the excerpt is too "
                        "short to show the answer was really on the page"
                    )
                    assert claim.accessed_at <= date.today(), (
                        f"{programme.id}/{answer.question}: read in the future"
                    )

    def test_gold_truth_comes_from_the_institution(self, gold):
        """The product will not accept an aggregator as proof; neither will the
        thing that grades it."""
        for programme in gold.programmes:
            for answer in programme.answered():
                for claim in answer.claims:
                    assert source_is_official(claim, programme), (
                        f"{programme.id}/{answer.question}: {claim.source_url}"
                    )

    def test_an_unchecked_or_absent_question_carries_no_claims(self, gold):
        for programme in gold.programmes:
            for answer in programme.answers:
                if answer.verdict in (ABSENT, NOT_CHECKED):
                    assert not answer.claims

    def test_absence_is_recorded_with_a_reason(self, gold):
        """`absent` is a positive finding — someone looked and it was not there.

        Without a note it is indistinguishable from "nobody could find it",
        and the two have opposite consequences: one says the extractor must
        not emit a claim, the other says nothing at all.
        """
        for programme in gold.programmes:
            for answer in programme.absent():
                assert answer.note.strip(), f"{programme.id}/{answer.question}"


class TestTheLoaderRefusesWhatItCannotStandBehind:
    @staticmethod
    def _payload(**overrides):
        base = {
            "version": 1,
            "frozen_at": "2026-08-30",
            "frozen_at_commit": "abc1234",
            "selection_rule": "x" * 100,
            "programmes": [
                {
                    "id": "example-cs",
                    "institution": "Example University",
                    "domain": "example.edu",
                    "discipline": "computer science",
                    "programme": "BSc Computer Science",
                    "programme_url": "https://www.example.edu/bsc-cs",
                    "answers": [],
                }
            ],
        }
        base["programmes"][0].update(overrides)
        return base

    @staticmethod
    def _answer(**overrides):
        answer = {
            "question": "tuition",
            "verdict": ANSWERED,
            "claims": [
                {
                    "type": "tuition",
                    "value": "2530 EUR",
                    "source_url": "https://www.example.edu/fees",
                    "excerpt": "Statutory tuition fee 2026/27: EUR 2,530 per year.",
                    "accessed_at": "2026-08-30",
                    "specificity": "program",
                    "status": "VERIFIED_CURRENT",
                }
            ],
        }
        answer.update(overrides)
        return answer

    def test_an_answer_with_no_claim_is_refused(self):
        payload = self._payload(answers=[self._answer(claims=[])])
        with pytest.raises(GoldDataError, match="no claim behind it"):
            parse(payload)

    def test_a_claim_missing_its_excerpt_is_refused(self):
        answer = self._answer()
        answer["claims"][0]["excerpt"] = ""
        with pytest.raises(GoldDataError, match="excerpt"):
            parse(self._payload(answers=[answer]))

    def test_a_claim_missing_when_it_was_read_is_refused(self):
        answer = self._answer()
        del answer["claims"][0]["accessed_at"]
        with pytest.raises(GoldDataError, match="accessed_at"):
            parse(self._payload(answers=[answer]))

    def test_a_claim_from_another_domain_is_refused(self):
        """The failure that would be hardest to spot by eye: a plausible URL on
        a site that is not the university's."""
        answer = self._answer()
        answer["claims"][0]["source_url"] = "https://www.topuniversities.com/example"
        with pytest.raises(GoldDataError, match="not on example.edu"):
            parse(self._payload(answers=[answer]))

    def test_a_lookalike_domain_is_refused(self):
        answer = self._answer()
        answer["claims"][0]["source_url"] = "https://example.edu.evil.test/fees"
        with pytest.raises(GoldDataError, match="not on example.edu"):
            parse(self._payload(answers=[answer]))

    def test_a_subdomain_of_the_institution_is_accepted(self):
        """Faculties publish on their own subdomains, and that is still the
        institution speaking."""
        answer = self._answer()
        answer["claims"][0]["source_url"] = "https://science.example.edu/fees"
        assert parse(self._payload(answers=[answer])).programmes[0].answered()

    def test_an_unknown_verdict_is_refused(self):
        with pytest.raises(GoldDataError, match="verdict"):
            parse(self._payload(answers=[self._answer(verdict="probably")]))

    def test_an_unknown_claim_type_is_refused(self):
        answer = self._answer()
        answer["claims"][0]["type"] = "vibes"
        with pytest.raises(GoldDataError, match="not a claim type"):
            parse(self._payload(answers=[answer]))

    def test_auditing_without_naming_the_programme_is_refused(self):
        payload = self._payload(programme="", programme_url="",
                                answers=[self._answer()])
        with pytest.raises(GoldDataError):
            parse(payload)


class TestCoverageIsReportedRatherThanAssumed:
    def test_unaudited_slots_are_counted_and_not_hidden(self, gold):
        coverage = gold.coverage()
        assert coverage["question_slots"] == len(gold.programmes) * len(QUESTION_LABELS)
        assert (
            coverage["answered"] + coverage["absent"] + coverage["not_checked"]
            == coverage["question_slots"]
        )

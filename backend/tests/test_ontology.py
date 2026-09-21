"""V2-12 — the field and degree ontology.

Nearly every test here is about one boundary: a strong alias is the same
field, a related concept is only worth fetching. Getting that wrong sends an
applicant to a programme that will not take their application, which is why
the two ideas are not allowed to share a return value.
"""

from __future__ import annotations

import json

import pytest

from app.adapters.search.ontology import (
    ONTOLOGY_PATH,
    Relation,
    canonical_field,
    degree_aliases,
    is_equivalent,
    load_ontology,
    ontology_version,
    retrieval_candidates,
)
from app.domain.enums import DegreeLevel


class TestAStrongAliasIsTheSameFieldAndARelatedOneIsNot:
    @pytest.mark.parametrize(
        "alias", ["computing science", "computing", "informatics", "Computer Science"]
    )
    def test_strong_aliases_resolve_to_one_concept(self, alias):
        assert canonical_field(alias) == "computer_science"
        assert is_equivalent("computer science", alias)

    @pytest.mark.parametrize(
        "neighbour",
        [
            "data science",
            "software engineering",
            "artificial intelligence",
            "computer engineering",
            "information systems",
            "information technology",
        ],
    )
    def test_a_neighbour_is_never_equivalent(self, neighbour):
        """The corpus already made this call twice by hand; encode it once."""
        assert not is_equivalent("computer science", neighbour)

    def test_the_two_aalto_decisions_are_what_this_module_encodes(self):
        """Draft2 refused Data Science; draft7 left Computer Engineering open.

        Both stay retrieval candidates here, so discovery still finds them and
        a human still decides. Neither becomes an automatic match.
        """
        candidates = {c.term: c for c in retrieval_candidates("computer science")}

        for term in ("data science", "computer engineering"):
            assert candidates[term].relation is Relation.RELATED
            assert not candidates[term].is_match

    def test_a_related_term_cannot_be_reached_through_alias_resolution(self):
        """Otherwise ``data science`` would resolve to computer science."""
        assert canonical_field("data science") == "data_science"
        assert canonical_field("computer engineering") == "computer_engineering"

    def test_the_relation_is_not_symmetric_by_accident(self):
        """Data science lists computer science as a neighbour, not as itself."""
        assert not is_equivalent("data science", "computer science")


class TestRetrievalExpansionIsOrderedAndHonest:
    def test_matches_come_before_candidates(self):
        """A small query budget should be spent on terms that would be a match."""
        relations = [c.is_match for c in retrieval_candidates("computer science")]

        assert relations == sorted(relations, reverse=True)

    def test_an_unknown_field_is_searched_for_verbatim(self):
        """Absence from the vocabulary is not a claim that the field is unreal."""
        candidates = retrieval_candidates("maritime archaeology")

        assert [c.term for c in candidates] == ["maritime archaeology"]
        assert canonical_field("maritime archaeology") is None

    def test_localized_aliases_are_matches_and_carry_their_language(self):
        finnish = [c for c in retrieval_candidates("computer science") if c.language == "fi"]

        assert [c.term for c in finnish] == ["tietotekniikka"]
        assert finnish[0].relation is Relation.LOCALIZED_ALIAS
        assert finnish[0].is_match

    def test_localized_aliases_can_be_left_out(self):
        candidates = retrieval_candidates("computer science", include_localized=False)

        assert all(c.language == "en" for c in candidates)

    def test_an_accented_or_cased_term_still_resolves(self):
        assert canonical_field("Informatik") == "computer_science"
        assert canonical_field("  INFORMATICA  ") == "computer_science"
        assert canonical_field("информатика") == "computer_science"


class TestDegrees:
    @pytest.mark.parametrize(
        ("degree", "expected"),
        [
            (DegreeLevel.BACHELOR, "bsc"),
            (DegreeLevel.MASTER, "msc"),
            (DegreeLevel.PHD, "phd"),
            (DegreeLevel.FOUNDATION, "foundation"),
        ],
    )
    def test_every_level_has_aliases_including_the_common_abbreviation(self, degree, expected):
        aliases = degree_aliases(degree)

        assert aliases[0] == str(degree) or str(degree) in aliases
        assert expected in aliases

    def test_every_degree_level_in_the_enum_is_in_the_ontology(self):
        """A level the ontology forgets would silently lose its abbreviations."""
        for level in DegreeLevel:
            assert degree_aliases(level)


class TestTheVocabularyItselfIsWellFormed:
    def test_it_is_versioned_so_a_measurement_can_be_explained_later(self):
        assert ontology_version() == load_ontology().version
        assert ontology_version()

    def test_no_term_is_both_a_strong_alias_and_a_neighbour_of_the_same_concept(self):
        for key, concept in load_ontology().fields.items():
            overlap = set(concept["strong_aliases"]) & set(concept["related_not_equivalent"])
            assert not overlap, f"{key}: {overlap} is claimed to be both"

    def test_no_alias_is_shared_by_two_concepts(self):
        """An ambiguous alias cannot be resolved; the loader refuses to try."""
        seen: dict[str, str] = {}
        for key, concept in load_ontology().fields.items():
            for alias in concept["strong_aliases"]:
                assert seen.setdefault(alias, key) == key, f"{alias!r} claimed by two concepts"

    def test_every_neighbour_is_a_real_term_not_a_typo(self):
        """A misspelt neighbour is a query that finds nothing, forever and silently."""
        known = {
            alias
            for concept in load_ontology().fields.values()
            for alias in concept["strong_aliases"]
        }
        unvouched = {
            neighbour
            for concept in load_ontology().fields.values()
            for neighbour in concept["related_not_equivalent"]
        } - known

        # Neighbours that are not themselves concepts in this ontology are
        # listed here deliberately, so adding one is a visible decision.
        assert unvouched == {
            "applied mathematics",
            "business analytics",
            "cognitive science",
            "computer science and engineering",
            "econometrics",
            "electrical engineering",
            "electronic engineering",
            "embedded systems",
            "information systems",
            "information technology",
            "machine learning",
            "statistics",
        }

    def test_the_file_is_the_single_source_and_parses(self):
        raw = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))

        assert set(raw) == {"version", "notes", "fields", "degrees"}
        assert raw["fields"].keys() == load_ontology().fields.keys()


class TestTheLoaderRefusesAmbiguousData:
    def test_one_alias_claimed_by_two_concepts_stops_the_load(self, tmp_path, monkeypatch):
        """Resolving it either way would be a coin toss nobody could audit."""
        from app.adapters.search import ontology as module

        bad = tmp_path / "ontology.json"
        bad.write_text(
            json.dumps(
                {
                    "version": "test",
                    "notes": "synthetic fixture",
                    "fields": {
                        "computer_science": {
                            "label": "Computer Science",
                            "strong_aliases": ["computing"],
                            "related_not_equivalent": [],
                            "localized_aliases": [],
                        },
                        "data_science": {
                            "label": "Data Science",
                            "strong_aliases": ["computing"],
                            "related_not_equivalent": [],
                            "localized_aliases": [],
                        },
                    },
                    "degrees": {},
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(module, "ONTOLOGY_PATH", bad)
        module.load_ontology.cache_clear()
        module._alias_index.cache_clear()
        try:
            with pytest.raises(ValueError, match="strong alias of both"):
                module.canonical_field("computing")
        finally:
            module.load_ontology.cache_clear()
            module._alias_index.cache_clear()

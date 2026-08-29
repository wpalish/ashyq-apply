"""The extractor and the eligibility model must know the same groups.

`restrictions.py` carried its own six-entry table of bloc names, separate from
the one in `app/domain/countries.py`. Two tables for one fact drift, and this
pair had: a page saying "open only to citizens of EFTA countries" or "nationals
of ASEAN member states" produced no restriction at all, so an award restricted
to four countries was presented as unrestricted.

That is the direction that matters. A missed restriction does not refuse a
student — it tells them an award is open when it is not, and they spend an
application on it.
"""
from __future__ import annotations

import pytest

from app.adapters.scholarship.restrictions import extract_restrictions
from app.domain.countries import BLOCS, canonical_bloc


@pytest.mark.parametrize("bloc", sorted(BLOCS))
def test_every_group_the_model_knows_is_recognised_in_a_sentence(bloc: str):
    text = f"The award is open only to citizens of {bloc}."
    found = extract_restrictions(text).blocs
    assert bloc in found, f"{bloc!r} was not recognised in {text!r}"


@pytest.mark.parametrize(
    "sentence,expected",
    [
        ("The award is open only to citizens of EFTA countries.", "EFTA"),
        ("Open only to nationals of ASEAN member states.", "ASEAN"),
        ("Restricted to citizens of EU/EEA countries.", "European Economic Area"),
        ("Open only to Commonwealth citizens.", "Commonwealth"),
        ("Reserved for nationals of the Nordic countries.", "Nordic countries"),
        ("Available only to Schengen area residents.", "Schengen area"),
    ],
)
def test_the_phrasings_pages_actually_use(sentence: str, expected: str):
    assert expected in extract_restrictions(sentence).blocs, sentence


def test_every_recognised_group_resolves_in_the_eligibility_model():
    """A restriction the extractor can name but the model cannot resolve is
    worse than not extracting it: it becomes an unanswerable condition on a
    real award."""
    text = " ".join(f"Open only to citizens of {b}." for b in BLOCS)
    for bloc in extract_restrictions(text).blocs:
        assert canonical_bloc(bloc) is not None, bloc


def test_a_group_word_without_a_restriction_is_not_one():
    """The guard the extractor already had, which must survive the change:
    naming a group is not restricting to it."""
    text = "The European Union funds part of this programme."
    assert extract_restrictions(text).blocs == []

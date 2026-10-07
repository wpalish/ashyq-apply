"""Offline control matrix: frozen matcher, initial proposal, final off/on."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import replay_aut_subject_phrase as loader
from app.adapters.search.ontology import load_ontology

ROOT = Path(__file__).resolve().parent
parent_proposal = ROOT.parent.parent / "subject-phrase.proposal.txt"
namespace = dict(vars(loader.discovery))
exec(parent_proposal.read_text(), namespace)
initial_proposal = namespace["matches_field_text"]
rows = []
concepts = load_ontology().fields
for key, concept in concepts.items():
    for alias in concept["strong_aliases"]:
        words = alias.split()
        if len(words) < 2:
            continue
        for variant, title, expected in [
            ("exact_alias", alias, True),
            ("alias_under_parent_degree", f"{alias.title()} Major - Bachelor of Other Subject", True),
            ("reversed_alias", "BSc " + " ".join(reversed(words)), False),
            ("split_alias", " Major - Bachelor of ".join(words), False),
        ]:
            fields = [concept["label"]]
            original = loader.legacy_matcher(title, fields)
            parent = initial_proposal(title, fields)
            with patch.object(loader.discovery, "SUBJECT_PHRASE_MATCH", False):
                off = loader.new_matcher(title, fields)
            with patch.object(loader.discovery, "SUBJECT_PHRASE_MATCH", True):
                on = loader.new_matcher(title, fields)
            assert off is original
            assert on is expected
            rows.append({"concept": key, "alias": alias, "variant": variant, "title": title,
                         "requested_fields": fields, "original": original, "initial_proposal": parent,
                         "final_off": off, "final_on": on, "expected_final_on": expected})
for title, fields, expected in [
    ("Computing Science Major - Bachelor of Computer and Information Sciences", ["computer science"], True),
    ("Business Informatics", ["computer science"], False),
    ("Cloud Computing", ["computer science"], False),
    ("Computing and Data Science", ["computer science"], False),
    ("Business Informatics", ["informatics"], True),
    ("Cloud Computing", ["computing"], True),
    ("CS", ["computer science"], False),
    ("CS", ["CS"], False),
    ("Computer and Information Science", ["computer science"], False),
    ("Computer Science and Engineering", ["computer science"], True),
]:
    with patch.object(loader.discovery, "SUBJECT_PHRASE_MATCH", False):
        off = loader.new_matcher(title, fields)
    with patch.object(loader.discovery, "SUBJECT_PHRASE_MATCH", True):
        on = loader.new_matcher(title, fields)
    original = loader.legacy_matcher(title, fields)
    assert off is original and on is expected
    rows.append({"variant": "explicit_policy_control", "title": title, "requested_fields": fields,
                 "original": original, "initial_proposal": initial_proposal(title, fields),
                 "final_off": off, "final_on": on, "expected_final_on": expected})
# Observe related titles without pretending a subject guard proves exact programme equivalence.
related = []
for key, concept in concepts.items():
    for title in concept.get("related_not_equivalent", []):
        with patch.object(loader.discovery, "SUBJECT_PHRASE_MATCH", True):
            on = loader.new_matcher(title, [concept["label"]])
        related.append({"concept": key, "title": title, "final_on_subject_match": on})
result = {"created_at_utc": datetime.now(UTC).isoformat(), "network_calls": 0, "provider_calls": 0,
          "ontology_concepts": len(concepts), "multiword_aliases": sum(len(a.split()) > 1 for c in concepts.values() for a in c["strong_aliases"]),
          "rows": rows, "related_title_observations": related,
          "parent_proposal_sha256": hashlib.sha256(parent_proposal.read_bytes()).hexdigest(),
          "current_proposed_source_sha256": hashlib.sha256((ROOT / "proposed/backend/app/adapters/discovery/live_discovery.py").read_bytes()).hexdigest(),
          "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "claim_scope": "Matcher controls only. Raw-own Computing/Informatics and longer explicit field combinations retain existing semantics; exact programme identity is not established here."}
(ROOT / "subject-phrase.control-matrix.offline.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"concepts": result["ontology_concepts"], "multiword_aliases": result["multiword_aliases"],
                  "controls": len(rows), "all_controls_passed": True, "related_observations": len(related)}, indent=2))

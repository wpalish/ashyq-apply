"""An attestation is evidence only if it identifies what was tested.

The generator accepted any JSON whose `sha` string matched HEAD and recorded
the container gate as PASS. Three things were wrong with that:

  - it trusted a hand-written file as though CI had produced it;
  - the SHA it matched against was `github.sha`, which on a `pull_request` is a
    synthetic merge commit, not the branch head — so an artifact named for
    `ba15bbb` was in fact built from merge commit `6a95c5bd`;
  - it recorded a bare "attested_sha" without saying which of the two it was.

The attestation now names `tested_sha`, `head_sha` and both trees. A working
copy can be compared against `head_tree`, which is the only one of the four
that exists outside the CI checkout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.release_evidence import attestation_gate

HEAD = "3a11fb2b7601b960cb09001b5bb30e7fba2ae98b"
TREE = "0df1e1cf2459f0c52006513e144cc22fc28a19c9"


def attestation(**overrides) -> dict:
    base = {
        "gate": "container_runtime",
        "command": "./scripts/compose_smoke.sh",
        "result": "success",
        "event": "pull_request",
        "tested_sha": "6a95c5bd0000000000000000000000000000dead",
        "head_sha": HEAD,
        "tested_tree": TREE,
        "head_tree": TREE,
        "run_url": "https://github.com/o/r/actions/runs/1",
    }
    base.update(overrides)
    return base


class TestWhatCountsAsAttested:
    def test_a_matching_head_tree_is_accepted(self, tmp_path: Path):
        gate = attestation_gate(attestation(), head_sha=HEAD, head_tree=TREE)
        assert gate["result"] == "pass"
        assert gate["head_sha"] == HEAD
        # The merge commit is recorded as what it is, not as the branch.
        assert gate["tested_sha"] != gate["head_sha"]

    def test_a_different_tree_is_refused(self):
        """The check that means something. A SHA can be copied into a file; the
        tree is what the code actually was."""
        gate = attestation_gate(attestation(), head_sha=HEAD, head_tree="0" * 40)
        assert gate["result"] == "not_run"
        assert "tree" in gate["detail"]

    def test_a_different_head_sha_is_refused(self):
        gate = attestation_gate(attestation(), head_sha="1" * 40, head_tree=TREE)
        assert gate["result"] == "not_run"

    def test_a_failing_smoke_step_is_recorded_as_a_failure(self):
        gate = attestation_gate(
            attestation(result="failure"), head_sha=HEAD, head_tree=TREE
        )
        assert gate["result"] == "fail"

    @pytest.mark.parametrize(
        "missing", ["result", "head_sha", "head_tree", "run_url", "tested_sha"]
    )
    def test_an_incomplete_attestation_is_refused(self, missing: str):
        """Absence of a required field is not a pass. Half an attestation
        describes half a test run."""
        payload = attestation()
        payload.pop(missing)
        gate = attestation_gate(payload, head_sha=HEAD, head_tree=TREE)
        assert gate["result"] == "not_run", missing

    def test_the_raw_attestation_is_kept_verbatim_with_a_digest(self):
        payload = attestation()
        gate = attestation_gate(payload, head_sha=HEAD, head_tree=TREE)
        assert gate["raw_attestation"] == payload
        assert len(gate["attestation_sha256"]) == 64
        # Recomputable by anyone holding the same bytes.
        import hashlib

        expected = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        assert gate["attestation_sha256"] == expected

    def test_a_hand_written_sha_alone_does_not_pass(self):
        """The original hole: matching one string was enough."""
        gate = attestation_gate(
            {"sha": HEAD, "result": "success"}, head_sha=HEAD, head_tree=TREE
        )
        assert gate["result"] == "not_run"

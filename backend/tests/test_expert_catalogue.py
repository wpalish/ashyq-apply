"""Catalogue allocation depends on identities; expert packets exclude seed facts."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from app.catalogue.importer import SEED_PATH, identity_key, stable_id
from evaluation.research.expert import catalogue as exporter
from evaluation.research.expert.__main__ import main
from evaluation.research.expert.catalogue import (
    DEFAULT_SPLIT_SEED,
    PILOT_IDENTITIES,
    PUBLIC_PROFILE,
    PublicCatalogue,
    build_catalogue_packet,
    build_catalogue_split,
    load_catalogue,
)
from evaluation.research.expert.packet import REQUEST_FIELDS, digest

SOURCE_SHA = "b" * 40


@pytest.fixture(scope="module")
def catalogue() -> PublicCatalogue:
    return load_catalogue(source_sha=SOURCE_SHA)


def capture_for(case_ids: list[str]) -> dict:
    return {
        "schema_version": "1",
        "pipeline_sha": SOURCE_SHA,
        "captured_at": "2026-10-04T00:00:00Z",
        "mode": "replay",
        "config": {
            "max_fetcher_calls_per_case": 60,
            "seconds_per_case": 120,
            "browser_enabled": False,
            "public_profile": deepcopy(PUBLIC_PROFILE),
        },
        "observations": [
            {
                "case_id": case_id,
                "ranked_urls": [],
                "programme_urls": [],
                "predictions": [],
                "error": "NO_SOURCE_READ",
                "telemetry": {
                    "http_fetches": 0,
                    "pdf_fetches": 0,
                    "browser_fetches": 0,
                    "latency_seconds": 0.01,
                },
            }
            for case_id in case_ids
        ],
    }


def test_actual_importer_runs_only_in_separate_memory_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_engine = exporter.create_engine
    real_import = exporter.import_catalogue
    engines = []
    imports = []

    def observed_engine(url):
        engines.append(url)
        return real_engine(url)

    def observed_import(session, document):
        imports.append(session.get_bind().url.database)
        return real_import(session, document)

    monkeypatch.setattr(exporter, "create_engine", observed_engine)
    monkeypatch.setattr(exporter, "import_catalogue", observed_import)
    actual = load_catalogue(source_sha=SOURCE_SHA)
    assert engines == ["sqlite:///:memory:"]
    assert imports == [":memory:"]
    assert len(actual.identities) == 501
    assert len(actual.seed_case_ids) == 500
    assert len(actual.extra_curated_case_ids) == 1
    assert actual.seed_sha256 == hashlib.sha256(SEED_PATH.read_bytes()).hexdigest()
    assert actual.seed_version == "2026-10-02/1.0"
    assert actual.source_sha == SOURCE_SHA


def test_loader_never_opens_configured_database(tmp_path: Path) -> None:
    configured_db = tmp_path / "must-not-open.sqlite"
    env = dict(os.environ, UNIMATCH_DATABASE_URL=f"sqlite:///{configured_db}")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from evaluation.research.expert.catalogue import load_catalogue; "
            f"print(len(load_catalogue(source_sha='{SOURCE_SHA}').identities))",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "501"
    assert not configured_db.exists()


def test_every_imported_identity_can_have_a_same_id_blinded_packet(
    catalogue: PublicCatalogue,
) -> None:
    case_ids = list(catalogue.case_ids)
    capture = capture_for(case_ids)
    packet = build_catalogue_packet(catalogue, capture, case_ids)
    assert {case["case_id"] for case in packet["cases"]} == set(case_ids)
    assert len(packet["cases"]) == 501
    assert packet["comparison_mode"] == "independent_full_budget"
    assert packet["public_profile"] == PUBLIC_PROFILE
    assert packet["baseline_budget"] == {
        "max_fetcher_calls": 60,
        "max_elapsed_ms": 120000,
        "browser_enabled": False,
        "max_search_queries": 6,
    }
    assert packet["capture_sha256"] == digest(capture)
    assert packet["catalogue"] == catalogue.provenance()
    for case in packet["cases"]:
        assert set(case) == {"case_id", "university", "domain", "request", "baseline"}
        assert set(case["request"]) == set(REQUEST_FIELDS)
        assert case["request"] == {
            "university": case["university"],
            "programme": None,
            "degree": "bachelor",
            "field": "computer science",
            "intake": "fall 2027",
            "population": None,
            "qualification": None,
            "academic_year": None,
        }
    assert any(case["domain"] is None for case in packet["cases"])


def test_projection_and_packet_never_copy_seed_hints_or_baseline_fact_payloads(
    tmp_path: Path,
) -> None:
    seed = json.loads(SEED_PATH.read_bytes())
    for row in seed["universities"]:
        row["tuition_usd_estimate"] = {"min": 1234567, "max": 2345678}
        row["ielts_hint"] = 987.5
        row["labels"] = [{"value": "SEALED_SEED_FACT_SENTINEL"}]
        row["proposals"] = [{"source_url": "https://secret-seed.example/fact"}]
    poisoned_seed = tmp_path / "seed.json"
    poisoned_seed.write_text(json.dumps(seed), encoding="utf-8")
    actual = load_catalogue(poisoned_seed, source_sha=SOURCE_SHA)
    capture = capture_for(list(actual.case_ids))
    for observation in capture["observations"]:
        observation["predictions"] = [
            {"value": "BASELINE_PREDICTION_SENTINEL", "evidence": {"excerpt": "signed"}}
        ]
        observation["page_outcomes"] = [{"detail": "BASELINE_ROUTE_SENTINEL"}]
        observation["proposals"] = [{"value": "BASELINE_PROPOSAL_SENTINEL"}]
        observation["telemetry"]["private_note"] = "TELEMETRY_SENTINEL"
    capture["config"]["answer"] = "CONFIG_ANSWER_SENTINEL"
    packet = build_catalogue_packet(actual, capture, list(actual.case_ids))
    serialized = json.dumps({"public_catalogue": asdict(actual), "packet": packet})
    for forbidden in (
        "SEALED_SEED_FACT_SENTINEL",
        "BASELINE_PREDICTION_SENTINEL",
        "BASELINE_ROUTE_SENTINEL",
        "BASELINE_PROPOSAL_SENTINEL",
        "TELEMETRY_SENTINEL",
        "CONFIG_ANSWER_SENTINEL",
        "1234567",
        "2345678",
        "987.5",
        '"tuition_usd_estimate"',
        '"registry_entry"',
        '"seed_snapshot"',
        '"programme_seeds"',
        '"labels"',
        '"proposals"',
        '"evidence"',
        '"excerpt"',
        '"value"',
    ):
        assert forbidden not in serialized
    assert all(case["baseline"]["prediction_count"] == 1 for case in packet["cases"])
    assert all(
        set(case["baseline"])
        == {"ranked_urls", "programme_urls", "prediction_count", "error", "telemetry"}
        for case in packet["cases"]
    )


@pytest.mark.parametrize("case_ids", [[], ["unknown"], ["duplicate", "duplicate"]])
def test_packet_rejects_empty_unknown_and_duplicate_ids(
    catalogue: PublicCatalogue, case_ids: list[str]
) -> None:
    with pytest.raises(ValueError, match="unique|Unknown"):
        build_catalogue_packet(catalogue, capture_for([]), case_ids)


def test_packet_requires_same_case_baseline_and_rejects_ambiguous_observations(
    catalogue: PublicCatalogue,
) -> None:
    first, second = catalogue.case_ids[:2]
    with pytest.raises(ValueError, match="Missing case or observation"):
        build_catalogue_packet(catalogue, capture_for([second]), [first])
    with pytest.raises(ValueError, match="Duplicate baseline"):
        build_catalogue_packet(catalogue, capture_for([first, first]), [first])
    with pytest.raises(ValueError, match="Unknown baseline"):
        build_catalogue_packet(catalogue, capture_for(["unknown"]), [first])
    with pytest.raises(ValueError, match="Unknown baseline"):
        build_catalogue_packet(catalogue, capture_for(["kaist"]), [first])


@pytest.mark.parametrize(
    "field,payload",
    [
        ("ranked_urls", [{"value": "FACT"}]),
        ("programme_urls", [{"excerpt": "FACT"}]),
        ("error", {"labels": "FACT"}),
        ("telemetry", {"http_fetches": {"fact": 3}}),
        ("predictions", {"value": "FACT"}),
    ],
)
def test_structured_payloads_cannot_hide_inside_baseline_allowlist_fields(
    catalogue: PublicCatalogue, field: str, payload: object
) -> None:
    case_id = catalogue.case_ids[0]
    capture = capture_for([case_id])
    capture["observations"][0][field] = payload
    with pytest.raises(ValueError, match="Baseline|baseline"):
        build_catalogue_packet(catalogue, capture, [case_id])


def test_packet_refuses_a_different_public_profile(catalogue: PublicCatalogue) -> None:
    case_id = catalogue.case_ids[0]
    capture = capture_for([case_id])
    capture["config"]["public_profile"]["intake_year"] = 2026
    with pytest.raises(ValueError, match="public profile differs"):
        build_catalogue_packet(catalogue, capture, [case_id])


def test_catalogue_packet_records_capture_query_budget(catalogue: PublicCatalogue) -> None:
    case_id = catalogue.case_ids[0]
    capture = capture_for([case_id])
    capture["config"]["max_search_queries_per_case"] = 3
    packet = build_catalogue_packet(catalogue, capture, [case_id])
    assert packet["baseline_budget"]["max_search_queries"] == 3


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_fetcher_calls_per_case", -1),
        ("max_fetcher_calls_per_case", True),
        ("seconds_per_case", float("inf")),
        ("seconds_per_case", 0),
        ("browser_enabled", "false"),
        ("max_search_queries_per_case", {"labels": 6}),
        ("max_search_queries_per_case", True),
        ("max_search_queries_per_case", 0),
    ],
)
def test_catalogue_packet_refuses_unbounded_or_malformed_baseline_configuration(
    catalogue: PublicCatalogue, field: str, value: object
) -> None:
    case_id = catalogue.case_ids[0]
    capture = capture_for([case_id])
    capture["config"][field] = value
    with pytest.raises(ValueError, match="Baseline"):
        build_catalogue_packet(catalogue, capture, [case_id])


def test_duplicate_and_unknown_ids_in_an_identity_export_are_rejected(
    catalogue: PublicCatalogue,
) -> None:
    duplicate = replace(catalogue, identities=(*catalogue.identities, catalogue.identities[0]))
    with pytest.raises(ValueError, match="Duplicate catalogue"):
        build_catalogue_split(duplicate)
    duplicate_seed = replace(
        catalogue, seed_case_ids=(*catalogue.seed_case_ids, catalogue.seed_case_ids[0])
    )
    with pytest.raises(ValueError, match="Duplicate seed"):
        build_catalogue_split(duplicate_seed)
    unknown = replace(catalogue, seed_case_ids=("unknown", *catalogue.seed_case_ids[1:]))
    with pytest.raises(ValueError, match="Unknown seed"):
        build_catalogue_split(unknown)


def test_split_covers_only_seed500_and_reserves_all_ten_public_pilot_names(
    catalogue: PublicCatalogue,
) -> None:
    manifest = build_catalogue_split(catalogue)
    dev, heldout = set(manifest["DEV"]), set(manifest["HELDOUT"])
    assert len(dev) == 350 and len(heldout) == 150
    assert dev.isdisjoint(heldout)
    assert dev | heldout == set(catalogue.seed_case_ids)
    assert manifest["excluded_curated_ids"] == list(catalogue.extra_curated_case_ids)
    assert set(manifest["excluded_curated_ids"]).isdisjoint(dev | heldout)
    expected_pilots = {
        pilot_id: stable_id(identity_key(name, country))
        for pilot_id, name, country in PILOT_IDENTITIES
    }
    assert {
        item["pilot_case_id"]: item["catalogue_case_id"] for item in manifest["pilot_reservations"]
    } == expected_pilots
    assert set(expected_pilots.values()) <= dev
    assert manifest["split_seed"] == DEFAULT_SPLIT_SEED
    assert manifest["split_seed_sha256"] == hashlib.sha256(DEFAULT_SPLIT_SEED.encode()).hexdigest()
    assert manifest["id_hashes"] == {
        "DEV": digest(sorted(dev)),
        "HELDOUT": digest(sorted(heldout)),
        "excluded_curated": digest(list(catalogue.extra_curated_case_ids)),
    }
    assert manifest["catalogue"] == catalogue.provenance()
    serialized = json.dumps(manifest)
    for forbidden in (
        '"labels"',
        '"value"',
        '"programme_urls"',
        '"proposals"',
        '"request"',
        "https://",
    ):
        assert forbidden not in serialized


def test_manifest_records_exact_deviation_from_sha256_seeded_allocation(
    catalogue: PublicCatalogue,
) -> None:
    def rank(case_id):
        message = json.dumps(
            [DEFAULT_SPLIT_SEED, case_id], ensure_ascii=False, separators=(",", ":")
        )
        return hashlib.sha256(message.encode()).hexdigest(), case_id

    unconstrained = set(sorted(catalogue.seed_case_ids, key=rank)[:350])
    manifest = build_catalogue_split(catalogue)
    dev = set(manifest["DEV"])
    reserved = {item["catalogue_case_id"] for item in manifest["pilot_reservations"]}
    deviation = manifest["allocation_deviation"]
    assert deviation["moved_from_seeded_HELDOUT_to_DEV"] == sorted(reserved - unconstrained)
    assert deviation["moved_from_seeded_DEV_to_HELDOUT"] == sorted(unconstrained - dev)
    assert len(deviation["moved_from_seeded_HELDOUT_to_DEV"]) == len(
        deviation["moved_from_seeded_DEV_to_HELDOUT"]
    )
    assert deviation["heldout_source_facts_used"] is False


def test_split_is_stable_under_identity_reordering_and_varies_with_seed(
    catalogue: PublicCatalogue,
) -> None:
    expected = build_catalogue_split(catalogue)
    reordered = replace(
        catalogue,
        identities=tuple(reversed(catalogue.identities)),
        seed_case_ids=tuple(reversed(catalogue.seed_case_ids)),
    )
    assert build_catalogue_split(reordered) == expected
    changed = build_catalogue_split(catalogue, "another-owner-frozen-seed")
    assert changed["HELDOUT"] != expected["HELDOUT"]
    assert changed["pilot_reservations"] == expected["pilot_reservations"]
    assert all(
        item["catalogue_case_id"] in changed["DEV"] for item in changed["pilot_reservations"]
    )


def test_reordering_seed_rows_changes_source_hash_but_not_allocation(
    catalogue: PublicCatalogue, tmp_path: Path
) -> None:
    document = json.loads(SEED_PATH.read_bytes())
    document["universities"].reverse()
    seed = tmp_path / "reordered.json"
    seed.write_text(json.dumps(document), encoding="utf-8")
    reordered = load_catalogue(seed, source_sha=SOURCE_SHA)
    actual, expected = build_catalogue_split(reordered), build_catalogue_split(catalogue)
    assert actual["DEV"] == expected["DEV"]
    assert actual["HELDOUT"] == expected["HELDOUT"]
    assert actual["allocation_deviation"] == expected["allocation_deviation"]
    assert actual["catalogue"]["identity_sha256"] == expected["catalogue"]["identity_sha256"]
    assert actual["catalogue"]["seed_sha256"] != expected["catalogue"]["seed_sha256"]


def test_catalogue_tools_do_not_read_reviewed_answers_or_identity_bindings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_bytes, real_text = Path.read_bytes, Path.read_text
    reads = []

    def check(path):
        reads.append(str(path))
        assert "/evaluation/research/data/" not in str(path)
        assert "/expert/data/" not in str(path)

    def guarded_bytes(path):
        check(path)
        return real_bytes(path)

    def guarded_text(path, *args, **kwargs):
        check(path)
        return real_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_bytes)
    monkeypatch.setattr(Path, "read_text", guarded_text)
    actual = load_catalogue(source_sha=SOURCE_SHA)
    split = build_catalogue_split(actual)
    case_id = split["HELDOUT"][0]
    packet = build_catalogue_packet(actual, capture_for([case_id]), [case_id])
    assert packet["cases"][0]["case_id"] == case_id
    assert reads


def test_extra_curated_identity_is_preparable_and_not_in_split(catalogue: PublicCatalogue) -> None:
    case_id = catalogue.extra_curated_case_ids[0]
    packet = build_catalogue_packet(catalogue, capture_for([case_id]), [case_id])
    assert packet["cases"][0]["university"] == "Nazarbayev University"
    assert packet["cases"][0]["domain"] == "nu.edu.kz"
    split = build_catalogue_split(catalogue)
    assert case_id not in split["DEV"] + split["HELDOUT"]


def test_catalogue_cli_writes_packet_and_split_offline(
    catalogue: PublicCatalogue, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    case_id = catalogue.extra_curated_case_ids[0]
    capture_path = tmp_path / "capture.json"
    capture_path.write_text(json.dumps(capture_for([case_id])), encoding="utf-8")
    packet_path, manifest_path = tmp_path / "nested/packet.json", tmp_path / "nested/split.json"
    main(
        [
            "prepare-catalogue",
            "--capture",
            str(capture_path),
            "--case",
            case_id,
            "--source-sha",
            SOURCE_SHA,
            "--out",
            str(packet_path),
        ]
    )
    packet = json.loads(packet_path.read_text())
    assert packet["cases"][0]["case_id"] == case_id
    assert f"packet sha256 {digest(packet)}" in capsys.readouterr().out
    main(["split-catalogue", "--source-sha", SOURCE_SHA, "--out", str(manifest_path)])
    manifest = json.loads(manifest_path.read_text())
    assert manifest == build_catalogue_split(catalogue)
    assert "350 DEV/150 HELDOUT" in capsys.readouterr().out


@pytest.mark.parametrize(
    "bad", ["unknown", "duplicate", "missing", "observation_duplicate", "profile", "sha"]
)
def test_prepare_catalogue_cli_invalid_inputs_have_no_output(
    catalogue: PublicCatalogue, tmp_path: Path, bad: str
) -> None:
    case_id = catalogue.case_ids[0]
    capture = capture_for([case_id])
    requested = [case_id]
    source_sha = SOURCE_SHA
    if bad == "unknown":
        requested = ["unknown"]
    elif bad == "duplicate":
        requested.append(case_id)
    elif bad == "missing":
        capture["observations"] = []
    elif bad == "observation_duplicate":
        capture["observations"].append(deepcopy(capture["observations"][0]))
    elif bad == "profile":
        capture["config"]["public_profile"]["level"] = "master"
    else:
        source_sha = "invalid"
    capture_path, output = tmp_path / "capture.json", tmp_path / "packet.json"
    capture_path.write_text(json.dumps(capture), encoding="utf-8")
    argv = [
        "prepare-catalogue",
        "--capture",
        str(capture_path),
        "--out",
        str(output),
        "--source-sha",
        source_sha,
    ]
    for requested_id in requested:
        argv.extend(["--case", requested_id])
    with pytest.raises(SystemExit) as failed:
        main(argv)
    assert failed.value.code == 2
    assert not output.exists()


def test_split_catalogue_cli_invalid_seed_has_no_output(tmp_path: Path) -> None:
    output = tmp_path / "manifest.json"
    with pytest.raises(SystemExit) as failed:
        main(
            [
                "split-catalogue",
                "--split-seed",
                " ",
                "--source-sha",
                SOURCE_SHA,
                "--out",
                str(output),
            ]
        )
    assert failed.value.code == 2
    assert not output.exists()

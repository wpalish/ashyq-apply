"""NN-1a: the importer reads only a reviewer-signed native-name overlay.

``app/catalogue/catalogue_native_names.signed.json`` is absent today, so every
seed record imports byte for byte as before. When present, an accepted row puts
its ``native_name`` list on the seed record, which the identity gate's branch
(ii) (``catalogue.discovery._native_name_match``) already reads. A row without
``review.decision = "accept"``, without a seed id, or signed for another name is
ignored. The proposals file under ``evaluation/`` is never read by the product.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.catalogue import importer
from app.catalogue.importer import SEED_PATH, identity_key, import_catalogue, stable_id
from app.db import create_all_for_tests
from app.models import University, UniversityObservation
from evaluation.research.wikidata_domains import HELDOUT_SEED_IDS

SEED = json.loads(SEED_PATH.read_text(encoding="utf-8"))
#: A German row that is not one of the held-out institutions.
ROW = next(
    r
    for r in SEED["universities"]
    if r["country"] == "Germany" and r["seed_id"] not in HELDOUT_SEED_IDS
)


def _session_with(monkeypatch, overlay: Path) -> Session:
    monkeypatch.setattr(importer, "NATIVE_NAMES_PATH", overlay)
    engine = create_engine("sqlite://")
    create_all_for_tests(engine)
    session = Session(engine)
    import_catalogue(session)
    session.commit()
    return session


def _record(session: Session, row: dict[str, Any]) -> dict[str, Any]:
    uni = session.get(University, stable_id(identity_key(row["name"], row["country"])))
    assert uni is not None
    return (uni.seed_snapshot or {})["record"]


def _overlay(tmp_path: Path, *rows: dict[str, Any]) -> Path:
    path = tmp_path / "catalogue_native_names.signed.json"
    path.write_text(json.dumps({"proposals": list(rows)}, ensure_ascii=False), encoding="utf-8")
    return path


def _row(decision: str | None, **overrides: Any) -> dict[str, Any]:
    return {
        "seed_id": ROW["seed_id"],
        "name": ROW["name"],
        "proposed_native_names": ["Synthetische Universität", "  "],
        "review": {"decision": decision, "reviewer": "owner", "note": None},
        **overrides,
    }


def test_the_signed_overlay_is_absent_today() -> None:
    assert importer.NATIVE_NAMES_PATH.name == "catalogue_native_names.signed.json"
    assert importer.NATIVE_NAMES_PATH.parent == SEED_PATH.parent
    assert not importer.NATIVE_NAMES_PATH.exists()
    assert importer.signed_native_names() == {}


def test_without_an_overlay_the_import_is_identical(monkeypatch, tmp_path) -> None:
    session = _session_with(monkeypatch, tmp_path / "absent.json")
    try:
        record = _record(session, ROW)
        assert record == ROW
        assert not any(
            "native_name" in (o.payload.get("record") or {})
            for o in session.scalars(select(UniversityObservation))
        )
    finally:
        session.close()


def test_an_accepted_row_puts_its_native_names_on_the_record(monkeypatch, tmp_path) -> None:
    session = _session_with(monkeypatch, _overlay(tmp_path, _row("accept")))
    try:
        record = _record(session, ROW)
        assert record["native_name"] == ["Synthetische Universität"]
        assert {k: v for k, v in record.items() if k != "native_name"} == ROW
        # Every other record is untouched.
        other = next(r for r in SEED["universities"] if r["seed_id"] != ROW["seed_id"])
        assert "native_name" not in _record(session, other)
    finally:
        session.close()
    assert "native_name" not in ROW  # the seed document is never written


@pytest.mark.parametrize(
    "row",
    [
        _row(None),
        _row("reject"),
        _row("accept", seed_id=None),
        _row("accept", name="Another University"),
        _row("accept", proposed_native_names=[]),
        _row("accept", proposed_native_names=["x" * 301]),
    ],
    ids=["unreviewed", "rejected", "no-seed-id", "another-name", "no-names", "too-long"],
)
def test_a_row_that_is_not_an_accepted_signature_is_ignored(monkeypatch, tmp_path, row) -> None:
    session = _session_with(monkeypatch, _overlay(tmp_path, row))
    try:
        assert "native_name" not in _record(session, ROW)
    finally:
        session.close()

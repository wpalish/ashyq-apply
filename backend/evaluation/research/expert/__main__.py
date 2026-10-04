"""Prepare blinded packets and validate expert traces without network access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .catalogue import (
    DEFAULT_SPLIT_SEED,
    SEED_PATH,
    build_catalogue_packet,
    build_catalogue_split,
    load_catalogue,
)
from .diagnose import diagnose
from .hypotheses import validate_hypotheses
from .models import validate_trace
from .packet import build_packet, digest


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="export public request and baseline observation")
    prepare.add_argument("--dataset", type=Path, required=True)
    prepare.add_argument("--capture", type=Path, required=True)
    prepare.add_argument("--case", action="append", required=True)
    prepare.add_argument("--out", type=Path, required=True)
    catalogue = commands.add_parser(
        "prepare-catalogue", help="export public catalogue requests and same-ID baselines offline"
    )
    catalogue.add_argument("--seed", type=Path, default=SEED_PATH)
    catalogue.add_argument("--source-sha", help="full source revision; defaults to local Git HEAD")
    catalogue.add_argument("--capture", type=Path, required=True)
    catalogue.add_argument("--case", action="append", required=True)
    catalogue.add_argument("--out", type=Path, required=True)
    split = commands.add_parser(
        "split-catalogue", help="freeze 350 DEV/150 HELDOUT seed IDs, with the ten pilots in DEV"
    )
    split.add_argument("--seed", type=Path, default=SEED_PATH)
    split.add_argument("--source-sha", help="full source revision; defaults to local Git HEAD")
    split.add_argument("--split-seed", default=DEFAULT_SPLIT_SEED)
    split.add_argument("--out", type=Path, required=True)
    validate = commands.add_parser("validate", help="check a submitted expert trace")
    validate.add_argument("--packet", type=Path, required=True)
    validate.add_argument("--trace", type=Path, required=True)
    validate.add_argument("--logs-dir", type=Path, help="verify the bytes of every raw tool log")
    diagnostics = commands.add_parser(
        "diagnose", help="compare sealed gold with published measurements"
    )
    diagnostics.add_argument("--dataset", type=Path, required=True)
    diagnostics.add_argument("--capture", type=Path, required=True)
    diagnostics.add_argument("--probe", type=Path, required=True)
    diagnostics.add_argument("--registry", type=Path)
    diagnostics.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        packet = build_packet(read_json(args.dataset), read_json(args.capture), args.case)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Wrote {len(packet['cases'])} cases; packet sha256 {digest(packet)}")
    elif args.command in {"prepare-catalogue", "split-catalogue"}:
        try:
            public_catalogue = load_catalogue(args.seed, source_sha=args.source_sha)
            if args.command == "prepare-catalogue":
                artifact = build_catalogue_packet(
                    public_catalogue, read_json(args.capture), args.case
                )
            else:
                artifact = build_catalogue_split(public_catalogue, args.split_seed)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            parser.error(str(exc))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if args.command == "prepare-catalogue":
            print(
                f"Wrote {len(artifact['cases'])} catalogue cases; packet sha256 {digest(artifact)}"
            )
        else:
            print(
                f"Wrote {len(artifact['DEV'])} DEV/{len(artifact['HELDOUT'])} HELDOUT IDs; "
                f"manifest sha256 {digest(artifact)}"
            )
    elif args.command == "validate":
        trace = validate_trace(
            read_json(args.trace), read_json(args.packet), logs_dir=args.logs_dir
        )
        level = "logs matched" if args.logs_dir else "shape only; logs not checked"
        print(
            f"Valid {level} for {trace.case_id}: {len(trace.actions)} actions; evidence unreviewed"
        )
    else:
        report = diagnose(read_json(args.dataset), read_json(args.capture), read_json(args.probe))
        if args.registry:
            validate_hypotheses(read_json(args.registry), report)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Wrote {len(report['records'])} measured-case diagnostics")


if __name__ == "__main__":
    main()

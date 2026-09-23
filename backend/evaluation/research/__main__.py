"""Offline by default: score a frozen output without importing the live runner."""

import argparse
from pathlib import Path

from .metrics import dump_report, score
from .schema import Capture, Dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--allow-drafts", action="store_true")
    args = parser.parse_args()
    dataset = Dataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
    capture = Capture.model_validate_json(args.capture.read_text(encoding="utf-8"))
    report = score(dataset, capture, allow_drafts=args.allow_drafts)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(dump_report(report), encoding="utf-8")
    print(dump_report(report["metrics"]))


if __name__ == "__main__":
    main()

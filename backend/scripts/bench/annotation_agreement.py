"""Create a blinded dual-review template and summarize categorical agreement.

This utility never assigns labels, adjudicates disagreements, or filters data.
It uses only the Python standard library so the annotation workflow is usable
offline. Existing exposed Belebele data remain development-only regardless of
annotation completion.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

FIELDS = {
    "same_meaning": {"yes", "partly", "no"},
    "answerable_same_gold": {"yes", "no"},
    "natural_hinglish": {"1", "2", "3"},
}
TEXT_FIELDS = ("notes",)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        rows = list(reader)
    if "id" not in reader.fieldnames:
        raise ValueError("CSV must contain an id column")
    ids = [row.get("id", "").strip() for row in rows]
    if any(not item_id for item_id in ids):
        raise ValueError("CSV contains a blank id")
    duplicates = sorted(item_id for item_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate ids: {duplicates[:10]}")
    return list(reader.fieldnames), rows


def template(source: Path, destination: Path) -> None:
    fields, rows = read_rows(source)
    for field in FIELDS:
        for suffix in ("reviewer_a", "reviewer_b", "adjudicated"):
            fields.append(f"{suffix}_{field}")
    for suffix in ("reviewer_a", "reviewer_b"):
        fields.append(f"{suffix}_notes")
    fields.append("adjudication_notes")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def assignment_template(source: Path, destination: Path) -> None:
    _, rows = read_rows(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "primary_reviewer", "second_reviewer", "overlap", "assignment_notes"]
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({"id": row["id"], "overlap": ""})


def kappa(labels_a: list[str], labels_b: list[str], categories: set[str]) -> dict:
    n = len(labels_a)
    if not n:
        return {"n_paired": 0, "observed_agreement": None, "expected_agreement": None, "cohen_kappa": None}
    observed = sum(a == b for a, b in zip(labels_a, labels_b, strict=True)) / n
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)
    expected = sum((counts_a[label] / n) * (counts_b[label] / n) for label in categories)
    value = (observed - expected) / (1 - expected) if not math.isclose(expected, 1.0) else None
    confusion = {a: {b: 0 for b in sorted(categories)} for a in sorted(categories)}
    for a, b in zip(labels_a, labels_b, strict=True):
        confusion[a][b] += 1
    return {
        "n_paired": n,
        "observed_agreement": observed,
        "expected_agreement": expected,
        "cohen_kappa": value,
        "labels": sorted(categories),
        "confusion_reviewer_a_rows_b_columns": confusion,
        "counts_reviewer_a": {label: counts_a[label] for label in sorted(categories)},
        "counts_reviewer_b": {label: counts_b[label] for label in sorted(categories)},
    }


def summarize(path: Path) -> dict:
    fields, rows = read_rows(path)
    results = {}
    for field, categories in FIELDS.items():
        columns = {name: f"{name}_{field}" for name in ("reviewer_a", "reviewer_b", "adjudicated")}
        absent = [column for column in columns.values() if column not in fields]
        if absent:
            raise ValueError(f"Missing annotation columns: {absent}")

        valid_counts = {name: Counter() for name in columns}
        invalid_counts = {name: 0 for name in columns}
        blank_counts = {name: 0 for name in columns}
        paired_a: list[str] = []
        paired_b: list[str] = []
        for row in rows:
            normalized = {}
            for name, column in columns.items():
                label = (row.get(column) or "").strip().lower()
                normalized[name] = label
                if not label:
                    blank_counts[name] += 1
                elif label not in categories:
                    invalid_counts[name] += 1
                else:
                    valid_counts[name][label] += 1
            if normalized["reviewer_a"] in categories and normalized["reviewer_b"] in categories:
                paired_a.append(normalized["reviewer_a"])
                paired_b.append(normalized["reviewer_b"])

        results[field] = {
            "allowed_labels": sorted(categories),
            "valid_counts": {name: dict(counter) for name, counter in valid_counts.items()},
            "blank_rows": blank_counts,
            "invalid_rows": invalid_counts,
            "independent_pair_agreement": kappa(paired_a, paired_b, categories),
        }

    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(path),
        "input_sha256": sha256(path),
        "scope": "Descriptive development-data annotation agreement only; no row filtering or adjudication.",
        "historical_exposure_warning": "The existing 500 Belebele rows are exposed development data, not a fresh confirmatory test.",
        "row_count": len(rows),
        "fields": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--template", type=Path, help="Create a dual-review template from an input CSV.")
    mode.add_argument("--assignment-template", type=Path, help="Create a blank reviewer assignment sheet from an input CSV.")
    mode.add_argument("--input", type=Path, help="Summarize a completed dual-review CSV.")
    parser.add_argument("--output", type=Path, required=True, help="Destination CSV template or JSON report.")
    args = parser.parse_args()
    if args.template:
        template(args.template, args.output)
        print(f"Wrote blank dual-review template: {args.output}")
        return
    if args.assignment_template:
        assignment_template(args.assignment_template, args.output)
        print(f"Wrote blank reviewer assignment sheet: {args.output}")
        return
    report = summarize(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": report["row_count"], "report": str(args.output)}))


if __name__ == "__main__":
    main()

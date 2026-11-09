"""Prepare an explicitly exposed, development-only Belebele family split.

This does not create fresh data or a confirmatory test set. The current source
sheet has 500 known-exposed rows; source families use exact normalized English
passage hashes only, so near-duplicate grouping still needs human audit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from build_source_splits import build


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "docs/annotation/belebele_cm_verify_500.csv"
OUTPUT = ROOT / "backend/data/bench/belebele_exposed_dev_only"
MODEL_FIELDS = "id,source_passage,question,options,hinglish_passage,hinglish_question,hinglish_options"


def normalize_passage(text: str) -> str:
    return " ".join(text.split()).casefold()


def prepare(source: Path = SOURCE, output: Path = OUTPUT) -> dict:
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 500 or len({row["id"] for row in rows}) != 500:
        raise ValueError("Expected exactly 500 uniquely identified source rows")

    records = []
    for row in rows:
        digest = hashlib.sha256(normalize_passage(row["english_passage"]).encode("utf-8")).hexdigest()
        records.append({
            "id": row["id"],
            "source_family_id": f"exact-{digest}",
            "historically_exposed": True,
            "gold": row["gold"],
            "source_passage": row["english_passage"],
            "question": row["english_question"],
            "options": row["english_options"],
            "hinglish_passage": row["hinglish_passage"],
            "hinglish_question": row["hinglish_question"],
            "hinglish_options": row["hinglish_options"],
        })

    output.mkdir(parents=True, exist_ok=True)
    input_path = output / "input_records.jsonl"
    with input_path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    args = argparse.Namespace(
        input=input_path,
        output_dir=output,
        labels_output=output / "sealed_labels_empty.jsonl",
        id_field="id",
        family_field="source_family_id",
        exposed_field="historically_exposed",
        gold_field="gold",
        model_fields=MODEL_FIELDS,
        source_text_field="source_passage",
        seed="exposed-only-no-random-allocation",
        train_share=0.4,
        dev_share=0.2,
        sealed_share=0.4,
    )
    result = build(args)
    (output / "STATUS.txt").write_text(
        "EXPOSED DEVELOPMENT ONLY. All 500 inputs are historically exposed. "
        "No sealed or confirmatory set was created. Exact source hashes do not "
        "replace human near-duplicate/source-family and license review.\n",
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    print(json.dumps(prepare(), ensure_ascii=False, indent=2))

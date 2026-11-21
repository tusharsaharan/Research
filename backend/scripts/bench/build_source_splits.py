"""Split a reviewed JSONL corpus by source family with exposed groups quarantined.

This is a preparation utility, not a source-discovery system. A human-curated
``source_family_id`` must group exact/near-duplicate sources and all variants.
Records marked historically exposed are forced out of the sealed split. Gold
labels are written separately from sealed model inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, start=1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on line {line_no}: {exc}") from exc
    return records


def canonical_hash(value: str) -> str:
    normalized = " ".join(value.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def allocation(group_id: str, seed: str, shares: list[tuple[str, float]]) -> str:
    value = int(hashlib.sha256(f"{seed}|{group_id}".encode("utf-8")).hexdigest(), 16) / 2**256
    cumulative = 0.0
    for name, share in shares:
        cumulative += share
        if value < cumulative:
            return name
    return shares[-1][0]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build(args: argparse.Namespace) -> dict:
    source = args.input.resolve()
    input_records = read_jsonl(source)
    if not input_records:
        raise ValueError("Input JSONL has no records")

    required = {args.id_field, args.family_field, args.exposed_field, args.gold_field}
    model_fields = [field.strip() for field in args.model_fields.split(",") if field.strip()]
    if not model_fields or args.id_field not in model_fields:
        raise ValueError("--model-fields must be a comma-separated allowlist containing --id-field")
    forbidden_names = {"gold", "gold_answer", "correct_answer", "correct_option", "label", "labels", "target"}
    if any(field.casefold() in forbidden_names or field == args.gold_field for field in model_fields):
        raise ValueError("--model-fields contains a gold/label field; sealed inputs must use a reviewed allowlist")
    seen: set[str] = set()
    group_exposure: dict[str, bool] = {}
    groups: dict[str, list[dict]] = defaultdict(list)
    source_hashes: dict[str, set[str]] = defaultdict(set)
    for index, row in enumerate(input_records, start=1):
        missing = sorted(field for field in required if field not in row)
        missing_model = sorted(field for field in model_fields if field not in row)
        missing.extend(missing_model)
        if missing:
            raise ValueError(f"Record {index} missing required fields: {missing}")
        item_id = str(row[args.id_field]).strip()
        family = str(row[args.family_field]).strip()
        if not item_id or not family:
            raise ValueError(f"Record {index} has blank id or source-family id")
        if item_id in seen:
            raise ValueError(f"Duplicate item id: {item_id}")
        seen.add(item_id)
        exposure_value = row[args.exposed_field]
        if not isinstance(exposure_value, bool):
            raise ValueError(f"{args.exposed_field} must be a JSON boolean for {item_id}")
        prior = group_exposure.setdefault(family, exposure_value)
        if prior != exposure_value:
            raise ValueError(f"Source family has mixed exposure status: {family}")
        if args.source_text_field:
            if not isinstance(row.get(args.source_text_field), str):
                raise ValueError(f"Missing/non-text {args.source_text_field} for {item_id}")
            source_hashes[family].add(canonical_hash(row[args.source_text_field]))
        groups[family].append(row)

    shares = [("train", args.train_share), ("development", args.dev_share), ("sealed", args.sealed_share)]
    if any(share <= 0 for _, share in shares) or abs(sum(share for _, share in shares) - 1.0) > 1e-9:
        raise ValueError("Train/development/sealed shares must each be > 0 and sum to 1")

    destinations: dict[str, list[dict]] = {name: [] for name, _ in shares}
    forced_exposed: list[dict] = []
    family_split: dict[str, str] = {}
    for family, records in sorted(groups.items()):
        if group_exposure[family]:
            split = "development"
            forced_exposed.extend(records)
        else:
            split = allocation(family, args.seed, shares)
        family_split[family] = split
        destinations[split].extend(records)

    all_ids = {str(row[args.id_field]) for rows in destinations.values() for row in rows}
    if all_ids != seen:
        raise AssertionError("Internal error: split output lost or duplicated records")
    sealed_families = {str(row[args.family_field]) for row in destinations["sealed"]}
    if any(group_exposure[family] for family in sealed_families):
        raise AssertionError("Internal error: exposed source family reached sealed split")

    output_dir = args.output_dir.resolve()
    input_path = output_dir / "sealed_inputs.jsonl"
    labels_path = args.labels_output.resolve()
    manifest_path = output_dir / "splits_manifest.json"
    id_field, gold_field = args.id_field, args.gold_field
    sealed_inputs = [{key: row[key] for key in model_fields} for row in destinations["sealed"]]
    sealed_labels = [{id_field: row[id_field], gold_field: row[gold_field]} for row in destinations["sealed"]]
    write_jsonl(output_dir / "train.jsonl", destinations["train"])
    write_jsonl(output_dir / "development.jsonl", destinations["development"])
    write_jsonl(input_path, sealed_inputs)
    write_jsonl(labels_path, sealed_labels)

    split_summary = {}
    for name, rows in destinations.items():
        families = {str(row[args.family_field]) for row in rows}
        split_summary[name] = {"items": len(rows), "source_families": len(families)}
    manifest = {
        "protocol": "source-family hash allocation; historically exposed families forced to development",
        "input_path": str(source),
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "id_field": id_field,
        "source_family_field": args.family_field,
        "historical_exposure_field": args.exposed_field,
        "gold_field": gold_field,
        "sealed_model_input_allowlist": model_fields,
        "seed": args.seed,
        "requested_shares_for_unexposed_families": dict(shares),
        "actual_counts": split_summary,
        "historically_exposed_families_forced_to_development": sum(group_exposure.values()),
        "sealed_exposed_families": 0,
        "sealed_inputs_path": str(input_path),
        "sealed_labels_path": str(labels_path),
        "sealed_inputs_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "sealed_labels_sha256": hashlib.sha256(labels_path.read_bytes()).hexdigest(),
        "exact_normalized_source_hashes_per_family": {
            family: sorted(hashes) for family, hashes in sorted(source_hashes.items())
        },
        "warning": "All source_family_id assignments require human near-duplicate/source audit. Keep sealed labels outside development access. This utility cannot establish freshness or licensing.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"manifest": str(manifest_path), "splits": split_summary}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--labels-output", type=Path, required=True, help="Custodian-controlled path outside normal development access")
    parser.add_argument("--id-field", default="id")
    parser.add_argument("--family-field", default="source_family_id")
    parser.add_argument("--exposed-field", default="historically_exposed")
    parser.add_argument("--gold-field", default="gold")
    parser.add_argument("--model-fields", required=True, help="Comma-separated sealed-input allowlist, e.g. id,source_passage,question,options")
    parser.add_argument("--source-text-field", default="source_passage")
    parser.add_argument("--seed", required=True, help="Frozen seed identifier; no default is provided")
    parser.add_argument("--train-share", type=float, required=True)
    parser.add_argument("--dev-share", type=float, required=True)
    parser.add_argument("--sealed-share", type=float, required=True)
    args = parser.parse_args()
    result = build(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Verify saved scale-up evidence and produce a compact, reproducible research review."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from grade import extract_letter
from local_qwen_campaign import digest, fingerprint


def records(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def review(data):
    from tokenizers import Tokenizer

    def read(name):
        return json.loads((data / name).read_text(encoding="utf-8"))
    report, stress, manifest = read("report.json"), read("stress_report.json"), read("manifest.json")
    state, workflow = read("state.json"), read("workflow.json")
    assert report["complete"] and stress["complete"] and workflow["status"] == "complete"
    for files in (report["files"], stress["sources"], manifest["files"]):
        for name, expected in files.items():
            assert digest(data / name) == expected, name
    tokenizer = Tokenizer.from_file(str(data / "tokenizer.json"))
    inputs = {r["uid"]: r for r in records(data / "inputs.jsonl")}
    expected = {uid + "|" + method for uid in inputs for method in manifest["methods"]}
    variants = {}
    for v in records(data / "variants.jsonl"):
        assert v["key"] not in variants
        variants[v["key"]] = v
        actual = len(tokenizer.encode(v["text"], add_special_tokens=False).ids)
        original = len(tokenizer.encode(inputs[v["uid"]]["context"], add_special_tokens=False).ids)
        assert actual == v["actual_tokens"] and original == v["original_tokens"]
        rate = 1 if v["method"] == "original" else float(v["method"].split("@")[1])
        assert v["target_tokens"] == (original if rate == 1 else max(1, math.floor(rate * original)))
        assert v["budget_met"] == (actual <= v["target_tokens"])
    assert set(variants) == expected
    counts, scores, invalid, errors = Counter(), Counter(), Counter(), Counter()
    seen, prompts = set(), {}
    for answer in records(data / "answers.jsonl"):
        key = (answer["model"], answer["key"])
        assert key not in seen and answer["config"] == fingerprint(manifest)
        assert answer["key"] in expected and answer["model"] in manifest["models"]
        seen.add(key)
        group = (answer["model"], answer["method"])
        counts[group] += 1
        scores[group] += extract_letter(answer["content"]) == inputs[answer["uid"]]["gold"]
        invalid[group] += extract_letter(answer["content"]) is None
        prompt_key = (answer["model"], answer["prompt_sha256"])
        assert prompts.setdefault(prompt_key, answer["content"]) == answer["content"]
        if answer["response"].get("generation_error"):
            assert answer["content"] == ""
            errors[answer["model"]] += 1
    assert len(seen) == len(expected) * len(manifest["models"])
    for model, methods in report["models"].items():
        assert state["models"][model]["status"] == "complete"
        assert any(g["size_vram"] > 0 for g in state["models"][model]["gpu"])
        for method, saved in methods.items():
            group = model, method
            assert counts[group] == len(inputs) == saved["n"]
            assert abs(scores[group] / counts[group] - saved["accuracy"]) < 1e-12
            assert invalid[group] == saved["invalid"]
    stress_inputs = {r["uid"]: r for r in records(data / "stress_inputs.jsonl")}
    totals, punctuation, examples, stress_seen = defaultdict(Counter), Counter(), [], set()
    guard = re.compile(r"\b(?:nahi|nahin|nhi|not|never|no|\d+)\b")
    for v in records(data / "stress_variants.jsonl"):
        identity = v["uid"], v["method"], v["rate"]
        assert identity not in stress_seen
        stress_seen.add(identity)
        source = stress_inputs[v["uid"]]
        assert v["stratum"] == source["stratum"]
        before, after = Counter(guard.findall(source["context"].lower())), Counter(guard.findall(v["text"].lower()))
        lost = sum((before - after).values())
        assert lost == v["lost_guard_occurrences"]
        key = f"{v['stratum']}|{v['method']}@{v['rate']}"
        totals[key].update(
            items=1,
            budget_misses=int(not v["budget_met"]),
            empty=int(not v["text"]),
            clipped=int(v["detail"]["budget_enforced"]),
            guard_occurrences=sum(before.values()),
            lost_guard_occurrences=lost,
            original_tokens=v["original_tokens"],
            output_tokens=v["actual_tokens"],
        )
        punctuation[key] += bool(v["text"]) and not re.search(r"[^\W_]", v["text"])
        if (
            len(examples) < 3
            and v["method"] == "bqwen35b_span"
            and v["rate"] == 0.33
            and v["stratum"].startswith("original")
            and lost
        ):
            examples.append(
                dict(
                    uid=v["uid"],
                    original=source["context"],
                    output=v["text"],
                    lost_guard_occurrences=lost,
                    clipped=v["detail"]["budget_enforced"],
                )
            )
    assert dict(totals) == stress["totals"]
    assert len(stress_seen) == len(stress_inputs) * 2 * len(manifest["rates"])
    summary = dict(
        verified=True,
        qa_records=len(seen),
        qa_items=len(inputs),
        source_passages=len({r["passage_group"] for r in inputs.values()}),
        stress_texts=len(stress_inputs),
        stress_records=len(stress_seen),
        generation_error_records=dict(errors),
        reference_budget_misses=sum(not v["budget_met"] for v in variants.values()),
        wall_hours=(
            datetime.fromisoformat(workflow["updated"]) - datetime.fromisoformat(workflow["started"])
        ).total_seconds()
        / 3600,
        metrics=report["models"],
        comparisons=report["comparisons"],
        stress=stress["totals"],
        punctuation_only_outputs=dict(punctuation),
        stress_examples=examples,
        qa_examples=[
            e
            for e in report["examples"]
            if e["model"] == "qwen3.8:27b" and e["method"] == "bqwen35b_span@0.5" and e["direction"] == 1
        ][:3],
        interpretation="Exploratory exposed-data evidence, unadjusted intervals. Fixed-text transfer under "
        "reference-token caps; one answer-model family. No semantic-preservation guarantee.",
        analysis_sha256=digest(__file__),
        sources={
            f: digest(data / f)
            for f in (
                "manifest.json",
                "report.json",
                "stress_report.json",
                "answers.jsonl",
                "variants.jsonl",
                "stress_variants.jsonl",
                "inputs.jsonl",
                "stress_inputs.jsonl",
                "workflow.json",
                "state.json",
            )
        },
    )
    (data / "verified_review.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Hinglish compressor: completed development evaluation",
        "",
        f"Verified {len(seen):,} answer records on {len(inputs)} questions / "
        f"{summary['source_passages']} source passages; {len(stress_inputs):,} stress texts / "
        f"{len(stress_seen):,} stress outputs. Wall time {summary['wall_hours']:.2f} hours.",
        "All saved data hashes, QA scores, duplicate-prompt consistency, "
        "reference token counts and stress counters checked.",
        "",
        "Candidate: Qwen3.6-35B question-only evidence ranking with original-span packing.",
        "",
        "| Answer model | Context target | Candidate % | BM25 % | LLML2 % | Delta vs BM25, pp [95% CI] |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for model, methods in report["models"].items():
        for rate in manifest["rates"]:
            candidate = f"bqwen35b_span@{rate}"
            c = next(
                c
                for c in report["comparisons"]
                if c["model"] == model
                and c["method"] == candidate
                and c["reference"] == f"bm25_strict@{rate}"
                and "selection_source_overlap" not in c
            )
            values = [
                100 * methods[name]["accuracy"] for name in (candidate, f"bm25_strict@{rate}", f"llml2L_strict@{rate}")
            ]
            lines.append(
                f"| {model} | {rate} | {values[0]:.2f} | {values[1]:.2f} | {values[2]:.2f} | "
                f"{100 * c['delta']:+.2f} [{100 * c['ci95'][0]:+.2f}, {100 * c['ci95'][1]:+.2f}] |"
            )
    lines += [
        "",
        "Intervals are paired passage-clustered, exploratory and unadjusted for multiple comparisons.",
        "At 0.50 and 0.33, BM25 intervals exclude zero for all four answer models, including the 666-question "
        "subset outside current selection sources. That subset still has historical exposure. Superiority over "
        "LLMLingua-2 is less uniform: several corresponding intervals include zero.",
        "",
        "## Efficiency and failure limits",
        "",
        "| Model | Original generation, s | Candidate compression + generation at 0.50, s |",
        "|---|---:|---:|",
    ]
    for model, methods in report["models"].items():
        candidate = methods["bqwen35b_span@0.5"]
        total = candidate["mean_compression_seconds"] + candidate["mean_generation_seconds"]
        lines.append(f"| {model} | {methods['original']['mean_generation_seconds']:.3f} | {total:.3f} |")
    first = next(iter(report["models"].values()))
    for rate in (0.5, 0.33):
        candidate = first[f"bqwen35b_span@{rate}"]
        lines += [
            "",
            f"At target {rate}, mean actual context kept is {100 * candidate['mean_context_ratio']:.1f}% "
            f"and full prompt kept is {100 * candidate['mean_full_prompt_ratio']:.1f}%.",
        ]
    lines += [
        "",
        "Component sums above are observed timings, not a controlled deployment latency benchmark. "
        "The ranker overhead exceeds measured answer-generation savings here; do not claim end-to-end speedup. "
        "Invalid outputs remain failures in denominators; raw output-cap errors are preserved.",
        "",
        "## Stress checks and manual review",
        "",
        "Budget compliance does not establish meaning preservation. Report original Roman text and derived "
        "romanizations separately. Literal negation/number deletion is a surface diagnostic, "
        "not a semantic error rate.",
    ]
    for stratum in ("original_roman_hindi_heuristic", "derived_romanization_annotator1"):
        key = f"{stratum}|bqwen35b_span@0.33"
        item = totals[key]
        lines += [
            "",
            f"{stratum}: {item['items']} texts; at 0.33, {item['empty']} empty, "
            f"{punctuation[key]} nonempty punctuation-only, {item['clipped']} prefix-clipped; "
            f"{item['lost_guard_occurrences']}/{item['guard_occurrences']} tracked literal occurrences dropped.",
        ]
    lines += [
        "",
        "Inspected QA wins bb-8, bb-11 and bb-21: bb-11 retains the daily nest-change evidence; "
        "bb-8 answers correctly although the selected text omits the tide condition, showing that accuracy "
        "alone cannot prove evidence preservation. Stress examples in verified_review.json drop a date/number "
        "or negation, and one emits only punctuation without the clipping flag.",
        "",
        "## Paper decision",
        "",
        "Promising development result, not a confirmed superiority or losslessness claim. Keep the selector opt-in. "
        "Next priorities: repair lossy span/fallback behaviour and test a cheaper distilled scorer; then evaluate "
        "a frozen method on fresh source-disjoint human-validated Hinglish QA with an independent model family. "
        "Establish novelty against current query-aware retrieval/compression work "
        "before drafting a contribution claim.",
        "",
        "Evidence: verified_review.json, report.json, stress_report.json and their fingerprinted raw files.",
    ]
    (data / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "verified",
                    "qa_records",
                    "qa_items",
                    "source_passages",
                    "stress_texts",
                    "stress_records",
                    "generation_error_records",
                )
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    review(parser.parse_args().data)

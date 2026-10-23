"""Small, versioned compressor comparison; no provider API calls.

prepare: deterministic paired inputs + source bundle for a private Kaggle run.
gpu: sequential compression checkpoints, then batched Qwen answers, no truncation.
grade: paired scores, achieved budgets, coverage and incomplete-run warnings.
audit: inspect historical Round 3 budgets locally without loading model weights.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
import math
import os
import subprocess
import time
import zipfile
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from common import BACKEND, BENCH, in_shard, read_jsonl

OUT = BENCH / "compressor_pilot_v2"
MODEL = "Qwen/Qwen2.5-3B-Instruct"
LARGE = "microsoft/llmlingua-2-xlm-roberta-large-meetingbank"
RATES = (0.5, 0.33)
METHODS = ("bhybrid_v2", "bhybrid", "bgraded", "bm25", "llml2L")


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def prepare(n: int, out: Path):
    if n < 1:
        raise ValueError("n must be positive")
    if (out / "manifest.json").exists():
        raise ValueError("Use a new output folder; an existing pilot is immutable")
    rows = []
    for name in ("belebele", "squad", "meetingbank", "hotpot"):
        folder = "belebele" if name == "belebele" else "hotpot" if name == "hotpot" else f"longqa_{name}"
        items = read_jsonl(BENCH / folder / "items.jsonl")
        # The existing Belebele development split stays separate from held-out data.
        if name == "belebele":
            items = [it for it in items if int(hashlib.sha256(f"hybrid-dev|{it['id']}".encode()).hexdigest(), 16) % 3 == 0]
        items.sort(key=lambda it: hashlib.sha256(f"compressor-pilot-v2|{name}|{it['id']}".encode()).hexdigest())
        if len(items) < n:
            raise ValueError(f"Not enough {name} inputs")
        for it in items[:n]:
            if name == "belebele":
                for lang in ("english", "hinglish"):
                    q = it[lang]
                    rows.append(dict(uid=f"{name}|{it['id']}|{lang}", item_id=it["id"], dataset=name,
                                     lang=lang, task="mcq", context=q["passage"], question=q["question"],
                                     options=q["options"], gold=it["gold"]))
            else:
                rows.append(dict(uid=f"{name}|{it['id']}|english", item_id=it["id"], dataset=name,
                                 lang="english", task="qa", context=it["context"], question=it["question"], gold=it["answer"]))
    write_rows(out / "inputs.jsonl", rows)
    # Source files only: no credentials, model weights, raw datasets or .env.
    scripts = ("common", "compressor_pilot", "baselines2", "hybrid", "belebele_extra", "belebele_cm", "hotpot", "grade")
    sources = [BACKEND / "scripts" / "bench" / f"{name}.py" for name in scripts]
    sources += [BACKEND / "src" / "gateway" / name for name in (
        "__init__.py", "schemas.py", "tokenizer.py", "pricing.py", "modules/__init__.py",
        *[f"modules/m2_compressor/{name}.py" for name in ("__init__", "budgeted", "guarded", "llmlingua2", "safety_span")],
    )]
    with zipfile.ZipFile(out / "source.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for file in sorted(sources):
            bundle.write(file, str(file.relative_to(BACKEND)).replace("\\", "/"))
    manifest = {
        "study": f"exploratory compressor pilot ({out.name})", "n_per_dataset": n, "units": len(rows),
        "rates": RATES, "methods": METHODS, "answer_model": MODEL,
        "budget_tokenizer": MODEL, "max_new_tokens": 128, "max_seconds": 3300,
        "source_sha256": hashlib.sha256((out / "source.zip").read_bytes()).hexdigest(),
        "inputs_sha256": hashlib.sha256((out / "inputs.jsonl").read_bytes()).hexdigest(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=BACKEND, text=True).strip(),
        "notes": "Belebele uses existing development items only. No certification or held-out claims.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest), flush=True)


def _prompt(row, context):
    if row["task"] == "mcq":
        from belebele_cm import mcq
        return ("Answer the multiple-choice question. Reply with only the correct option letter.",
                mcq(context, row["question"], row["options"]))
    from hotpot import SYSTEM
    return SYSTEM, f"Context:\n{context}\n\nQuestion: {row['question']}"


def gpu(data: Path, out: Path):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from baselines2 import bm25_select
    from hybrid import bgraded, bhybrid
    from gateway.modules.m2_compressor.budgeted import compress_bm25_budgeted
    from gateway.modules.m2_compressor.llmlingua2 import DEFAULT_MODEL, LLMLingua2Compressor

    if not torch.cuda.is_available():
        raise RuntimeError("GPU required; refusing an accidental CPU model run")
    started = time.monotonic()
    deadline = float(os.environ.get("COMPRESSOR_DEADLINE", time.time() + 3300))

    def check_time():
        if time.time() >= deadline:
            raise TimeoutError("Pilot time cap reached; partial outputs retained")

    out.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(data / "inputs.jsonl")
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256((data / "inputs.jsonl").read_bytes()).hexdigest() != manifest["inputs_sha256"]:
        raise ValueError("Input fingerprint mismatch")
    config = manifest["source_sha256"] + ":" + manifest["inputs_sha256"]
    metadata = dict(manifest, config=config, gpu=torch.cuda.get_device_name(), gpu_count=torch.cuda.device_count(),
                    versions={name: importlib.metadata.version(name) for name in ("torch", "transformers", "llmlingua")})
    (out / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    tok = AutoTokenizer.from_pretrained(MODEL, padding_side="left")
    tok.pad_token = tok.eos_token

    def count(text):
        return len(tok.encode(text, add_special_tokens=False))

    variants_file = out / "variants.jsonl"
    existing = {r["key"]: r for r in read_jsonl(variants_file)}
    if any(r.get("config") != config for r in existing.values()):
        raise ValueError("Resume source/input mismatch")
    # Sequential phases avoid holding the two compressors and causal LM together.
    for phase in ("small", "large"):
        check_time()
        lingua = LLMLingua2Compressor(DEFAULT_MODEL if phase == "small" else LARGE, device="cuda:0")
        with variants_file.open("a", encoding="utf-8") as fh:
            for row in rows:
                check_time()
                text, q = row["context"], row["question"]
                work = [("original", None)] if phase == "small" else []
                work += [(f"{method}@{rate}", rate) for rate in RATES
                         for method in (METHODS[:-1] if phase == "small" else ("llml2L",))]
                for method, rate in work:
                    key = row["uid"] + "|" + method
                    if key in existing:
                        continue
                    check_time()
                    detail = {}
                    t0 = time.monotonic()
                    if method == "original":
                        compressed = text
                    elif method.startswith("bhybrid_v2@"):
                        result = compress_bm25_budgeted(text, q, rate, count, lingua,
                                                       sent_share={0.5: 0.7, 0.33: 0.6}[rate])
                        detail = asdict(result)
                        compressed = detail.pop("text")
                    elif method.startswith("bhybrid@"):
                        compressed = bhybrid(text, q, rate, {0.5: 0.7, 0.33: 0.6}[rate], count, lingua)
                    elif method.startswith("bgraded@"):
                        compressed = bgraded(text, q, rate, count, lingua)
                    elif method.startswith("bm25@"):
                        compressed = bm25_select(text, q, rate, count)
                    else:
                        compressed = lingua._ensure().compress_prompt(text, rate=rate, force_tokens=["\n", "?", "."])["compressed_prompt"]
                    n, kept = count(text), count(compressed)
                    target = n if rate is None else max(1, math.floor(rate * n))
                    record = dict(key=key, uid=row["uid"], method=method, text=compressed,
                                  original_tokens=n, actual_tokens=kept, target_tokens=target,
                                  budget_met=kept <= target, kept_ratio=kept / max(1, n),
                                  compression_seconds=time.monotonic() - t0, config=config, detail=detail)
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                    fh.flush()
                    existing[key] = record
        del lingua
        gc.collect()
        torch.cuda.empty_cache()
        print(f"{phase} compression finished: {len(existing)} variants", flush=True)

    check_time()
    answers_file = out / "answers.jsonl"
    answers = {r["key"]: r for r in read_jsonl(answers_file)}
    if any(r.get("config") != config for r in answers.values()):
        raise ValueError("Answer resume fingerprint mismatch")
    inputs = {row["uid"]: row for row in rows}
    todo = []
    for key, variant in existing.items():
        if key in answers:
            continue
        row = inputs[variant["uid"]]
        system, prompt = _prompt(row, variant["text"])
        chat = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                                       tokenize=False, add_generation_prompt=True)
        todo.append((variant, chat, count(chat)))
    # Item-first order yields complete paired examples if the time cap is reached.
    todo.sort(key=lambda entry: (entry[0]["uid"], entry[0]["method"]))
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16, device_map="cuda:0").eval()
    max_context = min(int(getattr(model.config, "max_position_embeddings", 32768)), 16384)
    with answers_file.open("a", encoding="utf-8") as fh:
        for start in range(0, len(todo), 4):
            check_time()
            batch = todo[start:start + 4]
            if max(entry[2] for entry in batch) + 128 > max_context:
                raise ValueError("Context too long; refusing silent truncation of question/options")
            encoded = tok([entry[1] for entry in batch], padding=True, truncation=False,
                          add_special_tokens=False, return_tensors="pt").to(model.device)
            with torch.inference_mode():
                generated = model.generate(**encoded, max_new_tokens=128, do_sample=False, pad_token_id=tok.pad_token_id)
            for index, (variant, _, _) in enumerate(batch):
                content = tok.decode(generated[index, encoded["input_ids"].shape[1]:], skip_special_tokens=True)
                record = dict(key=variant["key"], uid=variant["uid"], method=variant["method"], model=MODEL,
                              content=content, prompt_tokens=int(encoded["attention_mask"][index].sum()), config=config)
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"answers {min(start + 4, len(todo))}/{len(todo)}, elapsed {time.monotonic() - started:.0f}s", flush=True)
    grade(data, out)


def grade(data: Path, out: Path):
    from grade import extract_letter
    from hotpot import clean, f1

    rows = read_jsonl(data / "inputs.jsonl")
    variants = {r["key"]: r for r in read_jsonl(out / "variants.jsonl")}
    answers = {r["key"]: r for r in read_jsonl(out / "answers.jsonl")}
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    config = manifest["source_sha256"] + ":" + manifest["inputs_sha256"]
    if any(r.get("config") != config for r in [*variants.values(), *answers.values()]):
        raise ValueError("Cannot grade mixed configurations")
    if any(r.get("model") != MODEL for r in answers.values()):
        raise ValueError("Cannot grade mixed answer models")
    methods = ["original", *[f"{method}@{rate}" for rate in RATES for method in METHODS]]
    expected_keys = {row["uid"] + "|" + method for row in rows for method in methods}
    if set(answers) - expected_keys or set(variants) - expected_keys:
        raise ValueError("Unexpected answer/variant keys in pilot output")
    if set(answers) - set(variants):
        raise ValueError("Answer is missing its compression variant")
    report = {"study": manifest["study"], "config": config, "expected_answers": len(rows) * len(methods),
              "answered": len(answers), "complete": set(answers) == expected_keys, "groups": {}}
    groups = defaultdict(list)
    for row in rows:
        groups[f"{row['dataset']}|{row['lang']}"].append(row)

    def score(row, method):
        reply = answers[row["uid"] + "|" + method]["content"]
        return float(extract_letter(reply) == row["gold"]) if row["task"] == "mcq" else f1(clean(reply), row["gold"])

    for group, inputs in groups.items():
        complete = [row for row in inputs if all(row["uid"] + "|" + m in answers for m in methods)]
        summary = {"n_inputs": len(inputs), "n_complete_paired": len(complete), "methods": {}}
        for method in methods:
            paired = [row for row in inputs if all(row["uid"] + "|" + m in answers for m in (method, "original"))]
            compressed = [variants[row["uid"] + "|" + method] for row in paired]
            result = {"n_paired_original": len(paired), "score": None, "score_original_paired": None,
                      "score_all_methods_paired": None, "mean_kept_ratio": None, "budget_misses": None}
            if paired:
                result.update(score=sum(score(row, method) for row in paired) / len(paired),
                              score_original_paired=sum(score(row, "original") for row in paired) / len(paired),
                              mean_kept_ratio=sum(v["kept_ratio"] for v in compressed) / len(compressed),
                              budget_misses=sum(not v["budget_met"] for v in compressed))
            if complete:
                result["score_all_methods_paired"] = sum(score(row, method) for row in complete) / len(complete)
            summary["methods"][method] = result
        report["groups"][group] = summary
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "groups"}), flush=True)
    return report


def audit(shard: str, out: Path):
    """Count saved Round 3 outputs using its original cl100k tokenizer."""
    from gateway.tokenizer import TokenCounter
    counter = TokenCounter()
    if counter.backend != "tiktoken_cl100k_base":
        raise RuntimeError("Exact tokenizer unavailable; refusing heuristic budget metrics")
    groups, examples, seen_examples = defaultdict(list), [], set()
    for file in sorted((BENCH / "round3").glob("*.jsonl")):
        dataset = file.name.split(".")[0]
        folder = "belebele" if dataset == "belebele" else "hotpot" if dataset == "hotpot" else f"longqa_{dataset}"
        originals = {row["id"]: row for row in read_jsonl(BENCH / folder / "items.jsonl")}
        for row in read_jsonl(file):
            if not in_shard(row["id"], shard):
                continue
            for method, text in row["variants"].items():
                original = originals[row["id"]]
                if dataset == "belebele":
                    original = original["hinglish" if row["tag"] == "hi" else "english"]["passage"]
                else:
                    original = original["context"]
                original_n, actual_n = counter.count(original), counter.count(text)
                ratio = actual_n / max(1, original_n)
                target = float(method.rsplit("@", 1)[1])
                groups[f"{dataset}|{row['tag']}|{method}"].append(ratio)
                if len(examples) < 3 and ratio > target + 0.25 and row["id"] not in seen_examples:
                    examples.append(dict(dataset=dataset, id=row["id"], tag=row["tag"], method=method,
                                         requested=target, saved_kept=row["kept"][method], measured_kept=ratio,
                                         original_tokens=original_n, actual_tokens=actual_n, original=original, text=text))
                    seen_examples.add(row["id"])
    report = {"shard": shard, "groups": {name: {"n": len(values), "mean_kept": sum(values) / len(values),
               "max_kept": max(values), "over_target_by_gt_0_02": sum(v > float(name.rsplit("@", 1)[1]) + 0.02 for v in values)}
               for name, values in groups.items()}, "examples": examples}
    out.mkdir(parents=True, exist_ok=True)
    (out / f"audit.{shard.replace('/', 'of')}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"audit {shard}: {len(groups)} groups, {len(examples)} saved examples", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=("prepare", "gpu", "grade", "audit"))
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--data", type=Path, default=OUT)
    ap.add_argument("--shard", default="1/1")
    args = ap.parse_args()
    if args.cmd == "prepare":
        prepare(args.n, args.out)
    elif args.cmd == "gpu":
        gpu(args.data, args.out)
    elif args.cmd == "grade":
        grade(args.data, args.out)
    else:
        audit(args.shard, args.out)

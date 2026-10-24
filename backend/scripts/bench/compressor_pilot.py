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
METHODS = ("bhybrid_v2", "bhybrid_doc", "bextract_doc", "bbridge_doc", "bstructured_doc",
           "bhybrid", "bgraded", "bm25", "llml2L",
           "bhybrid_strict", "bhybrid_char", "bhybrid_clause", "bhybrid_char_clause", "bm25_strict", "llml2L_strict")
STRICT_METHODS = {"bhybrid_strict", "bhybrid_char", "bhybrid_clause", "bhybrid_char_clause", "bm25_strict", "llml2L_strict"}
DEFAULT_METHODS = METHODS[:9]
DATASETS = ("belebele", "squad", "meetingbank", "hotpot", "musique", "2wiki")


def selected_methods(methods):
    chosen = tuple(methods) if methods is not None else DEFAULT_METHODS
    if not chosen or len(set(chosen)) != len(chosen) or set(chosen) - set(METHODS):
        raise ValueError("Choose distinct supported compressor methods")
    return chosen


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def prepare(n: int, out: Path, methods=None, offset: int = 0, datasets=None, unique_passages=False,
            exclude_inputs=(), allow_smaller=False):
    methods = selected_methods(methods)
    if n < 1:
        raise ValueError("n must be positive")
    if offset < 0:
        raise ValueError("offset must be nonnegative")
    if (out / "manifest.json").exists():
        raise ValueError("Use a new output folder; an existing pilot is immutable")
    datasets = tuple(datasets or ("belebele", "squad", "meetingbank", "hotpot"))
    if len(set(datasets)) != len(datasets) or set(datasets) - set(DATASETS):
        raise ValueError("Choose distinct supported datasets")
    def passage_group(text):
        return hashlib.sha256(' '.join(text.split()).encode()).hexdigest()

    excluded = set()
    exclusion_sources = {}
    for path in exclude_inputs:
        path = Path(path)
        exclusion_sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        for row in read_jsonl(path):
            excluded.add(passage_group(row['context']))
    selected_counts = {}
    rows = []
    for name in datasets:
        folder = "belebele" if name == "belebele" else "hotpot" if name == "hotpot" else f"longqa_{name}"
        items = read_jsonl(BENCH / folder / "items.jsonl")
        # Historical development IDs only; these are NOT a pristine held-out set.
        if name == "belebele":
            items = [it for it in items if int(hashlib.sha256(f"hybrid-dev|{it['id']}".encode()).hexdigest(), 16) % 3 == 0]
        items.sort(key=lambda it: hashlib.sha256(f"compressor-pilot-v2|{name}|{it['id']}".encode()).hexdigest())
        items = [it for it in items if passage_group(it['english']['passage'] if name == 'belebele' else it['context']) not in excluded]
        if unique_passages:
            distinct = {}
            for item in items:
                passage = item['english']['passage'] if name == 'belebele' else item['context']
                group = hashlib.sha256(' '.join(passage.split()).encode()).hexdigest()
                distinct.setdefault(group, item)
            items = list(distinct.values())
        if len(items) < offset + n and not allow_smaller:
            raise ValueError(f"Not enough {name} inputs")
        chosen = items[offset:offset + n]
        if not chosen:
            raise ValueError(f"No unexposed {name} passages available")
        selected_counts[name] = len(chosen)
        for it in chosen:
            if name == "belebele":
                for lang in ("english", "hinglish"):
                    q = it[lang]
                    rows.append(dict(uid=f"{name}|{it['id']}|{lang}", item_id=it["id"], dataset=name,
                                     lang=lang, task="mcq", context=q["passage"], question=q["question"],
                                     options=q["options"], gold=it["gold"],
                                     passage_group=hashlib.sha256(' '.join(it['english']['passage'].split()).encode()).hexdigest()))
            else:
                rows.append(dict(uid=f"{name}|{it['id']}|english", item_id=it["id"], dataset=name,
                                 lang="english", task="qa", context=it["context"], question=it["question"], gold=it["answer"]))
    write_rows(out / "inputs.jsonl", rows)
    # Source files only: no credentials, model weights, raw datasets or .env.
    scripts = ("common", "compressor_pilot", "baselines2", "hybrid", "belebele_extra", "belebele_cm", "hotpot", "grade")
    sources = [BACKEND / "scripts" / "bench" / f"{name}.py" for name in scripts]
    sources += [BACKEND / "src" / "gateway" / name for name in (
        "__init__.py", "schemas.py", "tokenizer.py", "pricing.py", "modules/__init__.py",
        *[f"modules/m2_compressor/{name}.py" for name in ("__init__", "budgeted", "document", "hinglish_budget", "guarded", "llmlingua2", "safety_span")],
    )]
    with zipfile.ZipFile(out / "source.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for file in sorted(sources):
            bundle.write(file, str(file.relative_to(BACKEND)).replace("\\", "/"))
    manifest = {
        "study": f"exploratory compressor pilot ({out.name})", "n_per_dataset": n, "selection_offset": offset,
        "units": len(rows),
        "datasets": datasets, "unique_passages": unique_passages,
        "selected_per_dataset": selected_counts, "excluded_input_sha256": exclusion_sources,
        "allow_smaller": allow_smaller,
        "rates": RATES, "methods": methods, "answer_model": MODEL,
        "budget_tokenizer": MODEL, "max_new_tokens": 128, "max_seconds": 3300,
        "source_sha256": hashlib.sha256((out / "source.zip").read_bytes()).hexdigest(),
        "inputs_sha256": hashlib.sha256((out / "inputs.jsonl").read_bytes()).hexdigest(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=BACKEND, text=True).strip(),
        "notes": "Previously exposed development data only; unique passages means within this run, not unseen sources. No confirmatory claims. Strict methods use identical explicit word-prefix budget enforcement.",
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


def group_identical_prompts(todo):
    """One greedy generation per exact rendered prompt, within this run only.

    Even greedy GPU inference can differ with batch padding/numerical kernels.
    Reusing exact inputs removes that nuisance difference between compressors.
    Full prompt strings (including the question/options) are the equality key.
    """
    grouped = {}
    for entry in todo:
        grouped.setdefault(entry[1], []).append(entry)
    return list(grouped.values())


def answer_records(group, content, prompt_tokens, config):
    source = group[0][0]["key"]
    fingerprint = hashlib.sha256(group[0][1].encode("utf-8")).hexdigest()
    for variant, _, _ in group:
        yield dict(key=variant["key"], uid=variant["uid"], method=variant["method"], model=MODEL,
                   content=content, prompt_tokens=prompt_tokens, config=config,
                   prompt_sha256=fingerprint, reused_from=source if variant["key"] != source else None)


def gpu(data: Path, out: Path, shard: str = "1/1"):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from baselines2 import bm25_select
    from hybrid import bgraded, bhybrid
    from gateway.modules.m2_compressor.budgeted import compress_bm25_budgeted
    from gateway.modules.m2_compressor.hinglish_budget import compress_ablation, strict_prefix
    from gateway.modules.m2_compressor.document import (
        bridge_document, compress_document, extract_document, structured_document,
    )
    from gateway.modules.m2_compressor.llmlingua2 import DEFAULT_MODEL, LLMLingua2Compressor

    if not torch.cuda.is_available():
        raise RuntimeError("GPU required; refusing an accidental CPU model run")
    started = time.monotonic()
    deadline = float(os.environ.get("COMPRESSOR_DEADLINE", time.time() + 3300))

    def check_time():
        if time.time() >= deadline:
            raise TimeoutError("Pilot time cap reached; partial outputs retained")

    out.mkdir(parents=True, exist_ok=True)
    rows = [row for row in read_jsonl(data / "inputs.jsonl") if in_shard(row["item_id"], shard)]
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    methods = selected_methods(manifest["methods"])
    rates = manifest["rates"]
    if hashlib.sha256((data / "inputs.jsonl").read_bytes()).hexdigest() != manifest["inputs_sha256"]:
        raise ValueError("Input fingerprint mismatch")
    config = manifest["source_sha256"] + ":" + manifest["inputs_sha256"]
    metadata = dict(manifest, config=config, gpu=torch.cuda.get_device_name(), gpu_count=torch.cuda.device_count(),
                    shard=shard, worker_inputs=len(rows),
                    versions={name: importlib.metadata.version(name) for name in ("torch", "transformers", "llmlingua")})
    (out / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    if not rows:
        write_rows(out / "variants.jsonl", [])
        write_rows(out / "answers.jsonl", [])
        return
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
        phase_methods = [m for m in methods if m.startswith("llml2L") == (phase == "large")]
        if not phase_methods:
            continue
        check_time()
        lingua = (LLMLingua2Compressor(DEFAULT_MODEL if phase == "small" else LARGE, device="cuda:0")
                  if any(m not in ("bm25", "bm25_strict", "bhybrid_clause", "bhybrid_char_clause") for m in phase_methods) else None)
        with variants_file.open("a", encoding="utf-8") as fh:
            for row in rows:
                check_time()
                text, q = row["context"], row["question"]
                work = [("original", None)] if phase == ("large" if all(m.startswith("llml2L") for m in methods) else "small") else []
                work += [(f"{method}@{rate}", rate) for rate in rates for method in phase_methods]
                for method, rate in work:
                    key = row["uid"] + "|" + method
                    if key in existing:
                        continue
                    check_time()
                    detail = {}
                    t0 = time.monotonic()
                    if method == "original":
                        compressed = text
                    elif method.split("@", 1)[0] in STRICT_METHODS - {"bm25_strict", "llml2L_strict"}:
                        result = compress_ablation(text, q, rate, count, lingua,
                                                   characters="char" in method, clauses="clause" in method)
                        detail = asdict(result)
                        compressed = detail.pop("text")
                    elif method.split("@", 1)[0] in ("bhybrid_doc", "bextract_doc", "bbridge_doc", "bstructured_doc"):
                        compressor = dict(bhybrid_doc=compress_document, bextract_doc=extract_document,
                                          bbridge_doc=bridge_document, bstructured_doc=structured_document)[
                                              method.split("@", 1)[0]]
                        result = compressor(text, q, rate, count, lingua)
                        detail = asdict(result)
                        compressed = detail.pop("text")
                    elif method.startswith("bhybrid_v2@"):
                        result = compress_bm25_budgeted(text, q, rate, count, lingua,
                                                       sent_share={0.5: 0.7, 0.33: 0.6}[rate])
                        detail = asdict(result)
                        compressed = detail.pop("text")
                    elif method.startswith("bhybrid@"):
                        compressed = bhybrid(text, q, rate, {0.5: 0.7, 0.33: 0.6}[rate], count, lingua)
                    elif method.startswith("bgraded@"):
                        compressed = bgraded(text, q, rate, count, lingua)
                    elif method.split("@", 1)[0] in ("bm25", "bm25_strict"):
                        compressed = bm25_select(text, q, rate, count)
                    else:
                        compressed = lingua._ensure().compress_prompt(text, rate=rate, force_tokens=["\n", "?", "."])["compressed_prompt"]
                    n = count(text)
                    target = n if rate is None else max(1, math.floor(rate * n))
                    if method.split("@", 1)[0] in STRICT_METHODS:
                        detail['before_enforcement_tokens'] = count(compressed)
                        detail['before_enforcement_text'] = compressed
                        compressed = strict_prefix(compressed, target, count)
                        detail['budget_enforced'] = compressed != detail['before_enforcement_text']
                    kept = count(compressed)
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
    grouped = group_identical_prompts(todo)
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16, device_map="cuda:0").eval()
    max_context = min(int(getattr(model.config, "max_position_embeddings", 32768)), 16384)
    with answers_file.open("a", encoding="utf-8") as fh:
        for start in range(0, len(grouped), 4):
            check_time()
            groups = grouped[start:start + 4]
            batch = [group[0] for group in groups]
            if max(entry[2] for entry in batch) + 128 > max_context:
                raise ValueError("Context too long; refusing silent truncation of question/options")
            encoded = tok([entry[1] for entry in batch], padding=True, truncation=False,
                          add_special_tokens=False, return_tensors="pt").to(model.device)
            with torch.inference_mode():
                generated = model.generate(**encoded, max_new_tokens=128, do_sample=False, pad_token_id=tok.pad_token_id)
            for index, group in enumerate(groups):
                content = tok.decode(generated[index, encoded["input_ids"].shape[1]:], skip_special_tokens=True)
                for record in answer_records(group, content, int(encoded["attention_mask"][index].sum()), config):
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"unique prompts {min(start + 4, len(grouped))}/{len(grouped)} for {len(todo)} answers, "
                  f"elapsed {time.monotonic() - started:.0f}s", flush=True)
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
    configured_methods = manifest.get("methods", METHODS)
    configured_rates = manifest.get("rates", RATES)
    methods = ["original", *[f"{method}@{rate}" for rate in configured_rates for method in configured_methods]]
    expected_keys = {row["uid"] + "|" + method for row in rows for method in methods}
    if set(answers) - expected_keys or set(variants) - expected_keys:
        raise ValueError("Unexpected answer/variant keys in pilot output")
    if set(answers) - set(variants):
        raise ValueError("Answer is missing its compression variant")
    inputs_by_uid = {row["uid"]: row for row in rows}
    for key, answer in answers.items():
        reference_key = answer.get("reused_from")
        if reference_key is None:
            continue
        reference = answers.get(reference_key)
        if (reference is None or reference_key == key
                or not answer.get("prompt_sha256")
                or any(answer.get(field) != reference.get(field)
                       for field in ("content", "prompt_tokens", "prompt_sha256"))):
            raise ValueError("Invalid reused answer provenance")
        left, right = variants[key], variants[reference_key]
        if _prompt(inputs_by_uid[left["uid"]], left["text"]) != _prompt(
                inputs_by_uid[right["uid"]], right["text"]):
            raise ValueError("Reused answer belongs to a different prompt")
    if any(v["budget_met"] != (v["actual_tokens"] <= v["target_tokens"]) for v in variants.values()):
        raise ValueError("Inconsistent actual token-budget metadata")
    report = {"study": manifest["study"], "config": config, "expected_answers": len(rows) * len(methods),
              "answered": len(answers), "complete": set(answers) == expected_keys, "groups": {},
              "analysis_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    same_prompts = defaultdict(list)
    for row in rows:
        for method in methods:
            key = row["uid"] + "|" + method
            if key in answers:
                same_prompts[_prompt(row, variants[key]["text"])].append(key)
    duplicate_groups = [keys for keys in same_prompts.values() if len(keys) > 1]
    disagreements = [keys for keys in duplicate_groups if len({answers[key]["content"] for key in keys}) > 1]
    report["identical_prompt_diagnostics"] = dict(groups=len(duplicate_groups),
                                                 inconsistent_answer_groups=len(disagreements),
                                                 examples=disagreements[:3],
                                                 reused_answers=sum(bool(a.get("reused_from")) for a in answers.values()))
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
            comparisons = {}
            if "@" in method:
                rate = method.rsplit("@", 1)[1]
                for family in ("bm25", "llml2L", "bhybrid"):
                    reference = f"{family}@{rate}"
                    if reference not in methods or reference == method:
                        continue
                    fair = [row for row in paired if row["uid"] + "|" + reference in answers
                            and variants[row["uid"] + "|" + method]["budget_met"]
                            and variants[row["uid"] + "|" + method]["actual_tokens"]
                            <= variants[row["uid"] + "|" + reference]["actual_tokens"]]
                    comparisons[reference] = {"n": len(fair), "delta_score": None}
                    if fair:
                        comparisons[reference]["delta_score"] = sum(
                            score(row, method) - score(row, reference) for row in fair) / len(fair)
            result["comparisons_at_no_more_context_tokens"] = comparisons
            summary["methods"][method] = result
        report["groups"][group] = summary
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "groups"}), flush=True)
    return report


def merge_workers(data: Path, out: Path, workers: list[Path]):
    """Merge disjoint GPU shards without silently accepting duplicate work."""
    for filename in ("variants.jsonl", "answers.jsonl"):
        merged = {}
        for worker in workers:
            for row in read_jsonl(worker / filename):
                if row["key"] in merged:
                    raise ValueError(f"Overlapping GPU shards: {row['key']}")
                merged[row["key"]] = row
        write_rows(out / filename, [merged[key] for key in sorted(merged)])
    metadata = [json.loads((worker / "run_metadata.json").read_text(encoding="utf-8"))
                for worker in workers if (worker / "run_metadata.json").exists()]
    if metadata:
        summary = dict(metadata[0], gpu_count=len(workers), worker_shards=[m.get("shard") for m in metadata],
                       worker_inputs=sum(m.get("worker_inputs", 0) for m in metadata))
        (out / "run_metadata.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return grade(data, out)


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


def audit_documents(shard: str, out: Path):
    """Model-free corpus audit of quotation envelopes and protected-span pressure."""
    from gateway.modules.m2_compressor.document import unwrap_document
    from gateway.modules.m2_compressor.safety_span import detect_spans
    from gateway.tokenizer import TokenCounter
    counter = TokenCounter()
    if counter.backend != "tiktoken_cl100k_base":
        raise RuntimeError("Exact tokenizer required for the corpus audit")
    groups = {}
    for name in ("belebele", "squad", "meetingbank", "hotpot"):
        folder = "belebele" if name == "belebele" else "hotpot" if name == "hotpot" else f"longqa_{name}"
        for row in read_jsonl(BENCH / folder / "items.jsonl"):
            if not in_shard(row["id"], shard):
                continue
            passages = [(lang, row[lang]["passage"]) for lang in ("english", "hinglish")] if name == "belebele" else [("english", row["context"])]
            for lang, text in passages:
                group = groups.setdefault(f"{name}|{lang}", dict(n=0, envelopes=0, before={}, after={}, examples=[]))
                group["n"] += 1
                unwrapped = unwrap_document(text)
                changed = unwrapped != text
                group["envelopes"] += changed
                n = counter.count(text)
                sizes = [max((counter.count(span.text) for span in detect_spans(value)), default=0)
                         for value in (text, unwrapped)]
                for label, largest in zip(("before", "after"), sizes):
                    for rate in RATES:
                        key = str(rate)
                        group[label][key] = group[label].get(key, 0) + (largest > max(1, math.floor(rate * n)))
                if changed and len(group["examples"]) < 3:
                    group["examples"].append(dict(id=row["id"], context_tokens=n,
                                                   largest_span_before=sizes[0], largest_span_after=sizes[1]))
    out.mkdir(parents=True, exist_ok=True)
    report = dict(shard=shard, tokenizer=counter.backend, groups=groups,
                  note="Span-size pressure is a diagnostic, not a formal token lower bound or quality score.")
    (out / f"documents.{shard.replace('/', 'of')}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"document audit {shard}: {sum(g['n'] for g in groups.values())} passages", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=("prepare", "gpu", "grade", "audit", "merge", "audit-documents"))
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--methods", nargs="+", choices=METHODS)
    ap.add_argument("--datasets", nargs="+", choices=DATASETS)
    ap.add_argument("--unique-passages", action="store_true")
    ap.add_argument("--exclude-inputs", nargs="+", type=Path, default=[])
    ap.add_argument("--allow-smaller", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--data", type=Path, default=OUT)
    ap.add_argument("--shard", default="1/1")
    ap.add_argument("--workers", type=Path, nargs="+", default=[])
    args = ap.parse_args()
    if args.cmd == "prepare":
        prepare(args.n, args.out, args.methods, args.offset, args.datasets, args.unique_passages,
                args.exclude_inputs, args.allow_smaller)
    elif args.cmd == "gpu":
        gpu(args.data, args.out, args.shard)
    elif args.cmd == "grade":
        grade(args.data, args.out)
    elif args.cmd == "merge":
        if not args.workers:
            ap.error("merge requires --workers")
        merge_workers(args.data, args.out, args.workers)
    elif args.cmd == "audit-documents":
        audit_documents(args.shard, args.out)
    else:
        audit(args.shard, args.out)

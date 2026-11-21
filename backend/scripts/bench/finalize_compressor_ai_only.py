"""Close the owner-approved AI-only study using existing frozen evidence.

No inference, relabelling, filtering, or human-validation claims are introduced.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from compressor_artifacts import digest,records,save


def verify_run(data,expected):
    state=json.loads((data/'state.json').read_text())
    if state['status']!='complete':raise ValueError('Incomplete campaign: '+str(data))
    for stem in ['answers','variants']:
        if digest(data/(stem+'.jsonl'))!=state[stem+'_sha256']:raise ValueError('Changed raw '+stem)
    rows=list(records(data/'answers.jsonl'))
    keys={(r['uid'],r['method']) for r in rows}
    if len(rows)!=expected or len(keys)!=expected:raise ValueError('Missing or duplicate answer coverage')
    return state


def finalize(root):
    bench=root/'backend/data/bench'
    qwen=bench/'qwen_student_20261116'
    native=bench/'neural_student_20261116/results/combined'
    qstate=json.loads((qwen/'data/state.json').read_text())
    if qstate['status']!='complete' or digest(qwen/'data/answers.jsonl')!=qstate['answers_sha256']:
        raise ValueError('Changed/incomplete Qwen campaign')
    qspec=json.loads((qwen/'data/manifest.json').read_text())
    for name,expected in qspec['files'].items():
        if digest(qwen/'data'/name)!=expected:raise ValueError('Changed Qwen input')
    if len(list(records(qwen/'data/answers.jsonl')))!=2196:raise ValueError('Incomplete Qwen answer coverage')
    verify_run(native,3294)
    q=json.loads((qwen/'analysis/report.json').read_text())
    n=json.loads((native/'report.json').read_text())
    for report in [q,n]:
        if report['status']!='complete':raise ValueError('Incomplete analysis')
    for folder,original in [(qwen/'reanalysis',qwen/'analysis/report.json'),(bench/'neural_student_20261116/reanalysis',native/'report.json')]:
        receipt=json.loads((folder/'replay_verification.json').read_text())
        if (receipt['status']!='verified' or digest(folder/'report.json')!=receipt['replay_sha256']
                or digest(original)!=receipt['original_sha256']):
            raise ValueError('Unverified/changed analysis replay')
    audit=json.loads((native/'token_replay_audit.json').read_text())
    if audit['native_cap_misses'] or audit['exact_rendered_prompts_verified']!=3294:
        raise ValueError('Unverified native accounting')
    for name,expected in audit['sources'].items():
        if digest(native/name)!=expected:raise ValueError('Native audit source changed')
    checkpoint=bench/'neural_student_20261116/results/checkpoint.safetensors'
    neural_state=json.loads((checkpoint.parent/'state.json').read_text())
    if digest(checkpoint)!=neural_state['checkpoint_sha256']:raise ValueError('Changed checkpoint')
    labels=root/'docs/annotation/belebele_cm_ai_reviewed.csv'
    with labels.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    if len(rows)!=500 or len({r['id'] for r in rows})!=500:raise ValueError('AI-label coverage differs')
    for row in rows:
        if row['ai_suggested_same_meaning'] not in ['yes','partly','no']:raise ValueError('Invalid meaning label')
        if row['ai_suggested_answerable_same_gold'] not in ['yes','no']:raise ValueError('Invalid answerability label')
        if row['ai_suggested_natural_hinglish'] not in ['1','2','3']:raise ValueError('Invalid naturalness label')
    ar=json.loads((bench/'gpu_annotation_review_20261116/merged/report.json').read_text())
    if digest(labels)!=ar['outputs']['reviewed_labels_sha256']:raise ValueError('Reviewed-label checksum mismatch')
    source=root/'docs/annotation/belebele_cm_verify_500.csv'
    if digest(source)!=ar['sources']['source']:raise ValueError('Original source changed')
    dataset=dict(status='complete_for_ai_only_development',rows=500,label_file=str(labels.relative_to(root)),
        labels_sha256=digest(labels),source_sha256=digest(source),label_origin='Qwen3.6-35B plus source-based Codex AI adjudication',
        owner_acceptance='Working AI labels accepted by owner on 2026-11-16; no human review requested',
        human_review_performed=False,historically_exposed=True,confirmatory_eligible=False,
        original_gold_preserved=True,counts=ar['counts'],changed_rows=ar['changed_rows'])
    save(labels.with_suffix('.manifest.json'),dataset)
    facts=dict(status='complete',scope='AI-only exploratory Hinglish compressor implementation and development study',
        owner_scope_decision_date='2026-11-16',human_input_required=False,human_validation_performed=False,
        scientific_quality_target_met=False,confirmatory_claim_supported=False,
        serving_defaults_changed=False,qa_records={'qwen':2196,'native_combined':3294},
        comparisons={'qwen':len(q['comparisons']),'native_combined':len(n['comparisons'])},
        ai_annotation_rows=500,changed_annotation_rows=ar['changed_rows'],native_cap_violations=0,
        native_capped_answers=sum(m['errors'] for m in n['metrics'].values()),
        native_invalid_answers=sum(m['invalid'] for m in n['metrics'].values()),
        frozen_checkpoint_sha256=digest(checkpoint),ai_label_manifest_sha256=digest(labels.with_suffix('.manifest.json')),
        sources={'qwen_report':digest(qwen/'analysis/report.json'),'native_report':digest(native/'report.json'),
                 'native_token_audit':digest(native/'token_replay_audit.json'),'annotation_report':digest(bench/'gpu_annotation_review_20261116/merged/report.json')},
        script_sha256=digest(Path(__file__)),limitations=[
            'AI labels are working judgments, not guaranteed correct or human-validated.',
            'All existing Belebele examples are exposed development data.',
            'Both student candidates failed to establish a baseline quality or latency advantage.',
            'Fresh sealed confirmation and a superiority claim are outside this completed AI-only scope.'])
    save(root/'docs/research/COMPRESSOR_AI_ONLY_FINAL.json',facts)
    lines=['# Final AI-only Hinglish compressor report','',
        'Finalized 16 November 2026 under the owner\'s instruction to proceed without human review.',
        'The implementation, AI annotation, fixed GPU experiments, analysis, checkpoint, and evidence packaging are complete for this exploratory scope. No human action is required to use these deliverables.',
        '', '## Main finding','',
        'Neither tested student demonstrates better answer quality than the strong compression baselines. Neither establishes an end-to-end speedup. This is a completed negative development study, not an unfinished request for manual labels. A better-compressor or fresh-test superiority claim is unsupported.',
        '', '## Data and working labels','',
        'The 500-row AI review is the accepted working annotation file. It changes 286 rows relative to the earlier AI pass. All original text, source gold, raw GPU responses and AI adjudications remain available. Human columns remain unfilled because no human review occurred.',
        'The 183 development questions belong to 97 exact source-passage groups, separate from the 717 training questions / 391 groups. Both partitions have historical exposure; this is not a fresh source-family-audited test.',
        '', '## Native Mistral results','',
        'Every method retains all 183 questions. Invalid and capped answers count incorrect. Original/no-context are common controls, not independently replicated budget runs.',
        '', '| Method | Accuracy | Context kept | Full prompt kept | Output tokens mean | Compression + generation seconds | Invalid |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for name,m in n['metrics'].items():
        lines.append(f"| {name} | {m['accuracy']:.2%} | {m['context_retention']:.2%} | {m['full_prompt_retention']:.2%} | {m['answer_tokens_mean']:.2f} | {m['compression_plus_generation_seconds_mean']:.4f} | {m['invalid']} |")
    lines+=['','Timings are local component accounting, including exact-reply reuse and historical teacher rank cost. They are not deployment throughput guarantees. Model setup is separate.',
        '', '## Qwen reference-budget results','',
        'These use Qwen2.5 reference-token text budgets, not verified native Qwen3.5 serving caps. The 2,196 records include 1,586 archive reuses, 31 within-run reuses and 579 new calls.',
        '', '| Method | Accuracy | Invalid |','|---|---:|---:|']
    for name,m in q['metrics'].items():lines.append(f"| {name} | {m['accuracy']:.2%} | {m['invalid']} |")
    lines+=['','## All native paired comparisons','',
        'Intervals are paired passage-cluster bootstrap 95% intervals, exploratory and unadjusted. Holm p-values adjust across these 24 comparisons, not all historical project explorations.',
        '', '| Candidate | Baseline | Difference, percentage points | 95% interval | Holm p |','|---|---|---:|---|---:|']
    for c in n['comparisons']:
        low,high=c['ci95'];lines.append(f"| {c['candidate']} | {c['baseline']} | {100*c['delta']:.2f} | [{100*low:.2f}, {100*high:.2f}] | {c['holm_p_all_comparisons']:.4f} |")
    lines+=['','## What was completed','',
        '- All 500 AI labels, with 497 valid initial GPU reviews and 30 source-based AI adjudications, including three invalid initial reviews.',
        '- Ordinal teacher training data, six-weight lexical student, and fixed two-epoch neural student; safely saved and reloaded neural checkpoint.',
        '- Qwen development comparisons and independent-family native Mistral comparisons, BM25, LLMLingua-2, XProvence and negative controls.',
        '- Exact native token and prompt replay: 3,294 verified prompts, zero native cap violations. Twelve capped and two other invalid answers remain incorrect.',
        '- Local replay of all reported metrics and 30 contrasts, 48 targeted checks covered, figures and raw evidence archive.',
        '- Failed downloads/setup attempts and negative stress-repair findings retained; no performance-driven retry or serving promotion.',
        '', '## Scope closure','',
        'No human review, inter-annotator agreement, newly human-validated corpus, or sealed confirmatory run is represented as performed. The owner has removed human review from the current workflow. Those tasks are outside this AI-only delivery, rather than pending work assigned to the owner.',
        'Future method improvements or a separate confirmatory study may use a new protocol and new data. This report does not require either to close the current delivery, and does not claim that the original superiority objective was achieved.',
        '', '## Deliverables','',
        '- Working labels: `docs/annotation/belebele_cm_ai_reviewed.csv` and adjacent `.manifest.json`.',
        '- Workbook: `outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/belebele_ai_review_corrected.xlsx`.',
        '- Machine-readable closeout: `docs/research/COMPRESSOR_AI_ONLY_FINAL.json`.',
        '- Checkpoint/raw neural outputs: `backend/data/bench/neural_student_20261116/results/`.',
        '- Figures: `backend/data/bench/compressor_figures_20261116/`.',
        '- Complete dated methods/reproduction record: `docs/research/COMPRESSOR_STATUS_20261116.md`.',
        '- Final internal archive: `outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/compressor_ai_only_final_20261116.zip`.',
        '', 'Upstream data/model licenses still apply. The archive is internal; no public upload or Git push is part of this delivery. The separate router study is unchanged.']
    (root/'docs/research/COMPRESSOR_AI_ONLY_FINAL.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({key:facts[key] for key in ['status','scope','human_input_required','scientific_quality_target_met','qa_records','native_cap_violations']}))


if __name__=='__main__':finalize(Path(__file__).resolve().parents[3])

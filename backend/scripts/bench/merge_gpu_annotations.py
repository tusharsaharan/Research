"""Merge all GPU reviews with prior AI labels; preserve sources and failures.

This produces an analysis CSV/JSON for the final workbook. No human label or
original gold is overwritten, and failed GPU rows remain explicitly unresolved.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from compressor_artifacts import digest, records, save


def merge(source,previous,review_dir,output):
    state=json.loads((review_dir/'state.json').read_text())
    spec=json.loads((review_dir/'manifest.json').read_text())
    if state['status']!='complete' or state['completed']!=500:raise ValueError('GPU review not complete')
    if digest(source)!=spec['source_sha256']:raise ValueError('Annotation source changed')
    if digest(review_dir/'raw_reviews.jsonl')!=state['raw_sha256']:raise ValueError('GPU raw reply hash mismatch')
    with source.open(encoding='utf-8-sig',newline='') as f:inputs=list(csv.DictReader(f))
    with previous.open(encoding='utf-8-sig',newline='') as f:prior={r['id']:r for r in csv.DictReader(f)}
    reviewed={}
    for row in records(review_dir/'raw_reviews.jsonl'):
        if row['id'] in reviewed:raise ValueError('Duplicate GPU review')
        reviewed[row['id']]=row
    if set(reviewed)!={r['id'] for r in inputs}:raise ValueError('GPU review ID coverage mismatch')
    rows=[];counts=Counter();disagreements=[]
    for source_row in inputs:
        item=source_row['id'];gpu=reviewed[item];result=gpu['result'];old=prior[item]
        row=dict(source_row)
        row.update(previous_ai_same_meaning=old['ai_suggested_same_meaning'],
            previous_ai_answerable_same_gold=old['ai_suggested_answerable_same_gold'],
            previous_ai_natural_hinglish=old['ai_suggested_natural_hinglish'],
            previous_ai_notes=old['ai_suggested_notes'])
        changed=[]
        for name in ['same_meaning','answerable_same_gold','natural_hinglish']:
            value='' if result is None else result[name]
            row['gpu_ai_'+name]=value
            if result is not None:
                counts[name+':'+str(value)]+=1
                if str(value)!=str(old['ai_suggested_'+name]):changed.append(name)
        row.update(gpu_ai_english_supported_option='' if result is None else result['english_supported_option'],
            gpu_ai_hinglish_supported_option='' if result is None else result['hinglish_supported_option'],
            gpu_ai_notes='' if result is None else result['notes'],
            gpu_ai_error=gpu['error'] or '',ai_changed_fields=', '.join(changed),
            review_status='GPU_AI_REVIEWED' if result is not None else 'GPU_AI_FAILED_REQUIRES_ADJUDICATION',
            provenance='AI review by '+spec['model']+'; not human-verified',gpu_model_digest=spec['digest'])
        if changed:disagreements.append(dict(id=item,fields=changed))
        counts['valid' if result is not None else 'failed']+=1
        if result is not None and result['english_supported_option']!=source_row['gold']:
            counts['source_gold_flag']+=1
        rows.append(row)
    output.mkdir(parents=True,exist_ok=True)
    with (output/'review_analysis.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    save(output/'workbook_data.json',dict(rows=rows,model=spec['model'],digest=spec['digest'],counts=dict(counts),
        disagreements=disagreements,scope='AI-assisted exposed-development review; not human validation'))
    report=dict(status='complete',rows=len(rows),counts=dict(counts),changed_rows=len(disagreements),disagreements=disagreements,
        sources=dict(source=digest(source),previous_ai=digest(previous),gpu_manifest=digest(review_dir/'manifest.json'),
                     raw_gpu=digest(review_dir/'raw_reviews.jsonl')),script_sha256=digest(Path(__file__)))
    save(output/'report.json',report)
    return {k:report[k] for k in ['status','rows','counts','changed_rows']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','previous','review-dir','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(merge(a.source,a.previous,a.review_dir,a.output),indent=2))

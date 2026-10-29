"""Sample public COMI-LINGUA text; keep original and derived Roman text separate."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

REVISION = 'f02e16a1a513cdf29cfaf20b19c007dd89d8083a'
HINDI = set('hai hain tha thi nahi nahin nhi mera meri mere mujhe tum tumhe kya kyun kaun '
            'hum ham aap apna apni aur lekin bahut bohot hoga hogi kare karna karne mein nahi'.split())


def fingerprint(text):
    return hashlib.sha256(' '.join(text.split()).encode()).hexdigest()


def eligible(text):
    return (8 <= len(text.split()) <= 350 and len(text.encode()) < 4500
            and not re.search('[\u0900-\u097f\ufffd]', text)
            and len(set(re.findall(r'[a-z]+', text.lower())) & HINDI) >= 2)


def prepare(source, out, limit=10000):
    if out.exists():
        raise ValueError('Preserve existing sample')
    groups = {}
    natural = source.with_name('MLI_train.csv')
    if natural.exists():
        with natural.open(encoding='utf-8-sig', newline='') as stream:
            for i, row in enumerate(csv.DictReader(stream)):
                text = row['Sentences'].strip()
                if (eligible(text) and sum(row.get(f'Annotated by: Annotator {j}') == 'hi'
                                          for j in (1, 2, 3)) >= 2):
                    key = fingerprint(text)
                    groups[key] = dict(uid='comi|' + key, context=text, stratum='original_roman_hindi_heuristic',
                                       source_group=key, source_csv_file=natural.name, source_csv_row=i + 2)
    with source.open(encoding='utf-8-sig', newline='') as stream:
        for i, row in enumerate(csv.DictReader(stream)):
            original = row['Sentences'].strip()
            key = fingerprint(original)
            if key in groups:
                continue
            if eligible(original):
                text, stratum = original, 'original_roman_hindi_heuristic'
            else:
                text = row.get('Annotator_1_RH_translation', '').strip()
                if not eligible(text):
                    continue
                stratum = 'derived_romanization_annotator1'
            groups[key] = dict(uid='comi|' + key, context=text, stratum=stratum,
                               source_group=key, source_csv_file=source.name, source_csv_row=i + 2)
    selected = []
    seen = set()
    ordered = sorted(groups.values(), key=lambda r: (not r['stratum'].startswith('original'), r['uid']))
    for row in ordered:
        key = fingerprint(row['context'])
        if key in seen:
            continue
        selected.append(row)
        seen.add(key)
        if len(selected) == limit:
            break
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in selected), encoding='utf-8')
    receipt = dict(items=len(selected), strata=dict(Counter(r['stratum'] for r in selected)),
        dataset='COMI-LINGUA', repository='https://github.com/lingo-iitgn/COMI-LINGUA', revision=REVISION,
        source_file=source.name, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        natural_source_sha256=hashlib.sha256(natural.read_bytes()).hexdigest() if natural.exists() else None,
        sample_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        license='CC-BY-SA-4.0 per LICENSE.txt; README says CC-BY-4.0; retain stricter license and attribution.',
        interpretation='Heuristic Roman-Hindi selection; code-mix not independently verified. '
                       'Derived romanizations separate from originals. No QA labels or semantic accuracy claim.')
    out.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.out)

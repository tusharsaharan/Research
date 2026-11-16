"""Download a frozen, native-split subset without executing dataset code."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request

REVISION = 'fbe3f6e903ee854eec2e69e9d96d0306cde59baf'
ROOT = Path('/home/user/hinglish-research/codeforces700_20261116')
FIELDS = ['id', 'title', 'description', 'input_format', 'output_format',
          'interaction_format', 'note', 'examples', 'time_limit', 'memory_limit']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import pyarrow.parquet as pq
    os.environ['HTTPS_PROXY'] = 'http://172.31.2.4:8080'
    ROOT.mkdir(parents=True, exist_ok=True)
    used_ids = {'852/A', '852/B'}
    used_text = set()
    manifest = {'dataset': 'open-r1/codeforces', 'revision': REVISION,
                'config': 'default', 'selection': 'native split/source order; first eligible unique rows',
                'excluded_exposed_ids': sorted(used_ids), 'source_files': [], 'counts': {},
                'limitations': 'Native split subset; not guaranteed contest-disjoint or model-unexposed. Checkers unvalidated; never executed.'}
    for split, count in [('train', 500), ('test', 200)]:
        selected = []
        skipped = 0
        files = [f'data/train-{i:05d}-of-00011.parquet' for i in range(11)] if split == 'train' else ['data/test-00000-of-00001.parquet']
        for source in files:
            local = ROOT / source.replace('/', '_')
            url = f'https://huggingface.co/datasets/open-r1/codeforces/resolve/{REVISION}/{source}'
            if not local.exists():
                with urllib.request.urlopen(url, timeout=300) as response, local.with_suffix('.part').open('wb') as sink:
                    while chunk := response.read(1024 * 1024):
                        sink.write(chunk)
                local.with_suffix('.part').replace(local)
            manifest['source_files'].append({'path': source, 'sha256': digest(local), 'url': url})
            for row in pq.read_table(local).to_pylist():
                keys = {row['id'], *(row.get('aliases') or [])}
                text = hashlib.sha256(' '.join((row.get('description') or '').split()).encode()).hexdigest()
                if keys & used_ids or text in used_text:
                    skipped += 1
                    continue
                selected.append(row)
                used_ids.update(keys)
                used_text.add(text)
                if len(selected) == count:
                    break
            if len(selected) == count:
                break
        assert len(selected) == count, (split, len(selected))
        for suffix, rows in [('full', selected), ('problems', [{k: r.get(k) for k in FIELDS} for r in selected])]:
            path = ROOT / f'{split}_{suffix}.jsonl'
            with path.open('w', encoding='utf-8') as out:
                for row in rows:
                    out.write(json.dumps(row, ensure_ascii=False) + '\n')
        manifest['counts'][split] = {'selected': len(selected), 'skipped_duplicates_or_exposed': skipped}
        print(split, len(selected), flush=True)
    manifest['outputs'] = {p.name: digest(p) for p in ROOT.glob('*.jsonl')}
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest['counts']), flush=True)


if __name__ == '__main__':
    main()

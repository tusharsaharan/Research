"""Reconcile saved submission IDs and audit skips without submitting anything."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import re
import time
from urllib.parse import urlencode

from codeforces_browser import evaluate
from submit_qwen_codeforces import DATA, code_from


REJECTIONS = {
    'COMPILATION_ERROR', 'RUNTIME_ERROR', 'WRONG_ANSWER', 'PRESENTATION_ERROR',
    'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED', 'IDLENESS_LIMIT_EXCEEDED',
    'SECURITY_VIOLATED', 'CRASHED', 'INPUT_PREPARATION_CRASHED', 'CHALLENGED',
}


def rows(data):
    return [json.loads(line) for line in data.splitlines()]


def write_atomic(path, data):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(data)
    tmp.replace(path)


def write_json(path, value):
    write_atomic(path, (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode())


def get_history(handle, target_id, oldest_id):
    history = {}
    for offset in range(1, 1001, 250):
        path = '/api/user.status?' + urlencode({'handle': handle, 'from': offset, 'count': 250})
        payload = evaluate(
            """(async () => {
                if (location.origin !== 'https://codeforces.com') throw Error('Expected Codeforces tab');
                const response = await fetch(PATH, {signal: AbortSignal.timeout(20000)});
                if (!response.ok) throw Error('Codeforces API HTTP ' + response.status);
                return response.json();
            })()""".replace('PATH', json.dumps(path)), target_id=target_id,
        )
        if payload['status'] != 'OK':
            raise RuntimeError(payload.get('comment', 'Codeforces API request failed'))
        page = payload['result']
        history.update((str(item['id']), item) for item in page)
        time.sleep(2)
        if len(page) < 250 or min(item['id'] for item in page) <= oldest_id:
            break
    return history


def reconcile(records, histories):
    evidence = []
    updates = Counter()
    for record in records:
        if not (submission_id := record.get('submission_id')):
            continue
        handle = record['handle']
        item = histories[handle].get(str(submission_id))
        if item is None:
            updates['missing_from_api'] += 1
            continue
        problem = item['problem']
        ident = f"{problem['contestId']}/{problem['index']}"
        authors = {member['handle'].casefold() for member in item['author']['members']}
        if ident != record['id'] or handle.casefold() not in authors:
            raise ValueError(f"Submission identity mismatch for {submission_id}")
        verdict = item.get('verdict')
        evidence.append(item)
        label = 'CORRECT' if verdict == 'OK' else 'WRONG' if verdict in REJECTIONS else None
        previous = record.get('label')
        if label is None and previous is not None:
            updates['previous_final_api_inconclusive'] += 1
            continue
        if label != previous:
            updates['new_final' if previous is None else 'changed_final'] += 1
            record['label_before_api_sync'] = previous
        record.update(label=label, api_verdict=verdict, verdict_source='Codeforces user.status')
    return evidence, updates


def review_skips(main, alternate):
    responses = {}
    problems = {}
    for split in ('train', 'test'):
        responses.update((r['id'], r['raw']) for r in rows(
            (DATA / 'qwen_answers_v1' / f'{split}_responses.jsonl').read_bytes()
        ))
        problems.update((r['id'], r) for r in rows((DATA / f'{split}_problems.jsonl').read_bytes()))
    alternates = {r['id']: r for r in alternate if r.get('submission_id')}
    groups = defaultdict(list)
    for r in main:
        if r['status'] != 'not_submitted':
            continue
        ident = r['id']
        raw = responses[ident]
        content = raw['message']['content']
        problem = problems[ident]
        item = {**r, 'generation_done_reason': raw.get('done_reason'),
                'extractable_cpp': bool(code_from(content)),
                'main_marker_in_response': bool(re.search(r'\bmain\s*\(', content)),
                'has_input_format': bool(problem.get('input_format')),
                'has_output_format': bool(problem.get('output_format')),
                'has_interaction_format': bool(problem.get('interaction_format'))}
        if ident in alternates:
            item['separately_generated_alternate'] = alternates[ident]
        groups[r['reason']].append(item)
    return dict(groups)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-id', required=True, help='ID of an open Codeforces CDP tab')
    args = parser.parse_args()
    datasets = ('official_codeforces_v1', 'alternate_languages_v1')
    paths = {name: DATA / name / 'submission_journal.jsonl' for name in datasets}
    original = {name: path.read_bytes() for name, path in paths.items()}
    records = {name: rows(data) for name, data in original.items()}
    ids_by_handle = defaultdict(set)
    for journal in records.values():
        for record in journal:
            if sid := record.get('submission_id'):
                ids_by_handle[record['handle']].add(int(sid))
    histories = {handle: get_history(handle, args.target_id, min(ids))
                 for handle, ids in ids_by_handle.items()}
    assert all(path.read_bytes() == original[name] for name, path in paths.items()), 'Journal changed during sync'
    for name in datasets:
        evidence, updates = reconcile(records[name], histories)
        counts = Counter(r['label'] or r['status'] for r in records[name])
        write_json(paths[name].with_name('api_verdict_sync.json'), {
            'fetched_at_utc': datetime.now(timezone.utc).isoformat(),
            'source': 'https://codeforces.com/apiHelp/methods#user.status',
            'input_journal_sha256': hashlib.sha256(original[name]).hexdigest(),
            'counts': dict(counts), 'updates': dict(updates), 'api_submissions': evidence,
        })
        data = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records[name]).encode()
        write_atomic(paths[name], data)
        print(name, dict(counts), dict(updates))
    groups = review_skips(*(records[name] for name in datasets))
    write_json(paths[datasets[0]].with_name('skip_review_after_sync.json'), {
        'skipped': sum(map(len, groups.values())),
        'groups': groups,
    })
    print('skip review', {reason: len(items) for reason, items in groups.items()})


if __name__ == '__main__':
    main()

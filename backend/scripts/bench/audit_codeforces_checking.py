"""Inventory checking metadata only; no dataset checker code is executed."""
import json
from pathlib import Path

root=Path('backend/data/bench/codeforces700_20261116')
report={}
for split in ('train','test'):
    rows=[json.loads(x) for x in (root/f'{split}_full.jsonl').open(encoding='utf-8')]
    report[split]={
        'problems':len(rows),
        'with_generated_checker':sum(bool(r.get('generated_checker')) for r in rows),
        'with_saved_official_tests':sum(bool(r.get('official_tests')) for r in rows),
        'marked_complete_official_tests':sum(bool(r.get('official_tests_complete')) for r in rows),
        'marked_executable':sum(bool(r.get('executable')) for r in rows),
        'saved_test_cases':sum(len(r.get('official_tests') or []) for r in rows),
        'missing_official_tests':[r['id'] for r in rows if not r.get('official_tests')],
        'with_interaction_format':[r['id'] for r in rows if r.get('interaction_format')],
    }
report['limitations']=['Metadata is not a verified judge inventory.',
    'Generated checkers may be incorrect; absent checker does not imply unjudgeable.',
    'Passing finite tests does not prove correctness on all valid inputs.']
(root/'checking_inventory.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))

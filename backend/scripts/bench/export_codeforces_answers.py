"""Export saved raw model answers with verbatim fenced C++ candidates."""
import json
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
for split, expected in [('train', 500), ('test', 200)]:
    rows = [json.loads(line) for line in (root / f'{split}_responses.jsonl').open(encoding='utf-8')]
    assert len(rows) == expected
    assert len({r['id'] for r in rows}) == expected
    with (root / f'{split}_answers.jsonl').open('w', encoding='utf-8') as out:
        for row in rows:
            text = row['raw']['message']['content']
            blocks = re.findall(r'```(?:cpp|c\+\+|cxx|C\+\+|C++)[^\n]*\n(.*?)```', text, re.DOTALL)
            out.write(json.dumps({'id': row['id'], 'split': split, 'model': row['raw'].get('model'),
                'answer': text, 'cpp_code_blocks': blocks,
                'done_reason': row['raw'].get('done_reason'),
                'code_selection': 'all matched fenced blocks, unchanged; unvalidated'}, ensure_ascii=False) + '\n')
    print(split, len(rows), 'exported')

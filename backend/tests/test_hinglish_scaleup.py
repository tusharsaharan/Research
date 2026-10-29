"""Source overlap and public-corpus provenance checks before expensive inference."""
import csv
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def scripts(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    return importlib.import_module('prepare_hinglish_scaleup'), importlib.import_module('prepare_hinglish_stress')


def test_shared_source_questions_remain_in_selection_overlap(scripts, tmp_path):
    pool, _ = scripts
    rows = [dict(id=str(i), gold='A', english={'passage': 'same' if i < 2 else 'different'},
                 hinglish=dict(passage='Yeh passage hai.', question='Kya?', options=['a', 'b', 'c', 'd']))
            for i in range(3)]
    items = tmp_path / 'items.jsonl'
    items.write_text('\n'.join(map(json.dumps, rows)))
    parent = tmp_path / 'parent'
    parent.mkdir()
    (parent / 'inputs.jsonl').write_text(json.dumps({'item_id': '0'}))
    (parent / 'manifest.json').write_text('{}')
    pool.prepare(items, parent, tmp_path / 'out')
    got = [json.loads(s) for s in (tmp_path / 'out/inputs.jsonl').read_text().splitlines()]
    assert [r['selection_source_overlap'] for r in got] == [True, True, False]
    assert all(r['historical_exposure'] for r in got)


def test_natural_and_derived_text_are_separate_and_deduplicated(scripts, tmp_path):
    _, stress = scripts
    source = tmp_path / 'MT_train.csv'
    original = 'Mera school bahut door hai lekin bus available nahi hai.'
    with source.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['Sentences', 'Annotator_1_RH_translation'])
        writer.writeheader()
        writer.writerows([{'Sentences': original, 'Annotator_1_RH_translation': ''},
                          {'Sentences': original, 'Annotator_1_RH_translation': ''},
                          {'Sentences': 'यह हिंदी है', 'Annotator_1_RH_translation':
                           'Meri train aaj bahut late hai aur kal bhi late thi.'}])
    stress.prepare(source, tmp_path / 'sample.jsonl')
    rows = [json.loads(s) for s in (tmp_path / 'sample.jsonl').read_text().splitlines()]
    assert len(rows) == 2
    assert {r['stratum'] for r in rows} == {'original_roman_hindi_heuristic', 'derived_romanization_annotator1'}
    assert rows[0]['context'] == original
    assert all('gold' not in row for row in rows)

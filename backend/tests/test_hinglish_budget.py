"""Experimental strict-budget and relational-unit invariants, without models."""
import importlib
import json
from pathlib import Path

from gateway.modules.m2_compressor.hinglish_budget import (
    character_scores, compress_ablation, split_clauses, strict_prefix,
)


def count(text):
    return len(text.split())


def test_character_ranking_handles_inflection_without_output_rewriting():
    units = ['A time clock sits upon a shelf.', 'Events allow comparison of different durations.']
    scores = character_scores(units, 'Compare events')
    assert scores[1] > scores[0]
    result = compress_ablation(' '.join(units), 'Compare events', 0.5, count, None,
                              characters=True, clauses=True)
    assert result.text == units[1]


def test_clause_preservation_keeps_original_words_and_connective():
    text = 'The tourists usually visit during the summer months, but the mountains are covered with snow in winter.'
    parts = split_clauses(text)
    assert len(parts) == 2
    assert parts[1].startswith('but ')
    assert ' '.join(parts) == text


def test_clause_split_does_not_cut_protected_quote():
    text = '"The tourists usually visit during the summer months, but the mountains are covered with snow in winter."'
    assert split_clauses(text) == [text]


def test_clauses_pack_other_evidence_when_top_unit_is_oversized():
    text = 'Question evidence is in this very long sentence with many unneeded words. Evidence is brief.'
    result = compress_ablation(text, 'Question evidence', 0.33, count, None, clauses=True)
    assert result.text == 'Evidence is brief.'
    assert result.budget_met


def test_strict_prefix_counts_nonmonotonic_candidates():
    token_counts = {'alpha beta gamma': 5, 'alpha beta': 2, 'alpha': 3, '': 0}
    assert strict_prefix('alpha beta gamma', 2, token_counts.__getitem__) == 'alpha beta'
    assert strict_prefix('alpha', 2, token_counts.__getitem__) == ''


def test_regrade_matches_audited_reverse_marker_rule(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    cpu = importlib.import_module('hinglish_cpu')
    assert cpu.revised_letter('Reasoning\nB####') == 'B'
    assert cpu.revised_letter('B####\nUncertain') is None
    assert cpu.revised_letter('#### C') == 'C'


def test_regrade_applies_same_parser_to_all_methods_and_latest_records(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    cpu = importlib.import_module('hinglish_cpu')
    monkeypatch.setattr(cpu, 'BENCH', tmp_path)
    for folder in ('belebele', 'kaggle'):
        (tmp_path / folder).mkdir()
    (tmp_path / 'belebele/items.jsonl').write_text(json.dumps(dict(id='bb-1', gold='B')) + '\n')
    answers = [dict(item_id='bb-1', model='test', methods=['original', 'candidate'], content=reply)
               for reply in ('A', 'Reasoning\nB####')]
    (tmp_path / 'kaggle/answers.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in answers))
    out = tmp_path / 'out'
    cpu.regrade('1/1', out)
    cpu.merge(out, 1)
    report = json.loads((out / 'report.json').read_text())
    assert report['records'] == 2
    assert all(g['old_accuracy'] == 0 and g['revised_accuracy'] == 1 for g in report['groups'])


def test_pilot_unique_passages_keeps_language_pairs_without_repeated_sources(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    pilot = importlib.import_module('compressor_pilot')
    monkeypatch.setattr(pilot, 'BENCH', tmp_path)
    data = []
    for i in range(120):
        language = dict(passage=f'Repeated source {i % 4}', question=f'Question {i}', options=['a','b','c','d'])
        data.append(dict(id=f'bb-{i}', gold='A', english=language, hinglish=language))
    pilot.write_rows(tmp_path / 'belebele/items.jsonl', data)
    out = tmp_path / 'prepared'
    pilot.prepare(4, out, methods=['bm25_strict'], datasets=['belebele'], unique_passages=True)
    inputs = pilot.read_jsonl(out / 'inputs.jsonl')
    assert len(inputs) == 8
    for group in {r['passage_group'] for r in inputs}:
        pair = [r for r in inputs if r['passage_group'] == group]
        assert len(pair) == 2 and {r['lang'] for r in pair} == {'english', 'hinglish'}

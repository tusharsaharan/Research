"""Closeout must reject edited raw outputs and duplicate coverage."""
import importlib
import json
from pathlib import Path
import pytest


@pytest.mark.parametrize('failure',['edited_raw','duplicate_identity'])
def test_closeout_does_not_trust_completion_state_alone(tmp_path,monkeypatch,failure):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts/bench'))
    module=importlib.import_module('finalize_compressor_ai_only')
    artifacts=importlib.import_module('compressor_artifacts')
    rows=[dict(uid='a',method='original'),dict(uid='b',method='original')]
    def write_answers(values):
        (tmp_path/'answers.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in values))
    write_answers(rows)
    (tmp_path/'variants.jsonl').write_text('{}\n')
    state=dict(status='complete',answers_sha256=artifacts.digest(tmp_path/'answers.jsonl'),
        variants_sha256=artifacts.digest(tmp_path/'variants.jsonl'))
    artifacts.save(tmp_path/'state.json',state)
    assert module.verify_run(tmp_path,2)['status']=='complete'
    if failure=='edited_raw':
        write_answers(rows+[dict(uid='c',method='original')])
        match='Changed raw'
    else:
        write_answers([rows[0],rows[0]])
        state['answers_sha256']=artifacts.digest(tmp_path/'answers.jsonl')
        artifacts.save(tmp_path/'state.json',state)
        match='coverage'
    with pytest.raises(ValueError,match=match):module.verify_run(tmp_path,2)

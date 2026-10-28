"""Campaign accounting, duplicate prevention and remote upload verification."""
import importlib
import time
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def campaign(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    module = importlib.import_module('compressor_campaign')
    monkeypatch.setattr(module, 'BENCH', tmp_path)
    for revision in (13, 14, 15, 16):
        data = tmp_path / f'compressor_pilot_v{revision}'
        data.mkdir()
        (data / 'inputs.jsonl').write_text('{}\n')
        with zipfile.ZipFile(data / 'source.zip', 'w') as archive:
            archive.writestr('code.py', 'VALUE = 1\n')
        manifest = dict(source_sha256=module.sha(data / 'source.zip'),
                        inputs_sha256=module.sha(data / 'inputs.jsonl'), answer_model='test',
                        max_seconds=3300, units=2, methods=['candidate'], rates=[0.5, 0.33])
        module.save(data / 'manifest.json', manifest)
    return module


def test_init_caps_total_compute_and_is_immutable(campaign, tmp_path):
    out = tmp_path / 'campaign'
    state = campaign.init(out, [13, 14, 15, 16])
    assert state['total_runtime_cap_seconds'] == 13200
    assert sum(j['expected_answers'] for j in state['jobs']) == 24
    with pytest.raises(ValueError, match='already exists'):
        campaign.init(out, [13])
    with pytest.raises(ValueError, match='exceed'):
        campaign.init(tmp_path / 'short', [13, 14, 15, 16], hours=3)


def test_changed_frozen_source_is_rejected(campaign, tmp_path):
    (tmp_path / 'compressor_pilot_v13/source.zip').write_bytes(b'changed')
    with pytest.raises(ValueError, match='Changed frozen artifact'):
        campaign.init(tmp_path / 'campaign', [13])


@pytest.mark.parametrize('tamper', [None, 'inputs.jsonl', 'manifest.json', 'source/code.py'])
def test_remote_recovery_requires_exact_all_file_equality(campaign, tmp_path, tamper):
    data = tmp_path / 'compressor_pilot_v13'
    remote = tmp_path / 'remote'
    (remote / 'source').mkdir(parents=True)
    for name in ('inputs.jsonl', 'manifest.json'):
        (remote / name).write_bytes((data / name).read_bytes())
    (remote / 'source/code.py').write_bytes(b'VALUE = 1\n')
    if tamper:
        (remote / tamper).write_bytes(b'changed')
        with pytest.raises(ValueError, match='differs'):
            campaign.verify_download(data, remote)
    else:
        campaign.verify_download(data, remote)


def test_status_parser_does_not_confuse_errors_with_results(campaign):
    assert campaign.kernel_status('has status "KernelWorkerStatus.COMPLETE"') == 'done'
    assert campaign.kernel_status('Permission denied; perhaps not found') == 'unknown'
    assert campaign.kernel_status('has status "KernelWorkerStatus.ERROR"') == 'failed'


def test_existing_launch_is_never_resubmitted_and_concurrency_is_bounded(campaign, monkeypatch, tmp_path):
    out = tmp_path / 'campaign'
    campaign.init(out, [13, 14, 15, 16])
    (tmp_path / 'compressor_pilot_v13/launch.json').write_text('{}')
    monkeypatch.setattr(campaign, 'account_env', lambda _: {'KAGGLE_USERNAME': 'owner'})
    monkeypatch.setattr(campaign, 'owned_kernels', lambda *_: set())
    submissions = []

    def command(args, *a, **kw):
        revision = int(args[args.index('--revision') + 1])
        if 'status' in args:
            return 0, 'KernelWorkerStatus.RUNNING'
        assert 'push' in args
        submissions.append(revision)
        (tmp_path / f'compressor_pilot_v{revision}/launch.json').write_text('{}')
        return 0, 'submitted'

    monkeypatch.setattr(campaign, 'command', command)
    campaign.advance(out, tmp_path)
    assert submissions == [14]
    assert [j['status'] for j in campaign.load(out / 'campaign.json')['jobs']] == [
        'running', 'queued', 'pending', 'pending',
    ]


def test_expired_window_skips_work_without_launch(campaign, monkeypatch, tmp_path):
    out = tmp_path / 'campaign'
    state = campaign.init(out, [13])
    state['deadline'] = time.time() - 1
    campaign.save(out / 'campaign.json', state)
    monkeypatch.setattr(campaign, 'account_env', lambda _: {'KAGGLE_USERNAME': 'owner'})
    monkeypatch.setattr(campaign, 'owned_kernels', lambda *_: set())
    monkeypatch.setattr(campaign, 'command', lambda *_a, **_kw: pytest.fail('Expired work must not launch'))
    campaign.advance(out, tmp_path)
    assert campaign.load(out / 'campaign.json')['jobs'][0]['status'] == 'skipped'


def test_active_lock_prevents_a_second_advance(campaign, tmp_path, monkeypatch):
    out = tmp_path / 'campaign'
    campaign.init(out, [13])
    (out / 'advance.lock').write_text('active')
    monkeypatch.setattr(campaign, 'account_env', lambda _: pytest.fail('No calls while locked'))
    campaign.advance(out, tmp_path)
    assert (out / 'advance.lock').exists()

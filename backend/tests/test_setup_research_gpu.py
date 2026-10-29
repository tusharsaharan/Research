"""Check GPU setup preconditions and proxy handling without installing anything."""
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts'))
    return importlib.import_module('setup_research_gpu')


def test_proxy_is_scoped_and_retains_local_bypass(setup, monkeypatch):
    monkeypatch.setenv('NO_PROXY', 'college.local')
    env = setup.proxy_environment('http://172.31.2.4:8080')
    assert env['HTTPS_PROXY'] == env['https_proxy'] == 'http://172.31.2.4:8080'
    assert set(env['NO_PROXY'].split(',')) >= {'college.local', 'localhost', '127.0.0.1', '::1'}
    assert setup.os.environ['NO_PROXY'] == 'college.local'


@pytest.mark.parametrize('proxy', ['socks5://host:1080', 'http://name:password@host:8080', 'invalid'])
def test_credential_proxy_rejected(setup, proxy):
    with pytest.raises(ValueError, match='without embedded credentials'):
        setup.proxy_environment(proxy)


def test_no_install_on_cpu_or_windows(setup, monkeypatch, tmp_path):
    monkeypatch.setattr(setup.platform, 'system', lambda: 'Linux')
    with pytest.raises(RuntimeError, match='working nvidia-smi'):
        setup.install(tmp_path / 'env', None, {'gpus': []})
    monkeypatch.setattr(setup.platform, 'system', lambda: 'Windows')
    with pytest.raises(RuntimeError, match='Linux'):
        setup.install(tmp_path / 'env', None, {'gpus': [{'driver': '580.1'}]})
    assert not (tmp_path / 'env').exists()


def test_inspection_does_not_install_or_import_torch(setup, monkeypatch):
    monkeypatch.setattr(setup.shutil, 'which', lambda name: None)
    report = setup.inventory()
    assert not report['gpus'] and not report['tmux']
    assert 'torch' not in setup.__dict__

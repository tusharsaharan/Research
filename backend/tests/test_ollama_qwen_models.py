"""Local-only inference and successful streamed model-pull receipts."""
import importlib
import io
from pathlib import Path

import pytest


@pytest.fixture
def models(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts'))
    return importlib.import_module('ollama_qwen_models')


@pytest.mark.parametrize('host', ['https://api.example.com', 'http://remote:11434',
                                'http://name:password@localhost:11434', 'http://localhost/path'])
def test_remote_or_credential_endpoint_rejected(models, host):
    with pytest.raises(ValueError, match='loopback'):
        models.LocalOllama(host)


@pytest.mark.parametrize('body', [b'{"status":"pulling manifest"}\n', b'{"error":"model not found"}\n'])
def test_incomplete_pull_not_marked_success(models, monkeypatch, body):
    api = models.LocalOllama('http://127.0.0.1:11435')
    monkeypatch.setattr(api, 'open', lambda *args: io.BytesIO(body))
    with pytest.raises(RuntimeError):
        api.pull('qwen3.5:4b', lambda event: None)


def test_streamed_pull_waits_for_success_receipt(models, monkeypatch):
    api = models.LocalOllama('http://127.0.0.1:11435')
    events = []
    monkeypatch.setattr(api, 'open', lambda *args: io.BytesIO(b'{"status":"pulling manifest"}\n{"status":"success"}\n'))
    api.pull('qwen3.5:4b', events.append)
    assert events[-1]['status'] == 'success'

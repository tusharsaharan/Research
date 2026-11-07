"""Resumable upload protocol checks without credentials or network calls."""
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests


@pytest.fixture
def transport(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    module = importlib.import_module('kaggle_upload_bounded')
    target = tmp_path / 'manifest.json'
    target.write_bytes(b'abcdef')
    calls, responses = [], []

    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def put(self, url, **kwargs):
            calls.append(dict(kwargs, payload=kwargs['data'].read() if 'data' in kwargs else None))
            response = responses.pop(0)
            if isinstance(response, Exception): raise response
            return response

    monkeypatch.setattr(module.requests, 'Session', Session)
    return module, target, calls, responses


def test_resumes_only_unreceived_bytes_with_timeouts(transport):
    module, path, calls, responses = transport
    responses.extend([SimpleNamespace(status_code=308, headers={'Range': 'bytes=0-1'}), SimpleNamespace(status_code=200)])
    assert module.upload(path, 'https://example.test/private', True) == 'COMPLETE'
    assert calls[1]['payload'] == b'cdef'
    assert calls[1]['headers']['Content-Range'] == 'bytes 2-5/6'
    assert all(c['timeout'] == (15, 45) for c in calls)


def test_already_complete_upload_is_not_repeated(transport):
    module, path, calls, responses = transport
    responses.append(SimpleNamespace(status_code=200))
    assert module.upload(path, 'https://example.test/private', True) == 'COMPLETE'
    assert len(calls) == 1


def test_timeout_retains_resume_state_without_leaking_url(transport, capsys):
    module, path, _, responses = transport
    responses.append(requests.ReadTimeout('https://example.test/?secret=credential'))
    assert module.upload(path, 'https://example.test/private') == 'INCOMPLETE'
    assert 'credential' not in capsys.readouterr().out


def test_expired_session_fails_without_resending(transport):
    module, path, calls, responses = transport
    responses.append(SimpleNamespace(status_code=404))
    assert module.upload(path, 'https://example.test/private', True) == 'FAILED'
    assert len(calls) == 1

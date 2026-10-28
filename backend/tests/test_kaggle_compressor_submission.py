"""A recovered blob-upload error must not hide a successful dataset receipt."""
import importlib
from pathlib import Path

import pytest


@pytest.mark.parametrize('code, prefix, suffix, expected', [
    (0, 'inputs.jsonl: ConnectionError; retaining resumable state\nUpload successful\n', 'owner/data', True),
    (0, '', 'owner/data', True),
    (1, '', 'owner/data', False),
    (0, '', 'other/data', False),
])
def test_creation_requires_correct_success_receipt(monkeypatch, code, prefix, suffix, expected):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    launcher = importlib.import_module('kaggle_compressor')
    output = prefix + 'Your private Dataset is being created. Please check progress at https://www.kaggle.com/datasets/' + suffix
    assert launcher.dataset_creation_succeeded(code, output, 'owner/data') is expected


def test_no_receipt_is_not_success(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    launcher = importlib.import_module('kaggle_compressor')
    for output in ('403 Forbidden', 'Dataset already exists', 'Upload successful: source.zip'):
        assert not launcher.dataset_creation_succeeded(0, output, 'owner/data')

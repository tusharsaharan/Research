"""Small shared helpers for reproducible compressor development artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def records(path: Path):
    with path.open(encoding='utf-8-sig') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def verify_archive(data: Path, names: list[str]) -> dict[str, str]:
    receipt = json.loads((data / 'RESTORE_RECEIPT.json').read_text(encoding='utf-8'))
    expected = {Path(row['path']).name: row['sha256'] for row in receipt['files']}
    actual = {}
    for name in names:
        if name not in expected:
            raise ValueError('No archived checksum for ' + name)
        actual[name] = digest(data / name)
        if actual[name] != expected[name]:
            raise ValueError('Archived evidence changed: ' + name)
    return actual

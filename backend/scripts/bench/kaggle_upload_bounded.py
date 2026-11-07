"""Kaggle CLI entry point with bounded blob PUTs and resumable status checks.

The installed CLI leaves both PUT paths without HTTP timeouts. This wrapper is
process-local; it neither changes the installed package nor prints signed URLs.
"""
from __future__ import annotations

import re
from pathlib import Path

import requests


def upload(path, url, resume=False):
    path = Path(path)
    size = path.stat().st_size
    start = 0
    try:
        with requests.Session() as session:
            if resume:
                status = session.put(url, headers={'Content-Length': '0', 'Content-Range': f'bytes */{size}'},
                                     timeout=(15, 45))
                if status.status_code in (200, 201):
                    return 'COMPLETE'
                if status.status_code == 503:
                    return 'INCOMPLETE'
                if status.status_code != 308:
                    print(f'{path.name}: resume HTTP {status.status_code}', flush=True)
                    return 'FAILED'
                received = status.headers.get('Range')
                if received:
                    match = re.fullmatch(r'bytes=0-(\d+)', received)
                    if not match:
                        return 'FAILED'
                    start = int(match[1]) + 1
            if not 0 <= start <= size:
                return 'FAILED'
            headers = {'Content-Length': str(size - start)}
            if start:
                headers['Content-Range'] = f'bytes {start}-{size - 1}/{size}'
            print(f'{path.name}: uploading {size - start} remaining bytes', flush=True)
            with path.open('rb') as stream:
                stream.seek(start)
                response = session.put(url, data=stream, headers=headers, timeout=(15, 45))
            if response.status_code in (200, 201):
                return 'COMPLETE'
            if response.status_code in (308, 503):
                return 'INCOMPLETE'
            print(f'{path.name}: upload HTTP {response.status_code}', flush=True)
            return 'FAILED'
    except requests.RequestException as error:
        # Exception strings can contain upload credentials in signed URLs.
        print(f'{path.name}: {type(error).__name__}; retaining resumable state', flush=True)
        return 'INCOMPLETE'


def main():
    from kaggle.api.kaggle_api_extended import KaggleApi, ResumableUploadResult
    from kaggle.cli import main as cli_main

    def bounded(self, path, url, quiet, resume=False):
        return getattr(ResumableUploadResult, upload(path, url, resume))

    KaggleApi.upload_complete = bounded
    KaggleApi.MAX_UPLOAD_RESUME_ATTEMPTS = 3
    cli_main()


if __name__ == '__main__':
    main()

"""Prepare a user-owned Linux CUDA environment for the Hinglish compressor.

Default: inventory only. --install creates an isolated venv and installs the
pilot dependencies; it does not download model weights or launch experiments.
Official wheel command: https://pytorch.org/get-started/previous-versions/#v2-7-1
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from urllib.parse import urlsplit

TORCH = '2.7.1'
TORCH_INDEX = 'https://download.pytorch.org/whl/cu118'
PACKAGES = ('llmlingua==0.2.2', 'transformers==4.57.1', 'accelerate>=0.34,<2',
            'tiktoken', 'pydantic>=2,<3', 'scipy', 'sentencepiece', 'psutil')
CUDA_CHECK = '''
import importlib.metadata, json
import torch
from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer
from llmlingua import PromptCompressor
if not torch.cuda.is_available():
    raise RuntimeError('CUDA unavailable: check the installed NVIDIA driver and wheel')
a = torch.ones((32, 32), device='cuda')
b = a @ a
torch.cuda.synchronize()
assert bool(torch.all(b == 32)), 'GPU matrix multiplication failed'
print(json.dumps(dict(status='passed', gpu=torch.cuda.get_device_name(0),
    cuda_runtime=torch.version.cuda, total_memory_bytes=torch.cuda.get_device_properties(0).total_memory,
    versions={p: importlib.metadata.version(p) for p in
              ('torch', 'transformers', 'llmlingua', 'accelerate')})))
'''


def proxy_environment(proxy):
    env = os.environ.copy()
    if proxy:
        parsed = urlsplit(proxy)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Use an http(s) proxy URL without embedded credentials')
        for key in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'):
            env[key] = proxy
    bypass = set(env.get('NO_PROXY', env.get('no_proxy', '')).split(',')) - {''}
    env['NO_PROXY'] = env['no_proxy'] = ','.join(sorted(bypass | {'localhost', '127.0.0.1', '::1'}))
    return env


def inventory():
    gpus = []
    if shutil.which('nvidia-smi'):
        result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.free,driver_version',
                                 '--format=csv,noheader,nounits'], capture_output=True, text=True,
                                timeout=20, check=True)
        for row in csv.reader(result.stdout.splitlines()):
            index, name, total, free, driver = [cell.strip() for cell in row]
            gpus.append(dict(index=int(index), name=name, total_mib=int(total), free_mib=int(free), driver=driver))
    return dict(platform=platform.system(), python=sys.version.split()[0], gpus=gpus,
                tmux=bool(shutil.which('tmux')), ollama=bool(shutil.which('ollama')))


def runtime_values(prefix, env):
    values = dict(HF_HOME=str(prefix / 'cache' / 'huggingface'), TOKENIZERS_PARALLELISM='false',
                  OMP_NUM_THREADS=str(min(14, os.cpu_count() or 1)),
                  MKL_NUM_THREADS=str(min(14, os.cpu_count() or 1)),
                  NO_PROXY=env['NO_PROXY'], no_proxy=env['no_proxy'])
    return values


def install(prefix, proxy, report):
    if platform.system() != 'Linux' or not report['gpus']:
        raise RuntimeError('Install requires Linux and a working nvidia-smi GPU inventory')
    if not (3, 10) <= sys.version_info[:2] <= (3, 13):
        raise RuntimeError('Run this setup with Python 3.10-3.13')
    if min(tuple(map(int, g['driver'].split('.'))) for g in report['gpus']) < (520, 61, 5):
        raise RuntimeError('CUDA 11.8 setup requires NVIDIA driver 520.61.05 or newer; ask the administrator')
    prefix.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(prefix).free < 8 * 1024**3:
        raise RuntimeError('Keep at least 8 GiB free for the Python/CUDA environment; model weights need more')
    env = proxy_environment(proxy)
    values = runtime_values(prefix, env)
    env.update(values)
    environment = prefix / '.venv'
    python = environment / 'bin' / 'python'
    if not environment.exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    if not python.exists() or not (environment / 'pyvenv.cfg').exists():
        raise RuntimeError('Existing .venv is incomplete; choose a new --prefix')
    (prefix / 'logs').mkdir(exist_ok=True)
    (prefix / 'cache' / 'huggingface').mkdir(parents=True, exist_ok=True)
    log = prefix / 'logs' / 'setup.log'
    with log.open('a', encoding='utf-8') as stream:
        stream.write('\nStarting isolated GPU dependency setup\n')
        stream.flush()
        for args in (['install', '--upgrade', 'pip'],
                     ['install', 'torch==' + TORCH, '--index-url', TORCH_INDEX],
                     ['install', *PACKAGES], ['check']):
            subprocess.run([str(python), '-m', 'pip', *args], env=env, stdout=stream,
                           stderr=subprocess.STDOUT, check=True, timeout=3600)
        checked = subprocess.run([str(python), '-c', CUDA_CHECK], env=env, capture_output=True,
                                 text=True, timeout=120)
        stream.write(checked.stdout + checked.stderr)
        stream.flush()
        checked.check_returncode()
    report['cuda_check'] = json.loads(checked.stdout.strip().splitlines()[-1])
    with (prefix / 'requirements.lock.txt').open('w', encoding='utf-8') as stream:
        subprocess.run([str(python), '-m', 'pip', 'freeze'], env=env, stdout=stream, check=True, timeout=30)
    # Proxy credentials are never persisted. A credential-free college proxy
    # supplied explicitly by the user is useful for later model downloads.
    if proxy:
        values.update({key: proxy for key in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy')})
    lines = ['# Generated environment for the Hinglish research workspace.']
    lines += ['export ' + key + '=' + shlex.quote(value) for key, value in values.items()]
    lines.append('source ' + shlex.quote(str(environment / 'bin' / 'activate')))
    (prefix / 'activate.sh').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    report.update(status='ready', prefix=str(prefix), log=str(log), model_weights='not downloaded',
                  experiments='not started')
    (prefix / 'setup.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, default=Path.home() / 'hinglish-research')
    parser.add_argument('--proxy', help='Optional college HTTP(S) proxy, without credentials')
    parser.add_argument('--install', action='store_true', help='Install packages; default only inspects the host')
    args = parser.parse_args()
    report = inventory()
    if args.install:
        report = install(args.prefix.expanduser().absolute(), args.proxy, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

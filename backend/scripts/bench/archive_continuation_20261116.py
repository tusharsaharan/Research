"""Package this completed continuation only; no inference or public upload."""
from pathlib import Path
import argparse
import subprocess
import sys

SOURCES=[
    'backend/data/bench/restored_evidence_20261116/RESTORE_RECEIPT.json',
    'backend/data/bench/restored_audit_20261116',
    'backend/data/bench/atomic_replay_20261116',
    'backend/data/bench/compact_student_20261116',
    'backend/data/bench/power_analysis_20261116.json',
    'backend/data/bench/compressor_development_20261116',
    'backend/data/bench/qwen_student_20261116',
    'backend/data/bench/mistral_native_20261116',
    'backend/data/bench/neural_student_20261116',
    'backend/data/bench/compressor_figures_20261116',
    'backend/data/bench/gpu_annotation_review_20261116',
    'backend/data/training/compressor_distill_20261116',
    'backend/src','backend/scripts','backend/tests/test_compressor_development.py',
    'backend/tests/test_compact_student.py','backend/tests/test_hinglish_evidence_repair.py',
    'backend/tests/test_qwen_evidence_campaign.py',
    'docs/annotation','docs/research/PREREG.md','docs/research/COMPRESSOR_STATUS_20261116.md',
    'docs/research/COMPRESSOR_HUMAN_INPUT_20261116.md','docs/research/COMPRESSOR_DATA_CARD.md',
    'README.md','AGENTS.md','TO-DO-EXECUTION-PLAN.md','to-do.md',
    'outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/belebele_ai_review_corrected.xlsx',
]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[3]
    command=[sys.executable,str(Path(__file__).with_name('archive_evidence.py')),'--output',str(a.output),
        '--scope-note','Internal compressor continuation; exposed development and provisional AI annotations, not confirmation. Historical evidence dependency SHA-256 7ebce5a3ae1dfc8abb3f9643475731a87168b8adc9506e12435465885ac42d91. Original data/model licenses apply; no public release or full base weights.']
    for source in SOURCES:command.extend(['--source',source])
    subprocess.run(command,cwd=root,check=True)

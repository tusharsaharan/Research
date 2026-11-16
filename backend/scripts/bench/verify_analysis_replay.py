"""Compare saved analysis metrics/contrasts to an independent offline replay."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from compressor_artifacts import digest,save


def compare(left,right,path='root'):
    if isinstance(left,dict):
        if not isinstance(right,dict) or set(left)!=set(right):raise ValueError('Keys differ: '+path)
        for key in left:compare(left[key],right[key],path+'.'+key)
    elif isinstance(left,list):
        if not isinstance(right,list) or len(left)!=len(right):raise ValueError('List differs: '+path)
        for i,(a,b) in enumerate(zip(left,right)):compare(a,b,path+f'[{i}]')
    elif isinstance(left,(int,float)) and not isinstance(left,bool):
        if not isinstance(right,(int,float)) or not math.isclose(left,right,rel_tol=1e-12,abs_tol=1e-12):
            raise ValueError('Number differs: '+path)
    elif left!=right:raise ValueError('Value differs: '+path)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',type=Path,required=True);p.add_argument('--replay',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();left=json.loads(a.original.read_text());right=json.loads(a.replay.read_text())
    for key in ['metrics','comparisons']:compare(left[key],right[key],key)
    save(a.output,dict(status='verified',cells=len(left['metrics']),comparisons=len(left['comparisons']),
        original_sha256=digest(a.original),replay_sha256=digest(a.replay),relative_and_absolute_tolerance=1e-12,
        script_sha256=digest(Path(__file__))))
    print(json.dumps(dict(status='verified',cells=len(left['metrics']),comparisons=len(left['comparisons']))))

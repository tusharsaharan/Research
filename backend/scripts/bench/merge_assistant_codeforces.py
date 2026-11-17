"""Merge completed assistant shards without filling missing answers."""
import hashlib
import json
from pathlib import Path

ROOT=Path('backend/data/bench/codeforces700_20261116')
OUT=ROOT/'assistant_answers_v1'


def main():
    records={}
    for split in ('train','test'):
        for line in (OUT/f'{split}_answers.jsonl').open(encoding='utf-8'):
            r=json.loads(line)
            if r.get('cpp_code') or r.get('status')=='unsupported_cpp':
                records[r['id']]=r
    for path in sorted(OUT.glob('shard*.jsonl')):
        for line in path.open(encoding='utf-8'):
            try:
                row=json.loads(line)
            except json.JSONDecodeError:
                raise RuntimeError(f'Incomplete shard write: {path}')
            assert (row.get('cpp_code') or row.get('status')=='unsupported_cpp') and row.get('explanation'), (path,row.get('id'))
            if row['id'] in records:
                assert records[row['id']].get('cpp_code')==row.get('cpp_code'), row['id']
            records[row['id']]=row
    summary={'status':'partial','authored':{},'unsupported_cpp':{},'pending':{},'output_sha256':{},
             'validation':'First 3 train answers sample-assisted; new shards unexecuted. Not certified correct.',
             'model_provenance':'Current assistant and delegated agents; exact backend model/version unavailable.'}
    selected=set()
    for split,expected in [('train',500),('test',200)]:
        rows=[json.loads(x) for x in (ROOT/f'{split}_problems.jsonl').open(encoding='utf-8')]
        assert len(rows)==expected
        summary['authored'][split]=0
        summary['unsupported_cpp'][split]=0
        temp=OUT/f'{split}_answers.jsonl.tmp'
        with temp.open('w',encoding='utf-8') as sink:
            for problem in rows:
                ident=problem['id'];selected.add(ident)
                if ident in records:
                    record=records[ident]
                    assert record['split']==split
                    if record.get('status')=='unsupported_cpp':
                        summary['unsupported_cpp'][split]+=1
                    else:
                        summary['authored'][split]+=1
                else:
                    record={'id':ident,'split':split,'status':'pending','cpp_code':None,'explanation':None}
                sink.write(json.dumps(record,ensure_ascii=False)+'\n')
        path=OUT/f'{split}_answers.jsonl'
        temp.replace(path)
        summary['pending'][split]=expected-summary['authored'][split]-summary['unsupported_cpp'][split]
        summary['output_sha256'][path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    assert records.keys()<=selected
    if sum(summary['pending'].values())==0:summary['status']='collection_complete'
    (OUT/'collection_status.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))


if __name__=='__main__':main()

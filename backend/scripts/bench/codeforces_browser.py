"""Local CDP bridge; authentication stays in the dedicated Chrome profile."""
import json
import sys
import urllib.request
import websocket
import os
from pathlib import Path


def evaluate(expression, *, target_id=None):
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    tabs=json.load(op.open('http://127.0.0.1:9223/json/list',timeout=10))
    target_file=Path(os.environ['LOCALAPPDATA'])/'CodexCodeforcesResearch/research_target.json'
    if target_id is None and target_file.exists():
        target_id=json.loads(target_file.read_text())['target_id']
    if target_id is not None:
        tab=next((t for t in tabs if t.get('id')==target_id),None)
        if tab is None:raise RuntimeError('Dedicated submission tab was closed; restore explicitly, never switch to another user tab')
    else:
        tab=next(t for t in tabs if t.get('type')=='page' and 'codeforces.com' in t.get('url',''))
    ws=websocket.create_connection(tab['webSocketDebuggerUrl'],timeout=330,suppress_origin=True)
    ws.send(json.dumps({'id':1,'method':'Runtime.evaluate','params':{
        'expression':expression,'returnByValue':True,'awaitPromise':True}}))
    try:
        while True:
            reply=json.loads(ws.recv())
            if reply.get('id')==1:
                if reply.get('error') or reply.get('result',{}).get('exceptionDetails'):
                    raise RuntimeError(str(reply))
                return reply.get('result',{}).get('result',{}).get('value')
    finally:ws.close()


if __name__=='__main__':
    expression=sys.stdin.read()
    print(json.dumps(evaluate(expression),ensure_ascii=True))

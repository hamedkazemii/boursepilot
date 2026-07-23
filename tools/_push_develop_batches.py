#!/usr/bin/env python3
import json,time
from pathlib import Path
from gumloop import Gumloop
client=Gumloop()
root=Path('/tmp/push_batches')
files=sorted(root.glob('args*.json'), key=lambda p:int(p.stem.replace('args','')))
for i,fp in enumerate(files):
    args=json.loads(fp.read_text(encoding='utf-8'))
    resp=client.mcp.execute('github','create_or_update_file', args)
    r=resp.results[0]
    if r.status!='success':
        print('FAIL',i,r.error); raise SystemExit(1)
    print('OK',i, fp.name)
    time.sleep(0.35)
print('ALL_OK', len(files))

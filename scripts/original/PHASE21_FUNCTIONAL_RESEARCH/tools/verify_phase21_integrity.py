#!/usr/bin/env python3
"""Read-only aggregate integrity verifier for Phase 21 artifacts."""
import glob, hashlib, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
fail=[]
def req(cond,msg):
    if not cond: fail.append(msg)
# Checkpoint invariant.
cp=json.loads((ROOT/'CHECKPOINT.json').read_text())
req(cp.get('status') == 'IN_PROGRESS', 'checkpoint status is not IN_PROGRESS')
req(cp.get('complete') is False, 'checkpoint complete is not false')
# Every evidence JSON must parse.
json_files=glob.glob(str(ROOT/'evidence/**/*.json'), recursive=True)
for name in json_files:
    try: json.loads(pathlib.Path(name).read_text())
    except Exception as e: fail.append(f'JSON parse failed: {name}: {e}')
# Matrix hashes must match current artifacts.
m=json.loads((ROOT/'evidence/requirement_matrix.json').read_text())
for row in m.get('rows',[]):
    p=ROOT/row['artifact']; req(p.exists(),f"matrix artifact missing: {row['artifact']}")
    if p.exists(): req(hashlib.sha256(p.read_bytes()).hexdigest()==row.get('sha256'),f"matrix hash mismatch: {row['artifact']}")
# Blocker evidence paths must resolve.
b=json.loads((ROOT/'evidence/blocker_register.json').read_text())
req(len(b.get('rows',[])) == 5, 'blocker register does not contain 5 rows')
for row in b.get('rows',[]):
    req(row.get('status') in ('OPEN', 'CLOSED'),f"blocker {row.get('id')} has invalid status")
    if row.get('status') == 'CLOSED':
        req(row.get('id') == 'B-RUNTIME-TARGET', 'unexpected closed blocker requires evidence review')
        capture=json.loads((ROOT/'evidence/target_live_20261104/target_package.json').read_text())
        observed={item['result'].get('path'):item['result'] for item in capture['records'] if item['kind']=='read'}
        for field,expected in [('vendor','0x10de'),('device','0x1f0b')]:
            value=observed.get('/sys/bus/pci/devices/0000:03:00.0/'+field,{})
            req(value.get('ok') and value.get('text','').strip()==expected, 'closed runtime blocker lacks matching live PCI identity')
    for ref in row.get('evidence',[]): req((ROOT/ref).exists(),f"blocker evidence missing: {ref}")
# Required report files.
for rel in ('PHASE21_CURRENT_STATE.md','EVIDENCE_LEDGER.md','REQUIREMENTS_AUDIT.md'):
    req((ROOT/rel).is_file() and (ROOT/rel).stat().st_size>0,f'report missing/empty: {rel}')
print(json.dumps({'status':'PASS' if not fail else 'FAIL','json_count':len(json_files),'blocker_count':len(b.get('rows',[])),'failures':fail},indent=2))
sys.exit(0 if not fail else 1)

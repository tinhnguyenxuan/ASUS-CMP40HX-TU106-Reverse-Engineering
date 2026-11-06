#!/usr/bin/env python3
"""Verify provenance/schema of a Phase 21 target package; no hardware access."""
import argparse, hashlib, json, pathlib, sys

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('package', type=pathlib.Path); a=ap.parse_args()
    p=a.package; d=json.loads(p.read_text())
    assert d.get('schema') == 'phase21-target-package-v1'
    assert d.get('read_only') is True
    assert d.get('bdf') == '0000:03:00.0'
    assert isinstance(d.get('created_utc'), str) and d['created_utc'].endswith(('+00:00','Z'))
    records=d.get('records'); assert isinstance(records,list) and records
    for rec in records:
        assert rec.get('kind') in ('read','command')
        r=rec['result']; assert isinstance(r,dict)
        assert isinstance(r.get('started_utc'),str)
        if rec['kind']=='command':
            assert isinstance(r.get('argv'),list) and r['argv']
            assert ('returncode' in r) or ('status' in r)
    sums=p.parent/'SHA256SUMS'; assert sums.exists()
    expected=sums.read_text().split()[0]; actual=hashlib.sha256(p.read_bytes()).hexdigest(); assert expected==actual
    print(f'package schema/provenance PASS; records={len(records)}; sha256={actual}')
if __name__=='__main__': main()

#!/usr/bin/env python3
"""Verify published sha256 checksums for files in this repository. No external deps."""
from pathlib import Path
import hashlib,sys
root=Path(__file__).resolve().parents[1]
listfile=root/'manifests'/'PUBLIC_SHA256SUMS.txt'
failed=0;count=0
for raw in listfile.read_text(encoding='utf-8').splitlines():
    if not raw or raw.startswith('#'):continue
    digest, rel=raw.split('  ',1)
    target=(root/rel).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        print('MISSING/UNSAFE',rel);failed+=1;continue
    h=hashlib.sha256()
    with target.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    count+=1
    if h.hexdigest()!=digest:print('MISMATCH',rel);failed+=1
print(f'Verified {count} files; failures={failed}')
sys.exit(1 if failed else 0)

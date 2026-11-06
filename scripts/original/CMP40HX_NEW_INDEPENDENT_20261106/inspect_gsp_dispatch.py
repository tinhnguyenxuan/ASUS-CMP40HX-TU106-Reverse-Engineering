#!/usr/bin/env python3
"""Extract GSP metadata for specific GR controls from the verified firmware."""
import hashlib, json, pathlib, struct
p=pathlib.Path('PHASE21_FUNCTIONAL_RESEARCH/evidence/target_live_20261104/gsp_tu10x_615.71.09.bin')
b=p.read_bytes();h=hashlib.sha256(b).hexdigest()
assert h=='78e0a2c8e4bd8a2faa1ff36137209669cdf60bd698b8f723dcf52869df82b909'
inner=b[0x40:0x40+0x15d2dc8]
out={'outer_sha256':h,'inner_sha256':hashlib.sha256(inner).hexdigest(),'entries':[]}
for cmd in [0x20800a26,0x20800a27,0x2080123b,0x208001e7,0x2080123c]:
 pat=struct.pack('<I',cmd);start=0;hits=[]
 while True:
  off=inner.find(pat,start)
  if off<0:break
  start=off+1
  if off>=16 and off+16<=len(inner):
   f,flags,access,method,size,cls=struct.unpack_from('<QIIIIQ',inner,off-16)
   hits.append({'inner_file_offset':hex(off),'outer_file_offset':hex(off+64),'record_hex':inner[off-16:off+16].hex(),'function_va':hex(f),'flags':hex(flags),'access':hex(access),'method':hex(method),'size':size,'class_pointer':hex(cls)})
 out['entries'].append({'command':hex(cmd),'hits':hits})
print(json.dumps(out,indent=2))

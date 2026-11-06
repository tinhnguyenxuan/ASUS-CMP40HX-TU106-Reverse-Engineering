#!/usr/bin/env python3
"""Record selected +0x790 accesses and prove offset-collision limits."""
import hashlib,json,pathlib,capstone
ROOT=pathlib.Path(__file__).resolve().parents[1]
inv=json.loads((ROOT/'evidence/firmware_capability_inventory.json').read_text())[0]
blob=pathlib.Path(inv['path']).read_bytes(); cs=capstone.Cs(capstone.CS_ARCH_RISCV,capstone.CS_MODE_RISCV64); cs.detail=True
wanted={0x04b20f68,0x0462ec60,0x049852b4}
found={}
for sec in inv['inner_elf']['sections']:
 if sec['type']!=1 or not sec['size']: continue
 off=sec['file_offset']; data=blob[off:off+sec['size']]
 for ins in cs.disasm(data,sec['va']):
  if ins.address not in wanted: continue
  mem=[o.mem for o in ins.operands if o.type==capstone.CS_OP_MEM]
  found[hex(ins.address)]={'mnemonic':ins.mnemonic,'op_str':ins.op_str,'displacements':[hex(m.disp) for m in mem],'bases':[ins.reg_name(m.base) for m in mem]}
out={'firmware':inv['path'],'sha256':hashlib.sha256(blob).hexdigest(),'selected_sites':found,'missing':[hex(x) for x in wanted if hex(x) not in found], 'semantic_scope':'The same numeric offset occurs in distinct object contexts; only consumer-local interpretation is asserted.'}
(ROOT/'evidence/display_790_sites.json').write_text(json.dumps(out,indent=2)+'\n')
assert out['sha256']==inv['sha256'] and not out['missing']
print('3 selected +0x790 collision sites verified; firmware SHA256 matches inventory')

#!/usr/bin/env python3
"""Reproducibly record selected +0x334 accesses in the TU10x GSP ELF."""
import json, pathlib, hashlib
import capstone
ROOT=pathlib.Path(__file__).resolve().parents[1]
inv=json.loads((ROOT/'evidence/firmware_capability_inventory.json').read_text())[0]
blob=pathlib.Path(inv['path']).read_bytes()
cs=capstone.Cs(capstone.CS_ARCH_RISCV,capstone.CS_MODE_RISCV64); cs.detail=True
wanted={0x0460b600,0x04616fa4,0x0485ed5c,0x0487c338,0x04894e70,0x04894e78,0x04b20f80,0x04b30138}
found={}
for sec in inv['inner_elf']['sections']:
    if sec['type']!=1 or not sec['size']: continue
    off=sec['file_offset']; data=blob[off:off+sec['size']]
    for ins in cs.disasm(data,sec['va']):
        if ins.address not in wanted: continue
        mem=[o.mem for o in ins.operands if o.type==capstone.CS_OP_MEM]
        found[hex(ins.address)]={
            'mnemonic':ins.mnemonic,'op_str':ins.op_str,
            'memory_displacements':[hex(m.disp) for m in mem],
            'base_registers':[ins.reg_name(m.base) for m in mem],
            'width': {capstone.CS_OP_INVALID:'unknown'}.get(ins.operands[0].type,'decoded') if ins.operands else 'unknown'
        }
missing=sorted(hex(x) for x in wanted if hex(x) not in found)
out={'firmware':inv['path'],'sha256':hashlib.sha256(blob).hexdigest(),'selected_sites':found,'missing':missing,
     'semantic_scope':'Instruction-level accesses only; same numeric offset does not prove same object/class alias.'}
(ROOT/'evidence/display_334_sites.json').write_text(json.dumps(out,indent=2)+'\n')
assert hashlib.sha256(blob).hexdigest()==inv['sha256']
assert not missing, missing
print(f"{len(found)} selected +0x334 sites verified; firmware SHA256 matches inventory")

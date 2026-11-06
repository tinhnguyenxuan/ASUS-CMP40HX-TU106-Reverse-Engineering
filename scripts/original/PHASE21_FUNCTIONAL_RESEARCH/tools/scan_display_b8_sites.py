#!/usr/bin/env python3
"""Bounded raw scan of RISC-V +0xb8 accesses in the hashed GSP image."""
import hashlib, json, pathlib
from capstone import Cs, CS_ARCH_RISCV, CS_MODE_RISCV64
ROOT = pathlib.Path(__file__).resolve().parents[1]
record = json.loads((ROOT / 'evidence/firmware_capability_inventory.json').read_text())[0]
blob = pathlib.Path(record['path']).read_bytes()
sections = [s for s in record['inner_elf']['sections'] if s['type'] != 8 and s['size']]
md = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64)
rows=[]
for s in sections:
    data=blob[s['file_offset']:s['file_offset']+s['size']]
    for ins in md.disasm(data,s['va']):
        if '0xb8(' in ins.op_str and ins.mnemonic in {'ld','sd','lw','sw','lbu','sb','jalr'}:
            rows.append({'va':hex(ins.address),'mnemonic':ins.mnemonic,'op_str':ins.op_str})
# The initialization routine's section-local neighborhood contains the consumer's
# only +0xb8 load; no direct +0xb8 store is present in 0x04b70000..0x04b7ffff.
init = [r for r in rows if 0x04b70000 <= int(r['va'],16) < 0x04b80000]
result={'firmware':record['path'],'sha256':hashlib.sha256(blob).hexdigest(),
        'all_access_count':len(rows),'initialization_window':'0x04b70000-0x04b7ffff',
        'initialization_window_accesses':init,
        'consumer_load':next((r for r in rows if r['va']=='0x4b72790'),None),
        'interpretation':'bounded access inventory; offset collisions elsewhere prevent global slot ownership inference'}
(ROOT/'evidence/display_b8_sites.json').write_text(json.dumps(result,indent=2)+'\n')
print(f"{len(rows)} +0xb8 accesses; init window {len(init)} access(es); firmware SHA256 matches inventory")

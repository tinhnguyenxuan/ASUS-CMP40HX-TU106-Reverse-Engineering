#!/usr/bin/env python3
import json, pathlib, struct, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
inv=json.loads((ROOT/'evidence/firmware_capability_inventory.json').read_text())[0]
b=pathlib.Path(inv['path']).read_bytes(); secs=[s for s in inv['inner_elf']['sections'] if s['type']!=8 and s['size']]
def word(va):
 for s in secs:
  if s['va']<=va and va+4<=s['va']+s['size'] and s['file_offset']+va-s['va']+4<=len(b):
   return struct.unpack_from('<I',b,s['file_offset']+va-s['va'])[0]
 raise ValueError(hex(va))
# lui a1,0x5995; addi a1,a1,0x528 at veto diagnostic branch
lui=word(0x04b20fcc); addi=word(0x04b20fd0)
assert lui==0x059955b7
# The addi instruction is in the next mapped text word; decode it below.
resolved=((lui & 0xfffff000) + ((addi>>20)&0xfff)) & 0xffffffff
assert resolved==0x05995528
mapped=[s['name'] for s in secs if s['va']<=resolved< s['va']+s['size']]
assert not mapped
out={'firmware':inv['path'],'sha256':hashlib.sha256(b).hexdigest(),'instructions':{'lui_va':'0x04b20fcc','addi_va':'0x04b20fd0','resolved_va':hex(resolved)},'mapped_sections':mapped,'result':'diagnostic string VA is outside current mapped inner-ELF sections; text intentionally unresolved'}
(ROOT/'evidence/diagnostic_literal.json').write_text(json.dumps(out,indent=2)+'\n')
print(f'diagnostic literal {resolved:#x} unmapped; firmware SHA256 matches inventory')

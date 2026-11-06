"""Independent raw-encoding regression checks for documented display edges."""
from pathlib import Path
import json,struct,hashlib
p=Path(__file__).resolve().parents[2];b=(p/'work_v15/outputs/gsp_tu10x.bin').read_bytes()
assert hashlib.sha256(b).hexdigest()=='0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b'
sx=lambda x,n:x-(1<<n) if x&(1<<(n-1)) else x
word=lambda pc:struct.unpack_from('<I',b,pc-0x3ffffc0)[0]
checks=[]
for pc,expected in [(0x4840374,0x45e130c),(0x4b300d0,0x45e130c)]:
 w,v=word(pc),word(pc+4)
 assert w&127==0x17 and v&0x707f==0x67
 assert (w>>7)&31==(v>>15)&31
 actual=(pc+sx(w&0xfffff000,32)+sx(v>>20,12))&~1
 assert actual==expected;checks.append({'kind':'call','pc':hex(pc),'target':hex(actual)})
for pc,expected in [(0x4840380,0x48403d4),(0x484038c,0x48403fc),(0x4b300dc,0x4b300ec),(0x4b300e8,0x4b30138)]:
 w=word(pc);assert w&127==0x63
 imm=((w>>31)<<12)|(((w>>7)&1)<<11)|(((w>>25)&63)<<5)|(((w>>8)&15)<<1)
 actual=pc+sx(imm,13);assert actual==expected
 checks.append({'kind':'branch','pc':hex(pc),'target':hex(actual)})
w=word(0x4b30138);assert w&0x707f==0x2023
imm=((w>>25)<<5)|((w>>7)&31)
assert sx(imm,12)==0x334 and (w>>15)&31==19 and (w>>20)&31==15
checks.append({'kind':'store','pc':'0x4b30138','source_register':'a5','base_register':'s3','displacement':'0x334','width':4})
for off,expected in [(0x9e968,b'RmDisableDisplay\0'),(0xb3078,b'RmDisableDisplay\0')]:
 assert b[off:off+len(expected)]==expected
 checks.append({'kind':'string','file_offset':hex(off),'text':'RmDisableDisplay'})
r={'checks':checks,'result':'PASS','scope':'Only documented raw branch/call/store/string facts; not reachability, helper semantics or target runtime'}
(p/'PHASE21_FUNCTIONAL_RESEARCH/evidence/display_dataflow_verification.json').write_text(json.dumps(r,indent=2)+'\n');print(len(checks),'raw encoding checks PASS')

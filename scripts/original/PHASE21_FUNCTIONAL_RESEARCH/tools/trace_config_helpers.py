"""Offline bounded helper extraction and raw checks, no hardware access."""
from pathlib import Path
import json,hashlib,struct,capstone
root=Path(__file__).resolve().parents[2];out=root/'PHASE21_FUNCTIONAL_RESEARCH/evidence'
j=json.loads((out/'firmware_capability_inventory.json').read_text())[0];b=Path(j['path']).read_bytes()
assert hashlib.sha256(b).hexdigest()==j['sha256']
secs=[s for s in j['inner_elf']['sections'] if s['type']!=8 and s['size'] and s['va']]
def offset(va,n=1):
 s=[s for s in secs if s['va']<=va and va+n<=s['va']+s['size']];assert len(s)==1
 return s[0]['file_offset']+va-s[0]['va']
def w(pc):return struct.unpack_from('<I',b,offset(pc,4))[0]
sx=lambda v,n:v-(1<<n) if v&(1<<(n-1)) else v
checks=[]
for pc,target in [(0x45e1344,0x54eca80),(0x45e139c,0x45cc178),(0x54ecac0,0x54dd7ec),(0x54ecb4c,0x54dd7ec)]:
 a,c=w(pc),w(pc+4);assert a&127==0x17 and c&0x707f==0x67 and (a>>7)&31==(c>>15)&31
 actual=(pc+sx(a&0xfffff000,32)+sx(c>>20,12))&~1;assert actual==target
 checks.append({'kind':'raw_call_or_tail','pc':hex(pc),'target':hex(target),'rd':(c>>7)&31})
for pc,rs1,rs2,disp in [(0x54ecad0,18,15,0),(0x45cc2a0,19,15,0)]:
 a=w(pc);assert a&0x707f==0x2023 and (a>>15)&31==rs1 and (a>>20)&31==rs2
 assert sx(((a>>25)<<5)|((a>>7)&31),12)==disp
 checks.append({'kind':'output_word_store','pc':hex(pc),'base_reg':rs1,'value_reg':rs2})
a=w(0x54f4718)
assert a&0x707f==0x3023 and (a>>15)&31==15 and (a>>20)&31==19
assert sx(((a>>25)<<5)|((a>>7)&31),12)==-0x518
checks.append({'kind':'list_head_pointer_store','pc':'0x54f4718','value_register':'s3','effective_address':'0x4396ae8','scope':'LUI a5 at 0x54f470c; intervening instructions do not clobber a5'})
md=capstone.Cs(capstone.CS_ARCH_RISCV,capstone.CS_MODE_RISCV64|capstone.CS_MODE_RISCVC)
windows=[]
for lo,hi in [(0x45e130c,0x45e13a4),(0x54eca80,0x54ecba8),(0x54dd7ec,0x54dd890),(0x45cc178,0x45cc2bc),(0x54f470c,0x54f4740)]:
 off=offset(lo,hi-lo);ins=list(md.disasm(b[off:off+hi-lo],lo));assert sum(i.size for i in ins)==hi-lo
 windows.append({'lo':hex(lo),'hi':hex(hi),'file_offset':hex(off),'raw_sha256':hashlib.sha256(b[off:off+hi-lo]).hexdigest(),'instructions':[{'pc':hex(i.address),'raw':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str} for i in ins]})
initial=[]
for va,n in [(0x4396ae8,8),(0x439686c,1)]:
 off=offset(va,n);initial.append({'va':hex(va),'file_offset':hex(off),'bytes':b[off:off+n].hex(),'scope':'File-initialized bytes only; runtime state unknown'})
h=Path('/tmp/nvsrc/common/sdk/nvidia/inc/nvstatuscodes.h');text=h.read_text()
lines=[x for x in text.splitlines() if '0x0000001F' in x or '0x0000003E' in x]
r={'input':{'path':j['path'],'sha256':j['sha256']},'capstone_version':capstone.__version__,'checks':checks,'windows':windows,'initial_data':initial,'status_source':{'path':str(h),'sha256':hashlib.sha256(h.read_bytes()).hexdigest(),'lines':lines,'scope':'Numeric enum corroboration; no debug-symbol function-name recovery'},'limits':['Bounded windows, not complete functions/CFG','No original writer or runtime list contents recovered','No RPC transport label assigned to fallback']}
(out/'gsp_config_helpers.json').write_text(json.dumps(r,indent=2)+'\n')
print(len(checks),'raw helper checks PASS;',len(windows),'bounded windows fully decoded')

"""Bounded straight-line LUI->ADDI/ADDIW string address references.
Stops on control transfer, unknown/compressed instruction, or source-register clobber.
No function-complete CFG/reachability claim. Run firmware inventory first.
"""
import json,struct,hashlib,capstone
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=root/'PHASE21_FUNCTIONAL_RESEARCH/evidence'
j=json.loads((out/'firmware_capability_inventory.json').read_text())[0]
b=Path(j['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==j['sha256']
secs=[s for s in j['inner_elf']['sections'] if s['type']!=8 and s['flags']&4 and s['size']]
targets={m['va']:t for t in j['capability_strings'] for m in t['mappings']}
highs={(v+0x800)&~0xfff for v in targets}
sx=lambda v,n:v-(1<<n) if v&(1<<(n-1)) else v
md=capstone.Cs(capstone.CS_ARCH_RISCV,capstone.CS_MODE_RISCV64|capstone.CS_MODE_RISCVC)
hits=[];seeds=0
for sec in secs:
 start=sec['file_offset'];end=start+sec['size']
 for off in range(start,end-3,2):
  w=struct.unpack_from('<I',b,off)[0]
  if w&0x7f!=0x37 or (w&0xfffff000) not in highs:continue
  reg=(w>>7)&31
  if not reg:continue
  seeds+=1;trace=[{'file_offset':hex(off),'raw':b[off:off+4].hex()}]
  for off2 in range(off+4,min(end-3,off+4*17),4):
   v=struct.unpack_from('<I',b,off2)[0];op=v&127;rd=(v>>7)&31;rs1=(v>>15)&31
   if v&3!=3 or op in (0x63,0x67,0x6f,0x73):break
   if op not in (0x03,0x07,0x0f,0x13,0x17,0x1b,0x23,0x27,0x2f,0x33,0x37,0x3b):break
   trace.append({'file_offset':hex(off2),'raw':b[off2:off2+4].hex()})
   if op in (0x13,0x1b) and (v>>12)&7==0 and rs1==reg:
    value=(sx(w&0xfffff000,32)+sx(v>>20,12))&((1<<64)-1)
    if op==0x1b:value=sx(value&0xffffffff,32)&((1<<64)-1)
    if value in targets:
     pc=sec['va']+off-start;pc2=sec['va']+off2-start
     t=targets[value]
     dis=[{'pc':hex(i.address),'raw':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str} for i in md.disasm(b[off:min(end,off2+100)],pc)]
     hits.append({'string':t['text'],'string_va':hex(value),'string_file_offset':hex(t['file_offset']),'lui_pc':hex(pc),'address_pc':hex(pc2),'destination_register':rd,'trace':trace.copy(),'context':dis,'confidence':'local straight-line address computation; block reachability and lookup semantics unproven'})
   # Stores and floating-point writes cannot clobber an integer source register.
   if op not in (0x07,0x0f,0x23,0x27) and rd==reg:break
windows=[]
for lo,hi in [(0x4840368,0x4840420),(0x4b300c0,0x4b301b0),(0x45e130c,0x45e1410)]:
 matching=[s for s in secs if s['va']<=lo and hi<=s['va']+s['size']]
 assert len(matching)==1
 sec=matching[0];off=sec['file_offset']+lo-sec['va']
 windows.append({'start':hex(lo),'end':hex(hi),'file_offset':hex(off),'instructions':[{'pc':hex(i.address),'raw':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str} for i in md.disasm(b[off:off+hi-lo],lo)]})
for h in hits:
 h['resolved_direct_calls']=[]
 c=h['context']
 for first,second in zip(c,c[1:]):
  raw1=bytes.fromhex(first['raw']);raw2=bytes.fromhex(second['raw'])
  if len(raw1)!=4 or len(raw2)!=4:continue
  w,v=struct.unpack('<I',raw1)[0],struct.unpack('<I',raw2)[0]
  if w&127==0x17 and v&0x707f==0x67 and (w>>7)&31==(v>>15)&31:
   target=(int(first['pc'],16)+sx(w&0xfffff000,32)+sx(v>>20,12))&~1
   h['resolved_direct_calls'].append({'auipc_pc':first['pc'],'jalr_pc':second['pc'],'target':hex(target),'link_register':(v>>7)&31,'scope':'adjacent raw instruction resolution, no callee semantic assignment'})
r={'windows':windows,'input':{'path':j['path'],'sha256':j['sha256']},'capstone_version':capstone.__version__,'bound_instructions':16,'seed_count':seeds,'coverage':'Halfword candidate seeds; 32-bit straight-line instructions only, no entry-boundary proof; stops on control flow/unknown/clobber','matches':hits}
(out/'gsp_name_xrefs.json').write_text(json.dumps(r,indent=2)+'\n')
print('seeds',seeds,'matches',len(hits))
for h in hits:print(h['string'],h['lui_pc'],h['address_pc'])

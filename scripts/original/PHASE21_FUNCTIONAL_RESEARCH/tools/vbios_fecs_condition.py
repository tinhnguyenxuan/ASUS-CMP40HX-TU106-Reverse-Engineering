"""Decode BIT I condition-table FECS references offline, no hardware I/O."""
from pathlib import Path
import json,struct,hashlib,shutil
root=Path(__file__).resolve().parents[2];out=root/'PHASE21_FUNCTIONAL_RESEARCH/evidence'
p=root/'work_v15/outputs/CMP40HX_ORIGINAL_1MB.bin';b=p.read_bytes();base=0x28600
u16=lambda o:struct.unpack_from('<H',b,o)[0]
# Follow validated BIT metadata rather than treating any byte match as an opcode.
bit=base+0x1b0
assert b[bit:bit+7]==b'\xff\xb8BIT\0\0'
h,nent,ct=b[bit+8:bit+11];assert h==12 and nent==6 and sum(b[bit:bit+h])%256==0
entries=[b[bit+h+i*nent:bit+h+(i+1)*nent] for i in range(ct)]
e=[e for e in entries if e[0]==ord('I')];assert len(e)==1
e=e[0];length=struct.unpack_from('<H',e,2)[0];rel=struct.unpack_from('<H',e,4)[0]
assert length>=8
cond_rel=u16(base+rel+6);cond=base+cond_rel
# Raw FECS readout occurrences must fall on a condition-record boundary.
hits=[];pos=0
while True:
 pos=b.find(struct.pack('<I',0x409660),pos)
 if pos<0:break
 if cond<=pos<base+0xf400 and (pos-cond)%12==0:
  reg,mask,value=struct.unpack_from('<III',b,pos)
  hits.append({'record_index':(pos-cond)//12,'file_offset':hex(pos),'register':hex(reg),'mask':hex(mask),'expected':hex(value),'raw':b[pos:pos+12].hex(),'interpretation':'condition test only; no write operation encoded by this record'})
 pos+=1
assert len(hits)==1 and hits[0]['record_index']==50
assert hits[0]['mask']==hits[0]['expected']=='0x10000'
legacy=b[base:base+0xf400]
candidates=[hex(base+i) for i in range(len(legacy)-1) if legacy[i:i+2]==b'\x75\x32']
source=Path('/tmp/envytools/nvbios/nvbios.c');snap=out/'sources/envytools_nvbios.c';shutil.copyfile(source,snap)
r={'input':{'path':str(p.relative_to(root)),'sha256':hashlib.sha256(b).hexdigest()},'source':{'path':str(snap.relative_to(root)),'sha256':hashlib.sha256(snap.read_bytes()).hexdigest(),'usage':'BIT I+6 condition pointer, 12-byte records register/mask/value; CONDITION opcode 0x75 followed by index'},'bit_offset':hex(bit),'bit_i':{'relative_pointer':hex(rel),'length':length},'condition_table':hex(cond),'fecs_readout_conditions':hits,'condition50_byte_candidates':candidates,'candidate_scope':'Byte matches only, not instruction-boundary or execution/reachability proof','other_bank_readout_occurrence':hex(b.find(struct.pack('<I',0x409660),0x79000)),'limits':['Full script traversal and branch consumers unresolved','Bit16 readout semantic label unproven on TU106','No selector write or runtime state implied','Second-bank raw copy is not independent board evidence']}
(out/'vbios_fecs_condition.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['fecs_readout_conditions'],indent=2));print('condition50 byte candidates',candidates)

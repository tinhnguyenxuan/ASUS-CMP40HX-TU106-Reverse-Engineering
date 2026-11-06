"""Decode bounded ROM scripts and raw CALL edges; no firmware execution."""
from pathlib import Path
import struct,json,hashlib
root=Path(__file__).resolve().parents[2];out=root/'PHASE21_FUNCTIONAL_RESEARCH/evidence';p=root/'work_v15/outputs/CMP40HX_ORIGINAL_1MB.bin';b=p.read_bytes();base=0x28600
assert hashlib.sha256(b).hexdigest()=='dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec'
u16=lambda a:struct.unpack_from('<H',b,base+a)[0]
assert u16(0x293)==0x4698 and u16(0x4698)==0x7634 and u16(0x469a)==0
edges=[]
for at,target,owner in [(0x7634,0x7639,0x7634),(0x763f,0x7644,0x7639),(0x764a,0x8a67,0x7644),(0xc7f0,0xca6e,0x8a67),(0xc7f5,0xca41,0x8a67)]:
 assert b[base+at]==0x5b and u16(at+1)==target
 edges.append({'owner_script':hex(owner),'instruction':hex(at),'file_offset':hex(base+at),'target_script':hex(target),'raw':b[base+at:base+at+3].hex(),'scope':'CALL bytes verified; owner assignment from nvbios traversal, runtime guards unresolved'})
scripts=[]
for start,end in [(0xca6e,0xcab3),(0xca41,0xca6e)]:
 pc=start;ins=[]
 while pc<end:
  op=b[base+pc];n={0x75:2,0x6e:13,0x7a:9,0xb1:3,0x72:1,0x71:1}[op]
  assert pc+n<=end
  item={'relative':hex(pc),'absolute':hex(base+pc),'opcode':hex(op),'raw':b[base+pc:base+pc+n].hex()}
  if op==0x75:item.update({'kind':'CONDITION','index':b[base+pc+1]})
  elif op==0x6e:
   reg,mask,value=struct.unpack_from('<III',b,base+pc+1);item.update({'kind':'NV_REG','register':hex(reg),'and_mask':hex(mask),'or_value':hex(value)})
  elif op==0x7a:
   reg,value=struct.unpack_from('<II',b,base+pc+1);item.update({'kind':'ZM_REG','register':hex(reg),'value':hex(value)})
  elif op==0xb1:item.update({'kind':'POLL_NV_COND','index':b[base+pc+1],'parameter':b[base+pc+2]})
  else:item['kind']='RESUME' if op==0x72 else 'DONE'
  ins.append(item);pc+=n
  if op==0x71:break
 assert pc==end and ins[-1]['kind']=='DONE'
 scripts.append({'start':hex(start),'instructions':ins})
conditions=[]
for index in [0x26,0x30,0x32,0x33,0x51,0x52,0x53]:
 off=0x2cc9c+index*12
 reg,mask,value=struct.unpack_from('<III',b,off)
 conditions.append({'index':hex(index),'file_offset':hex(off),'register':hex(reg),'mask':hex(mask),'expected':hex(value)})
r={'related_conditions':conditions,'input':{'path':str(p.relative_to(root)),'sha256':hashlib.sha256(b).hexdigest()},'script_table_relative':'0x4698','main_script_relative':'0x7634','call_edges':edges,'bounded_scripts':scripts,'limits':['Static table/command path only; conditions may suppress execution','Owner paths from nvbios command traversal, not an independent complete interpreter','No TU106 semantics assigned to the newly observed register fields','Full nvbios run emitted parser compatibility/OOB warnings; see stderr']}
(out/'init_condition50_trace.json').write_text(json.dumps(r,indent=2)+'\n');print('5 CALL encodings and 2 exact bounded scripts verified')

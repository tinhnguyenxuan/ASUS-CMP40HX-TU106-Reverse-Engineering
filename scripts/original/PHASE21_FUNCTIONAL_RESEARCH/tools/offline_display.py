"""Read saved inputs only. Run from workspace root; no hardware access."""
from pathlib import Path
import hashlib,json,struct
root=Path(__file__).resolve().parents[2]
out=root/'PHASE21_FUNCTIONAL_RESEARCH'
def record(p):
 b=p.read_bytes(); return {'path':str(p.relative_to(root)), 'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def parse(p):
 b=p.read_bytes(); base=0x28600
 assert b[base:base+2]==b'\x55\xaa'
 u16=lambda x:struct.unpack_from('<H',b,x)[0]
 ptr=u16(base+0x36); d=base+ptr
 assert 0<ptr<0xf400 and d+27<=base+0xf400
 v,h,n,s=b[d:d+4]
 assert v in (0x40,0x41) and h>=27 and s==8
 assert struct.unpack_from('<I',b,d+6)[0]==0x4edcbdcb
 assert d+h+n*s<=base+0xf400
 tables={}
 for name,off in [('communications',4),('gpio',10),('input',12),('cinema',14),('spread_spectrum',16),('i2c_devices',18),('connector',20),('hdtv',23),('switched_outputs',25)]:
  ptr2=u16(d+off)
  tables[name]={'relative_pointer':hex(ptr2),'absolute_offset':hex(base+ptr2) if ptr2 else None,'prefix_hex':b[base+ptr2:base+ptr2+16].hex() if ptr2 else None}
 return {**record(p),'legacy_base':hex(base),'pointer_field':hex(base+0x36),'dcb_offset':hex(d),'version':hex(v),'header_size':h,'entry_count':n,'entry_size':s,'header_hex':b[d:d+h].hex(),'tables':tables}
r=[parse(root/'work_v15/outputs'/x) for x in ['CMP40HX_ORIGINAL_1MB.bin','cmp40hx_t4.bin']]
(out/'evidence/dcb.json').write_text(json.dumps(r,indent=2)+'\n')
f=root/'work_v15/RAW_DATA/fuse2.json'; j=json.loads(f.read_text())
items=[]
for off,label,meaning in [(0x378,'NVDEC_DISABLE','TU102 source: bits 2:0 disable mask; raw zero does not prove decode execution'),(0x74c,'SECURE_GSP_DEBUG_DIS','TU102 source: debug disable bit'),(0xc04,'NV_FUSE_STATUS_OPT_DISPLAY','Official 615.78.08 TU106 dispatch selects GM107 helper; ENABLE=0 in saved header; archived bit0=1 evaluates false. Physical vs shadow and fresh state UNKNOWN; see evidence/display_gate.json'),(0x650,'UNKNOWN','No verified TU106 field semantics'),(0xc1c,'UNKNOWN','No verified TU106 field semantics')]:
 items.append({'offset':hex(off),'address':hex(j['base']+off),'value':hex(j['regs'][str(off)]),'name':label,'interpretation':meaning,'storage':'MMIO saved read; physical OTP vs shadow UNKNOWN'})
(out/'FUSE_CAPABILITY_MAP.json').write_text(json.dumps({'input':record(f),'words':len(j['regs']),'dump_bytes':4*len(j['regs']),'declared_span':j['span'],'fields':items},indent=2)+'\n')
print(json.dumps(r,indent=2))

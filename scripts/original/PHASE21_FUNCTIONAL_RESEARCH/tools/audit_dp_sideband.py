"""Offline CAD pin/net evidence and original VBIOS GPIO candidate correlation."""
from pathlib import Path
import json,hashlib,struct
root=Path(__file__).resolve().parents[2];p=root/'PHASE21_FUNCTIONAL_RESEARCH'
cad=json.loads((p/'evidence/pcb_design_rederived.json').read_text());parts=cad['sideband_components']
checks=[]
def pin(c,pin,net,gpu=None):
 rows=[r for r in parts[c]['pins'] if r['pin']==pin];assert len(rows)==1 and rows[0]['net']==net
 row=rows[0]
 if gpu:assert any(n['component']=='G1' and n['pin']==gpu for n in row['net_nodes'])
 checks.append({'component':c,'pin':pin,'net':net,'signal_line':row['signal_line'],'gpu_pin_same_net':gpu})
pin('Q7','4','IFPD_AUX','BE11');pin('Q7','1','IFPD_AUX*','BF11')
pin('Q7','3','IFPD_AUX_R');pin('Q7','6','IFPD_AUX_R*')
pin('Q509','1','IFPD_AUX_R');pin('Q509','4','IFPD_AUX_C')
pin('Q521','3','GPIO17_IFPD_HPD','BH1');pin('Q521','1','DP_D_HPD_R_Q')
pin('R742','1','DP_D_HPD_R_Q');pin('R742','2','DP_D_HPD_R')
pin('R720','1','DP_D_HPD_R');pin('R720','2','DP_D_HPD_C')
rom=root/'work_v15/outputs/CMP40HX_ORIGINAL_1MB.bin';b=rom.read_bytes();base=0x28600
u16=lambda x:struct.unpack_from('<H',b,x)[0]
dcb=base+u16(base+0x36);assert b[dcb]==0x41 and struct.unpack_from('<I',b,dcb+6)[0]==0x4edcbdcb
gpio=base+u16(dcb+10);version,h,n,stride=b[gpio:gpio+4];assert version==0x41 and stride>=5 and gpio+h+n*stride<=base+0xf400
candidates=[]
for i in range(n):
 off=gpio+h+i*stride;raw=b[off:off+stride]
 if raw[0]&63==17:candidates.append({'record_index':i,'file_offset':hex(off),'raw':raw.hex(),'line':17,'tag':hex(raw[1]),'tag_unused':raw[1]==255})
assert len(candidates)==1 and candidates[0]['tag_unused']
r={'schema':'phase21-dp-sideband-v1','cad_source':cad['input'],'cad_derived_sha256':hashlib.sha256((p/'evidence/pcb_design_rederived.json').read_bytes()).hexdigest(),'source_rom':{'path':str(rom.relative_to(root)),'sha256':hashlib.sha256(b).hexdigest()},'checked_net_memberships':checks,'gpio17_candidate':candidates,'limits':['No internal connection inferred through Q7/Q509/Q521; only pin/net membership','GPIO17 net name versus ROM line17 is a candidate correlation; physical hardware numbering not independently authenticated','Unused ROM tag is a configuration-description fact, not proof that hardware pin is disabled/absent','Reference CAD correspondence to tested CMP unit still unverified','No HPD override, short, strap change or live test performed']}
(p/'evidence/dp_sideband_audit.json').write_text(json.dumps(r,indent=2)+'\n')
print(len(checks),'pin/net memberships verified; ROM GPIO-line17 tag=',candidates[0]['tag'])

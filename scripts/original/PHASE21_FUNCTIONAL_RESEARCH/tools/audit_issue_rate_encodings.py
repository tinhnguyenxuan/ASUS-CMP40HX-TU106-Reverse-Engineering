"""Compare captured V2 numeric values to saved legacy API enums; no cross-API assumption."""
from pathlib import Path
import re,json,hashlib
root=Path(__file__).resolve().parents[2];p=root/'PHASE21_FUNCTIONAL_RESEARCH';h=Path('/tmp/nvsrc/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gr.h');text=h.read_text()
capture=json.loads((p/'evidence/reconciled_20261106/issue_rate_decoded.json').read_text())
rows=[]
for pair in capture['pairs']:
 name=pair['name'];value=pair['raw_speed_select'];pattern=r'^#define\s+NV2080_CTRL_GR_GET_SM_ISSUE_RATE_MODIFIER_'+name+r'_(\w+)\s+\(0x([0-9A-Fa-f]+)U\)'
 enums=[{'suffix':m.group(1),'value':int(m.group(2),16)} for m in re.finditer(pattern,text,re.M)]
 rows.append({**pair,'legacy_definitions_with_same_value':[x['suffix'] for x in enums if x['value']==value],'legacy_defined_values':sorted(set(x['value'] for x in enums)),'conclusion':'Candidate numeric correspondence only; V2 consumer translation and effective throughput not established'})
r={'schema':'phase21-issue-rate-enum-boundary-v1','header':{'path':str(h),'sha256':hashlib.sha256(h.read_bytes()).hexdigest(),'scope':'Saved local header; exact615.71.09 tag byte identity not verified by this script'},'capture_input_sha256':hashlib.sha256((p/'evidence/reconciled_20261106/issue_rate_decoded.json').read_bytes()).hexdigest(),'rows':rows,'limits':['Legacy query20801230 enum names do not by themselves define V2 query2080123c values','No generic divisor=2^code interpretation is authorized','Not hardware execution, raw OTP or production defect evidence']}
(p/'evidence/issue_rate_enum_boundary.json').write_text(json.dumps(r,indent=2)+'\n')
for x in rows:print(x['name'],x['raw_speed_select'],x['legacy_definitions_with_same_value'])

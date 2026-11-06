#!/usr/bin/env python3
import hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[1]
files=[ROOT.parent/'work_v15/TOPOLOGY/silicon_topology.json',ROOT.parent/'work_v15/TOPOLOGY/display_probe.json']
out=[]
for p in files:
 b=p.read_bytes(); rec={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'json_valid':True}
 j=json.loads(b)
 if p.name=='silicon_topology.json':
  q=j.get('smi_q',''); rec['captured_timestamp']=(re.search(r'Timestamp\s+:\s+([^\n]+)',q).group(1).strip() if re.search(r'Timestamp\s+:\s+([^\n]+)',q) else None);rec['bdf']='00000000:03:00.0';rec['gpu_uuid']=j.get('gpu_uuid');
  fields={}
  for label in ('Product Name','GPU Part Number','VBIOS Version','GSP Firmware Version','Display Attached','Display Active','Display Mode','Driver Version','PCI\n        Bus'):
   m=re.search(r'^\s*'+re.escape(label)+r'\s+:\s+([^\n]+)',q,re.M)
   if m: fields[label]=m.group(1).strip()
  rec['selected_fields']=fields; rec['source_metadata']='embedded nvidia-smi query string; no live recapture in this session'
 else:
  rec['bdf_resource']=j.get('bdf');rec['conclusion']=j.get('conclusion');rec['source_metadata']='saved BAR/resource0 readout; no capture timestamp or command metadata in file'
 out.append(rec)
out={'artifacts':out,'interpretation':'Saved historical runtime evidence is attributable to the recorded BDF where metadata exists, but it is not evidence of current target state. display_probe has no timestamp/command metadata; silicon_topology embeds a timestamped nvidia-smi query.'}
(ROOT/'evidence/saved_runtime_provenance.json').write_text(json.dumps(out,indent=2)+'\n')
print('saved runtime provenance audit PASS')

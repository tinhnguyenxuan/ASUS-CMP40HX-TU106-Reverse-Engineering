#!/usr/bin/env python3
import json, pathlib, hashlib, datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
items=[
 ('cuda_capability','CUDA capability/current correctness','TARGET_LIVE_FINDINGS.md','PARTIAL_CURRENT','CUDA 7.5/34 SM, 4096-element kernel and 256-output WMMA correctness PASS; libraries and profiling still unverified'),
 ('compute_restriction','Compute restriction and selector semantics','COMPUTE_SELECTOR_EVIDENCE.md','PROVEN_STATIC','Static selector evidence exists; exact runtime consumer mapping remains open'),
 ('display','Display policy, fuse gate and physical capability','GSP_DISPLAY_OBJECT_FIELDS.md','PROVEN_STATIC','Static policy/fuse dataflow recovered; current physical capability missing'),
 ('headless_graphics','EGL/OpenGL/Vulkan/KMS correctness','TARGET_LIVE_FINDINGS.md','PARTIAL_CURRENT','BDF-matched EGL pbuffer and shader/draw readback PASS; Vulkan and scanout remain unverified'),
 ('fuse','Fuse capability and physical-vs-shadow origin','FUSE_CAPABILITY_MAP.json','HISTORICAL_ONLY','Saved raw subset and archived predicate; current origin unresolved'),
 ('cross_sku_vbios','Revision-matched independent TU106 ROM comparison','VBIOS_DISPLAY_ANALYSIS.md','UNKNOWN','Local original/derivative comparison only'),
 ('gsp_gates','GSP/RM display gate and registry path','GSP_DISPLAY_CONFIG_DATAFLOW.md','PROVEN_STATIC','Static dataflow verified; effective target values/runtime reachability open'),
 ('feasibility','Per-function restoration feasibility','RESTORATION_FEASIBILITY_MATRIX.md','UNKNOWN','Rows retain unresolved runtime/hardware inputs'),
 ('safety_repro','Safe reproducible collection','TARGET_CAPTURE_CHECKLIST.md','PROVEN_STATIC','Read-only checklist and package collector/verifier exist'),
 ('deliverables','Reports/evidence/checkpoint integrity','CHECKPOINT.json','PROVEN_STATIC','Artifact suite and full integrity sweep pass'),
]
rows=[]
for key,req,rel,status,note in items:
 p=ROOT/rel; rows.append({'id':key,'requirement':req,'artifact':rel,'exists':p.exists(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,'status':status,'note':note})
out={'schema':'phase21-requirement-matrix-v1','generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'prompt scope and current workspace artifacts','rows':rows,'completion_rule':'Only rows with authoritative current-target evidence can be promoted from MISSING_CURRENT/HISTORICAL_ONLY/UNKNOWN; static artifact presence alone is insufficient.'}
(ROOT/'evidence/requirement_matrix.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
assert all(x['exists'] for x in rows)
print('requirement matrix PASS:',len(rows),'rows; unresolved=',sum(x['status']!='PROVEN_STATIC' for x in rows))

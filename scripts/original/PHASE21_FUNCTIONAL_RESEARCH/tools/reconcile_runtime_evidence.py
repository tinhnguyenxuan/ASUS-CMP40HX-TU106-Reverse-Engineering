"""Reconcile retained captures offline. Never connect to target or run probes."""
from pathlib import Path
import json,hashlib,struct,datetime,shutil
root=Path(__file__).resolve().parents[2];p=root/'PHASE21_FUNCTIONAL_RESEARCH';live=p/'evidence/target_live_20261104';new=root/'CMP40HX_NEW_INDEPENDENT_20261106';dst=p/'evidence/reconciled_20261106';dst.mkdir(exist_ok=True)
def load(f):return json.loads(f.read_text())
def ref(f):return {'path':str(f.relative_to(root)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
manifest=[]
for name in ['LIVE_IDENTITY.txt','LIVE_ADDITIONAL.txt','LIVE_RM_CANDIDATES_V2.json','probe_rm_get.py']:
 src=new/name;target=dst/name
 if target.exists():assert target.read_bytes()==src.read_bytes(),'Retained snapshot changed'
 else:shutil.copyfile(src,target)
 manifest.append({'source':ref(src),'snapshot':ref(target)})
j=load(dst/'LIVE_RM_CANDIDATES_V2.json');steps=j['steps'];get=[s for s in steps if s.get('cmd')=='0x2080123c'];assert len(get)==1
s=get[0];assert s['status']=='0x0' and s['size']==2044
raw=bytes.fromhex(s['output']);assert len(raw)==s['size']
n=struct.unpack_from('<I',raw)[0];assert 0<n<=255
pairs=[struct.unpack_from('<II',raw,4+i*8) for i in range(n)]
assert len(set(x[0] for x in pairs))==n
names={0:'FMLA16',1:'DP',2:'FMLA32',3:'FFMA',4:'IMLA0',5:'IMLA1',6:'IMLA2',7:'IMLA3',8:'IMLA4'}
failures=[]
for s in steps:
 if s.get('cmd') in ['0x2080123b','0x208001e7']:
  assert s['status']=='0x56' and s['input']==s['output']
  failures.append({'command':s['cmd'],'gpc':struct.unpack_from('<I',bytes.fromhex(s['input']))[0],'status':s['status'],'output_unchanged':True})
rate={'capture_utc':j['utc'],'input':ref(dst/'LIVE_RM_CANDIDATES_V2.json'),'count':n,'pairs':[{'index':i,'name':names.get(i,'UNKNOWN'),'raw_speed_select':v} for i,v in pairs],'denied_controls':failures,'limits':['Captured result, not a query executed by this reconciler','Cached API values, not direct MMIO or physical OTP','No inferred throughput divisor from code 6','Missing DP entry is not hardware-absent evidence','No TPC defect or recovery conclusion']}
(dst/'issue_rate_decoded.json').write_text(json.dumps(rate,indent=2)+'\n')
tests=[]
for name,label,expected in [('cuda_correctness.json','FP32 kernel, allocation and synchronization',4096),('tensor_correctness.json','sm_75 WMMA half-input/float-output',256),('cublas_correctness.json','cuBLAS SGEMM',256)]:
 f=live/name;j=load(f);assert j['returncode']==0 and 'PASS' in j['stdout'] and str(expected) in j['stdout']
 tests.append({'feature':label,'status':'PROVEN_WORKING','observed_utc':j['utc'],'bdf':'0000:03:00.0','stdout':j['stdout'],'source':ref(f),'scope':'Bounded correctness only; no stock or performance assertion'})
f=live/'cupti_query.json';j=load(f);assert j['cuptiGetVersion']['rc']==0
tests.append({'feature':'CUPTI metadata discovery','status':'PROVEN_WORKING','observed_utc':j['utc'],'source':ref(f),'scope':'Library/version only, no counters, callbacks or device profiling proved'})
f=live/'egl_shader_result.json';j=load(f)
assert j['matched_gpu'] and j['nvidia_hardware'] and j['pixels']['all_match'] and j['pixels']['count']==16
assert all(x==[0,255,0,255] for x in j['pixels']['read']) and j['egl_errors_clean'] and j['gl_errors_clean']
assert any(x['step']=='EGL_CUDA_DEVICE_NV_to_BDF' and x['ok'] and x['result']=='0000:03:00.0' for x in j['steps'])
render={'status':'PROVEN_WORKING','feature':'OpenGL ES headless shader/raster readback','utc':j['utc'],'renderer':j['gl'],'source':ref(f),'scope':'4x4 green triangle readback, not physical scanout or desktop OpenGL coverage'}
result={'schema':'phase21-runtime-reconciled-v1','generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PARTIAL_CAPTURED_TARGET','target':{'bdf':'0000:03:00.0','uuid':'GPU-REDACTED','captured_driver_gsp':'615.71.09'},'freshly_executed_target_tests':False,'tests':tests,'headless_graphics':render,'issue_rate_capture':'evidence/reconciled_20261106/issue_rate_decoded.json','unverified':['True stock state and throughput','cuBLASLt','DP4A correctness','CUDA graph execution','CUPTI device support/counter collection','CUDA/OpenGL interoperability','Vulkan render correctness','Physical display scanout'],'supersedes':'Earlier NOT_RUN only described local sandbox, not retained target captures'}
(p/'CUDA_RUNTIME_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
(dst/'input_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Reconciled:',len(tests),'compute/library evidence rows; matched EGL shader capture; issue-rate pairs:',pairs)

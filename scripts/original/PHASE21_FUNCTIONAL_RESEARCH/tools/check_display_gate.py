"""Evaluate archived display status using saved field definitions; no hardware I/O.
Dispatch and function body independently reviewed in official 615.78.08 sources.
"""
from pathlib import Path
import json,hashlib,re
root=Path(__file__).resolve().parents[2]; out=root/'PHASE21_FUNCTIONAL_RESEARCH'
h=root/'work_v15/PHASE16/SOURCES/nvidia_gm107_dev_fuse.h';f=root/'work_v15/RAW_DATA/fuse2.json'
s=h.read_text();j=json.loads(f.read_text())
def define(name):
 return re.search(r'^#define\s+'+name+r'\s+(\S+)',s,re.M).group(1)
addr=int(define('NV_FUSE_STATUS_OPT_DISPLAY'),16)
field=define('NV_FUSE_STATUS_OPT_DISPLAY_DATA');hi,lo=map(int,field.split(':'))
enable=int(define('NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE'),16)
raw=j['regs'][str(addr-j['base'])];data=(raw>>lo)&((1<<(hi-lo+1))-1)
def source(p):return {'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
r={'inputs':[source(h),source(f)],'address':hex(addr),'raw_archived':hex(raw),'field':field,'data':data,'enable_encoding':enable,'evaluated_support':data==enable,'classification':'ARCHIVED_STATUS_GATE_FALSE','scope':'Source predicate evaluation against saved snapshot, not current target observation or proof of physical OTP','official_dispatch':{'tag':'615.78.08','url':'https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/generated/g_gpu_nvoc.c','function':'__nvoc_init_funcTable_OBJGPU','selection':'TU102/TU104/TU106/TU116/TU117 -> gpuFuseSupportsDisplay_GM107','source_lines':[1941,1943]},'official_consumer':{'url':'https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/arch/maxwell/kern_gpu_gm107.c','function':'gpuFuseSupportsDisplay_GM107','predicate':'GPU_FLD_TEST_DRF_DEF on FUSE STATUS_OPT_DISPLAY DATA ENABLE'},'limits':['Header exact official tag bytes not fetched this turn; local snapshot hash retained','Archived dump timestamp and firmware state not tied to fresh target capture','Cannot distinguish physical fuse, shadow, strap-derived or emulated status from one read','Does not prove head/PHY absence or output routing']}
(out/'evidence/display_gate.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:r[k] for k in ['address','raw_archived','field','enable_encoding','evaluated_support','classification']},indent=2))

"""Compile/run bounded additional CUDA tests; capture failures without changing device config.
Requires an explicitly new output directory. Never installs toolchains or uses sudo.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,re,shutil,subprocess
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--bdf',default='0000:03:00.0');ap.add_argument('--expected-uuid',default='GPU-REDACTED');a=ap.parse_args()
out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
original_source=Path(__file__).resolve().with_name('cuda_additional_correctness.cu');source=out/'probe_source.cu';shutil.copyfile(original_source,source);nvcc=shutil.which('nvcc')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(argv,limit):
 record={'argv':argv,'started_utc':now()}
 try:
  p=subprocess.run(argv,capture_output=True,text=True,timeout=limit,check=False);record.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,status='EXITED')
 except subprocess.TimeoutExpired as e:record.update(status='TIMEOUT',stdout=(e.stdout or b'').decode(errors='replace') if isinstance(e.stdout,bytes) else e.stdout,stderr=(e.stderr or b'').decode(errors='replace') if isinstance(e.stderr,bytes) else e.stderr)
 except OSError as e:record.update(status='ENVIRONMENT_ERROR',error=str(e))
 record['ended_utc']=now();return record
r={'schema':'phase21-additional-cuda-v1','started_utc':now(),'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'bdf':a.bdf,'expected_uuid':a.expected_uuid,'status':'NOT_RUN','tests':[],'limits':['No throughput/stock claim','Device payload <=512 bytes per test; driver/context overhead not bounded by that number','CPU timeout is not a GPU reset/preemption guarantee','No device configuration, clock, voltage or privileged operation']}
if not nvcc:r['reason']='TOOLCHAIN_MISSING: nvcc not in PATH; no target inference'
else:
 r['compiler']=run([nvcc,'--version'],10);binary=out/'cuda_additional_correctness'
 r['build']=run([nvcc,'-std=c++14','-O2','-arch=sm_75',str(source),'-o',str(binary)],45)
 if r['build'].get('returncode')!=0:r.update(status='BUILD_FAILED_OR_TIMED_OUT',reason='Compiler/library support must be diagnosed separately from GPU capability')
 else:
  r['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
  for mode in ['fp16','dp4a','graph']:
   t=run([str(binary),mode,a.bdf],15);t['test']=mode
   stdout=t.get('stdout') or '';m=re.search(r'uuid=(GPU-[0-9a-f-]+)',stdout)
   t['identity_matches']=bool(m and m.group(1).lower()==a.expected_uuid.lower())
   t['correctness_pass']=bool(t.get('returncode')==0 and t['identity_matches'] and re.search(r'RESULT test='+mode+r' elements=32 mismatches=0 status=PASS cleanup=PASS',stdout))
   r['tests'].append(t)
   if t['status']=='TIMEOUT':break  # Do not keep launching after an unresponsive process.
  r['status']='PASS' if len(r['tests'])==3 and all(t['correctness_pass'] for t in r['tests']) else 'PARTIAL_OR_FAILED'
r['ended_utc']=now();(out/'results.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'status':r['status'],'reason':r.get('reason'),'result_file':str(out/'results.json')},indent=2))

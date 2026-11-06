"""Bounded read-only inventory; no sudo, BAR access, device writes or resets.
Run on target: python3 collect_readonly.py > target_inventory.json
GPU matching is by sysfs PCI vendor/device, not GPU ordinal.
"""
import datetime,json,subprocess,shutil
from pathlib import Path

def read(p):
 try:return p.read_text()[:65536].strip()
 except OSError as e:return {'error':str(e)}
def command(argv):
 if not shutil.which(argv[0]):return {'status':'TOOL_MISSING','argv':argv}
 try:
  r=subprocess.run(argv,capture_output=True,text=True,timeout=15,check=False)
  return {'argv':argv,'returncode':r.returncode,'stdout':r.stdout[:262144],'stderr':r.stderr[:65536]}
 except subprocess.TimeoutExpired:return {'argv':argv,'status':'TIMEOUT'}
r={'schema':1,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target_match':'10de:1f0b','devices':[],'warning':'Enumeration does not prove kernel execution, Tensor correctness, scanout or profiling.'}
for p in sorted(Path('/sys/bus/pci/devices').glob('*')):
 if read(p/'vendor')!='0x10de' or read(p/'device')!='0x1f0b':continue
 d={'bdf':p.name,'pci':{k:read(p/k) for k in ['vendor','device','subsystem_vendor','subsystem_device','revision','class','current_link_speed','current_link_width','max_link_speed','max_link_width']}}
 driver=p/'driver';d['driver']=driver.resolve().name if driver.exists() else None
 d['drm']=[]
 for card in sorted(Path('/sys/class/drm').glob('card*')):
  if '-' in card.name or not (card/'device').exists() or (card/'device').resolve()!=p.resolve():continue
  connectors=[]
  for c in sorted(Path('/sys/class/drm').glob(card.name+'-*')):
   connectors.append({'name':c.name,'status':read(c/'status'),'enabled':read(c/'enabled'),'modes':read(c/'modes')})
  d['drm'].append({'card':card.name,'connectors':connectors})
 d['render_nodes']=[x.name for x in Path('/sys/class/drm').glob('renderD*') if (x/'device').resolve()==p.resolve()]
 r['devices'].append(d)
r['nvidia_driver']=read(Path('/proc/driver/nvidia/version'))
r['nvidia_smi']=command(['nvidia-smi','--query-gpu=pci.bus_id,name,uuid,driver_version,vbios_version,pstate,clocks.current.graphics,clocks.current.memory,power.draw,temperature.gpu','--format=csv,noheader'])
print(json.dumps(r,indent=2))

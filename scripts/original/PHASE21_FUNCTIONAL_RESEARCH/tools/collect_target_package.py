#!/usr/bin/env python3
"""Collect a bounded read-only Phase 21 target package.

No sudo, writes, BAR access, resets, module reloads, or firmware actions.
Writes only the requested local output directory.
"""
import argparse, datetime, hashlib, json, os, pathlib, shutil, subprocess, sys

def run(argv, timeout=20):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if not shutil.which(argv[0]):
        return {'argv': argv, 'started_utc': start, 'status': 'TOOL_MISSING'}
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
        return {'argv': argv, 'started_utc': start, 'returncode': p.returncode,
                'stdout': p.stdout, 'stderr': p.stderr}
    except subprocess.TimeoutExpired as e:
        return {'argv': argv, 'started_utc': start, 'status': 'TIMEOUT',
                'stdout': e.stdout or '', 'stderr': e.stderr or ''}

def read(path):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        return {'path': str(path), 'started_utc': start, 'ok': True, 'text': pathlib.Path(path).read_text(errors='replace')}
    except OSError as e:
        return {'path': str(path), 'started_utc': start, 'ok': False, 'error': str(e)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('-o','--output',required=True)
    a=ap.parse_args(); out=pathlib.Path(a.output); out.mkdir(parents=True,exist_ok=True)
    records=[]
    for path in ['/sys/bus/pci/devices/0000:03:00.0/vendor','/sys/bus/pci/devices/0000:03:00.0/device','/sys/bus/pci/devices/0000:03:00.0/subsystem_vendor','/sys/bus/pci/devices/0000:03:00.0/subsystem_device','/sys/bus/pci/devices/0000:03:00.0/revision','/proc/driver/nvidia/version','/proc/driver/nvidia/params','/proc/driver/nvidia/gpus/0000:03:00.0/information','/proc/driver/nvidia/gpus/0000:03:00.0/registry']:
        records.append({'kind':'read','result':read(path)})
    cmds=[['uname','-a'],['nvidia-smi','-q'],['nvidia-smi','-q','-d','DISPLAY,COMPUTE,PERFORMANCE'],['nvidia-smi','--query-gpu=pci.bus_id,name,uuid,driver_version,vbios_version,display_active,display_mode','--format=csv,noheader'],['find','/sys/class/drm','-maxdepth','2','-type','f','-name','status','-o','-name','enabled','-o','-name','modes']]
    for c in cmds: records.append({'kind':'command','result':run(c,60 if c[0]=='nvidia-smi' else 20)})
    payload={'schema':'phase21-target-package-v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bdf':'0000:03:00.0','read_only':True,'records':records,'warning':'Missing files/tools are recorded as observations; this package does not prove absence of hardware.'}
    data=json.dumps(payload,indent=2,ensure_ascii=False).encode(); (out/'target_package.json').write_bytes(data)
    (out/'SHA256SUMS').write_text(hashlib.sha256(data).hexdigest()+'  target_package.json\n')
    print(json.dumps({'output':str(out/'target_package.json'),'sha256':hashlib.sha256(data).hexdigest(),'records':len(records)},indent=2))
if __name__=='__main__': main()

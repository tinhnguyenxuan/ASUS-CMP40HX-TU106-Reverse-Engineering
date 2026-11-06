#!/usr/bin/env python3
"""Bounded RM topology query; no BAR/MMIO or hardware control writes."""
import ctypes as C, fcntl, os, json, datetime
u32=C.c_uint32; u64=C.c_uint64
class Alloc(C.Structure):
 _fields_=[('root',u32),('parent',u32),('new',u32),('cls',u32),('params',u64),('size',u32),('status',u32)]
class Ctrl(C.Structure):
 _fields_=[('client',u32),('obj',u32),('cmd',u32),('flags',u32),('params',u64),('size',u32),('status',u32)]
class Device(C.Structure):
 _fields_=[('deviceId',u32),('share',u32),('targetClient',u32),('targetDevice',u32),('flags',u32),('vaSpaceSize',u64),('vaStart',u64),('vaLimit',u64),('vaMode',u32)]
class Route(C.Structure):
 _fields_=[('flags',u32),('route',u64)]
class Mask(C.Structure):
 _fields_=[('route',Route),('gpc',u32),('mask',u32)]
class SmEntry(C.Structure):
 _fields_=[('gpc',u32),('tpc',u32)]
class SmMap(C.Structure):
 _fields_=[('sm',SmEntry*512),('count',u32),('route',Route)]
class GpcMask(C.Structure):
 _fields_=[('route',Route),('mask',u32)]
assert (C.sizeof(Alloc),C.sizeof(Ctrl),C.sizeof(Device),C.sizeof(Route),C.sizeof(Mask),C.sizeof(SmMap))==(32,32,56,16,24,4120)
out={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'steps':[]}
def ioctl(fd,num,obj):
 cmd=0xc0000000 | (C.sizeof(obj)<<16) | (ord('F')<<8) | num
 fcntl.ioctl(fd,cmd,obj,True)
def alloc(fd,root,parent,cls,params=None,new=0):
 x=Alloc(root,parent,new,cls,C.addressof(params) if params is not None else 0,C.sizeof(params) if params is not None else 0,0)
 ioctl(fd,0x2b,x);out['steps'].append({'operation':'alloc','class':hex(cls),'status':hex(x.status),'handle':hex(x.new)});return x
def ctrl(fd,client,obj,cmd,params):
 x=Ctrl(client,obj,cmd,0,C.addressof(params),C.sizeof(params),0);ioctl(fd,0x2a,x)
 out['steps'].append({'operation':'control','cmd':hex(cmd),'status':hex(x.status)});return x.status
try:
 gpu_fd=os.open('/dev/nvidia0',os.O_RDWR|os.O_CLOEXEC)
 fd=os.open('/dev/nvidiactl',os.O_RDWR|os.O_CLOEXEC)
 root=alloc(fd,0,0,0x41)
 if root.status: raise RuntimeError('root allocation failed')
 ids=(u32*32)()
 if ctrl(fd,root.new,root.new,0x201,ids): raise RuntimeError('attached ids query failed')
 valid=[int(x) for x in ids if x!=0xffffffff];out['attached_gpu_ids']=[hex(x) for x in valid]
 if len(valid)!=1: raise RuntimeError('expected exactly one NVIDIA GPU; refusing ambiguous mapping')
 mask=u32()
 if ctrl(fd,root.new,root.new,0x204,mask): raise RuntimeError('device ids query failed')
 out['device_ids_mask']=hex(mask.value)
 if mask.value==0 or mask.value&(mask.value-1): raise RuntimeError('ambiguous device mask')
 dev=alloc(fd,root.new,root.new,0x80,Device(deviceId=mask.value.bit_length()-1))
 if dev.status: raise RuntimeError('device allocation failed')
 subid=u32(0);sub=alloc(fd,root.new,dev.new,0x2080,subid,0xcaf00001)
 if sub.status: raise RuntimeError('subdevice allocation failed')
 gm=GpcMask();status=ctrl(fd,root.new,sub.new,0x2080122a,gm);out['gpc_mask']={'status':hex(status),'value':hex(gm.mask)}
 if status: raise RuntimeError('gpc mask query failed')
 out['tpc_masks']=[]
 for i in range(32):
  if gm.mask & (1<<i):
   m=Mask(gpc=i);st=ctrl(fd,root.new,sub.new,0x2080122b,m);out['tpc_masks'].append({'gpc':i,'status':hex(st),'value':hex(m.mask) if st==0 else None})
 sm=SmMap();st=ctrl(fd,root.new,sub.new,0x2080120f,sm);out['sm_map']={'status':hex(st),'count':sm.count if st==0 else None,'entries':[{'sm':i,'gpc':sm.sm[i].gpc,'tpc':sm.sm[i].tpc} for i in range(sm.count)] if st==0 and sm.count<=512 else None}
 os.close(fd);os.close(gpu_fd)
except Exception as e: out['error']=repr(e)
print(json.dumps(out,indent=2))

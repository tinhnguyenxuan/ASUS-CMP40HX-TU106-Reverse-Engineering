#!/usr/bin/env python3
"""RM GET candidates only. No MMIO, fuse-controller access or configuration controls."""
import ctypes as C, fcntl, os, json, datetime, traceback
U=C.c_uint32; Q=C.c_uint64
class Alloc(C.Structure): _fields_=[('root',U),('parent',U),('new',U),('cls',U),('params',Q),('size',U),('status',U)]
class Ctrl(C.Structure): _fields_=[('client',U),('obj',U),('cmd',U),('flags',U),('params',Q),('size',U),('status',U)]
class Device(C.Structure): _fields_=[('deviceId',U),('share',U),('targetClient',U),('targetDevice',U),('flags',U),('vaSpaceSize',Q),('vaStart',Q),('vaLimit',Q),('vaMode',U)]
class Route(C.Structure): _fields_=[('flags',U),('route',Q)]
class Reconf(C.Structure): _fields_=[('gpc',U),('mask',U),('route',Route)]
class Simple(C.Structure): _fields_=[('gpc',U),('mask',U)]
assert (C.sizeof(Alloc),C.sizeof(Ctrl),C.sizeof(Device),C.sizeof(Reconf),C.sizeof(Simple))==(32,32,56,24,8)
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'steps':[]}
def ioctl(fd,num,obj): fcntl.ioctl(fd,0xc0000000|(C.sizeof(obj)<<16)|(ord('F')<<8)|num,obj,True)
def alloc(fd,root,parent,cls,params=None,new=0):
 x=Alloc(root,parent,new,cls,C.addressof(params) if params is not None else 0,C.sizeof(params) if params is not None else 0,0);ioctl(fd,0x2b,x);out['steps'].append({'op':'alloc','class':hex(cls),'status':hex(x.status)});return x
def ctrl(fd,client,obj,cmd,p):
 before=bytes(p).hex();x=Ctrl(client,obj,cmd,0,C.addressof(p),C.sizeof(p),0);ioctl(fd,0x2a,x);out['steps'].append({'op':'control','cmd':hex(cmd),'size':C.sizeof(p),'status':hex(x.status),'input':before,'output':bytes(p).hex()});return x.status
try:
 gpu=os.open('/dev/nvidia0',os.O_RDWR|os.O_CLOEXEC);fd=os.open('/dev/nvidiactl',os.O_RDWR|os.O_CLOEXEC)
 root=alloc(fd,0,0,0x41)
 if root.status: raise RuntimeError('root allocation')
 ids=(U*32)();assert ctrl(fd,root.new,root.new,0x201,ids)==0
 valid=[int(x) for x in ids if x!=0xffffffff];out['gpu_ids']=[hex(x) for x in valid]
 if len(valid)!=1: raise RuntimeError('GPU ambiguous')
 mask=U();assert ctrl(fd,root.new,root.new,0x204,mask)==0
 if mask.value==0 or mask.value&(mask.value-1): raise RuntimeError('device ambiguous')
 dev=alloc(fd,root.new,root.new,0x80,Device(deviceId=mask.value.bit_length()-1))
 if dev.status: raise RuntimeError('device allocation')
 sub=alloc(fd,root.new,dev.new,0x2080,U(0),0xcaf00001)
 if sub.status: raise RuntimeError('subdevice allocation')
 for g in range(3):
  p=Reconf(gpc=g,mask=0xdeadbeef);ctrl(fd,root.new,sub.new,0x2080123b,p)
  p=Simple(gpc=g,mask=0xdeadbeef);ctrl(fd,root.new,sub.new,0x208001e7,p)
 # Independent public GET of cached instruction-rate fuse-derived information, not a TPC-disable mask.
 p=(U*(1+255*2))();ctrl(fd,root.new,sub.new,0x2080123c,p)
 # KGR internal topology response is 8 structures of 0x54c bytes.
 p=(C.c_ubyte*0x2a60)();ctrl(fd,root.new,sub.new,0x20800a26,p)
 os.close(fd);os.close(gpu)
except Exception as e: out['error']=repr(e);out['traceback']=traceback.format_exc()
# Truncate the all-zero large response without losing informative bytes.
for x in out['steps']:
 if x.get('size')==0x2a60:
  for k in ('input','output'):
   s=x[k];x[k+'_nonzero_bytes']=[(i//2,s[i:i+2]) for i in range(0,len(s),2) if s[i:i+2]!='00'];del x[k]
print(json.dumps(out,indent=2))

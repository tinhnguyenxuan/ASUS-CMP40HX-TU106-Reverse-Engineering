"""Offline Vulkan capture/ABI audit. No library calls, target access or device I/O."""
import ast,ctypes as C,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2];p=root/'PHASE21_FUNCTIONAL_RESEARCH';d=p/'evidence/target_live_20261104'
def load(n):return json.loads((d/n).read_text())
def ref(n):f=d/n;return {'path':str(f.relative_to(root)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
j=load('vulkan_nvidia_only.json');cmd=j['command'];start=cmd.index('import ctypes');end=cmd.rfind('\nREMOTE');tree=ast.parse(cmd[start:end])
info=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Info')
fields=next(n.value for n in info.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='_fields_' for x in n.targets))
parsed=[]
for item in fields.elts:
 name,dtype=item.elts;assert isinstance(name,ast.Constant) and isinstance(dtype,ast.Attribute) and dtype.value.id=='c'
 assert dtype.attr in ('c_uint','c_void_p')
 parsed.append((name.value,getattr(C,dtype.attr)))
class Info(C.Structure):_fields_=parsed
assert C.sizeof(C.c_void_p)==8 and C.sizeof(C.c_uint)==4,'This checker supports the retained LP64 case only'
actual={n:getattr(Info,n).offset for n,_ in parsed}
expected={'sType':0,'next':8,'flags':16,'app':24,'layers':32,'layerNames':40,'extensions':48,'extensionNames':56}
assert actual==expected and C.sizeof(Info)==64
assert 'info.sType=1' in cmd and 'lib.vkCreateInstance.argtypes=' in cmd
out=json.loads(j['stdout']);assert out['create_result']==-9
assert "Could not get 'vkCreateInstance'" in j['stderr'] and 'Found no drivers' in j['stderr']
software=load('vulkan_device_query.json');assert software['create_result']==0
assert all(x['vendor_id']!='0x10de' for x in software['devices'])
linkage=load('nvidia_library_linkage.json');assert 'libGLX_nvidia.so.615.71.09' in linkage['stdout']
symbols=load('nvidia_vk_symbols_registry.json');assert all(' T '+x in symbols['stdout'] for x in ['vkCreateInstance','vkGetInstanceProcAddr','vk_icdGetInstanceProcAddr'])
permissions=load('glm_userspace_diagnostic.json');denied=[x['path'] for x in permissions['nodes'] if x.get('open_rdonly',{}).get('errno')==13]
r={'schema':'phase21-vulkan-capture-audit-v1','inputs':[ref(n) for n in ['vulkan_nvidia_only.json','vulkan_device_query.json','nvidia_library_linkage.json','nvidia_vk_symbols_registry.json','glm_userspace_diagnostic.json','vulkan_direct_icd_dispatch.json','vulkan_negotiated_dispatch.json']], 'lp64_create_info':{'field_offsets':actual,'sizeof':C.sizeof(Info),'result':'MATCHES reviewed VkInstanceCreateInfo LP64 layout','limits':'Local struct-layout audit only; no target replay or pointer/calling-convention validation for uncaptured probe code'},'loader_failure':{'vkCreateInstance':-9,'name':'VK_ERROR_INCOMPATIBLE_DRIVER','boundary':'Driver discovery/global entrypoint resolution fails; no NVIDIA physical-device render tested'},'software_enumeration':software['devices'],'denied_drm_nodes':denied,'conclusions':{'missing_dynamic_export':'Contradicted for three captured ELF symbols, not all possible symbols/dependencies','dependency_resolution':'Captured ldd resolves direct dependency graph; runtime dlopen/version/initialization failure remains possible','drm_permission_causality':'EACCES observed; causal link to Vulkan not isolated','gpu_vulkan_hardware':'UNKNOWN; CUDA/GLES success neither proves nor disproves Vulkan feature support','direct_probe_abi':'Incomplete provenance: command/source absent in two direct dispatch captures'},'next':['Review full direct-probe pointer return declarations before trusting NULL attribution','Reproduce loader/native-C ABI query under unchanged permissions if target access returns','Check runtime library opens/version negotiation separately from shader/scanout'], 'hardware_actions_executed':False}
(p/'evidence/vulkan_capture_audit.json').write_text(json.dumps(r,indent=2)+'\n')
print('LP64 VkInstanceCreateInfo layout PASS; retained Vulkan failure scoped to loader/ICD discovery; hardware capability remains UNKNOWN')

"""Bounded BIT display-root audit; no disassembly/execution or device access."""
from pathlib import Path
import struct,json,hashlib,shutil
root=Path(__file__).resolve().parents[2];p=root/'PHASE21_FUNCTIONAL_RESEARCH'
files=[root/'work_v15/outputs/CMP40HX_ORIGINAL_1MB.bin',root/'work_v15/outputs/cmp40hx_t4.bin']
files+=list((root/'CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF/03_VBIOS/geforce').glob('*.rom'))
rows=[]
for f in files:
 b=f.read_bytes();r={'path':str(f.relative_to(root)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
 base=0x28600
 if b[base:base+2]!=b'\x55\xaa':
  r['status']='HTML_NOT_ROM' if b.lstrip().lower().startswith(b'<!doctype html') else 'NOT_PARSED_AS_MATCHED_IMAGE';r['prefix_hex']=b[:32].hex();r['limitation']='Expected image root absent; filename does not establish ROM identity or validity';rows.append(r);continue
 bit=base+0x1b0;assert b[bit:bit+7]==b'\xff\xb8BIT\0\0'
 h,stride,n=b[bit+8:bit+11];assert h==12 and stride==6 and n<64 and sum(b[bit:bit+h])%256==0
 roots=[]
 for i in range(n):
  off=bit+h+i*stride;kind,version,length,relative=struct.unpack_from('<BBHH',b,off)
  if chr(kind) not in ('U','d','D','T','I'):continue
  data=base+relative;assert length==0 or (relative>0 and relative+length<=0xf400)
  rtype={ 'U':'Display programming root at+0 (envytools/nvbios and Nouveau disp)', 'd':'DP INFO pointer at+0 (envytools)', 'D':'DFP/panel-related pointers, detailed field semantics incomplete', 'T':'TMDS token; version-specific interpretation not assigned', 'I':'General init; not equivalent to display-programming root'}[chr(kind)]
  roots.append({'token':chr(kind),'version':version,'entry_file_offset':hex(off),'length':length,'data_file_offset':hex(data),'raw':b[data:data+length].hex(),'first_u16':hex(struct.unpack_from('<H',b,data)[0]) if length>=2 else None,'scope':rtype})
 U=next(x for x in roots if x['token']=='U');d=next(x for x in roots if x['token']=='d')
 assert U['raw']=='0000020000' and U['first_u16']=='0x0' and d['raw']=='0000'
 r.update({'status':'BOUNDED_ROOTS_DECODED','legacy_base':hex(base),'bit':hex(bit),'roots':roots,'display_programming_pointer_null':True,'dp_info_pointer_null':True,'remaining_U_bytes':'02 00 00 retained as unknown fields, not erased/empty token','limits':['No registered display-script table through this BIT U pointer','No claim of absent hidden scripts or driver/firmware fallback','General init may still touch graphics/display-related registers','No physical silicon/PHY or restoration conclusion']});rows.append(r)
sources=[]
for name in ['nvbios.c','bit.c','d.c','D.c']:
 src=Path('/tmp/envytools/nvbios')/name;dst=p/'evidence/sources'/('displayroots_'+name);shutil.copyfile(src,dst)
 sources.append({'path':str(dst.relative_to(root)),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
r={'schema':'phase21-vbios-display-roots-v1','inputs':rows,'parser_sources':sources,'nouveau_corroboration':'https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/nouveau/nvkm/subdev/bios/disp.c nvbios_disp_table: BIT U version1 uses u16 at+0, null returns no table'}
(p/'evidence/vbios_display_roots.json').write_text(json.dumps(r,indent=2)+'\n')
for x in rows:print(x['path'],x['status'],x.get('display_programming_pointer_null'))

"""Offline extraction of board tables. No device operations."""
import hashlib,json,re,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[2]; out=root/'PHASE21_FUNCTIONAL_RESEARCH'
sources=out/'evidence/sources';sources.mkdir(exist_ok=True)
paths=[Path('/tmp/envytools/nvbios')/x for x in ['i2c.c','gpio.c','bios.h','dcb.c']]+[Path('/tmp/cmpchk/0001-cmp40hx-unlock.patch')]
manifest=[]
for p in paths:
 dst=sources/p.name;shutil.copyfile(p,dst)
 manifest.append({'input':str(p),'snapshot':str(dst.relative_to(root)),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'provenance':'preexisting local snapshot; upstream commit/release UNKNOWN'})
(sources/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
bios_h=(sources/'bios.h').read_text()
hpd={int(v,16):n for n,v in re.findall(r'ENVY_BIOS_GPIO_(HPD_\d+)\s*=\s*(0x[0-9a-f]+)',bios_h)}
results=[]
for item in json.loads((out/'evidence/dcb.json').read_text()):
 b=(root/item['path']).read_bytes();tables={}
 for name in ['communications','gpio','i2c_devices','connector']:
  addr=int(item['tables'][name]['absolute_offset'],16)
  v,h,n,s=b[addr:addr+4]; assert h>=4 and s>=4 and addr+h+n*s<=0x37a00
  rows=[]
  for i in range(n):
   off=addr+h+i*s; raw=b[off:off+s];row={'index':i,'offset':hex(off),'raw':raw.hex()}
   if name=='communications':
    assert v==0x41
    word=int.from_bytes(raw,'little')
    row.update({'i2c_port':word&31,'dpaux_port':(word>>5)&31,'reserved_high':hex(word>>10),'interpretation':'CCB 4.1 NVIDIA spec; high bits retained, not decoded'})
   elif name=='gpio':
    assert v==0x41 and s>=5
    row.update({'line':raw[0]&63,'tag':hex(raw[1]),'hpd_tag':hpd.get(raw[1]),'special_output':raw[2],'special_input':raw[3]&31,'unused':raw[1]==255})
   rows.append(row)
  tables[name]={'version':hex(v),'header_size':h,'entry_count':n,'entry_size':s,'rows':rows}
 results.append({'rom':item['path'],'sha256':item['sha256'],'tables':tables})
(out/'evidence/board_tables.json').write_text(json.dumps(results,indent=2)+'\n')
for r in results:
 print(r['rom'])
 for k,t in r['tables'].items():
  print(k,t['entry_count'],'entries')
  if k=='communications': print('DPAUX declarations',[(x['index'],x['dpaux_port']) for x in t['rows'] if x['dpaux_port']!=31])
  if k=='gpio': print('HPD tags',[x for x in t['rows'] if x['hpd_tag']])

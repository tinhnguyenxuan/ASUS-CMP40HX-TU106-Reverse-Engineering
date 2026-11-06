"""Offline ELF/firmware provenance and bounded capability-string references.
No indirect pointer/code semantics inferred; only adjacent 32-bit AUIPC/LUI+ADDI pairs.
"""
from pathlib import Path
import struct,json,hashlib,re
root=Path(__file__).resolve().parents[2];out=root/'PHASE21_FUNCTIONAL_RESEARCH/evidence'
def elf(b,base):
 assert b[base:base+6]==b'\x7fELF\x02\x01'
 eh=struct.unpack_from('<HHIQQQIHHHHHH',b,base+16)
 typ,mach,ver,entry,phoff,shoff,flags,ehsize,phsize,phnum,shsize,shnum,shstr=eh
 assert shsize==64 and shnum<200 and base+shoff+shsize*shnum<=len(b)
 raw=[struct.unpack_from('<IIQQQQIIQQ',b,base+shoff+i*shsize) for i in range(shnum)]
 names=b[base+raw[shstr][4]:base+raw[shstr][4]+raw[shstr][5]]
 sections=[]
 for sh in raw:
  no,t,fl,va,fo,sz,li,inf,al,en=sh
  name=names[no:].split(b'\0',1)[0].decode('ascii',errors='replace')
  if t!=8:assert base+fo+sz<=len(b)
  sections.append({'name':name,'type':t,'flags':fl,'va':va,'file_offset':base+fo,'size':sz})
 return {'base':base,'type':typ,'machine':mach,'entry':entry,'sections':sections}
def sx(v,n):return v-(1<<n) if v&(1<<(n-1)) else v
paths=[root/'work_v15/outputs/gsp_tu10x.bin',Path('/tmp/gsp_firmware/gsp-570.144.bin'),Path('/tmp/gsp_firmware/gsp-535.113.01.bin')]
records=[]
for p in paths:
 b=p.read_bytes();e=elf(b,0)
 fw=[s for s in e['sections'] if s['name']=='.fwversion']
 rec={'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'outer_elf':e,'fwversion_sections':[{'offset':s['file_offset'],'hex':b[s['file_offset']:s['file_offset']+s['size']].hex(),'text':b[s['file_offset']:s['file_offset']+s['size']].rstrip(b'\0').decode(errors='replace')} for s in fw]}
 inner=elf(b,64) if b[64:68]==b'\x7fELF' else None
 rec['inner_elf']=inner
 if p==paths[0]:
  assert inner
  sections=[s for s in inner['sections'] if s['type']!=8 and s['size'] and s['va']]
  def mapping(off):
   matches=[s for s in sections if s['file_offset']<=off<s['file_offset']+s['size']]
   return [{'section':s['name'],'va':s['va']+off-s['file_offset']} for s in matches]
  targets=[]
  for m in re.finditer(rb'[\x20-\x7e]{5,}\x00',b):
   name=m.group()[:-1].decode()
   if re.search(r'(?i)(^rm.*(?:display|profil|tensor|cmp|fecs|gpccs|sec2)|cmp.?sku|display.*fuse|fuse.*display)',name):
    targets.append({'text':name,'file_offset':m.start(),'mappings':mapping(m.start())})
  for t in targets:
   refs=[]
   for mp in t['mappings']:
    pattern=struct.pack('<Q',mp['va'])
    for sec in sections:
     if sec['flags']&4:continue
     start=sec['file_offset'];end=start+sec['size'];pos=start
     while True:
      pos=b.find(pattern,pos,end)
      if pos<0:break
      refs.append({'pointer_file_offset':hex(pos),'pointer_va':hex(sec['va']+pos-start),'section':sec['name'],'aligned_8':pos%8==0,'context_file_offset':hex(max(start,pos-16)),'context_hex':b[max(start,pos-16):min(end,pos+32)].hex(),'interpretation':'raw address-valued bytes; descriptor shape and access semantics unproven'})
      pos+=1
   t['data_pointer_candidates']=refs
  rec['capability_strings']=targets
  target_vas={x['va'] for t in targets for x in t['mappings']}
  pairs=[];scanned=0
  for sec in sections:
   if not sec['flags']&4:continue
   lo=sec['file_offset'];hi=lo+sec['size']
   for off in range(lo,hi-7,2):
    w=struct.unpack_from('<I',b,off)[0]
    if w&0x7f not in (0x17,0x37):continue
    rd=(w>>7)&31
    if not rd:continue
    w2=struct.unpack_from('<I',b,off+4)[0]
    if w2&0x707f not in (0x13,0x1b) or (w2>>15)&31!=rd:continue
    pc=sec['va']+off-lo
    value=((pc if w&0x7f==0x17 else 0)+sx(w&0xfffff000,32)+sx(w2>>20,12))&((1<<64)-1)
    if w2&0x7f==0x1b:value=sx(value&0xffffffff,32)&((1<<64)-1)
    scanned+=1
    if value in target_vas:pairs.append({'pc':hex(pc),'file_offset':hex(off),'raw':b[off:off+8].hex(),'target_va':hex(value),'kind':('AUIPC' if w&0x7f==0x17 else 'LUI')+('+ADDIW' if w2&0x7f==0x1b else '+ADDI')+' syntactic adjacent pair; execution/reachability unproven'})
  rec['adjacent_pair_scan']={'coverage':'Halfword-aligned candidates in executable sections; ADDI/ADDIW; no CFG, no compressed ADDI, no intervening instructions, no pointer dereference tracing','candidate_pairs':scanned,'string_address_matches':pairs}
 records.append(rec)
(out/'firmware_capability_inventory.json').write_text(json.dumps(records,indent=2)+'\n')
for r in records:
 print(r['path'],r['sha256'],r['fwversion_sections'])
 if 'capability_strings' in r:print('capability strings',len(r['capability_strings']),'adjacent address refs',len(r['adjacent_pair_scan']['string_address_matches']))

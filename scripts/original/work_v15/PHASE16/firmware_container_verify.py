#!/usr/bin/env python3
# firmware_container_verify.py — verify ucodes_tu10x.bin container (offline, read-only, stdlib only).
# Parses ALL 496 slots (not the legacy 11). Re-run: /usr/bin/python3 firmware_container_verify.py
import struct, hashlib, json, math, sys
from collections import Counter
from pathlib import Path

BIN = Path('/home/REDACTED_USER/codex-work/work_v15/outputs/ucodes_tu10x.bin')
OUT = Path('/home/REDACTED_USER/codex-work/work_v15/PHASE16/firmware_container_verified.json')
HDR = struct.Struct('<8sIIQ')   # magic, version, count, fingerprint64 = 24 B
REC = struct.Struct('<QQII')    # length, unknown, marker, file_offset = 24 B

def entropy(b):
    if not b: return 0.0
    freq=[0]*256
    for x in b: freq[x]+=1
    n=len(b)
    return round(-sum((c/n)*math.log2(c/n) for c in freq if c),6)

def nz(b):
    if not b: return 0.0
    return round(sum(1 for x in b if x)/len(b),6)

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    data=BIN.read_bytes(); size=len(data); inhash=sha(data)
    print('RE-RUN: /usr/bin/python3 firmware_container_verify.py  (cwd PHASE16)')
    magic,version,count,fp=HDR.unpack_from(data,0)
    hdr=HDR.size; table_end=hdr+count*REC.size; first_payload=0x2F00
    records=[]; issues=[]
    for i in range(count):
        roff=hdr+i*REC.size
        length,unknown,marker,foff=REC.unpack_from(data,roff)
        rec={'slot':i,'record_offset':roff,'length':length,'unknown':unknown,'marker':marker,'file_offset':foff}
        ri=[]
        if length==0 and unknown==0 and marker==0 and foff==0: rec['class']='zero'
        elif marker==0 and foff==0 and unknown==0 and length!=0: rec['class']='size_only'
        elif marker==4:
            rec['class']='valid_marker4'
            if foff<0 or foff>=size: ri.append('offset_out_of_range')
            elif length<0: ri.append('negative_length')
            elif foff+length>size: ri.append('overflow_eof')
            elif foff+length>table_end and foff<first_payload: ri.append('offset_inside_table')
            if foff%4: ri.append('offset_not_aligned4')
            if length%4: ri.append('length_not_aligned4')
        else:
            rec['class']='other'; ri.append('unexpected_marker_or_fields')
        rec['issues']=[x for x in ri if x]
        issues.extend({'slot':i,'issue':x} for x in rec['issues'])
        records.append(rec)
    payloads=[]
    for rec in records:
        if rec['class']!='valid_marker4' or rec['issues']: continue
        off,ln=rec['file_offset'],rec['length']; blob=data[off:off+ln]
        payloads.append({'slot':rec['slot'],'offset':off,'length':ln,'offset_hex':'0x%08X'%off,
            'sha256':sha(blob),'entropy':entropy(blob),'nonzero_ratio':nz(blob),
            'head16':blob[:16].hex(),'tail16':blob[-16:].hex()})
    payloads.sort(key=lambda p:p['offset'])
    overlap=[]; duplicate=[]; seen={}
    for p in payloads:
        if p['offset'] in seen: duplicate.append({'slots':[seen[p['offset']],p['slot']],'offset':p['offset']})
        seen[p['offset']]=p['slot']
    for a,b in zip(payloads,payloads[1:]):
        if a['offset']+a['length']>b['offset']: overlap.append({'slots':[a['slot'],b['slot']],'a_end':a['offset']+a['length'],'b_start':b['offset']})
    gaps=[]; prev=table_end
    for p in payloads:
        g=p['offset']-prev
        if g>0:
            gb=data[prev:p['offset']]
            gaps.append({'start':prev,'end':p['offset'],'size':g,'all_zero':all(x==0 for x in gb),'nonzero_ratio':nz(gb)})
        prev=p['offset']+p['length']
    tail=size-prev
    if tail>0:
        tb=data[prev:]
        gaps.append({'start':prev,'end':size,'size':tail,'all_zero':all(x==0 for x in tb),'nonzero_ratio':nz(tb),'note':'tail_to_eof'})
    covered=sum(p['length'] for p in payloads)
    scan=[]; parsed_offs={p['offset'] for p in payloads}
    for o in range(hdr,first_payload-3,4):
        m=struct.unpack_from('<I',data,o)[0]; fo=struct.unpack_from('<I',data,o+4)[0]
        if m==4 and 0<=fo<size: scan.append({'scan_offset':o,'marker':m,'file_offset':fo})
    scan_conf=[h for h in scan if h['file_offset'] in parsed_offs]
    scan_extra=[h for h in scan if h['file_offset'] not in parsed_offs]
    report={'input_file':str(BIN),'input_size':size,'input_sha256':inhash,
        'header':{'magic':magic.decode('ascii','replace'),'version':version,'count':count,
            'fingerprint64':fp,'fingerprint64_hex':'0x%016X'%fp,'header_size':hdr,
            'table_end':table_end,'first_payload':first_payload,
            'padding_to_first_payload':first_payload-table_end},
        'hypothesis':{'header_struct':'<8sIIQ (24 B)','record_struct':'<QQII (24 B)','record_count_from_header':count},
        'record_counts':dict(Counter(r['class'] for r in records)),
        'invalid_unresolved':issues,'records':records,'payloads':payloads,
        'overlaps':overlap,'duplicates':duplicate,'gaps':gaps,
        'coverage':{'covered_bytes':covered,'uncovered_bytes':size-covered,'payload_count':len(payloads)},
        'independent_scan':{'region':'[header_end, first_payload)','hits':len(scan),'confirmed':len(scan_conf),'extra':scan_extra,
            'parsed_not_in_scan':[p for p in payloads if p['offset'] not in {h['file_offset'] for h in scan}]}}
    OUT.write_text(json.dumps(report,indent=2))
    print('HEADER',magic.decode(),'ver',version,'count',count,'fp',hex(fp))
    print('TABLE_END',table_end,hex(table_end),'FIRST_PAYLOAD',first_payload,'PAD',first_payload-table_end)
    print('CLASSES',dict(Counter(r['class'] for r in records)))
    print('PAYLOADS',len(payloads),'OVERLAPS',len(overlap),'DUPS',len(duplicate),'ISSUES',len(issues))
    print('COVERED',covered,'UNCOVERED',size-covered,'GAPS',len(gaps))
    print('SCAN',len(scan),'CONFIRMED',len(scan_conf),'EXTRA',len(scan_extra))
    print('WROTE',OUT)

if __name__=='__main__': main()

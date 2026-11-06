"""Bounded DTD-layout interpretation of BIT D first pointer; no hardware calls.
The 10-record window is analyst-selected; no table count or terminator is inferred.
"""
from pathlib import Path
import json,struct,hashlib
root=Path(__file__).resolve().parents[2];p=root/'PHASE21_FUNCTIONAL_RESEARCH';results=[]
for name in ['CMP40HX_ORIGINAL_1MB.bin','cmp40hx_t4.bin']:
 f=root/'work_v15/outputs'/name;b=f.read_bytes();base=0x28600
 bit=base+0x1b0;assert b[bit:bit+7]==b'\xff\xb8BIT\0\0'
 h,stride,n=b[bit+8:bit+11];assert h==12 and stride==6 and sum(b[bit:bit+h])%256==0
 entries=[struct.unpack_from('<BBHH',b,bit+h+i*stride) for i in range(n)]
 D=next(x for x in entries if x[0]==ord('D'));T=next(x for x in entries if x[0]==ord('T'))
 assert D[1:3]==(1,4) and T[1:3]==(1,2)
 start,second=struct.unpack_from('<HH',b,base+D[3]);tmds=struct.unpack_from('<H',b,base+T[3])[0]
 assert start==0x517d and second==0 and tmds==0
 rows=[]
 for i in range(11):
  off=base+start+i*18;assert off+18<=base+0xf400
  v=b[off:off+18];clock=struct.unpack_from('<H',v)[0]*10
  ha=v[2]+((v[4]>>4)<<8);hb=v[3]+((v[4]&15)<<8)
  va=v[5]+((v[7]>>4)<<8);vb=v[6]+((v[7]&15)<<8)
  hs=v[8]+((v[11]>>6)<<8);hw=v[9]+(((v[11]>>4)&3)<<8)
  vs=(v[10]>>4)+(((v[11]>>2)&3)<<4);vw=(v[10]&15)+((v[11]&3)<<4)
  plausible=bool(clock>0 and ha>=64 and va>=64 and hb>0 and vb>0 and hs+hw<=hb and vs+vw<=vb)
  row={'index':i,'offset':hex(off),'raw':v.hex(),'pixel_clock_khz':clock,'hactive':ha,'hblank':hb,'vactive':va,'vblank':vb,'hsync_offset':hs,'hsync_width':hw,'vsync_offset':vs,'vsync_width':vw,'flags':hex(v[17]),'interlace_bit':bool(v[17]&128),'raster_rate_hz':clock*1000/((ha+hb)*(va+vb)) if (ha+hb)*(va+vb) else None,'plausibility_check':plausible}
  rows.append(row)
 assert all(x['plausibility_check'] for x in rows[:10])
 results.append({'input':{'path':str(f.relative_to(root)),'sha256':hashlib.sha256(b).hexdigest()},'BIT_D_data':hex(base+D[3]),'first_pointer':hex(start),'second_pointer':hex(second),'BIT_T_data':hex(base+T[3]),'tmds_info_pointer':hex(tmds),'interpreted_records':rows[:10],'following_bytes_interpreted_as_dtd_for_boundary_check':rows[10],'limits':['18-byte DTD layout interpretation; count10 is bounded observation, not encoded table size','No EDID128-byte envelope/checksum or attached monitor is claimed','No mode availability, consumer reachability or output support is inferred','BIT D+2 legacy FP mode pointer is null; +0 is a separate timing-like data pointer']})
assert [x['raw'] for x in results[0]['interpreted_records']]==[x['raw'] for x in results[1]['interpreted_records']]
r={'schema':'phase21-retained-display-timings-v1','source_layout':'https://github.com/torvalds/linux/blob/master/include/drm/drm_edid.h struct detailed_timing/detailed_pixel_timing','legacy_BIT_D_consumer':'https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/nouveau/nouveau_bios.c parse_bit_display_tbl_entry distinguishes+0 timing-like records from+2 FP mode pointer','results':results}
(p/'evidence/retained_display_timings.json').write_text(json.dumps(r,indent=2)+'\n')
for x in results[0]['interpreted_records']:print(x['index'],f"{x['hactive']}x{x['vactive']}",x['pixel_clock_khz'],'kHz',round(x['raster_rate_hz'],3),'Hz')
print('First10 records plausible, original/derivative identical; following layout candidate:',results[0]['following_bytes_interpreted_as_dtd_for_boundary_check']['plausibility_check'])

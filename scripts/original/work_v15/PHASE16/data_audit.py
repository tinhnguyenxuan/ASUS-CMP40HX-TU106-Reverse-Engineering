#!/usr/bin/env python3
"""Recompute facts from archived inputs. Never queries the GPU."""
import collections
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text())


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def entropy(b):
    return -sum((v / len(b)) * math.log2(v / len(b)) for v in collections.Counter(b).values()) if b else 0


def wpr_address(raw):
    """TU102 dev_fb.h: VAL=31:4, ALIGNMENT=12; extract before shifting."""
    return ((raw >> 4) & 0xfffffff) << 12


def run():
    inputs = ['outputs/CMP40HX_ORIGINAL_1MB.bin', 'outputs/cmp40hx_t4.bin', 'outputs/gsp_tu10x.bin', 'outputs/ucodes_tu10x.bin', 'RAW_DATA/vbios_shadow.bin', 'FUSE/fuse2.json', 'UNKNOWN_DATABASE.json', 'TOOLS/verify_all.py']
    dump('input_hashes.json', {p: dict(bytes=(ROOT / p).stat().st_size, sha256=sha((ROOT / p).read_bytes())) for p in inputs})
    fuse = load('FUSE/fuse2.json')
    regs = {int(k): v for k, v in fuse['regs'].items()}
    poison = set(fuse['poison'])
    classes = collections.Counter('poison' if v in poison else 'zero' if v == 0 else 'data' for v in regs.values())
    nonpoison = [k for k, v in regs.items() if v not in poison]
    ones = [k for k, v in regs.items() if v == 1]
    digest_bytes = b''.join(struct.pack('<I', regs[o]) for o in range(0x718, 0x738, 4))
    dump('fuse_audit.json', dict(source='FUSE/fuse2.json; archived observation, not a fresh hardware read', requested_span=fuse['span'], dumped_words=len(regs), dumped_bytes=len(regs)*4, first_offset=min(regs), last_offset=max(regs), contiguous_offsets=sorted(regs) == list(range(min(regs), max(regs)+4, 4)), classes=dict(classes), poison_values=[hex(x) for x in sorted(poison)], last_nonpoison_offset=max(nonpoison), ones=len(ones), ones_first=min(ones), ones_last=max(ones), ones_offsets=ones, data_distinct=len({v for v in regs.values() if v and v not in poison}), pdi_from_words=hex((regs[0x348] << 32) | regs[0x344]), pdi_saved_report=load('FUSE/pdi_finding.json')['evidence']['nvidia_smi_GPU_PDI'], opaque_32_bytes=digest_bytes.hex(), physical_otp_cell_meaning='UNKNOWN; values alone do not identify OTP geometry or flags'))
    rom = (ROOT / 'outputs/CMP40HX_ORIGINAL_1MB.bin').read_bytes()
    t4 = (ROOT / 'outputs/cmp40hx_t4.bin').read_bytes()
    shadow = (ROOT / 'RAW_DATA/vbios_shadow.bin').read_bytes()
    span = len(rom) - 0x28600
    diffs = [dict(offset=i, original=rom[i], t4=t4[i]) for i in range(min(len(rom),len(t4))) if rom[i] != t4[i]]
    shdiff = [dict(shadow_offset=i, rom_offset=0x28600+i, shadow=shadow[i], rom=rom[0x28600+i]) for i in range(span) if shadow[i] != rom[0x28600+i]]
    bankdiff = [i for i in range(0x79000) if rom[i] != rom[i + 0x79000]]
    # Parse BIT headers; retain raw pointer values and reject implausible extents.
    bit = 0x287b0
    hdr, stride, count = rom[bit+8:bit+11]
    tokens = []
    def ptr(p):
        return 0x28600 + p + (0x11000 if p >= 0xf400 else 0)
    for i in range(count):
        p = bit + hdr + i*stride
        token, version, length, raw_ptr = struct.unpack_from('<BBHH', rom, p)
        tokens.append(dict(index=i, offset=p, token=chr(token), version=version, length=length, raw_pointer=raw_ptr, mapped_offset=ptr(raw_ptr), mapping_status='inherited Turing pointer formula, not a general parser'))
    perf = []
    for i in range(56):
        raw_ptr = struct.unpack_from('<I',rom,0x288d4+4*i)[0]
        if not raw_ptr:
            continue
        off = ptr(raw_ptr)
        if off + 4 > len(rom):
            perf.append(dict(index=i, raw_pointer=raw_ptr, offset=off, valid_header_shape=False))
            continue
        ver, h, sz, n = rom[off:off+4]
        size = h+sz*n
        perf.append(dict(index=i, raw_pointer=raw_ptr, offset=off, version=ver, header_size=h, entry_size=sz, count=n, valid_header_shape=bool(h >= 4 and sz and size <= 0x20000 and off+size <= len(rom)), semantic_status='UNKNOWN unless separately evidenced'))
    pcir = 0x28600 + struct.unpack_from('<H',rom,0x28618)[0]
    dump('vbios_audit.json',dict(rom_sha256=sha(rom), rom_bytes=len(rom), t4_bytes=len(t4), t4_shared_prefix_diff_count=len(diffs), t4_shared_prefix_diffs=diffs, repeat_span=0x79000, repeated_region_diffs=len(bankdiff), repeated_diff_first=min(bankdiff), repeated_diff_last=max(bankdiff), shadow_comparison_bytes=span, shadow_difference_count=len(shdiff), shadow_match_ratio=(span-len(shdiff))/span, shadow_differences=shdiff, pcir_offset=pcir, pcir_signature=rom[pcir:pcir+4].decode(), vendor=hex(struct.unpack_from('<H',rom,pcir+4)[0]), device=hex(struct.unpack_from('<H',rom,pcir+6)[0]), bit_header=dict(offset=bit, header=hdr, stride=stride, count=count), bit_tokens=tokens, perf_pointer_scan=perf, historical_images=load('outputs/vbios_map.json')['images'], warnings=['Historical images() ranges overlap and bank1 end 0xA1600 conflicts with repeat span 0x79000.', 'Header shape and checksum do not establish table semantics, authentication, encryption, or runtime use.']))
    uc = (ROOT / 'outputs/ucodes_tu10x.bin').read_bytes()
    payloads = []
    # Structural hypothesis: marker at H, length at H-16, file offset at H+4.
    # Scan the entire pre-payload header; do not truncate at the first 11 matches.
    for h in range(16, 0x2f00-7, 4):
        marker, off = struct.unpack_from('<II', uc, h)
        if marker != 4 or not 0x2f00 <= off < len(uc) or off & 255:
            continue
        length = struct.unpack_from('<I', uc, h-16)[0]
        if not length or off+length > len(uc):
            continue
        body = uc[off:off+length]
        payloads.append(dict(marker_offset=h, length_field_offset=h-16, offset=off, declared_length_candidate=length, end=off+length, sha256=sha(body), entropy=round(entropy(body),6), interpretation='structural candidate; marker/length semantics need external format source'))
    payloads.sort(key=lambda x: x['offset'])
    for i,p in enumerate(payloads):
        nxt = payloads[i+1]['offset'] if i+1<len(payloads) else len(uc)
        p['gap_to_next_payload_or_eof'] = nxt - p['end']
        p['gap_all_zero'] = p['end'] <= nxt and all(v == 0 for v in uc[p['end']:nxt])
    # Recheck the historical slices, which include padding.
    b6,b8 = uc[0xb7c00:0xd6700],uc[0xf5400:0x113f00]
    bd = [dict(relative_offset=i, b6=x, b8=y) for i,(x,y) in enumerate(zip(b6,b8)) if x!=y]
    timestamps = [dict(relative_offset=i, b6=b6[i:i+20].decode('ascii'),b8=b8[i:i+20].decode('ascii')) for i in (0x7200,0xb7b8)]
    residual = [d for d in bd if not any(i<=d['relative_offset']<i+20 for i in (0x7200,0xb7b8))]
    dump('firmware_audit.json',dict(container_bytes=len(uc), magic=uc[:8].decode(), header_word_0c=struct.unpack_from('<I',uc,12)[0], structural_payload_candidates=len(payloads), candidate_payloads=payloads, all_payload_spans_nonoverlapping=all(x['gap_to_next_payload_or_eof']>=0 for x in payloads), last_candidate_end=payloads[-1]['end'], legacy_blob10_extent_to_eof=len(uc)-0x134300, corrected_blob10_length_candidate=next(x['declared_length_candidate'] for x in payloads if x['offset']==0x134300), blob6_blob8=dict(compared_bytes=len(b6), differing_bytes=len(bd), diffs=bd, timestamp_windows=timestamps, differing_bytes_outside_timestamp_windows=residual, identical=False, interpretation='Two timestamp windows plus two unexplained bytes; no claim all changes are timestamp or no code differs.')))
    ap = load('TOPOLOGY/aperture_map.json')['reclassified_v7']
    corrected = ap['corrected_stats']
    mmio = load('MMIO/mmio.json')['registers']
    lo = mmio['NV_PFB_PRI_MMU_WPR2_ADDR_LO']['value']
    hi = mmio['NV_PFB_PRI_MMU_WPR2_ADDR_HI']['value']
    wlo, whi = wpr_address(lo), wpr_address(hi)
    dump('mmio_audit.json',dict(corrected_saved_page_counts=corrected, classified_pages=sum(corrected.values()), expected_pages_16MiB=4096, unclassified_pages=4096-sum(corrected.values()), poison_fraction_of_classified_pages=corrected['POISON']/sum(corrected.values()), poison_fraction_of_all_4096_pages=corrected['POISON']/4096, correction_method='arithmetic over historical summary; no new hardware read', wpr_raw_lo=lo, wpr_raw_hi=hi, raw_register_difference=hi-lo, wpr_decoded_lo=wlo, wpr_decoded_hi=whi, wpr_decoded_bound_difference_bytes=whi-wlo, wpr_decoded_bound_difference_mib=(whi-wlo)/2**20, wpr_sources=['https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/580.95.05/src/common/inc/swref/published/turing/tu102/dev_fb.h','https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/nova-core/fb/regs.rs'], wpr_interpretation='VAL[31:4]<<12. Linux Nova treats HI as exclusive; decoded bound difference is 128.875 MiB. Physical allocation and overlap with NVML Reserved are not established.', display_poison_implication='Does not distinguish removed hardware, decode mapping, privilege filtering, or gating.'))
    db = load('UNKNOWN_DATABASE.json')
    blocker_ids=['U-GSP-004','U-GSP-006','U-GSP-007','U-GSP-008','U-FW-012','U-FW-013']
    dump('unknown_audit.json',dict(total=len(db['items']), status_counts=dict(collections.Counter(x['status'] for x in db['items'])), duplicate_ids=[k for k,v in collections.Counter(x['id'] for x in db['items']).items() if v>1], phase15_blocker_ids_missing_from_database=[i for i in blocker_ids if i not in {x['id'] for x in db['items']}]))
    print(json.dumps(dict(fuse_classes=dict(classes), rom_t4_diff=len(diffs), shadow_diff=len(shdiff), firmware_payload_candidates=len(payloads), last_candidate_end=payloads[-1]['end'], ucodes_file_bytes=len(uc), blob6_blob8_differing_bytes=len(bd), timestamp_residual_diffs=residual, mmio_unclassified_pages=4096-sum(corrected.values())),indent=2))


if __name__ == '__main__':
    run()

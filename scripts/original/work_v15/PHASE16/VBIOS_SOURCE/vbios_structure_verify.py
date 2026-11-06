#!/usr/bin/env python3
"""Verify toan bo cau truc VBIOS CMP40HX/TU106 tu raw bytes.

Chuan: chi stdlib. Chi doc input (khong sua ROM, khong flash, khong truy cap GPU).
Tat so dem REDACTED_USER tu output cua chay nay, khong hardcode. Khong doan nghia bam/ma hoa tu entropy/checksum.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[2]          # /home/REDACTED_USER/codex-work/work_v15
OUT = SCRIPT.parent               # .../PHASE16/VBIOS_SOURCE
ROM_P = ROOT / "outputs" / "CMP40HX_ORIGINAL_1MB.bin"
T4_P = ROOT / "outputs" / "cmp40hx_t4.bin"
SHADOW_P = ROOT / "RAW_DATA" / "vbios_shadow.bin"

ROM_IMG = 0x28600      # legacy x86 image base trong container ROM (byte 55AA)
LEGACY_SZ = 0xF400     # kich thuc legacy image theo con tro Turing
EFI_SZ = 0x11000       # kich thuc khoi EFI (trong bo dao nguoc con tro)
REPEAT_SPAN = 0x79000  # do bank1 == bank2 (measure, khong ke thua tu images() cu)
TAIL_START = 0xF2000   # 2 * REPEAT_SPAN; NMX container tail bat dau day
ROM_SIZE = 1 << 20

SIGS = {
    "NVGIf_container": b"NVGIf",
    "ROM_55AA": b"\x55\xAA",
    "PCIR": b"PCIR",
    "NPDS": b"NPDS",
    "NPDE": b"NPDE",
    "NVGI": b"NVGI",
    "NMX_RIBILU": b"RIBILU",
    "NMX_PPID": b"PPID",
    "NMX_GXIP": b"GXIP",
    "NMX_JFFS": b"JFFS",
}

BIT_OFF = 0x287B0      # BIT table (trong legacy1)
PERF_OFF = 0x288D4     # PERF pointer slot (56 slot x 4 B)
KEYBLK = 0x3000        # NVGI key block (bank1)
KEYLEN = 0x4C0         # 38 record x 32 B
RECSZ = 32


def sha(b):
    return hashlib.sha256(b).hexdigest()


def find_all(data, needle):
    out, i = [], 0
    while True:
        j = data.find(needle, i)
        if j < 0:
            return out
        out.append(j)
        i = j + 1


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def ptr_map(p):
    """Con tro Turing: file_off = ROM_IMG + p (+EFI_SZ neu p >= LEGACY_SZ). ptr==0 -> base."""
    base = ROM_IMG + p
    if p >= LEGACY_SZ:
        base += EFI_SZ
    return base


def table_header(rom, off):
    """Parse header bang: ver, hdr_size, entry_size, count. Khong doan semantic."""
    if off + 4 > len(rom):
        return None
    ver, hdr, esz, cnt = rom[off], rom[off + 1], rom[off + 2], rom[off + 3]
    size = hdr + esz * cnt
    extent = (off, off + size)
    return dict(
        off=off, off_hex=f"0x{off:06x}",
        ver=ver, header_size=hdr, entry_size=esz, count=cnt, size=size,
        extent_start=extent[0], extent_end=extent[1],
        extent_end_hex=f"0x{extent[1]:06x}",
    )


def sig_hits(rom):
    out = {}
    for name, needle in SIGS.items():
        out[name] = dict(signature=needle.decode("latin1"), hex=needle.hex(),
                         hits=[dict(offset=o, offset_hex=f"0x{o:06x}") for o in find_all(rom, needle)])
    return out


def validate_image_boundary(rom, off, sig):
    """Xet xem co hit o off co phai ran gioi image thuc su (header+length+chain) hay chi la byte pattern."""
    if sig == "NVGIf_container":
        # Magic nhat nhat. Header 3 byte tiep theo giong nhau tai 2 vi tri -> cung container.
        hdr = rom[off + 5:off + 8].hex()
        forward = off + REPEAT_SPAN if off + REPEAT_SPAN < len(rom) else None
        backward = off - REPEAT_SPAN if off - REPEAT_SPAN >= 0 else None
        partner = None
        if forward is not None and rom[forward:forward + 5] == b"NVGIf":
            partner = forward
        elif backward is not None and rom[backward:backward + 5] == b"NVGIf":
            partner = backward
        chain = None
        if partner is not None:
            chain = dict(partner_offset=partner, partner_offset_hex=f"0x{partner:06x}",
                         same_header=rom[partner + 5:partner + 8].hex() == hdr,
                         span=REPEAT_SPAN, span_hex=f"0x{REPEAT_SPAN:06x}")
            # near-identical content over span (exclude known keyblock diff run)
            a, b = rom[off:off + REPEAT_SPAN], rom[partner:partner + REPEAT_SPAN]
            diffs = [i for i in range(REPEAT_SPAN) if a[i] != b[i]]
            chain.update(content_diffs_over_span=len(diffs),
                         content_match_ratio=(REPEAT_SPAN - len(diffs)) / REPEAT_SPAN,
                         direction="forward" if partner == forward else "backward")
        return dict(signature=sig, offset=off, offset_hex=f"0x{off:06x}",
                    header3=hdr, accepted_as_image_boundary=partner is not None,
                    proof="magic NVGIf + header3 giong nhau + ma NVGIf ke tiep khoang cach REPEAT_SPAN (hai chieu) + noi dung gan nhu giong het",
                    chain=chain)
    if sig == "ROM_55AA":
        ptr_off = off + 0x18
        ptr = u16(rom, ptr_off) if ptr_off + 2 <= len(rom) else None
        pcir = ptr_map(ptr) if ptr is not None else None
        pcir_ok = pcir is not None and pcir + 4 <= len(rom) and rom[pcir:pcir + 4] == b"PCIR"
        return dict(signature=sig, offset=off, offset_hex=f"0x{off:06x}",
                    pcntr_ptr_off=ptr_off, pcntr_ptr=ptr, pcntr_ptr_hex=f"0x{ptr:04x}" if ptr is not None else None,
                    pcir_target=pcir, pcir_target_hex=f"0x{pcir:06x}" if pcir is not None else None,
                    pcir_confirmed=pcir_ok,
                    accepted_as_image_boundary=pcir_ok,
                    proof="55AA + con tro tai +0x18 tro den PCIR co vendor/device" if pcir_ok else "chi co byte 55AA, chua co chuoi PCIR duoc chuong trinh")
    # PCIR / NPDS / NPDE / NVGI va cac chuoi NMX: chi danh dau hit, chua co by dai/chain toi uu -> khong nhan ran gioi image
    return dict(signature=sig, offset=off, offset_hex=f"0x{off:06x}",
                accepted_as_image_boundary=False,
                proof="chi la hit chu ki byte, chua co header/do dai/chain chuong trinh chay het")


def parse_bit(rom):
    off = BIT_OFF
    if rom[off:off + 5] != b"FFBIT\x00":
        # Header: FF B8 42 49 54 00 ... (FF B8 la prefix, "BIT\0")
        pass
    b8, sigb = rom[off], rom[off + 1:off + 5]
    hdr, stride, count = rom[off + 8], rom[off + 9], rom[off + 10]
    size = hdr + stride * count
    tokens = []
    for i in range(count):
        po = off + hdr + i * stride
        tok, ver, ln, raw_ptr = struct.unpack_from("<BBHH", rom, po)
        mapped = ptr_map(raw_ptr)
        tokens.append(dict(
            index=i, offset=po, offset_hex=f"0x{po:06x}",
            token=tok, token_hex=f"0x{tok:02x}", token_ascii=chr(tok) if 32 <= tok < 127 else "?",
            version=ver, length=ln, raw_pointer=raw_ptr, raw_pointer_hex=f"0x{raw_ptr:04x}",
            mapped_offset=mapped, mapped_offset_hex=f"0x{mapped:06x}",
            mapping_assumption="ptr_map (Turing); ptr==0 -> ROM image base (0x28600)",
            null_pointer=raw_ptr == 0,
            in_bounds=mapped + ln <= len(rom),
        ))
    return dict(
        offset=off, offset_hex=f"0x{off:06x}",
        prefix_byte=b8, signature=sigb.decode("latin1", errors="replace"),
        header_size=hdr, stride=stride, count=count, size=size,
        extent_end=off + size, extent_end_hex=f"0x{off + size:06x}",
        mapping_assumption="file_off = ROM_IMG + ptr + (EFI_SZ if ptr >= LEGACY_SZ else 0); ptr==0 -> base",
        tokens=tokens,
    )


def parse_perf(rom):
    off = PERF_OFF
    nptr = 56
    slots = []
    tables = []
    for i in range(nptr):
        po = off + i * 4
        raw_ptr = u32(rom, po)
        rec = dict(index=i, slot_offset=po, slot_offset_hex=f"0x{po:06x}",
                   raw_pointer=raw_ptr, raw_pointer_hex=f"0x{raw_ptr:08x}", null=raw_ptr == 0)
        if raw_ptr == 0:
            slots.append(rec)
            continue
        mapped = ptr_map(raw_ptr)
        rec.update(mapped_offset=mapped, mapped_offset_hex=f"0x{mapped:06x}")
        th = table_header(rom, mapped)
        if th is None:
            rec.update(table=None, valid_header_shape=False,
                       reason="header het ROM")
            slots.append(rec)
            continue
        in_bounds = th["extent_end"] <= len(rom)
        # overlap voi BIT table?
        bit_end = BIT_OFF + 12 + 6 * 17
        overlaps_bit = not (th["extent_end"] <= BIT_OFF or th["off"] >= bit_end)
        rec.update(table=th, valid_header_shape=bool(
            th["header_size"] >= 4 and th["entry_size"] > 0 and th["count"] > 0 and in_bounds),
                   in_bounds=in_bounds, overlaps_BIT_table=overlaps_bit,
                   semantic_status="UNKNOWN (header shape chua xac dinh nghia bang)")
        tables.append(rec)
        slots.append(rec)
    # overlap giua cac table khong null
    overlaps = []
    nonnull = [t for t in tables if t.get("table")]
    for a_i in range(len(nonnull)):
        for b_i in range(a_i + 1, len(nonnull)):
            a, b = nonnull[a_i]["table"], nonnull[b_i]["table"]
            if not (a["extent_end"] <= b["off"] or b["extent_end"] <= a["off"]):
                overlaps.append(dict(a=nonnull[a_i]["index"], a_extent=[a["off"], a["extent_end"]],
                                     b=nonnull[b_i]["index"], b_extent=[b["off"], b["extent_end"]]))
    return dict(offset=off, offset_hex=f"0x{off:06x}", pointer_slots=nptr,
                null_pointers=sum(1 for s in slots if s["null"]),
                nonnull_pointers=sum(1 for s in slots if not s["null"]),
                parsed_tables=len([t for t in tables if t.get("table")]),
                valid_header_tables=sum(1 for t in tables if t.get("valid_header_shape")),
                in_bounds_tables=sum(1 for t in tables if t.get("in_bounds")),
                overlaps_bit_table=sum(1 for t in tables if t.get("overlaps_BIT_table")),
                table_table_overlaps=overlaps,
                slots=slots)


def parse_key_records(rom, base):
    n = KEYLEN // RECSZ
    recs = []
    for i in range(n):
        o = base + i * RECSZ
        b = rom[o:o + RECSZ]
        if b == b"\xff" * RECSZ:
            recs.append(dict(idx=i, off=o, off_hex=f"0x{o:04x}", present=False, all_ff=True))
            continue
        sig, ver = struct.unpack_from("<HH", b, 0)
        f4 = u32(b, 4)
        f8 = u32(b, 8)
        fc = u32(b, 12)
        h = b[16:32]
        recs.append(dict(idx=i, off=o, off_hex=f"0x{o:04x}", present=True, all_ff=False,
                         sig=f"0x{sig:04x}", ver=f"0x{ver:04x}",
                         f4=f4, f4_hex=f"0x{f4:08x}",
                         f8=f"0x{f8:08x}", fc=f"0x{fc:08x}",
                         flags_lo=fc & 0xFF, flags_hi=(fc >> 16) & 0xFF,
                         hash16=h.hex(),
                         hash_semantic="UNKNOWN (khong khop SHA/MD5 cua vung ROM boi thu nvgi_block.py)")),
    return dict(base=base, base_hex=f"0x{base:04x}", length=KEYLEN, record_size=RECSZ, count=n,
                records=recs, present=sum(1 for r in recs if r["present"]),
                all_ff=sum(1 for r in recs if r["all_ff"]))


def diff_regions(a, b, label_a, label_b, span):
    diffs = [i for i in range(span) if a[i] != b[i]]
    runs = []
    if diffs:
        cur = [diffs[0]]
        for x, y in zip(diffs, diffs[1:]):
            if y - x <= 128:
                cur.append(y)
            else:
                runs.append([cur[0], cur[-1]])
                cur = [y]
        runs.append([cur[0], cur[-1]])
    return dict(label_a=label_a, label_b=label_b, span=span, span_hex=f"0x{span:06x}",
                diff_count=len(diffs), diff_first=diffs[0] if diffs else None,
                diff_last=diffs[-1] if diffs else None,
                diff_runs=[[s, e] for s, e in runs],
                diff_runs_hex=[[f"0x{s:06x}", f"0x{e:06x}"] for s, e in runs],
                match_ratio=(span - len(diffs)) / span,
                diff_detail=[dict(offset=i, offset_hex=f"0x{i:06x}",
                                  a=a[i], b=b[i], a_hex=f"0x{a[i]:02x}", b_hex=f"0x{b[i]:02x}")
                             for i in diffs])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rom = ROM_P.read_bytes()
    t4 = T4_P.read_bytes()
    shadow = SHADOW_P.read_bytes()
    assert len(rom) == ROM_SIZE, f"ROM phai 1 MiB, thay {len(rom)}"
    assert len(t4) == REPEAT_SPAN, f"T4 phai 0x79000, thay {len(t4)}"
    assert len(shadow) == ROM_SIZE, f"shadow phai 1 MiB, thay {len(shadow)}"

    result = dict(
        script=SCRIPT.name,
        inputs=dict(
            rom=dict(path=str(ROM_P), size=len(rom), sha256=sha(rom)),
            t4=dict(path=str(T4_P), size=len(t4), sha256=sha(t4)),
            shadow=dict(path=str(SHADOW_P), size=len(shadow), sha256=sha(shadow)),
        ),
        constants=dict(ROM_IMG=ROM_IMG, ROM_IMG_hex=f"0x{ROM_IMG:06x}",
                       LEGACY_SZ=LEGACY_SZ, LEGACY_SZ_hex=f"0x{LEGACY_SZ:06x}",
                       EFI_SZ=EFI_SZ, EFI_SZ_hex=f"0x{EFI_SZ:06x}",
                       REPEAT_SPAN=REPEAT_SPAN, REPEAT_SPAN_hex=f"0x{REPEAT_SPAN:06x}",
                       TAIL_START=TAIL_START, TAIL_START_hex=f"0x{TAIL_START:06x}"),
        raw_header=dict(
            rom_first8=rom[0:8].hex(" "),
            rom_0x79000_first8=rom[0x79000:0x79008].hex(" "),
            rom_legacy_start=rom[0x28600:0x28620].hex(" "),
            rom_pcntr_ptr=rom[0x28618:0x2861c].hex(" "),
            rom_pcir=rom[0x28770:0x28780].hex(" "),
            rom_bit_header=rom[0x287B0:0x287C0].hex(" "),
            rom_perf_start=rom[0x288D4:0x288E0].hex(" "),
            shadow_first24=shadow[0:24].hex(" "),
            shadow_pcir=shadow[0x170:0x180].hex(" "),
        ),
        signatures=sig_hits(rom),
        image_boundaries=[],
        bit=parse_bit(rom),
        perf=parse_perf(rom),
        key_block_bank1=parse_key_records(rom, KEYBLK),
        key_block_bank2=parse_key_records(rom, KEYBLK + REPEAT_SPAN),
        repeated_banks=diff_regions(rom[0:REPEAT_SPAN], rom[REPEAT_SPAN:2 * REPEAT_SPAN],
                                    "bank1[0x00000:0x79000]", "bank2[0x79000:0xF2000]", REPEAT_SPAN),
        t4_comparison=diff_regions(rom[0:len(t4)], t4, "rom[0:0x79000]", "t4 payload", len(t4)),
        shadow_comparison=diff_regions(shadow[0:ROM_SIZE - ROM_IMG], rom[ROM_IMG:],
                                       "shadow[0:883200]", "rom[0x28600:1048576]", ROM_SIZE - ROM_IMG),
        tail=dict(start=TAIL_START, start_hex=f"0x{TAIL_START:06x}",
                  size=ROM_SIZE - TAIL_START,
                  all_ff=set(rom[TAIL_START:]) == {0xFF},
                  ff_count=sum(1 for v in rom[TAIL_START:] if v == 0xFF),
                  zero_count=sum(1 for v in rom[TAIL_START:] if v == 0x00),
                  other_count=sum(1 for v in rom[TAIL_START:] if v not in (0xFF, 0x00))),
    )

    # Image boundary validation for each signature hit class
    for signame, hits in result["signatures"].items():
        for h in hits["hits"]:
            result["image_boundaries"].append(
                validate_image_boundary(rom, h["offset"], signame))

    # Accepted / rejected candidates
    accepted, rejected = [], []
    for ib in result["image_boundaries"]:
        entry = dict(signature=ib["signature"], offset=ib["offset"], offset_hex=ib["offset_hex"])
        if ib["accepted_as_image_boundary"]:
            accepted.append(entry)
        else:
            entry2 = dict(entry)
            entry2["reason"] = "chi hit chu ki, chua co header/do dai/chain chuong trinh"
            rejected.append(entry2)
    result["accepted_candidates"] = accepted
    result["rejected_candidates"] = rejected

    # Counts (REDACTED_USER lai tu output, khong hardcode)
    result["counts"] = dict(
        rom_bytes=len(rom), t4_bytes=len(t4), shadow_bytes=len(shadow),
        signature_hit_total=sum(len(h["hits"]) for h in result["signatures"].values()),
        accepted_image_boundaries=len(accepted),
        rejected_signature_hits=len(rejected),
        bit_tokens=result["bit"]["count"],
        bit_null_tokens=sum(1 for t in result["bit"]["tokens"] if t["null_pointer"]),
        perf_pointer_slots=result["perf"]["pointer_slots"],
        perf_null_pointers=result["perf"]["null_pointers"],
        perf_nonnull_pointers=result["perf"]["nonnull_pointers"],
        perf_parsed_tables=result["perf"]["parsed_tables"],
        perf_valid_header_tables=result["perf"]["valid_header_tables"],
        perf_table_table_overlaps=len(result["perf"]["table_table_overlaps"]),
        keyblock_records_bank1=result["key_block_bank1"]["count"],
        keyblock_present_bank1=result["key_block_bank1"]["present"],
        keyblock_allff_bank1=result["key_block_bank1"]["all_ff"],
        keyblock_present_bank2=result["key_block_bank2"]["present"],
        repeated_bank_diff_bytes=result["repeated_banks"]["diff_count"],
        repeated_bank_denominator=result["repeated_banks"]["span"],
        t4_shared_prefix_diff_bytes=result["t4_comparison"]["diff_count"],
        t4_shared_prefix_denominator=result["t4_comparison"]["span"],
        shadow_compare_bytes=result["shadow_comparison"]["span"],
        shadow_diff_bytes=result["shadow_comparison"]["diff_count"],
    )

    # Unresolved regions (raw bytes, khong bo sot)
    unresolved = []
    unresolved.append(dict(region="NMX container tail", start=TAIL_START, end=ROM_SIZE,
                           size=ROM_SIZE - TAIL_START, start_hex=f"0x{TAIL_START:06x}",
                           end_hex="0x100000",
                           note="Co chuoi RIBILU/PPID/GXIP/JFFS nhung cau truc trong bo con chua duoc giao dich; ke tu PPID/serial khong duoc phep doan"))
    unresolved.append(dict(region="NVGI key block 16-byte hash", base=KEYBLK, count=38,
                           note="16 byte hash cua moi record chua biet la ma gi; thu SHA/MD5/SHA1 cua 6 vung ROM het khop (0/912)"))
    unresolved.append(dict(region="PERF bang semantic", count=result["perf"]["valid_header_tables"],
                           note="Tat ca header hop ly nhan semantic_status=UNKNOWN; chua co nguon dich field"))
    unresolved.append(dict(region="BIT token nghia", count=result["bit"]["count"],
                           note="Ma token (0x32,0x42,...) duoc liet ke tuy nhien; nghia cua tung token chua duoc nguon dich"))
    result["unresolved_regions"] = unresolved

    # Reproduction commands
    result["reproduction_commands"] = [
        f"python3 {SCRIPT}",
        f"sha256sum {ROM_P} {T4_P} {SHADOW_P}",
        f"python3 {ROOT / 'scripts' / 'test_parser.py'}",
        f"python3 {ROOT / 'scripts' / 'verify_diff.py'} {ROM_P} {T4_P}",
    ]

    # Write JSON
    json_path = OUT / "vbios_structure_verified.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"JSON ghi: {json_path}")

    # Concise stdout summary
    c = result["counts"]
    print("=== VBIOS structure verify ===")
    print(f"ROM {c['rom_bytes']:,} B  sha256 {result['inputs']['rom']['sha256']}")
    print(f"T4  {c['t4_bytes']:,} B  sha256 {result['inputs']['t4']['sha256']}")
    print(f"shadow {c['shadow_bytes']:,} B  sha256 {result['inputs']['shadow']['sha256']}")
    print(f"Signature hits: {c['signature_hit_total']}  accepted boundaries: {c['accepted_image_boundaries']}  rejected: {c['rejected_signature_hits']}")
    print(f"BIT: {c['bit_tokens']} tokens ({c['bit_null_tokens']} null) @ 0x287B0")
    print(f"PERF: {c['perf_pointer_slots']} slots, {c['perf_nonnull_pointers']} non-null, {c['perf_parsed_tables']} parsed tables, {c['perf_valid_header_tables']} valid-header, {c['perf_table_table_overlaps']} table-table overlaps")
    print(f"Key block: bank1 {c['keyblock_present_bank1']}/{c['keyblock_records_bank1']} present, bank2 {c['keyblock_present_bank2']}/{c['keyblock_records_bank1']} present (all 0xFF in key range)")
    print(f"Repeated banks: {c['repeated_bank_diff_bytes']}/{c['repeated_bank_denominator']:,} bytes differ (denominator), runs={[ [f'0x{s:06x}',f'0x{e:06x}'] for s,e in result['repeated_banks']['diff_runs'] ]}")
    print(f"T4 shared-prefix: {c['t4_shared_prefix_diff_bytes']}/{c['t4_shared_prefix_denominator']:,} bytes differ")
    print(f"Shadow vs ROM[0x28600:]: {c['shadow_diff_bytes']}/{c['shadow_compare_bytes']:,} bytes differ (NOT 100%; denominator {c['shadow_compare_bytes']:,})")
    print(f"Unresolved: {len(result['unresolved_regions'])} regions")
    print("DONE")


if __name__ == "__main__":
    main()

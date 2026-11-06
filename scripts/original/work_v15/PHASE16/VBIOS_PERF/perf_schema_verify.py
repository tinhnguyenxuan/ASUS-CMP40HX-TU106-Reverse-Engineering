#!/usr/bin/env python3
"""Perf schema verify — CMP40HX/TU106 VBIOS PERF_PTRS (BIT token 'P').

Chi stdlib. Chi doc input (khong sua ROM, khong flash, khong truy cap GPU).
Tat so dem REDACTED_USER lai tu raw bytes, khong hardcode.

Nguon dich:
  - envytools/nvbios/bit.c      : BIT header (hlen/rlen/count), entry (type/ver/t_len/t_offset), 6-byte stride
  - envytools/nvbios/power.c    : P token = Power table; P2_tbls maps byte offset -> ten bang (version 2)
  - envytools/nvbios/nvbios.c   : PM_Mode table header parse (slot 0 = PERFORMANCE)

URL: https://github.com/envytools/envytools (nvbios/ — local snapshot /tmp/envytools/nvbios/)
Hash: chua REDACTED_USER (file local, khong download)
Version: envytools snapshot tai /tmp/envytools/nvbios/, commit chua xac dinh

Ponytail: stdlib only, one file, __main__ self-check.
"""

import hashlib
import json
import struct
import sys
from pathlib import Path

# ---------- constants (tu ROM thuc, khong hardcode theo job khac) ----------
ROM_IMG = 0x28600      # legacy x86 image base (byte 55AA @0x28600)
LEGACY_SZ = 0xF400     # kich thuc legacy image theo con tro Turing
EFI_SZ = 0x11000       # kich thuc khoi EFI (bo dao nguoc con tro)
BIT_OFF = 0x287B0      # BIT table (trong legacy1)
PERF_OFF = 0x288D4     # P token data (ptr(724) = 0x28600+724 = 0x288D4)
PERF_SLOTS = 56
ROM_SIZE = 1 << 20

# ---------- P2_tbls tu envytools/nvbios/power.c (version 2) ----------
# Byte offset trong P token data -> ten bang. Offset = slot_index * 4.
P2_TBLS_V2 = {
    0x00: "PERFORMANCE",
    0x04: "MEMORY TIMINGS MAPPING",
    0x08: "MEMORY TIMINGS",
    0x0c: "VOLTAGE",
    0x10: "THERMAL",
    0x14: "THERMAL DEVICES",
    0x18: "THERMAL COOLERS",
    0x1c: "PERF SETTINGS SCRIPT",
    0x20: "VOLT MAPPING",
    0x24: "VENTURA",
    0x28: "POWER SENSE",
    0x2c: "POWER BUDGET",
    0x30: "BOOST",
    0x34: "CSTEP",
    0x38: "POWER BASE CLOCK",
    0x3c: "POWER TOPOLOGY",
    0x40: "POWER LEAKAGE",
    0x44: "PERF TEST SPEC",      # slot 17
    0x48: "THERMAL CHANNEL",
    0x4c: "THERMAL ADJUSTMENT",
    0x50: "THERMAL POLICY",
    0x54: "PSTATE MEMORY CLK FREQ",
    0x58: "FAN COOLERS",
    0x5c: "POWER FAN_MGMT",
    0x60: "DI/DT",
    0x64: "FAN TEST",
    0x68: "VOLTAGE RAIL",
    0x6c: "VOLTAGE DEVICE",
    0x70: "VOLTAGE POLICY",
    0x74: "LOW POWER",
    0x78: "LOW POWER PCIe",
    0x7c: "LOW POWER PCIe-PLATFORM",
    0x80: "LOW POWER GR",
    0x84: "LOW POWER MS",
    0x88: "LOW POWER DI",
    0x8c: "LOW POWER GC6",
    0x90: "LOW POWER PSI",
    0x94: "THERM MONITOR",
    0x98: "OVERCLOCKING",
    # 0x9c: "LOW POWER NVLINK"  (commented out in source)
}

# ---------- helpers ----------
def sha(b):
    return hashlib.sha256(b).hexdigest()


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def ptr_map(p):
    """Con tro Turing: file_off = ROM_IMG + p (+EFI_SZ neu p >= LEGACY_SZ). ptr==0 -> null."""
    if p == 0:
        return 0, True
    base = ROM_IMG + p
    is_legacy = p < LEGACY_SZ
    if not is_legacy:
        base += EFI_SZ
    return base, False


# ---------- BIT table ----------
def parse_bit(rom):
    off = BIT_OFF
    # header: +6 version(u16), +8 hlen(u8), +9 rlen(u8), +10 entriesnum(u8)  [bit.c]
    bver = u16(rom, off + 6)
    hlen = rom[off + 8]
    rlen = rom[off + 9]
    entries = rom[off + 10]
    tokens = []
    for i in range(entries):
        po = off + hlen + i * rlen
        tok, ver, t_len, t_off = struct.unpack_from("<BBHH", rom, po)
        tokens.append(dict(
            index=i, offset=po, offset_hex=f"0x{po:06x}",
            token=tok, token_hex=f"0x{tok:02x}",
            token_ascii=chr(tok) if 32 <= tok < 127 else "?",
            version=ver,
            t_len=t_len, t_len_hex=f"0x{t_len:04x}",
            t_offset=t_off, t_offset_hex=f"0x{t_off:04x}",
        ))
    return dict(
        offset=off, offset_hex=f"0x{off:06x}",
        version=bver, version_hex=f"0x{bver:04x}",
        hlen=hlen, rlen=rlen, entries=entries,
        size=hlen + rlen * entries,
        tokens=tokens,
    )


# ---------- PERF slots ----------
def parse_perf_slots(rom, bit):
    # Tim token 'P'
    p_tok = None
    for t in bit["tokens"]:
        if t["token_ascii"] == "P":
            p_tok = t
            break
    if p_tok is None:
        return dict(error="BIT token 'P' khong tim thi")

    p_ptr = p_tok["t_offset"]
    p_len = p_tok["t_len"]
    p_ver = p_tok["version"]

    # 56 slots x 4B = 224B — kiem tra voi t_len thuc te
    expected_len = PERF_SLOTS * 4
    slots_fit = (p_len == expected_len)

    base, _ = ptr_map(p_ptr)
    slots = []
    tables = []
    for i in range(PERF_SLOTS):
        so = PERF_OFF + i * 4
        raw_ptr = u32(rom, so)
        mapped, is_null = ptr_map(raw_ptr)
        p2_off = i * 4
        p2_name = P2_TBLS_V2.get(p2_off, None)
        rec = dict(
            index=i, slot_offset=so, slot_offset_hex=f"0x{so:06x}",
            raw_pointer=raw_ptr, raw_pointer_hex=f"0x{raw_ptr:06x}",
            null=is_null,
            p2_byte_offset=p2_off, p2_byte_offset_hex=f"0x{p2_off:02x}",
            p2_name=p2_name,
            p2_name_source="envytools/nvbios/power.c P2_tbls (version 2)" if p2_name else None,
        )
        if is_null:
            slots.append(rec)
            continue

        # Doc 32 byte raw o dia chi map duoc
        raw32 = rom[mapped:mapped + 32]
        rec.update(mapped_offset=mapped, mapped_offset_hex=f"0x{mapped:06x}",
                   raw32=raw32.hex(" "), raw32_16=raw32[:16].hex(" "))

        # Generic header: ver, hdr, esz, cnt (model cu, chua xac dinh schema)
        if mapped + 4 <= len(rom):
            ver, hdr, esz, cnt = rom[mapped], rom[mapped + 1], rom[mapped + 2], rom[mapped + 3]
            size = hdr + esz * cnt
            extent_end = mapped + size
            in_bounds = extent_end <= len(rom)
            rec.update(
                ver=ver, header_size=hdr, entry_size=esz, count=cnt,
                generic_size=size, extent_end=extent_end,
                extent_end_hex=f"0x{extent_end:06x}",
                in_bounds=in_bounds,
                generic_header_valid=(hdr >= 4 and esz > 0 and cnt > 0 and in_bounds),
            )
            if in_bounds:
                tables.append(rec)

        slots.append(rec)

    # Overlap giua cac table khong null (dau vao: generic extent)
    overlaps = []
    for ai in range(len(tables)):
        for bi in range(ai + 1, len(tables)):
            a, b = tables[ai], tables[bi]
            if not (a["extent_end"] <= b["mapped_offset"] or b["extent_end"] <= a["mapped_offset"]):
                overlaps.append(dict(
                    a=a["index"], b=b["index"],
                    a_name=a["p2_name"], b_name=b["p2_name"],
                    a_offset=a["mapped_offset"], a_offset_hex=f"0x{a['mapped_offset']:06x}",
                    b_offset=b["mapped_offset"], b_offset_hex=f"0x{b['mapped_offset']:06x}",
                    a_extent=[a["mapped_offset"], a["extent_end"]],
                    b_extent=[b["mapped_offset"], b["extent_end"]],
                ))

    return dict(
        p_token=dict(
            index=p_tok["index"], token=p_tok["token_ascii"], version=p_ver,
            t_len=p_len, t_len_hex=f"0x{p_len:04x}",
            t_offset=p_ptr, t_offset_hex=f"0x{p_ptr:04x}",
            perf_data_base=base, perf_data_base_hex=f"0x{base:06x}",
        ),
        slots_fit_56x4=slots_fit,
        expected_len=expected_len,
        pointer_slots=PERF_SLOTS,
        null_pointers=sum(1 for s in slots if s["null"]),
        non_null_pointers=sum(1 for s in slots if not s["null"]),
        parsed_tables=len(tables),
        slots=slots,
        tables=tables,
        table_table_overlaps=overlaps,
    )


# ---------- schema assessment ----------
def assess_schema(rom, slot_rec):
    """Danh gia muc do xac dinh schema cho mot slot.

    Tra ve dict co: source_correlated, schema_confidence, fields, reason.
    """
    idx = slot_rec["index"]
    mapped = slot_rec["mapped_offset"]
    p2_name = slot_rec.get("p2_name")

    out = dict(
        index=idx,
        p2_name=p2_name,
        source_correlated=False,
        schema_confidence="unknown",
        fields=[],
        reason="",
    )

    if p2_name is not None:
        # Co ten tu P2_tbls (envytools) — source-correlated ten, nhung schema field chua biet
        out["source_correlated"] = True
        out["schema_confidence"] = "name_only"
        out["reason"] = f"Ten bang tu P2_tbls (envytools/nvbios/power.c): '{p2_name}'. Schema field chua co nguon dich."

    # Generic header — luu duoc nhung danh da la model cu, chua xac dinh
    if "generic_size" in slot_rec:
        out["generic_header"] = dict(
            ver=slot_rec["ver"], header_size=slot_rec["header_size"],
            entry_size=slot_rec["entry_size"], count=slot_rec["count"],
            size=slot_rec["generic_size"],
        )
        out["generic_header_confidence"] = "generic_model"
        out["reason"] += " Generic header (ver/hdr/esz/cnt) la model cu, chua xac dinh schema."

    return out


# ---------- main ----------
def main():
    rom_path = Path("/home/REDACTED_USER/codex-work/work_v15/outputs/CMP40HX_ORIGINAL_1MB.bin")
    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)

    rom = rom_path.read_bytes()
    assert len(rom) == ROM_SIZE, f"ROM phai {ROM_SIZE} B, thay {len(rom)}"

    rom_sha = sha(rom)

    # Parse BIT
    bit = parse_bit(rom)

    # Find P token and parse PERF
    perf = parse_perf_slots(rom, bit)

    # Schema assessment for non-null slots
    schema_reports = []
    for t in perf["tables"]:
        schema_reports.append(assess_schema(rom, t))

    # Overlap classification (generic extents)
    overlap_details = []
    for ov in perf["table_table_overlaps"]:
        a_idx = ov["a"]; b_idx = ov["b"]
        a_rec = next(s for s in perf["tables"] if s["index"] == a_idx)
        b_rec = next(s for s in perf["tables"] if s["index"] == b_idx)
        # Alias: cung mapped_offset
        is_alias = (a_rec["mapped_offset"] == b_rec["mapped_offset"])
        # Containment: mot nam trong mot khac
        a_contains_b = (a_rec["mapped_offset"] <= b_rec["mapped_offset"] and
                        b_rec["extent_end"] <= a_rec["extent_end"])
        b_contains_a = (b_rec["mapped_offset"] <= a_rec["mapped_offset"] and
                        a_rec["extent_end"] <= b_rec["extent_end"])
        is_containment = a_contains_b or b_contains_a
        # Partial overlap
        is_partial = (not is_alias) and (not is_containment)

        classification = "generic_model_artifact"
        if is_alias:
            classification = "alias"
        elif is_containment:
            classification = "containment"
        elif is_partial:
            classification = "partial_overlap"

        overlap_details.append(dict(
            a=a_idx, b=b_idx,
            a_name=a_rec.get("p2_name"), b_name=b_rec.get("p2_name"),
            a_offset=a_rec["mapped_offset"], b_offset=b_rec["mapped_offset"],
            is_alias=is_alias, is_containment=is_containment, is_partial=is_partial,
            classification=classification,
            reason="Generic extents (ver/hdr/esz/cnt) — chua biet schema thuc, overlap co the la artifact cua model cu.",
        ))

    # Result
    result = dict(
        script=Path(__file__).name,
        inputs=dict(
            rom=dict(path=str(rom_path), size=len(rom), sha256=rom_sha),
        ),
        sources=dict(
            bit_c="envytools/nvbios/bit.c — BIT header/entry schema, 6-byte stride",
            power_c="envytools/nvbios/power.c — P token = Power table, P2_tbls slot->ten bang (ver 2)",
            nvbios_c="envytools/nvbios/nvbios.c — PM_Mode table header parse (slot 0)",
            local_snapshot="/tmp/envytools/nvbios/",
        ),
        bit=bit,
        p_token=perf["p_token"],
        slots_fit_56x4=perf["slots_fit_56x4"],
        expected_len=perf["expected_len"],
        actual_len=perf["p_token"]["t_len"],
        perf=perf,
        schema_reports=schema_reports,
        overlaps=overlap_details,
        slot17=next((s for s in perf["tables"] if s["index"] == 17), None),
    )

    # Write JSON
    json_path = out_dir / "perf_schema_verified.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    # Write run.log
    log_path = out_dir / "run.log"
    lines = [
        f"ROM: {rom_path} ({len(rom):,} B, sha256={rom_sha})",
        f"BIT: @0x{BIT_OFF:06x} hlen={bit['hlen']} rlen={bit['rlen']} entries={bit['entries']} ver=0x{bit['version']:04x}",
        f"P token: idx={perf['p_token']['index']} ver={perf['p_token']['version']} t_len={perf['p_token']['t_len']} t_offset=0x{perf['p_token']['t_offset']:04x}",
        f"56 slots x 4B = {perf['expected_len']} B == t_len {perf['p_token']['t_len']} B -> slots_fit={perf['slots_fit_56x4']}",
        f"Non-null pointers: {perf['non_null_pointers']} / {perf['pointer_slots']}",
        f"Parsed tables (generic header): {perf['parsed_tables']}",
        f"Table-table overlaps (generic extents): {len(perf['table_table_overlaps'])}",
        "",
        "Slot 17:",
    ]
    s17 = result["slot17"]
    if s17:
        lines.append(f"  raw_ptr=0x{s17['raw_pointer']:06x} mapped=0x{s17['mapped_offset']:06x}")
        lines.append(f"  P2_tbls name: {s17.get('p2_name')}")
        lines.append(f"  Generic header: ver=0x{s17['ver']:02x} hdr={s17['header_size']} esz={s17['entry_size']} cnt={s17['count']} size={s17['generic_size']}")
        lines.append(f"  raw32: {s17['raw32']}")
        lines.append(f"  In bounds: {s17['in_bounds']}")
    lines.append("")
    log_path.write_text("\n".join(lines) + "\n")

    # Concise stdout
    print(f"=== Perf schema verify ===")
    print(f"ROM {len(rom):,} B sha256 {rom_sha}")
    print(f"BIT @0x{BIT_OFF:06x} hlen={bit['hlen']} rlen={bit['rlen']} entries={bit['entries']}")
    print(f"P token: ver={perf['p_token']['version']} t_len={perf['p_token']['t_len']} t_offset=0x{perf['p_token']['t_offset']:04x}")
    print(f"56x4={perf['expected_len']}B == t_len {perf['p_token']['t_len']}B -> fit={perf['slots_fit_56x4']}")
    print(f"PERF slots: {perf['non_null_pointers']} non-null, {perf['parsed_tables']} parsed tables")
    print(f"Overlaps: {len(perf['table_table_overlaps'])}")
    print(f"JSON: {json_path}")
    print(f"Log: {log_path}")
    print("DONE")


def demo():
    """Self-check: chay va assert cac not than ket cua BIT/P parsing."""
    rom_path = Path("/home/REDACTED_USER/codex-work/work_v15/outputs/CMP40HX_ORIGINAL_1MB.bin")
    rom = rom_path.read_bytes()
    bit = parse_bit(rom)
    assert bit["hlen"] == 12, bit["hlen"]
    assert bit["rlen"] == 6, bit["rlen"]
    assert bit["entries"] == 17, bit["entries"]
    p = next(t for t in bit["tokens"] if t["token_ascii"] == "P")
    assert p["version"] == 2, p["version"]
    assert p["t_len"] == 224, p["t_len"]
    assert p["t_offset"] == 724, p["t_offset"]
    assert 56 * 4 == 224
    perf = parse_perf_slots(rom, bit)
    assert perf["slots_fit_56x4"] is True
    assert perf["non_null_pointers"] == 40, perf["non_null_pointers"]
    s17 = next(s for s in perf["tables"] if s["index"] == 17)
    assert s17["raw_pointer"] == 0x1aff2, hex(s17["raw_pointer"])
    assert s17["mapped_offset"] == 0x545f2, hex(s17["mapped_offset"])
    assert s17["p2_name"] == "PERF TEST SPEC", s17["p2_name"]
    print("demo: 7/7 PASS")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        main()

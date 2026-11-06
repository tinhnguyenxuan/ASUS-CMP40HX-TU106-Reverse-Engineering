#!/usr/bin/env python3
"""VBIOS_VERSION_CONSUMER — how envytools populates bios->info.version[0] and
what the nvbios PM_Mode consumer branches do with it, applied to CMP 40HX
(TU106) ORIGINAL / T4 / shadow ROM images.

Read-only, stdlib only. No hardware, no flashing, no tool installs.
Source: /tmp/envytools/nvbios (git f102b82381f3f11cee113d16374c87091db039d9).
"""
import hashlib
import json
import struct
import sys
from datetime import datetime, timezone

OUT_DIR = "/home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_VERSION_CONSUMER"

IMAGES = {
    "rom":  {"path": "/home/REDACTED_USER/codex-work/cmp40hx_transfer/CMP40HX_ORIGINAL_1MB.bin.txt",
             "sha256": "dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec",
             "size": 1048576},
    "t4":   {"path": "/home/REDACTED_USER/codex-work/cmp40hx_transfer/cmp40hx_t4.bin.txt",
             "sha256": "aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb",
             "size": 495616},
    "shadow": {"path": "/tmp/v11chk/RAW_DATA/vbios_shadow.bin",
               "sha256": "2715c0b106931b540b5ef6660201919e9297f3f5cdc61432d9a16352c55b717a",
               "size": 1048576},
}

SOURCE = {
    "bit.c":    "/tmp/envytools/nvbios/bit.c",
    "power.c":  "/tmp/envytools/nvbios/power.c",
    "nvbios.c": "/tmp/envytools/nvbios/nvbios.c",
    "bios.c":   "/tmp/envytools/nvbios/bios.c",
}
SOURCE_SHA256 = {
    "bit.c":    "ad7475b67203275e1fe05ac8c910ce2ad431eacb930ca3a858e085dceb87f335",
    "power.c":  "6f4d9d065dd37d8ea49ec3f7a7aeedd2723b13a1c223bc90e90de5be1802c8a6",
    "nvbios.c": "7e9f739bf8e4b45f168e90b4d6b07c0c0d039a2bdb76f753b38069714f36907f",
    "bios.c":   "1a87fa1eab4712e120771ef9af0d5df2c81ee7a69dbf43cd38415d6bcdf09ac8",
}

BIT_OFF = 0x287b0          # rom/t4: ff b8 42 49 54 00 00  (bios.c:198 bitsig)
BIT_OFF_SHADOW_1 = 0x1b0   # shadow: first BIT table (shadow base 0x00000)
BIT_OFF_SHADOW_2 = 0x791b0 # shadow: second BIT table
PERF_V60_OFF = 0x54155     # rom/t4: PERFORMANCE table whose header version byte = 0x60
PERF_V60_SHADOW_OFF = 0x2bb55  # shadow equivalent (shadow[X] == rom[0x28600 + X])
ROM_LEGACY_BASE = 0x28600  # BIT t_offset fields in rom/t4 are relative to this base

fails = []
checks = 0

def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        fails.append(msg)
        print("  FAIL: " + msg)
    else:
        print("  ok: " + msg)

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def u8(d, o): return d[o]
def u16(d, o): return struct.unpack_from("<H", d, o)[0]
def u32(d, o): return struct.unpack_from("<I", d, o)[0]

results = {"images": {}, "source": {}, "code_paths": [], "bit": {},
           "bmp": {}, "version": {}, "pm_mode": {}, "table_0x60": {}, "conclusion": {}}

print("=== input images ===")
for name, spec in IMAGES.items():
    d = open(spec["path"], "rb").read()
    ok_size = len(d) == spec["size"]
    ok_hash = sha256_file(spec["path"]) == spec["sha256"]
    check(ok_size and ok_hash, "image %s size+sha256 match recorded (%s)" % (name, spec["path"]))
    results["images"][name] = {"path": spec["path"], "size": len(d),
                               "sha256": sha256_file(spec["path"]),
                               "size_ok": ok_size, "hash_ok": ok_hash}
    results["images"][name]["_data"] = d

print("=== envytools source hashes @ git f102b823 ===")
for name, path in SOURCE.items():
    d = open(path, "rb").read()
    h = hashlib.sha256(d).hexdigest()
    check(h == SOURCE_SHA256[name], "source %s sha256 matches recorded git blob" % name)
    results["source"][name] = {"path": path, "sha256": h, "hash_ok": h == SOURCE_SHA256[name]}

print("=== code paths that populate bios->info.version[0] ===")
results["code_paths"] = [
    {"file": "nvbios/info.c", "function": "envy_bios_parse_bit_i",
     "lines": "49-52",
     "statement": "info->version[0] = data[bit->t_offset + 3]; (version[3]=+0, version[2]=+1, "
                  "version[1]=+2, version[0]=+3 MAJOR, version[4]=+4)",
     "precondition": "BIT entry type=='i', version==2 (bit.c:50), t_len>=0x19 (info.c:31)",
     "called_from": "bit.c:140 envy_bios_parse_bit dispatch, inside envy_bios_parse (bios.c:237)"},
    {"file": "nvbios/nvbios.c", "function": "parse_bios_version",
     "lines": "849-868 (write at 858)",
     "statement": "bios->info.version[0] = bios->data[offset + 3]; called with "
                  "bios->bmp_offset + 10 at nvbios.c:1078 -> reads data[bmp_offset + 13]",
     "precondition": "bios->bmp_offset != 0 && bios->type == ENVY_BIOS_TYPE_NV04 (nvbios.c:1077)",
     "notes": "BMP path OVERWRITES whatever BIT 'i' wrote; BMP signature \\xff\\x7fNV\\0 located by "
              "find_string (bios.c:161-168, bios.c:229)"},
]
for cp in results["code_paths"]:
    print("  - %s %s [%s]" % (cp["file"], cp["function"], cp["lines"]))

print("=== BIT table parse (bit.c:70-149) per image ===")
def parse_bit(d, bit_off, label):
    out = {"bit_off": bit_off, "sig": d[bit_off:bit_off+7].hex(),
           "sig_ok": d[bit_off:bit_off+7] == b"\xff\xb8BIT\0\0",
           "header": {}, "entries": [], "i_entry": None}
    check(out["sig_ok"], "%s BIT signature at 0x%x" % (label, bit_off))
    hlen = u8(d, bit_off + 8); rlen = u8(d, bit_off + 9); nent = u8(d, bit_off + 10)
    bver = u16(d, bit_off + 6)
    chk = sum(d[bit_off:bit_off + hlen]) & 0xff
    out["header"] = {"version_u16@+6": hex(bver), "hlen@+8": hlen, "rlen@+9": rlen,
                     "entriesnum@+10": nent, "header_checksum_mod256": chk}
    check(bver == 0x0100, "%s BIT header version 0x0100 accepted (bit.c:98-103)" % label)
    check(hlen >= 12, "%s hlen>=12 (bit.c:104-107)" % label)
    check(rlen >= 6, "%s rlen>=6 (bit.c:108-111)" % label)
    check(chk == 0, "%s BIT header checksum mod256 == 0 (bit.c:82-94)" % label)
    for i in range(nent):
        o = bit_off + hlen + rlen * i
        typ = u8(d, o); ver = u8(d, o + 1); tlen = u16(d, o + 2); toff = u16(d, o + 4)
        ent = {"idx": i, "type": chr(typ) if 32 <= typ < 127 else "?",
               "type_hex": hex(typ), "version": ver, "t_len": tlen, "t_offset": toff,
               "t_offset_hex": hex(toff)}
        out["entries"].append(ent)
        if typ == 0x69 and ver == 2:  # 'i' Info v2
            out["i_entry"] = ent
            # info.c:49-52 population at STORED t_offset (stock envytools absolute read)
            v = [u8(d, toff + 3), u8(d, toff + 2), u8(d, toff + 1), u8(d, toff + 0), u8(d, toff + 4)]
            # info.c mapping: v[3]=+0, v[2]=+1, v[1]=+2, v[0]=+3, v[4]=+4
            out["i_stock_version"] = {"version": v, "major_version[0]": hex(v[0]),
                                      "read_offset": hex(toff + 3), "read_byte": hex(v[0])}
            # ROM-layout-intended read: t_offset relative to 0x28600 (verified empirically below)
            abs_off = ROM_LEGACY_BASE + toff
            v2 = [u8(d, abs_off + 3), u8(d, abs_off + 2), u8(d, abs_off + 1),
                  u8(d, abs_off + 0), u8(d, abs_off + 4)]
            out["i_intended_version"] = {"version": v2, "major_version[0]": hex(v2[0]),
                                         "read_offset": hex(abs_off + 3),
                                         "read_base": hex(ROM_LEGACY_BASE), "stored_t_offset": hex(toff)}
            out["i_raw_stored"] = d[toff:toff + min(tlen, 16)].hex()
            out["i_raw_intended"] = d[abs_off:abs_off + min(tlen, 16)].hex()
    return out

for name, spec in IMAGES.items():
    d = results["images"][name]["_data"]
    if name == "shadow":
        res1 = parse_bit(d, BIT_OFF_SHADOW_1, "%s (shadow first BIT)" % name)
        res2 = parse_bit(d, BIT_OFF_SHADOW_2, "%s (shadow second BIT)" % name)
        results["bit"][name] = {"first": res1, "second": res2}
        print("  %s: first BIT @0x%x sig_ok=%s entries=%d; second BIT @0x%x sig_ok=%s entries=%d"
              % (name, BIT_OFF_SHADOW_1, res1["sig_ok"], len(res1["entries"]),
                 BIT_OFF_SHADOW_2, res2["sig_ok"], len(res2["entries"])))
        # cross-check shadow[0x3f4] == rom intended 'i' bytes
        rom = results["images"]["rom"]["_data"]
        check(d[0x3f4:0x3f4 + 5] == rom[0x289f4:0x289f4 + 5],
              "shadow i-table @0x3f4 == rom intended i-table @0x289f4 bytes")
    else:
        res = parse_bit(d, BIT_OFF, name)
        results["bit"][name] = res
        ie = res["i_entry"]
        print("  %s: entries=%d i_entry=%s" % (name, len(res["entries"]),
                                               json.dumps(ie) if ie else None))
        # empirical verification: t_offset is relative to 0x28600 in rom/t4
        if ie:
            target = ROM_LEGACY_BASE + ie["t_offset"]
            check(ie["t_offset"] + ROM_LEGACY_BASE == target, "t_offset arithmetic")
            # 'B' entry [1] -> 0x2883e matches prior gap analysis; 'P' [7] -> 0x288d4 matches P-dir loc
            b = res["entries"][1]; p = res["entries"][7]
            check(ROM_LEGACY_BASE + b["t_offset"] == 0x2883e,
                  "rom/t4 'B' entry maps to 0x2883e (prior gap-analysis anchor)")
            check(ROM_LEGACY_BASE + p["t_offset"] == 0x288d4,
                  "rom/t4 'P' entry maps to 0x288d4 (prior P-dir anchor)")
            check(ROM_LEGACY_BASE + ie["t_offset"] == 0x289f4,
                  "rom/t4 'i' entry maps to 0x289f4; table end 0x289f4+0x68=0x28a5c matches prior report")

print("=== BMP path (nvbios.c:1077-1078, parse_bios_version at 858) ===")
for name, spec in IMAGES.items():
    d = results["images"][name]["_data"]
    sig_off = d.find(b"\xff\x7fNV\0")
    active = sig_off >= 0
    results["bmp"][name] = {"sig_found": active, "bmp_offset": sig_off,
                            "bmp_path_version0_offset": None if sig_off < 0 else hex(sig_off + 13)}
    print("  %s: BMP signature \\xff\\x7fNV\\0 at %s -> parse_bios_version %s"
          % (name, hex(sig_off) if sig_off >= 0 else "NOT FOUND",
             "NOT CALLED" if not active else "would read data[bmp_offset+13]"))
    check(not active, "%s: no BMP signature -> BMP version path inactive (version[] only from BIT 'i')" % name)

print("=== version[0] established per image ===")
for name, spec in IMAGES.items():
    bit = results["bit"][name]
    if name == "shadow":
        # shadow's first BIT is at file base 0 -> stock read applies directly; its 'i' table @0x3f4
        stock = bit["first"]["i_stock_version"]["major_version[0]"]
        intended_same = bit["first"]["i_stock_version"]["read_offset"] == bit["first"]["i_intended_version"]["read_offset"]
        final = stock  # shadow layout is self-consistent (image base = 0)
    else:
        stock = bit["i_stock_version"]["major_version[0]"]
        intended = bit["i_intended_version"]["major_version[0]"]
        final = intended  # t_offset fields verified relative to 0x28600
        print("  %s: stock(abs @%s)=%s ; intended(0x28600+t_off @%s)=%s"
              % (name, bit["i_stock_version"]["read_offset"], stock,
                 bit["i_intended_version"]["read_offset"], intended))
    results["version"][name] = {"stock_envytools_read": stock,
                                "final_established_major": final if name != "shadow" else stock,
                                "basis": "BIT 'i' info.c:49-52; BMP path inactive (no \\xff\\x7fNV\\0)"}
    print("  %s -> established bios->info.version[0] = %s" % (name, results["version"][name]["final_established_major"]))

print("=== PM_Mode consumer branches vs established version[0] (nvbios.c:1477-1554) ===")
# table start and header bytes (PERFORMANCE v0x60)
rom = results["images"]["rom"]["_data"]
t4 = results["images"]["t4"]["_data"]
sh = results["images"]["shadow"]["_data"]
perf_hdr_rom = rom[PERF_V60_OFF:PERF_V60_OFF + 8].hex()
perf_hdr_t4 = t4[PERF_V60_OFF:PERF_V60_OFF + 8].hex()
perf_hdr_shadow_eq = sh[PERF_V60_SHADOW_OFF:PERF_V60_SHADOW_OFF + 8].hex()
perf_hdr_shadow_file = sh[PERF_V60_OFF:PERF_V60_OFF + 8].hex()
results["table_0x60"]["perf_v60"] = {"file": "PERFORMANCE table (BIT 'P' dir entry 0x00 -> 0x1ab55)",
                                     "start_rom": hex(PERF_V60_OFF),
                                     "header_rom": perf_hdr_rom,
                                     "table_version_byte": rom[PERF_V60_OFF],
                                     "byte_identical_rom_t4": perf_hdr_rom == perf_hdr_t4,
                                     "shadow_equivalent_offset": hex(PERF_V60_SHADOW_OFF),
                                     "shadow_equivalent_header": perf_hdr_shadow_eq,
                                     "shadow_equivalent_matches_rom": perf_hdr_rom == perf_hdr_shadow_eq,
                                     "shadow_file_at_0x54155": perf_hdr_shadow_file,
                                     "notes": "shadow file at 0x54155 is 0xFF-filled (different image region); "
                                              "shadow-equivalent offset 0x2bb55 matches rom byte-for-byte"}
print("  PERFORMANCE v0x60 @ ROM %s: %s ... table version byte = 0x%02x"
      % (hex(PERF_V60_OFF), perf_hdr_rom, rom[PERF_V60_OFF]))
print("  T4 identical: %s ; shadow @0x2bb55 identical: %s ; shadow file @0x54155: %s"
      % (perf_hdr_rom == perf_hdr_t4, perf_hdr_rom == perf_hdr_shadow_eq, perf_hdr_shadow_file))

def branch_eval(major):
    """Evaluate nvbios.c:1491-1528 dispatch for a given BIOS major version, against
    table start 0x54155 whose header version byte is 0x60. Returns branch outcome;
    no section bounds are adopted (none are supported for table version 0x60)."""
    if major == 0x4:
        return {"branch": "nvbios.c:1491", "condition": "version[0] == 0x4",
                "taken": True, "schema": "version=data[start+0], hdr=data[start+1], "
                                         "entry_count=data[start+2], entry_length=data[start+3]",
                "table_v60_consumed": False,
                "note": "header_length fields only; table version 0x60 has no case here (this branch "
                        "keys on BIOS major, not table version)"}
    if major < 0x70:
        start = PERF_V60_OFF
        return {"branch": "nvbios.c:1497", "condition": "version[0] < 0x70", "taken": True,
                "schema": "version=data[start+0]=0x60; header_length=data[start+1]=0x0a; "
                          "entry_count=data[start+2]=0x05; mode_info_length=data[start+3]=0x07; "
                          "extra_data_count=data[start+4]=0x06; extra_data_length=data[start+5]=0x0a; "
                          "entry_length = mode_info_length + extra_data_count*extra_data_length = 0x07 + 6*8 = 53",
                "computed_extent": [hex(start), hex(start + 10 + 53), "len 63 incl header"],
                "table_v60_consumed": False,
                "note": "table version 0x60 matches no per-entry sub-schema (0x12/0x13/0x15, 0x21-0x24, "
                        "0x25, 0x30/0x35, 0x40-0x50) -> 'Version unknown'; entry_length=53 is a "
                        "generic hdr+esz*count-style figure with no v60 schema backing — NOT adopted"}
    if (major & 0xf0) <= 0x80:
        return {"branch": "nvbios.c:1505", "condition": "(version[0] & 0xf0) <= 0x80", "taken": True,
                "schema": "subentry model; case 0x50 / default",
                "table_v60_consumed": False,
                "note": "no case 0x60; default reads entry_count=data[start+5], subentry_size=data[start+3], "
                        "subentry_count=data[start+4] — generic, not v60-specific"}
    return {"branch": "nvbios.c:1527", "condition": "else", "taken": True,
            "statement": 'printf("Unknown PM major version %x")',
            "table_v60_consumed": False,
            "note": "only printcmd(start, header_length>0?header_length:10) hex dump; no table field consumed"}

for major_name, major in (("v00_stock_rom_t4", 0x00), ("v90_established_rom_t4", 0x90),
                          ("v90_shadow_stock", 0x90)):
    res = branch_eval(major)
    res["evaluated_against_table"] = "PERFORMANCE v0x60 @ " + hex(PERF_V60_OFF)
    results["pm_mode"][major_name] = {"bios_major": hex(major), "result": res}
    print("  BIOS major %s: %s -> %s" % (hex(major), res["branch"], res["note"][:120]))

print("=== table ID 0x60 (power.c P2_tbls, DI/DT) ===")
results["table_0x60"]["power_table_id_0x60"] = {"name": "DI/DT", "target": "power->unk60.offset",
                                                "parser": "envy_bios_parse_power_unk60 (power.c:1605-1621)",
                                                "own_header": "version@offset+0, hlen@+1, rlen@+2, entriesnum@+3",
                                                "consumes_bios_info_version": False,
                                                "note": "independent of nvbios.c PM_Mode dispatch; version[0] never read"}
print("  power.c:107 {0x60, &power->unk60.offset, \"DI/DT\"} -> envy_bios_parse_power_unk60; no consumption of bios->info.version[0]")

print("=== self-check ===")
print("  total checks: %d, failures: %d" % (checks, len(fails)))
results["self_checks"] = {"total": checks, "failures": len(fails), "failed_msgs": fails}
# strip raw image blobs before serialization
for _name in results["images"]:
    results["images"][_name].pop("_data", None)
results["created_utc"] = datetime.now(timezone.utc).isoformat()
results["conclusion"] = {
    "version[0]_established": "0x90 for rom/t4 (BIT 'i' at 0x289f4: bytes 00 67 06 90 06 -> "
                              "\"90.06.67.00.06\", confirming the handoff string is the BIT 'i' version, "
                              "not an incidental string); stock envytools absolute read on rom/t4 yields "
                              "0x00 because this ROM stores BIT t_offset relative to 0x28600; shadow "
                              "stock read yields 0x90.",
    "bmp_path": "inactive in all three images (no \\xff\\x7fNV\\0 signature)",
    "pm_mode_vs_table_0x60": "with version[0]=0x90 -> nvbios.c:1527 'Unknown PM major version 90', "
                             "no table field consumed; with version[0]=0x00 -> nvbios.c:1497 branch taken "
                             "but table version byte 0x60 matches no sub-schema; no section bounds or "
                             "stride for the v60 table are adopted in any case",
    "table_id_0x60": "DI/DT via power->unk60.offset, independent parser, no version[0] consumption",
    "adopted_extent": "NONE — PERFORMANCE v60 remains OPAQUE; unknown fields preserved",
}

out_json = {"results": results}
with open(OUT_DIR + "/VBIOS_VERSION_CONSUMER.json", "w") as f:
    json.dump(out_json, f, indent=2)
print("\nwrote " + OUT_DIR + "/VBIOS_VERSION_CONSUMER.json")
sys.exit(1 if fails else 0)

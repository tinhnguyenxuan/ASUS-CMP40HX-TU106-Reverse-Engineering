#!/usr/bin/env python3
# T05 independent offline VBIOS/DCB parser. Bounds-checked, no hardware access.
import hashlib, json, struct

ROMS = {
    "CMP40HX_ORIGINAL_1MB.bin": "/home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF/03_VBIOS/CMP40HX_ORIGINAL_1MB.bin",
    "cmp40hx_t4_derivative.bin": "/home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF/03_VBIOS/cmp40hx_t4_derivative.bin",
}
OUT = "/home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/results/T05"
LOG = []

def log(msg):
    LOG.append(msg)

def rd(data, off, n, what):
    if off < 0 or off + n > len(data):
        raise ValueError(f"OOB read {what}: off=0x{off:x} n={n} len=0x{len(data):x}")
    return data[off:off+n]

def u16(data, off, what):
    return struct.unpack("<H", rd(data, off, 2, what))[0]

def u32(data, off, what):
    return struct.unpack("<I", rd(data, off, 4, what))[0]

def find_pcir_images(data):
    """Scan 512-byte-aligned blocks for 0x55AA + PCIR. Independent decoder."""
    images = []
    off = 0
    while off + 512 <= len(data):
        b = rd(data, off, 512, "block")
        if b[0] == 0x55 and b[1] == 0xAA:
            pcir_off = struct.unpack("<H", b[24:26])[0]
            if 0 < pcir_off <= 508 and b[pcir_off:pcir_off+4] == b"PCIR":
                vendor, device = struct.unpack("<HH", b[pcir_off+4:pcir_off+8])
                img_len = struct.unpack("<H", b[pcir_off+16:pcir_off+18])[0] * 512
                images.append({"block_off": off, "pcir_off_in_block": pcir_off,
                               "vendor": hex(vendor), "device": hex(device),
                               "image_len": img_len})
                off += img_len if img_len else 512
            else:
                off += 512
        else:
            off += 512
    return images

def parse_dcb(data, dcb_abs, name):
    """Decode DCB v4.0/4.1 header per envytools/NVIDIA DCB 4.x layout."""
    r = {"dcb_abs": hex(dcb_abs)}
    hdr = rd(data, dcb_abs, 44, "dcb header")
    ver = hdr[0]
    r["version"] = hex(ver)
    r["sig_bytes"] = hdr[0:8].hex()
    if ver not in (0x40, 0x41):
        log(f"{name}: DCB version 0x{ver:02x} at 0x{dcb_abs:x} unexpected")
        r["valid"] = False
        return r
    r["header_size"] = hdr[1]
    r["entry_size"] = hdr[2]
    r["entry_count"] = hdr[3]
    # v4.x pointer table: u16 slots after 4-byte prologue, relative to DCB base.
    # envytools dcb.c slot order for 4.0/4.1:
    # 0 connector, 1 input, 2 encoder, 3 homebrew, 4 cinema, 5 io,
    # 6 spread_spectrum, 7 hdtv, 8 i2c_devices, 9 gpio, 10 communications(4.1)
    names = {0: "connector", 1: "input", 2: "encoder", 3: "homebrew", 4: "cinema",
             5: "io", 6: "spread_spectrum", 7: "hdtv", 8: "i2c_devices", 9: "gpio",
             10: "communications"}
    tables = {}
    for idx in range(11):
        rel = u16(hdr, 4 + idx * 2, f"dcb ptr slot {idx}")
        nm = names[idx]
        t = {"rel": rel}
        if rel == 0:
            t["present"] = False
        else:
            t["present"] = True
            t["abs"] = hex(dcb_abs + rel)
            th = rd(data, dcb_abs + rel, 8, f"table {nm} header")
            t["hdr_hex"] = th.hex()
            t["ver"] = hex(th[0])
            t["hdr_size"] = th[1]
            t["count"] = th[2]
            t["entry_size"] = th[3]
        tables[nm] = t
    r["tables"] = tables
    r["valid"] = True
    return r

def dump_rows(data, abs_off, count, esize, max_rows=48):
    rows = []
    for i in range(min(count, max_rows)):
        try:
            rows.append(rd(data, abs_off + i * esize, esize, f"row {i}").hex())
        except ValueError as e:
            log(str(e))
            break
    return rows

def decode_comm(row_hex):
    """CCB 4.1 communications entry: u32 LE -> low byte i2c port, next dpaux."""
    b = bytes.fromhex(row_hex)
    v = struct.unpack("<I", b)[0]
    return {"i2c_port": v & 0x1F, "dpaux_port": (v >> 5) & 0x1F, "raw_high": hex(v >> 10)}

def decode_gpio(row_hex):
    b = bytes.fromhex(row_hex)
    line = b[0]
    tag = b[1]
    return {"line": line, "tag": hex(tag),
            "unused": tag == 0xff,
            "byte2": hex(b[2]), "byte3": hex(b[3]),
            "byte4": hex(b[4]), "byte5": hex(b[5])}

results = {}
for name, path in ROMS.items():
    with open(path, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    log(f"{name}: len=0x{len(data):x} sha256={sha}")
    r = {"file": name, "size": len(data), "sha256": sha}
    r["sig_55aa_at_0"] = data[0:2] == b"\x55\xAA"
    imgs = find_pcir_images(data)
    r["pcir_images"] = imgs
    log(f"{name}: pcir images = {imgs}")
    if len(data) >= 0x1A:
        r["last_image_ptr_field_0x18"] = hex(u16(data, 0x18, "last image ptr"))
    # BIT token scan (0x54 0x4e) from 0
    bit_hits = [i for i in range(0, min(len(data) - 8, 0x40000), 4) if data[i] == 0x54 and data[i + 1] == 0x4e]
    r["bit_token_hits"] = [hex(h) for h in bit_hits[:10]]
    if bit_hits:
        bh = bit_hits[0]
        r["bit_header"] = {"off": hex(bh), "bytes": rd(data, bh, 12, "bit header").hex()}
        log(f"{name}: BIT header at 0x{bh:x}: {r['bit_header']['bytes']}")
    # Legacy image base claim 0x28600 — VERIFY, not assume
    legacy = [im for im in imgs if im["block_off"] == 0x28600]
    r["legacy_image_at_0x28600"] = bool(legacy)
    lb = 0x28600 if legacy else (imgs[-1]["block_off"] if imgs else 0)
    r["legacy_base"] = hex(lb)
    # DCB pointer at legacy_base + 0x36 per BIT/DCB 4.x convention — CHECK
    try:
        dcb_ptr = u16(data, lb + 0x36, "dcb ptr @base+0x36")
        r["dcb_ptr_at_base_plus_0x36"] = hex(dcb_ptr)
        dcb_abs = lb + dcb_ptr
        r["dcb_abs_computed"] = hex(dcb_abs)
        r["claimed_dcb_abs_0x2d9ac_matches"] = (dcb_abs == 0x2D9AC)
    except ValueError as e:
        log(f"{name}: {e}")
        dcb_abs = None
    if dcb_abs is not None:
        try:
            dcb = parse_dcb(data, dcb_abs, name)
        except ValueError as e:
            log(f"{name}: dcb parse fail: {e}")
            dcb = {"error": str(e)}
        r["dcb"] = dcb
        base = dcb_abs
        t = dcb.get("tables", {})
        # connector detail
        ct = t.get("connector", {})
        if ct.get("present") and ct.get("count", 0) > 0:
            cabs = base + ct["rel"] + ct["hdr_size"]
            r["connector_entries"] = dump_rows(data, cabs, ct["count"], ct["entry_size"])
        # gpio detail
        gt = t.get("gpio", {})
        if gt.get("present") and gt.get("count", 0) > 0:
            gabs = base + gt["rel"] + gt["hdr_size"]
            rows = dump_rows(data, gabs, gt["count"], gt["entry_size"])
            r["gpio_entries"] = [dict(decode_gpio(h), raw=h) for h in rows]
        # communications detail (CCB 4.1)
        mt = t.get("communications", {})
        if mt.get("present") and mt.get("count", 0) > 0:
            mabs = base + mt["rel"] + mt["hdr_size"]
            rows = dump_rows(data, mabs, mt["count"], mt["entry_size"])
            r["communications_entries"] = [dict(decode_comm(h), raw=h) for h in rows]
        # i2c_devices
        it = t.get("i2c_devices", {})
        if it.get("present") and it.get("count", 0) > 0:
            iabs = base + it["rel"] + it["hdr_size"]
            r["i2c_device_entries"] = dump_rows(data, iabs, it["count"], it["entry_size"])
    results[name] = r

with open(f"{OUT}/VBIOS_DISPLAY_TABLES.json", "w") as f:
    json.dump({"parser_log": LOG, "results": results}, f, indent=2)
print("LOG:")
print("\n".join(LOG))
for name, r in results.items():
    print(f"\n== {name} ==")
    print(json.dumps({k: v for k, v in r.items() if k not in ("gpio_entries", "i2c_device_entries")}, indent=2)[:3500])

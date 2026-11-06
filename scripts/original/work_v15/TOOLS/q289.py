#!/usr/bin/env python3
"""Q2 + Q8 + Q9: hash fuse, 24 byte blob diff, bang descriptor thu 2.

Dung: python3 q289.py
Xuat: VBIOS/q2_hash.json, FIRMWARE/q8_blobdiff.json, GSP/q9_table2.json
"""
import hashlib
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

FUSE_HASHES = {"fuse_0x0718": 0x0718, "fuse_0x0344": 0x0344}


def load_fuse():
    d = json.load(open(P("FUSE", "fuse2.json")))
    r = {int(k): v for k, v in d["regs"].items()}
    out = {}
    for nm, off in FUSE_HASHES.items():
        b = b"".join(struct.pack("<I", r.get(off + i * 4, 0)) for i in range(8))
        out[nm] = b
    return out


def q2():
    """Thu SHA-256 tren moi cua so truot cua cac vung lon."""
    print("=" * 88)
    print("Q2 — 32 byte hash trong fuse: tim vung khop")
    print("=" * 88)
    fh = load_fuse()
    for nm, b in fh.items():
        print(f"  {nm} = {b.hex()}")

    targets = {v: k for k, v in fh.items()}
    # nguon du lieu
    srcs = []
    for path, nm in ((P("outputs", "CMP40HX_ORIGINAL_1MB.bin"), "rom"),
                     (P("outputs", "gsp_tu10x.bin"), "gsp"),
                     (P("outputs", "ucodes_tu10x.bin"), "ucodes")):
        if os.path.exists(path):
            srcs.append((nm, open(path, "rb").read()))
            print(f"  nguon {nm}: {os.path.getsize(path):,} B")

    hits = []
    trials = 0
    for nm, d in srcs:
        # (a) hash toan bo
        for algo in ("sha256", "sha3_256", "blake2s"):
            h = hashlib.new(algo, d).digest()
            trials += 1
            if h in targets:
                hits.append(dict(src=nm, mode="whole", algo=algo))
        # (b) cua so truot: kich thuoc le, stride 0x200
        for sz in (0x1000, 0x2000, 0x4000, 0x8000, 0x10000, 0x1800, 0xC00,
                   0x400, 0x200, 0x100, 0x40):
            for s in range(0, len(d) - sz + 1, 0x200):
                h = hashlib.sha256(d[s:s + sz]).digest()
                trials += 1
                if h in targets:
                    hits.append(dict(src=nm, mode="window", algo="sha256",
                                     size=sz, start=s))
            if len(d) > 4_000_000 and sz < 0x1000:
                break        # gsp 22 MB x cua so nho qua lau, bo
    print(f"\n  {trials:,} phep thu")
    print(f"  -> {len(hits)} khop")
    for h in hits:
        print(f"    KHOP: {h}")

    # (c) doi chieu: 32 B co phai 2x SHA256 khong
    print(f"\n  kiem tra: 32 B co phai la 2 hash 16 B ghep?")
    for nm, b in fh.items():
        print(f"    {nm}: first16={b[:16].hex()} last16={b[16:].hex()}")

    json.dump(dict(targets={k: v.hex() for k, v in fh.items()},
                   trials=trials, hits=hits,
                   note="0 khop = khong phai SHA-256 cua vung/whole-file nao"),
              open(P("VBIOS", "q2_hash.json"), "w"), indent=1)
    return len(hits)


def q8():
    """Q8: 24 byte khac giua blob[6] va blob[8]."""
    print("\n" + "=" * 88)
    print("Q8 — 24 byte khac giua blob[6] va blob[8]")
    print("=" * 88)
    p = P("outputs", "ucodes_tu10x.bin")
    if not os.path.exists(p):
        print("  SKIP: khong co ucodes_tu10x.bin")
        return None
    d = open(p, "rb").read()
    OFFS = [0x2F00, 0x20F00, 0x3EF00, 0x5CF00, 0x7AF00, 0x98F00,
            0xB7C00, 0xD6700, 0xF5400, 0x113F00, 0x134300]
    b6 = d[OFFS[6]:OFFS[7]]
    b8 = d[OFFS[8]:OFFS[9]]
    diff = [i for i in range(len(b6)) if b6[i] != b8[i]]
    print(f"  blob[6] 0x{OFFS[6]:06x} vs blob[8] 0x{OFFS[8]:06x}  "
          f"({len(b6)} vs {len(b8)} B)")
    print(f"  {len(diff)} byte khac\n")
    print(f"  {'off':>8s}  blob[6]                              blob[8]")
    recs = []
    for i in diff:
        lo = max(0, i - 8)
        hi = min(len(b6), i + 9)
        print(f"  0x{i:06x}  {b6[lo:hi].hex(' '):<36s}  {b8[lo:hi].hex(' ')}")
        recs.append(dict(off=i, off_hex=f"0x{i:06x}", v6=b6[i], v8=b8[i]))

    # gom cum
    runs = []
    cur = [diff[0]]
    for a, b in zip(diff, diff[1:]):
        if b - a <= 64:
            cur.append(b)
        else:
            runs.append((cur[0], cur[-1]))
            cur = [b]
    runs.append((cur[0], cur[-1]))
    print(f"\n  {len(runs)} cum:")
    for s, e in runs:
        print(f"    0x{s:06x}..0x{e:06x} ({e - s + 1} B)")
        print(f"      b6: {b6[s:e + 1].hex(' ')}")
        print(f"      b8: {b8[s:e + 1].hex(' ')}")
        # thu doc u32
        if (e - s + 1) % 4 == 0:
            u6 = struct.unpack(f"<{(e - s + 1) // 4}I", b6[s:e + 1])
            u8 = struct.unpack(f"<{(e - s + 1) // 4}I", b8[s:e + 1])
            print(f"      u32 b6: {[hex(x) for x in u6]}")
            print(f"      u32 b8: {[hex(x) for x in u8]}")

    # co phai timestamp / version khong
    print(f"\n  kiem tra nghia:")
    for s, e in runs:
        seg = b6[s:e + 1]
        if len(seg) >= 4:
            v = struct.unpack("<I", seg[:4])[0]
            print(f"    0x{s:06x} u32={v} (0x{v:08x})")
            # version dang X.Y.Z
            if v < 0x10000:
                print(f"      -> co the la version: {v >> 8}.{v & 0xFF}")

    json.dump(dict(blob6=f"0x{OFFS[6]:06x}", blob8=f"0x{OFFS[8]:06x}",
                   size=len(b6), diff_count=len(diff), bytes=recs,
                   runs=[dict(start=s, end=e, size=e - s + 1,
                              hex6=b6[s:e + 1].hex(), hex8=b8[s:e + 1].hex())
                         for s, e in runs],
                   note="24 byte khac = 4 cum: 2 cum 1 B + 2 cum 20 B"),
              open(P("FIRMWARE", "q8_blobdiff.json"), "w"), indent=1)
    return len(diff)


def q9():
    """Q9: tim bang descriptor thu 2 chua RMClkVfOverride / OVERVOLTAGE_*."""
    print("\n" + "=" * 88)
    print("Q9 — bang descriptor thu 2 (chua 7 ten khong co trong 60 bang)")
    print("=" * 88)
    p = P("outputs", "gsp_tu10x.bin")
    if not os.path.exists(p):
        print("  SKIP: khong co gsp_tu10x.bin")
        return None
    d = open(p, "rb").read()
    DELTA = 0x4000000
    INNER = 0x40

    # ELF sections
    e = d[INNER:INNER + 64]
    shoff = struct.unpack("<Q", e[40:48])[0]
    shsz = struct.unpack("<H", e[58:60])[0]
    shnum = struct.unpack("<H", e[60:62])[0]
    shstr = struct.unpack("<H", e[62:64])[0]
    o = INNER + shoff + shstr * shsz
    stoff = struct.unpack("<Q", d[o + 24:o + 32])[0]
    stsz = struct.unpack("<Q", d[o + 32:o + 40])[0]
    strs = d[INNER + stoff:INNER + stoff + stsz]
    shs = []
    for i in range(shnum):
        o = INNER + shoff + i * shsz
        nm = struct.unpack("<I", d[o:o + 4])[0]
        addr = struct.unpack("<Q", d[o + 16:o + 24])[0]
        off = struct.unpack("<Q", d[o + 24:o + 32])[0]
        size = struct.unpack("<Q", d[o + 32:o + 40])[0]
        z = strs.find(b"\x00", nm)
        shs.append(dict(name=strs[nm:z].decode("latin1"), vaddr=addr,
                        file_off=INNER + off, size=size))

    TARGETS = ["RMClkVfOverride", "RmAtsVolOverride", "RmClkControllersOverride",
               "OVERVOLTAGE_LOGIC", "OVERVOLTAGE_NVVDD_0", "OVERVOLTAGE_NVVDD_1",
               "PERFORMANCE_CAP0"]
    locs = {}
    for t in TARGETS:
        i = d.find(t.encode())
        if i >= 0:
            locs[t] = i
    print(f"  vi tri 7 ten: {{k: hex(v) for k,v in locs.items()}}")
    for t, i in locs.items():
        print(f"    {t:<32s} @0x{i:08x} vaddr 0x{DELTA + i:08x}")

    # --- xung quanh moi ten: co entry 32B nao tro toi khong ---
    print(f"\n  tim entry 32 B tro toi tung ten (moi section, moi offset chan 4)")
    found = []
    for t, fo in locs.items():
        va = DELTA + fo
        p32 = struct.pack("<I", va)
        p64 = struct.pack("<Q", va)
        n32 = d.count(p32)
        n64 = d.count(p64)
        # quet entry-style: u64 ptr tai offset o, cac truong sau <= 10000
        ent = []
        for s in shs:
            if s["size"] < 0x100:
                continue
            lo, hi = s["file_off"], min(s["file_off"] + s["size"], len(d) - 32)
            # chi quet vung co the chua bang (rodata/data)
            if "text" in s["name"]:
                continue
            for q in range(lo, hi, 4):
                if d[q:q + 8] != p64:
                    continue
                f0c = struct.unpack("<I", d[q + 12:q + 16])[0]
                ent.append(dict(off=q, f0c=f0c,
                                f08=f"0x{struct.unpack('<I', d[q + 8:q + 12])[0]:08x}",
                                id=struct.unpack("<I", d[q + 16:q + 20])[0],
                                f14=struct.unpack("<I", d[q + 20:q + 24])[0],
                                f18=struct.unpack("<I", d[q + 24:q + 28])[0]))
        print(f"    {t:<32s} u32ptr={n32} u64ptr={n64} entry-style={len(ent)}")
        for x in ent[:3]:
            print(f"      @0x{x['off']:08x} f08={x['f08']} f0c={x['f0c']} "
                  f"id={x['id']} f14={x['f14']} f18={x['f18']}")
        found.append(dict(name=t, file_off=fo, vaddr=va,
                          u32_ptr=n32, u64_ptr=n64, entries=ent))

    # --- xung quanh ten: co bang nao khac khong ---
    print(f"\n  ngu canh 128 B quanh moi ten:")
    for t, fo in list(locs.items())[:3]:
        print(f"    --- {t} ---")
        for k in range(max(0, fo - 32), min(len(d), fo + 96), 16):
            b = d[k:k + 16]
            s = "".join(chr(c) if 32 <= c < 127 else "." for c in b)
            print(f"      {k:08x}  {b.hex(' '):<47s} {s}")

    json.dump(dict(targets=found, sections=shs,
                   note="quet entry-style (u64 ptr + truong so) trong "
                        ".rodata/.data, loai .text"),
              open(P("GSP", "q9_table2.json"), "w"), indent=1)
    return len(found)


def main():
    h = q2()
    n = q8()
    f = q9()
    print("\n" + "=" * 88)
    print(f"Q2: {h} khop hash | Q8: {n} byte khac | Q9: {f} ten kiem tra")
    print("=" * 88)


if __name__ == "__main__":
    main()
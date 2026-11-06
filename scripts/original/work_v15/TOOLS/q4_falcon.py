#!/usr/bin/env python3
"""Q4: parse FALCON_DATA + NVINIT day du tu VBIOS.

Dung: python3 q4_falcon.py CMP40HX_ORIGINAL_1MB.bin VBIOS/
"""
import json
import struct
import sys

FALCON = 0x48B54
NVINIT_ENTRY = 0x28893
BIT = 0x287B0
IMG, IL, EL = 0x28600, 0xF400, 0x11000


def ptr(p):
    a = IMG + p
    return a + EL if p >= IL else a


def main():
    rom = open(sys.argv[1], "rb").read()
    out = sys.argv[2].rstrip("/")

    # ---------- BIT token NVINIT ----------
    print("=== BIT token table ===")
    hdr, tsz, cnt = rom[BIT + 8], rom[BIT + 9], rom[BIT + 10]
    toks = {}
    for i in range(cnt):
        o = BIT + hdr + i * tsz
        tok = rom[o]
        p = struct.unpack("<H", rom[o + 4:o + 6])[0]
        ln = rom[o + 2]
        toks[tok] = dict(ptr=p, at=ptr(p), len=ln)
    print(f"  {cnt} token")
    for t in (0x70, 0x49, 0x50, 0x43, 0x4D):
        if t in toks:
            print(f"    0x{t:02x} -> 0x{toks[t]['at']:06x} (len {toks[t]['len']})")

    # ---------- FALCON_DATA ----------
    print(f"\n=== FALCON_DATA @0x{FALCON:06x} ===")
    h = rom[FALCON:FALCON + 16]
    ver, hd, esz, n = h[0], h[1], h[2], h[3]
    print(f"  header: {h[:8].hex(' ')}")
    print(f"  ver=0x{ver:02x} hdr={hd} esz={esz} cnt={n} -> {hd + esz * n} B")
    ents = []
    for i in range(n):
        o = FALCON + hd + i * esz
        b = rom[o:o + esz]
        txt = "".join(chr(c) if 32 <= c < 127 else "." for c in b)
        u32 = [struct.unpack("<I", b[k:k + 4])[0] for k in range(0, esz - 3, 4)]
        u16 = [struct.unpack("<H", b[k:k + 2])[0] for k in range(0, esz - 1, 2)]
        ents.append(dict(idx=i, off=o, off_hex=f"0x{o:06x}", raw=b.hex(),
                         ascii=txt, u32=u32, u16=u16))
        print(f"  [{i:>2d}] @0x{o:06x} {b.hex(' ')}")
        if any(32 <= c < 127 for c in b):
            print(f"        txt: {txt}")
        if any(u32):
            print(f"        u32: {u32}")

    # ---------- NVINIT ----------
    print(f"\n=== NVINIT: token 0x49 ===")
    if 0x49 in toks:
        at = toks[0x49]["at"]
        ln = toks[0x49]["len"]
        print(f"  token 0x49 len={ln} -> 0x{at:06x}")
        print(f"  raw: {rom[at:at + 32].hex(' ')}")
        # doc nhu mang con tro u16
        print(f"\n  NVINIT_PTRS nhu u16:")
        for i in range(12):
            v = struct.unpack("<H", rom[at + i * 2:at + i * 2 + 2])[0]
            if v == 0:
                continue
            tgt = ptr(v)
            # kiem tra tgt co hop le
            ok = 0x28600 <= tgt < 0x79000
            print(f"    [{i:>2d}] ptr=0x{v:04x} -> 0x{tgt:06x} "
                  f"{'OK' if ok else 'ngoai vung'}")
        # thu doc nhu u32
        print(f"\n  NVINIT_PTRS nhu u32:")
        for i in range(8):
            v = struct.unpack("<I", rom[at + i * 4:at + i * 4 + 4])[0]
            if v == 0:
                continue
            print(f"    [{i:>2d}] 0x{v:08x}")

    # ---------- NVINIT_ENTRY cu ----------
    print(f"\n=== so sanh: offset cu 0x{NVINIT_ENTRY:06x} (bao cao truoc) ===")
    print(f"  raw: {rom[NVINIT_ENTRY:NVINIT_ENTRY + 32].hex(' ')}")
    print(f"  nam trong BIT table? {BIT <= NVINIT_ENTRY < BIT + 0x100}")
    print(f"  token 0x49 that o 0x{toks.get(0x49, {}).get('at', 0):06x}")

    # ---------- parse tung khoi NVINIT ----------
    print(f"\n=== parse khoi NVINIT ===")
    blocks = []
    if 0x49 in toks:
        at = toks[0x49]["at"]
        for i in range(12):
            v = struct.unpack("<H", rom[at + i * 2:at + i * 2 + 2])[0]
            if not v:
                continue
            tgt = ptr(v)
            if not (0x28600 <= tgt < 0x79000):
                continue
            hh = rom[tgt:tgt + 8]
            rec = dict(idx=i, ptr=v, at=tgt, at_hex=f"0x{tgt:06x}",
                       head8=hh.hex(), ver=hh[0], hdr=hh[1],
                       esz=hh[2], cnt=hh[3])
            blocks.append(rec)
            print(f"  [{i:>2d}] @0x{tgt:06x} ver=0x{hh[0]:02x} hdr={hh[1]} "
                  f"esz={hh[2]} cnt={hh[3]} -> {hh[1] + hh[2] * hh[3]} B")
            if hh[2] and hh[3] and hh[1] + hh[2] * hh[3] < 0x10000:
                for k in range(min(hh[3], 4)):
                    oo = tgt + hh[1] + k * hh[2]
                    print(f"         [{k}] @0x{oo:06x} "
                          f"{rom[oo:oo + min(hh[2], 16)].hex(' ')}")

    json.dump(dict(falcon_data=dict(base=FALCON, ver=ver, hdr=hd, esz=esz,
                                    count=n, entries=ents),
                   nvinit=dict(token=0x49, at=toks.get(0x49, {}).get("at"),
                               old_offset=NVINIT_ENTRY, blocks=blocks),
                   bit_tokens={f"0x{k:02x}": v for k, v in toks.items()}),
              open(f"{out}/q4_falcon.json", "w"), indent=1)
    print(f"\n  -> {out}/q4_falcon.json")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""P4: phan biet nen vs ma hoa trong 4 blob entropy cao. Tuan thu C3/I.

Dung: python3 fw_entropy.py ucodes_tu10x.bin FIRMWARE/
Khong brute-force khoa, khong trich xuat bi mat.
"""
import json
import lzma
import math
import sys
import zlib
from collections import Counter

OFFS = [0x2F00, 0x20F00, 0x3EF00, 0x5CF00, 0x7AF00, 0x98F00,
        0xB7C00, 0xD6700, 0xF5400, 0x113F00, 0x134300]


def ent(b):
    c = Counter(b)
    n = len(b)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def main():
    d = open(sys.argv[1], "rb").read()
    out = sys.argv[2].rstrip("/")
    blobs = []
    for k, off in enumerate(OFFS):
        end = OFFS[k + 1] if k + 1 < len(OFFS) else len(d)
        b = d[off:end]
        e = ent(b)
        rec = dict(idx=k, offset=off, offset_hex=f"0x{off:08x}", size=len(b),
                   entropy=round(e, 4),
                   nonzero=round(sum(1 for x in b if x) / len(b), 4))
        if e > 7.9:
            # --- thu 1: nen lai ---
            z = zlib.compress(b, 9)
            l = lzma.compress(b, preset=9)
            rec["zlib_ratio"] = round(len(b) / len(z), 4)
            rec["lzma_ratio"] = round(len(b) / len(l), 4)
            rec["compressible"] = len(z) < len(b) * 0.98
            # --- thu 2: histogram flatness ---
            c = Counter(b)
            vals = sorted(c.values(), reverse=True)
            rec["distinct_bytes"] = len(c)
            rec["max_byte_freq"] = round(vals[0] / len(b), 5)
            rec["expected_uniform"] = round(1 / 256, 5)
            # --- thu 3: tim 16 byte lap lai (IV/salt) ---
            head16 = b[:16]
            rec["head16"] = head16.hex()
            rec["head16_repeats_in_blob"] = b.count(head16)
        else:
            rec["text_like"] = sum(1 for x in b if 32 <= x < 127 or x in (9, 10, 13)) / len(b)
        blobs.append(rec)

    # --- thu 4: XOR cap blob cung kich thuoc (phat hien stream cipher) ---
    print("=== XOR cap blob cung kich thuoc ===")
    xor_pairs = []
    groups = {}
    for b in blobs:
        groups.setdefault(b["size"], []).append(b)
    for size, g in groups.items():
        if len(g) < 2:
            continue
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                a = d[g[i]["offset"]:g[i]["offset"] + size]
                c = d[g[j]["offset"]:g[j]["offset"] + size]
                x = bytes(p ^ q for p, q in zip(a, c))
                ex = ent(x)
                nz = sum(1 for v in x if v) / len(x)
                xor_pairs.append(dict(a=g[i]["idx"], b=g[j]["idx"], size=size,
                                      xor_entropy=round(ex, 4),
                                      xor_nonzero=round(nz, 4)))
                print(f"  blob[{g[i]['idx']}] ^ blob[{g[j]['idx']}] "
                      f"({size} B): entropy {ex:.4f}, nonzero {nz:.1%}")
    if not xor_pairs:
        print("  khong co cap cung kich thuoc")

    print(f"\n=== 4 blob entropy cao: kiem tra nen lai ===")
    print(f"  {'#':>3s} {'size':>8s} {'ent':>6s} {'distinct':>8s} "
          f"{'max_freq':>9s} {'zlib':>7s} {'lzma':>7s}  ket luan")
    for r in blobs:
        if "lzma_ratio" not in r:
            continue
        verdict = ("NEN DUOC -> khong ma hoa" if r["compressible"]
                   else "KHONG nen duoc -> nen hoac ma hoa")
        print(f"  {r['idx']:>3d} {r['size']:>8d} {r['entropy']:>6.3f} "
              f"{r['distinct_bytes']:>8d} {r['max_byte_freq']:>9.5f} "
              f"{r['zlib_ratio']:>7.3f} {r['lzma_ratio']:>7.3f}  {verdict}")

    print(f"\n=== 6 blob plaintext ===")
    for r in blobs:
        if "text_like" in r:
            print(f"  [{r['idx']:>2d}] 0x{r['offset']:06x} {r['size']:>8d} B  "
                  f"ent {r['entropy']:.3f}  text_like {r['text_like']:.1%}")

    # --- ket luan co so ---
    enc = [r for r in blobs if "lzma_ratio" in r]
    comp = [r for r in enc if r["compressible"]]
    print(f"\n=== KET LUAN P4 ===")
    print(f"  {len(enc)} blob entropy cao; {len(comp)} nen duoc, "
          f"{len(enc) - len(comp)} khong nen duoc")
    if not comp and enc:
        print("  -> ca 4 blob KHONG nen duoc => da nen hoac da ma hoa.")
        print("     KHONG the phan biet AES vs LZMA tu du lieu nay (C3).")
    json.dump(dict(file=sys.argv[1], size=len(d), blobs=blobs,
                   xor_pairs=xor_pairs,
                   conclusion=dict(high_entropy=len(enc),
                                   compressible=len(comp),
                                   aes_claim="KHONG ket luan AES (entropy khong du)")),
              open(f"{out}/firmware_inventory.json", "w"), indent=1)
    print(f"\n  -> {out}/firmware_inventory.json")


if __name__ == "__main__":
    main()
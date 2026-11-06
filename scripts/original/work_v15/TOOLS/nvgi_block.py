#!/usr/bin/env python3
"""P2: parse NVGI key/cert record block + so sanh 2 bank. Xuat VBIOS/.

Dung: python3 nvgi_block.py CMP40HX_ORIGINAL_1MB.bin VBIOS/
"""
import hashlib
import json
import struct
import sys

KEYBLK = 0x3000
KEYLEN = 0x4C0
REC = 32


def parse_records(rom, base=KEYBLK, n=KEYLEN // REC):
    out = []
    for i in range(n):
        o = base + i * REC
        b = rom[o:o + REC]
        if b == b"\xff" * REC:
            out.append(dict(idx=i, off=o, off_hex=f"0x{o:04x}", present=False))
            continue
        sig, ver = struct.unpack("<HH", b[0:4])
        f4 = struct.unpack("<I", b[4:8])[0]
        f8 = struct.unpack("<I", b[8:12])[0]
        fc = struct.unpack("<I", b[12:16])[0]
        h = b[16:32]
        out.append(dict(idx=i, off=o, off_hex=f"0x{o:04x}", present=True,
                        sig=f"0x{sig:04x}", ver=f"0x{ver:04x}",
                        f4=f4, f4_hex=f"0x{f4:08x}",
                        f8=f"0x{f8:08x}", fc=f"0x{fc:08x}",
                        flags_lo=fc & 0xFF, flags_hi=(fc >> 16) & 0xFF,
                        hash16=h.hex(),
                        hash32_first8=f"0x{struct.unpack('<Q', h[:8])[0]:016x}"))
    return out


def main():
    rom = open(sys.argv[1], "rb").read()
    out = sys.argv[2].rstrip("/")
    A = rom[0:KEYBLK + KEYLEN]
    B = rom[KEYBLK + KEYLEN:]

    # --- so sanh toan ROM: 2 ban sao? ---
    print("=== cau truc ROM 1 MiB ===")
    n = 0x79000
    a, b = rom[:n], rom[n:2 * n]
    diff = [i for i in range(n) if a[i] != b[i]]
    runs = []
    if diff:
        cur = [diff[0]]
        for x, y in zip(diff, diff[1:]):
            if y - x <= 128:
                cur.append(y)
            else:
                runs.append((cur[0], cur[-1]))
                cur = [y]
        runs.append((cur[0], cur[-1]))
    print(f"  ban 1: 0x00000..0x{n:05x} ({n:,} B)")
    print(f"  ban 2: 0x{n:05x}..0x{n * 2:05x} ({n:,} B)")
    print(f"  byte khac: {len(diff):,} / {n:,} = {100 * len(diff) / n:.3f}%")
    print(f"  cum khac: {[(f'0x{s:x}', f'0x{e:x}') for s, e in runs]}")
    print(f"  sau 0x{n * 2:x}: {0x100000 - n * 2:,} B toan 0xFF? "
          f"{set(rom[n * 2:]) == {0xFF}}")

    # --- records ---
    print(f"\n=== NVGI key block @0x{KEYBLK:04x}, {KEYLEN // REC} record x {REC} B ===")
    recs = parse_records(rom)
    recsB = parse_records(rom, KEYBLK + n)
    pres = [r for r in recs if r["present"]]
    print(f"  ban 1: {len(pres)}/{len(recs)} record co du lieu")
    print(f"  ban 2: {sum(1 for r in recsB if r['present'])}/{len(recsB)}")

    from collections import Counter
    vc = Counter(r["ver"] for r in pres)
    sg = Counter(r["sig"] for r in pres)
    print(f"  sig: {dict(sg)}")
    print(f"  ver: {dict(vc)}")
    print(f"\n  {'#':>3s} {'off':>7s} {'ver':>6s} {'f4':>12s} {'f8':>12s} "
          f"{'fl lo':>6s} {'fl hi':>6s}  hash16")
    for r in pres:
        print(f"  {r['idx']:>3d} {r['off_hex']:>7s} {r['ver']:>6s} "
              f"{r['f4_hex']:>12s} {r['f8']:>12s} {r['flags_lo']:>6d} "
              f"{r['flags_hi']:>6d}  {r['hash16'][:32]}")

    # --- kiem tra: hash16 co phai SHA256 cua gi khong? (thu vai vung) ---
    print(f"\n=== thu doi chieu hash16 voi cac vung ===")
    cands = {
        "rom[0:0x3000]": rom[0:0x3000],
        "rom[0x3400:0x79000]": rom[0x3400:0x79000],
        "legacy1": rom[0x28600:0x37A00],
        "EFI1": rom[0x37A00:0x48A00],
        "NPDS_E0_2": rom[0x54000:0x76800],
        "keyblock": rom[KEYBLK:KEYBLK + KEYLEN],
    }
    hits = 0
    for nm, data in cands.items():
        for algo in ("sha256", "sha1", "md5", "sha384"):
            h = hashlib.new(algo, data).digest()
            for i, r in enumerate(pres):
                if r["hash16"][:len(h) * 2] == h.hex() or r["hash16"] == h.hex()[:32]:
                    print(f"  KHOP record[{i}] = {algo}({nm})")
                    hits += 1
    print(f"  -> {hits} khop / {len(pres) * len(cands) * 4} phep thu")

    # --- f4 co phai timestamp? ---
    print(f"\n=== f4 co phai unix time? (thu mien hop ly) ===")
    import datetime
    ok = 0
    for r in pres:
        t = r["f4"]
        if 946684800 < t < 1893456000:      # 2000..2030
            ok += 1
    print(f"  {ok}/{len(pres)} record co f4 trong 2000..2030 -> "
          f"{'CO THE la timestamp' if ok > len(pres) * 0.5 else 'KHONG phai unix time'}")
    print(f"  vd f4 dau: {[r['f4'] for r in pres[:5]]}")

    # --- f8 = 0x1669xxxx: cung prefix? ---
    print(f"\n=== f8 prefix ===")
    pref = Counter(r["f8"][:6] for r in pres)
    print(f"  {dict(pref)}")
    print(f"  -> {'cung ho 0x16..' if len(pref) < 5 else 'nhieu ho'}")

    json.dump(dict(rom_size=len(rom),
                   layout=dict(bank1=dict(start=0, end=n),
                               bank2=dict(start=n, end=n * 2),
                               tail=dict(start=n * 2, end=0x100000,
                                         all_ff=set(rom[n * 2:]) == {0xFF}),
                               diff_bytes=len(diff),
                               diff_runs=[[s, e] for s, e in runs]),
                   keyblock=dict(base=f"0x{KEYBLK:04x}", length=KEYLEN,
                                 record_size=REC, records=recs,
                                 records_bank2=recsB,
                                 summary=dict(sig=dict(sg), ver=dict(vc),
                                              present=len(pres))),
                   hash_match_attempts=dict(candidates=list(cands),
                                            algorithms=["sha256", "sha1", "md5",
                                                        "sha384"],
                                            hits=hits)),
              open(f"{out}/vbios_crossrefs.json", "w"), indent=1)
    print(f"\n  -> {out}/vbios_crossrefs.json")


if __name__ == "__main__":
    main()
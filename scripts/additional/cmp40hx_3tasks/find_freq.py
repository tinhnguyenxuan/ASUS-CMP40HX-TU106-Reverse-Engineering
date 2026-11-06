#!/usr/bin/env python3
"""Tim phuong trinh tan so + giai VFE_VAR dung stride 25.

Dung: python3 find_freq.py CMP40HX_ORIGINAL_1MB.bin
"""
import struct
import sys

VFE_HDR = 0x5649C
VFE_SLOT = 0x56699
STRIDE = 24
VAR_ESZ = 25
VAR_CNT = 20


def slots(rom):
    out = []
    for i in range(150):
        o = VFE_SLOT + i * STRIDE
        b = rom[o:o + STRIDE]
        out.append(dict(
            i=i, off=o, type=b[0], var=b[1], next=b[2], flags=b[23],
            lo=struct.unpack("<f", b[3:7])[0],
            hi=struct.unpack("<f", b[7:11])[0],
            c0=struct.unpack("<f", b[11:15])[0],
            c1=struct.unpack("<f", b[15:19])[0],
            c2=struct.unpack("<f", b[19:23])[0],
        ))
    return out


def main():
    rom = open(sys.argv[1], "rb").read()

    # ---------- VFE_VAR dung stride 25 ----------
    print("=" * 88)
    print("VFE_VAR: header 0x30 0x09 esz=0x19=25 cnt=0x14=20  ->  9+25*20 = 509")
    print("=" * 88)
    print(f"  header 9B @0x{VFE_HDR:06x}: {rom[VFE_HDR:VFE_HDR + 9].hex(' ')}")
    used = {s["var"] for s in slots(rom)} - {255}
    print(f"  var_idx dung: {sorted(used)}\n")
    print(f"  {'var':>3s} {'off':>9s}  25B hex")
    for v in range(VAR_CNT):
        o = VFE_HDR + 9 + v * VAR_ESZ
        b = rom[o:o + VAR_ESZ]
        fl = struct.unpack("<6f", b[:24])
        good = [round(x, 2) for x in fl if x == x and 0.001 < abs(x) < 3e6]
        mark = " *" if v in used else "  "
        print(f" {v:>3d} 0x{o:06x}{mark} {b.hex(' ')}")
        if good:
            print(f"            float hop ly: {good}")

    # ---------- tim tan so ----------
    print("\n" + "=" * 88)
    print("TIM TAN SO 1890 / 1905 / 2100 trong toan ROM (moi dang ma hoa)")
    print("=" * 88)
    forms = {
        "u16 MHz": lambda m: struct.pack("<H", m),
        "u32 MHz": lambda m: struct.pack("<I", m),
        "u32 kHz": lambda m: struct.pack("<I", m * 1000),
        "u32 Hz": lambda m: struct.pack("<I", m * 1000000),
        "f32 MHz": lambda m: struct.pack("<f", float(m)),
        "u16 x2 MHz": lambda m: struct.pack("<H", m * 2),
        "u16 x10": lambda m: struct.pack("<H", m // 10),
        "u16 0x3fff masked": lambda m: struct.pack("<H", m | 0x4000),
    }
    for mhz in (1650, 1890, 1905, 1965, 2025, 2070, 2100):
        out = []
        for nm, f in forms.items():
            pat = f(mhz)
            locs = [i for i in range(0, len(rom) - len(pat)) if rom[i:i + len(pat)] == pat]
            if locs:
                out.append(f"{nm}@{[hex(x) for x in locs[:4]]}x{len(locs)}")
        if out:
            print(f"  {mhz} MHz: {' | '.join(out)}")

    # ---------- slot nao la tan so ----------
    print("\n" + "=" * 88)
    print("SLOT nao cho y trong dai 1000..2500 (MHz) khi x = dien ap mV 693..1125")
    print("=" * 88)
    sc = slots(rom)
    for s in sc:
        if s["c1"] == 0 and s["c2"] == 0:
            continue
        ys = [s["c0"] + s["c1"] * x + s["c2"] * x * x for x in (693.5, 800, 1068.75, 1125)]
        if all(500 < y < 3000 for y in ys):
            print(f"  slot[{s['i']:>3d}] var={s['var']:>3d} type={s['type']} "
                  f"lo={s['lo']:.1f} hi={s['hi']:.1f}")
            print(f"    y = {s['c0']:.4f} + {s['c1']:.6f}x + {s['c2']:.9f}x^2")
            print(f"    x=693.5 -> {ys[0]:.2f} | 800 -> {ys[1]:.2f} | "
                  f"1068.75 -> {ys[2]:.2f} | 1125 -> {ys[3]:.2f}")

    # ---------- nghich dao: x nao cho y=1890 ----------
    print("\n" + "=" * 88)
    print("NGHICH DAO: slot nao cho y=1890 voi x trong dai hop ly")
    print("=" * 88)
    for s in sc:
        if s["c2"] == 0 and s["c1"] == 0:
            continue
        for tgt in (1890, 1905, 2100):
            if s["c2"] != 0:
                disc = s["c1"] ** 2 - 4 * s["c2"] * (s["c0"] - tgt)
                if disc < 0:
                    continue
                for sg in (1, -1):
                    x = (-s["c1"] + sg * disc ** 0.5) / (2 * s["c2"])
                    if s["lo"] - 1 <= x <= s["hi"] + 1 and 0 < x < 3000:
                        print(f"  y={tgt} tai slot[{s['i']:>3d}] var={s['var']:>3d} "
                              f"x={x:.1f} (clamp [{s['lo']:.0f},{s['hi']:.0f}])")
            elif s["c1"] != 0:
                x = (tgt - s["c0"]) / s["c1"]
                if s["lo"] - 1 <= x <= s["hi"] + 1 and 0 < x < 6000:
                    print(f"  y={tgt} tuyen REDACTED_USER tai slot[{s['i']:>3d}] var={s['var']:>3d} "
                          f"x={x:.1f} (clamp [{s['lo']:.0f},{s['hi']:.0f}])")

    # ---------- chuoi tu selector ----------
    print("\n" + "=" * 88)
    print("CHUOI phu thuoc tu 4 selector (REL/ALT/OV/VMIN)")
    print("=" * 88)
    sel = rom[0x2D384:0x2D38A]
    print(f"  selector @0x2D384 = {sel.hex(' ')}")
    for k, nm in enumerate(["REL", "ALT", "OV"]):
        cur, chain = sel[k], []
        while cur < 150 and cur not in chain and len(chain) < 15:
            chain.append(cur)
            cur = sc[cur]["next"]
        parts = []
        for c in chain:
            s = sc[c]
            parts.append(f"[{c}]" + ("const" if s["c1"] == 0 and s["c2"] == 0 else "f(x)"))
        print(f"  {nm:<4s} -> {' -> '.join(parts)}")


if __name__ == "__main__":
    main()
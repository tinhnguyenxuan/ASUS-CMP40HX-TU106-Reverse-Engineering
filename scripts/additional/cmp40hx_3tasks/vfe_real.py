#!/usr/bin/env python3
"""Parser VFE chuan — offset lay tu `nvbios fields` (ground truth), khong doan.

nvbios fields cho:
  nvvdd_rel_equation_max_mv  equation_offset = 353945 = 0x56699
  nvvdd_alt_equation_max_mv  equation_offset = 353969 = 0x566B1   (+24)
  nvvdd_ov_equation_max_mv   equation_offset = 354017 = 0x566E1   (+48)
  nvvdd_vmin_mv              equation_offset = 354041 = 0x566F9   (+24)
  *_selector_index           offset          = 185220 = 0x2D384

=> base 0x56699, stride 24, float KHONG align 4.

Layout slot 24 B:
  +0   u8   type      1 = constant/quadratic, 4 = opaque
  +1   u8   var_idx
  +2   u8   next      0xff = end of chain
  +3   f32  clamp_lo
  +7   f32  clamp_hi
  +11  f32  c0
  +15  f32  c1
  +19  f32  c2
  +23  u8   flags

y = c0 + c1*x + c2*x^2, clamp vao [clamp_lo, clamp_hi].

Dung: python3 vfe_real.py CMP40HX_ORIGINAL_1MB.bin [--all]
"""
import struct
import sys

BASE = 0x56699
STRIDE = 24
SEL = 0x2D384
COUNT = 150


def main():
    rom = open(sys.argv[1], "rb").read()
    show_all = "--all" in sys.argv

    sel = rom[SEL:SEL + 6]
    print(f"selector @0x{SEL:06x} = {sel.hex(' ')}")
    print(f"  REL   -> slot {sel[0]}")
    print(f"  ALT   -> slot {sel[1]}")
    print(f"  OV    -> slot {sel[2]}")
    print(f"  (byte 3..5 = {sel[3:].hex(' ')} — khong phai VMIN)")
    # VMIN lay tu nvbios: equation_offset 354041 = 0x566F9 -> slot 4
    # (rail row byte 9, khong nam trong selector array nay)
    VMIN_SLOT = (354041 - BASE) // STRIDE
    print(f"  VMIN  -> slot {VMIN_SLOT} (tu equation_offset 354041)")

    def slot(i):
        o = BASE + i * STRIDE
        b = rom[o:o + STRIDE]
        return dict(
            i=i, off=o, type=b[0], var=b[1], next=b[2],
            lo=struct.unpack("<f", b[3:7])[0],
            hi=struct.unpack("<f", b[7:11])[0],
            c0=struct.unpack("<f", b[11:15])[0],
            c1=struct.unpack("<f", b[15:19])[0],
            c2=struct.unpack("<f", b[19:23])[0],
            flags=b[23],
        )

    # ---- kiem chung 4 hang so dien ap ----
    print("\n=== kiem chung (nvbios fields lam chuan) ===")
    checks = [(0, 1068750.0, "REL"), (1, 1093750.0, "ALT"),
              (3, 1125000.0, "OV"), (4, 693500.0, "VMIN")]
    ok = 0
    for idx, want, nm in checks:
        s = slot(idx)
        good = abs(s["c0"] - want) < 1.0
        ok += good
        print(f"  slot{idx} {nm:<5s} c0={s['c0']:>12.1f} "
              f"want={want:>12.1f} {'OK' if good else 'SAI'}")
    assert ok == 4, f"chi {ok}/4 hang so dung"

    # ---- thong ke ----
    eqs = [slot(i) for i in range(COUNT)]
    const = [e for e in eqs if e["c1"] == 0 and e["c2"] == 0]
    lin = [e for e in eqs if e["c1"] != 0 and e["c2"] == 0]
    quad = [e for e in eqs if e["c2"] != 0]
    print(f"\n=== {COUNT} slot ===")
    print(f"  hang so     : {len(const)}")
    print(f"  tuyen REDACTED_USER  : {len(lin)}")
    print(f"  bac 2       : {len(quad)}")
    types = {}
    for e in eqs:
        types[e["type"]] = types.get(e["type"], 0) + 1
    print(f"  type        : {types}")
    vars_ = {}
    for e in eqs:
        vars_[e["var"]] = vars_.get(e["var"], 0) + 1
    print(f"  var dung    : {sorted(vars_.items(), key=lambda x: -x[1])[:8]}")

    # ---- bang chinh ----
    if show_all:
        print(f"\n{'#':>4s} {'type':>4s} {'var':>4s} {'next':>4s} {'lo':>12s} "
              f"{'hi':>12s} {'c0':>14s} {'c1':>12s} {'c2':>12s}")
        print("-" * 100)
        for e in eqs:
            lo = f"{e['lo']:.1f}" if abs(e['lo']) < 1e12 else "-inf"
            hi = f"{e['hi']:.1f}" if abs(e['hi']) < 1e12 else "+inf"
            print(f"{e['i']:>4d} {e['type']:>4d} {e['var']:>4d} "
                  f"0x{e['next']:02x} {lo:>12s} {hi:>12s} "
                  f"{e['c0']:>14.1f} {e['c1']:>12.4f} {e['c2']:>12.6f}")

    # ---- chuoi tu selector ----
    print(f"\n=== chuoi tu selector ===")
    for i, n in enumerate(["REL", "ALT", "OV"]):
        cur = sel[i]
        chain = []
        for _ in range(12):
            if cur >= COUNT or cur in chain:
                break
            chain.append(cur)
            cur = eqs[cur]["next"]
        desc = []
        for c in chain:
            e = eqs[c]
            if e["c1"] == 0 and e["c2"] == 0:
                desc.append(f"[{c}]={e['c0']:.0f}uV")
            else:
                desc.append(f"[{c}]=f(x)")
        print(f"  {n:<5s}: {' -> '.join(desc)}")

    print(f"\n[ok] base 0x{BASE:06x}, stride {STRIDE}, {COUNT} slot, "
          f"4/4 hang so khop nvbios fields")


if __name__ == "__main__":
    main()
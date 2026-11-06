#!/usr/bin/env python3
"""P9d: host co DOC duoc vung WPR2 qua BAR1 khong? (CHI DOC)

WPR = "Write Protected Region" -- ten noi len chi bao ve GHI.
Chua ai kiem tra host read co bi chan khong.

Neu doc duoc -> dump duoc GSP-RM dang chay tu VRAM, doi chieu voi
gsp_tu10x.bin (22.9 MB).

Phuong phap: doc cua so 4 KB qua /sys/.../resource1 (BAR1, 64 GB).
Moi lan doc kiem tra card con song truoc va sau.

Vung thu:
  VRAM 0x00000000   doi chung 1 (dau VRAM)
  VRAM 0x01000000   doi chung 2 (16 MB)
  VRAM 0x01F78200   WPR2 LO   <-- muc tieu
  VRAM 0x01F7E000   WPR2 HI
  VRAM 0x01FFEE00   WPR2 alt LO
  VRAM 0x1FFFFFF0   WPR2 alt HI
"""
import mmap
import os
import struct
import subprocess
import sys
from collections import Counter

BAR1 = "/sys/bus/pci/devices/0000:03:00.0/resource1"
BAR1_SIZE = 64 << 30
WIN = 4096

ZONES = [
    ("CTRL_head",       0x00000000, "doi chung - dau VRAM"),
    ("CTRL_16M",        0x01000000, "doi chung - 16 MB"),
    ("WPR2_LO",         0x01F78200, "WPR2 start (23.75 KB region)"),
    ("WPR2_mid",        0x01F7B000, "WPR2 giua"),
    ("WPR2_HI",         0x01F7E000, "WPR2 end"),
    ("WPR2_alt_LO",     0x01FFEE00, "WPR2 alt start (~480 MB)"),
    ("WPR2_alt_HI",     0x1FFFFFF0, "WPR2 alt end"),
    ("CTRL_512M",       0x20000000, "doi chung - 512 MB"),
]


def card_alive():
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=clocks.sm,power.draw",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10)
        return r.returncode == 0 and r.stdout.strip()
    except Exception:
        return None


def is_poison(v):
    return (v & 0xFFFF0000) == 0xBADF0000 or v == 0xBAD00100


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "p9_wpr_read.json"
    print("=== P9d: host doc duoc WPR2 qua BAR1? (read-only) ===")
    a = card_alive()
    print(f"  card truoc thu: {a}")
    if not a:
        print("  CARD KHONG PHAN HOI -> DUNG, khong thu")
        return 1

    if not os.path.exists(BAR1):
        print(f"  khong co {BAR1}")
        return 1
    sz = os.path.getsize(BAR1)
    print(f"  BAR1 size: {sz} B ({sz/2**30:.1f} GiB)")

    fd = os.open(BAR1, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, min(sz, 1 << 30), mmap.MAP_SHARED, mmap.PROT_READ)
    print(f"  mmap {min(sz,1<<30)/2**30:.1f} GiB OK\n")

    res = []
    print(f"  {'vung':<14s} {'offset':>10s}  {'nonzero':>8s} {'entropy':>8s} "
          f"{'poison':>7s}  {'distinct u32':>12s}  {'top value':>12s}")
    for nm, off, note in ZONES:
        try:
            buf = bytes(mm[off:off + WIN])
        except Exception as e:
            print(f"  {nm:<14s} 0x{off:08x}  LOI: {e}")
            res.append(dict(name=nm, off=f"0x{off:08x}", error=str(e)))
            continue
        nz = sum(1 for b in buf if b)
        ctr = Counter(buf)
        ent = -sum((c / WIN) * __import__("math").log2(c / WIN)
                   for c in ctr.values() if c)
        vz = [struct.unpack_from("<I", buf, k)[0] for k in range(0, WIN, 4)]
        vc = Counter(vz)
        pz = sum(1 for v in vz if is_poison(v) or v == 0xFFFFFFFF)
        top = vc.most_common(1)[0]
        print(f"  {nm:<14s} 0x{off:08x}  {nz:5d}/{WIN} {ent:8.3f} "
              f"{pz:5d}/{WIN//4}  {len(vc):12d}  0x{top[0]:08x} x{top[1]}")
        res.append(dict(name=nm, off=f"0x{off:08x}", note=note, nonzero=nz,
                        entropy=round(ent, 3), poison_u32=pz,
                        distinct_u32=len(vc), top=f"0x{top[0]:08x}",
                        top_n=top[1], data=buf[:64].hex()))
        # kiem tra card sau moi vung
        a2 = card_alive()
        if not a2:
            print("  !!! CARD MAT PHAN HOI SAU KHI DOC VUNG NAY -> DUNG NGAY")
            mm.close()
            os.close(fd)
            json.dump(dict(zones=res, aborted_at=nm,
                           card_alive_after=False), open(out, "w"), indent=1)
            return 2
    mm.close()
    os.close(fd)
    a3 = card_alive()
    print(f"\n  card sau thu: {a3}")

    # --- phan tich ---
    print("\n=== KET LUAN ===")
    ctrl = [r for r in res if r["name"].startswith("CTRL")]
    wpr = [r for r in res if r["name"].startswith("WPR2")]
    ctrl_ok = any(r.get("nonzero", 0) > 0 and r.get("distinct_u32", 0) > 8
                  for r in ctrl)
    wpr_data = [r for r in wpr
                if r.get("nonzero", 0) > 0 and r.get("distinct_u32", 1) > 8]
    print(f"  doi chung co du lieu that : {ctrl_ok}")
    print(f"  vung WPR2 doc duoc du lieu : {len(wpr_data)}/{len(wpr)}")
    if ctrl_ok and wpr_data:
        print("  -> WPR KHONG chan host DOC. Day la phuc hoi duoc GSP-RM tu VRAM.")
    elif ctrl_ok and not wpr_data:
        print("  -> WPR2 chan host doc (poison/0xFF/zero). Write-protect co hieu luc.")
    else:
        print("  -> doi chung khong co du lieu -> khong ket luan duoc gi.")

    import json
    json.dump(dict(zones=res, card_before=a, card_after=a3,
                   conclusion=("host_doc_duoc_WPR2" if (ctrl_ok and wpr_data)
                               else "WPR2_chan_doc" if ctrl_ok
                               else "khong_ket_luan")),
              open(out, "w"), indent=1)
    print(f"  -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

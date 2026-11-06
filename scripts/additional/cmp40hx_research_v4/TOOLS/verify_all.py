#!/usr/bin/env python3
"""Self-check toan bo du lieu nghien cuu. Chay: python3 TOOLS/verify_all.py"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
FAIL = []


def ck(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAIL.append(name)


def L(*a):
    try:
        return json.load(open(P(*a)))
    except Exception as e:
        return {"_err": str(e)}


def main():
    print("=== 1. FUSE ===")
    f = L("FUSE", "fuse2.json")
    regs = {int(k): v for k, v in f.get("regs", {}).items()}
    poison = set(f.get("poison", []))
    wd = {k: v for k, v in regs.items() if v not in poison and v != 0}
    ck("fuse dump 3072 word", len(regs) == 3072, len(regs))
    ck("fuse co du lieu 352", len(wd) == 352, len(wd))
    ck("fuse+0x4D8 = 1F0B", regs.get(0x4D8) == 0x1F0B, hex(regs.get(0x4D8, 0)))
    ck("fuse+0x56C = 1F4B", regs.get(0x56C) == 0x1F4B)
    ck("fuse+0x650 = 0x4001F", regs.get(0x650) == 0x4001F)
    ck("NVDEC_DISABLE = 0", regs.get(0x378) == 0)
    ck("GSP_DEBUG_DIS = 1", regs.get(0x74C) == 1)
    ck("DISPLAY ENABLE = 1", regs.get(0xC04) == 1)
    ck("GPC = 0x38", regs.get(0xC1C) == 0x38)
    ck("trang 0x2000 toan poison",
       all(regs.get(0x2000 + i, 0) in poison for i in range(0, 0x1000, 4)))

    print("\n=== 2. MMIO ===")
    m = L("MMIO", "mmio.json")
    mr = m.get("registers", {})
    ck("boot0 = 0x166000A1", m.get("boot0") == "0x166000a1", m.get("boot0"))
    lo = mr.get("NV_PFB_PRI_MMU_WPR2_ADDR_LO", {}).get("value")
    hi = mr.get("NV_PFB_PRI_MMU_WPR2_ADDR_HI", {}).get("value")
    ck("WPR2 lo = 0x1F7E000", lo == 0x1F7E000, hex(lo or 0))
    ck("WPR2 hi = 0x1FFEE00", hi == 0x1FFEE00, hex(hi or 0))
    ck("xve map = 1f0b10de",
       mr.get("NV_PCFG_XVE_REGISTER_MAP_START_OFFSET", {}).get("value") == 0x1F0B10DE)
    nd = sum(1 for x in mr.values() if x["state"] == "data")
    ck("33 register doc duoc", nd == 33, nd)

    print("\n=== 3. VBIOS ===")
    rom = open(P("outputs", "CMP40HX_ORIGINAL_1MB.bin"), "rb").read()
    ck("ROM 1 MiB", len(rom) == 1048576)
    n = 0x79000
    ck("NVGIf @0x79000", rom[n:n + 5] == b"NVGIf")
    diff = [i for i in range(n) if rom[i] != rom[n + i]]
    ck("2 ban sao khac 1212 byte", len(diff) == 1212, len(diff))
    ck("cum khac 0x3000..0x34BF", min(diff) == 0x3000 and max(diff) == 0x34BF,
       f"{min(diff):#x}..{max(diff):#x}")
    ck("key block ban1 co du lieu", rom[0x3000] != 0xFF)
    ck("key block ban2 toan 0xFF", set(rom[n + 0x3000:n + 0x34C0]) == {0xFF})
    ck("38 record x 32", (0x34C0 - 0x3000) // 32 == 38)

    print("\n=== 4. GSP-RM ===")
    g = L("GSP", "gsp_functions.json")
    ck("340 entry that", g.get("real_entries") == 340, g.get("real_entries"))
    ck("60 bang", g.get("real_tables") == 60, g.get("real_tables"))
    names = {e["name"] for t in g.get("tables", []) for e in t["entries"]}
    ck("co RELIABILITY_NVVDD", "RELIABILITY_NVVDD" in names)
    ck("co VMIN_NVVDD_1", "VMIN_NVVDD_1" in names)
    ck("co UNLOAD_DRIVER_VOLTAGE_RAIL_0", "UNLOAD_DRIVER_VOLTAGE_RAIL_0" in names)
    ck("co MCLK_LIMIT", "MCLK_LIMIT" in names)
    ck("KHONG co RMClkVfOverride",
       "RMClkVfOverride" not in names)
    # kiem tra khong con fragment
    frag = [x for x in names if x.startswith(("CONTROLLER_", "ER_", "M_GRP", "OWER"))]
    ck("khong con fragment chuoi", len(frag) == 0, frag[:5])

    print("\n=== 5. FIRMWARE ===")
    fw = L("FIRMWARE", "firmware_inventory.json")
    ck("11 blob", len(fw.get("blobs", [])) == 11)
    up = P("outputs", "ucodes_tu10x.bin")
    if not os.path.exists(up):
        print("  SKIP  blob[6]/blob[8]  (ucodes_tu10x.bin khong co trong goi; "
              "8.8 MB, tai lai tu /lib/firmware/nvidia/615.78.08/)")
        print("  SKIP  blob cuoi")
        d = None
    else:
        d = open(up, "rb").read()
    if d is not None:
        OFFS = [0x2F00, 0x20F00, 0x3EF00, 0x5CF00, 0x7AF00, 0x98F00,
                0xB7C00, 0xD6700, 0xF5400, 0x113F00, 0x134300]
        b6 = d[OFFS[6]:OFFS[7]]
        b8 = d[OFFS[8]:OFFS[9]]
        nd8 = sum(1 for i in range(len(b6)) if b6[i] != b8[i])
        ck("blob[6] vs blob[8] khac 24 byte", nd8 == 24, nd8)
        ck("blob cuoi ket thuc dung file", OFFS[-1] + len(d) - OFFS[-1] == len(d))

    print("\n=== 6. PCIe / Memory ===")
    p = L("PCIE", "pcie_map.json")
    ck("BAR1 = 64G", any("64G" in r for r in p.get("regions", [])))
    ck("link runtime Gen1", "2.5 GT/s" in str(p.get("current_link_speed")))
    ck("link cap Gen2", "5GT/s" in str(p.get("capabilities")))
    mem = L("MEMORY", "memory_registers.json")
    ck("Reserved 389 MiB", "389 MiB" in str(mem.get("smq")))

    print("\n=== 7. Phat hien vong Q2-Q9 ===")
    disp = L("TOPOLOGY", "display_probe.json")
    c = disp.get("conclusion", {})
    ck("display 0 word du lieu", c.get("display_data_words") == 0,
       c.get("display_data_words"))
    ck("doi chung co du lieu", c.get("control_data_words", 0) > 0,
       c.get("control_data_words"))
    q3 = L("PCIE", "q3_link.json")
    lk = q3.get("link", {})
    ck("card cap 5GT/s", "5GT/s" in str(lk.get("card", {}).get("LnkCap")))
    ck("root cap 8GT/s", "8GT/s" in str(lk.get("root", {}).get("LnkCap")))
    ck("ca 2 dau target 5GT/s",
       "5GT/s" in str(lk.get("card", {}).get("LnkCtl2"))
       and "5GT/s" in str(lk.get("root", {}).get("LnkCtl2")))
    ck("ca 2 dau runtime 2.5GT/s",
       "2.5GT/s" in str(lk.get("card", {}).get("LnkSta"))
       and "2.5GT/s" in str(lk.get("root", {}).get("LnkSta")))
    q4 = L("VBIOS", "q4_falcon.json")
    fd = q4.get("falcon_data", {})
    ck("FALCON_DATA esz=6 cnt=16", fd.get("esz") == 6 and fd.get("count") == 16)
    import struct as _st
    nz = sum(1 for e in fd.get("entries", [])
             if _st.unpack("<I", bytes.fromhex(e["raw"])[2:6])[0])
    ck("FALCON_DATA 7 entry co du lieu", nz == 7, nz)
    nv = q4.get("nvinit", {}).get("blocks", [])
    ck("NVINIT 9 con tro hop le", len(nv) == 9, len(nv))
    q8 = L("FIRMWARE", "q8_blobdiff.json")
    ck("blob6/8 khac 24 byte", q8.get("diff_count") == 24, q8.get("diff_count"))
    runs = q8.get("runs", [])
    ck("co 4 cum khac", len(runs) == 4, len(runs))
    ck("cum 20 B la build timestamp ASCII",
       any("Dec 31 2024" in bytes.fromhex(r["hex6"]).decode("latin1", "ignore")
           for r in runs))
    q5 = L("FUSE", "q5_hash.json")
    ck("hash tren fuse 0 khop", q5.get("hits") == 0)

    q1 = L("GSP", "q1_lui.json")
    ck("Q1: tim thay LUI khop base", len(q1.get("hits", [])) == 8,
       len(q1.get("hits", [])))
    ck("Q1: 381665 LUI trong 17 MB text", q1.get("lui_in_text") == 381665,
       q1.get("lui_in_text"))
    q1d = L("GSP", "q1_disasm.json")
    tot = q1d.get("total_decoded", 0)
    inv = q1d.get("invalid", 0)
    ck("Q1: disasm capstone <5% invalid", tot > 500 and inv / max(tot, 1) < 0.05,
       f"{inv}/{tot}")

    print("\n=== 8. Database ===")
    u = L("UNKNOWN_DATABASE.json")
    c = L("COVERAGE.json")
    q = L("RESEARCH_QUEUE.json")
    ck("UNKNOWN co items", len(u.get("items", [])) >= 30)
    ck("COVERAGE co FUSE/MMIO", "FUSE" in c and "MMIO" in c)
    ck("QUEUE co muc", len(q.get("queue", [])) >= 5)

    print(f"\n=== {'TAT CA PASS' if not FAIL else f'{len(FAIL)} FAIL: {FAIL}'} ===")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
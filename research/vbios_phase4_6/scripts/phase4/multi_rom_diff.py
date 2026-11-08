#!/usr/bin/env python3
"""Phase 4H tool: semantic field diff across N TU106 ROMs.

    python3 scripts/phase4/multi_rom_diff.py a.rom b.rom [c.rom ...] [-o out.csv]

Compares by *structure* (P2 slot -> parser -> field), never by file offset, so
a ROM with a different table order still compares correctly. Columns are one
per ROM; a final "varies" column says whether the field differs across them.

Purpose: once more TU106 ROMs exist, this answers "which fields track model /
PCB / VRAM vendor / PCIe policy / TDP" without re-deriving anything.

ROMs are third-party firmware. Do not commit them; this tool takes paths.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from tu106_vbios import load  # noqa: E402


def fields(rom):
    """Yield (group, name, value) tuples. Values are strings for CSV."""
    out = {}

    pci = rom.pci()
    out[("PCI", "device_id")] = f"{pci['device']:#06x}"
    out[("PCI", "class")] = f"{pci['class_code']:#08x}"
    out[("PCI", "legacy_len")] = f"{pci['images'][0]['image_len']:#x}"

    pb = rom.power_budget()
    out[("PWR_BUDGET", "hlen/esz/cnt")] = f"{pb['hlen']}/{pb['entry_len']}/{pb['count']}"
    for e in pb["entries"]:
        if e["class_id"] == 1:
            out[("PWR_BUDGET", "gpu_limit_min")] = str(e["limit_min"])
            out[("PWR_BUDGET", "gpu_limit_rated")] = str(e["limit_rated"])
            out[("PWR_BUDGET", "gpu_limit_max")] = str(e["limit_max"])
    out[("PWR_BUDGET", "tgp_idx")] = str(pb["tgp_idx"])
    out[("PWR_BUDGET", "viol")] = f"{pb['viol_len']}x{pb['viol_cnt']}"

    pt = rom.power_topology()
    out[("PWR_TOPO", "entries")] = str(pt["count"])
    out[("PWR_TOPO", "first_rail")] = f"{pt['entries'][0]['pwr_rail']:#04x}"

    ck = rom.clocks_v35()
    if ck:
        out[("CLOCKS35", "usage")] = "".join(str(r["usage"]) for r in ck["rows"])

    pf = rom.perf_v60()
    out[("PSTATE", "levels")] = ",".join(f"{e['pstate']:02x}" for e in pf["entries"])
    live = [e for e in pf["entries"] if not e["skip"]]
    if live:
        for s in live[-1]["subs"]:
            out[("PSTATE_TOP", f"{s['domain']}_nom")] = str(s["nom"])
            out[("PSTATE_TOP", f"{s['domain']}_max")] = str(s["mx"])
    out[("PSTATE", "pcie_idx")] = ",".join(
        str(e["pcie_idx"]) for e in live)

    bc = rom.power_base_clock()
    out[("PBC", "base")] = str(bc["entries"][0]["clocks"][0])
    out[("PBC", "boost")] = str(bc["entries"][2]["clocks"][0])
    # full 10-byte tail: 2 bytes would report "identical" while CMP has
    # ff*10 and GeForce 03 09 ff*8 (see TU106_POWER_THERMAL_REVERSE.md §6)
    out[("PBC", "hdr_tail")] = rom.hex(bc["hdr"] + 9, 10)

    mc = rom.mem_clock_table()
    out[("MEMCLK", "last_max")] = str(mc["entries"][-1]["max_mhz"])

    mt = rom.mem_tweak_table()
    for strap in (0, 14, 15):
        e = mt["entries"][strap]
        out[("MEMTWEAK", f"s{strap}_RFC")] = str(e["RFC"])
        out[("MEMTWEAK", f"s{strap}_CL")] = str(e["CL"])
        out[("MEMTWEAK", f"s{strap}_REFRESH")] = str(e["REFRESH"])

    tpr = rom.thermal_policy()
    out[("THERMAL", "hdr_tail")] = tpr["hdr_tail"].hex(" ")

    lg = rom.lpwr_gr()
    out[("LPWR_GR", "e0")] = lg["entries"][0]["raw"].hex()

    lp = rom.lpwr_pcie()
    out[("LPWR_PCIE", "e0")] = lp["entries"][0]["raw"].hex()

    ps = rom.pcie_settings_script()
    out[("PCIE_SCRIPT", "writes")] = ";".join(
        f"{o['addr']:#x}={o.get('data', 0):#x}" for o in ps["ops"] if "addr" in o)
    out[("PCIE_SCRIPT", "cond")] = ",".join(
        str(o["cond"]) for o in ps["ops"] if o["op"] == "CONDITION")

    return out


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    out_path = None
    if "-o" in argv:
        out_path = argv[argv.index("-o") + 1]
        args = [a for a in args if a != out_path]
    if len(args) < 2:
        print(__doc__)
        return 2

    roms = [(os.path.basename(p)[:12], load(p, os.path.basename(p))) for p in args]
    data = {name: fields(rom) for name, rom in roms}

    keys = []
    for d in data.values():
        for k in d:
            if k not in keys:
                keys.append(k)
    keys.sort()

    rows = []
    for k in keys:
        vals = [data[n].get(k, "") for n, _ in roms]
        rows.append([k[0], k[1]] + vals + ["yes" if len(set(vals)) > 1 else "no"])

    head = ["group", "field"] + [n for n, _ in roms] + ["varies"]
    if out_path:
        with open(out_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(rows)
        print(f"{out_path}: {len(rows)} fields, "
              f"{sum(1 for r in rows if r[-1] == 'yes')} vary")
    else:
        w = csv.writer(sys.stdout)
        w.writerow(head)
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

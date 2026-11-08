#!/usr/bin/env python3
"""Write data/PHASE4_FIELD_EVIDENCE.csv.

Every row is one claim about one field: where the evidence came from, which
level it reaches, and what would raise or lower it. Levels are the same four
used everywhere else in this repo.

    python3 scripts/phase4/evidence.py

ponytail: rows are hand-written, not derived from the parser, because the point
of the table is the *justification*, and that is not in the ROM.
"""
import csv
import os

HEAD = ["id", "phase", "subject", "field_or_register", "value_cmp",
        "value_2060s", "value_2070", "source", "url_or_symbol", "level",
        "would_be_promoted_by"]

# level: PROVEN | STRONGLY SUPPORTED | HYPOTHESIS | UNKNOWN
ROWS = [
    ("E01", "4D", "POWER BUDGET", "e2.limit_min", "110000", "125000", "125000",
     "ROM + nvgpu pwr_policy_3x_entry_struct.limit_min", "bios.h:809",
     "STRONGLY SUPPORTED", "RM/GSP-RM consumer, or a 4th ROM with a known min"),
    ("E02", "4D", "POWER BUDGET", "e2.limit_rated", "184000", "184000", "185000",
     "ROM + nvgpu pwr_policy_3x_entry_struct.limit_rated", "bios.h:809",
     "STRONGLY SUPPORTED", "nvidia-smi default_limit on the real card"),
    ("E03", "4D", "POWER BUDGET", "e2.limit_max", "220000", "220000", "222000",
     "ROM + nvgpu pwr_policy_3x_entry_struct.limit_max", "bios.h:809",
     "STRONGLY SUPPORTED", "nvidia-smi max_limit on the real card"),
    ("E04", "4D", "POWER BUDGET", "table extent 44+20*66+15*14+13*13=1743",
     "1743 (exact)", "1743 (exact)", "1743 (exact)",
     "four block sizes read from the table's own header close onto the next P2 slot",
     "this work, regression_power_budget_extent", "PROVEN", "-"),
    ("E05", "4D", "POWER TOPOLOGY", "header + entry match pwr_topology_2x",
     "6 / 22 / 20 / rel 27x15", "same", "same",
     "nvgpu pwr_topology_2x_header+entry, extent 851 exact", "bios.h:749",
     "PROVEN", "-"),
    ("E06", "4D", "POWER TOPOLOGY", "whole table bytes", "identical", "identical",
     "identical", "byte compare of all 851 B", "this work",
     "PROVEN", "a CMP ROM from a different board"),
    ("E07", "4D", "THERMAL POLICY", "header byte +4", "0xFF", "0x02", "0x02",
     "ROM raw; no schema", "slot 20", "UNKNOWN", "a published v0x10 thermal-policy schema"),
    ("E08", "4D", "THERMAL POLICY", "header bytes +7/+8", "C0 01", "C0 01", "00 02",
     "ROM raw; no schema", "slot 20", "UNKNOWN", "idem"),
    ("E09", "4D", "LOW POWER GR", "entry0 feature mask", "0xE7FFFFFF", "0xEFFFFFFF",
     "0xEFFFFFFF", "ROM raw; nvgpu names only bits 0 and 4", "bios.h:1201",
     "UNKNOWN", "RM parser for the remaining mask bits"),
    ("E10", "4C", "PERFORMANCE", "PCIEGEN domain nom/min/max", "1/1/1", "3/3/3",
     "3/3/3", "ROM + vix-editor GV HAL domain order (10/10 ordering match)",
     "tables.py TURING_CLOCK_ROWS", "STRONGLY SUPPORTED",
     "LnkSta on the card showing 2.5 GT/s, plus a Gen2-only Turing ROM showing 2"),
    ("E11", "4C", "PCIe script", "reg 0x0088610 write", "0x00000001", "0x00001001",
     "0x00001001", "ROM decoded with the Devinit spec (0x7A = 9 B)",
     "ogdoc/Devinit/devinit.xml INIT_ZM_REG", "PROVEN",
     "a register map naming 0x88610"),
    ("E12", "4C", "PCIe script", "register block of 0x88610", "PPCI+0x610", "same",
     "same", "nouveau gp100_pci_func.cfg{.addr=0x088000,.size=0x1000}",
     "nvkm/subdev/pci/gp100.c", "STRONGLY SUPPORTED",
     "a Turing register map that names PPCI+0x610"),
    ("E13", "4C", "PCIe script", "CONDITION id", "86", "82", "82",
     "ROM, Devinit INIT_CONDITION (0x75) operand", "devinit.xml",
     "PROVEN", "the condition table contents"),
    ("E14", "4C", "LOW POWER PCIe", "entry byte 8, all 5 entries", "0xFB", "0xF8",
     "0xF8", "ROM raw, structural fit {0x10,5,12,5} closes on slot 31",
     "slot 30", "PROVEN", "entry schema"),
    ("E15", "4C", "LOW POWER PCIe", "meaning of entry byte 8", "bits 0,1 set", "-",
     "-", "no schema, no consumer", "slot 30", "UNKNOWN",
     "GSP-RM parser or a 4th ROM"),
    ("E16", "4C", "PERFORMANCE", "pcie_idx values used", "{0,2}", "{0,1,2}", "{0,1,2}",
     "ROM; CMP drops p-state 0x0A which is the only user of index 1",
     "bios.h:612", "PROVEN", "-"),
    ("E17", "4C", "PERFORMANCE", "pcie_idx target table", "unknown", "unknown",
     "unknown", "nvgpu never dereferences it; nouveau has no v0x60 parser; "
     "open-gpu-kernel-modules has no perf parser", "-", "UNKNOWN",
     "RM/GSP-RM disassembly"),
    ("E20", "4B", "RT Core", "RT hardware presence", "no ROM field", "no ROM field",
     "no ROM field", "GPC domain byte-identical; no RT table in the ROM",
     "this work", "UNKNOWN", "M08/M10 measuring traversal separately"),
    ("E21", "4E", "GR firmware", "device-id branch for 1F0B",
     "none found in public sources", "-", "-",
     "nvgpu/nouveau/ogkm searched; TU106 has one chipset entry", "nvkm/device/base.c nv166_chipset",
     "UNKNOWN", "GSP-RM binary disassembly"),
    ("E22", "4E", "floor sweep", "TPC5 disable", "0x20 observed", "-", "-",
     "live read from a previous session (results/TPC5_LIVE)", "0x021C38", "HYPOTHESIS",
     "M17 deviceQuery on two cards"),
    ("E25", "4G", "memory", "strap timings profile", "differs at strap 12-17",
     "reference", "reference", "MEM TIMINGS v0x20 entries", "this work", "PROVEN",
     "which strap is active (M04 + RM telemetry)"),
]


def main():
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "data", "PHASE4_FIELD_EVIDENCE.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEAD)
        w.writerows(ROWS)
    print(f"{out}: {len(ROWS)} rows")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Export decoded + unknown field tables for the three TU106 ROMs.

    python3 scripts/export_fields.py [rom_dir] [out_dir]

Read-only: reads the ROMs, writes only data/*.csv.

Offset columns are deliberately split:
  file_offset    where the *definition* lives (a BIT record, a pointer slot,
                 a CONFIG word, a header byte)
  target_offset  where the *structure* it points at lives, if it points
That separation is the fix for two bugs the v2 export had: it labelled the BIT
'P' version with the P2 directory address (not the BIT record), and it labelled
each P2 slot pointer with the resolved table address (not the pointer slot).
"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tu106_vbios import load, P2_NAMES, MEM_TWEAK_FIELDS

ROMS = ["TU106.rom", "219827.rom", "265590.rom"]
LABEL = {"TU106.rom": "CMP40HX", "219827.rom": "RTX2060S", "265590.rom": "RTX2070"}
DEV = {0x1F0B: "CMP 40HX", 0x1F06: "RTX 2060 SUPER", 0x1F07: "RTX 2070"}

# field definition source -> (citation, evidence level)
SRC = {
    "pci": ("PCI spec / nvgpu nvgpu_bios_parse_rom(): PCIR+0x10 image_len x512", "PROVEN"),
    "bit": ("NVIDIA BIOS-Information-Table spec; envytools nvbios/bit.c:75-78", "PROVEN"),
    "p2ptr": ("nvgpu common/vbios/bios.c nvgpu_bios_get_perf_table_ptrs(): "
              "pointer at data_ptr + table_id*PERF_PTRS_WIDTH(4); "
              "offset > base_rom_size adds expansion_rom_offset", "PROVEN"),
    "p2names": ("envytools nvbios/power.c P2_tbls[] (names only)", "PROVEN"),
    "nvgpu.pstate": ("NVIDIA nvgpu include/nvgpu/bios.h: vbios_pstate_header_6x / "
                     "vbios_pstate_entry_6x / vbios_pstate_entry_clock_6x", "PROVEN"),
    "nvgpu.clocks35": ("NVIDIA nvgpu include/nvgpu/bios.h: vbios_clocks_table_35_*", "PROVEN"),
    "nvgpu.domain": ("NVIDIA nvgpu bios.h PERF_CLK_DOMAINS_IDX_MAX sizes the array but "
                     "does not name indices; order taken from the v0x35 GV HAL rows",
                     "STRONGLY SUPPORTED"),
    "pciegen": ("no consumer found in nvgpu / open-gpu-kernel-modules / nouveau; "
                "value 1 vs 3 correlates with Gen1 vs Gen3 only", "HYPOTHESIS"),
    "perf.extent": ("this work: hdr+cnt*(base+sub*subcnt) == next P2 pointer", "PROVEN"),
    "memclk": ("NVIDIA MemoryClockTable spec (v0x11) + extent arithmetic", "PROVEN"),
    "memtweak": ("NVIDIA MemoryTweakTable spec (v0x20) + extent arithmetic", "PROVEN"),
    "lpwrpcie": ("structural only: {ver,hlen,esz,cnt} + exact extent to slot 31. "
                 "No published schema for the 12B entries.", "UNKNOWN"),
    "devinit": ("NVIDIA open-gpu-doc Devinit spec: INIT_ZM_REG 0x7A / INIT_NV_REG 0x6E / "
                "EOL 0xFF, operand sizes 9/13 bytes", "PROVEN"),
    "devinit.reg": ("register addresses and values as written; Turing register names "
                    "are not published", "UNKNOWN"),
    "dcb": ("NVIDIA DCB 4.x Specification (entry Type nibble)", "PROVEN"),
    "pbc": ("envytools nvbios/power.c envy_bios_parse_power_base_clock() case 0x20", "PROVEN"),
    "pwrpolicy": ("nvgpu pwr_policy_3x_header_struct / pwr_policy_3x_entry_struct "
                  "(TU106 header +7 B, entry +20 B) + exact extent closure", "PROVEN"),
    "pwrtopo": ("nvgpu pwr_topology_2x_header / pwr_topology_2x_entry + relative block "
                "declared in the header; exact extent closure", "PROVEN"),
    "thermpol": ("structural only: {ver=0x10,hlen=10,esz=40,cnt=4} closes on the next "
                 "table; no published field schema", "UNKNOWN"),
    "lpwrgr": ("structural only: {ver=0x10,hlen=10,esz=5,cnt=5}; nvgpu's lpwr_gr struct "
               "is 7 B header / 4 B entry, so TU106 is wider. u32 feature mask, "
               "bits 0 (GR) and 4 (RPPG) named by nvgpu; bit 3 unnamed", "UNKNOWN"),
    "vfe": ("nvgpu vbios_vfe_3x_header_struct / _var_entry_struct (25 B) / "
            "_equ_entry_struct (24 B); extent closes with 55 rppm records of 24 B "
            "+ 15 B tail. Every var type<=7 and equ type<=6 on all 3 ROMs", "PROVEN"),
    "vfe.rppm": ("no published struct; region is 24-byte-periodic for ~95% of its bytes",
                 "UNKNOWN"),
}

UNKNOWN_ROWS = [
    ("LOW POWER PCIe (slot 30)", "entry payload (12 B x 5)", "0x5624b..0x5628c",
     "CMP entry0 = ff fd ff ff fa 48 1f fd fb 9f f8 ff; both GeForce = .. fd f8 .. "
     "(byte 8 differs in all 5 entries). Entries look like bit masks, not clocks.",
     "No published {ver=0x10,hlen=5,esz=12,cnt=5} table schema; nvgpu defines the "
     "LPWR *index* table (5B entries) not this one.",
     "GSP-RM/RM parser for P2 slot 30, or a second family's ROM to see if the "
     "12B layout is stable."),
    ("PERFORMANCE v0x60", "pcie_idx target table", "base entry +3",
     "pcie_idx = 0 / 1 / 2 across entries; slot 30 has 5 entries so the range fits, "
     "but nothing in the ROM names the target.",
     "nvgpu names the field `pcie_idx` and never dereferences it in any public file.",
     "RM/GSP-RM disassembly of the P-state loader."),
    ("PERFORMANCE v0x60", "PCIEGEN clock domain unit", "clock entry idx 8",
     "CMP 1/1/1, GeForce 3/3/3 (nom/min/max). Impossible as MHz; identical min=nom=max.",
     "nvgpu masks the field as NOM_FREQ_MHZ generically, which does not fit a link "
     "generation. No consumer defines the unit.",
     "Live LnkCap/LnkSta on the card + a Turing ROM with a Gen2-only link to see 1/2/3."),
    ("PERFORMANCE v0x60", "lpwr_entry_idx target table", "base entry +2",
     "0x00/0x01/0x02/0x04. nvgpu's LPWR index table entry is 5B "
     "{pcie_idx,gr_idx,ms_idx,di_idx,gc6_idx}; slot 29 decodes as "
     "ver=0x10 hlen=6 esz=7 cnt=5, i.e. 2 bytes wider than nvgpu's struct.",
     "Entry width mismatch: slot 29 carries two extra bytes per entry.",
     "A newer nvgpu bios.h, or slot 29 from a GV100 ROM."),
    ("PERFORMANCE v0x60", "header flags0 bits 2..7", "hdr+6",
     "0x01 on all three ROMs.", "nvgpu defines only bits 0 and 1.",
     "GSP-RM disassembly."),
    ("PERFORMANCE v0x60", "cpi_support_level / cpi_features", "hdr+8 / hdr+9",
     "0x00 / 0x01 on all three ROMs.", "nvgpu names the fields but not the values.",
     "GSP-RM disassembly."),
    ("PERFORMANCE v0x60", "why HUB and DISP are 27 MHz on CMP", "clock entry idx 4, 7",
     "CMP nom=min=max=27 for both. GeForce HUB 540 (max 810), DISP 1080 (max 1330).",
     "Two tables agree the domains are unmanaged on CMP (v0x35 usage=0 FIXED), but "
     "the ROM cannot say whether 27 is a placeholder or a real cap.",
     "Read NV_PCLK per domain under load (read-only) — see the investigation doc."),
    ("CLOCKS v0x35", "param1 meaning on FIXED rows", "row+3..row+6",
     "CMP HUB/DISP param1 = 1b 00 00 00; GeForce HUB = 17 02 00 00, DISP = 00 00 00 00.",
     "nvgpu gives param1 meaning only for MASTER (OC delta) and SLAVE (master index); "
     "CMP's rows are FIXED.",
     "A FIXED-row image from another chip family."),
    ("POWER BASE CLOCK", "header +9..+0x12 and entries 3..16", "0x54326",
     "CMP: 0xff x10 after +8; GeForce: 03 09 then 0xff. Entries 3..16 decode to "
     "implausible clocks (e.g. 133412) under the envytools v0x20 assumption.",
     "envytools documents the header only for the fields it reads; the TU106 "
     "sub-record layout for entries past index 2 differs.",
     "A POWER BASE CLOCK v0x20 consumer in GSP-RM or another family's image."),
    ("POWER BUDGET", "7-byte header extension and 20-byte entry extension", "slot 11",
     "nvgpu's 37 B header / 46 B entry do not cover TU106's 44 / 66; the extra 7 and "
     "20 bytes are unread.",
     "Nothing in the ROM labels the extension; only the blocks the header sizes "
     "(entries, rel, viol) are decoded.",
     "GSP-RM disassembly of the power-policy loader."),
    ("POWER BUDGET", "class-id meaning for every entry", "slot 11 +44",
     "20 entries, class nibble 0/1/4/5/a, unit bit 4; nvgpu names only class 0x5 "
     "(HW_THRESHOLD).",
     "Only class 5 and the class-1 GPU limit are corroborated by value plausibility.",
     "A second TU106-family ROM with a known TDP, or RM source."),
    ("POWER TOPOLOGY", "relative block schema (15 x 27 B)", "slot 15",
     "Header declares rel_entry_size=27, num_rel_entries=15; contents unread.",
     "nvgpu's struct stops at the 22-byte entry; no layout for the relative block.",
     "GSP-RM disassembly."),
    ("POWER TOPOLOGY", "class-id meaning", "slot 15 +6",
     "classes 0, 2, 5 across 20 entries; nvgpu names only CLASS_SENSOR = 1, which "
     "does not occur here.",
     "The one named class is absent, so the enum does not cover this table.",
     "A GV100/GA100 ROM with the same table, or RM source."),
    ("THERMAL POLICY", "field schema", "slot 20",
     "{ver=0x10,hlen=10,esz=40,cnt=4}; hdr byte +4 = 0xff (CMP) vs 0x02 (GeForce), "
     "2070 also differs at +7/+8; entry 2 byte 0 = 0x00 vs 0x01.",
     "No published schema and no nvgpu struct for a v0x10 thermal policy of this shape.",
     "A TU106-shaped THERMAL POLICY parser or RM source."),
    ("LOW POWER GR", "feature-mask bit meaning", "slot 32",
     "5 entries of u32 mask + 1 byte; CMP entry 0 = 0xe7ffffff, GeForce = 0xefffffff "
     "(bit 27 differs).",
     "nvgpu names only bits 0 (GR) and 4 (RPPG) of the mask; bit 27 is unnamed and "
     "the trailing byte is unexplained.",
     "RM/GSP-RM parser."),
    ("PCIe settings script", "register names", "0x3606f (CMP)",
     "Writes 0x137c00, 0x8b900, 0x8c100, 0x88610, 0x8a088, 0x8b400, 0x1404.",
     "Operand layout is PROVEN (Devinit spec); the Turing register map at 0x008xxxx "
     "is not published, so what each write configures stays unknown.",
     "Turing register map / rnndb entries for 0x00880610 and 0x0088b900."),
]


def collect(d):
    out, roms = [], {}
    for f in ROMS:
        p = os.path.join(d, f)
        if not os.path.exists(p):
            raise SystemExit(f"missing ROM: {p}")
        roms[LABEL[f]] = load(p, LABEL[f])

    def add(label, table, field, off, width, raw, val, note, src, ev=None,
            target=None):
        out.append(dict(rom=label, table=table, field=field,
                        file_offset=hex(off) if off is not None else "",
                        target_offset=hex(target) if target else "",
                        width=width, raw=raw, value=val, note=note,
                        source=SRC[src][0], evidence=ev or SRC[src][1]))

    for lbl, r in roms.items():
        pci = r.pci()
        add(lbl, "PCI", "VendorId", pci["pcir"] + 4, 16, f"{pci['vendor']:#06x}",
            pci["vendor"], "little-endian in PCIR; 0x10DE = NVIDIA", "pci")
        add(lbl, "PCI", "DeviceId", pci["pcir"] + 6, 16, f"{pci['device']:#06x}",
            pci["device"], DEV.get(pci["device"], "unknown"), "pci")
        add(lbl, "PCI", "ClassCode", pci["pcir"] + 13, 24,
            f"{pci['class_code']:#08x}", pci["class_name"],
            "0x030000 = VGA controller, 0x030200 = 3D controller", "pci")
        for i, im in enumerate(pci["images"]):
            add(lbl, "PCI", f"image{i}.length", im["pcir"] + 0x10, 16,
                hex(im["image_len"] // 512), im["image_len"],
                "PCIR+0x10, in 512-byte blocks", "pci")
        pm = r.ptr_maps()
        add(lbl, "PCI", "image0_base", None, 16, hex(pm["image0_base"]),
            pm["image0_base"], "512-aligned base of the legacy image (BIT lives inside)",
            "pci", target=pm["image0_base"])

        b = r.bit()
        add(lbl, "BIT", "signature_base", b["base"], 32, "ffb8 424954", b["base"],
            "0xffb8 + 'BIT'; checksum over hlen == 0", "bit")
        add(lbl, "BIT", "version", b["base"] + 6, 16, hex(b["ver"]), b["ver"],
            "u16 LE at +6", "bit")
        add(lbl, "BIT", "header_len", b["base"] + 8, 8, hex(b["hlen"]), b["hlen"],
            "entries start at base+hlen", "bit")
        add(lbl, "BIT", "record_len", b["base"] + 9, 8, hex(b["rlen"]), b["rlen"],
            "6 B/entry: type, ver, len16, off16", "bit")
        add(lbl, "BIT", "token_count", b["base"] + 10, 8, hex(b["count"]), b["count"],
            "", "bit")

        P = b["tokens"]["P"]
        # The version byte is byte 1 of the 6-byte BIT record at P["ent"].
        # v2 shipped P["file"] here, i.e. the P2 directory address.
        add(lbl, "BIT 'P'", "version", P["ent"] + 1, 8, hex(P["ver"]), P["ver"],
            "BIT record byte +1; the record starts at 'ent'", "bit",
            target=P["file"])
        add(lbl, "BIT 'P'", "t_len", P["ent"] + 2, 16, hex(P["t_len"]), P["t_len"],
            f"{P['t_len']//4} x u32 table pointers", "bit", target=P["file"])
        add(lbl, "BIT 'I'", "pcie_settings_script_ptr", b["tokens"]["I"]["file"] + 0x12,
            16, "-", hex(r.u16(b["tokens"]["I"]["file"] + 0x12)),
            "nvinit_ptrs field 9 of 15", "bit",
            target=r.ptr(r.u16(b["tokens"]["I"]["file"] + 0x12)))

        for slot, v in sorted(r.p2().items()):
            # file_offset = the pointer slot itself (P2 base + 4*N);
            # target_offset = the table it resolves to. Exporting only the
            # target made an off-by-one slot indistinguishable from a correct one.
            add(lbl, "P2 dir", f"slot{slot}_ptr", v["ptr_off"], 32, hex(v["raw"]),
                hex(v["file"]), P2_NAMES.get(slot, "no name in envytools"),
                "p2ptr", target=v["file"])

        # --- PERFORMANCE v0x60 (nvgpu) ------------------------------------
        pf = r.perf_v60()
        hmap = {"ver": 0, "hdr_len": 1, "base_len": 2, "entry_cnt": 3,
                "sup_len": 4, "sup_cnt": 5, "flags0": 6, "initial_pstate": 7,
                "cpi_support_level": 8, "cpi_features": 9}
        for k, rel in hmap.items():
            add(lbl, "PERFORMANCE v0x60", f"hdr.{k}", pf["hdr"] + rel, 8,
                hex(pf[k]), pf[k], "", "nvgpu.pstate")
        add(lbl, "PERFORMANCE v0x60", "flags0.pstates_required", pf["hdr"] + 6, 1,
            hex(pf["flags0"]), pf["pstates_required"], "bit0", "nvgpu.pstate")
        add(lbl, "PERFORMANCE v0x60", "flags0.arbiter_lock", pf["hdr"] + 6, 1,
            hex(pf["flags0"]), pf["arbiter_lock"], "bit1", "nvgpu.pstate")
        add(lbl, "PERFORMANCE v0x60", "extent", pf["hdr"], 8, f"{pf['size']} B",
            f"{pf['hdr']:#x}..{pf['end']:#x}",
            "hdr + cnt*(base + sub*subcnt); lands on POWER BASE CLOCK", "perf.extent")
        for e in pf["entries"]:
            add(lbl, "PERFORMANCE v0x60", f"e{e['idx']}.pstate_level", e["off"], 8,
                f"{e['pstate']:#04x}", e["pstate"],
                "VBIOS_PERFLEVEL_SKIP_ENTRY = 0xFF" if e["skip"] else "",
                "nvgpu.pstate")
            add(lbl, "PERFORMANCE v0x60", f"e{e['idx']}.flags0", e["off"] + 1, 8,
                f"{e['flags0']:#04x}",
                f"cap={e['pstate_cap']} cuda_not_safe={e['cuda_not_safe']} "
                f"ovoc={e['ovoc']}",
                "PSTATE_CAP 1:0, CUDA 2, OVOC 3, DECREASE_THRESHOLD 4",
                "nvgpu.pstate")
            add(lbl, "PERFORMANCE v0x60", f"e{e['idx']}.lpwr_entry_idx", e["off"] + 2,
                8, f"{e['lpwr_idx']:#04x}", e["lpwr_idx"],
                "index into the LOW POWER table; target schema UNKNOWN", "nvgpu.pstate")
            add(lbl, "PERFORMANCE v0x60", f"e{e['idx']}.pcie_idx", e["off"] + 3, 8,
                f"{e['pcie_idx']:#04x}", e["pcie_idx"],
                "index into a PCIe config table; no public consumer defines the target",
                "nvgpu.pstate", "UNKNOWN")
            add(lbl, "PERFORMANCE v0x60", f"e{e['idx']}.nvlink_idx", e["off"] + 4, 8,
                f"{e['nvlink_idx']:#04x}", e["nvlink_idx"], "0xff = none",
                "nvgpu.pstate")
            for s in e["subs"]:
                note = {"DRAM": "memory data rate (4x the native clock)",
                        "PCIEGEN": "1 vs 3; unit undefined by any consumer",
                        }.get(s["domain"], "clock bound in MHz")
                add(lbl, "PERFORMANCE v0x60", f"e{e['idx']}.{s['domain']}.nom",
                    s["off"], 14, f"{s['nom_raw']:#06x}", s["nom"], note,
                    "nvgpu.pstate",
                    "HYPOTHESIS" if s["domain"] == "PCIEGEN" else
                    ("STRONGLY SUPPORTED" if s["domain"] in ("GPC", "DRAM")
                     else None))
                add(lbl, "PERFORMANCE v0x60", f"e{e['idx']}.{s['domain']}.min",
                    s["off"] + 2, 14, f"{s['p1_raw']:#010x}", s["mn"],
                    "param1[13:0]", "nvgpu.pstate",
                    "HYPOTHESIS" if s["domain"] == "PCIEGEN" else None)
                add(lbl, "PERFORMANCE v0x60", f"e{e['idx']}.{s['domain']}.max",
                    s["off"] + 2, 14, f"{s['p1_raw']:#010x}", s["mx"],
                    "param1[27:14]", "nvgpu.pstate",
                    "HYPOTHESIS" if s["domain"] == "PCIEGEN" else None)

        # --- CLOCKS v0x35 --------------------------------------------------
        ck = r.clocks_v35()
        if ck:
            add(lbl, "CLOCKS v0x35", "header", ck["hdr"], 4, r.hex(ck["hdr"], 4),
                f"ver={ck['ver']:#x}", "signature 35 09 0b 0a", "nvgpu.clocks35")
            add(lbl, "CLOCKS v0x35", "entry_size/count", ck["hdr"] + 2, 16,
                r.hex(ck["hdr"] + 2, 2), f"{ck['row_len']} x {ck['count']}",
                "", "nvgpu.clocks35")
            for row in ck["rows"]:
                add(lbl, "CLOCKS v0x35", f"{row['domain']}.usage", row["off"], 5,
                    f"{row['usage']}", {0: "FIXED", 1: "MASTER", 2: "SLAVE"}[row["usage"]],
                    "NV_VBIOS_CLOCKS_TABLE_1X_ENTRY_FLAGS0_USAGE", "nvgpu.clocks35")
                add(lbl, "CLOCKS v0x35", f"{row['domain']}.ordering_idx",
                    row["off"] + 7, 8, hex(row["ordering"]), row["ordering"],
                    "domain identity; matches the GV HAL row order", "nvgpu.clocks35")
                add(lbl, "CLOCKS v0x35", f"{row['domain']}.pre_volt_idx",
                    row["off"] + 7, 4, hex(row["pre_volt_idx"]), row["pre_volt_idx"],
                    "param2[3:0]", "nvgpu.clocks35")
                add(lbl, "CLOCKS v0x35", f"{row['domain']}.post_volt_idx",
                    row["off"] + 7, 4, hex(row["post_volt_idx"]), row["post_volt_idx"],
                    "param2[7:4]", "nvgpu.clocks35")

        # --- memory -------------------------------------------------------
        mc = r.mem_clock_table()
        for k, rel in {"ver": 0, "hdr_len": 1, "base_len": 2, "strap_len": 3,
                       "strap_cnt": 4, "entry_cnt": 5}.items():
            add(lbl, "MEM TIMINGS MAPPING", k, mc["hdr"] + rel, 8, hex(mc[k]), mc[k],
                "TU106 uses base 60 / strap 33 (spec's 20/26 is the original sizing)",
                "memclk")
        add(lbl, "MEM TIMINGS MAPPING", "extent", mc["hdr"], 8, f"{mc['size']} B",
            f"{mc['hdr']:#x}..{mc['end']:#x}", "lands on MEM TIMINGS", "memclk")
        for e in mc["entries"]:
            add(lbl, "MEM TIMINGS MAPPING", f"e{e['idx']}.min_mhz", e["off"], 14,
                hex(e["min_raw"]), e["min_mhz"], "bits 13:0 = MHz", "memclk")
            add(lbl, "MEM TIMINGS MAPPING", f"e{e['idx']}.max_mhz", e["off"] + 2, 14,
                hex(e["max_raw"]), e["max_mhz"], "bits 13:0 = MHz", "memclk")
            add(lbl, "MEM TIMINGS MAPPING", f"e{e['idx']}.rw_config0", e["off"] + 8,
                32, hex(e["rw0"]), hex(e["rw0"]),
                "Read/Write Config0 bitfield; inner layout UNKNOWN", "memclk")
            add(lbl, "MEM TIMINGS MAPPING", f"e{e['idx']}.rw_config1", e["off"] + 12,
                32, hex(e["rw1"]), hex(e["rw1"]),
                "Read/Write Config1 bitfield; inner layout UNKNOWN", "memclk")

        mt = r.mem_tweak_table()
        for k, rel in {"ver": 0, "hdr_len": 1, "base_len": 2, "ext_len": 3,
                       "ext_cnt": 4, "entry_cnt": 5}.items():
            add(lbl, "MEM TIMINGS", k, mt["hdr"] + rel, 8, hex(mt[k]), mt[k],
                "spec v0x20 says base 76; TU106 ROMs use 74", "memtweak")
        add(lbl, "MEM TIMINGS", "extent", mt["hdr"], 8, f"{mt['size']} B",
            f"{mt['hdr']:#x}..{mt['end']:#x}", "lands on LOW POWER", "memtweak")
        # Every timing field, with the CONFIG word it lives in, its shift, mask
        # and the full raw word. v2 emitted a bare number with raw="-", which
        # made a bad shift indistinguishable from a bad ROM.
        for e in mt["entries"]:
            for (name, w, sh, mask) in MEM_TWEAK_FIELDS:
                f = e["fields"][name]
                add(lbl, "MEM TIMINGS", f"e{e['idx']}.{name}", f["word_off"], 32,
                    hex(f["raw"]),
                    f"CONFIG{w}[{sh + mask.bit_length() - 1}:{sh}] = {f['value']}",
                    f"shift {sh}, mask {mask:#x}, word CONFIG{w}", "memtweak")

        # --- POWER BASE CLOCK ---------------------------------------------
        bc = r.power_base_clock()
        for k, rel in {"ver": 0, "hlen": 1, "rlen": 2, "entry_cnt": 3,
                       "secount": 4, "selen": 5}.items():
            add(lbl, "POWER BASE CLOCK", k, bc["hdr"] + rel, 8, hex(bc[k]), bc[k],
                "", "pbc")
        add(lbl, "POWER BASE CLOCK", "extent", bc["hdr"], 8, f"{bc['size']} B",
            f"{bc['hdr']:#x}..{bc['end']:#x}", "lands on PERF TEST SPEC (slot 17)",
            "pbc")
        for e in bc["entries"][:3]:
            add(lbl, "POWER BASE CLOCK", f"e{e['idx']}.pstate", e["off"], 8,
                f"{e['pstate']:#04x}", e["pstate"], "0xff = unused slot", "pbc")
            add(lbl, "POWER BASE CLOCK", f"e{e['idx']}.clock0_MHz", e["off"] + 3, 16,
                hex(e["clocks"][0] // 4), e["clocks"][0],
                "u16 raw x4; entry0 = base, entry2 = boost", "pbc",
                "STRONGLY SUPPORTED")

        # --- LOW POWER PCIe (slot 30) -------------------------------------
        lp = r.lpwr_pcie()
        if lp:
            for k, rel in {"ver": 0, "hlen": 1, "entry_len": 2, "count": 3}.items():
                add(lbl, "LOW POWER PCIe", k, lp["hdr"] + rel, 8, hex(lp[k]), lp[k],
                    "structural fit only; entries are 12 B", "lpwrpcie")
            add(lbl, "LOW POWER PCIe", "extent", lp["hdr"], 8, f"{lp['size']} B",
                f"{lp['hdr']:#x}..{lp['end']:#x}", "lands on slot 31", "lpwrpcie")
            for e in lp["entries"]:
                add(lbl, "LOW POWER PCIe", f"e{e['idx']}.raw", e["off"], 96,
                    e["raw"].hex(" "), "-", "payload semantics UNKNOWN", "lpwrpcie")

        # --- PCIe settings script ------------------------------------------
        ps = r.pcie_settings_script()
        if ps:
            add(lbl, "PCIe settings script", "script_ptr", r.bit()["tokens"]["I"]["file"] + 0x12,
                16, hex(ps["ptr"]), hex(ps["off"]), "nvinit_ptrs field +0x12", "devinit",
                target=ps["off"])
            for op in ps["ops"]:
                if op["op"] == "EOL":
                    add(lbl, "PCIe settings script", "EOL", op["off"], 8, "ff",
                        "0xff", "terminator", "devinit")
                elif op["op"] == "ZM_REG":
                    add(lbl, "PCIe settings script", f"reg{op['addr']:#x}",
                        op["off"], 32, r.hex(op["off"], 9),
                        f"= {op['data']:#010x}", "INIT_ZM_REG", "devinit",
                        "UNKNOWN")
                elif op["op"] == "NV_REG":
                    add(lbl, "PCIe settings script", f"reg{op['addr']:#x}",
                        op["off"], 32, r.hex(op["off"], 13),
                        f"= (reg & {op['mask']:#010x}) | {op['data']:#010x}",
                        "INIT_NV_REG", "devinit", "UNKNOWN")
                else:
                    add(lbl, "PCIe settings script", op["op"], op["off"], 8,
                        hex(r.u8(op["off"])), "-", "unknown opcode stops the decode",
                        "devinit", "UNKNOWN")


        # --- POWER BUDGET / TOPOLOGY / THERMAL POLICY / LOW POWER GR -------
        pb = r.power_budget()
        for k, rel in {"ver": 0, "hlen": 1, "entry_len": 2, "count": 3}.items():
            add(lbl, "POWER BUDGET", k, pb["hdr"] + rel, 8, hex(pb[k]), pb[k],
                "TU106 header is 44 B vs nvgpu 37", "pwrpolicy")
        for k, rel in {"base_sample_ms": 4, "min_client_sample_ms": 6}.items():
            add(lbl, "POWER BUDGET", k, pb["hdr"] + rel, 16, hex(pb[k]), pb[k],
                "", "pwrpolicy")
        for k, rel in {"rel_len": 8, "rel_cnt": 9, "tgp_idx": 10, "rtp_idx": 11,
                       "mxm_idx": 12, "dnotifier_idx": 13,
                       "viol_len": 34, "viol_cnt": 35}.items():
            add(lbl, "POWER BUDGET", k, pb["hdr"] + rel, 8, hex(pb[k]), pb[k],
                "", "pwrpolicy")
        add(lbl, "POWER BUDGET", "extent", pb["hdr"], 8, f"{pb['size']} B",
            f"{pb['hdr']:#x}..{pb['end']:#x}",
            "hlen + cnt*esz + rel_cnt*rel_len + viol_cnt*viol_len", "pwrpolicy")
        for e in pb["entries"]:
            if not (e["limit_min"] or e["limit_rated"] or e["limit_max"]):
                continue
            add(lbl, "POWER BUDGET", f"e{e['idx']}.class_id", e["off"], 4,
                f"{e['flags0']:#04x}", e["class_id"], "flags0[3:0]", "pwrpolicy")
            for name, off in (("limit_min", 2), ("limit_rated", 6), ("limit_max", 10)):
                add(lbl, "POWER BUDGET", f"e{e['idx']}.{name}", e["off"] + off, 32,
                    hex(e[name]), e[name],
                    "mW on class-1/5 entries; unit for other classes UNKNOWN",
                    "pwrpolicy", "STRONGLY SUPPORTED")

        pt = r.power_topology()
        for k, rel in {"ver": 0, "hlen": 1, "entry_len": 2, "count": 3,
                       "rel_len": 4, "rel_cnt": 5}.items():
            add(lbl, "POWER TOPOLOGY", k, pt["hdr"] + rel, 8, hex(pt[k]), pt[k],
                "matches nvgpu pwr_topology_2x_header exactly", "pwrtopo")
        add(lbl, "POWER TOPOLOGY", "extent", pt["hdr"], 8, f"{pt['size']} B",
            f"{pt['hdr']:#x}..{pt['end']:#x}",
            "6 + 20*22 + 15*27 = 851", "pwrtopo")
        for e in pt["entries"]:
            add(lbl, "POWER TOPOLOGY", f"e{e['idx']}.class_id", e["off"], 4,
                f"{e['flags0']:#04x}", e["class_id"],
                "nvgpu names only CLASS_SENSOR=1 (absent here)", "pwrtopo")
            add(lbl, "POWER TOPOLOGY", f"e{e['idx']}.pwr_rail", e["off"] + 1, 8,
                f"{e['pwr_rail']:#04x}", e["pwr_rail"], "", "pwrtopo")
            add(lbl, "POWER TOPOLOGY", f"e{e['idx']}.curr_corr_slope",
                e["off"] + 6, 32, hex(e["curr_corr_slope"]), e["curr_corr_slope"],
                "", "pwrtopo")
            add(lbl, "POWER TOPOLOGY", f"e{e['idx']}.curr_corr_offset",
                e["off"] + 10, 32, hex(e["curr_corr_offset"]), e["curr_corr_offset"],
                "", "pwrtopo")

        tp = r.thermal_policy()
        for k, rel in {"ver": 0, "hlen": 1, "entry_len": 2, "count": 3}.items():
            add(lbl, "THERMAL POLICY", k, tp["hdr"] + rel, 8, hex(tp[k]), tp[k],
                "", "thermpol")
        add(lbl, "THERMAL POLICY", "hdr_tail", tp["hdr"] + 4, 8,
            tp["hdr_tail"].hex(" "), "-",
            "CMP +4=0xff vs GeForce 0x02; field names UNKNOWN", "thermpol")
        add(lbl, "THERMAL POLICY", "extent", tp["hdr"], 8, f"{tp['size']} B",
            f"{tp['hdr']:#x}..{tp['end']:#x}", "", "thermpol")
        for e in tp["entries"]:
            add(lbl, "THERMAL POLICY", f"e{e['idx']}.raw", e["off"], 320,
                e["raw"].hex(" "), "-", "payload semantics UNKNOWN", "thermpol")

        lg = r.lpwr_gr()
        for k, rel in {"ver": 0, "hlen": 1, "entry_len": 2, "count": 3}.items():
            add(lbl, "LOW POWER GR", k, lg["hdr"] + rel, 8, hex(lg[k]), lg[k], "",
                "lpwrgr")
        add(lbl, "LOW POWER GR", "extent", lg["hdr"], 8, f"{lg['size']} B",
            f"{lg['hdr']:#x}..{lg['end']:#x}", "", "lpwrgr")
        for e in lg["entries"]:
            add(lbl, "LOW POWER GR", f"e{e['idx']}.feature_mask", e["off"], 32,
                hex(e["feature_mask"]), hex(e["feature_mask"]),
                "u32 LE; bit0 GR, bit4 RPPG named by nvgpu; bit3 unnamed",
                "lpwrgr")
            add(lbl, "LOW POWER GR", f"e{e['idx']}.tail", e["off"] + 4, 8,
                e["tail"].hex(), e["tail"].hex(), "1 byte after the u32: UNKNOWN",
                "lpwrgr")


        # --- VFE 3x (slot 8) ----------------------------------------------
        vf = r.vfe_3x()
        for k, rel in {"ver": 0, "hlen": 1, "var_len": 2, "var_cnt": 3,
                       "equ_len": 4, "equ_cnt": 5, "polling_ms": 6,
                       "var_rppm_cnt": 7, "equ_rppm_cnt": 8}.items():
            add(lbl, "VFE 3x", k, vf["hdr"] + rel, 8, hex(vf[k]), vf[k],
                "9 B header per nvgpu vbios_vfe_3x_header_struct", "vfe")
        add(lbl, "VFE 3x", "extent", vf["hdr"], 8, f"{vf['span']} B",
            f"{vf['hdr']:#x}..{vf['end']:#x}",
            "9 + 20*25 + 150*24 + 55*24 + 15", "vfe")
        for e in vf["vars"]:
            add(lbl, "VFE 3x", f"var{e['idx']}.type", e["off"], 8,
                f"{e['type']:#04x}", e["type"],
                "VBIOS_VFE_3X_VAR_ENTRY_TYPE_* (0..7)", "vfe")
            add(lbl, "VFE 3x", f"var{e['idx']}.out_max", e["off"] + 5, 32,
                hex(e["out_max"]), e["out_max"], "fixed-point/float, UNKNOWN scaling",
                "vfe", "UNKNOWN")
        for e in vf["equs"][:20]:
            add(lbl, "VFE 3x", f"equ{e['idx']}.type", e["off"], 8,
                f"{e['type']:#04x}", e["type"],
                "VBIOS_VFE_3X_EQU_ENTRY_TYPE_* (0..6)", "vfe")
            add(lbl, "VFE 3x", f"equ{e['idx']}.var_idx", e["off"] + 1, 8,
                f"{e['var_idx']:#04x}", e["var_idx"],
                "0xFF = VBIOS_VFE_3X_EQU_ENTRY_IDX_INVALID", "vfe")
            add(lbl, "VFE 3x", f"equ{e['idx']}.param3", e["off"] + 23, 8,
                hex(e["param3"] & 0xF), e["param3"] & 0xF,
                "PAR3_OUTPUT_TYPE 0..0xC (MHZ/VOLT_UV/POWER_MW/...)", "vfe")
        for e in vf["rppm"][:6]:
            add(lbl, "VFE 3x", f"rppm{e['idx']}.raw", e["off"], 192,
                e["raw"].hex(" "), "-", "rppm record, semantics UNKNOWN", "vfe.rppm")

        # --- DCB -----------------------------------------------------------
        d = r.dcb()
        add(lbl, "DCB", "header", d.get("off") or 0, 32,
            f"ver={d.get('ver')} hdr={d.get('hdr')} cnt={d.get('cnt')} "
            f"len={d.get('len')}", f"active={d['active']}",
            "Type nibble 0xE = EOL, 0xF = Skip", "dcb")
        for e in d["entries"]:
            add(lbl, "DCB", f"entry{e['idx']}.type", e["off"], 4, f"{e['type']:#04x}",
                e["type_name"], "display-path word bits 3:0", "dcb")

    return out


def main(argv):
    d = argv[1] if len(argv) > 1 else os.environ.get("CMP_ROM_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "roms"))
    outdir = argv[2] if len(argv) > 2 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(outdir, exist_ok=True)
    rows = collect(d)

    p1 = os.path.join(outdir, "TU106_DECODED_FIELDS.csv")
    with open(p1, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    p2 = os.path.join(outdir, "TU106_UNKNOWN_FIELDS.csv")
    with open(p2, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["table", "field", "offset", "observed", "why_unknown",
                    "needed_to_resolve"])
        w.writerows(UNKNOWN_ROWS)

    print(f"{p1}: {len(rows)} rows")
    print(f"{p2}: {len(UNKNOWN_ROWS)} rows")


if __name__ == "__main__":
    main(sys.argv)

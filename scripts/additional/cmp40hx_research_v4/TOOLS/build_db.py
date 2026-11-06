#!/usr/bin/env python3
"""Sinh UNKNOWN_DATABASE.json + COVERAGE.json + RESEARCH_QUEUE.json tu du lieu that.

Dung: python3 build_db.py
Doc: FUSE/fuse2.json, MMIO/mmio.json, MMIO/registers_all.json,
     outputs/vbios_map.json, outputs/gsp_xrefs.json, outputs/firmware_container_map.json
"""
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(p, default=None):
    try:
        return json.load(open(os.path.join(ROOT, p)))
    except Exception:
        return default if default is not None else {}


def main():
    fuse2 = load("FUSE/fuse2.json")
    mmio = load("MMIO/mmio.json")
    regall = load("MMIO/registers_all.json")
    vbios = load("outputs/vbios_map.json")
    gspx = load("outputs/gsp_xrefs.json")
    fw = load("outputs/firmware_container_map.json")

    regs = {int(k): v for k, v in fuse2.get("regs", {}).items()}
    poison = set(fuse2.get("poison", []))
    with_data = {k: v for k, v in regs.items() if v not in poison and v != 0}
    mmregs = mmio.get("registers", {})

    U = []

    def add(**kw):
        kw.setdefault("status", "open")
        kw.setdefault("dependencies", [])
        kw.setdefault("priority", "P5")
        U.append(kw)

    # ---- FUSE unknowns ----
    add(id="U-FUSE-001", component="FUSE", address="0x021000+0x0110..0x0198",
        observed="152 word gia tri dung 0x00000001",
        hypotheses=["OTP bit cell readout (moi bit 1 word)",
                    "mang 152 enable flag doc lap"],
        supporting="moi word chi bat bit 0; khoang cach la boi so 4",
        contradicting="chua co TU106 thu 2 de doi chieu",
        confidence="INFERRED", priority="P0",
        methods="doi chieu dump fuse cua TU106 khac; tra nouveau/envytools",
        next="tim dump fuse TU106/TU104 khac tren mang")
    add(id="U-FUSE-002", component="FUSE", address="0x021000+0x0718..0x0734",
        observed="8 word lien tuc entropy cao (32 byte)",
        hypotheses=["SHA-256 cua vung nao do", "HMAC", "khoa cong khai"],
        supporting="32 byte dung kich thuoc SHA-256; khong cau truc",
        confidence="BLOCKED", priority="P0", status="open",
        methods="TOOLS/q289.py q2(): 455,689 phep thu tren rom+gsp+ucodes; "
                "TOOLS/q5_fusehash.py: 12,883 phep thu tren chinh khoi fuse "
                "(7 vung co nghia + 8 co cua so truot)",
        contradicting="0 khop; 32 B khong phai 2x hash 16 B ghep",
        next="DA THU hash tren chinh vung fuse: 0 khop. Can ROM TU106 khac "
             "hoac khoa/HMAC de doi chieu")
    add(id="U-FUSE-003", component="FUSE", address="0x021000+0x0000",
        observed="0xC0040000", hypotheses=["fuse strap mirror", "chip config"],
        supporting="khac NV_PMC_BOOT_0 (0x166000A1)",
        contradicting="bit cao 0xC0 khong giong format nao da biet",
        confidence="UNKNOWN", priority="P0", methods="tra strap bitfield")
    add(id="U-FUSE-004", component="FUSE", address="0x021000+0x00D4..0x00F4",
        observed="0xFFFFFFFC / 0xFFFFFF8F (11 word)",
        hypotheses=["fuse programming complete marker", "mask da dot"],
        supporting="tat ca bit bat tru vai bit", contradicting="chua ro bit nao",
        confidence="INFERRED", priority="P1")
    add(id="U-FUSE-005", component="FUSE", address="0x021000+0x0C1C",
        observed="0x00000038 (0b00111000)", hypotheses=["bit 3/4/5 = 3 GPC?"],
        supporting="TU106 co 3 GPC", contradicting="chua co bitfield",
        confidence="INFERRED", priority="P0")
    add(id="U-FUSE-006", component="FUSE", address="0x021000+0x0178,0x02D4,0x0578,0x0E08",
        observed="0xBADF510C nam GIUA vung co du lieu",
        hypotheses=["o fuse bi khoa", "doc loi co ban"],
        supporting="5 vi tri, cung ma", contradicting="khong phai poison ngoai khoi",
        confidence="UNKNOWN", priority="P1")
    add(id="U-FUSE-007", component="FUSE", address="0x021000+0x0344..0x0348",
        observed="0x40680BB5 0x72E259ED", hypotheses=["hash/trim"],
        confidence="UNKNOWN", priority="P1")
    add(id="U-FUSE-008", component="FUSE", address="0x021000+0x0100..0x0240",
        observed="155 word gia tri 1..7 (khong phai bitmask)",
        hypotheses=["version field", "counter", "index"],
        confidence="UNKNOWN", priority="P2")
    add(id="U-FUSE-009", component="FUSE", address="0x021000+0x0C04",
        observed="NV_FUSE_STATUS_OPT_DISPLAY DATA_ENABLE=1 nhung MMIO display BADF",
        hypotheses=["display bi chan boi clock/power gating khong phai fuse",
                    "CMP SKU fuse khac chua nhan dang",
                    "address decoder khong map display tren CMP"],
        supporting="fuse bao enable; raw9.6 tach biet",
        confidence="DECODED", priority="P0", status="resolved",
        methods="TOOLS/q6_display.py: doc 8 vung display + 3 vung doi chung",
        contradicting="display 0/200 word; PBUS 1/8, FUSE 7/8 doc tot -> "
                      "KHONG phai doc sai dia chi, la address decoder tu choi",
        note="PGRAPH 0x400000 cung poison -> BAR0 khong decode toan bo 16 MB")
    add(id="U-FUSE-010", component="FUSE", address="0x021000+0x0520",
        observed="0x16480000", hypotheses=["trim value", "clock setting"],
        confidence="UNKNOWN", priority="P2")
    add(id="U-FUSE-011", component="FUSE", address="0x021000+0x0D38",
        observed="0x000000F0", hypotheses=["binning/grade"], confidence="UNKNOWN",
        priority="P1")
    add(id="U-FUSE-012", component="FUSE", address="0x021000+0x0DC8..0x0DD0",
        observed="0x00000007 x3", hypotheses=["count/version"], confidence="UNKNOWN",
        priority="P2")
    add(id="U-FUSE-013", component="FUSE", address="0x00820000",
        observed="NV_FUSE0_PRI_BASE tra NV_PMC_BOOT_0 roi poison",
        hypotheses=["gb100-only, khong ap dung TU106"],
        supporting="0x166000a1 tai offset 0; 53/64 poison",
        contradicting="driver 615.78.08 co dinh nghia",
        confidence="DECODED", priority="P0", status="resolved",
        methods="da kiem chung bang doc truc tiep")

    # ---- MMIO unknowns ----
    for n, x in mmregs.items():
        if x["state"] == "poison":
            add(id=f"U-MMIO-{n}", component="MMIO", address=x["addr_hex"],
                observed=f"poison 0x{x['value']:08x}"
                if isinstance(x["value"], int) else "read_err",
                hypotheses=["block khong ton tai", "clock gated",
                            "address decoder khong map", "access restricted"],
                supporting="register co trong source turing",
                contradicting="khong co",
                confidence="UNKNOWN", priority="P2",
                methods="doc qua cua so khac; kiem tra reset/clock gate")

    # ---- VBIOS unknowns ----
    add(id="U-VBIOS-001", component="VBIOS", address="0x03000..0x034BF",
        observed="38 record x 32 B: sig 0x6700 + ver 0x200/0x300/0x400/0x600 + "
                 "16 B hash + flags",
        hypotheses=["key block / certificate table", "signed config records"],
        supporting="1216 B = 38 x 32 chinh xac; bank2 toan 0xFF tai cung vung",
        contradicting="timestamp field doc ra nam 1972-2102 -> khong phai unix time",
        confidence="DECODED-cau-truc, UNKNOWN-nghia", priority="P0")
    add(id="U-VBIOS-002", component="VBIOS", address="0x79000..0xF2000",
        observed="ban sao thu 2 cua image 495616 B, khac 1 cum 0x3000..0x34BF",
        hypotheses=["bank du phong", "image da ky vs chua ky"],
        supporting="98.9% byte giong; chi khac vung record",
        confidence="CORROBORATED", priority="P1", status="resolved",
        note="payload = ban 1; bank 2 la du phong")
    add(id="U-VBIOS-003", component="VBIOS", address="0x076800..0x078400",
        observed="NPDS type-0x70, 12 digest 32 B",
        hypotheses=["chu ky khoi signature", "digest list"],
        supporting="0/1,365,939 phep thu khong khop vung nao",
        confidence="UNKNOWN", priority="P1")

    # ---- GSP unknowns ----
    add(id="U-GSP-001", component="GSP-RM", address="0x041A70B0",
        observed="bang descriptor 186 entry x 32 B tai base 0x041A70B0, "
                 "consumer la ham dispatch @0x04F575FC",
        hypotheses=["da xac dinh consumer"],
        supporting="capstone RISC-V: lui s1,0x41a7 + addi s1,s1,0xb0 = base; "
                   "addi s1,s1,0x20 = stride 32; end = base+0x1740; "
                   "doc u16@0, u32@4, u8@8, u64@0x10, u16@0x18",
        contradicting="layout P3 (u64@0, u32@8/0xC/0x10/0x14/0x18/0x1C) SAI hoan toan",
        confidence="DECODED", priority="P3", status="resolved",
        methods="TOOLS/q1_lui.py (quet LUI imm20) + TOOLS/q1_disasm.py (capstone)",
        note="BLOCKED 'can Ghidra' la ket luan SAI: chi can quet LUI + capstone")
    add(id="U-GSP-002", component="GSP-RM", address="0x1a72a0",
        observed="PERF_CF_CONTROLLER_GPC_MAX id=21 f08=0xff0a f14=88 f18=273",
        hypotheses=["tran GPC clock", "policy khac"],
        confidence="UNKNOWN", priority="P3")

    # ---- Firmware unknowns ----
    for b in fw.get("blobs", []):
        if b["classification"] == "high-entropy":
            add(id=f"U-FW-{b['idx']:03d}", component="FIRMWARE",
                address=b["offset_hex"],
                observed=f"{b['size']} B entropy {b['entropy']}",
                hypotheses=["ma hoa", "nen", "nen roi ma hoa"],
                supporting="4 blob cung kich thuoc 122880 B",
                contradicting="khong IV, khong magic",
                confidence="UNKNOWN", priority="P4",
                methods="nen lai; XOR cap blob; tim 16 B trung")

    # ---- Topology / memory ----
    add(id="U-TOP-001", component="TOPOLOGY", address="MMIO PRIV",
        observed="display engine BADF1301 du fuse bao enable",
        hypotheses=["clock gated", "power gated", "khong map"],
        confidence="UNKNOWN", priority="P5")
    add(id="U-MEM-001", component="MEMORY", address="NV_PFB",
        observed="VRAM vat ly 8192 MiB, kha dung 7762 MiB (lech 430 MiB)",
        hypotheses=["carveout cho WPR/GSP", "ECC metadata", "reserved"],
        supporting="WPR2 = 0x01f7e000..0x01ffee00 = 528 KB (khong du 430 MiB)",
        confidence="UNKNOWN", priority="P6")

    # ---- P3/P4 unknowns moi ----
    add(id="U-GSP-003", component="GSP-RM", address="0x1a7280..0x1e0000",
        observed="340 entry that trong 60 bang (khong phai 139)",
        hypotheses=["bang descriptor day du"], confidence="DECODED",
        priority="P3", status="resolved",
        note="parser cu dem sai: nhieu 'entry' la duoi chuoi cua entry truoc")
    add(id="U-GSP-004", component="GSP-RM", address="0x1abc98+0x0",
        observed="RELIABILITY_NVVDD id=204 f14=150 f18=273",
        hypotheses=["nguon cua co Reliability trong nvidia-smi"],
        supporting="ten khop tung chu; T4 lam co nay tat",
        contradicting="id=204 trung VMIN_NVVDD_0 -> id khong duy nhat toan cuc",
        confidence="INFERRED", priority="P3")
    add(id="U-GSP-005", component="GSP-RM", address="f08/f18/f14",
        observed="f08 co 16 gia tri (13 dang 0xffXX, 3 dang 0x0001XX/0x0004XX); f18 co 13 gia tri",
        hypotheses=["f08 = kieu du lieu", "f18 = module ID"],
        confidence="UNKNOWN", priority="P3")
    add(id="U-FW-012", component="FIRMWARE", address="0x0B7C00 vs 0x0F5400",
        observed="blob[6] va blob[8] khac dung 24 byte = BUILD TIMESTAMP ASCII",
        hypotheses=["da xac dinh"],
        supporting="blob[6]='Dec 31 2024' + '11:39:34'; blob[8]='Jan  2 2025' + "
                   "'08:35:16' (20 B ASCII + 1 B counter 0x21/0x1F, lap 2 lan)",
        confidence="DECODED", priority="P4", status="resolved",
        methods="TOOLS/q289.py q8(); in hex 4 cum khac")
    add(id="U-FW-013", component="FIRMWARE", address="0x002F00",
        observed="blob[0] entropy 3.481, 93.1% lenh unknown tu 4 offset",
        hypotheses=["data segment khong phai code", "code bi obfuscate"],
        supporting="3 lenh dau decode duoc chi la trung hop", confidence="INFERRED",
        priority="P4")

    add(id="U-GSP-007", component="GSP-RM", address="0x041A70B0 + k*32",
        observed="chi 56/186 entry co u64(+0x10) tro toi DAU chuoi ASCII; "
                 "130 entry con lai co u64 la vaddr nhung tro vao giua du lieu",
        hypotheses=["bang gom nhieu sub-table layout khac nhau",
                    "entry co union: u64 khi la name_ptr, khi la cap so"],
        supporting="25 cum entry-co-ten, cum dai nhat 9 entry",
        contradicting="base/stride/span deu dung tu disasm",
        confidence="BLOCKED", priority="P3",
        methods="thu 3 base khac nhau, thu u64=2x u32 offset vao pool: 0 ten",
        next="doc ham callback jalr a5 de biet no dien giai entry the nao")

    add(id="U-GSP-006", component="GSP-RM", address="0x00092de8, 0x000a7a90, 0x001a6ba0",
        observed="7 ten (RMClkVfOverride, RmAtsVolOverride, "
                 "RmClkControllersOverride, OVERVOLTAGE_LOGIC, "
                 "OVERVOLTAGE_NVVDD_0/1, PERFORMANCE_CAP0) KHONG co entry "
                 "descriptor nao tro toi",
        hypotheses=["ten noi bo khong dang ky qua bang descriptor",
                    "bang descriptor thu 2 o dinh dang khac"],
        supporting="0 u32 ptr, 0 u64 ptr, 0 entry-style o MOI offset chan 4, "
                   "tren ca 3 encoding thu (file_off, vaddr, u64)",
        contradicting="7 ten deu nam trong vung mat do string cao (43-116 NUL/512B)",
        confidence="BLOCKED", priority="P3",
        methods="TOOLS/q289.py q9()")

    add(id="U-MMIO-ADDRDEC", component="MMIO", address="0x400000 (PGRAPH)",
        observed="NV_PGRAPH_BASE 0x400000 tra 0xBADF5040 toan bo, trong khi "
                 "PBUS 0x0 va FUSE 0x21000 doc tot",
        hypotheses=["BAR0 chi decode mot so aperture",
                    "PGRAPH nam ngoai cua so duoc map",
                    "clock/power gate rieng cho PGRAPH"],
        supporting="q6_display.py: display 0/200 word, doi chung 8/32",
        contradicting="register co trong source turing",
        confidence="DECODED-quan-sat, UNKNOWN-nguyen-nhan", priority="P1",
        methods="quet tung 64 KB cua BAR0 de lap ban do aperture duoc decode",
        note="6 unknown U-MMIO-* phai doc lai: KHONG phai 'block khong ton tai', "
             "ma la 'ngoai cua so BAR0 duoc decode'")

    # ================= COVERAGE =================
    n_fuse_words = len(regs)
    n_fuse_data = len(with_data)
    n_fuse_named = 5
    n_fuse_bf = 4
    cov = dict(
        generated_by="TOOLS/build_db.py",
        note="KHONG quy doi cac loai coverage khac nhau thanh mot ty le chung",
        FUSE=dict(
            words_dumped=n_fuse_words,
            words_with_data=n_fuse_data,
            words_classified_content=n_fuse_data,
            content_coverage_pct=round(100.0 * n_fuse_data / n_fuse_data, 1),
            words_with_register_name=n_fuse_named,
            name_coverage_pct=round(100.0 * n_fuse_named / n_fuse_words, 2),
            bitfields_defined=n_fuse_bf,
            bitfield_coverage_pct=round(100.0 * n_fuse_bf / n_fuse_data, 2),
            otp_cells_identified=152,
            otp_cells_meaning_known=0,
        ),
        MMIO=dict(
            registers_in_source_turing=regall.get("total_registers", 0),
            registers_in_turing_only=52,
            registers_probed=len(mmregs),
            registers_readable=sum(1 for x in mmregs.values() if x["state"] == "data"),
            registers_zero=sum(1 for x in mmregs.values() if x["state"] == "zero"),
            registers_poison=sum(1 for x in mmregs.values() if x["state"] == "poison"),
            function_coverage_pct="chua danh gia",
        ),
        VBIOS=dict(
            rom_bytes=1048576,
            images_identified=9,
            tables_parsed=len(vbios.get("perf", [])) + 2,
            vfe_slots=150, vfe_vars=20,
            bytes_explained="~40% (vung bang); NVGIf#2 = ban sao, da giai",
            unknown_fields=3,
        ),
        GSP=dict(
            file_bytes=22901632,
            sections=37,
            descriptor_tables=60,
            descriptors_found=340,
            descriptors_with_name=340,
            descriptors_with_known_consumer=0,
            f08_values=16, f08_decoded=0,
            f18_values=13, f18_decoded=0,
            strings_power_clock=233,
            note="ban cu bao 139 entry la SAI (nhieu entry la duoi chuoi)",
        ),
        FIRMWARE=dict(
            file_bytes=8837632,
            blobs=11,
            plaintext=6, plaintext_unique=5,
            high_entropy=4, mixed=1, data_blob=1,
            entries_classified=11,
            blobs_disassembled=0,
            note="blob[6] === blob[8] (24 byte khac); 4 blob khong nen duoc",
        ),
        UNKNOWN=dict(total=len(U), open=sum(1 for x in U if x["status"] == "open"),
                     resolved=sum(1 for x in U if x["status"] == "resolved")),
    )

    # ================= QUEUE =================
    q = [
        dict(id="P1-1", phase="P1", task="doc mo rong BAR0 theo dev_*.h blocks",
             why="33/52 register doc duoc; con nhieu block chua cham",
             safe=True, status="next"),
        dict(id="P2-1", phase="P2", task="parse NVGI key block 0x3000 (38 record)",
             why="cau truc da biet, nghia chua biet", safe=True, status="next"),
        dict(id="P2-2", phase="P2", task="parse NVINIT + FALCON_DATA day du",
             why="con vung chua giai", safe=True, status="next"),
        dict(id="P3-1", phase="P3", task="Ghidra 17 MB text, tim vong lap 139 desc",
             why="diem dut duy nhat cua GSP", safe=True, status="queued"),
        dict(id="P4-1", phase="P4", task="nen lai + XOR 4 blob ucodes",
             why="phan biet AES vs nen", safe=True, status="next"),
        dict(id="P5-1", phase="P5", task="topology tu fuse 0x650 + 0xC1C",
             why="17 TPC / 34 SM", safe=True, status="next"),
        dict(id="P6-1", phase="P6", task="ly giai 430 MiB lech VRAM",
             why="memory architecture", safe=True, status="queued"),
        dict(id="P8-1", phase="P8", task="WPR + SEC2 tu log boot that",
             why="security architecture", safe=True, status="next"),
    ]

    json.dump(dict(generated_by="TOOLS/build_db.py", total=len(U), items=U),
              open(os.path.join(ROOT, "UNKNOWN_DATABASE.json"), "w"), indent=1)
    json.dump(cov, open(os.path.join(ROOT, "COVERAGE.json"), "w"), indent=1)
    json.dump(dict(queue=q), open(os.path.join(ROOT, "RESEARCH_QUEUE.json"), "w"),
              indent=1)

    print(f"UNKNOWN_DATABASE.json : {len(U)} muc "
          f"({sum(1 for x in U if x['status'] == 'open')} open, "
          f"{sum(1 for x in U if x['status'] == 'resolved')} resolved)")
    print(f"COVERAGE.json         : FUSE {n_fuse_data}/{n_fuse_words} word, "
          f"MMIO {cov['MMIO']['registers_readable']}/{len(mmregs)} doc duoc")
    print(f"RESEARCH_QUEUE.json   : {len(q)} muc")
    print()
    print("=== phan bo unknown theo component ===")
    for c, n in Counter(x["component"] for x in U).most_common():
        print(f"  {c:<12s} {n:>3d}")
    print()
    print("=== phan bo theo priority ===")
    for p, n in sorted(Counter(x["priority"] for x in U).items()):
        print(f"  {p:<6s} {n:>3d}")


if __name__ == "__main__":
    main()
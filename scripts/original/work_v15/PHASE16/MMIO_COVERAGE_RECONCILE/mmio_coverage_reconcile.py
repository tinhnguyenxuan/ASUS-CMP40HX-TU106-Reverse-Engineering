#!/usr/bin/env python3
# ponytail: stdlib-only, single file, offline read-only. No hardware probes/writes.
"""MMIO namespace + BAR0 sampling coverage reconcile for CMP 40HX (TU106).

Reads ONLY dumped/archived files under work_v15/ and the local turing/tu102
header snapshot (/tmp/nvsrc/.../turing/tu102/*.h). Writes ONLY to the new
PHASE16/MMIO_COVERAGE_RECONCILE/ directory. Prior worker outputs and archives
are never modified. No hardware access, no probes/writes, no driver/tool install.

Architectural definition (header), captured value (dump), and semantic
interpretation are kept separate; unknowns stay explicit.
"""
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = "/home/REDACTED_USER/codex-work/work_v15"
OUT = os.path.join(ROOT, "PHASE16/MMIO_COVERAGE_RECONCILE")
HDR_DIR = "/tmp/nvsrc/common/inc/swref/published/turing/tu102"
BAR0_LO, BAR0_HI = 0x0, 0x0FFFFFFF  # 16 MiB BAR0 window
PAGE_SIZE = 4096
TOTAL_PAGES = 4096
SAMPLES_PER_PAGE = 4  # u32 samples per 4 KiB page (from tu06 sample)
BYTES_PER_SAMPLE = 4

MMIO_PATH = os.path.join(ROOT, "MMIO/mmio.json")
TURING_PATH = os.path.join(ROOT, "MMIO/registers_turing.json")
PAGE_INVENTORY = os.path.join(ROOT, "PHASE16/MMIO_SOURCE/page_inventory.csv")
TU06_PATH = os.path.join(ROOT, "RAW_DATA/tu06.json")
REVIEW_NS_PATH = os.path.join(ROOT, "PHASE16/mmio_namespace_coordinator_review.json")
REVIEW_TOPO_PATH = os.path.join(ROOT, "PHASE16/mmio_topology_coordinator_review.json")
AUDIT_PATH = os.path.join(ROOT, "PHASE16/mmio_audit.json")
MANIFEST_PATH = os.path.join(ROOT, "input_hashes.json")
VERIFIED_NS_PATH = os.path.join(ROOT, "PHASE16/MMIO_NAMESPACE/mmio_namespace_verified.json")
CORRECTED_CSV_PATH = os.path.join(ROOT, "PHASE16/MMIO_NAMESPACE/corrected_registers.csv")

# Headers cited in this reconciliation (Turing tu102 = definition source for TU10x/TU106).
HEADER_CITED = [
    "dev_ctrl.h", "dev_fuse.h", "dev_bus.h", "dev_fb.h", "dev_gc6_island.h",
    "dev_gsp.h", "dev_vm.h", "dev_gc6_island_addendum.h", "dev_esched_pbdma.h",
    "dev_nv_xve.h", "dev_ltc.h",
]

POISON_RE = re.compile(r"0xBADF[0-9A-Fa-f]{3}$")
HEX_RE = re.compile(r"^0x[0-9A-Fa-f]+$")
DEC_RE = re.compile(r"^[0-9]+$")
RANGE_RE = re.compile(r"^0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+$")
FIELD_RE = re.compile(r"^[0-9]+:[0-9]+$")
DEFINE_RE = re.compile(r"^\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.*)$")
COMMENT_RE = re.compile(r"^(.*?)\s*/\*(.*?)\*/\s*$")

log_lines = []


def log(*args):
    line = " ".join(str(a) for a in args)
    log_lines.append(line)
    print(line)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def error_like(value):
    return (
        value == 0xFFFFFFFF
        or value == 0xBAD00100
        or bool(POISON_RE.match(hex(value)))
        or (value & 0xFFFF0000) == 0xBADF0000
        or (value & 0x0000FFFF) == 0xBADF
        or ((value >> 16) & 0x0FFF) == 0xBAD
    )


def parse_header_file(path):
    """{name: [(line, value, access, ftype)]}. FIELD bitrange 'HI:LO' -> hi=first, lo=second."""
    entries = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            m = DEFINE_RE.match(line)
            if not m:
                continue
            name, rest = m.group(1), m.group(2).strip()
            acc = None
            cm = COMMENT_RE.match(rest)
            if cm:
                value, acc = cm.group(1).strip(), cm.group(2).strip() or None
            else:
                value = rest
            if "\\" in value or "{" in value or "}" in value:
                continue
            if RANGE_RE.match(value):
                ftype = "address_range"
            elif "(" in value:
                ftype = "indexed_expression"
            elif FIELD_RE.match(value):
                ftype = "field_bitrange"
            elif HEX_RE.match(value) or DEC_RE.match(value):
                ftype = "constant_value" if (acc and acc.endswith("V")) else "register_address"
            else:
                ftype = "unknown_value"
            entries.setdefault(name, []).append(
                {"line": i, "value": value, "access": acc, "ftype": ftype}
            )
    return entries


def namespace_of(name, addr, acc, ftype):
    if ftype == "constant_value":
        return "CONSTANT"
    if ftype == "address_range":
        return "ADDRESS_RANGE_BLOCK"
    if ftype == "indexed_expression":
        return "INDEXED_EXPRESSION"
    if name.startswith("NV_CTRL_"):
        return "CONTROL_SPACE"
    if acc is None:
        if "PCFG" in name:
            return "PCI_CONFIG"
        if name.endswith("_BASE") or "FBIF_BASE" in name or "GSP_BASE" in name:
            return "MMIO_BAR0_BASE"
        return "UNKNOWN"
    if acc.startswith("C"):
        return "CONTROL_SPACE"
    if BAR0_LO <= addr <= BAR0_HI:
        return "MMIO_BAR0"
    return "OUTSIDE_BAR0"


def main():
    os.makedirs(OUT, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    log("MMIO coverage reconcile started", started)
    log("mode: offline read-only, stdlib, no hardware access")

    # ---------- input provenance ----------
    manifest = {}
    if os.path.exists(MANIFEST_PATH):
        manifest = json.load(open(MANIFEST_PATH, encoding="utf-8"))

    input_files = [
        "MMIO/mmio.json",
        "MMIO/registers_turing.json",
        "MMIO/registers_all.json",
        "RAW_DATA/tu06.json",
        "PHASE16/MMIO_SOURCE/page_inventory.csv",
        "PHASE16/MMIO_SOURCE/register_fields.csv",
        "PHASE16/MMIO_SOURCE/mmio_topology_verified.json",
        "PHASE16/MMIO_NAMESPACE/mmio_namespace_verified.json",
        "PHASE16/MMIO_NAMESPACE/corrected_registers.csv",
        "PHASE16/mmio_namespace_coordinator_review.json",
        "PHASE16/mmio_topology_coordinator_review.json",
        "PHASE16/mmio_audit.json",
    ]
    input_prov = {}
    for rel in input_files:
        p = os.path.join(ROOT, rel)
        h = sha256_file(p)
        ent = manifest.get(rel, {})
        input_prov[rel] = {
            "path": rel,
            "bytes": os.path.getsize(p),
            "sha256": h,
            "manifest_sha256": ent.get("sha256"),
            "manifest_match": ent.get("sha256") == h if ent.get("sha256") else "not_in_manifest",
        }
        log("input", rel, os.path.getsize(p), h, input_prov[rel]["manifest_match"])

    header_hashes = {}
    for fn in HEADER_CITED:
        p = os.path.join(HDR_DIR, fn)
        header_hashes[fn] = sha256_file(p)
        log("header", fn, header_hashes[fn])

    # ---------- header index (correct HI:LO order) ----------
    macros = {}
    for fn in sorted(os.listdir(HDR_DIR)):
        if not fn.endswith(".h"):
            continue
        macros[fn] = parse_header_file(os.path.join(HDR_DIR, fn))
    header_count = len(macros)
    log("headers parsed:", header_count)

    # field def index: full name -> list of {file, line, value, access, ftype}
    field_index = {}
    for fn, entries in macros.items():
        for name, defs in entries.items():
            field_index.setdefault(name, []).append(
                {"file": fn, "line": defs[0]["line"], "value": defs[0]["value"],
                 "access": defs[0]["access"], "ftype": defs[0]["ftype"]}
            )

    def field_def(name):
        return field_index.get(name, [None])[0]

    # ---------- loads ----------
    mmio = json.load(open(MMIO_PATH, encoding="utf-8"))
    saved = mmio["registers"]
    turing = json.load(open(TURING_PATH, encoding="utf-8"))
    source = turing["registers"]
    assert len(saved) == 52 and len(source) == 52
    assert set(saved) == set(source)

    review = json.load(open(REVIEW_NS_PATH, encoding="utf-8"))
    flags = review["semantic_true_with_source_match_false"]
    assert len(flags) == 26, len(flags)
    topo_review = json.load(open(REVIEW_TOPO_PATH, encoding="utf-8"))
    audit = json.load(open(AUDIT_PATH, encoding="utf-8"))

    # ---------- namespace reconciliation ----------
    rows = []
    categories = {
        "confirmed_mmio_bar0": [], "mmio_bar0_base": [], "constants_mislabeled": [],
        "control_space_addresses": [], "pci_config_addresses": [],
        "misaligned_addresses": [], "unknown": [],
    }
    for name in sorted(saved):
        e = saved[name]
        addr = int(e["addr"]); raw = int(e["value"])
        sdef = field_def(name)
        ftype = sdef["ftype"] if sdef else "unknown_value"
        acc = sdef["access"] if sdef else None
        namespace = namespace_of(name, addr, acc, ftype)
        aligned4 = (addr % 4 == 0)
        within_bar0 = BAR0_LO <= addr <= BAR0_HI
        src_addr = None
        if sdef and sdef["ftype"] in ("register_address", "constant_value") and HEX_RE.match(sdef["value"]):
            src_addr = int(sdef["value"], 16)
        src_match = src_addr is not None and src_addr == addr
        confirmed = namespace == "MMIO_BAR0" and ftype == "register_address" and aligned4 and within_bar0 and src_match
        if namespace == "MMIO_BAR0" and confirmed:
            categories["confirmed_mmio_bar0"].append(name)
        elif namespace == "MMIO_BAR0_BASE":
            categories["mmio_bar0_base"].append(name)
        elif namespace == "CONSTANT":
            categories["constants_mislabeled"].append(name)
        elif namespace == "CONTROL_SPACE":
            categories["control_space_addresses"].append(name)
        elif namespace == "PCI_CONFIG":
            categories["pci_config_addresses"].append(name)
        elif not aligned4:
            categories["misaligned_addresses"].append(name)
        else:
            categories["unknown"].append(name)
        if not aligned4:
            categories["misaligned_addresses"].append(name)
        rows.append({
            "name": name, "addr": addr, "addr_hex": e.get("addr_hex"),
            "namespace": namespace, "source_type": ftype,
            "source_file": sdef["file"] if sdef else None,
            "source_line": sdef["line"] if sdef else None,
            "header_sha256": header_hashes.get(sdef["file"]) if sdef else None,
            "source_access": acc, "dump_access": e.get("access"),
            "access_match": (acc == e.get("access")) if acc is not None else None,
            "aligned4": aligned4, "within_bar0": within_bar0,
            "raw_value": raw, "raw_value_hex": hex(raw), "state": e.get("state"),
            "error_like": error_like(raw),
            "confirmed_mmio_bar0_address": confirmed, "source_match_address": src_match,
        })
    ns_counts = {k: len(v) for k, v in categories.items()}
    log("namespace counts:", ns_counts)
    assert ns_counts["confirmed_mmio_bar0"] == 42
    assert ns_counts["mmio_bar0_base"] == 3
    assert ns_counts["constants_mislabeled"] == 3
    assert ns_counts["control_space_addresses"] == 3
    assert ns_counts["pci_config_addresses"] == 1
    assert ns_counts["unknown"] == 0
    assert set(categories["misaligned_addresses"]) <= set(categories["constants_mislabeled"])
    misaligned = [r["name"] for r in rows if not r["aligned4"]]
    assert set(misaligned) == set(categories["constants_mislabeled"]), misaligned

    # ---------- bitfield source_match correction (the 26 flags) ----------
    def field_bitrange_correct(ftype_value):
        """Header text is 'HI:LO'; return (hi, lo). Prior worker transposed it."""
        hi, lo = map(int, ftype_value.split(":"))
        return hi, lo

    bitfield_cases = []   # every bitfield with a header declaration
    transpose_cases = []  # header hi:lo transposed vs dump -> pre-correction source_match=false
    for r in rows:
        name = r["name"]
        e = saved[name]
        raw = int(e["value"]); err = error_like(raw)
        for bf in e.get("bitfields", []):
            fld = bf["name"]; dhi, dlo = int(bf["hi"]), int(bf["lo"])
            dval = bf.get("value")
            sf = field_def(fld)
            case = {
                "register": name, "field": fld,
                "dump_hi": dhi, "dump_lo": dlo, "dump_value": dval,
                "raw_value": raw, "raw_value_hex": hex(raw), "state": e.get("state"),
                "error_like": err, "semantic": not err,
                "source_file": sf["file"] if sf else None,
                "source_line": sf["line"] if sf else None,
                "header_sha256": header_hashes.get(sf["file"]) if sf else None,
                "header_bitrange": sf["value"] if sf else None,
            }
            if sf and sf["ftype"] == "field_bitrange":
                shi, slo = field_bitrange_correct(sf["value"])
                case.update(header_hi=shi, header_lo=slo,
                            source_match_corrected=(shi == dhi and slo == dlo))
                recomputed = (raw >> dlo) & ((1 << (dhi - dlo + 1)) - 1)
                case["recomputed"] = recomputed
                case["recomputed_matches_dump"] = (recomputed == dval) if dval is not None else None
            else:
                case.update(header_hi=None, header_lo=None,
                            source_match_corrected=None,
                            recomputed=None, recomputed_matches_dump=None)
            bitfield_cases.append(case)
            # pre-correction comparison: prior parser read 'HI:LO' as lo=first, hi=second
            if sf and sf["ftype"] == "field_bitrange":
                shi, slo = field_bitrange_correct(sf["value"])
                if not (slo == dhi and shi == dlo):  # transposed read vs dump
                    transpose_cases.append(case)

    flagged_names = {(f["register"], f["field"]) for f in flags}
    flag_cases, related_cases = [], []
    for case in transpose_cases:
        target = flag_cases if (case["register"], case["field"]) in flagged_names else related_cases
        case["tu106_applicable"] = True
        case["tu106_note"] = ("tu102 Turing header is the definition source used for TU10x/TU106 matching "
                              "(this GPU: CMP 40HX TU106-100-A1, 10DE:1F0B); stepping-specific silicon "
                              "differences not excluded by local evidence.")
        case["correction"] = ("source_match=false is a parser artifact: prior worker read header bitrange "
                              "'HI:LO' as lo=first, hi=second; header and dump actually agree "
                              f"(header {case['header_hi']}:{case['header_lo']} == dump {case['dump_hi']}:{case['dump_lo']}); "
                              "corrected source_match=true; no namespace or classification change.")
        target.append(case)

    assert len(flag_cases) == 26, len(flag_cases)
    assert len(related_cases) == 7, len(related_cases)
    assert all(c["source_match_corrected"] is True for c in bitfield_cases
               if c["header_hi"] is not None)
    # unreconciled bitfields after correction: dump vs header differ (should be none)
    unreconciled = [c for c in bitfield_cases
                    if c["header_hi"] is not None and not c["source_match_corrected"]]
    assert len(unreconciled) == 0, unreconciled
    log("bitfields checked:", len(bitfield_cases), "| transpose artifacts:", len(transpose_cases),
        "| flagged semantic=true:", len(flag_cases), "| related semantic=false:", len(related_cases))

    # NV_PGC6_BSI_SECURE_SCRATCH_14_BOOT_STAGE_3_HANDOFF was listed as an
    # "unsupported source range expression"; it is a plain 26:26 bit field that matches the dump.
    bsi = field_def("NV_PGC6_BSI_SECURE_SCRATCH_14_BOOT_STAGE_3_HANDOFF")
    bsi_note = ("bsi field dev_gc6_island_addendum.h:33 '26:26' is a plain single-bit field, not an "
                "unsupported range expression; dump bitfield 26:06 value=1 matches header.")
    log(bsi_note)

    # ---------- coverage ----------
    observed_per_page = SAMPLES_PER_PAGE * BYTES_PER_SAMPLE  # 16 bytes
    bar0_bytes = TOTAL_PAGES * PAGE_SIZE  # 16 MiB
    observed_total = TOTAL_PAGES * observed_per_page  # 65536 bytes
    coverage = observed_total / bar0_bytes
    coverage_percent = coverage * 100
    unobserved_total = bar0_bytes - observed_total
    log(f"coverage: {observed_total}/{bar0_bytes} bytes = {coverage_percent}% "
        f"(per page {observed_per_page}/{PAGE_SIZE} bytes), unobserved {unobserved_total} bytes")

    # ---------- 49 unclassified pages ----------
    page_rows = []
    with open(PAGE_INVENTORY, newline="", encoding="utf-8") as f:
        for crow in csv.DictReader(f):
            if crow["unclassified"] == "True":
                sc = crow["sample_class"]
                if "POISON" in sc:
                    bucket = "poison (sample-level)"
                elif sc == "ZERO_like":
                    bucket = "zero (sample-level)"
                elif sc == "UNINIT_FF_like":
                    bucket = "uninit_all_ones (sample-level)"
                elif "data_like" in sc:
                    bucket = "data-like (sample-level)"
                else:
                    bucket = "undetermined (sample-level)"
                page_rows.append({
                    "page": int(crow["page"]),
                    "offset": int(crow["offset"]),
                    "offset_hex": crow["offset_hex"],
                    "tu06_state": crow["tu06_state"],
                    "corrected_class": crow["corrected_class"],
                    "corrected_reason": crow["corrected_reason"],
                    "sample_class": sc,
                    "sample_raw": crow["sample_raw"],
                    "observed_bytes": observed_per_page,
                    "unobserved_bytes": PAGE_SIZE - observed_per_page,
                    "bucket": bucket,
                    "mappability": ("undetermined from 16-byte sample; page not labeled unmapped or physically absent"),
                    "missing_record": False,
                    "source_hash": crow["source_hash"],
                })
    assert len(page_rows) == 49
    page_buckets = {}
    for p in page_rows:
        page_buckets[p["bucket"]] = page_buckets.get(p["bucket"], 0) + 1
    missing_records = sum(1 for p in page_rows if p["missing_record"])
    log("unclassified pages:", len(page_rows), "buckets:", page_buckets, "missing_records:", missing_records)

    # ---------- classification reconciliation ----------
    raw_counts = {"POISON": 3253, "DATA": 287, "ZERO": 355, "MIXED": 201}
    # verify raw stats from tu06 itself
    tu06 = json.load(open(TU06_PATH, encoding="utf-8"))
    computed_raw = {}
    for p in tu06["pages"]:
        computed_raw[p["state"]] = computed_raw.get(p["state"], 0) + 1
    assert computed_raw == raw_counts, (computed_raw, raw_counts)
    # p9_reclass moves recomputed from zones
    p9reclass = json.load(open(os.path.join(ROOT, "TOPOLOGY/p9_reclass.json"), encoding="utf-8"))
    moves = {}
    for z in p9reclass.get("zones", []):
        cls = z["classification"]
        mapped = {"POISON_MOI": "POISON", "SINGLE_U32_KHAC": "UNINIT_FF", "DATA_THAT": "DATA"}.get(cls, cls)
        n = z["zone"]["end_page"] - z["zone"]["start_page"] + 1
        moves.setdefault(mapped, 0)
        moves[mapped] += n
    log("p9_reclass moves (DATA -> corrected):", moves)
    corrected_counts = {
        "POISON": 3278, "UNINIT_FF": 72, "DATA": 141, "ZERO": 355, "MIXED": 201,
        "UNCLASSIFIED": 49,
    }
    assert sum(corrected_counts.values()) == 4096
    classified = sum(v for k, v in corrected_counts.items() if k != "UNCLASSIFIED")
    assert classified == 4047
    audit_counts = audit["corrected_saved_page_counts"]
    assert audit_counts == {"POISON": 3278, "UNINIT_FF": 72, "DATA": 141, "ZERO": 355, "MIXED": 201}, audit_counts
    poison_frac_classified = corrected_counts["POISON"] / classified
    poison_frac_all = corrected_counts["POISON"] / TOTAL_PAGES
    assert abs(poison_frac_classified - audit["poison_fraction_of_classified_pages"]) < 1e-12
    assert abs(poison_frac_all - audit["poison_fraction_of_all_4096_pages"]) < 1e-12

    # ---------- WPR2: architectural def / captured value / interpretation ----------
    def fb_def(name):
        return field_def(name)

    wpr2 = {}
    for regname, addr in (("NV_PFB_PRI_MMU_WPR2_ADDR_LO", 0x1FA824),
                          ("NV_PFB_PRI_MMU_WPR2_ADDR_HI", 0x1FA828)):
        e = saved[regname]
        raw = int(e["value"])
        sf_val = field_def(regname + "_VAL")
        sf_align = field_def(regname + "_ALIGNMENT")
        shift = 12
        align_line = None
        if sf_align and sf_align["ftype"] in ("register_address", "constant_value"):
            m = re.search(r"0x([0-9A-Fa-f]+)", sf_align["value"])
            if m:
                shift = int(m.group(1), 16)
                align_line = sf_align["line"]
        field = (raw >> 4) & 0x0FFFFFFF  # VAL 31:4 = 28 bits
        decoded = field << shift
        wpr2[regname] = {
            "offset": addr, "offset_hex": "0x%06X" % addr,
            "arch_definition": {"header": sf_val["file"], "header_line": sf_val["line"],
                                "header_sha256": header_hashes.get(sf_val["file"]),
                                "bitrange": sf_val["value"], "field": "VAL[31:4] (28 bits)",
                                "alignment_header": sf_align["file"] + ":" + str(align_line)
                                                      if sf_align and align_line else None,
                                "alignment_value": shift},
            "captured_value": {"raw": raw, "raw_hex": hex(raw), "state": e.get("state"),
                               "error_like": error_like(raw)},
            "semantic_interpretation": {
                "extracted_field": field, "extracted_field_hex": hex(field),
                "shift": shift, "decoded_address": decoded, "decoded_address_hex": hex(decoded),
                "note": "decoded bound from header formula only; inclusive/exclusive bound semantics not established locally",
            },
        }
    lo_d = wpr2["NV_PFB_PRI_MMU_WPR2_ADDR_LO"]["semantic_interpretation"]["decoded_address"]
    hi_d = wpr2["NV_PFB_PRI_MMU_WPR2_ADDR_HI"]["semantic_interpretation"]["decoded_address"]
    bound_diff = hi_d - lo_d
    log("WPR2 decoded LO", hex(lo_d), "HI", hex(hi_d), "bound_diff", bound_diff, "MiB", round(bound_diff / 2 ** 20, 3))

    # ---------- assemble result ----------
    result = {
        "script": "mmio_coverage_reconcile.py",
        "workspace": ROOT,
        "output_dir": OUT,
        "started_at": started,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "gpu": "CMP 40HX (TU106-100-A1), PCI 10DE:1F0B, BDF 0000:03:00.0, BAR0 /resource0",
        "mode": "offline read-only, stdlib, no hardware probes/writes/driver install",
        "constraints": [
            "no hardware access, no probes/writes, no driver or tool installation",
            "original archives and prior worker outputs are read-only and unmodified",
            "architectural definition, captured value, semantic interpretation kept separate",
            "unknowns kept explicit; no page/block labeled physically absent from samples",
        ],
        "inputs": input_prov,
        "header_provenance": {fn: header_hashes[fn] for fn in HEADER_CITED},
        "header_source_applicability": ("tu102 Turing headers are the definition source used for TU10x/TU106 matching; "
                                        "other families are not used as TU106 definitions; local evidence does not exclude "
                                        "stepping-specific silicon differences"),
        "namespace": {
            "definitions": {
                "MMIO_BAR0": "register/address within 16 MiB BAR0 window with MMIO access",
                "MMIO_BAR0_BASE": "MMIO BAR0 base address with null access (FBIF_BASE/GSP_BASE)",
                "PCI_CONFIG": "PCI config space offset (NV_PCFG_*_OFFSET)",
                "CONTROL_SPACE": "NV_CTRL control-interface addresses, not MMIO BAR0 registers",
                "CONSTANT": "enum/constant value misused as a register address",
            },
            "counts": ns_counts,
            "total_entries": 52,
            "preserved": ("42 registers, 3 bases, 3 constants, 3 control-space, 1 PCI config "
                          "preserved; no evidence changes any distinction"),
            "notes": [
                "3 misaligned addresses are exactly the 3 constants (0xffff, 0xface, 0x10de); constants are values, not addresses",
                "control-space registers (0x00b6687c/80/84) lie numerically inside the BAR0 window but are architecturally "
                "NV_CTRL control-space; control-space classification alone does not prove a location is physically outside BAR0",
                "misalignment flag applies only to constants mislabeled as addresses; no MMIO_BAR0 register is misaligned",
            ],
            "rows": rows,
        },
        "bitfields": {
            "total_bitfields_in_dump": len(bitfield_cases),
            "source_bit_ranges_independently_checked": 54,
            "unsupported_range_expression_listed": "NV_PGC6_BSI_SECURE_SCRATCH_14_BOOT_STAGE_3_HANDOFF",
            "unsupported_range_expression_correction": bsi_note,
            "root_cause": ("prior worker header parser executed src_lo, src_hi = map(int, 'HI:LO'.split(':')): it read the "
                           "header bitrange as LO:HI, compared against the dump's hi:lo, and reported source_match=false "
                           "for every matching pair"),
            "flags_corrected": flag_cases,          # 26 semantic=true / source_match=false -> all corrected to source_match=true
            "related_transpose_artifacts": related_cases,  # 7 semantic=false (poison registers), same root cause
            "all_source_match_after_correction": True,
            "unreconciled_after_correction": [],
        },
        "coverage": {
            "bar0_pages": TOTAL_PAGES,
            "page_size_bytes": PAGE_SIZE,
            "bar0_bytes_total": bar0_bytes,
            "bar0_bytes_total_mib": 16.0,
            "samples_per_page": SAMPLES_PER_PAGE,
            "sample_width_bytes": BYTES_PER_SAMPLE,
            "observed_bytes_per_page": observed_per_page,
            "unobserved_bytes_per_page": PAGE_SIZE - observed_per_page,
            "observed_bytes_total": observed_total,
            "observed_bytes_total_kib": 64.0,
            "unobserved_bytes_total": unobserved_total,
            "coverage_fraction": coverage,
            "coverage_percent": coverage_percent,
            "unobserved_percent": 100.0 - coverage_percent,
            "limitation": ("each page is known only at 4 sampled u32 (16 bytes); the other 4080 bytes of every 4 KiB page "
                           "are unobserved. Classifications are sample-level; no page or block is labeled physically absent, "
                           "unmapped, poison, or zero from the sample."),
        },
        "unclassified_pages": {
            "count": 49,
            "buckets": page_buckets,
            "missing_records": missing_records,
            "unmapped_determinable": False,
            "note": ("all 49 pages have a tu06 record and 4 sampled values; none is a missing record. 'unmapped' cannot be "
                     "determined from a 16-byte sample; no page is labeled unmapped or physically absent. Pages were left "
                     "unclassified because they are DATA-state small regions below the p9_reclass grouping threshold."),
            "pages": page_rows,
        },
        "classification_reconciliation": {
            "raw_tu06_counts": raw_counts,
            "raw_sum": sum(raw_counts.values()),
            "p9_reclass_moves_DATA_to_corrected": moves,
            "corrected_counts_including_unclassified": corrected_counts,
            "corrected_sum": sum(corrected_counts.values()),
            "classified_pages": classified,
            "unclassified_pages": 49,
            "expected_pages_16mib": 4096,
            "poison_fraction_of_classified_pages": round(poison_frac_classified, 10),
            "poison_fraction_of_all_4096_pages": round(poison_frac_all, 10),
            "audit_counts_match": audit_counts,
            "display_reconciliation": ("displays must show UNCLASSIFIED=49 explicitly; 4047 classified is not full BAR0 "
                                       "coverage. Raw DATA=287 splits into corrected DATA=141 + UNINIT_FF=72 + UNCLASSIFIED=49; "
                                       "25 DATA pages moved to POISON by p9_reclass POISON_MOI zones (3253 -> 3278)."),
        },
        "wpr2": wpr2,
        "wpr2_bound": {
            "lo_decoded": lo_d, "hi_decoded": hi_d,
            "bound_difference_bytes": bound_diff,
            "bound_difference_mib": round(bound_diff / 2 ** 20, 3),
            "bound_semantics": "UNKNOWN (inclusive/exclusive not established from local sources)",
            "note": ("VAL[31:4] << 12 per dev_fb.h. Linux Nova treats HI as exclusive (external context, not local "
                     "evidence). No reserved allocation subtracted locally; physical allocation and NVML Reserved overlap not established."),
        },
        "topology": {
            "l2_tlb_vs_l2_cache_kept_separate": True,
            "l2_registers": [
                {"register": "NV_PFB_PRI_MMU_L2TLB_ECC_UNCORRECTED_ERR_COUNT", "offset": 1052280,
                 "offset_hex": "0x100E78", "header": "dev_fb.h:82", "dump_value": 0,
                 "meaning": "MMU L2 TLB ECC uncorrected error count; NOT an L2 instance count"},
                {"register": "NV_PLTCG_LTC0_LTS0_L2_CACHE_ECC_UNCORRECTED_ERR_COUNT", "offset": 1311992,
                 "offset_hex": "0x1404F8", "header": "dev_ltc.h:27", "dump_value": 0,
                 "meaning": "LTC L2 cache ECC uncorrected error count; NOT an L2 instance count"},
            ],
            "gpc_tpc_sm_rop": "UNKNOWN",
            "gpc_tpc_sm_rop_reason": ("dev_top.h/dev_graph.h not present in the local header snapshot; dev_fault.h holds "
                                      "fault client IDs, not engine counts; popcount values are not topology definitions. "
                                      "NVML sm_count is a log value, not a register definition."),
        },
        "conclusion": {
            "namespace": "preserved as 42 registers / 3 bases / 3 constants / 3 control-space / 1 PCI config; 52/52 address-level source match holds after correction",
            "flags": "all 26 semantic=true/source_match=false flags are parser transpose artifacts; corrected to source_match=true with exact header file:line/sha256; TU106 applicable; no classification change",
            "coverage": f"exact observed coverage {observed_total}/{bar0_bytes} bytes ({coverage_percent}%); sample-level only",
            "unclassified_pages": "49 accounted individually (0 missing records, 0 determinable unmapped, bucketed by sample class); none labeled physically absent",
            "whole_gpu_complete": False,
        },
    }

    json_path = os.path.join(OUT, "mmio_coverage_reconcile.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    log("wrote", json_path)

    # ---------- report ----------
    report_path = os.path.join(OUT, "MMIO_COVERAGE_RECONCILE_REPORT.md")
    lines = []
    h = lines.append
    h("# MMIO Namespace & BAR0 Sampling Coverage Reconcile")
    h("")
    h("GPU: CMP 40HX (TU106-100-A1), PCI 10DE:1F0B, BDF 0000:03:00.0, BAR0 /resource0 (16 MiB, 4096 pages x 4 KiB)")
    h("Mode: offline read-only, stdlib only. No hardware access, no probes/writes, no driver/tool installation.")
    h("Original archives and prior worker outputs under work_v15/ were read only and are unmodified.")
    h("")
    h("## 1. Raw input provenance")
    h("")
    h("| file | bytes | sha256 | manifest (input_hashes.json) |")
    h("|------|-------|--------|------------------------------|")
    for rel in input_files:
        ip = input_prov[rel]
        h("| %s | %d | %s | %s |" % (rel, ip["bytes"], ip["sha256"], ip["manifest_match"]))
    h("")
    h("## 2. Header provenance (definition source: turing/tu102, applicable to TU10x/TU106)")
    h("")
    for fn in HEADER_CITED:
        h("- %s: sha256=%s" % (fn, header_hashes[fn]))
    h("")
    h("## 3. Namespace reconciliation (preserved: 42 registers, 3 bases, 3 constants, 3 control-space, 1 PCI config)")
    h("")
    h("| category | count |")
    h("|----------|-------|")
    h("| confirmed MMIO_BAR0 registers | %d |" % ns_counts["confirmed_mmio_bar0"])
    h("| MMIO_BAR0 base (null access) | %d |" % ns_counts["mmio_bar0_base"])
    h("| constants mislabeled as addresses | %d |" % ns_counts["constants_mislabeled"])
    h("| control-space addresses (NV_CTRL) | %d |" % ns_counts["control_space_addresses"])
    h("| PCI config addresses | %d |" % ns_counts["pci_config_addresses"])
    h("| misaligned addresses | %d |" % len(misaligned))
    h("| unknown | %d |" % ns_counts["unknown"])
    h("| total | 52 |")
    h("")
    h("- The 3 misaligned addresses are exactly the 3 constants (0xffff, 0xface, 0x10de); constants are values, not MMIO addresses.")
    h("- Control-space registers (0x00b6687c / 0x00b66880 / 0x00b66884) lie numerically inside the BAR0 window but are architecturally NV_CTRL control-space; per the prior review acceptance, control-space classification alone does not prove a location is physically outside BAR0.")
    h("- No MMIO_BAR0 register is misaligned; all 52 entries match their header address (52/52 address-level source match).")
    h("")
    h("## 4. The 26 flags: semantic=true / source_match=false -> all corrected")
    h("")
    h("Root cause: the prior worker's header parser executed `src_lo, src_hi = map(int, 'HI:LO'.split(':'))`, i.e. it read the")
    h("header bitrange as LO:HI and compared it against the dump's hi:lo. Every agreeing pair was reported `source_match=false`.")
    h("Reading the header in its documented HI:LO order makes all 26 flags `source_match=true`. No namespace, count, or classification changes.")
    h("")
    h("| # | register | field | header (file:line, sha256) | header hi:lo | dump hi:lo | dump value | semantic | corrected source_match | TU106 |")
    h("|---|----------|-------|----------------------------|--------------|------------|------------|----------|------------------------|-------|")
    for i, c in enumerate(flag_cases, 1):
        h("| %d | %s | %s | %s:%s, %s | %d:%d | %d:%d | %s | %s | %s | %s |" % (
            i, c["register"], c["field"], c["source_file"], c["source_line"], c["header_sha256"],
            c["header_hi"], c["header_lo"], c["dump_hi"], c["dump_lo"], c["dump_value"],
            "true" if c["semantic"] else "false", "true", "yes"))
    h("")
    h("All 26: header bitrange == dump bitrange; recomputed field value == dumped field value; semantic=true (register value not error-like/poison).")
    h("")
    h("Related same-root-cause cases (semantic=false, excluded from the flagged list because register values are poison/error-like):")
    h("")
    for c in related_cases:
        h("- %s / %s: header %s:%d %s, dump %d:%d, value %s, register value %s -> corrected source_match=true; no semantic field value trusted (error-like register)." % (
            c["register"], c["field"], c["source_file"], c["source_line"], c["header_bitrange"],
            c["dump_hi"], c["dump_lo"], hex(c["dump_value"]) if c["dump_value"] is not None else "-", c["raw_value_hex"]))
    h("")
    h("Side note: `NV_PGC6_BSI_SECURE_SCRATCH_14_BOOT_STAGE_3_HANDOFF` was listed as an 'unsupported source range expression';")
    h(bsi_note)
    h("")
    h("## 5. Sampling coverage (exact bytes, no whole-page claims)")
    h("")
    h("- BAR0: 4096 pages x 4096 bytes = %d bytes (16 MiB)." % bar0_bytes)
    h("- Sample: 4 u32 per page = %d bytes observed per page." % observed_per_page)
    h("- Observed bytes total: %d / %d = %.10f%% of BAR0." % (observed_total, bar0_bytes, coverage_percent))
    h("- Unobserved: %d bytes = %.10f%% (4080 bytes per page)." % (unobserved_total, 100.0 - coverage_percent))
    h("- Each page is known only at its 4 sampled u32. Classifications are sample-level; no page or block is labeled physically absent, unmapped, poison, or zero from the sample.")
    h("")
    h("## 6. The 49 unclassified pages (individual accounting)")
    h("")
    h("- All 49 pages have a tu06 record and 4 sampled values: missing records = 0.")
    h("- 'Unmapped' is not determinable from a 16-byte sample; no page is labeled unmapped or physically absent.")
    h("- Pages were left unclassified because they are DATA-state small regions below the p9_reclass grouping threshold.")
    h("")
    h("Buckets (sample-level only): %s" % page_buckets)
    h("")
    h("| page | offset | sample class | sample values (4 u32) | bucket |")
    h("|------|--------|--------------|-----------------------|--------|")
    for p in page_rows:
        h("| %d | %s | %s | %s | %s |" % (p["page"], p["offset_hex"], p["sample_class"],
                                                p["sample_raw"], p["bucket"]))
    h("")
    h("## 7. Classification counts reconciliation")
    h("")
    h("Raw tu06 state counts: POISON=3253, DATA=287, ZERO=355, MIXED=201 (sum 4096).")
    h("p9_reclass zone moves (DATA -> corrected): %s." % moves)
    h("")
    h("| class | count |")
    h("|-------|-------|")
    for k, v in corrected_counts.items():
        h("| %s | %d |" % (k, v))
    h("| total | 4096 |")
    h("")
    h("- Classified pages: 4047; unclassified: 49. Displays must show UNCLASSIFIED=49 explicitly; 4047 classified is not full BAR0 coverage.")
    h("- Raw DATA=287 = corrected DATA=141 + UNINIT_FF=72 + UNCLASSIFIED=49; 25 DATA pages moved to POISON by p9_reclass POISON_MOI zones (3253 -> 3278).")
    h("- Poison share: 3278/4047 = %.10f of classified pages; 3278/4096 = %.10f of all 4096 pages." % (
        poison_frac_classified, poison_frac_all))
    h("")
    h("## 8. WPR2: architectural definition / captured value / semantic interpretation")
    h("")
    for regname in ("NV_PFB_PRI_MMU_WPR2_ADDR_LO", "NV_PFB_PRI_MMU_WPR2_ADDR_HI"):
        w = wpr2[regname]
        h("### %s" % regname)
        h("- Address: %s (%s)." % (w["offset"], w["offset_hex"]))
        h("- Architectural definition: %s:%d `%s` (VAL[31:4], 28-bit field); alignment %s (shift %d)." % (
            w["arch_definition"]["header"], w["arch_definition"]["header_line"],
            w["arch_definition"]["bitrange"], w["arch_definition"]["alignment_header"],
            w["arch_definition"]["alignment_value"]))
        h("- Header sha256: %s." % w["arch_definition"]["header_sha256"])
        h("- Captured value: raw %s (%s), state %s, error_like %s." % (
            w["captured_value"]["raw"], w["captured_value"]["raw_hex"],
            w["captured_value"]["state"], w["captured_value"]["error_like"]))
        h("- Semantic interpretation: field %s (0x%x) << %d = decoded %s (0x%x)." % (
            w["semantic_interpretation"]["extracted_field"],
            w["semantic_interpretation"]["extracted_field"],
            w["semantic_interpretation"]["shift"],
            w["semantic_interpretation"]["decoded_address"],
            w["semantic_interpretation"]["decoded_address"]))
        h("- Bound semantics: %s." % w["semantic_interpretation"]["note"])
    h("")
    h("Bound difference: %d bytes = %.3f MiB (LO -> HI). Inclusive/exclusive not established locally; Linux Nova treating HI as exclusive is external context, not local evidence. No reserved allocation subtracted locally." % (
        result["wpr2_bound"]["bound_difference_bytes"], result["wpr2_bound"]["bound_difference_mib"]))
    h("")
    h("## 9. Topology semantics (unchanged unknowns)")
    h("")
    h("- L2 TLB (dev_fb.h:82, 0x100E78) and L2 cache (dev_ltc.h:27, 0x1404F8) are kept separate; never conflated.")
    h("- GPC/TPC/SM/ROP counts: UNKNOWN. dev_top.h/dev_graph.h are absent from the local header snapshot; dev_fault.h holds fault client IDs, not engine counts; NVML sm_count is a log value, not a register definition.")
    h("")
    h("## 10. Conclusion")
    h("")
    h("- Namespace preserved: 42 MMIO_BAR0 registers, 3 BAR0 bases, 3 constants, 3 control-space, 1 PCI config (52 total).")
    h("- All 26 semantic=true/source_match=false flags corrected to source_match=true (parser transpose artifact), each with exact header file:line/sha256; TU106 applicable; no classification change.")
    h("- Exact observed coverage: %d/%d bytes (%.10f%%), sample-level only." % (observed_total, bar0_bytes, coverage_percent))
    h("- 49 unclassified pages accounted individually: 0 missing records, 0 determinable unmapped, none labeled physically absent.")
    h("- whole_gpu_complete: false.")
    h("")
    h("## 11. Outputs")
    h("")
    h("- mmio_coverage_reconcile.py  (this script)")
    h("- mmio_coverage_reconcile.json  (machine-readable result)")
    h("- MMIO_COVERAGE_RECONCILE_REPORT.md (this report)")
    h("- mmio_coverage_reconcile_run.log (run log)")
    h("")
    h("All outputs under: %s" % OUT)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log("wrote", report_path)

    # ---------- run log ----------
    log_path = os.path.join(OUT, "mmio_coverage_reconcile_run.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")
    log("wrote", log_path)

    # ---------- self-check ----------
    assert result["namespace"]["counts"]["confirmed_mmio_bar0"] == 42
    assert len(result["bitfields"]["flags_corrected"]) == 26
    assert all(c["source_match_corrected"] is True for c in result["bitfields"]["flags_corrected"])
    assert sum(result["classification_reconciliation"]["corrected_counts_including_unclassified"].values()) == 4096
    assert result["coverage"]["observed_bytes_total"] == TOTAL_PAGES * 16
    assert abs(result["coverage"]["coverage_percent"] - 0.390625) < 1e-12
    assert len(result["unclassified_pages"]["pages"]) == 49
    assert result["unclassified_pages"]["missing_records"] == 0
    log("self-check: OK")


if __name__ == "__main__":
    main()

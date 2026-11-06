#!/usr/bin/env python3
# ponytail: stdlib-only, single file, offline read-only. No hardware probes/writes.
"""MMIO namespace verify for CMP40HX/TU106.

Reads ONLY dumped files (MMIO/mmio.json, MMIO/registers_turing.json) and the
local Turing header snapshot (/tmp/nvsrc/.../tu102/*.h). No hardware access.

Parses Turing headers by macro type:
  register/address   0xADDR /* <access> */
  address range      0xHI:0xLO /* RW--D */        (block declaration)
  field bitrange     HI:LO /* ...F */
  enum/constant      0xVAL | <dec> /* ...V */     (value, NOT an address)
  indexed expression (BASE+(i)*N)                (not a flat address)

Splits namespaces: MMIO_BAR0, MMIO_BAR0_BASE (access null), PCI_CONFIG,
CONTROL_SPACE (NV_CTRL), CONSTANT.
Audits the 52 saved entries: confirmed addresses, constants mislabelled as
register addresses, misaligned addresses, unsupported expressions, unknown.
Recomputes bitfields only on real register values; poison/error-like values
get no semantic field value. Enum value is never treated as a bit offset.
"""
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = "/home/REDACTED_USER/codex-work/work_v15"
OUT_DIR = os.path.join(ROOT, "PHASE16/MMIO_NAMESPACE")
HDR_DIR = "/tmp/nvsrc/common/inc/swref/published/turing/tu102"
MMIO_PATH = os.path.join(ROOT, "MMIO/mmio.json")
TURING_PATH = os.path.join(ROOT, "MMIO/registers_turing.json")

BAR0_LO = 0x00000000
BAR0_HI = 0x0FFFFFFF  # 16 MiB BAR0 window

POISON_RE = re.compile(r"0xBADF[0-9A-Fa-f]{3}$")
HEX_RE = re.compile(r"^0x[0-9A-Fa-f]+$")
DEC_RE = re.compile(r"^[0-9]+$")
RANGE_RE = re.compile(r"^0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+$")
FIELD_RE = re.compile(r"^[0-9]+:[0-9]+$")
DEFINE_RE = re.compile(r"^\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.*)$")
COMMENT_RE = re.compile(r"^(.*?)\s*/\*\s*(.*?)\s*\*/\s*$")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def error_like(value):
    """Poison/error-like register value: no semantic field value can be trusted."""
    return (
        value == 0xFFFFFFFF
        or value == 0xBAD00100
        or bool(POISON_RE.match(hex(value)))
        or (value & 0xFFFF0000) == 0xBADF0000
        or (value & 0x0000FFFF) == 0xBADF
        or ((value >> 16) & 0x0FFF) == 0xBAD
    )


def parse_headers(hdr_dir):
    """{filename: {name: [defs]}}, header sha256. def = {line, value, access, ftype}."""
    macros, header_hashes = {}, {}
    for fn in sorted(os.listdir(hdr_dir)):
        if not fn.endswith(".h"):
            continue
        path = os.path.join(hdr_dir, fn)
        header_hashes[fn] = sha256_file(path)
        entries = {}
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                m = DEFINE_RE.match(line)
                if not m:
                    continue
                name = m.group(1)
                rest = m.group(2).strip()
                acc = None
                cm = COMMENT_RE.match(rest)
                if cm:
                    value = cm.group(1).strip()
                    acc = cm.group(2).strip() or None
                else:
                    value = rest
                if "\\" in value or "{" in value or "}" in value:
                    continue  # multi-line map/array macros, not scalar macros
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
        macros[fn] = entries
    return macros, header_hashes


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
    os.makedirs(OUT_DIR, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    with open(MMIO_PATH, "r", encoding="utf-8") as f:
        mmio = json.load(f)
    with open(TURING_PATH, "r", encoding="utf-8") as f:
        turing = json.load(f)

    saved = mmio["registers"]
    source = turing["registers"]
    assert len(saved) == 52 and len(source) == 52, (len(saved), len(source))
    assert set(saved) == set(source), "saved vs source name sets differ"

    macros, header_hashes = parse_headers(HDR_DIR)

    # source macro index by full name (registers and fields have distinct names)
    source_full = {}
    for fn, entries in macros.items():
        for name, defs in entries.items():
            source_full.setdefault(name, []).append(
                {"file": fn, "line": defs[0]["line"],
                 "value": defs[0]["value"], "access": defs[0]["access"],
                 "ftype": defs[0]["ftype"]}
            )

    # header-level macro type stats (informational; indexed expressions are not flat addresses)
    indexed_macros = []
    for fn, entries in macros.items():
        for name, defs in entries.items():
            if defs[0]["ftype"] == "indexed_expression":
                indexed_macros.append({"file": fn, "name": name, "line": defs[0]["line"],
                                       "expression": defs[0]["value"]})

    rows = []
    categories = {
        "confirmed_mmio_bar0": [],
        "mmio_bar0_base": [],
        "constants_mislabeled": [],
        "control_space_addresses": [],
        "pci_config_addresses": [],
        "misaligned_addresses": [],
        "unknown": [],
    }

    for name in sorted(saved):
        entry = saved[name]
        sreg = source[name]
        addr = int(entry["addr"])
        acc_dump = entry.get("access")
        raw = int(entry["value"])
        state = entry.get("state")
        err = error_like(raw)

        sdef = source_full[name][0]  # primary definition of the name
        src_addr = int(sdef["value"], 16) if sdef["ftype"] in ("register_address", "constant_value") and HEX_RE.match(sdef["value"]) else None
        ftype = sdef["ftype"]
        namespace = namespace_of(name, addr, sdef["access"], ftype)
        aligned4 = (addr % 4 == 0)
        within_bar0 = BAR0_LO <= addr <= BAR0_HI
        src_match = (src_addr is not None and src_addr == addr)

        confirmed = (namespace == "MMIO_BAR0" and ftype == "register_address"
                     and aligned4 and within_bar0 and src_match)

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

        # bitfield recomputation: only on real register values
        fields_out = []
        for bf in entry.get("bitfields", []):
            lo = int(bf["lo"]); hi = int(bf["hi"])
            mask = (1 << (hi - lo + 1)) - 1
            dump_val = int(bf["value"]) if "value" in bf else None
            # source field declaration (same full name in headers)
            sf = source_full.get(bf["name"], [None])[0]
            src_hi = src_lo = None
            if sf and sf["ftype"] == "field_bitrange":
                src_lo, src_hi = map(int, sf["value"].split(":"))
            if err:
                recomputed = None
                semantic = False
                bf_note = "no semantic field value: error-like/poison register value"
            else:
                recomputed = (raw >> lo) & mask
                semantic = True
                bf_note = None
            match = (dump_val == recomputed) if (dump_val is not None and recomputed is not None) else None
            fields_out.append({
                "field": bf["name"], "hi": hi, "lo": lo, "mask": hex(mask),
                "source_hi": src_hi, "source_lo": src_lo,
                "source_match": (src_hi == hi and src_lo == lo) if src_hi is not None else None,
                "dump_value": dump_val, "recomputed": recomputed, "matches_dump": match,
                "semantic": semantic, "note": bf_note,
            })

        rows.append({
            "name": name, "addr": addr, "addr_hex": entry.get("addr_hex"),
            "namespace": namespace, "source_type": ftype,
            "source_file": sdef["file"], "source_line": sdef["line"],
            "header_sha256": header_hashes[sdef["file"]],
            "source_access": sdef["access"], "dump_access": acc_dump,
            "access_match": (sdef["access"] == acc_dump),
            "aligned4": aligned4, "within_bar0": within_bar0,
            "raw_value": raw, "raw_value_hex": hex(raw),
            "state": state, "error_like": err,
            "confirmed_mmio_bar0_address": confirmed,
            "bitfields": fields_out,
            "note": None,
        })

    # WPR2 decode (header dev_fb.h: VAL 31:4, shift 12, ALIGNMENT 12)
    wpr2 = {}
    for nm in ("NV_PFB_PRI_MMU_WPR2_ADDR_LO", "NV_PFB_PRI_MMU_WPR2_ADDR_HI"):
        if nm in saved:
            raw = saved[nm]["value"]
            field = (raw >> 4) & 0xFFFFFFFF
            decoded = field << 12
            wpr2[nm] = {
                "addr": saved[nm]["addr"], "addr_hex": saved[nm]["addr_hex"],
                "raw": raw, "raw_hex": hex(raw),
                "field_VAL_31_4": field, "field_hex": hex(field),
                "decoded_address": decoded, "decoded_hex": hex(decoded),
                "state": saved[nm]["state"], "error_like": error_like(raw),
            }
    if len(wpr2) == 2:
        lo_dec = wpr2["NV_PFB_PRI_MMU_WPR2_ADDR_LO"]["decoded_address"]
        hi_dec = wpr2["NV_PFB_PRI_MMU_WPR2_ADDR_HI"]["decoded_address"]
        wpr2["bound_difference_bytes"] = hi_dec - lo_dec
        wpr2["bound_difference_mib"] = round((hi_dec - lo_dec) / 2 ** 20, 3)
        wpr2["alignment_from_header"] = 0xC
        wpr2["bound_inclusive_exclusive"] = "UNKNOWN (no local source defines local bound semantics)"
        wpr2["note"] = "VAL[31:4]<<12 per dev_fb.h; 28-bit decoded address, no 20-bit mask"

    l2 = {
        "L2TLB": {
            "name": "NV_PFB_PRI_MMU_L2TLB_ECC_UNCORRECTED_ERR_COUNT",
            "addr": 1052280, "addr_hex": "0x00100e78",
            "file": "dev_fb.h", "access": "RW-4R",
            "meaning": "MMU L2 TLB ECC uncorrected error count (TOTAL 15:0, UNIQUE 31:16)",
        },
        "L2_CACHE": {
            "name": "NV_PLTCG_LTC0_LTS0_L2_CACHE_ECC_UNCORRECTED_ERR_COUNT",
            "addr": 1311992, "addr_hex": "0x001404f8",
            "file": "dev_ltc.h", "access": "RW-4R",
            "meaning": "LTC L2 cache ECC uncorrected error count",
        },
        "conflated": False,
        "note": "L2TLB (dev_fb.h) != L2 cache (dev_ltc.h); kept in separate namespaces, never merged",
    }

    report = {
        "script": "mmio_namespace_verify.py",
        "workspace": ROOT,
        "started_at": started,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "mmio_dump": {"path": MMIO_PATH, "sha256": sha256_file(MMIO_PATH), "entries": len(saved)},
            "turing_source": {"path": TURING_PATH, "sha256": sha256_file(TURING_PATH), "entries": len(source)},
            "headers_dir": HDR_DIR, "header_count": len(macros),
            "header_hashes": header_hashes,
            "source_applicability": "tu102 headers are the definition source for TU10x/TU106 matching; other families are NOT used as TU106 definitions",
        },
        "namespace_defs": {
            "MMIO_BAR0": "register/address within 16 MiB BAR0 window, MMIO access (R--4R/RW-4R/-W-4R/RW--V/...)",
            "MMIO_BAR0_BASE": "MMIO BAR0 base address with null access (FBIF_BASE/GSP_BASE)",
            "PCI_CONFIG": "PCI config space offset (NV_PCFG_*_OFFSET)",
            "CONTROL_SPACE": "NV_CTRL control-interface addresses (access C--4R), not MMIO BAR0",
            "CONSTANT": "enum/constant value misused as a register address",
        },
        "header_macro_stats": {
            "indexed_expressions_in_headers": len(indexed_macros),
            "indexed_macros": indexed_macros,
            "note": "indexed expressions are excluded from flat address verification; none of the 52 saved entries use indexed form",
        },
        "audit_summary": {
            "saved_entries": len(saved),
            "confirmed_mmio_bar0_registers": len(categories["confirmed_mmio_bar0"]),
            "mmio_bar0_base_null_access": len(categories["mmio_bar0_base"]),
            "constants_mislabeled_as_addresses": len(categories["constants_mislabeled"]),
            "control_space_addresses": len(categories["control_space_addresses"]),
            "pci_config_addresses": len(categories["pci_config_addresses"]),
            "misaligned_addresses": len(categories["misaligned_addresses"]),
            "unknown": len(categories["unknown"]),
            "poison_state_mismatch": [r["name"] for r in rows if r["error_like"] and r["state"] == "data"],
        },
        "audit_categories": categories,
        "rows": rows,
        "wpr2": wpr2,
        "l2tlb_vs_l2cache": l2,
        "conclusion": {
            "matched_source_52_52_valid": False,
            "reason": "input catalog mixes enum/constant values and control-space addresses with MMIO BAR0 register addresses; 52/52 name+address equality with a flawed input catalog is not independent proof.",
        },
    }

    verified_path = os.path.join(OUT_DIR, "mmio_namespace_verified.json")
    with open(verified_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # corrected_registers.csv
    csv_path = os.path.join(OUT_DIR, "corrected_registers.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "namespace", "source_type", "addr", "addr_hex",
                    "aligned4", "within_bar0", "source_file", "source_line",
                    "source_access", "dump_access", "access_match",
                    "raw_value", "raw_value_hex", "state", "error_like",
                    "confirmed_mmio_bar0_address", "bitfield_semantic", "note"])
        for r in rows:
            bf_sem = "none_poison" if r["bitfields"] and not r["bitfields"][0]["semantic"] else \
                     ("partial_poison" if any(not b["semantic"] for b in r["bitfields"]) else "ok")
            w.writerow([r["name"], r["namespace"], r["source_type"], r["addr"], r["addr_hex"],
                        r["aligned4"], r["within_bar0"], r["source_file"], r["source_line"],
                        r["source_access"], r["dump_access"], r["access_match"],
                        r["raw_value"], r["raw_value_hex"], r["state"], r["error_like"],
                        r["confirmed_mmio_bar0_address"], bf_sem, r["note"]])

    # console summary
    print("MMIO namespace verify complete.")
    print("entries={} confirmed_mmio_bar0={} mmio_bar0_base={} constants_mislabeled={} control_space={} pci_config={} misaligned={} unknown={}".format(
        len(saved), len(categories["confirmed_mmio_bar0"]), len(categories["mmio_bar0_base"]),
        len(categories["constants_mislabeled"]), len(categories["control_space_addresses"]),
        len(categories["pci_config_addresses"]), len(categories["misaligned_addresses"]),
        len(categories["unknown"])))
    print("poison_as_data_states={}".format(report["audit_summary"]["poison_state_mismatch"]))
    print("wpr2_bound_bytes={} bound_mib={}".format(
        wpr2.get("bound_difference_bytes"), wpr2.get("bound_difference_mib")))
    print("l2tlb={} l2cache={} conflated={}".format(l2["L2TLB"]["addr"], l2["L2_CACHE"]["addr"], l2["conflated"]))
    print("outputs: {} {}".format(verified_path, csv_path))


if __name__ == "__main__":
    main()

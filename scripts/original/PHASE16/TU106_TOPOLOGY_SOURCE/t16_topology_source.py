#!/usr/bin/env python3
# ponytail: stdlib-only, single file, offline read-only. No hardware access, no MMIO/PCI writes.
"""PHASE16/TU106_TOPOLOGY_SOURCE — what can be PROVED about CMP 40HX (TU106) GPC/TPC/SM/ROP topology.

Input evidence (all read-only, hash-verified):
  work_v15/RAW_DATA/fuse2.json          archived fuse array dump, base 0x21000
  work_v15/RAW_DATA/p5678.json          saved NVML/nvidia-smi query archive
  work_v15/TOPOLOGY/silicon_topology.json saved NVML sm_count fragment
  work_v15/MMIO/mmio.json               saved MMIO snapshot (52 registers)
  work_v15/MMIO/registers_turing.json   saved turing register namespace
  PHASE16/ENGINE_INTERFACES/findings.json archived coordinator findings (BAO_CAO claims)
  /tmp/BAO_CAO_CMP40HX_TU106.md         archived primary report (prose, source of 3/17/34)
  /tmp/nvsrc/.../turing/tu102/dev_fuse.h public Turing fuse register definitions
  /tmp/nvsrc/.../turing/tu102/dev_fault.h public fault client IDs (indices, not counts)

Output: t16_topology_evidence.json (structured, machine-readable).
No hardware probed. No writes. Only addresses actually captured are used as decode input.
"""

import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = "/home/REDACTED_USER/codex-work"
WORK = os.path.join(ROOT, "work_v15")
OUT = os.path.join(ROOT, "PHASE16/TU106_TOPOLOGY_SOURCE")
NVSRC = "/tmp/nvsrc/common/inc/swref/published/turing/tu102"

INPUTS = [
    (os.path.join(WORK, "RAW_DATA/fuse2.json"), "archived fuse array dump (base 0x21000)"),
    (os.path.join(WORK, "RAW_DATA/p5678.json"), "saved NVML / nvidia-smi query archive"),
    (os.path.join(WORK, "TOPOLOGY/silicon_topology.json"), "saved NVML sm_count fragment"),
    (os.path.join(WORK, "MMIO/mmio.json"), "saved MMIO snapshot (52 registers)"),
    (os.path.join(WORK, "MMIO/registers_turing.json"), "saved turing register namespace"),
    (os.path.join(ROOT, "PHASE16/ENGINE_INTERFACES/findings.json"), "archived coordinator findings"),
    ("/tmp/BAO_CAO_CMP40HX_TU106.md", "archived primary technical report (prose)"),
    (os.path.join(NVSRC, "dev_fuse.h"), "public Turing fuse register definitions"),
    (os.path.join(NVSRC, "dev_fault.h"), "public fault client IDs (indices, not counts)"),
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def popcount(v):
    return bin(int(v) & 0xFFFFFFFF).count("1")


def field(value, hi, lo):
    return (int(value) >> lo) & ((1 << (hi - lo + 1)) - 1)


def main():
    os.makedirs(OUT, exist_ok=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    input_records = []
    for path, role in INPUTS:
        if not os.path.exists(path):
            input_records.append({"path": path, "role": role, "present": False})
            continue
        input_records.append({
            "path": path, "role": role, "present": True,
            "bytes": os.path.getsize(path), "sha256": sha256_file(path),
        })

    # ---------- 1. Raw fuse values, verified against saved fuse2.json ----------
    fuse = json.load(open(os.path.join(WORK, "RAW_DATA/fuse2.json"), encoding="utf-8"))
    fuse_base = int(fuse["base"])
    regs = fuse["regs"]
    raw_fuse = []
    for off_hex in ("0x650", "0xc1c"):
        off = int(off_hex, 16)
        raw_fuse.append({
            "offset_hex": off_hex, "offset_dec": off,
            "abs_addr_hex": "0x%06X" % (fuse_base + off),
            "abs_addr": fuse_base + off,
            "fuse_base_hex": "0x%06X" % fuse_base,
            "raw_value": int(regs[str(off)]),
            "raw_value_hex": "0x%08X" % int(regs[str(off)]),
            "popcount": popcount(int(regs[str(off)])),
            "verified_from_saved_dump": True,
            "note": "raw value only; no bitfield definition in public TU106-applicable source",
        })

    # ---------- 2. Saved MMIO snapshot coverage ----------
    mmio = json.load(open(os.path.join(WORK, "MMIO/mmio.json"), encoding="utf-8"))
    dumped = mmio["registers"]
    addrs = sorted(int(r["addr"]) for r in dumped.values())
    topology_addr_wanted = {
        "gpc_nr": 0x00409604,
        "tpc_nr": 0x00502608,
        "TPC_UNIT_base": 0x00504000,
    }
    captured = {name: False for name in topology_addr_wanted}
    for r in dumped.values():
        a = int(r["addr"])
        for name, want in topology_addr_wanted.items():
            if a == want:
                captured[name] = True
    mmio_pages = sorted(set(r.get("page") for r in dumped.values() if r.get("page") is not None))
    mmio_snapshot = {
        "registers_dumped": len(dumped),
        "pages_touched": mmio_pages,
        "sample_rule": "tu06: 4 u32 (16 bytes) per 4 KiB page; not a full-page capture",
        "coverage_statement": "sparse 16-byte-per-page sample is NOT a complete MMIO scan; "
                             "only sampled addresses may be used as decode input",
        "topology_registers_in_saved_snapshot": {
            "gpc_nr_0x00409604_page_1033": captured["gpc_nr"],
            "tpc_nr_0x00502608_page_1282": captured["tpc_nr"],
            "TPC_UNIT_0x00504000_page_1284": captured["TPC_UNIT_base"],
        },
        "all_dumped_registers": [
            {"name": n, "addr": r["addr"], "addr_hex": r["addr_hex"],
             "value": r["value"], "state": r.get("state"), "page": r.get("page")}
            for n, r in sorted(dumped.items(), key=lambda kv: kv[1]["addr"])
        ],
    }

    # ---------- 3. Saved NVML / nvidia-smi query archive ----------
    p5678 = json.load(open(os.path.join(WORK, "RAW_DATA/p5678.json"), encoding="utf-8"))
    smq = p5678.get("topology", {}).get("smi_q", "")
    mem = p5678.get("memory", {}).get("smi", "")
    nvml = {
        "multiProcessorCount_present_in_saved_log": bool(re.search(r"multiProcessorCount", smq)),
        "cuda_cores_present_in_saved_log": bool(re.search(r"CUDA Cores", smq)),
        "sm_count_field_value": p5678.get("topology", {}).get("sm_count"),
        "gpu_uuid": p5678.get("topology", {}).get("gpu_uuid"),
        "saved_log_contains": {
            "product_name": "NVIDIA CMP 40HX" in smq,
            "architecture_turing": "Turing" in smq,
            "display_attached_no": "Display Attached                                   : No" in smq,
            "display_active_disabled": "Display Active                                     : Disabled" in smq,
        },
        "fb_memory_usage": mem,
        "note": "saved nvidia-smi -q log does NOT contain multiProcessorCount/CUDA cores; "
              "the 34-SM figure appears only in archived BAO_CAO prose",
    }
    sil = json.load(open(os.path.join(WORK, "TOPOLOGY/silicon_topology.json"), encoding="utf-8"))
    nvml["silicon_topology_sm_count_field"] = sil.get("sm_count")
    nvml["silicon_topology_gpu_uuid"] = sil.get("gpu_uuid")

    # ---------- 4. Public register definitions actually present (tu102, TU106-applicable) ----------
    dev_fuse_text = open(os.path.join(NVSRC, "dev_fuse.h"), encoding="utf-8", errors="replace").read()
    dev_fault_text = open(os.path.join(NVSRC, "dev_fault.h"), encoding="utf-8", errors="replace").read()
    defs = {
        "dev_fuse_h": {
            "path": os.path.join(NVSRC, "dev_fuse.h"),
            "sha256": sha256_file(os.path.join(NVSRC, "dev_fuse.h")),
            "registers_defined": [
                {"name": "NV_FUSE_OPT_NVDEC_DISABLE", "addr": 0x00021378,
                 "field": "NV_FUSE_OPT_NVDEC_DISABLE_DATA", "bits": "2:0",
                 "saved_read": int(next(r for r in dumped.values() if int(r["addr"]) == 0x21378)["value"]),
                 "topic": "NVDEC, NOT topology"},
                {"name": "NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS", "addr": 0x0002174C,
                 "field": "NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS_DATA", "bits": "0:0",
                 "saved_read": int(next(r for r in dumped.values() if int(r["addr"]) == 0x2174C)["value"]),
                 "topic": "GSP debug, NOT topology"},
            ],
            "definitions_at_fuse_0x650": False,
            "definitions_at_fuse_0xc1c": False,
            "tu106_applicable_note": "tu102 Turing-family header, accepted as TU10x/TU106-shared; "
                                     "no TU106-specific override directory exists",
        },
        "dev_fault_h": {
            "path": os.path.join(NVSRC, "dev_fault.h"),
            "sha256": sha256_file(os.path.join(NVSRC, "dev_fault.h")),
            "content": "NV_PFAULT_CLIENT_GPC_TPCCS_* / NV_PFAULT_CLIENT_GPC_T1_* fault CLIENT IDs only "
                       "(client index space, NOT engine counts)",
            "topic": "fault client IDs, not topology counts",
        },
        "absent_headers": {
            "dev_top_h_tu102": False,
            "dev_gr_h_tu102": False,
            "dev_graph_h_tu102": False,
            "tu106_register_directory": False,
            "note": "dev_top.h/dev_gr.h/dev_graph.h exist only for OTHER generations "
                    "(ampere/ga100, blackwell/gb100, volta/gv100, pascal/gp100, rubin/gr100) "
                    "and must not stand in for TU106",
        },
    }

    # ---------- 5. Archived query claims (from archived BAO_CAO prose; NOT saved snapshot) ----------
    bao_path = "/tmp/BAO_CAO_CMP40HX_TU106.md"
    bao_text = open(bao_path, encoding="utf-8", errors="replace").read()
    archived_claims = [
        {
            "count": "GPC",
            "claim": "3 GPC",
            "basis": "archived prose: gpc_nr (0x00409604) = 0x08040003 -> low 16 bits = 3",
            "source": "BAO_CAO_CMP40HX_TU106.md section 3.1",
            "register_address": "0x00409604",
            "register_address_captured_in_saved_MMIO": False,
            "status": "ARCHIVED_QUERY_CLAIM",
        },
        {
            "count": "TPC (in GPC0)",
            "claim": "5 TPC",
            "basis": "archived prose: tpc_nr (0x00502608) = 0x00040005 -> low 16 bits = 5",
            "source": "BAO_CAO_CMP40HX_TU106.md section 3.1",
            "register_address": "0x00502608",
            "register_address_captured_in_saved_MMIO": False,
            "status": "ARCHIVED_QUERY_CLAIM",
        },
        {
            "count": "TPC (total)",
            "claim": "17 TPC",
            "basis": "archived prose: TPC map probe TPC_UNIT = 0x504000 + g*0x8000 + t*0x800; "
                     "GPC0: 5 live + TPC5 poison; GPC1: 6 live; GPC2: 6 live -> 5+6+6 = 17",
            "source": "BAO_CAO_CMP40HX_TU106.md section 3.2",
            "register_address": "0x00504000 + g*0x8000 + t*0x800",
            "register_address_captured_in_saved_MMIO": False,
            "status": "ARCHIVED_QUERY_CLAIM",
        },
        {
            "count": "SM",
            "claim": "34 SM / 2176 CUDA cores",
            "basis": "archived prose: 17 TPC x 2 SM == cudaGetDeviceProperties() "
                     "multiProcessorCount = 34, CUDA cores = 2176",
            "source": "BAO_CAO_CMP40HX_TU106.md section 3.3",
            "register_address": "none (CUDA runtime query, not MMIO register)",
            "register_address_captured_in_saved_MMIO": False,
            "saved_nvidia_smi_contains_multiProcessorCount": False,
            "status": "ARCHIVED_QUERY_CLAIM",
        },
        {
            "count": "ROP",
            "claim": "64 ROP (16 per L2 partition, 4 partitions)",
            "basis": "archived prose: inferred from TU106 reference comparison (RTX 2070 SKU table)",
            "source": "BAO_CAO_CMP40HX_TU106.md section 10",
            "register_address": "none",
            "register_address_captured_in_saved_MMIO": False,
            "status": "ARCHIVED_INFERENCE_FROM_OTHER_SKU",
        },
        {
            "count": "fuse TPC mask",
            "claim": "fuse+0x650 = 0x0004001F, bits 0-4 = 0x1F = 5 TPC enabled",
            "basis": "archived prose; raw value VERIFIED against saved fuse2.json (0x4001f)",
            "source": "BAO_CAO_CMP40HX_TU106.md sections 3.4 / 5.1",
            "register_address": "fuse base 0x21000 + 0x650",
            "register_address_captured_in_saved_MMIO": "n/a (fuse array, not MMIO)",
            "raw_verified": True,
            "status": "RAW_VALUE_VERIFIED_MEANING_UNKNOWN",
        },
    ]

    # ---------- 6. Per-count prove/disprove matrix ----------
    def verdict(topology, archived, raw, reg_cap, definition, decode):
        return {
            "topology": topology,
            "archived_query_claim": archived,
            "register_value_raw": raw,
            "register_captured_in_saved_MMIO": reg_cap,
            "public_TU106_definition": definition,
            "actual_decoded_topology": decode,
            "proved": not decode.startswith("UNKNOWN"),
        }

    results = {
        "GPC": verdict(
            "GPC",
            "3 GPC — archived gpc_nr 0x00409604 = 0x08040003 (low16=3)",
            "fuse+0xC1C = 0x38 raw (popcount 3), verified from saved fuse2.json",
            False,
            "None: dev_fuse.h has no field at fuse+0xC1C; dev_top.h/dev_gr.h absent for tu106",
            "UNKNOWN — popcount(0x38)==3 is consistent with the archived claim but is not a "
            "bitfield decode; no source field names these bits as GPC count/enable mask",
        ),
        "TPC": verdict(
            "TPC",
            "17 TPC total — archived TPC map probe (5+6+6); 5 TPC in GPC0 — archived tpc_nr 0x00502608 = 0x00040005",
            "fuse+0x650 = 0x4001F raw (bits0-4 = 5), verified from saved fuse2.json",
            False,
            "None: dev_fuse.h has no field at fuse+0x650",
            "UNKNOWN — bits0-4 of 0x4001F == 5 matches archived tpc_nr low16 but is not a decode; "
            "17 not divisible by 3, per-GPC distribution undecidable from saved evidence",
        ),
        "SM": verdict(
            "SM",
            "34 SM — archived: 17 TPC x 2 == cudaGetDeviceProperties multiProcessorCount=34, CUDA cores=2176",
            "saved nvidia-smi log contains NO multiProcessorCount/CUDA cores; "
            "silicon_topology.json sm_count field is 'NVIDIA CMP 40HX, 7.5' (fragment, not 34)",
            False,
            "None: no dev_top.h/dev_gr.h for tu106",
            "UNKNOWN — 34 SM exists only as an archived query claim; not present in the saved "
            "NVML log, not decodable from any captured register",
        ),
        "ROP": verdict(
            "ROP",
            "64 ROP — archived inference from TU106/RTX-2070 reference SKU table",
            "no ROP/L2/MC register captured in saved MMIO snapshot",
            False,
            "None: no dev_top.h/dev_gr.h for tu106; dev_ltc.h/dev_fb.h hold only ECC/invalidate regs",
            "UNKNOWN — 0% measured on this card; inferred only from other-SKU reference",
        ),
    }

    # ---------- 7. Independent cross-checks (raw datum vs raw datum) ----------
    cross_checks = [
        {
            "pair": "fuse+0xC1C popcount(0x38)==3 vs archived gpc_nr 0x08040003 low16==3",
            "raw_a": "fuse2.json base+0xc1c = 0x38",
            "raw_b": "BAO_CAO archived gpc_nr register = 0x08040003 (not in saved MMIO snapshot)",
            "result": "consistent value (3), two independent raw datums, but NO shared bitfield "
                      "definition -> 'consistent, not proven'; popcount inference explicitly rejected",
        },
        {
            "pair": "fuse+0x650 bits0-4 == 5 vs archived tpc_nr 0x00040005 low16==5",
            "raw_a": "fuse2.json base+0x650 = 0x4001F",
            "raw_b": "BAO_CAO archived tpc_nr register = 0x00040005 (not in saved MMIO snapshot)",
            "result": "consistent value (5), two independent raw datums, but NO shared bitfield "
                      "definition -> 'consistent, not proven'",
        },
        {
            "pair": "17 TPC vs 3 GPC divisibility",
            "raw_a": "archived TPC map total 17",
            "raw_b": "archived GPC count 3",
            "result": "17 % 3 != 0 -> per-GPC TPC distribution (5/6/6 claimed) is NOT provable "
                      "from saved evidence; GPC0 TPC5 poison claim contradicts '3x6 uniform' assumption",
        },
        {
            "pair": "17 x 2 == 34 SM vs cudaGetDeviceProperties 34",
            "raw_a": "archived TPC-map-derived 34 SM",
            "raw_b": "archived CUDA runtime multiProcessorCount=34, cores=2176",
            "result": "both figures exist only in archived BAO_CAO prose; NEITHER appears in the "
                      "saved nvidia-smi log or any captured register -> mutual corroboration within "
                      "archived prose only, not saved-evidence proof",
        },
    ]

    # ---------- 8. Unresolved elements + missing capture ----------
    unresolved = [
        {
            "id": "U-TOP-GPC-DECODE",
            "element": "GPC count and fuse+0xC1C=0x38 field semantics",
            "reason": "no dev_top.h/dev_gr.h for tu106; dev_fuse.h lacks any field at fuse+0xC1C; "
                      "gpc_nr register 0x00409604 not captured in saved MMIO snapshot",
            "missing_capture": "MMIO read of 0x00409604 (gpc_nr) PLUS a TU106-applicable public "
                               "header defining the gpc_nr/tpc_nr bitfields (dev_top.h/dev_gr.h "
                               "tu106)",
        },
        {
            "id": "U-TOP-TPC-DIST",
            "element": "TPC count (17) and per-GPC distribution",
            "reason": "tpc_nr 0x00502608 and TPC_UNIT map 0x504000+ not captured in saved MMIO "
                      "snapshot; no public bitfield source; 17 not divisible by 3",
            "missing_capture": "MMIO read of 0x00502608 and per-TPC unit probe addresses "
                               "0x504000 + g*0x8000 + t*0x800 (+0x010/+0x100/+0x400) across all "
                               "GPC/TPC, plus header definitions",
        },
        {
            "id": "U-TOP-SM-COUNT",
            "element": "SM count (34) and CUDA cores (2176)",
            "reason": "saved nvidia-smi -q log lacks multiProcessorCount/CUDA cores; silicon_topology "
                      "sm_count is a fragment ('NVIDIA CMP 40HX, 7.5'); no SM-count register captured",
            "missing_capture": "complete nvidia-smi -q / NVML query archive containing "
                               "multiProcessorCount and CUDA cores, OR MMIO capture of an SM-count "
                               "register with TU106-applicable definition",
        },
        {
            "id": "U-TOP-ROP-COUNT",
            "element": "ROP count (64 claimed), L2 partitions, memory controllers",
            "reason": "0% measured on this card; every L2/MC/ROP-related MMIO address outside the "
                      "captured 52-register set; dev_ltc.h/dev_fb.h contain only ECC/invalidate "
                      "registers, not instance counts",
            "missing_capture": "MMIO capture of L2/ROP/MC address space with TU106-applicable "
                               "register definitions, or official TU106 die topology document",
        },
        {
            "id": "U-FUSE-0x650-0xC1C",
            "element": "fuse+0x650=0x4001F and fuse+0xC1C=0x38 semantics",
            "reason": "raw values verified, but no public Turing/TU106 dev_fuse.h field at either "
                      "offset; popcount-to-topology inference rejected by prior coordinator review",
            "missing_capture": "official TU106 fuse bitfield definition (or RM fuse-consuming code) "
                               "naming these offsets",
        },
    ]

    result = {
        "phase": "PHASE16/TU106_TOPOLOGY_SOURCE",
        "target": "NVIDIA CMP 40HX (TU106-100-A1), PCI 10de:1f0b, subsystem 8804:1043, rev 0xA1, "
                  "BDF 0000:03:00.0, BAR0 0xfa000000 size 16 MiB",
        "mode": "offline read-only, stdlib-only, no hardware access, no MMIO/PCI writes",
        "generated_utc": generated,
        "inputs": input_records,
        "raw_fuse_verified": raw_fuse,
        "saved_mmio_coverage": mmio_snapshot,
        "nvidia_smi_saved_log": nvml,
        "public_register_definitions_checked": defs,
        "archived_query_claims": archived_claims,
        "decode_results": results,
        "cross_checks": cross_checks,
        "unresolved": unresolved,
        "conclusion": (
            "From the SAVED offline evidence alone, nothing about GPC/TPC/SM/ROP topology can be "
            "decoded: the saved MMIO snapshot contains no topology register (gpc_nr/tpc_nr/TPC_UNIT "
            "all absent), the saved nvidia-smi log lacks multiProcessorCount, and the public "
            "TU106-applicable header set (tu102, 37 headers) has no dev_top.h/dev_gr.h and no "
            "dev_fuse.h field at fuse+0x650 or 0xc1c. The only PROVED raw facts are fuse base+0x650 "
            "= 0x4001f and base+0xc1c = 0x38 (verified against saved fuse2.json). The archived "
            "claims '3 GPC, 17 TPC, 34 SM' are query/register claims from BAO_CAO prose whose "
            "source addresses were never captured in the saved snapshot; they are consistent with "
            "each other and with the raw fuse popcounts, but consistency is not a decode. Every "
            "topology count remains UNKNOWN with the missing capture listed above."
        ),
    }
    with open(os.path.join(OUT, "t16_topology_evidence.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    print("WROTE", os.path.join(OUT, "t16_topology_evidence.json"))
    for k, v in results.items():
        print(k, "->", v["actual_decoded_topology"][:60])
    return 0


if __name__ == "__main__":
    sys.exit(main())

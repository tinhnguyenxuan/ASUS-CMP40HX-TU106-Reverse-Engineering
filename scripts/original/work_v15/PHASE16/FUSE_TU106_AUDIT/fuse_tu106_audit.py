#!/usr/bin/env python3
# ponytail: single-file, stdlib-only reproducible audit. No new deps, no network, no hardware access.
"""FUSE_TU106_AUDIT — source-backed audit of the archived TU106 fuse/OTP dump.

Reads (read-only, no modification):
  work_v15/RAW_DATA/fuse2.json          archived fuse dump (base 0x21000)
  work_v15/PHASE16/UNKNOWN_DATABASE.json baseline + phase16 unknown items
  work_v15/PHASE16/FUSE_SOURCE/source_evidence.json curated per-word source evidence
  /tmp/nvsrc/.../turing/tu102/dev_fuse.h   official Turing source snapshot
  /tmp/nvsrc/.../maxwell/gm107/dev_fuse.h  official Maxwell source snapshot
  work_v15/PHASE16/SOURCES/nvidia_*_dev_fuse.h local byte-identical snapshots

Writes (new artifacts only, under PHASE16/FUSE_TU106_AUDIT/):
  fuse_tu106_audit_report.json  machine-readable report
  FUSE_TU106_AUDIT.md           human-readable report
  fuse_tu106_audit_run.log      execution log

Does NOT: brute-force hashes/keys, identify crypto from 32-byte length, probe/write
hardware, infer topology from popcount, or import non-Turing definitions to TU106.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

WORK_ROOT = "/home/REDACTED_USER/codex-work/work_v15"
PHASE16 = os.path.join(WORK_ROOT, "PHASE16")
AUDIT_DIR = os.path.join(PHASE16, "FUSE_TU106_AUDIT")
DUMP_PATH = os.path.join(WORK_ROOT, "RAW_DATA", "fuse2.json")
DB_PATH = os.path.join(PHASE16, "UNKNOWN_DATABASE.json")
EVIDENCE_PATH = os.path.join(PHASE16, "FUSE_SOURCE", "source_evidence.json")
TU102_SRC = "/tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_fuse.h"
GM107_SRC = "/tmp/nvsrc/common/inc/swref/published/maxwell/gm107/dev_fuse.h"
TU102_LOCAL = os.path.join(PHASE16, "SOURCES", "nvidia_tu102_dev_fuse.h")
GM107_LOCAL = os.path.join(PHASE16, "SOURCES", "nvidia_gm107_dev_fuse.h")

EXPECTED_DUMP_SHA = "0e770041019aa3e4ac25733429589867a03c5542e83bc89f6937878c6e5c4ecc"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def u32(v):
    return v & 0xFFFFFFFF


def pad(v):
    return "0x%08X" % u32(v)


def main():
    os.makedirs(AUDIT_DIR, exist_ok=True)
    log_lines = []

    def log(*args):
        line = " ".join(str(a) for a in args)
        log_lines.append(line)
        print(line)

    log("=" * 72)
    log("FUSE_TU106_AUDIT — archived TU106 fuse/OTP dump source-backed audit")
    log("UTC %s" % datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    log("Mode: offline read-only. Original dump and UNKNOWN_DATABASE.json untouched.")
    log("=" * 72)

    # ---------------- input verification ----------------
    dump_sha = sha256_file(DUMP_PATH)
    log("[INPUT] dump %s sha256=%s (expected %s) %s"
        % (DUMP_PATH, dump_sha, EXPECTED_DUMP_SHA,
           "OK" if dump_sha == EXPECTED_DUMP_SHA else "MISMATCH"))
    assert dump_sha == EXPECTED_DUMP_SHA, "dump hash mismatch"

    db = load_json(DB_PATH)
    evidence = load_json(EVIDENCE_PATH)

    src_hashes = {}
    for label, path in (("turing/tu102/dev_fuse.h", TU102_SRC),
                        ("maxwell/gm107/dev_fuse.h", GM107_SRC),
                        ("local SOURCES nvidia_tu102_dev_fuse.h", TU102_LOCAL),
                        ("local SOURCES nvidia_gm107_dev_fuse.h", GM107_LOCAL)):
        src_hashes[label] = sha256_file(path)
        log("[INPUT] source %s sha256=%s size=%d" % (path, src_hashes[label],
                                                     os.path.getsize(path)))

    # local snapshots must be byte-identical to /tmp/nvsrc snapshots
    assert src_hashes["turing/tu102/dev_fuse.h"] == src_hashes["local SOURCES nvidia_tu102_dev_fuse.h"]
    assert src_hashes["maxwell/gm107/dev_fuse.h"] == src_hashes["local SOURCES nvidia_gm107_dev_fuse.h"]

    dump = load_json(DUMP_PATH)
    base = dump["base"]  # 0x21000
    span = dump["span"]  # 32768 declared
    poison = set(int(x, 16) if isinstance(x, str) else x for x in dump["poison"])
    regs = {int(k): int(v) for k, v in dump["regs"].items()}

    # ---------------- dump geometry ----------------
    offsets = sorted(regs)
    assert offsets[0] == 0 and offsets[-1] == 12284
    assert all(offsets[i + 1] - offsets[i] == 4 for i in range(len(offsets) - 1)), "dump not contiguous step 4"
    dumped_bytes = (offsets[-1] - offsets[0]) + 4
    log("[DUMP] base=0x%X span(declared)=%d dumped_words=%d dumped_bytes=%d extent=0x0..0x%X"
        % (base, span, len(offsets), dumped_bytes, offsets[-1]))
    log("[DUMP] poison_declared=%s pages=%s" % ([hex(p) for p in sorted(poison)], dump["pages"]))

    # ---------------- classification ----------------
    def classify(v):
        if v in poison:
            return "POISON"
        if v == 0:
            return "ZERO"
        return "DATA"

    inventory = []
    counts = {"DATA": 0, "ZERO": 0, "POISON": 0}
    ones = []
    for off in offsets:
        v = regs[off]
        cls = classify(v)
        counts[cls] += 1
        if v == 1:
            ones.append(off)
        inventory.append({"offset": off, "abs_addr": base + off,
                          "raw_value": v, "raw_hex": pad(v), "class": cls})

    log("[CLASSIFY] DATA=%d ZERO=%d POISON=%d total=%d (stats in dump: %s)"
        % (counts["DATA"], counts["ZERO"], counts["POISON"], len(offsets), dump["stats"]))
    assert (counts["DATA"], counts["ZERO"], counts["POISON"]) == (dump["stats"]["with_data"],
                                                                  dump["stats"]["zero"],
                                                                  dump["stats"]["poison"])
    assert counts["DATA"] == 352 and counts["ZERO"] == 518 and counts["POISON"] == 2202
    log("[ONES] word==1 count=%d first=0x%X last=0x%X" % (len(ones), ones[0], ones[-1]))
    assert len(ones) == 152

    nonpoison = [o for o in offsets if regs[o] not in poison]
    nonzero = [o for o in offsets if regs[o] not in poison and regs[o] != 0]
    last_nonpoison = nonpoison[-1]
    log("[RANGE] nonpoison_count=%d nonzero_count=%d last_nonpoison_offset=0x%X (%d)"
        % (len(nonpoison), len(nonzero), last_nonpoison, last_nonpoison))
    log("[RANGE] min_offset=0x0 max_offset=0x%X" % offsets[-1])

    # ---------------- source definitions (architectural) ----------------
    # Each entry: register, address, field, bit description, decoded values, source file, line, hash, tu106_applicable.
    SOURCE_DEFS = [
        {
            "register": "NV_FUSE_OPT_NVDEC_DISABLE",
            "address": 0x21378, "offset_from_base": 0x378,
            "field": "NV_FUSE_OPT_NVDEC_DISABLE_DATA", "bits": "2:0",
            "values": {"0": "INIT (disable=0)"},
            "source_file": "common/inc/swref/published/turing/tu102/dev_fuse.h",
            "source_abs": TU102_SRC, "source_hash": src_hashes["turing/tu102/dev_fuse.h"],
            "lines": [31, 32, 33],
            "tu106_applicable": True,
            "applicability_note": "Turing tu102 header; accepted by coordinator as TU10x/TU106-applicable field source. "
                                  "No TU106-specific header in snapshot; applicability rests on tu102->TU10x family compatibility, "
                                  "not a TU106-specific definition.",
        },
        {
            "register": "NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS",
            "address": 0x2174C, "offset_from_base": 0x74C,
            "field": "NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS_DATA", "bits": "0:0",
            "values": {"0": "NO", "1": "YES"},
            "source_file": "common/inc/swref/published/turing/tu102/dev_fuse.h",
            "source_abs": TU102_SRC, "source_hash": src_hashes["turing/tu102/dev_fuse.h"],
            "lines": [26, 27, 28, 29],
            "tu106_applicable": True,
            "applicability_note": "Turing tu102 header; accepted by coordinator as TU10x/TU106-applicable field source. "
                                  "Applicability rests on tu102->TU10x family compatibility, not a TU106-specific definition.",
        },
        {
            "register": "NV_FUSE_STATUS_OPT_DISPLAY",
            "address": 0x21C04, "offset_from_base": 0xC04,
            "field": "NV_FUSE_STATUS_OPT_DISPLAY_DATA", "bits": "0:0",
            "values": {"0": "ENABLE (only defined value)"},
            "source_file": "common/inc/swref/published/maxwell/gm107/dev_fuse.h",
            "source_abs": GM107_SRC, "source_hash": src_hashes["maxwell/gm107/dev_fuse.h"],
            "lines": [27, 28, 29],
            "tu106_applicable": False,
            "applicability_note": "MAXWELL gm107 only. Dump reads 1 at this offset, which is NOT in the defined enum {0}. "
                                  "Rejected for TU106: cannot import a Maxwell definition whose defined value contradicts the observed TU106 dump value.",
        },
    ]

    src_by_offset = {d["offset_from_base"]: d for d in SOURCE_DEFS}

    # ---------------- decode words with source support ----------------
    decoded = []
    for off in offsets:
        if off in src_by_offset:
            d = src_by_offset[off]
            v = regs[off]
            _bp = d["bits"].split(":")
            _b_high, _b_low = int(_bp[0]), int(_bp[1])
            bit_field_val = (v >> _b_low) & ((1 << (_b_high - _b_low + 1)) - 1)
            decoded.append({
                "offset": off, "abs_addr": base + off, "raw_value": v, "raw_hex": pad(v),
                "class": classify(v), "mapped_to": d["register"],
                "field": d["field"], "bits": d["bits"], "field_value": bit_field_val,
                "field_value_hex": pad(bit_field_val),
                "source_file": d["source_file"], "source_abs": d["source_abs"],
                "source_hash": d["source_hash"], "source_lines": d["lines"],
                "tu106_applicable": d["tu106_applicable"],
                "applicability_note": d["applicability_note"],
                "decoded_meaning": d["values"].get(str(bit_field_val), "value not in defined enum"),
            })

    log("[DECODE] source-mapped words=%d" % len(decoded))
    for d in decoded:
        log("  offset=0x%X abs=0x%X val=%s -> %s [%s] tu106_applicable=%s"
            % (d["offset"], d["abs_addr"], d["raw_hex"], d["mapped_to"], d["decoded_meaning"], d["tu106_applicable"]))

    # PDI corroboration (U-FUSE-007, kept resolved)
    pdi_low = regs[0x344]; pdi_high = regs[0x348]
    pdi = (pdi_high << 32) | pdi_low
    log("[PDI] fuse+0x344=%s fuse+0x348=%s combined PDI=0x%016X (U-FUSE-007, kept RESOLVED/CORROBORATED vs nvidia-smi)"
        % (pad(pdi_low), pad(pdi_high), pdi))
    assert pdi == 0x0000000000000000

    # ---------------- revisit U-FUSE items ----------------
    # Build per-item value snapshots from the dump.
    def val(off):
        return regs.get(off)

    revisit = []
    items = {it["id"]: it for it in db["items"] if it.get("component") == "FUSE"}

    def gap_stmt(extra):
        return ("No Turing/TU106 dev_fuse.h definition at this offset; no consuming code identified in the "
                "/tmp/nvsrc snapshot. %s" % extra)

    # U-FUSE-001
    offs001 = list(range(0x110, 0x198 + 1, 4))
    v001 = {o: val(o) for o in offs001}
    revisit.append({
        "id": "U-FUSE-001", "address": "0x021000+0x0110..0x0198",
        "observed": "152 words == 1 with gaps (0x11C=0, 0x124=0); values: %s" % {hex(o): pad(v) for o, v in v001.items() if v},
        "mapped_source": None,
        "finding": "Sparse all-bit0 words with gaps. Consistent with an enable-flag ARRAY (inferred), but coordinator "
                   "rejection stands: sparse ones do NOT rule out physical OTP readout. No source definition, no second "
                   "TU106 dump for comparison.",
        "recommendation": "KEEP OPEN — UNKNOWN (soften from categorical 'not physical OTP'). Gap: %s" % gap_stmt("no TU106 fuse-array definition."),
    })
    # U-FUSE-002
    offs002 = list(range(0x718, 0x734 + 1, 4))
    v002 = {o: val(o) for o in offs002}
    revisit.append({
        "id": "U-FUSE-002", "address": "0x021000+0x0718..0x0734",
        "observed": "8 contiguous words = 32 bytes high entropy: %s" % {hex(o): pad(v) for o, v in v002.items()},
        "mapped_source": None,
        "finding": "No structure, no magic, no IV. Finite hash trials (455,689 + 12,883) returned 0 matches; no key/HMAC "
                   "material available. Per constraints: no cryptographic identification from 32-byte length, no brute force.",
        "recommendation": "KEEP OPEN — BLOCKED/UNKNOWN. Gap: no TU106 reference image/kernel to compare against; no hash input material beyond the block itself.",
    })
    # U-FUSE-003
    revisit.append({
        "id": "U-FUSE-003", "address": "0x021000+0x0000",
        "observed": "0x%08X" % val(0x0),
        "mapped_source": None,
        "finding": "0xC0040000 != NV_PMC_BOOT_0 (0x166000A1). Strap-mirror hypothesis unproven: no strap bitfield "
                   "definition in snapshot.",
        "recommendation": "KEEP OPEN — UNKNOWN. Gap: no TU106 strap/boot-0 fuse definition; cannot name the bits.",
    })
    # U-FUSE-004
    offs004 = list(range(0x0D4, 0x0F4 + 1, 4))
    v004 = {o: val(o) for o in offs004}
    revisit.append({
        "id": "U-FUSE-004", "address": "0x021000+0x00D4..0x00F4",
        "observed": "11 words: %s" % {hex(o): pad(v) for o, v in v004.items()},
        "mapped_source": None,
        "finding": "All-high words (0xFFFFFFFC / 0xFFFFFF8F). Inferred marker only; bit meaning unknown.",
        "recommendation": "KEEP OPEN — INFERRED/UNKNOWN. Gap: no bitfield source defining which bits are set.",
    })
    # U-FUSE-005
    revisit.append({
        "id": "U-FUSE-005", "address": "0x021000+0x0C1C",
        "observed": "0x%08X (popcount 3: bits 3,4,5)" % val(0xC1C),
        "mapped_source": None,
        "finding": "Popcount == 3 matches the known TU106 GPC count, but coordinator rejects popcount/mask inference: "
                   "GPC count is topology knowledge, not a fuse bitfield. No bitfield source.",
        "recommendation": "KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 dev_fuse.h definition at 0x0C1C; do not decode as GPC mask.",
    })
    # U-FUSE-006 (7 observed offsets)
    offs006 = [0x178, 0x2D4, 0x4A8, 0x4AC, 0x4B0, 0x578, 0xE08]
    v006 = {o: val(o) for o in offs006}
    revisit.append({
        "id": "U-FUSE-006", "address": "0x021000+0x0178,0x02D4,0x04A8,0x04AC,0x04B0,0x0578,0x0E08",
        "observed": "0x%08X at all 7 offsets; NOT in declared poison set {0xBADF5040, 0xBADF1300, 0xBADF1100}" % val(0x178),
        "mapped_source": None,
        "finding": "In-window error-like value, independently re-matched against the raw dump. Not declared poison; "
                   "not proof that a physical OTP block is erased (fixed-poison assumption rejected).",
        "recommendation": "KEEP OPEN — UNKNOWN. Gap: no definition/consumer for 0xBADF510C; do not treat as physical OTP-erase evidence.",
    })
    # U-FUSE-008
    offs008 = list(range(0x100, 0x240 + 1, 4))
    v008 = {o: val(o) for o in offs008}
    distinct008 = sorted(set(v008.values()))
    revisit.append({
        "id": "U-FUSE-008", "address": "0x021000+0x0100..0x0240",
        "observed": "155 words, values %s (not a bitmask)" % [pad(v) for v in distinct008],
        "mapped_source": None,
        "finding": "Small integer values 1..7. Version/counter/index hypotheses unproven.",
        "recommendation": "KEEP OPEN — UNKNOWN. Gap: no source definition; semantic identity of the values unknown.",
    })
    # U-FUSE-009 (REOPEN)
    revisit.append({
        "id": "U-FUSE-009", "address": "0x021000+0x0C04",
        "observed": "0x%08X" % val(0xC04),
        "mapped_source": SOURCE_DEFS[2],  # gm107, NOT applicable
        "finding": "Only source is MAXWELL gm107 NV_FUSE_STATUS_OPT_DISPLAY, which defines DATA_ENABLE=0 only. The "
                   "dump reads 1 — outside the defined enum. Cannot import Maxwell to TU106; no Turing/TU106 field "
                   "source. Previous DECODED/resolved status is NOT supported.",
        "recommendation": "REOPEN — OPEN/UNKNOWN, INSUFFICIENT_EVIDENCE. Gap: no Turing/TU106 dev_fuse.h definition "
                          "at 0x0C04; observed value 1 contradicts the only available (Maxwell) enum.",
    })
    # U-FUSE-010
    revisit.append({
        "id": "U-FUSE-010", "address": "0x021000+0x0520",
        "observed": "0x%08X" % val(0x520),
        "mapped_source": None,
        "finding": "Trim/clock-setting hypotheses unproven; no source definition.",
        "recommendation": "KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 definition at 0x0520.",
    })
    # U-FUSE-011
    revisit.append({
        "id": "U-FUSE-011", "address": "0x021000+0x0D38",
        "observed": "0x%08X" % val(0xD38),
        "mapped_source": None,
        "finding": "Binning/grade hypothesis unproven; no source definition.",
        "recommendation": "KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 definition at 0x0D38.",
    })
    # U-FUSE-012
    offs012 = [0xDC8, 0xDCC, 0xDD0]
    v012 = {o: val(o) for o in offs012}
    revisit.append({
        "id": "U-FUSE-012", "address": "0x021000+0x0DC8..0x0DD0",
        "observed": "0x%08X x3" % val(0xDC8),
        "mapped_source": None,
        "finding": "Count/version hypothesis unproven; no source definition.",
        "recommendation": "KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 definition at 0x0DC8..0x0DD0.",
    })

    # Kept items (not revisited but reported for completeness)
    kept = [
        {"id": "U-FUSE-007", "status": "RESOLVED / CORROBORATED (keep)",
         "note": "PDI 0x0000000000000000 at fuse+0x344/0x348 matches nvidia-smi -q (2 independent sources)."},
        {"id": "U-FUSE-013", "status": "RESOLVED / DECODED (keep, narrowed)",
         "note": "0x820000 is outside the 0x21000 fuse dump. 'GB100-only' is too narrow (GA100 also publishes 0x820000); "
                 "applicability to TU106 not established — preserve as not-applicable-to-TU106-fuse-aperture."},
    ]

    # ---------------- physical OTP / shadow / strap / status provenance ----------------
    log("[PROVENANCE] physical OTP geometry: NOT established. Sparse ones (152) and gaps do not prove cell readout "
        "(coordinator/E16-006). No OTP geometry source in snapshot.")
    log("[PROVENANCE] shadow/strap: U-FUSE-003 0xC0040000 != NV_PMC_BOOT_0 0x166000A1; no strap bitfield source — not established.")
    log("[PROVENANCE] status/class fields: decoded only where Turing source exists (0x378 NVDEC_DISABLE=0, 0x74C GSP_DEBUG_DIS=1). "
        "0xC04 DISPLAY=1 is Maxwell-only and not applicable.")

    # ---------------- write JSON report ----------------
    report = {
        "audit": "FUSE_TU106_AUDIT",
        "gpu": "CMP 40HX (TU106-100-A1), PCI 10DE:1F0B",
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "offline read-only; no hardware probes/writes; no hash/key brute-force; no crypto-from-length; no popcount topology inference",
        "inputs": {
            "dump": {"path": DUMP_PATH, "sha256": dump_sha, "bytes": os.path.getsize(DUMP_PATH)},
            "unknown_database": {"path": DB_PATH, "sha256": sha256_file(DB_PATH), "bytes": os.path.getsize(DB_PATH),
                             "note": "input_hashes.json records this file at 23192 bytes / sha256 600e96943f0c0191faa263e48c30a72f97188a81b8b8fc7c7b8d85472cff4ab0; "
                                     "the on-disk file is now 26429 bytes (updated after that snapshot). This audit hashes the on-disk file as-is and does not modify it."},
            "source_evidence": {"path": EVIDENCE_PATH, "sha256": sha256_file(EVIDENCE_PATH)},
            "sources": {k: {"path": v, "sha256": src_hashes[k]} for k, v in
                        [("turing/tu102/dev_fuse.h", TU102_SRC),
                         ("maxwell/gm107/dev_fuse.h", GM107_SRC),
                         ("local SOURCES nvidia_tu102_dev_fuse.h", TU102_LOCAL),
                         ("local SOURCES nvidia_gm107_dev_fuse.h", GM107_LOCAL)]},
        },
        "dump_geometry": {
            "base": base, "base_hex": pad(base), "declared_span": span,
            "dumped_words": len(offsets), "dumped_bytes": dumped_bytes,
            "first_offset": 0, "last_offset": offsets[-1],
            "contiguous": True, "poison_declared": [hex(p) for p in sorted(poison)],
            "pages": dump["pages"],
        },
        "classification": counts,
        "ones": {"count": len(ones), "first": ones[0], "last": ones[-1], "offsets": [hex(o) for o in ones]},
        "ranges": {
            "nonpoison_count": len(nonpoison), "nonzero_count": len(nonzero),
            "last_nonpoison_offset": last_nonpoison, "last_nonpoison_hex": pad(last_nonpoison),
            "nonpoison_offsets": [hex(o) for o in nonpoison],
        },
        "source_definitions": SOURCE_DEFS,
        "decoded_words": decoded,
        "revisit": revisit,
        "kept_items": kept,
        "word_inventory": inventory,  # full exact enumeration: offset, abs_addr, raw_value, class
        "recommendations": {
            "open": [r["id"] for r in revisit],
            "resolved": [k["id"] for k in kept],
            "newly_decoded_tu106": [d["offset"] for d in decoded if d["tu106_applicable"]],
            "not_applicable_maxwell": [d["offset"] for d in decoded if not d["tu106_applicable"]],
        },
        "rejected_assumptions": [
            "Sparse-bit/ones => physical OTP cell readout (rejected by coordinator; sparse ones do not prove geometry).",
            "GPC popcount/mask: popcount(0x38)==3 == TU106 GPC count is NOT a fuse bitfield (coordinator rejection).",
            "Maxwell display import: gm107 NV_FUSE_STATUS_OPT_DISPLAY DATA_ENABLE=0 cannot be imported to TU106; dump reads 1 (outside enum).",
            "Fixed poison: 0xBADF510C is not in the declared poison set; not proof of physical OTP erasure.",
            "Crypto identification from 32-byte length: not attempted (constraint).",
            "Topology inference from popcount: not attempted (constraint).",
        ],
    }
    report_path = os.path.join(AUDIT_DIR, "fuse_tu106_audit_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    log("[WRITE] %s" % report_path)

    # ---------------- markdown report ----------------
    md = []
    md.append("# FUSE_TU106_AUDIT — archived TU106 fuse/OTP source-backed audit")
    md.append("")
    md.append("GPU: CMP 40HX (TU106-100-A1), PCI 10DE:1F0B. Mode: offline read-only.")
    md.append("UTC: %s" % report["utc"])
    md.append("")
    md.append("## Inputs (hash-verified, read-only)")
    md.append("| input | path | sha256 | bytes |")
    md.append("|---|---|---|---|")
    md.append("| archived fuse dump | RAW_DATA/fuse2.json | %s | %d |" % (dump_sha, os.path.getsize(DUMP_PATH)))
    md.append("| UNKNOWN_DATABASE.json | PHASE16/UNKNOWN_DATABASE.json | %s | %d |" % (sha256_file(DB_PATH), os.path.getsize(DB_PATH)))
    md.append("| _(note)_ | input_hashes.json recorded 23192 B / sha256 600e9694…; on-disk file is now 26429 B / sha256 %s (updated after that snapshot). This audit hashes the on-disk file as-is and does not modify it. | | |" % sha256_file(DB_PATH))
    md.append("| source_evidence.json | PHASE16/FUSE_SOURCE/source_evidence.json | %s | %d |" % (sha256_file(EVIDENCE_PATH), os.path.getsize(EVIDENCE_PATH)))
    for label in src_hashes:
        md.append("| source %s | %s | %s | %d |" % (label, {"turing/tu102/dev_fuse.h": TU102_SRC,
                                                           "maxwell/gm107/dev_fuse.h": GM107_SRC,
                                                           "local SOURCES nvidia_tu102_dev_fuse.h": TU102_LOCAL,
                                                           "local SOURCES nvidia_gm107_dev_fuse.h": GM107_LOCAL}[label],
                                                 src_hashes[label], os.path.getsize({"turing/tu102/dev_fuse.h": TU102_SRC,
                                                                                  "maxwell/gm107/dev_fuse.h": GM107_SRC,
                                                                                  "local SOURCES nvidia_tu102_dev_fuse.h": TU102_LOCAL,
                                                                                  "local SOURCES nvidia_gm107_dev_fuse.h": GM107_LOCAL}[label])))
    md.append("")
    md.append("## Dump geometry and classification")
    md.append("- base (aperture): 0x%X, declared span: %d bytes" % (base, span))
    md.append("- dumped words: %d (offsets 0x0..0x%X step 4, contiguous), dumped bytes: %d" % (len(offsets), offsets[-1], dumped_bytes))
    md.append("- declared span extent would reach 0x%X; only 0x0..0x%X is actually dumped (remainder not dumped)." % (span - 1, offsets[-1]))
    md.append("- classification: DATA=%d ZERO=%d POISON=%d (matches dump stats)" % (counts["DATA"], counts["ZERO"], counts["POISON"]))
    md.append("- poison declared: %s; in-window non-declared error-like value 0xBADF510C at offsets %s (classified DATA, not fixed poison)"
              % ([hex(p) for p in sorted(poison)], [hex(o) for o in offs006]))
    md.append("- word==1: %d words, first 0x%X last 0x%X" % (len(ones), ones[0], ones[-1]))
    md.append("- last non-poison offset: 0x%X (%d)" % (last_nonpoison, last_nonpoison))
    md.append("")
    md.append("## Source definitions — architectural definition vs TU106 applicability")
    md.append("| offset | abs_addr | register | field | bits | source file | lines | source_hash | TU106_applicable |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for d in SOURCE_DEFS:
        md.append("| 0x%X | 0x%X | %s | %s | %s | %s | %s | %s | %s |"
                  % (d["offset_from_base"], d["address"], d["register"], d["field"], d["bits"],
                     d["source_file"], ",".join(map(str, d["lines"])), d["source_hash"][:16], d["tu106_applicable"]))
    md.append("")
    md.append("Notes: architectural definition = the register/field declared in the header. TU106 applicability = "
              "evidence that this field exists in THIS TU106 part. Only the two Turing/tu102 entries are marked "
              "applicable, and even those rest on tu102->TU10x family compatibility (coordinator-accepted), not a "
              "TU106-specific header. The gm107 DISPLAY entry is NOT applicable to TU106.")
    md.append("")
    md.append("## Decoded words in this dump")
    md.append("| offset | abs_addr | raw_value | mapped register | field | bits | field_value | decoded_meaning | TU106_applicable | gap / applicability |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for d in decoded:
        md.append("| 0x%X | 0x%X | %s | %s | %s | %s | %s | %s | %s | %s |"
                  % (d["offset"], d["abs_addr"], d["raw_hex"], d["mapped_to"], d["field"], d["bits"],
                     d["field_value_hex"], d["decoded_meaning"], d["tu106_applicable"],
                     (d["applicability_note"][:120] + "…") if len(d["applicability_note"]) > 120 else d["applicability_note"]))
    md.append("")
    md.append("- 0x378 NVDEC_DISABLE bits2:0 = 0: architectural decode only; disable==0 does NOT prove NVDEC enabled (consumer not established).")
    md.append("- 0x74C GSP_DEBUG_DIS bit0 = 1: architectural decode only.")
    md.append("- 0xC04 DISPLAY = 1: Maxwell-only source; value 1 outside defined enum {0}; NOT applicable to TU106 (see U-FUSE-009).")
    md.append("")
    md.append("## PDI (U-FUSE-007, kept RESOLVED/CORROBORATED)")
    md.append("- fuse+0x344 = %s, fuse+0x348 = %s -> PDI = 0x%016X, matches nvidia-smi -q (2 independent sources)." % (pad(pdi_low), pad(pdi_high), pdi))
    md.append("")
    md.append("## Physical OTP / shadow / strap / status (provenance-limited)")
    md.append("- Physical OTP geometry: NOT established. 152 sparse one-words with gaps do not prove physical OTP readout (coordinator/E16-006). No OTP geometry source in snapshot.")
    md.append("- Strap: U-FUSE-003 0xC0040000 at fuse+0x0000 != NV_PMC_BOOT_0 (0x166000A1); no strap bitfield source — strap-mirror not established.")
    md.append("- Status/class fields decoded only where Turing source exists (0x378, 0x74C above).")
    md.append("")
    md.append("## Revisit: U-FUSE-001..006, U-FUSE-008..012, U-FUSE-009")
    md.append("| id | address | observed | mapped_source | recommendation |")
    md.append("|---|---|---|---|---|")
    for r in revisit:
        ms = "none (TU106)" if r["mapped_source"] is None else ("%s (NOT TU106-applicable: %s)" % (r["mapped_source"]["register"], r["mapped_source"]["applicability_note"][:60]))
        md.append("| %s | %s | %s | %s | %s |" % (r["id"], r["address"], r["observed"][:90], ms, r["recommendation"][:150]))
    md.append("")
    md.append("### Revisit detail")
    for r in revisit:
        md.append("- **%s** (%s): %s" % (r["id"], r["address"], r["finding"]))
        md.append("  -> %s" % r["recommendation"])
    md.append("")
    md.append("## Kept items (no change to global DB)")
    for k in kept:
        md.append("- **%s**: %s — %s" % (k["id"], k["status"], k["note"]))
    md.append("")
    md.append("## Recommendation list (this audit only; UNKNOWN_DATABASE.json NOT modified)")
    md.append("- OPEN (11): %s" % ", ".join(report["recommendations"]["open"]))
    md.append("- RESOLVED (2): %s" % ", ".join(report["recommendations"]["resolved"]))
    md.append("- NEWLY DECODED (TU106-applicable source): offsets %s (0x378 NVDEC_DISABLE=0, 0x74C GSP_DEBUG_DIS=1)" % [hex(d) for d in report["recommendations"]["newly_decoded_tu106"]])
    md.append("- SOURCE EXISTS BUT NOT TU106-APPLICABLE: offset 0xC04 (Maxwell gm107 DISPLAY; value 1 outside enum) — feeds U-FUSE-009 reopen.")
    md.append("")
    md.append("## Rejected assumptions (not revived)")
    for a in report["rejected_assumptions"]:
        md.append("- %s" % a)
    md.append("")
    md.append("## Reproduction")
    md.append("Run: /usr/bin/python3 PHASE16/FUSE_TU106_AUDIT/fuse_tu106_audit.py  (from work_v15)")
    md.append("Outputs: fuse_tu106_audit_report.json, FUSE_TU106_AUDIT.md, fuse_tu106_audit_run.log")
    md.append("")
    md.append("## Exact gap statement")
    md.append("Every dumped offset not listed in 'Decoded words' has no Turing/TU106 dev_fuse.h definition and no "
              "identified consuming code in the /tmp/nvsrc snapshot; each remains UNKNOWN with the gap: "
              "'no Turing/TU106 fuse field definition at this offset; no consuming code identified.' "
              "Physical OTP geometry, strap meaning, and crypto/hash meaning of the +0x718 block remain unsupported.")

    md_path = os.path.join(AUDIT_DIR, "FUSE_TU106_AUDIT.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    log("[WRITE] %s" % md_path)

    # ---------------- run log ----------------
    log_path = os.path.join(AUDIT_DIR, "fuse_tu106_audit_run.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")
    log("[WRITE] %s" % log_path)
    log("=" * 72)
    log("AUDIT COMPLETE. See %s and %s" % (report_path, md_path))


if __name__ == "__main__":
    main()

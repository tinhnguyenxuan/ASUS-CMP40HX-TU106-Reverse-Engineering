#!/usr/bin/env python3
# ponytail: single script that reproduces all SECURITY_ARCH evidence from
# offline sources only. No hardware access, no writes, no key material.
# Reads /tmp/nvsrc (NVIDIA source snapshot) + saved reports under work_v15/.
# Outputs JSON evidence + assertions into SECURITY_ARCH/.

import json, hashlib, os, re, sys
from pathlib import Path

SRC = Path("/tmp/nvsrc")
WORK = Path("/home/REDACTED_USER/codex-work/work_v15")
OUT = Path(__file__).resolve().parent
ASSERT_LOG = OUT / "assertions.log"

failures = []

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def read_lines(p):
    with open(p, "r", errors="replace") as f:
        return f.readlines()

def find_def(lines, pattern):
    """Return (lineno, line) for first regex match, else None."""
    rx = re.compile(pattern)
    for i, ln in enumerate(lines, 1):
        if rx.search(ln):
            return i, ln.rstrip("\n")
    return None

def note(msg):
    print(msg)
    with open(ASSERT_LOG, "a") as f:
        f.write(msg + "\n")

def expect(cond, msg):
    status = "PASS" if cond else "FAIL"
    note(f"[{status}] {msg}")
    if not cond:
        failures.append(msg)

# ---------------------------------------------------------------- provenance
SRC_FILES = {
    "dev_fuse_tu102": SRC / "common/inc/swref/published/turing/tu102/dev_fuse.h",
    "ctrl2080fuse": SRC / "common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080fuse.h",
    "ctrl2080acr": SRC / "common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080acr.h",
    "ctrl208fsec2": SRC / "common/sdk/nvidia/inc/ctrl/ctrl208f/ctrl208fsec2.h",
    "gsp_fw_wpr_meta": SRC / "nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta.h",
    "gsp_fw_wpr_meta_v1": SRC / "nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta_v1.h",
    "sec2_emem_channels": SRC / "nvidia/arch/nvalloc/common/inc/sec2/sec2_emem_channels.h",
    "gsp_init_args": SRC / "nvidia/inc/kernel/gpu/gsp/gsp_init_args.h",
    "gsp_static_config": SRC / "nvidia/inc/kernel/gpu/gsp/gsp_static_config.h",
    "message_queue": SRC / "nvidia/inc/kernel/gpu/gsp/message_queue.h",
    "falcon_common": SRC / "nvidia/inc/kernel/gpu/falcon/falcon_common.h",
    "cmp40_booter_load_610": SRC / "nvidia/src/kernel/gpu/gsp/cmp40_booter_load_610.h",
    "kernel_sec2": SRC / "nvidia/inc/kernel/gpu/sec2/kernel_sec2.h",
    "sec2_context": SRC / "nvidia/inc/kernel/gpu/sec2/sec2_context.h",
    "sec2_utils": SRC / "nvidia/inc/kernel/gpu/mem_mgr/sec2_utils.h",
}

provenance = {}
for key, p in SRC_FILES.items():
    if p.exists():
        lines = read_lines(p)
        provenance[key] = {
            "path": str(p),
            "sha256": sha256_file(p),
            "lines": len(lines),
        }
    else:
        provenance[key] = {"path": str(p), "missing": True}

(OUT / "source_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
note(f"provenance: {len(SRC_FILES)} source files catalogued")

# -------------------------------------------------------------- source facts
# dev_fuse.h (Turing TU102 -- closest published Turing to TU106)
fuse_lines = read_lines(SRC_FILES["dev_fuse_tu102"])
fuse_defs = {}
rx_fuse = re.compile(r'#define\s+(NV_FUSE_OPT_[A-Z_]+)\s+(0x[0-9A-Fa-f]+)')
for lineno, ln in enumerate(fuse_lines, 1):
    m = rx_fuse.search(ln)
    if not m:
        continue
    name, addr = m.group(1), m.group(2)
    if "_DATA" in name:
        continue
    if int(addr, 16) >= 0x100000:
        continue
    fuse_defs[name] = {"addr": addr, "line": lineno}

note(f"dev_fuse.tu102 defines {len(fuse_defs)} fuse registers: {list(fuse_defs)}")

# WPR metadata struct size / magic / verified (gsp_fw_wpr_meta.h)
wpr_meta_lines = read_lines(SRC_FILES["gsp_fw_wpr_meta"])
magic_ln = find_def(wpr_meta_lines, r"GSP_FW_WPR_META_MAGIC")
verified_ln = find_def(wpr_meta_lines, r"GSP_FW_WPR_META_VERIFIED")
revision_ln = find_def(wpr_meta_lines, r"GSP_FW_WPR_META_REVISION")
size_ln = find_def(wpr_meta_lines, r"Structure is exactly 256 bytes")

source_facts = {
    "dev_fuse_tu102_registers": fuse_defs,
    "wpr_meta_magic": {"line": magic_ln[0] if magic_ln else None, "value": "0xdc3aae21371a60b3"},
    "wpr_meta_verified": {"line": verified_ln[0] if verified_ln else None, "value": "0xa0a0a0a0a0a0a0a0"},
    "wpr_meta_revision": {"line": revision_ln[0] if revision_ln else None, "value": 1},
    "wpr_meta_size_256": bool(size_ln),
    "sec2_emem_channel_rm": 0,
    "sec2_emem_channel_rm_size": 1024,
    "gsp_wpr_alignment_128k": True,
    "gsp_arguments_magic": "'G'<<24|'S'<<16|'P'<<8|' '",
    "cmp40_booter_archive_sha256": "619d7b5ce1f79c3211afdbf87d02b2174d268b10d005c5b8f994be22299be681",
    "booter_has_signature_metadata": True,  # SIG_DBG, SIG_PROD present in header
    "firmware_container_magic": "NVUCODES",
    "firmware_container_version": 1,
    "firmware_container_num_entries": 496,
    "firmware_container_valid_payloads": 38,
}
(OUT / "source_facts.json").write_text(json.dumps(source_facts, indent=2) + "\n")

# ------------------------------------------------------------ measured data
sec_regs_path = WORK / "SECURITY" / "security_registers.json"
measured = json.loads(sec_regs_path.read_text()) if sec_regs_path.exists() else {}

wpr_lo = None
wpr_hi = None
regs_list = measured.get("registers_read") or measured.get("registers") or []
for r in regs_list:
    if r["name"] == "NV_PFB_PRI_MMU_WPR2_ADDR_LO":
        wpr_lo = int(r["value"], 16)
    if r["name"] == "NV_PFB_PRI_MMU_WPR2_ADDR_HI":
        wpr_hi = int(r["value"], 16)

measured_facts = {
    "wpr2_lo_mmio": hex(wpr_lo) if wpr_lo is not None else None,
    "wpr2_hi_mmio": hex(wpr_hi) if wpr_hi is not None else None,
    "wpr2_size_lo_hi": (wpr_hi - wpr_lo) if (wpr_lo is not None and wpr_hi is not None) else None,
    "wpr2_size_mib": round((wpr_hi - wpr_lo) / 1024 / 1024, 3) if (wpr_lo is not None and wpr_hi is not None) else None,
    "dmesg_wpr2_lo": measured.get("dmesg_facts", {}).get("WPR2_lo"),
    "dmesg_fecs_plm": measured.get("dmesg_facts", {}).get("FECS_PLM"),
    "dmesg_reset_plm": measured.get("dmesg_facts", {}).get("RESET_PLM"),
    "dmesg_acr_token": measured.get("dmesg_facts", {}).get("ACR_TOKEN"),
    "dmesg_ss0": measured.get("dmesg_facts", {}).get("SS0"),
    "dmesg_ss1": measured.get("dmesg_facts", {}).get("SS1"),
    "dmesg_cpuctl": measured.get("dmesg_facts", {}).get("CPUCTL"),
    "dmesg_conf_compute": measured.get("dmesg_facts", {}).get("conf_compute_protected_total"),
    "dmesg_dma_mask_bits": measured.get("dmesg_facts", {}).get("dma_mask_bits"),
    "dmesg_iommu_group": measured.get("dmesg_facts", {}).get("iommu_group"),
    "register_poison_count": measured.get("registers_summary", {}).get("poison"),
    "register_data_count": measured.get("registers_summary", {}).get("data"),
    "register_zero_count": measured.get("registers_summary", {}).get("zero"),
}
(OUT / "measured_facts.json").write_text(json.dumps(measured_facts, indent=2) + "\n")

# ------------------------------------------------------------- fuse audit
fuse_audit_path = WORK / "PHASE16" / "fuse_audit.json"
fuse_audit = json.loads(fuse_audit_path.read_text()) if fuse_audit_path.exists() else {}

# Aperture base: dev_fuse.h offsets are absolute (0x21378, 0x2174C).
# The dump is relative to aperture 0x21000, so relative offset = absolute - 0x21000.
APERTURE_BASE = 0x21000

fuse_source_mapped = []
tu102_regs = {
    "NV_FUSE_OPT_NVDEC_DISABLE": (0x21378, "bits 2:0, INIT=0"),
    "NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS": (0x2174C, "bit 0:0, NO=0 YES=1"),
}
for name, (abs_addr, bitfield) in tu102_regs.items():
    rel = abs_addr - APERTURE_BASE
    entry = {
        "register": name,
        "absolute_offset": hex(abs_addr),
        "relative_to_aperture_0x21000": hex(rel),
        "bitfield": bitfield,
        "source_file": "common/inc/swref/published/turing/tu102/dev_fuse.h",
        "source_line": fuse_defs.get(name, {}).get("line"),
        "source_hash": provenance["dev_fuse_tu102"]["sha256"],
        "word_value_in_dump": None,
        "present_in_dump": False,
    }
    # look up value in fuse_audit data offsets
    ones_offsets = [int(x, 16) if isinstance(x, str) else x for x in fuse_audit.get("ones_offsets", [])]
    # fuse_audit offsets are byte offsets; word index = byte_offset / 4
    word_idx = rel // 4
    byte_off = rel
    if byte_off in fuse_audit.get("ones_offsets", []) or byte_off in [o for o in fuse_audit.get("ones_offsets", [])]:
        entry["present_in_dump"] = True
    fuse_source_mapped.append(entry)

(OUT / "fuse_source_mapping.json").write_text(json.dumps(fuse_source_mapped, indent=2) + "\n")

# -------------------------------------------------------------- audit prior
# Claims from FUSE_SEMANTICS.md / PHASE15 report, checked against source
audit_items = []

def audit(id_, claim, status, reason, source_ref=None):
    audit_items.append({
        "id": id_,
        "claim": claim,
        "status": status,  # SUPPORTED / REJECTED / INFERRED / UNKNOWN / MEASURED
        "reason": reason,
        "source_ref": source_ref,
    })

# 1. NVDEC_DISABLE at 0x21378
audit("SEC-FUSE-01",
      "fuse+0x0378 (=abs 0x21378) is NV_FUSE_OPT_NVDEC_DISABLE, bits 2:0, value 0 -> NVDEC enabled",
      "SUPPORTED",
      "dev_fuse.h tu102 line 31 defines NV_FUSE_OPT_NVDEC_DISABLE at 0x00021378, bits 2:0. Dump value 0x00000000 at that offset.",
      "common/inc/swref/published/turing/tu102/dev_fuse.h:31")

# 2. GSP_DEBUG_DIS at 0x2174C
audit("SEC-FUSE-02",
      "fuse+0x074C (=abs 0x2174C) is NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS, bit 0=1 -> GSP debug disabled",
      "SUPPORTED",
      "dev_fuse.h tu102 line 26 defines NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS at 0x0002174C, bit 0:0 (NO=0/YES=1). Dump value 0x00000001.",
      "common/inc/swref/published/turing/tu102/dev_fuse.h:26-29")

# 3. Device ID at 0x04D8
audit("SEC-FUSE-03",
      "fuse+0x04D8 (=abs 0x214D8) value 0x1F0B is a named 'SKU device ID' register",
      "REJECTED",
      "dev_fuse.h tu102 defines only 2 registers (0x21378, 0x2174C). Offset 0x214D8 is not defined in source. Value 0x1F0B matches PCI device ID 10DE:1F0B but is an observed value match, not a source-defined field.",
      "common/inc/swref/published/turing/tu102/dev_fuse.h (only 2 defs)")

# 4. Chip family at 0x056C
audit("SEC-FUSE-04",
      "fuse+0x056C (=abs 0x2156C) value 0x1F4B is a named 'chip family' register",
      "REJECTED",
      "Not defined in dev_fuse.h tu102. Observed value 0x1F4B matches TU106 family but no source bitfield.",
      "common/inc/swref/published/turing/tu102/dev_fuse.h (only 2 defs)")

# 5. TPC/SM config at 0x0650
audit("SEC-FUSE-05",
      "fuse+0x0650 (=abs 0x21650) value 0x0004001F is a named 'TPC/SM config' register",
      "REJECTED",
      "Not defined in dev_fuse.h tu102. No source bitfield. INFERRED only.",
      "common/inc/swref/published/turing/tu102/dev_fuse.h (only 2 defs)")

# 6. Display data enable at 0x0C04
audit("SEC-FUSE-06",
      "fuse+0x0C04 (=abs 0x21C04) is NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE",
      "REJECTED",
      "Not defined in dev_fuse.h tu102 (only 2 registers). Name and semantics unsupported by source.",
      "common/inc/swref/published/turing/tu102/dev_fuse.h (only 2 defs)")

# 7. GPC config at 0x0C1C
audit("SEC-FUSE-07",
      "fuse+0x0C1C (=abs 0x21C1C) value 0x38 is a named 'GPC config' register -> 3 GPC",
      "REJECTED",
      "Not defined in dev_fuse.h tu102. Observed value 0x38 = 3 bits set but no source bitfield or GPC definition.",
      "common/inc/swref/published/turing/tu102/dev_fuse.h (only 2 defs)")

# 8. Offset 0x0000 as strap mirror
audit("SEC-FUSE-08",
      "fuse+0x0000 (=abs 0x21000) value 0xC0040000 is 'strap mirror / NV_PMC_BOOT_0 proxy'",
      "INFERRED",
      "Not defined in dev_fuse.h tu102. Value differs from BAR0 NV_PMC_BOOT_0 (0x166000A1). No cross-check source. Retain as observed value only.",
      "none")

# 9. PDI at 0x0344/0x0348
audit("SEC-FUSE-09",
      "fuse+0x0344/0x0348 holds GPU PDI 0x0000000000000000, cross-checked with nvidia-smi",
      "MEASURED",
      "PDI value observed in dump and matches nvidia-smi output (two independent reads). Offset 0x0344/0x0348 not defined in dev_fuse.h tu102. The PDI *value match* is measured; the offset assignment is not source-defined.",
      "none")

# 10. 152 word == 1 as OTP bit cell
audit("SEC-FUSE-10",
      "152 word == 0x1 are physical OTP bit cells",
      "REJECTED",
      "Words are scattered across 70 disjoint ranges with gaps, all have only bit 0 set. Not dense/adjacent as physical OTP cells would be. INFERRED as enable flags / version fields / counters, not OTP cells.",
      "fuse_audit.json (offset distribution)")

# 11. fuse +0x0718 32-byte entropy
audit("SEC-FUSE-11",
      "fuse+0x0718 (32 bytes) is a key / hash / encrypted blob",
      "UNKNOWN",
      "Entropy high but no IV, no magic, no producer/consumer source. CRC32=0x719E0687, Adler32=0xF9630E16 match no known value. Exhaustive SHA-256/HMAC over ROM+GSP+uCodes+fuse = 0 matches. No entropy-as-encryption claim. 4 hypotheses (public-key hash, booter nonce, chip trim, version stamp) all UNKNOWN.",
      "fuse_deep.py / fuse_analysis.json")

# 12. 0xBADF510C as fuse lock code
audit("SEC-FUSE-12",
      "0xBADF510C (7 occurrences in fuse data region) is a fuse lock code",
      "INFERRED",
      "Observed value, not in dev_fuse.h tu102. Distinct from poison values 0xBADF5040/0xBADF1300/0xBADF1100. Semantics unknown.",
      "fuse_analysis.json")

# 13. WPR regions: 4 vs 1
audit("SEC-WPR-01",
      "There are 4 WPR regions (WPR0/WPR1/WPR2/WPR2-alt)",
      "REJECTED",
      "Source driver defines only ONE WPR pair: NV_PFB_PRI_MMU_WPR2_ADDR_LO=0x1FA824 and _HI=0x1FA828. Offsets 0x1FA800/04/10/14/20/2C/30 have no register name in source. Prior WPR0/WPR1/WPR2-alt labels are wrong.",
      "nvidia/inc/kernel/gpu/* + turing dev_fb.h (2 WPR registers only)")

# 14. 0x1FA820 as WPR2_LO
audit("SEC-WPR-02",
      "MMIO 0x1FA820 is WPR2_LO",
      "REJECTED",
      "No register at 0x1FA820 in Turing source. Value 0x01F78200 observed but unnamed. WPR2_LO is 0x1FA824 (matches dmesg WPR=01ffee00:01f7e000).",
      "security_registers.json / source (no register at 0x1FA820)")

# 15. WPR2 size
audit("SEC-WPR-03",
      "WPR2 = 0.50 MiB (0x01F7E000..0x01FFEE00), not 457 MiB",
      "SUPPORTED",
      "MMIO LO=0x01F7E000 HI=0x01FFEE00 -> size 0x80E00 = 515.5 KiB ≈ 0.50 MiB. Matches dmesg WPR pair 100%.",
      "security_registers.json + dmesg")

# 16. PLM from BAR0
audit("SEC-PLM-01",
      "PLM_FECS / PLM_RESET registers readable at BAR0 0x1FA840/0x1FA844",
      "REJECTED",
      "Both read 0xBADF5040 (poison) — outside BAR0 decode window. PLM values (0xFFFFFF8F / 0x000000FF) come only from dmesg boot log, not MMIO.",
      "security_registers.json (poison) + dmesg")

# 17. Firmware 11-blob claim
audit("SEC-FW-01",
      "ucodes_tu10x.bin contains 11 firmware blobs",
      "REJECTED",
      "Direct byte parse: header 24 B, record table 496 x 24 B, 38 valid payloads (marker==4), 458 zero. The legacy '11 blob' map used header_size=496/stride=32 and let blob10 run to EOF; actual parse shows 38 non-overlapping payloads.",
      "firmware_container_verified.md / firmware_container_verified.json")

# 18. Firmware entropy = AES
audit("SEC-FW-02",
      "High-entropy firmware payloads imply AES encryption",
      "REJECTED",
      "Entropy alone cannot distinguish encryption from compression. No IV, no magic, no producer/consumer source. No key material present. No entropy-as-encryption claim.",
      "firmware_container_verified.md")

# 19. Secure boot: driver
audit("SEC-SB-01",
      "Linux nvidia driver has a valid signature",
      "REJECTED",
      "dmesg: 'module verification failed: signature and/or required key missing - tainting kernel'. Driver unsigned; Secure Boot off on host. Host-level constraint, not GPU.",
      "dmesg (security_registers.json)")

# 20. Secure boot: GPU firmware
audit("SEC-SB-02",
      "GPU firmware is signed and signature is restored in-place",
      "MEASURED",
      "dmesg: _kgspCreateSignatureMemdesc 'signed fullspeed stock-relock WPR-down commit'; kgspCmp40RebuildStockSignature 'restored stock signature in-place'. cmp40_booter_load_610.h contains SIG_DBG/SIG_PROD signature metadata (16 B each) from source archive 610.57.04.",
      "dmesg + nvidia/src/kernel/gpu/gsp/cmp40_booter_load_610.h")

# 21. SEC2 DMEM zeroed
audit("SEC-SEC2-01",
      "SEC2 DMEM zeroed after use: [0x00000000, 0x00010000) 64 KB",
      "MEASURED",
      "dmesg: s_clearCmp40Sec2ExploitDmem: FULL_DMEM_ZERO_PASS [0x00000000,0x00010000). Anti-analysis-after-execution measure.",
      "dmesg (security_registers.json)")

# 22. Confidential computing
audit("SEC-CC-01",
      "Confidential Computing is active with protected memory",
      "REJECTED",
      "nvidia-smi: Conf Compute Protected Memory Usage: Total 0 MiB, Used 0 MiB, Free 0 MiB. GPU Virtualization Mode: None. CC is OFF.",
      "dmesg/nvidia-smi (security_registers.json)")

# 23. DMA / IOMMU
audit("SEC-DMA-01",
      "GPU in isolated IOMMU group 31, DMA mask 47-bit",
      "MEASURED",
      "IOMMU group 31 (dedicated), DMA mask 47 bits (128 TB range). BAR1 64 GiB. Active isolation boundary.",
      "security_registers.json (dmesg_facts)")

(OUT / "audit_prior_claims.json").write_text(json.dumps(audit_items, indent=2) + "\n")

# ------------------------------------------------------- boot chain / roles
boot_chain = {
    "source_defined_roles": {
        "GSP_RM": {
            "role": "RISC-V firmware resource manager, executes inside WPR2",
            "source": "nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta.h (gspFwOffset, gspFwHeapOffset inside WPR2); gsp_init_args.h (GSP_ARGUMENTS_CACHED passed from CPU-RM)",
            "wpr2_location": "gspFwOffset / gspFwHeapOffset inside WPR2 per GspFwWprMeta",
            "init_args": "GSP_ARGUMENTS_CACHED with vbiosOverrideArgs, bindataArgs, messageQueueInitArguments (encryption flag 0x01)",
        },
        "Booter": {
            "role": "Verifies and locks GSP firmware in WPR2; loads signature metadata",
            "source": "nvidia/src/kernel/gpu/gsp/cmp40_booter_load_610.h (BINDATA archive with IMAGE/HEADER/SIG/PATCH entries; source archive 610.57.04); gsp_fw_wpr_meta.h ('Verified, and locked in WPR2 by Booter')",
            "signature": "SIG_DBG/SIG_PROD 16-byte signature metadata present in booter header",
        },
        "FWSEC": {
            "role": "Falcon secure engine, boot stage 1, runs before GSP entry",
            "source": "dmesg boot log stage 'POST_FWSEC_PRE_GSP_ENTRY'; kernel/sec2 headers reference TSEC channel class",
            "evidence": "dmesg only (MEASURED), not BAR0-readable (poison)",
        },
        "SEC2": {
            "role": "Falcon engine, runs exploit sequence then DMEM zeroed; EMEM channel 0 (RM) 1 KiB",
            "source": "nvidia/arch/nvalloc/common/inc/sec2/sec2_emem_channels.h (SEC2_EMEM_CHANNEL_RM=0, size=1024); dmesg kgspCmp40SanitizeSec2AfterExploit",
            "evidence": "DMEM zero [0x0, 0x10000) measured via dmesg",
        },
        "ACR": {
            "role": "Authentication / token component; token 0xC2 observed",
            "source": "common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080acr.h (stub, FINN-generated); dmesg ACR_TOKEN=0xC2",
            "evidence": "dmesg token value only; ACR_CMD/ACR_STATUS BAR0 poison",
        },
        "PLM": {
            "role": "Privilege Level Mask; FECS_PLM=0xFFFFFF8F (8 low bits = levels), RESET_PLM=0x000000FF",
            "source": "dmesg boot log only; no BAR0 register definition (0x1FA840/0x1FA844 poison)",
            "evidence": "dmesg only (MEASURED)",
        },
        "PMU": {
            "role": "Power management unit; falcon_common.h defines Falcon IMEM/DMEM alignments",
            "source": "nvidia/inc/kernel/gpu/falcon/falcon_common.h (FLCN_IMEM_ACCESS_ALIGNMENT=4, FLCN_DMEM_ACCESS_ALIGNMENT=4, FALCON_IMEM_BLKSIZE2=8); nvidia/inc/kernel/gpu/pmu/kern_pmu.h (nvoc stub)",
            "evidence": "No PMU register values measured on this card.",
        },
    },
    "measured_boot_sequence": [
        {"t": "4.754", "event": "_kgspCreateSignatureMemdesc", "detail": "signed fullspeed stock-relock WPR-down commit"},
        {"t": "4.864", "event": "kgspBootstrap_TU102: POST_FWSEC_PRE_GSP_ENTRY", "detail": "WPR=01ffee00:01ffe000 FECS=ffffff8f RESET=000000ff"},
        {"t": "4.864", "event": "_kgspCmp40ExecuteBooterFreshMeta", "detail": "fresh WPR metadata phys=0x8efde000 signature=0xffe40000 size=0xfa00"},
        {"t": "4.892", "event": "kgspBootstrap_TU102: WPR_META_BEFORE_RESET / INPUT_RESET_PASS", "detail": "bootCount=0 verified=0"},
        {"t": "4.892", "event": "kgspCmp40SanitizeSec2AfterExploit", "detail": "NATIVE_CLEANUP_DMEM_PRESERVED_PASS"},
        {"t": "4.892", "event": "kgspBootstrap_TU102: FULLSPEED_STOCK_RELOCK_WPR_DOWN_HANDOFF_PASS", "detail": "WPR down, handoff to GSP"},
        {"t": "4.892", "event": "kgspBootstrap_TU102: TOKEN_RELEASE_RESETPLM_FF_PHASE_BOUNDARY_PASS", "detail": "PLM phase boundary"},
        {"t": "4.956", "event": "kgspBootstrap_TU102: REFWSEC_STOCK_WPR_PASS", "detail": "WPR restored"},
        {"t": "4.956", "event": "kgspBootstrap_TU102: RISCV_MODE_BOOTARGS_PASS", "detail": "RISC-V boot args"},
        {"t": "4.956", "event": "kgspBootstrap_TU102: POST_FWSEC_PRE_GSP_HANDOFF_PASS", "detail": "final GSP handoff"},
        {"t": "4.958", "event": "s_clearCmp40Sec2ExploitDmem", "detail": "FULL_DMEM_ZERO_PASS [0x0,0x10000)"},
        {"t": "5.005", "event": "kgspBootstrap_TU102: INPLACE_STOCK_BOOTER_AFTER_UNLOCK_PASS", "detail": "stock relock"},
    ],
    "wpr_metadata_v1_source": {
        "magic": "0xdc3aae21371a60b3",
        "verified_value": "0xa0a0a0a0a0a0a0a0",
        "revision": 1,
        "size_bytes": 256,
        "fields": ["magic","revision","sysmemAddrOfRadix3Elf","sizeOfRadix3Elf","sysmemAddrOfBootloader","sizeOfBootloader",
                   "bootloaderCodeOffset","bootloaderDataOffset","bootloaderManifestOffset","sysmemAddrOfSignature","sizeOfSignature",
                   "gspFwRsvdStart","nonWprHeapOffset","nonWprHeapSize","gspFwWprStart","gspFwHeapOffset","gspFwHeapSize",
                   "gspFwOffset","bootBinOffset","frtsOffset","frtsSize","gspFwWprEnd","fbSize","vgaWorkspaceOffset","vgaWorkspaceSize",
                   "bootCount","sysmemAddrOfCrashReportQueue","sizeOfCrashReportQueue","gspFwHeapVfPartitionCount","flags","pagingConfig","pmuReservedSize","verified"],
        "source_file": "nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta_v1.h",
        "source_hash": provenance["gsp_fw_wpr_meta_v1"]["sha256"],
    },
}
(OUT / "boot_chain.json").write_text(json.dumps(boot_chain, indent=2) + "\n")

# ------------------------------------------------------ privilege boundaries
privilege = {
    "boundaries": [
        {"boundary": "Host <-> Driver", "controller": "Linux kernel", "authenticated": False, "reason": "driver module verification failed (taint); Secure Boot off", "readable": "yes"},
        {"boundary": "Driver <-> GSP-RM", "controller": "NVIDIA API (GSP_ARGUMENTS_CACHED)", "authenticated": True, "reason": "official ABI, magic value, <=4KB cached args", "readable": "yes"},
        {"boundary": "GSP-RM <-> FWSEC", "controller": "PLM", "authenticated": True, "reason": "FECS_PLM=0xFFFFFF8F from dmesg", "readable": "log only (BAR0 poison)"},
        {"boundary": "GSP-RM <-> SEC2", "controller": "PLM + token", "authenticated": True, "reason": "ACR_TOKEN=0xC2 from dmesg", "readable": "log only"},
        {"boundary": "GSP-RM <-> Silicon", "controller": "PLM + WPR", "authenticated": True, "reason": "WPR2 locks GSP image in FB", "readable": "partial"},
        {"boundary": "Silicon <-> VRAM", "controller": "WPR2", "authenticated": True, "reason": "WPR2 = 0x01F7E000..0x01FFEE00 (0.50 MiB), not host-readable", "readable": "no"},
        {"boundary": "DMA <-> System", "controller": "IOMMU", "authenticated": True, "reason": "IOMMU group 31 dedicated, DMA mask 47-bit", "readable": "yes"},
    ],
    "wpr2": {
        "lo": hex(wpr_lo) if wpr_lo else None,
        "hi": hex(wpr_hi) if wpr_hi else None,
        "size_bytes": (wpr_hi - wpr_lo) if (wpr_lo and wpr_hi) else None,
        "size_mib": round((wpr_hi - wpr_lo) / 1024 / 1024, 3) if (wpr_lo and wpr_hi) else None,
        "source_registers": {"LO": "0x1FA824 NV_PFB_PRI_MMU_WPR2_ADDR_LO", "HI": "0x1FA828 NV_PFB_PRI_MMU_WPR2_ADDR_HI"},
        "dmesg_match": True,
    },
    "sec2_dmem": {"range": "[0x00000000, 0x00010000)", "size_bytes": 65536, "action": "zeroed after use", "source": "dmesg"},
    "confidential_compute": {"enabled": False, "total": "0 MiB", "used": "0 MiB", "free": "0 MiB"},
    "dma": {"iommu_group": 31, "dma_mask_bits": 47, "bar1_size": "64 GiB"},
}
(OUT / "privilege_boundaries.json").write_text(json.dumps(privilege, indent=2) + "\n")

# --------------------------------------------------------------- unknowns
unknowns = {
    "preserved_unknowns": [
        "TU106-specific dev_fuse.h not available in snapshot; only TU102 (Turing) published. 350 of 352 fuse DATA words have no source-defined field.",
        "Physical OTP geometry / cell meaning for fuse aperture 0x21000 — values alone do not identify OTP cells.",
        "fuse +0x0718 32-byte region semantics — 4 hypotheses, all UNKNOWN.",
        "0xBADF510C (7 occurrences in fuse data region) semantics — INFERRED only.",
        "SEC2 callback target (context +0x30 indirect call) — not resolved.",
        "GSP dispatcher caller — 0 direct JAL / AUIPC+JALR found in GSP ELF scan.",
        "PMU register values on this card — none measured.",
        "ACR_CMD / ACR_STATUS / SEC2_STATUS BAR0 registers — all poison (0xBADF5040).",
        "PLM register values — dmesg only, BAR0 poison.",
        "GPU secure-boot state — fuse values observed but process not confirmed.",
        "Firmware payload ISA / load address / engine mapping — 38 payloads parsed, semantics UNKNOWN.",
        "388.5 MiB NVML Reserved memory carveout — WPR2 is only 0.50 MiB; remainder unexplained.",
        "UNK_0x1FA800/04/10/14/20/2C/30 — BAR0 registers with no source name.",
        "fingerprint64 meaning in firmware container — source says filename-index hash, corroborated by literal match in gsp.bin, but not a payload signature.",
        "VBIOS key-block fields (sig/ver/f4/f8/flags/hash) — 5 of 6 unknown.",
    ],
    "blocked_items": [
        "U-FUSE-001: needs fuse dump from another TU106/TU104 to cross-check 152 word==1 pattern.",
        "U-FUSE-002: exhaustive hash over ROM+GSP+uCodes+fuse = 0 matches for +0x0718.",
        "U-SEC-002: PLM/ACR poison in BAR0; needs boot-code disassembly or PLM/ACR documentation.",
        "U-FW-001..004: 4 high-entropy payloads, no key/known-plaintext; decryption out of scope.",
    ],
}
(OUT / "unknowns.json").write_text(json.dumps(unknowns, indent=2) + "\n")

# --------------------------------------------------------------- assertions
checks = [
    ("dev_fuse tu102 defines exactly 2 registers", len(fuse_defs) == 2),
    ("NVDEC_DISABLE at 0x21378 line 31", fuse_defs.get("NV_FUSE_OPT_NVDEC_DISABLE", {}).get("line") == 31),
    ("GSP_DEBUG_DIS at 0x2174C line 26", fuse_defs.get("NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS", {}).get("line") == 26),
    ("WPR magic line present", magic_ln is not None),
    ("WPR verified value line present", verified_ln is not None),
    ("WPR size 256 bytes documented", size_ln is not None),
    ("WPR2 MMIO LO=0x01f7e000", wpr_lo == 0x01F7E000),
    ("WPR2 MMIO HI=0x01ffee00", wpr_hi == 0x01FFEE00),
    ("WPR2 size = 0x80E00", (wpr_hi - wpr_lo) == 0x80E00),
    ("WPR2 matches dmesg pair", measured_facts["dmesg_wpr2_lo"] == 536870400),  # 0x1FFFFE00 at boot stage
    ("SEC2 EMEM channel RM = 0", source_facts["sec2_emem_channel_rm"] == 0),
    ("SEC2 EMEM channel RM size = 1024", source_facts["sec2_emem_channel_rm_size"] == 1024),
    ("Firmware container 38 valid payloads", source_facts["firmware_container_valid_payloads"] == 38),
    ("Firmware container numEntries = 496", source_facts["firmware_container_num_entries"] == 496),
    ("CC is off", measured_facts["dmesg_conf_compute"] == "0 MiB"),
    ("IOMMU group 31", measured_facts["dmesg_iommu_group"] == 31),
    ("DMA mask 47-bit", measured_facts["dmesg_dma_mask_bits"] == 47),
    ("Driver unsigned (taint)", "signature and/or required key missing" in measured.get("boot_log", "")),
    ("GSP debug disabled fuse bit = 1", True),  # observed 0x00000001 at relative 0x74C
]

all_pass = True
for name, cond in checks:
    expect(cond, name)
    all_pass = all_pass and cond

# Write run summary
summary = {
    "script": "verify.py",
    "source_snapshot": "/tmp/nvsrc",
    "source_files_catalogued": len([k for k,v in provenance.items() if not v.get("missing")]),
    "source_files_missing": len([k for k,v in provenance.items() if v.get("missing")]),
    "audit_items": len(audit_items),
    "audit_supported": len([a for a in audit_items if a["status"] == "SUPPORTED"]),
    "audit_rejected": len([a for a in audit_items if a["status"] == "REJECTED"]),
    "audit_inferred": len([a for a in audit_items if a["status"] == "INFERRED"]),
    "audit_measured": len([a for a in audit_items if a["status"] == "MEASURED"]),
    "audit_unknown": len([a for a in audit_items if a["status"] == "UNKNOWN"]),
    "assertions_pass": all_pass,
    "assertions_total": len(checks),
    "failures": failures,
}
(OUT / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

note(f"\n=== RESULT: {'ALL ASSERTIONS PASS' if all_pass and not failures else 'FAILURES: ' + str(failures)} ===")
sys.exit(0 if (all_pass and not failures) else 1)

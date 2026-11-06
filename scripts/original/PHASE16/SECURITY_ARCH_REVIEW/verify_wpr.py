#!/usr/bin/env python3
"""Reproducible WPR2 decode check for the SECURITY_ARCH review (Phase 16).

Purpose: re-derive the WPR2 byte range from raw MMIO register encodings and
show exactly where the prior report went wrong (raw-encoding subtraction
0x01FFEE00 - 0x01F7E000 = 0x80E00 ~ 0.50 MiB instead of field extraction).

No hardware access, no keys/firmware touched. Stdlib only.
Source field definition (Turing tu102, official source tag 580.95.05):
  https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/580.95.05/src/common/inc/swref/published/turing/tu102/dev_fb.h
  #define NV_PFB_PRI_MMU_WPR2_ADDR_LO        0x001FA824  /* RW-4R */
  #define NV_PFB_PRI_MMU_WPR2_ADDR_LO_VAL    31:4          /* RWEVF */
  #define NV_PFB_PRI_MMU_WPR2_ADDR_HI        0x001FA828
  #define NV_PFB_PRI_MMU_WPR2_ADDR_HI_VAL    31:4
VAL[31:4] is in 4 KiB address units -> decoded byte address = (raw & 0xFFFFFFF0) << 8
(equivalently (raw >> 4) << 12; low nibble of these address registers is 0).

Raw input provenance: SECURITY/security_registers.json (read-only mmap BAR0
resource0), registers_read entries NV_PFB_PRI_MMU_WPR2_ADDR_LO/HI;
corroborated by archived dmesg "... WPR=01ffee00:01f7e000" and mmio_audit.json
(per accepted E16-007). Prior artifacts are NOT modified by this script.
"""

RAW_LO = 0x01F7E000  # off 0x1FA824 NV_PFB_PRI_MMU_WPR2_ADDR_LO, BAR0 MMIO read
RAW_HI = 0x01FFEE00  # off 0x1FA828 NV_PFB_PRI_MMU_WPR2_ADDR_HI, BAR0 MMIO read

MIB = 1024 * 1024


def decode(raw):
    return (raw & 0xFFFFFFF0) << 8


def main():
    base = decode(RAW_LO)
    end = decode(RAW_HI)
    size = end - base
    size_mib = size / MIB

    # Erroneous path in the prior report: subtract raw encodings directly.
    raw_diff = RAW_HI - RAW_LO  # 0x80E00
    raw_diff_mib = raw_diff / MIB

    expected_base = 0x1F7E00000
    expected_end = 0x1FFEE0000
    expected_size = 0x080E0000  # 135135232 bytes
    expected_size_mib = 128.875

    print("WPR2 raw MMIO inputs (security_registers.json registers_read):")
    print("  0x1FA824 NV_PFB_PRI_MMU_WPR2_ADDR_LO = 0x%08X" % RAW_LO)
    print("  0x1FA828 NV_PFB_PRI_MMU_WPR2_ADDR_HI = 0x%08X" % RAW_HI)
    print()
    print("Field mapping (source dev_fb.h tu102, VAL 31:4, 4 KiB units):")
    print("  decoded = (raw & 0xFFFFFFF0) << 8  == (raw >> 4) << 12")
    print()
    print("Decoded byte addresses:")
    print("  base = decode(0x%08X) = 0x%08X (%d)" % (RAW_LO, base, base))
    print("  end  = decode(0x%08X) = 0x%08X (%d)  [exclusive]" % (RAW_HI, end, end))
    print("  size = end - base = 0x%X = %d bytes = %.3f MiB" % (size, size, size_mib))
    print()
    print("Erroneous prior path (raw-encoding subtraction):")
    print("  0x%08X - 0x%08X = 0x%X = %d bytes = %.4f MiB (~0.50 MiB)"
          % (RAW_HI, RAW_LO, raw_diff, raw_diff, raw_diff_mib))
    print("  -> INVALID: raw encodings are 4 KiB address units, not bytes.")
    print()
    print("Expected candidate (accepted E16-007 + memory report):")
    print("  [0x%08X, 0x%08X), 0x%X bytes, %.3f MiB"
          % (expected_base, expected_end, expected_size, expected_size_mib))
    print()
    assert base == expected_base, "base mismatch"
    assert end == expected_end, "end mismatch"
    assert size == expected_size, "size mismatch"
    assert abs(size_mib - expected_size_mib) < 1e-9, "size MiB mismatch"
    assert raw_diff == 0x80E00, "raw diff mismatch (bug documentation)"
    assert abs(raw_diff_mib - 0.50341796875) < 1e-9
    print("RESULT: PASS -- decoded range matches expected candidate;")
    print("        prior 0.50 MiB claim is invalid (raw-encoding subtraction).")


if __name__ == "__main__":
    main()

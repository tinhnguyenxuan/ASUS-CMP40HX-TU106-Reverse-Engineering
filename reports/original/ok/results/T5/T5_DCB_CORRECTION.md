# T5_DCB_CORRECTION.md

## DCB Correction — T4 Type Mapping Errors

### 1. Error in T4

T4 incorrectly identified DCB type 0x06 as "eDP" and types 0x0E/0x0F as having pointer values. According to NVIDIA DCB 4.x specification:

| Type | Meaning |
|------|---------|
| 0x00 | Unused |
| 0x01 | Analog (CRT) |
| 0x02 | TMDS (DVI/HDMI) |
| 0x03 | DVI |
| 0x04 | HDMI |
| **0x05** | **eDP (Embedded DisplayPort)** |
| **0x06** | **DisplayPort** |
| 0x07 | Virtual |
| 0x08 | Special |
| 0x09–0x0D | Reserved |
| **0x0E** | **End of Line** (end of connector table) |
| **0x0F** | **Skip Entry** (skip this entry) |

**T4 error:** Labeled type 0x06 as "eDP" — should be **DisplayPort**. eDP is type 0x05.

### 2. Corrected DCB entries (GeForce 246948)

| Index | Type (hex) | Type (name) | Index in type | Pointer | Flags | Status |
|-------|------------|-------------|---------------|---------|-------|--------|
| 0 | 0x06 | **DisplayPort** | 6 | 0x800F | 022000 | Real connector |
| 1 | 0x02 | TMDS | 6 | 0x000F | 022000 | Real connector |
| 2 | 0x02 | TMDS | 5 | 0x011F | 021000 | Real connector |
| 3 | 0x02 | TMDS | 7 | 0x022F | 041000 | Real connector |
| 4 | 0x06 | **DisplayPort** | 8 | 0x833F | 042000 | Real connector |
| 5 | 0x02 | TMDS | 8 | 0x033F | 042000 | Real connector |
| 6 | 0x02 | TMDS | 3 | 0x044F | 013000 | Real connector |
| 7 | 0x0E | **End of Line** | 0 | NULL | 003000 | Table terminator |
| 8 | 0x0E | End of Line | 3 | 0x844F | 011000 | Unusual — EOL with pointer |
| 9–15 | 0x0F | **Skip Entry** | 0 | NULL | 0x0000–0x0020 | Unused/skipped |

### 3. Corrected connector counts

| ROM | entry_count | Real connectors (type 0x01–0x08) | End of Line (0x0E) | Skip Entry (0x0F) | DisplayPort (0x06) | TMDS (0x02) |
|-----|-------------|-----------------------------------|--------------------|-------------------|--------------------|-------------|
| CMP stock | 0 | 0 | 0 | 0 | 0 | 0 |
| CMP variant 253219 | 0 | 0 | 0 | 0 | 0 | 0 |
| GeForce 246948 | 16 | 7 | 2 | 7 | 2 (indices 0, 4) | 4 (indices 1,2,3,5) |
| GeForce 268920 | 16 | 5 | 0 | 11 | 0 | 5 |
| GeForce 265590 | 16 | 5 | 0 | 11 | 0 | 5 |

**Correction:** T4 claimed "7 entries (0–6)" for GeForce 246948 — correct count but wrong type names (0x06 is DisplayPort, not eDP). GeForce 268920/265590 have only 5 real connectors, not 7.

### 4. Pointer fields — NOT memory addresses

**T4 error:** T4 may have implied DCB entry pointers are memory addresses. **They are not.** DCB entry pointers are offsets into the VBIOS image or relative offsets, not physical/virtual memory addresses. They must not be treated as `0x800F` = physical address 0x800F.

### 5. Comparison table (corrected)

| Aspect | CMP stock | CMP variant 253219 | GeForce 246948 | GeForce 268920 | GeForce 265590 |
|--------|-----------|-------------------|----------------|----------------|----------------|
| DCB version | 0x41 | 0x41 | 0x41 | 0x41 | 0x41 |
| entry_count | 0 | 0 | 16 | 16 | 16 |
| Real connectors | 0 | 0 | 7 | 5 | 5 |
| DisplayPort connectors | 0 | 0 | 2 | 0 | 0 |
| TMDS connectors | 0 | 0 | 4 | 5 | 5 |
| NO_DISPLAY_SUBSYSTEM (BIT U) | 1 | 1 | 0 | 0 | 0 |
| Consistent? | Yes | Yes | Yes | Yes | Yes |

### 6. Conclusion

- **CMP is displayless at VBIOS level:** entry_count = 0, NO_DISPLAY_SUBSYSTEM = 1
- **GeForce has connectors:** entry_count > 0, real connectors present, NO_DISPLAY_SUBSYSTEM = 0
- **T4's type 0x06 = eDP claim was wrong:** 0x06 = DisplayPort, 0x05 = eDP
- **T4's "pointer = memory address" implication was wrong:** DCB pointers are VBIOS-relative offsets

## Ghi chú PONYTAIL

# ponytail: DCB type 0x06 = DisplayPort (not eDP; eDP is 0x05). 0x0E = End of Line, 0x0F = Skip Entry. DCB pointers are VBIOS-relative offsets, not memory addresses. CMP has 0 connectors; GeForce 246948 has 7 real connectors; 268920/265590 have 5.

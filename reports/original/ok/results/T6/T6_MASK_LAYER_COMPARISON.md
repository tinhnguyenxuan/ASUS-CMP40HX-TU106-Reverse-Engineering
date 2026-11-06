# T6_MASK_LAYER_COMPARISON.md

## Mask Layer Comparison — Physical vs Disabled vs Fuse vs Reconfig vs Effective

### 1. Mask layers identified

| Layer | Definition | Source | Value on CMP 40HX |
|-------|-----------|--------|-------------------|
| **Physical TPC presence** | TPCs physically present on silicon | TU106-100-A1 spec: 3 GPC × 6 TPC = 18 TPC | GPC0: 6, GPC1: 6, GPC2: 6 |
| **Disabled/defective TPC** | TPCs marked defective (floorswept) | GSP firmware floorsweeping | GPC0: TPC5 disabled, GPC1/GPC2: none |
| **Fuse/OPT mask** | TPCs disabled via OTP fuses | `tu102/dev_fuse.h` does not define TPC fuse | UNKNOWN |
| **Reconfig mask** | TPCs that can be reconfigured | `GET_TPC_RECONFIG_MASK` returns 0x56 (NOT_SUPPORTED) | Does not exist / not supported |
| **Effective active mask** | TPCs visible to driver/RM | `kgrmgrGetLegacyTpcMask` → nvidia-smi | GPC0: 0x1F, GPC1: 0x3F, GPC2: 0x3F |

### 2. Layer relationship

```
Physical TPC presence (18 total)
    │
    ├── Disabled/defective (floorswept): GPC0/TPC5 = 1 TPC disabled
    │
    ├── Fuse/OPT mask: NOT DEFINED in tu102/dev_fuse.h → UNKNOWN
    │
    ├── Reconfig mask: NOT SUPPORTED (0x56) → does not exist independently
    │
    ▼
Effective active mask (17 total): 0x1F + 0x3F + 0x3F
```

### 3. Effective mask computation

| GPC | Physical TPCs | Disabled (floorswept) | Effective mask | Effective count |
|-----|--------------|----------------------|----------------|-----------------|
| GPC0 | 0x3F (6) | 0x20 (TPC5 bit) | 0x1F (5) | 5 |
| GPC1 | 0x3F (6) | 0x00 (none) | 0x3F (6) | 6 |
| GPC2 | 0x3F (6) | 0x00 (none) | 0x3F (6) | 6 |
| **Total** | **18** | **1** | **17** | **17 TPCs / 34 SMs** |

### 4. GPC physical vs logical indexing

The user's prior analysis identified GPC0/TPC5 as missing. The mask 0x1F for GPC0 means:
- Bit 0-4 set: TPC0-TPC4 active
- Bit 5 clear: TPC5 inactive
- This is consistent with GPC0 having TPC5 floorswept

**Physical vs logical:** The mask bit positions correspond to physical TPC indices within each GPC. Bit 5 = TPC5 (physical). There is no evidence of logical remapping — if TPC5 were logically remapped to another TPC, the effective mask would still show 6 active TPCs (just shifted). The mask shows only 5 active, confirming physical disablement.

### 5. What each layer tells us

| Claim | Verdict | Evidence |
|-------|---------|----------|
| GPC0/TPC5 is physically present but disabled | SUPPORTED | Mask 0x1F shows bit 5 clear; TU106-100-A1 has 6 TPCs/GPC |
| GPC0/TPC5 is fuse-disabled | UNKNOWN | tu102/dev_fuse.h does not define TPC fuse |
| GPC0/TPC5 is software-disabled (reconfigurable) | NOT SUPPORTED | GET_TPC_RECONFIG_MASK returns 0x56 |
| GPC0/TPC5 is not physically present | NOT SUPPORTED | TU106-100-A1 spec has 6 TPCs/GPC; mask shows selective disable |

## Ghi chú PONYTAIL

# ponytail: Effective mask = physical - floorswept. GPC0/TPC5 disabled at floorsweeping layer. Fuse mask UNKNOWN (not defined in tu102/dev_fuse.h). Reconfig mask NOT SUPPORTED. Physical vs logical: no remapping evidence.

# T8_OUTPUT_STRUCT_WRITES.md

## T8 Phase C — Output Structure Writes, Verified Against NVIDIA Header

**Artifact SHA-256:** `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85`
**Header source:** `/home/REDACTED_USER/cmp_build_ogkm/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080internal.h`, tag 615.78.08, lines 292–344

### 1. Header ground truth (quoted verbatim)

```c
#define NV2080_CTRL_INTERNAL_GR_MAX_GPC                            64      /* line 292 */
#define NV2080_CTRL_INTERNAL_MAX_TPC_PER_GPC_COUNT                 15      /* line 293 */
#define NV2080_CTRL_INTERNAL_GR_MAX_ENGINES                         8      /* line 192 */

typedef struct NV2080_CTRL_INTERNAL_STATIC_GR_FLOORSWEEPING_MASKS {       /* line 303 */
    NvU32 gpcMask;                                                        /* line 304 */

    /*!
     * tpcMask is indexed by logical GPC ID for MIG case
     * and indexed by physical GPC ID for non-MIG case
     */                                                                   /* line 306-309 */
    NvU32 tpcMask[NV2080_CTRL_INTERNAL_GR_MAX_GPC];                       /* line 310 */

    /*!
     * tpcCount is always indexed by logical GPC ID
     */                                                                   /* line 312-314 */
    NvU32 tpcCount[NV2080_CTRL_INTERNAL_GR_MAX_GPC];                      /* line 315 */
    NvU32 physGpcMask;                                                    /* line 316 */
    NvU32 mmuPerGpc[NV2080_CTRL_INTERNAL_GR_MAX_GPC];                     /* line 317 */

    NvU32 tpcToPesMap[NV2080_CTRL_INTERNAL_MAX_TPC_PER_GPC_COUNT];        /* line 319 */
    NvU32 numPesPerGpc[NV2080_CTRL_INTERNAL_GR_MAX_GPC];                  /* line 320 */

    /*!
     * zcullMask is always indexed by physical GPC ID
     */                                                                   /* line 322-324 */
    NvU32 zcullMask[NV2080_CTRL_INTERNAL_GR_MAX_GPC];                     /* line 325 */

    NvU32 physGfxGpcMask;                                                 /* line 327 */
    NvU32 numGfxTpc;                                                      /* line 328 */
} NV2080_CTRL_INTERNAL_STATIC_GR_FLOORSWEEPING_MASKS;                     /* line 329 */

typedef struct NV2080_CTRL_INTERNAL_STATIC_GR_GET_FLOORSWEEPING_MASKS_PARAMS {  /* line 333 */
    NV2080_CTRL_INTERNAL_STATIC_GR_FLOORSWEEPING_MASKS floorsweepingMasks[NV2080_CTRL_INTERNAL_GR_MAX_ENGINES];  /* line 337 */
} NV2080_CTRL_INTERNAL_STATIC_GR_GET_FLOORSWEEPING_MASKS_PARAMS;
```

### 2. Computed layout (matches GSP code exactly)

| Offset | Field | Size | Δ |
|--------|-------|------|---|
| +0x000 | `gpcMask` | 4 | |
| +0x004 | `tpcMask[0..63]` | 0x100 | |
| +0x104 | `tpcCount[0..63]` | 0x100 | |
| +0x204 | `physGpcMask` | 4 | |
| +0x208 | `mmuPerGpc[0..63]` | 0x100 | |
| +0x308 | `tpcToPesMap[0..14]` | 0x3C | |
| +0x344 | `numPesPerGpc[0..63]` | 0x100 | |
| +0x444 | `zcullMask[0..63]` | 0x100 | |
| +0x544 | `physGfxGpcMask` | 4 | |
| +0x548 | `numGfxTpc` | 4 | |
| **0x54C** | **sizeof** | **1356** | |

`0x54C × 8 engines = 0x2A60 = 10,848` — **exactly the `reqSize` field of dispatch record 0x40614B8 and the value the handler builds into `a2` at 0x4BC6894.**

This is a three-way closed loop:
1. Dispatch table says payload = 0x2A60.
2. Header says `sizeof(params) = 0x54C × 8 = 0x2A60`.
3. Handler code computes `a2 = 0x3000 - 0x5A0 = 0x2A60` and computes `eng_base = params + eng*0x54C`.

### 3. All four writes to the output buffer (`s11`, x27)

`sw` stores with base register `x27` in the handler (exhaustive scan of 0x4BC682C–0x4BC7200):

| Address | Instruction | Raw bytes | Target | Field |
|---------|-------------|-----------|--------|-------|
| 0x04BC69B0 | `sw a5, 0x000(x27)` | `23 a0 fd 00` | `params[0]+0x000` | **`floorsweepingMasks[0].gpcMask`** |
| 0x04BC69B4 | `sw a5, 0x204(x27)` | `23 a2 fd 20` | `params[0]+0x204` | **`floorsweepingMasks[0].physGpcMask`** |
| 0x04BC69C8 | `sw a0, 0x544(x27)` | `23 a2 ad 54` | `params[0]+0x544` | **`floorsweepingMasks[0].physGfxGpcMask`** |
| 0x04BC69E0 | `sw a0, 0x548(x27)` | `23 a4 ad 54` | `params[0]+0x548` | **`floorsweepingMasks[0].numGfxTpc`** |

**Correction to my own earlier draft:** `[s11+0x204]` is **`physGpcMask`**, not `tpcMask[0]`. The two values written at 0x4BC69B0 and 0x4BC69B4 are the same register `a5`, so at engine 0 the GSP reports `gpcMask == physGpcMask` initially. This is consistent with a non-MIG configuration where logical and physical GPC numbering coincide.

### 4. The engine-base pointer `s3` — root of the per-engine writes

```
4bc6c6c: 93 07 c0 54   li   a5, 0x54c        ; engine stride
4bc6c70: b3 87 fc 02   mul  a5, a5, s6       ; a5 = 0x54C * engineIdx
4bc6c74: 03 36 84 e3   ld   a2, -0x1c8(s0)   ; a2 = params  (stashed at 4bc6944: sd s11,-0x1c8(s0))
4bc6c94: b3 09 f6 00   add  s3, a2, a5       ; s3 = &params[engineIdx]
```

Raw byte decode of `0x02FC87B3` at 0x4BC6C70:
- opcode `0x33`, funct3 `0`, funct7 `0x01` → **`MUL`**
- rd = 15 (`a5`), rs1 = 25 (`s6`), rs2 = 15 (`a5`)
- → `a5 = s6 * a5` = `engineIdx * 0x54C` ✓

`x19` (`s3`) is written **exactly once** in the range 0x4BC6C94–0x4BC6D58 (verified by scanning every instruction whose rd is x19). Therefore every `sw (...)(s3)` from 0x4BC6C94 onward targets `params[engineIdx]`.

### 5. Per-engine writes via `s3`

| Address | Instruction | Raw | Target (offset within engine) | Field |
|---------|-------------|-----|------------------------------|-------|
| 0x04BC6C98 | `sw zero, 0x000(s3)` | `23 a0 09 00` | +0x000 | **clear `gpcMask`** |
| 0x04BC6C9C | `sw zero, 0x204(s3)` | `23 a2 09 20` | +0x204 | **clear `physGpcMask`** |
| 0x04BC6D1C | `sw a5, 0x000(s3)` | `00 f9 a0 23` → `23 a0 f9 00` | +0x000 | **`gpcMask \|= (1 << gpcIdx)`** |
| 0x04BC6D50 | `sw a5, 0x204(s3)` | `23 a2 f9 20` | +0x204 | **`physGpcMask \|= (1 << ...)`** |

### 6. `tpcMask[]` — where is it actually written?

`tpcMask` lives at engine offset **+0x004**, i.e. `params + eng*0x54C + 0x004 + 4*tpcIdx`.

**No `sw` in the handler uses offset 0x004 or any offset in 0x004–0x0FC.** The exhaustive store scan found only `+0x000`, `+0x204`, `+0x444`-family, `+0x544`, `+0x548` on `s3`, plus stack/negative-offset stores.

The `tpcMask` array is therefore filled through a **pointer passed to a callee**, not by direct store. The two candidates are the slot-38 calls at 0x4BC6A28 and 0x4BC6D64, whose `a3` out-pointer is computed as:

```
; call #1 (0x4BC6A1C-0x4BC6A20)
addi a3, a3, 0x4
add  a3, s11, a3          ; = params + (a3 + 4)

; call #2 (0x4BC6D58-0x4BC6D5C)
addi s7, s4, 0x4          ; s4 = s3 = &params[eng]
mv   a3, s7               ; = params + eng*0x54C + 0x004
```

**Call #2's `a3 = params[eng] + 0x004` is precisely `&tpcMask[0]`.** That is the write path for `tpcMask`.

### 7. `zcullMask[]` at +0x444

Call #1's out-pointer lands at `params + 0x444 + 4*gpcIdx` = `&zcullMask[gpcIdx]`. Consistent with the header comment "zcullMask is always indexed by physical GPC ID" and with this call being inside the per-GPC loop.

### 8. Relationship to the live observed value `tpcMask[0] = 0x1F`

| Step | Source |
|------|--------|
| `gpcMask`/`physGpcMask` at engine 0 | Slot 37 (+0x128) out-param, stored at 0x4BC69B0 / 0x4BC69B4 |
| Per-engine `gpcMask` rebuild | 0x4BC6D1C, `1 << s10` where `s10` is the GPC index |
| `tpcMask[eng][gpc]` | filled by slot-38 (+0x130) call with `a3 = &params[eng]+0x004`, one dword per iteration |
| Bit source | `sllw a4, s1, a2` with `a2` = slot-64 (+0x200) out-param — **the TPC index** |

So `tpcMask[0] = 0x1F` means: the TPC-index enumerator returned exactly the indices 0,1,2,3,4 (five set bits) and not index 5, for physical GPC 0.

### 9. Nested correction of prior claims

| Prior claim | Correction | Basis |
|-------------|------------|-------|
| T6/T7: `sw [s3+0x204]` is an "internal bitmap, not proven to be output tpcMask" | **Half right, half wrong.** It *is* an output param — but it is `physGpcMask` (+0x204), **not** `tpcMask`. `tpcMask` starts at +0x004. | Header layout, §2 |
| T8 draft: `[s11+0x204]` = `tpcMask[0]` | **Wrong** — it is `physGpcMask`. | Same |
| T7: output struct offset 0x204 = tpcMask[0] | **Wrong** — the engine has 64 GPCs, so `tpcMask` is 256 bytes, pushing `physGpcMask` to +0x204. | `MAX_GPC=64`, not 3 |

The root error in T6/T7 was assuming `NV2080_CTRL_INTERNAL_GR_MAX_GPC` was small (3–8). It is **64**, which is why the offsets are far apart.

## Ghi chú PONYTAIL

# ponytail: Header says MAX_GPC=64 → sizeof(FLOORSWEEPING_MASKS)=0x54C exactly = engine stride = 0x2A60/8 = dispatch reqSize. Closed loop, three independent sources agree. Only 4 direct writes to output: +0x000 gpcMask, +0x204 physGpcMask, +0x544 physGfxGpcMask, +0x548 numGfxTpc. tpcMask[] at +0x004-0x0FC is written via the slot-38 out-pointer (params[eng]+4). Corrects T7 which thought +0x204 was tpcMask[0].

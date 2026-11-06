# T8_GPC0_TPC5_ORIGIN.md

## T8 Phase D — Origin of `tpcMask[0] = 0x1F`

**Artifact SHA-256:** `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85`
**Live observation:** GPC0 mask = `0x1F`, GPC1 = `0x3F`, GPC2 = `0x3F` → 17 TPCs / 34 SMs

### 1. Traced chain, from output value back to the last identified producer

```
HOST: nvidia-smi / kgrmgrGetLegacyTpcMask_IMPL
  └─ RM control 0x20800A26  (NV2080_CTRL_CMD_INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS)
     └─ GSP dispatch record  0x40614B8   (@vaddr, .rm_rodata, idx 192 of 1182)
        └─ GSP handler      0x4BC682C   (payload 0x2A60, section .rm_text)
           │
           ├─ [0x4BC6984] slot 37 (+0x128) ──► writes u32 to stack (s0-0x198)
           │     └─ [0x4BC69A0] loaded → stored to params[0]+0x000 (gpcMask)
           │                             → stored to params[0]+0x204 (physGpcMask)
           │
           └─ ENGINE LOOP  (engineIdx = s6, stride 0x54C)
              │  [0x4BC6C70] mul a5 = 0x54C * s6
              │  [0x4BC6C94] s3 = params + a5            ; &params[eng]
              │  [0x4BC6C98] sw zero,[s3+0x000]          ; gpcMask = 0
              │  [0x4BC6C9C] sw zero,[s3+0x204]          ; physGpcMask = 0
              │  [0x4BC6CA0] lw a2,[s11+0x1B8]           ; <<< INPUT INDEX from host params
              │  [0x4BC6CAC] bitmap_enumerate(s2, a2, out[63], &cnt)
              │  │      └─ reads  *(u32*)(s2 + 0x3E0 + a2*4)   <<< THE BITMAP WORD
              │  │      └─ writes ascending bit indices to out[] (stack, s0-0x178)
              │  │      └─ writes count to (s0-0x1A4)
              │  │
              │  └─ GPC LOOP  (gpcIdx = s10, s8 walks out[])
              │        [0x4BC6D0C] lw  a5,[s3+0x000]      ; gpcMask accumulator
              │        [0x4BC6D10] sllw a4, 1, s10        ; 1 << gpcIdx
              │        [0x4BC6D14] lw  a2,[s8]            ; tpcIdx from out[]
              │        [0x4BC6D1C] sw  a5,[s3+0x000]      ; gpcMask |= bit
              │        [0x4BC6D30] slot 64 (+0x200)       ; -> real tpcIdx at (s0-0x1A8)
              │        [0x4BC6D48] sllw a4,1,a2
              │        [0x4BC6D50] sw  a5,[s3+0x204]      ; physGpcMask |= bit
              │        [0x4BC6D64] slot 38 (+0x130)  a3 = &params[eng]+0x004  ; tpcMask write path
              │
              └─ [0x4BC69C8] sw a0,[s11+0x544]   ; physGfxGpcMask  (from slot call)
                 [0x4BC69E0] sw a0,[s11+0x548]   ; numGfxTpc       (from slot call)
```

### 2. The last identified producer object

**`s2 + 0x3E0 + idx*4`** — a 32-bit bitmap word inside the GSP per-GPU object at
`s2 = *(*(pGpu+0x160)+0xE8)+0x28F50`.

| Property | Value | Basis |
|----------|-------|-------|
| Address formula | `s2 + 0x3E0 + (*(u32*)(params+0x1B8))*4` | `0x4BC6C84` (a1=s2), `0x4BC6CA0` (a2=params+0x1B8), `0x4BC6C3C0`-class `lw a1,0x3e0(a2)` in callee |
| Content | bitmap of set bits → enumerated into index array | helper semantics, T8_A |
| Index source | **host-supplied** `params+0x1B8` | `lw a2, 0x1b8(s11)` at `0x4BC6CA0` |
| Where the word is written | **NOT FOUND in this handler** | exhaustive store scan of 0x4BC682C–0x4BC7200 |
| Where `params+0x1B8` is written | **NOT FOUND in this handler** | inputs, not outputs |

**This is the exact break.** Both inputs to the enumeration come from outside the handler:
- the bitmap word at `s2+0x3E0+4i` is pre-populated elsewhere,
- the index `i` is read from the incoming request payload at `+0x1B8`.

### 3. Physical vs logical / compacted — direct header evidence

The header resolves this precisely (ctrl2080internal.h:306–314):

```c
    /*!
     * tpcMask is indexed by logical GPC ID for MIG case
     * and indexed by physical GPC ID for non-MIG case
     */                                                                   /* 306-309 */
    NvU32 tpcMask[NV2080_CTRL_INTERNAL_GR_MAX_GPC];                       /* 310 */

    /*!
     * tpcCount is always indexed by logical GPC ID
     */                                                                   /* 312-314 */
    NvU32 tpcCount[NV2080_CTRL_INTERNAL_GR_MAX_GPC];                      /* 315 */
```

```c
    /*!
     * zcullMask is always indexed by physical GPC ID
     */                                                                   /* 322-324 */
```

| Array | Indexing |
|-------|----------|
| `tpcMask[]` | logical GPC ID under MIG, **physical GPC ID otherwise** |
| `tpcCount[]` | always logical GPC ID |
| `zcullMask[]` | always physical GPC ID |
| `physGpcMask` | by definition physical |
| `gpcMask` | unspecified in header; conventionally logical |

**CMP 40HX is not MIG-capable and does not run MIG.** Therefore, on this GPU, `tpcMask` is indexed by **physical GPC ID**. Bit 5 of `tpcMask[0]` therefore refers to physical TPC5 within physical GPC0 — **no compaction, no remap**. GPC0/TPC5 is a real physical location.

### 4. Why `tpcMask[0] = 0x1F` specifically — three distinguishable readings

The value `0x1F` means the TPC-index enumerator produced indices {0,1,2,3,4} and not 5. From the code, this can arise from **three distinct upstream conditions**, which the handler does not distinguish:

| # | Reading | What would be at `s2+0x3E0+4i` | Distinguished by |
|---|---------|-------------------------------|------------------|
| 1 | **Physical absence** — TPC5 not on the die | bitmap bit 5 = 0 | Fuse/wafer test data; not observable from GSP code |
| 2 | **Defective mask** — TPC5 present but marked bad | bitmap bit 5 = 0 | Same bitmap, different origin; needs fuse/OPT read |
| 3 | **Software floor-sweep** — TPC5 present and good but disabled by product config | bitmap bit 5 = 0 | Needs product-config source (VBIOS/strap/fuse OPT) |

**All three produce identical GSP behaviour.** The GSP handler receives one bitmap and enumerates whatever bits are set. It contains **no branch that could distinguish "absent" from "defective" from "swept"** — the enumeration loop at `0x4BC6D0C` has exactly one predicate (`bnez` on remaining bits).

This is why `tpcMask[0] = 0x1F` cannot be read as evidence of a broken TPC5, nor as evidence that it is recoverable.

### 5. Two-level structure that would distinguish them — and why it's not here

NVIDIA ships a *reconfiguration* mask separate from the *active* mask precisely so the host can tell these apart. The header exposes it as a distinct command; the driver handler `subdeviceCtrlCmdGpuGetTpcReconfigMask_IMPL` (`subdevice_ctrl_gpu_kernel.c:1903`) returned `NV_ERR_NOT_SUPPORTED (0x56)`.

**Per the user's constraint, 0x56 does not prove the mask does not exist.** What it does prove, in combination with this trace:

| Fact | Evidence |
|------|----------|
| The GSP handler for 0x20800A26 does not emit a reconfig mask | payload is exactly `sizeof(FLOORSWEEPING_MASKS)×8`, all 10 fields accounted for; no 11th array |
| The `zcullMask` at +0x444 is the only extra per-GPC array written | and it is zcull, per the header comment |
| Therefore a reconfig mask, if it exists, is served by a **different** GSP command | not by 0x20800A26 |

So: the active mask and any reconfig mask are **structurally independent** in the ABI. The active mask being 0x1F says nothing about the reconfig mask.

### 6. What is PROVEN, SUPPORTED, UNKNOWN

| Claim | Status | Basis |
|-------|--------|-------|
| The value the host sees as `tpcMask[0]` originates from a bitmap word at `s2+0x3E0+4i` in the GSP object | **PROVEN** | instruction chain §1, plus `lw a1,0x3e0(a2)` in callee |
| The bitmap is enumerated, not computed, by GSP at this control | **PROVEN** | helper writes only indices and count; return is always 0 |
| `tpcMask[]` on CMP is indexed by **physical** GPC ID | **PROVEN** | header 306–309 + non-MIG device |
| GPC0 bit 5 is physical TPC5, not a compacted index | **PROVEN** | same |
| GSP does not distinguish absent / defective / swept | **PROVEN** | no such branch exists in handler |
| The bitmap at `s2+0x3E0` is populated before this control runs | **PROVEN** | it is read, never written, in the handler |
| **Where** `s2+0x3E0` is populated | **UNKNOWN** | exhaustive store scan found no write in this handler |
| **Where** `params+0x1B8` (the index) comes from | **UNKNOWN** | it is input; the host-side caller sets it |
| Physical TPC5 is defective | **UNKNOWN** | bitmap bit clear is consistent with all three readings |
| Physical TPC5 is present on the die | **UNKNOWN** | not observable from GSP code or from mask value |
| A reconfig mask exists | **UNKNOWN** | 0x56 does not refute it; not in this payload either |

### 7. The next link to check (one concrete test)

**Object:** `s2 + 0x3E0` — 32-bit bitmap array in the GSP per-GPU object.

**Test (offline, read-only):**
1. Find every write to `0x3E0(reg)` in RM text (17 MB, `section_task_rm_elf_text_instance`). Pattern: opcode `0x23`, funct3 `2` (sw), imm12 `0x3E0`.
2. For each hit, walk back to the enclosing function entry and record its callers.
3. The setter's caller chain terminates in exactly one of: a fuse-read helper, a devinit table walk, or a constant baked into the GSP image.

If step 3 lands on **a `lui/addi`-materialised constant table**, TPC5's status is a **build-time product configuration** — recoverable in principle by product config, not by fence hardware change.
If step 3 lands on **a fuse/OPT read**, TPC5's status is **hardware-fused** — not recoverable.
If step 3 lands on a **devinit register read**, it is a **strapped/latched value** — possibly reconfigurable at init.

That single disambiguation is worth more than any further handler-level work, and it is bounded: one scan, one caller walk.

## Ghi chú PONYTAIL

# ponytail: tpcMask[0]=0x1F traces back to a bitmap word at s2+0x3E0+4i in the GSP per-GPU object, enumerated (not computed) by GSP. Header proves tpcMask is physical-GPC-indexed on non-MIG, so bit 5 IS physical TPC5 — no compaction. GSP has no branch distinguishing absent/defective/swept, so 0x1F proves none of the three. Next test: scan for writers of 0x3E0(reg) and walk callers — lands on constant table (config), fuse read (hard), or devinit (strap).

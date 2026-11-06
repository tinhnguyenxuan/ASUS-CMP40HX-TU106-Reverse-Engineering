# T8_VERDICT.md

## T8 FINAL VERDICT — Real TPC Mask Source

**Artifact:** `gsp_tu10x_615.78.08_inner.elf`
**SHA-256:** `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85`
**Tool:** `/usr/lib/llvm-18/bin/llvm-objdump -d --triple=riscv64`
**Header:** `open-gpu-kernel-modules` tag 615.78.08, `ctrl2080internal.h:292-344`

### 1. The complete proven chain

```
ACTIVE MASK SOURCE (single source of truth):
    u32 bitmap at  s2 + 0x3E0 + (idx * 4)
    where s2 = *(*(pGpu+0x160)+0xE8) + 0x28F50

READ path (what the host sees):
  [0x4BC6CAC] bitmap_enumerate(s2, idx, out[63], &cnt)
       └─ [0x4C853C0] lw a1, 0x3E0(a2)          <<< reads the bitmap word
       └─ writes ascending bit indices to out[] (stack)
  [0x4BC6D0C..0x4BC6D50] per-index loop ORs bits into params[eng]+0x000 / +0x204
  [0x4BC6D64] slot 38 (+0x130) a3 = &params[eng]+0x004   → tpcMask[] write path

WRITE path (who edits the bitmap):
  func 0x4C85220 ← called ONLY from 0x4CBF74C (inside func 0x4CBF424)
    [0x4C85268] lw  a5, 0x3E0(a2)                 ; read current word
    [0x4C85270] and a3, a3, a5                    ; a3 = ~(1<<tpcIdx) precomputed
    [0x4C85274] sw  a3, 0x3E0(a2)                 ; <<< WRITE BACK: clear bit
  func 0x4CBF424:
    [0x4CBF4B0] sw zero, -0x16c(s0)               ; cnt = 0
    [0x4CBF4B8] → 0x04C853B4 (bitmap_enumerate!)  ; fills TPC index list + cnt
    [0x4CBF4C4] lw s1, -0x16c(s0)                 ; s1 = cnt
    [0x4CBF4C8] bnez s1, ...                      ; if no indices → different path
    [0x4CBF74C] → 0x4C85220                       ; apply clears
```

**The bitmap at `s2+0x3E0` is the single source of truth.** It is read by the same enumerator helper from both the query path and the update path. Everything the host sees derives from it.

### 2. Direct answers to the T8 questions

#### A. Helper 0x04C853B4 — decoded

**`bitmap_enumerate(void *base, u32 idx, u32 *out /*63 slots*/, u32 *count) → always 0`**

- Reads `u32` at `base + 0x3E0 + idx*4`
- Writes **ascending bit indices** of set bits into `out[]`, max 63
- Writes the count to `*count`
- Constants `0x55555555 / 0x33333333 / 0x0F0F0F0F / 0x00FF00FF / 0x0000FFFF` with `seqz` + `slliw {4,3,2,1}` = **ctz ladder**, not popcount, not nth-set-bit
- **Return value is always 0.** The caller's `sext.w s10, a0; bnez s10` at `0x4BC6CB0/0x4BC6CB4` is an **error check on a constant**, not a value use
- **Not a mask producer.** It reads no hardware and computes no mask.

#### B. Indirect calls — resolved, with ABI correction

> User was right: `a0` is argument 0 and is a **different pointer** from `s2` (`a0 = *(s0-0x1b8)`, `a1 = s2`). This is a **callback-slot table**, not a method vtable. The label is dropped.

| Slot | Offset | Supplies | Proof |
|------|--------|----------|-------|
| 37 | +0x128 | the u32 written to `gpcMask` **and** `physGpcMask` at engine 0 | `lw a5,-0x198(s0)` @0x4BC69A0 → `sw` @0x4BC69B0, 0x4BC69B4 |
| 38 | +0x130 | per-GPC `zcullMask[]` and per-TPC `tpcMask[]` aux fill | `a3 = params+0x444+4g` / `a3 = params[eng]+0x004` |
| 64 | +0x200 | the **TPC bit index** | `lw a2,-0x1a8(s0)` @0x4BC6D3C → `sllw` @0x4BC6D48 |

**Slot 38 does not prepare the next iteration.** It is called at `0x4BC6D64`, *after* the mask store at `0x4BC6D50`, its return is only an error code, and the loop's own induction variables are `s10` (`addiw` @0x4BC6DC0) and `s8` (`addi` @0x4BC6DC4).

#### C. Output structure — verified against header, T7 corrected

`NV2080_CTRL_INTERNAL_GR_MAX_GPC = 64` (header line 292), **not 3 or 8**. Therefore:

| Offset | Field |
|--------|-------|
| +0x000 | `gpcMask` |
| +0x004 | `tpcMask[0..63]` (256 B) |
| +0x104 | `tpcCount[0..63]` |
| +0x204 | **`physGpcMask`** ← *T7 wrongly called this `tpcMask[0]`* |
| +0x208 | `mmuPerGpc[0..63]` |
| +0x308 | `tpcToPesMap[0..14]` |
| +0x344 | `numPesPerGpc[0..63]` |
| +0x444 | `zcullMask[0..63]` |
| +0x544 | `physGfxGpcMask` |
| +0x548 | `numGfxTpc` |
| **0x54C** | **sizeof** |

Closed loop, three independent sources:
- `sizeof = 0x54C` × 8 engines = **0x2A60**
- dispatch record `0x40614B8` `reqSize` = **0x2A60**
- handler builds `a2 = 0x3000 - 0x5A0` = **0x2A60** at `0x4BC6894`

Direct writes to the output buffer (`x27`/`s11`), exhaustive scan — **exactly four**:

| Site | Target | Field |
|------|--------|-------|
| 0x04BC69B0 | `params[0]+0x000` | `gpcMask` |
| 0x04BC69B4 | `params[0]+0x204` | `physGpcMask` |
| 0x04BC69C8 | `params[0]+0x544` | `physGfxGpcMask` |
| 0x04BC69E0 | `params[0]+0x548` | `numGfxTpc` |

`tpcMask[]` (at +0x004) is **never** written by a direct store — it is filled through the slot-38 out-pointer `params[eng]+0x004`.

#### D. Root cause — where the chain now ends

| Layer | Status | Evidence |
|-------|--------|----------|
| Active mask seen by host | **PROVEN** = enumeration of `s2+0x3E0+4i` | full chain §1 |
| Bitmap is sole source of truth | **PROVEN** | same helper `0x4C853B4` used by both query (`0x4BC6CAC`) and update (`0x4CBF4B8`) paths |
| Bitmap is **mutated** only by `0x4C85220` | **PROVEN** | 1 caller total (`0x4CBF74C`); the 8 other `sw 0x3E0` sites write unrelated objects (each writes a *family* of nearby offsets 0x3B4/0x3B8/0x3BC/0x3D0/0x3E0/0x3E4 = generic struct fields) |
| Bitmap is **initialised** from | **NOT FOUND** | no store to a *s2-relative* `0x3E0` anywhere; `0x4C85220` only *clears* existing bits |
| `params+0x1B8` (the index) source | **UNKNOWN** | it is an **input** to control 0x20800A26; set by the host RM side, not GSP |
| Physical TPC5 defective / absent / swept | **UNKNOWN** | GSP has **no branch distinguishing the three** |

### 3. The precise break, and why it is a real wall

**Break point:** nobody in the GSP image *creates* the bitmap bits. `0x4C85220` only **clears** them (`and` with a precomputed `~(1<<idx)`). A clear-only mutator operating on a bitmap implies the bitmap is **born with all presence bits set** and then progressively cleared.

Two candidate initialisations, and how to tell them apart:

| Candidate | Consequence | How to separate |
|-----------|-------------|-----------------|
| Static constant baked into the GSP ELF `.data`/`.rodata` | floor-sweep is a **build-time product configuration** — recoverable in principle | dump the object's static initialiser at `+0x3E0+4i` in `.section_task_rm_elf_data_instance` |
| Populated at GSP boot from a fuse/devinit register read | **hardware-fused or strapped** — not recoverable by config | find boot-time writers with a wider scan including `sd`/`memcpy` into the object base |

**The single most informative next test** (offline, read-only, bounded):
> Locate the GSP object's static initialiser in `.section_task_rm_elf_data_instance` (vaddr 0x4201000, file 0x201000, 0x387000 bytes) by searching for the object whose `+0x3E0` dword for TU106 reads `0x3F` (6 TPCs) or `0x1F`. If a static `0x3F` exists, the sweep is applied at runtime → **software-configurable**. If no static bitmap exists, it is **fuse/devinit-derived**.

### 4. What `tpcMask[0] = 0x1F` proves — strictly

| Proposition | Verdict | Why |
|-------------|---------|-----|
| Display/compute topology reports 17 TPCs / 34 SMs | **PROVEN** | live nvidia-smi + this chain |
| The reported values are an **enumeration** of a bitmap, not a computation | **PROVEN** | helper semantics |
| GPC0 bit 5 refers to **physical** TPC5 (no compaction) | **PROVEN** | header 306-309 + non-MIG device |
| The bitmap is the single point that decides all of it | **PROVEN** | one helper, two call paths |
| TPC5 is **defective** | **NOT PROVEN** | clear bit consistent with absent / defective / swept |
| TPC5 is **present on the die** | **NOT PROVEN** | not observable from GSP code |
| TPC5 is **recoverable** | **NOT PROVEN** | depends on the initialiser question in §3 |
| A **reconfig mask** exists separately | **UNDETERMINED** | `0x56` does not refute it; it is not in this payload (all 10 fields accounted for, no 11th array) |

### 5. Three branches used, three branches closed

| Branch | Outcome |
|--------|---------|
| A — decode helper `0x4C853B4` | **CLOSED.** Full byte-level decode; not a producer. |
| B — resolve indirect slots +0x128/+0x130/+0x200 | **CLOSED.** Slots 37/38/64 assigned roles; initialiser unfindable because slots are installed by a parameterised looping ctor (no `lui`-anchorable constant). |
| C — trace output struct writes | **CLOSED.** Header-exact layout; `sizeof=0x54C` triple-confirmed; exactly 4 direct writes; `tpcMask[]` via slot-38 pointer. |

Per the three-branch budget, work stops here. The remaining unknown (§3) has a named, bounded, offline test.

## Ghi chú PONYTAIL

# ponytail: Real source = u32 bitmap at s2+0x3E0+4i, enumerated by helper 0x4C853B4 (ctz ladder, returns 0 always). Same helper used by both query (0x4BC6CAC) and update (0x4CBF4B8) paths → single source of truth. Only 0x4C85220 writes it, and it only CLEARS bits. Break: nobody in GSP creates the bits. Sizeof=0x54C×8=0x2A60 triple-confirmed (header, dispatch record, handler code). Corrects T7: +0x204 is physGpcMask not tpcMask[0], because MAX_GPC=64.

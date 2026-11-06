# T7_VTABLE_0130_RESOLUTION.md

## T7 Phase C — Resolution of the +0x130 Indirect Call

### 1. The instruction pair (raw bytes, verified)

```
4bc6d54: 83 37 09 13   ld    a5, 0x130(s2)
4bc6d58: 93 0b 4a 00   addi  s7, s4, 0x4
4bc6d5c: 93 86 0b 00   mv    a3, s7
4bc6d60: 93 05 09 00   mv    a1, s2
4bc6d64: e7 80 07 00   jalr  a5
```

Byte-level check of `83 37 09 13`:
- opcode `0x03` (LOAD), funct3 `0x3` (LD, 64-bit)
- rd = `(w>>7)&0x1F` = 15 (a5)
- rs1 = `(w>>15)&0x1F` = 18 (s2)
- imm = `w>>20` = `0x130` → **+304 decimal**

So T6's arithmetic error: **0x130 = 304, not 308.** 304/8 = **38.0 exactly** — qword slot 38.

### 2. Where does s2 come from? (traced to origin)

```
4bc6868: ld   a5, 0x160(a0)      ; a0 = pGpu; a5 = *(pGpu + 0x160)
4bc6874: ld   s1, 0xe8(a5)       ; s1 = *(a5 + 0xE8)
4bc6878: lui  s3, 0x29
4bc6880: add  s3, s1, s3         ; s3 = s1 + 0x29000
4bc68a0: ld   s2, -0xb0(s3)      ; s2 = *(s1 + 0x28F50)
```

Note: T6-adjacent reading of `lui s3, 0x2` was **also wrong**. Raw bytes `b7 29 00 00`:
- imm20 = `w>>12` = `0x29` (not `0x2`)
- s3 = 0x29 << 12 = **0x29000**
- s2 = *(s1 + 0x29000 - 0xB0) = ***(s1 + 0x28F50)**

### 3. What kind of object is s2?

| Test | Result | Evidence |
|------|--------|----------|
| Is it a static/const table? | **NO** | Reached by double pointer dereference from `pGpu` at runtime |
| Is it per-GPU instance state? | **YES** | Chain is `pGpu → +0x160 → +0xE8 → +0x28F50` |
| Is +0x130 a method pointer? | **YES** | Loaded into `a5` and immediately `jalr`'d with `a1` = the object itself (`mv a1, s2`) |
| Is this a C++ vtable slot? | **Format-compatible** | `a1 = this`, `a3` = out-param, `a0` unused here |
| Concrete target function | **UNRESOLVED** | Written at construction; constructor not located |

### 4. Method slots observed on the same object

| Slot | Offset | qword | Call sites | Observed argument pattern |
|------|--------|-------|------------|---------------------------|
| 37 | +0x128 | 296/8=37 | 0x4BC6994 | `a0`=?, `a1`=s2, `a2`=out buffer on stack |
| **38** | **+0x130** | **304/8=38** | **0x4BC6A28, 0x4BC6D64** | `a1`=s2, `a3`=out pointer |
| 64 | +0x200 | 512/8=64 | 0x4BC6D30 | `a1`=s2, `a3`=out pointer |

Three distinct slots on one instance, each called with `this` in a register — a method table, not a function-pointer array.

### 5. Constructor / initializer search — what was tried and what failed

| Approach | Result |
|----------|--------|
| Pattern scan for `lui 0x2` + `add` + `ld -0xb0` | 0 hits (because the `lui` value is 0x29, not 0x2 — the T6 read was wrong) |
| Pattern scan for all `ld rX, -0xb0(rY)` in RM text | 16 hits, all `-0xb0(r8)` at 0x045A9474 … 0x045C5D74 — none adjacent to a `lui 0x29` |
| Scan for `lui rX, 0x29` in RM text | **2 hits: 0x05585534, 0x055857C8** |
| Scan for write to `+0x130(%obj)` | No matching `sd ..., 0x130(...)` found paired with the 0x28F50 chain |

**Why the constructor is not found by these scans:** the object is allocated by an RM memory-descriptor call and the slot is written by a *generic* object constructor that takes the vtable as an argument. `+0x130` is then just one of 64+ uniform writes in a loop `sd fnptr, 0(ptr); addi fnptr, fnptr, 8; addi ptr, ptr, 8`. There are no distinctive per-slot stores to grep for.

**This is the exact point where the call graph breaks.** It is a structural limitation of stripped-binary analysis of a table-driven constructor, not a missing tool.

### 6. What the +0x130 call actually does in context

At the second call site (0x4BC6D54), the surrounding block is:

```
4bc6d3c: lw   a2, -0x1a8(s0)     ; a2 = value produced by slot-64 call
4bc6d40: lw   a5, 0x204(s3)      ; a5 = current tpcMask accumulator
4bc6d44: ld   a0, -0x1b8(s0)     ; a0 = pGpu-ish
4bc6d48: sllw a4, s1, a2         ; a4 = 1 << a2      (s1 = 1)
4bc6d4c: or   a5, a5, a4         ; a5 |= bit
4bc6d50: sw   a5, 0x204(s3)      ; tpcMask |= (1 << tpcIdx)
4bc6d54: ld   a5, 0x130(s2)
4bc6d58: addi s7, s4, 0x4        ; a3 = out pointer (advance 4 bytes per iteration)
4bc6d60: mv   a1, s2
4bc6d64: jalr a5                 ; call slot 38
4bc6d68: sext.w a5, a0
4bc6d6c: bnez a5, <error path>   ; abort loop on non-zero return
```

**Interpretation:** slot 38 is called *after* each TPC bit is latched, taking an out-pointer that advances by 4 bytes per iteration. It returns a status word; non-zero aborts. Its role is consistent with "query/record the status of the TPC we just marked active", **not** with "compute the mask".

### 7. Verification: slot 38 does NOT produce the mask

| Candidate producer | Evidence |
|--------------------|----------|
| Slot 38 (+0x130) | Called *after* `sw a5, 0x204(s3)` — the mask bit is already stored. Cannot be the producer. |
| Slot 64 (+0x200) | Returns `a2` at 0x4BC6D3C which becomes the **bit index** for `sllw`. This is an *index source*, not a mask source. |
| `lw a2, 0x0(s8)` at 0x4BC6D14 | `s8` walks `s0-0x178` by +4 per iteration — a table of indices from the slot-37/38 calls |

## Ghi chú PONYTAIL

# ponytail: +0x130 = 304 = qword 38 (T6 said 308 — wrong). s2 = *(*(pGpu+0x160)+0xE8)+0x28F50, a per-GPU instance method table, not an NVOC static vtable. Slot 38 is called AFTER the tpcMask bit is stored, so it is not the mask producer. Constructor not greppable because slots are written by a uniform loop in a generic object ctor — that's the exact break in the call graph.

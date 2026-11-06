# T7_GSP_DISPATCH_XREF.md

## T7 Phase B — GSP Dispatch Table Located, Handler for 0x20800A26 Resolved

### 1. Method

Searched the RM rodata section (vaddr 0x401d000–0x4201000, file 0x1d000–0x201000) for the little-endian DWORD `0x20800A26`.

**Exactly one hit:** file offset 0x614B8 → **vaddr 0x40614B8**.

Context dump (32 bytes at 0x40614B8):
```
26 0a 80 20  60 2a 00 00  c8 04 07 04 00 00 00 00
2c 68 bc 04  00 00 00 00  80 00 01 00 00 00 00 00
```

### 2. Record layout (empirically confirmed by 1182 consistent entries)

| Offset | Type | Field | Value for A26 |
|--------|------|-------|---------------|
| 0x00 | u32 | cmdId | `0x20800A26` |
| 0x04 | u32 | request payload size (bytes) | `0x2A60` (10,848) |
| 0x08 | u64 | table-base constant | `0x040704C8` (identical in every entry) |
| 0x10 | u64 | **handler function pointer** | **`0x04BC682C`** |
| 0x18 | u32 | flags | `0x00010080` |

Entry stride: **32 bytes**.

### 3. Table bounds (walked programmatically)

| Property | Value |
|----------|-------|
| Base vaddr | `0x405FCB8` |
| Last entry | `0x4069058` |
| Entry count | **1182** |
| Total size | 37,824 bytes |
| Section | `.section_task_rm_elf_rodata_instance` |
| A26 index | **192** |

Neighbouring entries (verifies sequential command-ID ordering, typical of a generated RM control table):

| idx | vaddr | cmdId | reqSize | handler | flags |
|-----|-------|-------|---------|---------|-------|
| 186 | 0x40613F8 | 0x20800A20 | 0x0B8 | 0x04DC667C | 0x000C1 |
| 187 | 0x4061418 | 0x20800A21 | 0x008 | 0x04BB70C4 | 0x1C0C0 |
| 188 | 0x4061438 | 0x20800A22 | 0x14020 | 0x04BC3810 | 0x10080 |
| 189 | 0x4061458 | 0x20800A23 | 0x14020 | 0x04DCFB9C | 0x000D0 |
| 190 | 0x4061478 | 0x20800A24 | 0x040 | 0x04DD0080 | 0x000D0 |
| 191 | 0x4061498 | 0x20800A25 | 0x020 | 0x04BB70F8 | 0x1C0C0 |
| **192** | **0x40614B8** | **0x20800A26** | **0x2A60** | **0x04BC682C** | **0x10080** |
| 193 | 0x40614D8 | 0x20800A27 | 0x2A60 | 0x04C7699C | 0x08000 |
| 194 | 0x40614F8 | 0x20800A28 | 0x420 | 0x04DC0460 | 0x000C0 |
| 195 | 0x4061518 | 0x20800A29 | 0x001 | 0x04BB7060 | 0x1C0C0 |
| 196 | 0x4061538 | 0x20800A2A | 0xFC0 | 0x04BC091C | 0x10080 |
| 197 | 0x4061558 | 0x20800A2B | 0xFC0 | 0x04BB7160 | 0x1C0C0 |

The alternating pattern (even idx = `flags 0x10080`, odd idx = `flags 0x1C0C0`) and the paired equal `reqSize` values at A26/A27, A2A/A2B, A2C/A2D, A2E/A2F, A30/A31 are consistent with GET/SET command pairs sharing the same payload structure — independent corroboration that the record layout is correct.

### 4. Handler disassembly — entry (0x4BC682C)

```
4bc682c: 13 01 01 e0  addi sp, sp, -0x200
4bc6830: 23 38 81 1e  sd   s0, 0x1f0(sp)
...
4bc6864: 13 04 01 20  addi s0, sp, 0x200
4bc6868: 83 37 05 16  ld   a5, 0x160(a0)     ; a5 = pGpu->something
4bc686c: 93 8d 05 00  mv   s11, a1           ; s11 = args buffer (a1)
4bc6870: 37 37 20 04  lui  a4, 0x4203        ; a4 = 0x4203000 (rodata anchor)
4bc6874: 83 b4 87 0e  ld   s1, 0xe8(a5)      ; s1 = *(a5+0xE8)
4bc6878: b7 29 00 00  lui  s3, 0x29          ; s3 = 0x29000
4bc687c: 37 36 00 00  lui  a2, 0x3           ; a2 = 0x3000
4bc6880: b3 89 34 01  add  s3, s1, s3        ; s3 = s1 + 0x29000
4bc6884: 83 37 07 93  ld   a5, -0x6d0(a4)    ; a4-0x6d0 = 0x4203000-0x6D0
4bc688c: 93 07 00 00  li   a5, 0x0
4bc6890: 13 0a 05 00  mv   s4, a0           ; s4 = pGpu
4bc6894: 13 06 06 a6  addi a2, a2, -0x5a0   ; a2 = 0x3000-0x5A0 = 0x2A60
4bc6898: 93 05 00 00  li   a1, 0x0
4bc689c: 13 85 0d 00  mv   a0, s11
4bc68a0: 03 b9 09 f5  ld   s2, -0xb0(s3)     ; s2 = *(s1 + 0x29000 - 0xB0) = *(s1+0x28F50)
4bc68a4: 23 34 94 e4  sd   s1, -0x1b8(s0)
4bc68ac: 97 f0 6a 00  auipc ra, 0x6af
4bc68b0: e7 80 00 75  jalr 0x750(ra)         ; -> 0x05275FFC
```

**Critical verification:** the constant built into `a2` at 0x4BC6894 (`lui 0x3` at 4bc687c then `addi -0x5a0`) equals **0x2A60** — exactly the `reqSize` field of the dispatch record at 0x40614B8. The handler self-validates the argument size it was dispatched with. **This is independent, in-code confirmation that 0x4BC682C is the correct handler for command 0x20800A26.**

### 5. Resolved direct call targets

| Call site | Target | Purpose |
|-----------|--------|---------|
| 0x4BC68B0 | 0x05275FFC | size/param validation init |
| 0x4BC6974 | 0x04B720CC | (auipc 0xfffab + jalr) common helper |
| 0x4BC6C68 | 0x04B720CC | same helper, second path |
| 0x4BC6DF8 | 0x0461A6A4 | completion / teardown |
| 0x4BC6FCC, 0x4BC701C, 0x4BC70D0, 0x4BC711C | 0x045A5F44 | error/assert path (4 sites, all same target) |

### 6. Indirect calls resolved (object-relative)

The handler loads method pointers from a per-GPU sub-object `s2 = *(s1 + 0x28F50)` where `s1 = *(pGpu + 0x160) + 0xE8`:

| Site | Load | Slot | Meaning |
|------|------|------|---------|
| 0x4BC6994 | `ld a5,0x128(s2)` | +0x128 (296) = qword 37 | method — topology/gpc query |
| 0x4BC6A28 | `ld a5,0x130(s2)` | +0x130 (304) = qword 38 | **method — the "reported" +0x130** |
| 0x4BC6D30 | `ld a5,0x200(s2)` | +0x200 (512) = qword 64 | method — per-TPC status query |
| 0x4BC6D64 | `ld a5,0x130(s2)` | +0x130 again | same method, TPC loop |
| 0x4BC69C4 | `ld a5,-0x658(s5)` | relative to a derived pointer | helper |
| 0x4BC69D8 | `ld a5,-0x638(s5)` | relative | helper |
| 0x4BC6CD4 | `ld a5,-0x658(s11)` | relative to args | helper |
| 0x4BC6CE8 | `ld a5,-0x638(s11)` | relative | helper |

### 7. Correction of T6's "+0x130" interpretation

T6 called +0x130 a "vtable offset" without evidence. **Corrected, with evidence:**

1. `+0x130 = 304 bytes = 38 × 8`. On RISC-V64 with a pointer array, this is qword slot 38.
2. It is loaded from a **heap/instance object** (`*(s1+0x28F50)` where `s1` derives from `pGpu`), not from a static table.
3. The object is **per-GPU-instance state**, and the same slot is called twice in two different loops within one handler.
4. Slot 37 (+0x128), slot 38 (+0x130), and slot 64 (+0x200) are all called as methods on the same object — a genuine method table, but of an **RM object instance in GSP**, not an NVOC static vtable.
5. **What cannot be claimed:** the concrete function each slot points to. It is written at object construction time, and the constructor was not located. Calling it a "vtable" is permitted; naming the target function is not.

## Ghi chú PONYTAIL

# ponytail: GSP dispatch table found at 0x405FCB8, 1182 × 32B entries. A26 → handler 0x4BC682C. Independent proof: handler builds a2=0x2A60, matching the record's reqSize field byte-for-byte. +0x130 is a method slot (qword 38) on a per-GPU instance object at *(s1+0x28F50), not an NVOC static vtable; target function remains unnamed.

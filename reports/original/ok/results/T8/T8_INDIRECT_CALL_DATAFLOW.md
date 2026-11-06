# T8_INDIRECT_CALL_DATAFLOW.md

## T8 Phase B — Indirect Call Dataflow (slots +0x128, +0x130, +0x200)

**Artifact SHA-256:** `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85`
**Handler:** `0x04BC682C` (control `0x20800A26`, payload `0x2A60`)

### 1. Object chain (verified instruction by instruction)

```
4bc6868: 83 37 05 16   ld   a5, 0x160(a0)      ; a0 = pGpu (control dispatch ctx)
4bc6874: 83 b4 87 0e   ld   s1, 0xe8(a5)       ; s1 = *(pGpu+0x160)+0xE8
4bc6878: b7 29 00 00   lui  s3, 0x29           ; 0x29<<12 = 0x29000
4bc6880: b3 89 34 01   add  s3, s1, s3         ; s3 = s1 + 0x29000
4bc68a0: 03 b9 09 f5   ld   s2, -0xb0(s3)      ; s2 = *(s1 + 0x28F50)
```

**`s2` is a pointer field inside a per-GPU sub-object.** Not a static table, not a const.

### 2. ABI correction (per user instruction)

> "Không suy ra C++ vtable chỉ vì a1=s2; trong ABI RISC-V, a0 mới là thanh ghi đối số đầu tiên."

Verified: `a0` is indeed argument 0. At every indirect site, `a0` is set from `-0x1b8(s0)` — a **different** pointer from `s2`:

```
4bc6988: 13 85 04 00   mv   a0, s1        ; a0 = *(s0-0x1b8)  [loaded at 4bc6968/4bc68a4]
4bc6990: 93 05 09 00   mv   a1, s2        ; a1 = s2  (arg 1)
```

So the call shape is `fn(a0, s2, out)`. `s2` is **argument 1**, not `this`. Therefore:

- If this were a C++/C++-like method table, `a0` would be `this`.
- Here `a0` is a *different* object (`*(s0-0x1b8)`).
- **The correct reading is a function-pointer table taking `(ctx, topologyObj, out)` — a callable-slot table, not a method vtable.**

`+0x130` remains a valid slot index (qword 38), but the "vtable" label is dropped. It is a **dispatch/callback slot table** on the per-GPU object.

### 3. All indirect sites in the handler

| Site | Load | Args (a0, a1, a2/a3) | Out destination | Return used as |
|------|------|----------------------|-----------------|----------------|
| `0x4BC6994` | `ld a5, 0x128(s2)` | `a0=*(s0-0x1b8)`, `a1=s2`, `a2=s0-0x198` | stack u32 | `sext.w s1` → `bnez` → **error branch 0x4BC71AC** |
| `0x4BC6A28` | `ld a5, 0x130(s2)` | `a0=*(s0-0x1b8)`, `a1=s2`, `a3=s11+a3+4` | **`params` buffer** | `sext.w s1` → `bnez` → **error branch 0x4BC6BB4** |
| `0x4BC6D30` | `ld a5, 0x200(s2)` | `a0=*(s0-0x1b8)`, `a1=s2`, `a3=s0-0x1a8` | stack u32 | `sext.w a5` → `bnez` → **error branch 0x4BC6FEC** |
| `0x4BC6D64` | `ld a5, 0x130(s2)` | `a0=*(s0-0x1b8)`, `a1=s2`, `a3=s7=s4+4` | **`params` buffer** | `sext.w a5` → `bnez` → **error branch 0x4BC7054** |

**All four sites use the return value only as an error code.** None of them assign the return into a mask.

### 4. Which slot supplies what

#### Slot `+0x128` (296 = qword 37) — supplies the gpcMask value

```
4bc6984: ld   a5, 0x128(s2)
4bc6988: mv   a0, s1
4bc698c: addi a2, s0, -0x198     ; out ptr: stack u32
4bc6990: mv   a1, s2
4bc6994: jalr a5
4bc6998: sext.w s1, a0           ; status
4bc699c: bnez s1, <error>        ; abort on non-zero
4bc69a0: lw   a5, -0x198(s0)     ; <<<< VALUE PRODUCED BY SLOT 37
4bc69b0: sw   a5, 0x0(s11)       ; params[0].gpcMask = value
4bc69b4: sw   a5, 0x204(s11)     ; params[0].tpcMask[0] = SAME value
```

**Slot 37 (+0x128) is the producer of the word written to both `gpcMask` and `tpcMask[0]` at engine 0.** This is the strongest producer candidate found.

#### Slot `+0x130` (304 = qword 38) — supplies per-GPC TPC counts, called twice

Call #1 (`0x4BC6A28`), inside a per-GPC loop:

```
4bc6a18: ld   a5, 0x130(s2)
4bc6a1c: addi a3, a3, 0x4
4bc6a20: add  a3, s11, a3        ; a3 = params + a3 + 4  -> tpcCount[] region
4bc6a24: mv   a1, s2
4bc6a28: jalr a5
```

The out-pointer advances by 4 per GPC iteration through `params`, landing in the `+0x444 + 4*gpc` window.

Call #2 (`0x4BC6D64`), inside the per-TPC loop:

```
4bc6d54: ld   a5, 0x130(s2)
4bc6d58: addi s7, s4, 0x4        ; s4 = s3 = engine base
4bc6d5c: mv   a3, s7             ; a3 = engine_base + 4
4bc6d64: jalr a5
```

Out goes to `engine_base + 4` = `params[eng].gpcMask + 4` = **`params[eng].tpcMask[0...]` window**.

**Both +0x130 calls are per-iteration status/aux fills. Neither computes the bit that gets OR'd.**

#### Slot `+0x200` (512 = qword 64) — supplies the TPC bit index

```
4bc6d20: ld   a5, 0x200(s2)
4bc6d24: ld   a0, -0x1b8(s0)
4bc6d28: addi a3, s0, -0x1a8
4bc6d2c: mv   a1, s2
4bc6d30: jalr a5
4bc6d34: sext.w a5, a0
4bc6d38: bnez a5, <error>
4bc6d3c: lw   a2, -0x1a8(s0)     ; <<<< VALUE PRODUCED BY SLOT 64 = TPC index
4bc6d48: sllw a4, s1, a2         ; a4 = 1 << tpcIdx
4bc6d4c: or   a5, a5, a4
4bc6d50: sw   a5, 0x204(s3)      ; params[eng].tpcMask[0] |= (1 << tpcIdx)
```

**Slot 64 is the TPC-index source.** It produces an *index*, not a mask.

### 5. Loop structure (CFG)

```
                    +---------------------------+
                    |  0x4BC6984  slot37 call   |  gpcMask value -> *(s0-0x198)
                    +-------------+-------------+
                                  |
                    +-------------v-------------+
                    | 0x4BC69B0 sw [s11+0x000] |  gpcMask = val
                    | 0x4BC69B4 sw [s11+0x204] |  tpcMask[0] = val
                    +-------------+-------------+
                                  |
              +-------------------v--------------------+
              |  OUTER LOOP over engines (idx in a2)   |
              |  0x4BC6C6C  li a5, 0x54C               |
              |  0x4BC6C70  mul a5 = a5 * s6           |
              |  0x4BC6C74  ld a2, -0x1c8(s0)          |  a2 = params
              |  0x4BC6C94  add s3, a2, a5             |  s3 = &params[eng]
              |  0x4BC6C98  sw zero, 0x0(s3)           |  gpcMask = 0
              |  0x4BC6C9C  sw zero, 0x204(s3)         |  tpcMask[0] = 0
              |  0x4BC6CA0  lw a2, 0x1b8(s11)          |  bitmap index in
              |  0x4BC6CAC  bitmap_enumerate(...)      |  -> out[] at s0-0x178
              |  0x4BC6CB8  lw s6, -0x1a4(s0)          |  count
              +-------------------+--------------------+
                                  |
              +-------------------v--------------------+
              |  INNER LOOP over TPCs (s8 walks out[])  |
              |  0x4BC6D0C  lw a5, 0x0(s3)             |  gpcMask (acc)
              |  0x4BC6D10  sllw a4, s1, s10           |  1<<gpcIdx (s1=1)
              |  0x4BC6D14  lw a2, 0x0(s8)             |  tpcIdx from out[]
              |  0x4BC6D1C  sw a5, 0x0(s3)             |  gpcMask |= bit
              |  0x4BC6D30  slot64 call                |  -> *(s0-0x1a8)
              |  0x4BC6D3C  lw a2, -0x1a8(s0)          |  real tpcIdx
              |  0x4BC6D50  sw a5, 0x204(s3)           |  tpcMask |= 1<<idx
              |  0x4BC6D64  slot38 call (a3=s3+4)      |  aux fill
              |  0x4BC6DD0  j 0x4BC6D0C                |  loop back
              +----------------------------------------+
```

### 6. Does +0x130 prepare the next iteration?

**No.** Evidence:

```
4bc6d50: sw   a5, 0x204(s3)      ; mask bit stored
4bc6d54: ld   a5, 0x130(s2)      ; slot loaded AFTER the store
4bc6d64: jalr a5                 ; called after
4bc6d6c: bnez a5, <error>        ; only on error does it break out
4bc6dc0: addiw s10, s10, 0x1     ; next GPC index
4bc6dd0: j    0x4BC6D0C          ; loop
```

Nothing written by the slot-38 call is read back before the loop head. The loop's own induction variables are `s10` (`addiw` at 0x4BC6DC0) and `s8` (`addi s8,s8,0x4` at 0x4BC6DC4). **Slot 38 is a terminal side-effect, not a loop-carried value.**

### 7. Where the object `s2` and its slots are initialized — xref search results

| Search performed | Result |
|------------------|--------|
| `lui rX,0x29` in RM text | **2 sites only:** `0x05585534`, `0x055857C8` |
| `ld rX,-0xb0(rY)` in RM text | 16 sites, all `-0xb0(r8)` at `0x045A9474`–`0x045C5D74` — **none** preceded by `lui 0x29` |
| `sd ..., 0x130(reg)` store scan | No store to offset `0x130` paired with the 0x28F50 chain |
| Callers of helper `0x4C853B4` | 15 sites (listed in A) |

**Why the initializer is not findable by instruction-pattern xref:** a slot table of uniform 8-byte function pointers is populated by a generic constructor looping `sd fnptr,0(p); addi fnptr,fnptr,8; addi p,p,8`. Every slot write looks identical; only the *incoming function-array pointer* differs, and that pointer arrives as a function argument, so there is no `lui`-addressable constant to anchor a search on.

**This is the precise break in the call graph.** State it as: *the slot values are installed by a parameterised constructor; identifying which constructor requires resolving the array of handler function addresses, which itself requires a sweep of every `auipc+addi` pair that materialises `0x4588000`-relative addresses — feasible but out of budget for the three-branch limit.*

### 8. What is PROVEN vs not

| Claim | Status | Evidence |
|-------|--------|----------|
| s2 = `*(*(pGpu+0x160)+0xE8)+0x28F50` | **PROVEN** | 4 instruction chain, raw bytes shown |
| `+0x130` = 304 = qword 38 | **PROVEN** | `0x130` imm field decoded from `0x8313_3783`-class word |
| Slot 37 (+0x128) produces the value written to gpcMask **and** tpcMask[0] | **PROVEN** | `lw a5,-0x198(s0)` at 0x4BC69A0 follows the slot-37 call and feeds both `sw` at 0x4BC69B0/0x4BC69B4 |
| Slot 64 (+0x200) produces the TPC bit index | **PROVEN** | `lw a2,-0x1a8(s0)` at 0x4BC6D3C feeds `sllw` at 0x4BC6D48 |
| Slot 38 (+0x130) is not the mask producer | **PROVEN** | Called after the store; return used only as error code; out-ptr targets tpcCount/tpcMask side windows |
| It is a C++ vtable | **NOT CLAIMED** | a0 ≠ s2; a0 is a distinct ctx pointer, s2 is arg 1 |
| The concrete function behind each slot | **UNRESOLVED** | Parameterised constructor; break documented in §7 |

## Ghi chú PONYTAIL

# ponytail: ABI corrected — a0 is arg0 and is a different pointer than s2, so this is a callback-slot table, not a method vtable. Slot 37 supplies the word written to BOTH gpcMask and tpcMask[0]. Slot 64 supplies the TPC index. Slot 38 is called AFTER the mask store and its return is only an error code — provably not a loop-carried producer. Initializer unfindable because slots are installed by a generic looping ctor with the address array as an argument.

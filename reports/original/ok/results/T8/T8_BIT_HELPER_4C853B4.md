# T8_BIT_HELPER_4C853B4.md

## T8 Phase A — Full Decode of Helper 0x04C853B4

**Artifact:** `gsp_tu10x_615.78.08_inner.elf`
**SHA-256:** `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85`
**Section:** `.section_task_rm_elf_text_instance` (vaddr 0x4588000, file 0x588000)
**Tool:** `/usr/lib/llvm-18/bin/llvm-objdump -d --triple=riscv64`

### 1. Function boundaries

| Property | Value |
|----------|-------|
| Entry | `0x04C853B4` |
| Last instruction (ret) | `0x04C854C4` |
| Size | 0x110 = 272 bytes |
| Next function starts | `0x04C854C8` (confirmed distinct: 2 callers, different prologue) |
| Callers | **15** (0x04B17200, 0x04BC58F8, 0x04BC5C48, 0x04BC6CAC, 0x04BCA744, 0x04BE9220, 0x04C62478, 0x04C96E1C, 0x04CBF4B8, 0x04CC6964, …) |

### 2. Complete disassembly (entry → all returns)

```
4c853b4: 93 17 06 02   slli  a5, a2, 0x20
4c853b8: 13 d6 e7 01   srli  a2, a5, 0x1e        ; a2 = (u32)a2 * 4
4c853bc: 33 06 b6 00   add   a2, a2, a1           ; a2 = a1 + idx*4
4c853c0: 83 25 06 3e   lw    a1, 0x3e0(a2)        ; a1 = *(u32*)(a1 + idx*4 + 0x3E0)
4c853c4: 23 20 07 00   sw    zero, 0x0(a4)        ; *a4 = 0
4c853c8: 63 8c 05 0e   beqz  a1, 0x4c854c0       ; if word==0 -> return 0
--- prologue ---
4c853cc: 13 01 01 fe   addi  sp, sp, -0x20
4c853d0: 23 3c 81 00   sd    s0, 0x18(sp)
4c853d4: 23 38 91 00   sd    s1, 0x10(sp)
4c853d8: 23 34 21 01   sd    s2, 0x8(sp)
4c853dc: 13 04 01 02   addi  s0, sp, 0x20
--- constants ---
4c853e0: b7 5e 55 55   lui   t4, 0x55555
4c853e4: 37 0e 01 00   lui   t3, 0x10
4c853e8: 37 03 ff 00   lui   t1, 0xff0
4c853ec: b7 18 0f 0f   lui   a7, 0xf0f1
4c853f0: 37 38 33 33   lui   a6, 0x33333
4c853f4: 13 85 06 00   mv    a0, a3           ; a0 = a3 (out ptr)
4c853f8: 93 8f c6 0f   addi  t6, a3, 0xfc   ; t6 = a3 + 252  (loop bound)
4c853fc: 93 02 00 00   li    t0, 0x0          ; t0 = 0  (slot counter)
4c85400: 93 8e 5e 55   addi  t4, t4, 0x555  ; t4 = 0x55555555
4c85404: 13 0e fe ff   addi  t3, t3, -0x1   ; t3 = 0xFFFF
4c85408: 13 03 f3 0f   addi  t1, t1, 0xff   ; t1 = 0xFF00FF
4c8540c: 93 88 f8 f0   addi  a7, a7, -0xf1  ; a7 = 0x0F0F0F0F
4c85410: 13 08 38 33   addi  a6, a6, 0x333  ; a6 = 0x33333333
4c85414: 13 0f 10 00   li    t5, 0x1          ; t5 = 1
--- loop body: isolate lowest set bit, compute its index ---
4c85418: bb 07 b0 40   negw  a5, a1
4c8541c: b3 f7 f5 00   and   a5, a1, a5       ; a5 = a1 & -a1  (isolate lowest set bit)
4c85420: 9b 87 07 00   sext.w a5, a5
4c85424: 33 f6 d7 01   and   a2, a5, t4       ; a2 = bit & 0x55555555
4c85428: 33 f9 c7 01   and   s2, a5, t3       ; s2 = bit & 0x0000FFFF
4c8542c: 93 b3 17 00   seqz  t2, a5
4c85430: b3 f4 67 00   and   s1, a5, t1       ; s1 = bit & 0x00FF00FF
4c85434: 13 36 16 00   seqz  a2, a2
4c85438: 13 39 19 00   seqz  s2, s2
4c8543c: 3b 06 76 00   addw  a2, a2, t2
4c85440: 1b 19 49 00   slliw s2, s2, 0x4
4c85444: b3 f3 17 01   and   t2, a5, a7       ; t2 = bit & 0x0F0F0F0F
4c85448: 93 b4 14 00   seqz  s1, s1
4c8544c: 3b 06 26 01   addw  a2, a2, s2
4c85450: 9b 94 34 00   slliw s1, s1, 0x3
4c85454: 93 b3 13 00   seqz  t2, t2
4c85458: b3 f7 07 01   and   a5, a5, a6       ; a5 = bit & 0x33333333
4c8545c: 3b 06 96 00   addw  a2, a2, s1
4c85460: 9b 93 23 00   slliw t2, t2, 0x2
4c85464: 93 b7 17 00   seqz  a5, a5
4c85468: 3b 06 76 00   addw  a2, a2, t2
4c8546c: 9b 97 17 00   slliw a5, a5, 0x1
4c85470: bb 07 f6 00   addw  a5, a2, a5      ; a5 = bit index (0..31)
4c85474: 3b 16 ff 00   sllw  a2, t5, a5      ; a2 = 1 << index
4c85478: 9b 82 12 00   addiw t0, t0, 0x1
4c8547c: 13 46 f6 ff   not   a2, a2
4c85480: 33 f6 c5 00   and   a2, a1, a2      ; a2 = a1 & ~(1<<idx)  (clear that bit)
4c85484: 23 20 57 00   sw    t0, 0x0(a4)      ; *a4 = slot counter (1,2,3,...)
4c85488: 9b 05 06 00   sext.w a1, a2
4c8548c: 63 84 06 00   beqz  a3, 0x4c85494
4c85490: 23 20 f5 00   sw    a5, 0x0(a0)      ; *out = bit index
4c85494: 63 0a f5 01   beq   a0, t6, 0x4c854a8   ; if out ptr reached a3+0xFC -> done
4c85498: 13 05 45 00   addi  a0, a0, 0x4
4c8549c: 63 86 05 00   beqz  a1, 0x4c854a8     ; if no bits left -> done
4c854a0: 83 22 07 00   lw    t0, 0x0(a4)
4c854a4: 6f f0 5f f7   j     0x4c85418
4c854a8: lds/ret -> a0 = 0
4c854c0: li a0, 0 ; ret       ; early exit when word==0
```

### 3. RISC-V64 ABI parameter mapping

| Reg | Role at entry | Recovered from code |
|-----|---------------|---------------------|
| `a0` | (unused on entry) | overwritten at `0x4c853f4` with `a3` |
| `a1` | **base pointer** | `add a2, a2, a1` → `lw a1, 0x3e0(a2)` |
| `a2` | **index** (32-bit) | `slli a5,a2,0x20 ; srli a2,a5,0x1e` = `idx*4` |
| `a3` | **output array pointer**, 64 slots (a3..a3+0xFC) | `mv a0,a3`, `addi t6,a3,0xfc` |
| `a4` | **output count pointer** (u32) | `sw zero,0x0(a4)` init, `sw t0,0x0(a4)` increment |

**Recovered signature:**
```c
int func(void *base, uint32_t idx, uint32_t *out_indices /*64 entries*/, uint32_t *out_count)
```
Returns: `0` always (both return paths set `a0 = 0`). **Return value is not a status — it is meaningless.**

### 4. Address accessed by `lw a1, 0x3e0(a2)`

```
a2 (idx) → a2 = idx*4
a2 = a1 + idx*4
lw a1, 0x3e0(a2)  →  reads u32 at (base + 0x3E0 + idx*4)
```

At the call site `0x4BC6CAC` the arguments are established at `0x4BC6C84`–`0x4BC6CA0`:

| Reg | Setup instruction | Value |
|-----|-------------------|-------|
| `a1` | `0x4BC6C8C  mv a1, s2` | **s2** — the per-GPU object pointer at `*(*(pGpu+0x160)+0xE8)+0x28F50` |
| `a2` | `0x4BC6CA0  lw a2, 0x1b8(s11)` | **`s11+0x1B8`** — a 32-bit **input** value read from the parameters buffer |
| `a3` | `0x4BC6C88  addi a3, s0, -0x178` | stack buffer, 64 × u32 |
| `a4` | `0x4BC6C84  addi a4, s0, -0x1a4` | stack u32 (count) |

**Therefore `lw a1,0x3e0(a2)` reads:**
```
*(u32*)( s2 + 0x3E0 + (*(u32*)(s11+0x1B8)) * 4 )
```

`s2 + 0x3E0 + i*4` is an array of 32-bit bitmap words **inside the GSP per-GPU object**. The index `i` comes from the **RM caller's parameter block** (`params+0x1B8`), not from hardware.

`0x3E0` = 992 bytes = qword slot boundary not applicable (it is a dword array base). No RAMIN/register access appears in this function — **every memory operand is relative to a pointer passed in**.

### 5. What the constants mean

| Constant | Value | Role in the sequence |
|----------|-------|----------------------|
| `0x55555555` | even-bit mask | bit-counter stage 1 |
| `0x33333333` | 2-bit group mask | bit-counter stage 2 |
| `0x0F0F0F0F` | nibble mask | bit-counter stage 3 |
| `0x00FF00FF` | byte-pair mask | bit-counter stage 4 |
| `0x0000FFFF` | low-half mask | bit-counter stage 5 |

Combined with `negw/and` (isolate lowest set bit) and `seqz` per stage, this is the **classic 5-stage branchless "position of lowest set bit" (ctz) computation**, using `seqz` to produce a 0/1 per stage and summing with shifts 1,2,3,4 — i.e. `idx = (bit & K1 ? 0:1) + ((bit & K2 ?0:1)<<4) + ...`.

**Not popcount.** Popcount would `add` the `seqz` results without per-stage shifts of 1/2/3/4. Here each `seqz` result is `slliw`-ed by a distinct amount (4, 3, 2, 1) and summed — that is positional, not cardinal.

**Not nth-set-bit.** That would require an outer loop over set bits; here the outer loop is over *slots of the output array* (bound `a3+0xFC` = 63 entries), and each iteration extracts and clears *the single lowest set bit*.

**Exact classification:**
> **`bitmap_enumerate`: for a given 32-bit word, write the ascending bit indices of its set bits into `out[]`, cap at 63 entries, and return the total count in `*out_count`. Return value is always 0.**

Equivalent C:
```c
// ponytail: reconstructed semantics, not original source
int bitmap_enumerate(void *base, uint32_t idx, uint32_t *out, uint32_t *count) {
    uint32_t w = *(uint32_t*)((char*)base + 0x3E0 + idx*4);
    *count = 0;
    if (!w) return 0;
    int slot = 0;
    while (w && slot < 63) {
        int b = ctz(w);            // 5-stage seqz/slliw ladder
        out[slot] = b;
        (*count)++;
        w &= ~(1u << b);
        slot++;
    }
    return 0;
}
```

### 6. Verification that this helper is NOT the mask producer

| Criterion | Finding |
|-----------|---------|
| Does it read hardware? | **NO** — every load is `0x3E0(ptr)` where `ptr` = the s2 object passed in |
| Does it write the mask? | **NO** — writes only `out[]` (stack buffer at `s0-0x178`) and `*count` (`s0-0x1a4`) |
| What does the caller do with the result? | `s10 = sext.w(a0)` at `0x4BC6CB0` — but `a0` is the **return status (always 0)**, and `bnez s10` at `0x4BC6CB4` is an **error check**, not a value use |
| Where does the real bit index come from? | `lw a2, 0x0(s8)` at `0x4BC6D14` reads `s8 = s0-0x178`, i.e. **the `out[]` array this helper just filled** |
| Where does the count come from? | `lw s6, -0x1a4(s0)` at `0x4BC6CB8` = `*out_count` |

**Conclusion:** the helper is an **index enumerator over an already-populated bitmap**. It reads no hardware and produces no mask. Calling it a "mask producer" would be false. It *does* tell us the upstream bitmap lives at `s2 + 0x3E0 + idx*4` — that is where to look next.

## Ghi chú PONYTAIL

# ponytail: 0x4C853B4 = bitmap_enumerate(base, idx, out[], *count): reads u32 at base+0x3E0+idx*4, writes ascending bit indices (max 63), returns 0 always. Constants 0x55555555/0x33333333/0x0F0F0F0F/0x00FF00FF/0x0000FFFF + seqz + slliw{4,3,2,1} = ctz ladder, NOT popcount. Caller's `sext.w s10,a0` is an error check (a0 always 0), not a value. Real index list comes from the stack buffer this helper fills. Not a mask producer.

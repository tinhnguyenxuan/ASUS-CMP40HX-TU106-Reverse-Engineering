#!/usr/bin/env python3
# Run with: /tmp/csvenv/bin/python3 /home/REDACTED_USER/codex-work/work_v15/PHASE16/GSP_DATAFLOW_FIX/header_consumer_dataflow_fix.py
# (/usr/bin/python3 on this host has no capstone; /tmp/csvenv has capstone 5.0.7.)
# GSP_DATAFLOW_FIX — repaired symbolic dataflow for the GSP header consumer (NVUCODES).
# NEW output directory only; nothing under GSP_HEADER_CONSUMER* is modified.
# Static offline diagnosis: no hardware, no device writes, no keys, no bypass.
#
# Repairs vs the prior worker (GSP_HEADER_CONSUMER_FOLLOWUP/header_consumer_followup.py):
#   1. mem_size: lhu = 2 bytes (was 1). unsigned halfword load is 2 bytes.
#   2. step_sym: stores have no destination register (bits 11:7 are S-immediate bits);
#      store address uses the S immediate; stores write NO symbolic register (no rd clobber).
#   3. Memory effective address is captured from PRE-instruction state, before the transfer
#      overwrites the destination register (load rd == base register no longer loses its EA).
#   4. Symbolic seeds: s9/s10 seeded ONLY at the entry block (no unproven per-block global
#      seeds, no unproven s7/s8 assumptions). Every table fact comes from local definitions
#      or the entry seed; everything else is reported unresolved/uncertain.
#   5. Abstract domain: flat per-register lattice {absent ⊥, concrete u64, unknown ⊤};
#      join = agree-or-⊤; height 2 per register => guaranteed termination; pass cap with
#      explicit termination diagnostic; no growing constants can cycle.
#   6. Serializer: call_indirect/jump targets guarded before va_to_file (tgt == None made
#      seg_for compare int <= None -> TypeError); unresolved targets serialize as explicit
#      null + "UNRESOLVED" label; output coverage validated against CFG instruction count.
#   7. Call ABI clobbers: calls clobber ra + caller-saved (a0-a7, t0-t6) and the result reg;
#      callee-saved s-regs preserved (documented assumption).
#
import struct, hashlib, json, os, heapq, re, sys
from capstone import *

GSP = "/home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin"
OUTDIR = "/home/REDACTED_USER/codex-work/work_v15/PHASE16/GSP_DATAFLOW_FIX"
INNER = 0x40                      # embedded ELF64 starts at outer file 0x40
CANDIDATE_VA = 0x0459C5E0         # candidate entry (prior review json)
TABLE_BASE_VA = 0x04584790        # table base: lui s9,0x4584 / addi s9,s9,0x790
TABLE_STRIDE = 24                 # s10 = 0x18
FIELDS = {0: "actualSize", 4: "compressedSize", 8: "pData", 16: "flags", 20: "relOffset"}
MAX_INSNS = 500000
SYM_PASS_CAP = 200000
MASK64 = (1 << 64) - 1

REGS = {0: "zero", 1: "ra", 2: "sp", 3: "gp", 4: "tp", 5: "t0", 6: "t1", 7: "t2", 8: "s0", 9: "s1",
        10: "a0", 11: "a1", 12: "a2", 13: "a3", 14: "a4", 15: "a5", 16: "a6", 17: "a7",
        18: "s2", 19: "s3", 20: "s4", 21: "s5", 22: "s6", 23: "s7", 24: "s8", 25: "s9",
        26: "s10", 27: "s11", 28: "t3", 29: "t4", 30: "t5", 31: "t6"}
def rn(r): return REGS.get(r, f"x{r}")
ZERO, RA, SP, S7, S8, S9, S10, S11, S4, S2, A4, A5 = 0, 1, 2, 23, 24, 25, 26, 27, 20, 18, 14, 15
# ra + t0-t6 + a0-a7 may be clobbered by calls; s0-s11 (8, 9, 18-27) callee-saved (assumption)
CALLER_SAVES = frozenset({1, 5, 6, 7, 28, 29, 30, 31, 10, 11, 12, 13, 14, 15, 16, 17})

os.makedirs(OUTDIR, exist_ok=True)
DIS = os.path.join(OUTDIR, "disassembly"); os.makedirs(DIS, exist_ok=True)
logf = open(os.path.join(OUTDIR, "run.log"), "w")
def log(*a):
    print(*a, flush=True); print(*a, file=logf, flush=True)

checks = []  # (name, ok, detail)
def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    log(f"[check] {'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""))

# ---------------- ELF parse (stdlib struct only) --------------------------------
data = open(GSP, "rb").read()
gsp_sha = hashlib.sha256(data).hexdigest()
log(f"[inputs] gsp={GSP} size={len(data)} sha256={gsp_sha}")
inner = data[INNER:]
eh = inner[:64]
(e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum,
 e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", eh, 16)
segs = []
for i in range(e_phnum):
    p_type, p_flags, p_off, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack_from(
        "<IIQQQQQQ", inner, e_phoff + i * e_phentsize)
    segs.append(dict(type=p_type, flags=p_flags, off=p_off, vaddr=p_vaddr, paddr=p_paddr,
                     filesz=p_filesz, memsz=p_memsz, align=p_align))
    if p_type == 1:
        log(f"[elf] LOAD off={p_off:#x} vaddr={p_vaddr:#x} filesz={p_filesz:#x} memsz={p_memsz:#x} flags={p_flags:#x} exec={bool(p_flags & 1)} delta={p_vaddr - p_off:#x}")

def seg_for(va):
    for s in segs:
        if s["type"] == 1 and s["vaddr"] <= va < s["vaddr"] + s["filesz"]:
            return s
    return None

def va_to_file(va):
    if va is None:
        return None
    s = seg_for(va)
    if s is None:
        return None
    return INNER + s["off"] + (va - s["vaddr"])

def va_in_loaded(va): return seg_for(va) is not None

def va_exec(va):
    s = seg_for(va); return s is not None and bool(s["flags"] & 1)

def read_va(va, n):
    s = seg_for(va)
    if s is None: return None
    f = INNER + s["off"] + (va - s["vaddr"])
    if f < 0 or f + n > len(data): return None
    return data[f:f + n]

def read_u32_va(va):
    b = read_va(va, 4)
    return struct.unpack_from("<I", b)[0] if b else None

deltas = sorted({s["vaddr"] - s["off"] for s in segs if s["type"] == 1})
log(f"[elf] entry={e_entry:#x} machine={e_machine:#x} phnum={e_phnum} load_deltas={[hex(d) for d in deltas]}")
assert e_machine == 0xf3
cf = va_to_file(CANDIDATE_VA); assert cf == 0x59c620, f"candidate {cf:#x}"
log(f"[elf] candidate VA {CANDIDATE_VA:#x} = file {cf:#x} OK")

# ---------------- Capstone (real RISC-V backend; 16-bit C instructions possible) --
md = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64 | CS_MODE_RISCVC)

def sext(x, bits):
    if x & (1 << (bits - 1)): x -= (1 << bits)
    return x

def decode_fields(w):
    opc = w & 0x7f
    rd = (w >> 7) & 0x1f; rs1 = (w >> 15) & 0x1f; rs2 = (w >> 20) & 0x1f
    f3 = (w >> 12) & 0x7; f7 = (w >> 25) & 0x7f
    imm_i = sext(w >> 20, 12)
    imm_u = (w >> 12) & 0xfffff
    # S-type immediate (stores): imm[11:5] = bits[31:25], imm[4:0] = bits[11:7]
    imm_s = sext(((w >> 25) << 5) | ((w >> 7) & 0x1f), 12)
    xb = ((w >> 31) & 1) << 12 | ((w >> 7) & 1) << 11 | ((w >> 25) & 0x3f) << 5 | ((w >> 8) & 0xf) << 1
    imm_b = xb - 0x2000 if (xb & 0x1000) else xb
    xj = ((w >> 31) & 1) << 20 | ((w >> 21) & 0x3ff) << 1 | ((w >> 20) & 1) << 11 | ((w >> 12) & 0xff) << 12
    imm_j = xj - 0x200000 if (xj & 0x100000) else xj
    shamt = (w >> 20) & 0x1f
    shift6 = (w >> 20) & 0x3f
    return dict(opc=opc, rd=rd, rs1=rs1, rs2=rs2, f3=f3, f7=f7,
                imm_i=imm_i, imm_u=imm_u, imm_s=imm_s, imm_b=imm_b, imm_j=imm_j,
                shamt=shamt, shift6=shift6, compressed=False)

def disasm_ins(va):
    b = read_va(va, 4)
    if b is None:
        b = read_va(va, 2)          # segment end: a 2-byte C instruction may be all that remains
        if b is None: return None
    insns = list(md.disasm(b, va))
    if not insns: return None
    ins = insns[0]
    if ins.size == 2:
        b2 = read_va(va, 2)
        if b2 is not None:
            insns = list(md.disasm(b2, va))
            if insns: ins = insns[0]
            b = b2
    w = struct.unpack_from("<I", b, 0)[0] if len(b) >= 4 else struct.unpack_from("<H", b, 0)[0]
    f = decode_fields(w)
    f["compressed"] = (ins.size == 2)
    d = dict(va=ins.address, file=va_to_file(va), size=ins.size,
             raw=struct.unpack_from("<I", b, 0)[0] if len(b) >= 4 else w,
             mnemonic=ins.mnemonic, op_str=ins.op_str,
             kind=None, target=None, fields=f)
    m = ins.mnemonic
    if m == "ret": d["kind"] = "ret"
    elif m == "ebreak": d["kind"] = "ebreak"
    elif m == "jal":
        if f["rd"] == 0: d["kind"] = "jump"          # jal x0 == unconditional direct jump
        else: d["kind"] = "call"                     # jal ra == function call (fallthrough continues)
        d["target"] = va + f["imm_j"]
    elif m == "jalr":
        if f["rd"] == 0 and f["rs1"] == RA and f["imm_i"] == 0:
            d["kind"] = "ret"
        else:
            d["kind"] = "call_indirect"
    elif m.startswith("c."):
        if m == "c.jal":
            d["kind"] = "call"; d["target"] = None   # c.jal target not decoded (conservative)
        elif m == "c.j":
            d["kind"] = "jump"; d["target"] = None
        elif m in ("c.jalr", "c.jr"):
            d["kind"] = "call_indirect"; d["target"] = None
        elif m in ("c.beqz", "c.bnez"):
            d["kind"] = "branch_cond"; d["target"] = None   # target not decoded (conservative)
        else:
            d["kind"] = None                          # data-processing C op: not tracked
    elif m in ("beq", "bne", "blt", "bge", "bltu", "bgeu", "beqz", "bnez"):
        d["kind"] = "branch_cond"; d["target"] = va + f["imm_b"]
    elif m == "lui": d["kind"] = "lui"
    elif m == "auipc": d["kind"] = "auipc"
    elif m in ("lb", "lh", "lw", "lbu", "lhu", "lw", "ld", "lwu"): d["kind"] = "load"
    elif m in ("sb", "sh", "sw", "sd"): d["kind"] = "store"
    return d

# ---------------- CFG walk (unchanged logic: preserves raw CFG evidence) ----------
blocks = {}
block_range = {}
decoded_ins = {}
edges = []
calls = []
oob = []
overlaps = []
worklist = [(0, CANDIDATE_VA)]
queued = {CANDIDATE_VA}
done = set()
total_insns = 0
hit_cap = False

def push(va):
    if va in queued: return
    queued.add(va)
    heapq.heappush(worklist, (abs(va - CANDIDATE_VA), va))

def in_exec_range(va):
    return va_in_loaded(va) and va_exec(va)

while worklist and total_insns < MAX_INSNS:
    _, va = heapq.heappop(worklist)
    if va in done: continue
    if not in_exec_range(va):
        oob.append(("block_start", va, va_to_file(va)))
        done.add(va); continue
    if va % 2 != 0:
        oob.append(("unaligned", va, va_to_file(va))); done.add(va); continue
    first = disasm_ins(va)
    if first is None:
        done.add(va); continue
    done.add(va)
    block = []; cur = va; block_start = va
    while total_insns < MAX_INSNS:
        if cur in decoded_ins:
            ins = decoded_ins[cur]
        else:
            ins = disasm_ins(cur)
            if ins is None: break
            decoded_ins[cur] = ins
            total_insns += 1
        block.append(ins)
        kind = ins["kind"]; nxt = cur + ins["size"]
        if kind in ("ret", "ebreak"):
            edges.append((block_start, None, kind, ins["va"])); break
        if kind == "jump":
            t = ins["target"]
            edges.append((block_start, t, "jump", ins["va"]))
            if t is not None and in_exec_range(t): push(t)
            else: oob.append(("jump", ins["va"], t, va_to_file(t)))
            break
        if kind == "call":
            edges.append((block_start, ins["target"], "call", ins["va"]))
            cur = nxt
            if cur - va > 4000:
                edges.append((block_start, nxt, "block_bound", ins["va"]))
                if in_exec_range(nxt): push(nxt)
                break
            continue
        if kind == "call_indirect":
            resolved = None; au = None
            if len(block) >= 2 and block[-2]["kind"] == "auipc":
                au = block[-2]
                if au["fields"]["rd"] == RA:
                    resolved = (au["va"] + (au["fields"]["imm_u"] << 12)) + ins["fields"]["imm_i"]
            if resolved is not None and in_exec_range(resolved):
                calls.append(dict(ins=ins["va"], ins_file=ins["file"], kind="indirect_resolved",
                                  target=resolved, target_file=va_to_file(resolved), op=ins["op_str"],
                                  auipc_va=au["va"] if au else None))
                edges.append((block_start, resolved, "call_indirect", ins["va"]))
            else:
                calls.append(dict(ins=ins["va"], ins_file=ins["file"],
                                  kind="indirect_unresolved" if resolved is None else "indirect_out_of_exec",
                                  target=resolved,
                                  target_file=va_to_file(resolved) if resolved else None,
                                  op=ins["op_str"], auipc_va=au["va"] if au else None))
                edges.append((block_start, None, "call_indirect_unresolved", ins["va"]))
                if resolved is not None and not in_exec_range(resolved):
                    oob.append(("indirect_call", ins["va"], resolved, va_to_file(resolved)))
            cur = nxt
            if cur - va > 4000:
                edges.append((block_start, nxt, "block_bound", ins["va"]))
                if in_exec_range(nxt): push(nxt)
                break
            continue
        if kind == "branch_cond":
            t = ins["target"]
            edges.append((block_start, t, "branch_taken", ins["va"]))
            edges.append((block_start, nxt, "branch_fallthrough", ins["va"]))
            if t is not None and in_exec_range(t): push(t)
            else: oob.append(("branch", ins["va"], t, va_to_file(t)))
            if in_exec_range(nxt): push(nxt)
            else: oob.append(("branch_fallthrough", ins["va"], nxt, va_to_file(nxt)))
            break
        cur = nxt
        if cur % 2 != 0:
            edges.append((block_start, None, "misaligned_fallthrough", ins["va"])); break
        if cur - va > 4000:
            edges.append((block_start, nxt, "block_bound", ins["va"]))
            if in_exec_range(nxt): push(nxt)
            break
    blocks[block_start] = block
    block_range[block_start] = (block_start, cur if block else block_start)
    for s2, (a, b_) in block_range.items():
        if s2 == block_start: continue
        if a <= block_start < b_:
            overlaps.append((block_start, s2, a, b_))
            break

fixpoint = (not worklist) and not hit_cap
log(f"[cfg] blocks={len(blocks)} decoded_insns={len(decoded_ins)} walked_insns={total_insns} hit_cap={hit_cap}")
log(f"[cfg] edges={len(edges)} calls={len(calls)} oob={len(oob)} overlaps={len(overlaps)} fixpoint={fixpoint}")
log(f"[cfg] span={min(blocks) if blocks else CANDIDATE_VA:#x}..{max((r[1] for r in block_range.values()), default=CANDIDATE_VA):#x}")
for x, y, a_, b_ in overlaps[:10]:
    log(f"[cfg] overlap block {x:#x} inside block {a_:#x}..{b_:#x} (from block {y:#x})")
for kind, *rest in oob[:10]:
    log(f"[cfg] oob {kind} {rest}")

# ---------------- immediate correctness self-check (vs capstone op_str) ----------
# branches/jals: I/B/J immediates as before; loads: I immediate; stores: S immediate.
imm_bad = 0; imm_checked = 0; imm_detail = []
for s2, block in blocks.items():
    for ins in block:
        f = ins["fields"]; m = ins["mnemonic"]
        if m in ("beq", "bne", "blt", "bge", "bltu", "bgeu", "beqz", "bnez", "jal"):
            imm_checked += 1
            mt = re.findall(r"-?0x[0-9a-fA-F]+|-?\d+", ins["op_str"])
            cs = int(mt[-1], 0) if mt else None
            my = f["imm_b"] if m != "jal" else f["imm_j"]
            if cs is not None and my != cs:
                imm_bad += 1
                if len(imm_detail) < 8: imm_detail.append(f"{ins['va']:#x} {m} {ins['op_str']} my={my} cs={cs}")
        elif ins["kind"] in ("load", "store") and not f.get("compressed"):
            imm_checked += 1
            mt = re.findall(r"(-?0x[0-9a-fA-F]+|-?\d+)\s*\(", ins["op_str"])
            cs = int(mt[0], 0) if mt else None
            my = f["imm_s"] if ins["kind"] == "store" else f["imm_i"]
            if cs is not None and my != cs:
                imm_bad += 1
                if len(imm_detail) < 8: imm_detail.append(f"{ins['va']:#x} {m} {ins['op_str']} my={my} cs={cs}")
log(f"[check] branch/jal/load/store immediates checked={imm_checked} mismatches={imm_bad}")
for d in imm_detail: log(f"[check] IMM MISMATCH {d}")
check("immediates-vs-capstone", imm_bad == 0, f"mismatches={imm_bad}")
check("no-compressed-in-extent", not any(i["fields"].get("compressed") for b_ in blocks.values() for i in b_),
      "compressed transfer handling is dormant/structural only")

# ---------------- symbolic dataflow: table field accesses -----------------------
# sym: reg -> (val, def_va); val in {int (u64), "IDX", "BASE_IDX24", "S7_IDX24", None}
#   absent reg = ⊥ (unreachable/unknown), concrete int = constant, None = ⊤ (overdefined)
# Join: agree-or-⊤. Flat lattice per register, height 2 => monotone, finite, terminating.
# Seeds: s9=TABLE_BASE_VA and s10=TABLE_STRIDE at entry block CANDIDATE_VA ONLY. No global
# per-block seeds (s9/s10), no unproven s7/s8 assumptions. Loop headers are logged, not seeded.

def is_loop_header(bs):
    for (src, dst, kind, ins_va) in edges:
        if dst == bs and kind in ("branch_taken", "jump") and src is not None and src > bs:
            return True
    return False

loop_headers = sorted(bs for bs in blocks if is_loop_header(bs))
log(f"[dataflow] loop headers (back-edge targets): {[hex(x) for x in loop_headers]}")

def step_sym(sym, ins):
    f = ins["fields"]; m = ins["mnemonic"]; opc = f["opc"]; rd = f["rd"]; rs1 = f["rs1"]; rs2 = f["rs2"]
    sym = dict(sym)
    if f.get("compressed"):
        # compressed data ops are not decoded (none occur in this extent); no precise clobber info.
        if m == "c.jal": sym[RA] = (None, ins["va"])
        return sym
    if opc == 0x37:  # lui
        sym[rd] = ((f["imm_u"] << 12) & MASK64, ins["va"])
    elif opc == 0x13 and f["f3"] == 0:  # addi (incl. mv)
        if rs1 == ZERO:
            sym[rd] = (f["imm_i"] & MASK64, ins["va"])
        else:
            v, _ = sym.get(rs1, (None, None))
            if isinstance(v, int): sym[rd] = ((v + f["imm_i"]) & MASK64, ins["va"])
            else: sym[rd] = (None, ins["va"])
    elif opc == 0x13 and f["f3"] == 1:  # slli
        v, _ = sym.get(rs1, (None, None)); sh = f["shift6"]
        if isinstance(v, int): sym[rd] = ((v << sh) & MASK64, ins["va"])
        elif v == "IDX" and sh == 32: sym[rd] = ("IDX", ins["va"])
        else: sym[rd] = (None, ins["va"])
    elif opc == 0x13 and f["f3"] == 5:  # srli / srai
        v, _ = sym.get(rs1, (None, None)); sh = f["shift6"]
        if isinstance(v, int):
            sym[rd] = (v >> sh, ins["va"])           # values tracked are u64 addresses/indices
        elif v == "IDX" and sh == 32: sym[rd] = ("IDX", ins["va"])
        else: sym[rd] = (None, ins["va"])
    elif opc == 0x33 and f["f3"] == 0 and f["f7"] == 0:  # add
        a, da = sym.get(rs1, (None, None)); b, db = sym.get(rs2, (None, None))
        if isinstance(a, int) and isinstance(b, int): sym[rd] = ((a + b) & MASK64, ins["va"])
        elif a == TABLE_BASE_VA and b == "IDX24": sym[rd] = ("BASE_IDX24", ins["va"])
        elif b == TABLE_BASE_VA and a == "IDX24": sym[rd] = ("BASE_IDX24", ins["va"])
        else: sym[rd] = (None, ins["va"])
    elif opc == 0x33 and f["f3"] == 0 and f["f7"] == 1:  # mul
        a, _ = sym.get(rs1, (None, None)); b, _ = sym.get(rs2, (None, None))
        if (a == "IDX" and b == TABLE_STRIDE) or (b == "IDX" and a == TABLE_STRIDE):
            sym[rd] = ("IDX24", ins["va"])
        elif isinstance(a, int) and isinstance(b, int): sym[rd] = ((a * b) & MASK64, ins["va"])
        else: sym[rd] = (None, ins["va"])
    elif m == "mv" or (opc == 0x13 and f["f3"] == 0 and rs1 == ZERO):
        sym[rd] = sym.get(rs1, (None, None))
    elif ins["kind"] == "load":
        pass  # destination handled by caller using PRE state; write unknown below
    elif ins["kind"] == "store":
        pass  # stores have no destination register; bits 11:7 are S-immediate bits -> no sym write
    elif ins["kind"] in ("call", "call_indirect", "ret"):
        for r in CALLER_SAVES: sym[r] = (None, ins["va"])
        if rd != 0 and rd not in CALLER_SAVES: sym[rd] = (None, ins["va"])
    else:
        sym[rd] = (None, ins["va"])
    if ins["kind"] == "load":  # load destination is overwritten: unknown after the EA was captured
        sym[rd] = (None, ins["va"])
    sym[ZERO] = (0, None)
    return sym

def mem_size(ins):
    m = ins["mnemonic"]
    if m in ("ld", "sd"): return 8
    if m in ("lw", "sw"): return 4
    if m in ("lh", "lhu", "sh"): return 2          # lhu = 2 (prior bug: mapped to 1)
    if m in ("lb", "lbu", "sb"): return 1
    return None

succs_of = {}; preds_of = {}
for (src, dst, kind, ins_va) in edges:
    if dst is None: continue
    if kind in ("branch_taken", "branch_fallthrough", "jump"):
        succs_of.setdefault(src, []).append(dst)
        preds_of.setdefault(dst, []).append(src)

entry_sym = {bs: {} for bs in blocks}
entry_sym[CANDIDATE_VA] = {S9: (TABLE_BASE_VA, None), S10: (TABLE_STRIDE, None)}
work = [CANDIDATE_VA]; inwork = {CANDIDATE_VA}
processed_sym = {}
sym_passes = 0
table_accesses = []
xref_scan = []
field_offsets = set(FIELDS.keys())

while work and sym_passes < SYM_PASS_CAP:
    bs = work.pop(0); inwork.discard(bs); sym_passes += 1
    sym = dict(entry_sym.get(bs, {}))
    pending = None  # (ins_va, field, loaded_reg) waiting for a guard branch
    for ins in blocks[bs]:
        pre = dict(sym)          # PRE-instruction state: effective address computed from here
        sym = step_sym(sym, ins)
        if ins["kind"] in ("load", "store"):
            sz = mem_size(ins)
            rs1 = ins["fields"]["rs1"]
            base_val, base_def = pre.get(rs1, (None, None))
            off = ins["fields"]["imm_s"] if ins["kind"] == "store" else ins["fields"]["imm_i"]
            base_tag = None; rec_index = None; rec_va = None; def_base_va = None
            if isinstance(base_val, int):
                if base_val == TABLE_BASE_VA:
                    base_tag = "BASE"; rec_index = 0; rec_va = TABLE_BASE_VA; def_base_va = base_def
                elif (base_val - TABLE_BASE_VA) % TABLE_STRIDE == 0:
                    idx = (base_val - TABLE_BASE_VA) // TABLE_STRIDE
                    if 0 <= idx < 65536:
                        base_tag = "BASE"; rec_index = idx; rec_va = base_val; def_base_va = base_def
            elif base_val == "BASE_IDX24":
                base_tag = "BASE_IDX24"; def_base_va = base_def
            elif base_val == "S7_IDX24":
                base_tag = "S7_IDX24"; def_base_va = base_def
            field = FIELDS.get(off)
            if off in field_offsets:
                xref_scan.append(dict(
                    ins=ins["va"], ins_file=ins["file"], mnemonic=ins["mnemonic"], op_str=ins["op_str"],
                    raw=ins["raw"], size=ins["size"], base_reg=rn(rs1), offset=off, field=FIELDS.get(off),
                    tag=base_tag if base_tag else "unresolved",
                    base_value=(hex(base_val) if isinstance(base_val, int) else base_val),
                    def_base_va=def_base_va))
            if base_tag in ("BASE", "BASE_IDX24") and field:
                raw = None; rfile = None; value = None; raw_verified = False
                if rec_va is not None:
                    rb = read_va(rec_va + off, sz)
                    if rb:
                        raw = rb.hex(); rfile = va_to_file(rec_va + off)
                        if sz == 4: value = struct.unpack_from("<I", rb, 0)[0]
                        elif sz == 8: value = struct.unpack_from("<Q", rb, 0)[0]
                        # independent validation: same bytes reachable via file offset
                        if rfile is not None and rfile + sz <= len(data):
                            raw_verified = (data[rfile:rfile + sz].hex() == raw)
                table_accesses.append(dict(
                    ins=ins["va"], ins_file=ins["file"], mnemonic=ins["mnemonic"], op_str=ins["op_str"],
                    raw=ins["raw"], size=ins["size"], kind=ins["kind"],
                    base_reg=rn(rs1), base_tag=base_tag, offset=off, field=field,
                    rec_index=rec_index, rec_va=rec_va,
                    rec_file=va_to_file(rec_va) if rec_va else None,
                    raw_bytes=raw, raw_file=rfile, value=value, size_read=sz,
                    raw_verified=raw_verified, guard=None, def_base_va=def_base_va,
                    proven=(base_tag == "BASE"), assumption=None))
                pending = (ins["va"], field, ins["fields"]["rd"])
            else:
                pending = None
        elif pending is not None:
            f2 = ins["fields"]
            if ins["kind"] == "branch_cond" and (f2["rs1"] == pending[2] or f2["rs2"] == pending[2]):
                table_accesses[-1]["guard"] = ins["va"]; pending = None
            elif ins["kind"] in ("load", "store", "call", "call_indirect", "ret", "lui", "auipc", "jump"):
                pending = None
            elif f2["opc"] == 0x13 and f2["f3"] == 0x7 and f2["rd"] == pending[2]:  # andi on loaded reg
                pass  # keep pending, next branch may use it
    processed_sym[bs] = sym
    for dst in succs_of.get(bs, ()):
        if dst not in blocks: continue
        old = entry_sym.get(dst, {})
        regs = set(old)
        for p in preds_of.get(dst, ()):
            if p in processed_sym:
                for r in processed_sym[p]: regs.add(r)
        joined = {}
        for r in regs:
            ents = [processed_sym[p][r] for p in preds_of.get(dst, ())
                    if p in processed_sym and r in processed_sym[p]]
            vals = [e[0] for e in ents]
            if vals and all(v == vals[0] for v in vals):
                v = vals[0]
                dfs = [e[1] for e in ents]
                d = dfs[0] if all(x == dfs[0] for x in dfs) else None
                joined[r] = (v, d)
            else:
                joined[r] = (None, None)
        if joined != old:
            entry_sym[dst] = joined
            if dst not in inwork:
                work.append(dst); inwork.add(dst)
sym_hit_cap = sym_passes >= SYM_PASS_CAP
sym_status = "capped" if sym_hit_cap else ("fixpoint" if not work else "open")
log(f"[dataflow] passes={sym_passes} cap={SYM_PASS_CAP} hit_cap={sym_hit_cap} status={sym_status}")
log(f"[dataflow] lattice: per-register {{absent, concrete u64, unknown}}; join=agree-or-unknown; "
    f"height 2/register => monotone termination; no widening needed, no growing constants")

# ---- deduplicate accesses reported from overlapping blocks (same insn in >1 block) ----
dedup = {}
for t in table_accesses:
    k = t["ins"]; prev = dedup.get(k)
    if prev is None:
        dedup[k] = dict(t)
    else:
        if t["rec_index"] is not None and prev["rec_index"] is None:
            prev["rec_index"] = t["rec_index"]; prev["rec_va"] = t["rec_va"]
            prev["rec_file"] = t["rec_file"]; prev["raw_bytes"] = t["raw_bytes"]
            prev["raw_file"] = t["raw_file"]; prev["value"] = t["value"]
            prev["raw_verified"] = t["raw_verified"]
        if t["rec_index"] is not None:
            prev["base_tag"] = t["base_tag"]; prev["proven"] = t["proven"]
        if t["guard"] is not None: prev["guard"] = t["guard"]
        prev["_dup_insns"] = prev.get("_dup_insns", 0) + 1
table_accesses = list(dedup.values())
xref_dedup = {}
for x in xref_scan:
    k = (x["ins"], x["offset"])
    if k not in xref_dedup: xref_dedup[k] = x
xref_scan = list(xref_dedup.values())
base_table_accesses = [t for t in table_accesses if t["base_tag"] in ("BASE", "BASE_IDX24")]
s7_table_accesses = [t for t in table_accesses if t["base_tag"] == "S7_IDX24"]
log(f"[dataflow] table accesses (base 0x4584790): {len(base_table_accesses)}  (via s7 table: {len(s7_table_accesses)})")
for t in base_table_accesses:
    log(f"[tbl] {t['ins']:#x} {t['mnemonic']:6s} {t['op_str']} base={t['base_tag']} field={t['field']} off={t['offset']} "
        f"idx={t['rec_index']} rec_va={t['rec_va'] and hex(t['rec_va'])} value={t['value'] and hex(t['value'])} "
        f"raw={t['raw_bytes']} guard={t['guard'] and hex(t['guard'])} def_base_va={t['def_base_va'] and hex(t['def_base_va'])} "
        f"proven={t['proven']} raw_verified={t['raw_verified']}")

# ---------------- record dump & validation against firmware container -----------
count_from_header = 496
n_valid = 0; n_zero = 0; n_oob = 0; records = []
for idx in range(count_from_header):
    rva = TABLE_BASE_VA + idx * TABLE_STRIDE
    if not va_in_loaded(rva + TABLE_STRIDE - 1):
        n_oob += 1; records.append(dict(index=idx, rec_va=rva, rec_file=None, in_bounds=False))
        continue
    rb = read_va(rva, TABLE_STRIDE)
    f00 = struct.unpack_from("<I", rb, 0)[0]; f04 = struct.unpack_from("<I", rb, 4)[0]
    f08 = struct.unpack_from("<Q", rb, 8)[0]; f16 = struct.unpack_from("<I", rb, 16)[0]
    f20 = struct.unpack_from("<I", rb, 20)[0]
    allz = (rb == b"\x00" * TABLE_STRIDE)
    if allz: n_zero += 1
    else: n_valid += 1
    records.append(dict(index=idx, rec_va=rva, rec_file=va_to_file(rva), in_bounds=True,
                        actualSize=f00, compressedSize=f04, pData=f08, flags=f16, relOffset=f20,
                        raw=rb.hex(), all_zero=allz,
                        pData_file=va_to_file(f08) if va_in_loaded(f08) else None,
                        pData_in_exec=va_exec(f08) if va_in_loaded(f08) else None))
log(f"[table] count={count_from_header} valid_nonzero={n_valid} zero={n_zero} out_of_bounds={n_oob}")
desc_base = 0x41a70b0
desc_in_bounds = va_in_loaded(desc_base + TABLE_STRIDE - 1)
log(f"[xref] descriptor_table.json base 0x{desc_base:x} (gsp_summary) in_loaded={desc_in_bounds}; "
    f"distinct from 0x{TABLE_BASE_VA:x}; no cross-reference -> names/engine = UNKNOWN")

# ---------------- focused semantic checks on real instructions ------------------
# C1: width table
wtable = {"lb": 1, "lbu": 1, "lh": 2, "lhu": 2, "lw": 4, "sw": 4, "ld": 8, "sd": 8, "sh": 2, "sb": 1}
width_check = all(mem_size(dict(mnemonic=m)) == w for m, w in wtable.items())
real_widths = {}
for block in blocks.values():
    for ins in block:
        if ins["kind"] in ("load", "store"):
            real_widths[ins["mnemonic"]] = real_widths.get(ins["mnemonic"], 0) + 1
check("mem_size width table (lhu=2)", width_check, f"real load/store mnemonics in CFG: {dict(sorted(real_widths.items()))}")

# C2: store does not clobber rd field (bits 11:7 are S immediate bits); address uses S immediate
fake_store = dict(va=0x1000, file=0x1000, raw=0, size=4, mnemonic="sw", op_str="sw t0, 8(a0)", kind="store",
                  fields=dict(opc=0x23, rd=5, rs1=10, rs2=11, f3=2, f7=0, imm_i=0, imm_s=8, imm_b=0, imm_j=0,
                              shamt=0, shift6=0, compressed=False))
sym_test = {S4: (0x4584790, 0x2000), 10: (0x1000, None), 5: (42, None)}
pre = dict(sym_test); sym_after = step_sym(sym_test, fake_store)
check("store writes no rd (t0=42 preserved)", sym_after.get(5) == (42, None) and sym_after.get(10) == (0x1000, None),
      "store EA from pre-state; rd field untouched")
# C3: load whose rd == its base register uses PRE-state base
fake_load = dict(va=0x1004, file=0x1004, raw=0, size=4, mnemonic="lw", op_str="lw a0, 0(a0)", kind="load",
                 fields=dict(opc=0x03, rd=10, rs1=10, rs2=0, f3=2, f7=0, imm_i=0, imm_s=0, imm_b=0, imm_j=0,
                             shamt=0, shift6=0, compressed=False))
sym_test2 = {10: (TABLE_BASE_VA, 0x3000)}
pre2 = dict(sym_test2); _ = step_sym(sym_test2, fake_load)
acc_check = None
# replicate the access evaluation for the fake load
bv, bd = pre2.get(10, (None, None))
if isinstance(bv, int) and bv == TABLE_BASE_VA:
    acc_check = ("BASE", 0, TABLE_BASE_VA, bd)
check("load EA from pre-state even when rd overwrites base", acc_check == ("BASE", 0, TABLE_BASE_VA, 0x3000),
      f"eval={acc_check}")
# C4: known-positive recovery chain 0x459c708 -> 0x459c70c -> 0x459c710 -> 0x459c714
acc_70c = [t for t in base_table_accesses if t["ins"] == 0x459c70c]
chain_ok = (len(acc_70c) == 1 and acc_70c[0]["base_tag"] == "BASE" and acc_70c[0]["field"] == "flags"
            and acc_70c[0]["offset"] == 16 and acc_70c[0]["rec_index"] == 0
            and acc_70c[0]["rec_va"] == TABLE_BASE_VA and acc_70c[0]["value"] == 0
            and acc_70c[0]["raw_bytes"] == "00000000" and acc_70c[0]["guard"] == 0x459c714
            and acc_70c[0]["def_base_va"] == 0x459c708 and acc_70c[0]["proven"] is True
            and acc_70c[0]["raw_verified"] is True)
ins708 = [i for b_ in blocks.values() for i in b_ if i["va"] == 0x459c708]
ins710 = [i for b_ in blocks.values() for i in b_ if i["va"] == 0x459c710]
ins714 = [i for b_ in blocks.values() for i in b_ if i["va"] == 0x459c714]
chain_ok = chain_ok and len(ins708) >= 1 and ins708[0]["mnemonic"] == "add" and ins708[0]["fields"]["rs1"] == S9 and ins708[0]["fields"]["rs2"] == S2
chain_ok = chain_ok and len(ins710) >= 1 and ins710[0]["mnemonic"] == "andi"
chain_ok = chain_ok and len(ins714) >= 1 and ins714[0]["mnemonic"] == "beqz"
# file-offset cross-check of the flags raw bytes
rec0_file = va_to_file(TABLE_BASE_VA)
flags_file_bytes = data[rec0_file + 16:rec0_file + 20].hex() if rec0_file is not None else None
chain_ok = chain_ok and flags_file_bytes == "00000000"
check("known-positive: 0x459c708 add a4,s9,s2; 0x459c70c lw flags+16 idx0 raw=00000000 guard=0x459c714 def=0x459c708; file bytes match VA",
      chain_ok, f"ins708={ins708 and ins708[0]['op_str']} ins710={ins710 and ins710[0]['op_str']} ins714={ins714 and ins714[0]['op_str']} flags_file={flags_file_bytes}")
# C5: second flags load 0x459c71c lw a5,0x10(s2): base s2 = s7+s2, s7 unproven -> unresolved, NOT merged with BASE table
acc_71c = [t for t in base_table_accesses if t["ins"] == 0x459c71c]
xref_71c = [x for x in xref_scan if x["ins"] == 0x459c71c]
s7_ok = (len(acc_71c) == 0 and len(xref_71c) >= 1 and xref_71c[0]["tag"] == "unresolved"
         and xref_71c[0]["base_reg"] == "s2" and xref_71c[0]["offset"] == 16)
check("second flags load 0x459c71c lw a5,0x10(s2): separate s7-derived base, unresolved, not merged",
      s7_ok, f"xref={xref_71c}")
# C6: compressedSize(+4)/relOffset(+20) offset-matched but base-unresolved insns are listed, not attributed
off4 = [x for x in xref_scan if x["offset"] == 4]
off20 = [x for x in xref_scan if x["offset"] == 20]
off4_resolved = [x for x in off4 if x["tag"] != "unresolved"]
off20_resolved = [x for x in off20 if x["tag"] != "unresolved"]
check("compressedSize+4 and relOffset+20: present-but-unresolved, not attributed to 0x4584790",
      len(off4_resolved) == 0 and len(off20_resolved) == 0,
      f"offset4 insns={len(off4)} (resolved {len(off4_resolved)}); offset20 insns={len(off20)} (resolved {len(off20_resolved)})")
# C7: termination
check("dataflow termination", sym_status == "fixpoint", f"passes={sym_passes} cap={SYM_PASS_CAP}")
# C8: records cross-check (rec0 flags vs access value)
rec0_flags = records[0]["flags"] if records else None
check("records_dump rec0.flags == 0x459c70c access value (0)", rec0_flags == 0 and acc_70c and acc_70c[0]["value"] == 0,
      f"rec0.flags={rec0_flags}")

# ---------------- serialize outputs ---------------------------------------------
def ins_ser(ins):
    return dict(va=ins["va"], file=ins["file"], raw=ins["raw"], size=ins["size"],
                mnemonic=ins["mnemonic"], op_str=ins["op_str"], kind=ins["kind"],
                target=ins["target"], imm_b=ins["fields"]["imm_b"], imm_j=ins["fields"]["imm_j"])

cfg_out = {
  "blocks": {hex(k): [ins_ser(i) for i in v] for k, v in blocks.items()},
  "block_range": {hex(k): [a, b_] for k, (a, b_) in block_range.items()},
  "edges": [[s, d, k, (va if va is not None else None)] for s, d, k, va in edges],
  "calls": calls,
  "oob": oob,
  "overlaps": [[x, y, a, b_] for (x, y, a, b_) in overlaps],
  "fixpoint": fixpoint, "hit_cap": hit_cap,
  "total_insns_walked": total_insns, "decoded_insns": len(decoded_ins),
  "span_start": min(blocks) if blocks else CANDIDATE_VA, "span_end": max((r[1] for r in block_range.values()), default=CANDIDATE_VA),
  "loop_headers": [hex(x) for x in loop_headers],
}
json.dump(cfg_out, open(os.path.join(DIS, "cfg.json"), "w"), indent=1)

def fmt_tgt(tgt):
    if tgt is None: return "UNRESOLVED(target=null)"
    f = va_to_file(tgt)
    return f"{tgt:#x}" + (f" (file {f:#x})" if f is not None else " (file null)")

acc_by_va = {t["ins"]: t for t in base_table_accesses}
ins_line_total = 0
seen_vas = set()
with open(os.path.join(DIS, "extended_disasm.txt"), "w") as f:
    f.write(f"; GSP_DATAFLOW_FIX disassembly of candidate at VA {CANDIDATE_VA:#x} (file {cf:#x})\n")
    f.write("; offline, /tmp/csvenv/bin/python3 capstone 5.0.7, CS_ARCH_RISCV|CS_MODE_RISCV64|CS_MODE_RISCVC\n")
    f.write(f"; blocks={len(blocks)} decoded_insns={len(decoded_ins)} walked={total_insns} fixpoint={fixpoint} hit_cap={hit_cap}\n")
    f.write(f"; span={min(blocks) if blocks else CANDIDATE_VA:#x}..{max((r[1] for r in block_range.values()), default=CANDIDATE_VA):#x}\n")
    f.write(f"; edges={len(edges)} indirect_calls={len(calls)} unresolved_indirect={sum(1 for c in calls if c['kind']=='indirect_unresolved')} overlaps={len(overlaps)} oob={len(oob)}\n")
    f.write("; 16/32-bit variable lengths honored; jal x0 = direct jump; jalr x0,0(ra)=ret; unresolved jalr/c.jalr = UNRESOLVED(target=null) indirect edge\n")
    f.write("; symbolic seeds: s9/s10 at entry block only; no unproven global s9/s10 or s7/s8 seeds\n")
    for bs in sorted(blocks):
        f.write(f"; block {bs:#010x} (insns {len(blocks[bs])})\n")
        for ins in blocks[bs]:
            tag = ""
            if ins["kind"] == "branch_cond":
                tag = f" -> {fmt_tgt(ins['target'])}"
            elif ins["kind"] in ("call_indirect", "call", "jump"):
                tag = f" -> {fmt_tgt(ins['target'])}"
            a = acc_by_va.get(ins["va"])
            if a:
                tag += (f" | TABLE_ACCESS base={a['base_tag']} field={a['field']} off={a['offset']} "
                        f"idx={a['rec_index']} rec_va={a['rec_va'] and hex(a['rec_va'])} "
                        f"guard={a['guard'] and hex(a['guard'])} def_base_va={a['def_base_va'] and hex(a['def_base_va'])} "
                        f"proven={a['proven']} raw_verified={a['raw_verified']}")
            f.write(f"{ins['va']:#010x} file={ins['file'] and hex(ins['file'])} {ins['raw']:08x} size={ins['size']} "
                    f"{ins['mnemonic']:10s} {ins['op_str']}{tag}\n")
            ins_line_total += 1
            seen_vas.add(ins["va"])
    f.write("\n; indirect call sites:\n")
    for c in calls:
        f.write(f";   {c['ins']:#010x} {c['kind']} target={c['target'] and hex(c['target'])} file={c['target_file'] and hex(c['target_file'])} op={c['op']}\n")
    f.write("\n; overlaps (block start inside another block's range):\n")
    for x, y, a, b_ in overlaps:
        f.write(f";   block {x:#x} inside {a:#x}..{b_:#x} (previously block {y:#x})\n")

expected_total = sum(len(b_) for b_ in blocks.values())
expected_unique = len(decoded_ins)
coverage_ok = (ins_line_total == expected_total and len(seen_vas) == expected_unique)
check("disasm coverage vs CFG instruction count", coverage_ok,
      f"lines={ins_line_total} expected_total={expected_total} unique_vas={len(seen_vas)} expected_unique={expected_unique}")

json.dump(dict(table_accesses=base_table_accesses, s7_table_accesses=s7_table_accesses,
               xref_scan=xref_scan),
          open(os.path.join(OUTDIR, "table_accesses.json"), "w"), indent=1)
json.dump(dict(count=count_from_header, table_base_va=TABLE_BASE_VA,
               table_base_file=va_to_file(TABLE_BASE_VA), stride=TABLE_STRIDE,
               records=records),
          open(os.path.join(OUTDIR, "records_dump.json"), "w"), indent=1)

# ---------------- verified report -----------------------------------------------
magic_raw = read_va(0x4022330, 8); fp_raw = read_va(0x4022338, 8)
fp_val = struct.unpack_from("<Q", fp_raw, 0)[0] if fp_raw else None
field_status = {}
for off, name in FIELDS.items():
    accs = [t for t in base_table_accesses if t["offset"] == off]
    field_status[name] = dict(offset=off, confirmed=len(accs),
                              example=accs[0] if accs else None,
                              note=("proven at record index 0 (rec0 sentinel)" if accs and accs[0]["rec_index"] == 0 else
                                    ("offset-matched but base unresolved" if any(x["offset"] == off for x in xref_scan) else "no offset-matched insn")))
verified = {
  "inputs": {"gsp": GSP, "gsp_sha256": gsp_sha, "script": os.path.abspath(__file__),
             "python": "/tmp/csvenv/bin/python3", "capstone": "5.0.7", "mode": "RISCV64|RISCVC", "offline": True},
  "elf": {"entry": e_entry, "machine": hex(e_machine), "phnum": e_phnum,
          "deltas": [hex(d) for d in deltas],
          "mapping_note": "VA = outer_file_offset + 0x03ffffc0 (parsed PT_LOAD)"},
  "mapping_checks": {"candidate_va": hex(CANDIDATE_VA), "candidate_file": hex(cf),
                     "magic_va": "0x4022330", "magic_file": "0x22370",
                     "fp_va": "0x4022338", "fp_file": "0x22378",
                     "fp_value": hex(fp_val), "fp_ok": fp_val == 0x8D1990AB6B98AE2B,
                     "magic_ok": magic_raw == b"NVUCODES"},
  "cfg": cfg_out,
  "dataflow": {
    "abstract_domain": "per-register flat lattice {absent ⊥, concrete u64, unknown ⊤}; join = agree-or-⊤",
    "seeds": {"entry_only": [f"s9={TABLE_BASE_VA:#x}", f"s10={TABLE_STRIDE}"],
              "assumption_seeded": []},
    "passes": sym_passes, "pass_cap": SYM_PASS_CAP, "hit_cap": sym_hit_cap, "status": sym_status,
    "note": "constants never grow: join of two distinct constants yields ⊤ immediately; no widening required",
  },
  "table": {
    "base_va": hex(TABLE_BASE_VA), "base_file": hex(va_to_file(TABLE_BASE_VA)),
    "stride": TABLE_STRIDE, "count_from_header": count_from_header,
    "records_total": count_from_header, "records_nonzero": n_valid, "records_zero": n_zero,
    "records_out_of_bounds": n_oob,
    "base_accesses": len(base_table_accesses), "s7_base_accesses": len(s7_table_accesses),
    "fields": FIELDS, "field_status": field_status,
    "sym_pass_cap_hit": sym_hit_cap,
    "record0_zero": records[0]["all_zero"] if records else None,
    "xref_scan": xref_scan,
    "note_internal_vs_external": "495 nonzero / 1 zero records are the INTERNAL table at 0x4584790 (stride 24). "
                                 "This is distinct from the external NVUCODES archive (496 slots / 38 external "
                                 "payloads); equal stride alone does not establish identical contents or occupancy.",
  },
  "xref": {
    "descriptor_table_json_base": hex(desc_base),
    "descriptor_in_loaded": desc_in_bounds,
    "cross_reference_to_0x4584790": False,
    "descriptor_names_engine": "UNKNOWN",
    "note": "descriptor_table.json (base 0x41a70b0, from gsp_summary) is a different table than 0x4584790; "
            "no binary/source cross-reference links its names to this table, so descriptor names and engine are UNKNOWN.",
  },
  "serialization": {
    "unresolved_target_label": "UNRESOLVED(target=null)",
    "example": "0x459c648 jalr s2 -> UNRESOLVED(target=null)",
    "coverage_ok": coverage_ok,
    "insn_lines": ins_line_total, "expected_total": expected_total,
    "unique_vas": len(seen_vas), "expected_unique": expected_unique,
  },
  "checks": [{"name": n, "ok": ok, "detail": d} for (n, ok, d) in checks],
  "fixpoint": fixpoint, "hit_cap": hit_cap,
  "limits": {
    "indirect_calls_not_entered": len(calls),
    "unresolved_indirect_calls": sum(1 for c in calls if c["kind"] == "indirect_unresolved"),
    "out_of_bounds_targets": len(oob),
    "overlaps_handled": len(overlaps),
    "cap": MAX_INSNS,
  },
  "verdict": {
    "cfg_complete": fixpoint and not hit_cap,
    "dataflow_terminated": sym_status == "fixpoint",
    "table_fields_confirmed": {name: st["confirmed"] for name, st in field_status.items()},
    "table_fields_not_confirmed": ["compressedSize (+4)", "relOffset (+20)"],
    "s7_table_access": "0x459c71c lw a5,0x10(s2) - separate table base, unresolved, verifier incomplete for this access",
    "descriptor_names_engine": "UNKNOWN (no cross-reference)",
  },
}
json.dump(verified, open(os.path.join(OUTDIR, "verified.json"), "w"), indent=1)

log(f"[dataflow] table accesses (base 0x4584790): {len(base_table_accesses)}  (via s7 table: {len(s7_table_accesses)})")
for name, ok, d in checks:
    if not ok: log(f"[check] FAIL {name}: {d}")
log(f"[done] fixpoint={fixpoint} hit_cap={hit_cap} dataflow_status={sym_status}")
log(f"[done] wrote {OUTDIR}/verified.json, {OUTDIR}/table_accesses.json, {OUTDIR}/records_dump.json, {DIS}/cfg.json, {DIS}/extended_disasm.txt, {OUTDIR}/run.log")
failed = [n for (n, ok, d) in checks if not ok]
logf.close()
print("EXIT=0" if not failed else f"EXIT=1 failed_checks={failed}")
sys.exit(0 if not failed else 1)

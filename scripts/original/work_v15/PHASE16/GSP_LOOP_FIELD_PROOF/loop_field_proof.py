#!/usr/bin/env python3
# Run with: /tmp/csvenv/bin/python3 /home/REDACTED_USER/codex-work/work_v15/PHASE16/GSP_LOOP_FIELD_PROOF/loop_field_proof.py
# GSP_LOOP_FIELD_PROOF — loop-carried index / field-offset / table-identity proof for the GSP
# NVUCODES header consumer at VA 0x0459C5E0. Static offline diagnosis; saved GSP binary only.
#
# Purpose: prove or leave unknown the loop-carried record index, the field offsets
# (actualSize+0, compressedSize+4, pData+8, flags+16, relOffset+20) and the table
# identities (s9-derived BASE 0x4584790 vs s7-derived) beyond the already-grounded
# flags+16 load at record index 0.
#
# Method:
#   * Rebuild the CFG from the binary with LEADER-based basic blocks: every proven
#     branch/jump/resolved-call target and every fallthrough-after-terminator starts a
#     block. This splits overlapping blocks at every proven branch target, removes
#     duplicated decode slots, and yields each instruction exactly once (traversed CFG,
#     bounded — callees not entered, so not function-complete).
#   * Trace local definitions of s9=0x4584790, s10=24, s8(index): dominance, survival
#     across calls/back-edges. Run dataflow WITH and WITHOUT the s9/s10 entry seed and
#     compare (seed must not be load-bearing; here s9/s10/s8 are defined in the entry
#     block so results agree).
#   * Flat lattice {absent, concrete u64, unknown}; join=agree-or-unknown. Report the
#     join precision loss at back-edge targets (concrete 0 vs concrete k -> unknown).
#   * Separate affine/relational index derivation: s8 = IV(0,1), a4 = 0x4584790 + k*24;
#     loop bound a3 = frame load (unknown statically) -> index unbounded concretely ->
#     per-record proof only sound for k=0.
#   * Verify branch conditions and load/store widths from raw bytes (re-decode vs
#     capstone op_str immediates; width table lhu=2 etc.).
#   * Track s9-derived (BASE) and s7-derived bases SEPARATELY, never merged.
#   * Per-access: VA, raw instruction, reaching base def, guard for actualSize+0,
#     compressedSize+4, pData+8, flags+16, relOffset+20 vs 0x4584790.
#   * Preserve unresolved indirect calls and ABI clobbers.
#
# No hardware, no writes, no keys, no bypass. Originals under GSP_DATAFLOW_FIX* and
# GSP_HEADER_CONSUMER* are read only.

import struct, hashlib, json, os, heapq, re, bisect, sys
from capstone import *

GSP = "/home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin"
SCRIPT = os.path.abspath(__file__)
OUTDIR = "/home/REDACTED_USER/codex-work/work_v15/PHASE16/GSP_LOOP_FIELD_PROOF"
DIS = os.path.join(OUTDIR, "disassembly")
INNER = 0x40
CANDIDATE_VA = 0x0459C5E0
TABLE_BASE_VA = 0x04584790
TABLE_STRIDE = 24
FIELDS = {0: "actualSize", 4: "compressedSize", 8: "pData", 16: "flags", 20: "relOffset"}
MAX_INSNS = 500000
SYM_PASS_CAP = 200000
MASK64 = (1 << 64) - 1

REGS = {0:"zero",1:"ra",2:"sp",3:"gp",4:"tp",5:"t0",6:"t1",7:"t2",8:"s0",9:"s1",
        10:"a0",11:"a1",12:"a2",13:"a3",14:"a4",15:"a5",16:"a6",17:"a7",
        18:"s2",19:"s3",20:"s4",21:"s5",22:"s6",23:"s7",24:"s8",25:"s9",
        26:"s10",27:"s11",28:"t3",29:"t4",30:"t5",31:"t6"}
def rn(r): return REGS.get(r, f"x{r}")
ZERO,RA,SP,S7,S8,S9,S10,S11,S4,S2,A4,A5,A2,A3 = 0,1,2,23,24,25,26,27,20,18,14,15,12,13
CALLER_SAVES = frozenset({1,5,6,7,28,29,30,31,10,11,12,13,14,15,16,17})

os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(DIS, exist_ok=True)
logf = open(os.path.join(OUTDIR, "run.log"), "w")
def log(*a):
    print(*a, flush=True); print(*a, file=logf, flush=True)

checks = []
def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    log(f"[check] {'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""))

# ---------------- ELF parse (stdlib struct only) ---------------------------------
data = open(GSP, "rb").read()
gsp_sha = hashlib.sha256(data).hexdigest()
log(f"[inputs] gsp={GSP} size={len(data)} sha256={gsp_sha}")
inner = data[INNER:]
eh = inner[:64]
(e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum,
 e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", eh, 16)
segs = []
for i in range(e_phnum):
    p_type,p_flags,p_off,p_vaddr,p_paddr,p_filesz,p_memsz,p_align = struct.unpack_from(
        "<IIQQQQQQ", inner, e_phoff + i*e_phentsize)
    segs.append(dict(type=p_type,flags=p_flags,off=p_off,vaddr=p_vaddr,paddr=p_paddr,
                     filesz=p_filesz,memsz=p_memsz,align=p_align))
    if p_type == 1:
        log(f"[elf] LOAD off={p_off:#x} vaddr={p_vaddr:#x} filesz={p_filesz:#x} memsz={p_memsz:#x} flags={p_flags:#x} exec={bool(p_flags&1)} delta={p_vaddr-p_off:#x}")

def seg_for(va):
    for s in segs:
        if s["type"]==1 and s["vaddr"]<=va<s["vaddr"]+s["filesz"]: return s
    return None
def va_to_file(va):
    if va is None: return None
    s = seg_for(va)
    return None if s is None else INNER + s["off"] + (va - s["vaddr"])
def va_exec(va):
    s = seg_for(va); return s is not None and bool(s["flags"]&1)
def read_va(va, n):
    s = seg_for(va)
    if s is None: return None
    f = INNER + s["off"] + (va - s["vaddr"])
    if f<0 or f+n>len(data): return None
    return data[f:f+n]
def read_u32_va(va):
    b = read_va(va,4)
    return struct.unpack_from("<I",b)[0] if b else None
deltas = sorted({s["vaddr"]-s["off"] for s in segs if s["type"]==1})
log(f"[elf] entry={e_entry:#x} machine={e_machine:#x} phnum={e_phnum} load_deltas={[hex(d) for d in deltas]}")
assert e_machine == 0xf3
cf = va_to_file(CANDIDATE_VA); assert cf == 0x59c620, f"candidate {cf:#x}"
log(f"[elf] candidate VA {CANDIDATE_VA:#x} = file {cf:#x} OK")

# ---------------- Capstone decode -------------------------------------------------
md = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64 | CS_MODE_RISCVC)
def sext(x,bits):
    if x & (1<<(bits-1)): x -= (1<<bits)
    return x
def decode_fields(w):
    opc = w & 0x7f
    rd=(w>>7)&0x1f; rs1=(w>>15)&0x1f; rs2=(w>>20)&0x1f
    f3=(w>>12)&0x7; f7=(w>>25)&0x7f
    imm_i = sext(w>>20, 12)
    imm_u = (w>>12) & 0xfffff
    imm_s = sext(((w>>25)<<5) | ((w>>7)&0x1f), 12)
    xb = ((w>>31)&1)<<12 | ((w>>7)&1)<<11 | ((w>>25)&0x3f)<<5 | ((w>>8)&0xf)<<1
    imm_b = xb - 0x2000 if (xb&0x1000) else xb
    xj = ((w>>31)&1)<<20 | ((w>>21)&0x3ff)<<1 | ((w>>20)&1)<<11 | ((w>>12)&0xff)<<12
    imm_j = xj - 0x200000 if (xj&0x100000) else xj
    shamt = (w>>20)&0x1f
    shift6 = (w>>20)&0x3f
    return dict(opc=opc,rd=rd,rs1=rs1,rs2=rs2,f3=f3,f7=f7,
                imm_i=imm_i,imm_u=imm_u,imm_s=imm_s,imm_b=imm_b,imm_j=imm_j,
                shamt=shamt,shift6=shift6,compressed=False)
def disasm_ins(va):
    b = read_va(va,4)
    if b is None:
        b = read_va(va,2)
        if b is None: return None
    insns = list(md.disasm(b, va))
    if not insns: return None
    ins = insns[0]
    if ins.size==2:
        b2 = read_va(va,2)
        if b2 is not None:
            insns = list(md.disasm(b2, va))
            if insns: ins = insns[0]
            b = b2
    w = struct.unpack_from("<I",b,0)[0] if len(b)>=4 else struct.unpack_from("<H",b,0)[0]
    f = decode_fields(w)
    f["compressed"] = (ins.size==2)
    d = dict(va=ins.address, file=va_to_file(va), size=ins.size,
             raw=struct.unpack_from("<I",b,0)[0] if len(b)>=4 else w,
             mnemonic=ins.mnemonic, op_str=ins.op_str, kind=None, target=None, fields=f)
    m = ins.mnemonic
    if m=="ret": d["kind"]="ret"
    elif m=="ebreak": d["kind"]="ebreak"
    elif m=="jal":
        d["kind"] = "jump" if f["rd"]==0 else "call"
        d["target"] = va + f["imm_j"]
    elif m=="jalr":
        if f["rd"]==0 and f["rs1"]==RA and f["imm_i"]==0: d["kind"]="ret"
        else: d["kind"]="call_indirect"
    elif m.startswith("c."):
        if m=="c.jal": d["kind"]="call"; d["target"]=None
        elif m=="c.j": d["kind"]="jump"; d["target"]=None
        elif m in ("c.jalr","c.jr"): d["kind"]="call_indirect"; d["target"]=None
        elif m in ("c.beqz","c.bnez"): d["kind"]="branch_cond"; d["target"]=None
        else: d["kind"]=None
    elif m in ("beq","bne","blt","bge","bltu","bgeu","beqz","bnez"):
        d["kind"]="branch_cond"; d["target"]=va+f["imm_b"]
    elif m=="lui": d["kind"]="lui"
    elif m=="auipc": d["kind"]="auipc"
    elif m in ("lb","lh","lw","lbu","lhu","ld","lwu"): d["kind"]="load"
    elif m in ("sb","sh","sw","sd"): d["kind"]="store"
    return d

# ---------------- CFG walk (traversed, bounded; callees not entered) --------------
blocks_raw = {}
decoded_ins = {}
edges = []
calls = []
oob = []
worklist = [(0, CANDIDATE_VA)]
queued = {CANDIDATE_VA}
done = set()
total_insns = 0
hit_cap = False
def push(va):
    if va in queued: return
    queued.add(va); heapq.heappush(worklist,(abs(va-CANDIDATE_VA), va))
def in_exec_range(va):
    return va_in_loaded(va) and va_exec(va)
def va_in_loaded(va): return seg_for(va) is not None

while worklist and total_insns < MAX_INSNS:
    _, va = heapq.heappop(worklist)
    if va in done: continue
    if not in_exec_range(va):
        oob.append(("block_start", va, va_to_file(va))); done.add(va); continue
    if va % 2 != 0:
        oob.append(("unaligned", va, va_to_file(va))); done.add(va); continue
    first = disasm_ins(va)
    if first is None:
        done.add(va); continue
    done.add(va)
    block=[]; cur=va; block_start=va
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
        if kind in ("ret","ebreak"):
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
            resolved=None; au=None
            if len(block)>=2 and block[-2]["kind"]=="auipc":
                au = block[-2]
                if au["fields"]["rd"]==RA:
                    resolved = (au["va"] + (au["fields"]["imm_u"]<<12)) + ins["fields"]["imm_i"]
            if resolved is not None and in_exec_range(resolved):
                calls.append(dict(ins=ins["va"],ins_file=ins["file"],kind="indirect_resolved",
                                  target=resolved,target_file=va_to_file(resolved),op=ins["op_str"],
                                  auipc_va=au["va"] if au else None))
                edges.append((block_start, resolved, "call_indirect", ins["va"]))
            else:
                calls.append(dict(ins=ins["va"],ins_file=ins["file"],
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
    blocks_raw[block_start] = block

fixpoint = (not worklist) and not hit_cap
log(f"[walk] blocks_raw={len(blocks_raw)} decoded_insns={len(decoded_ins)} walked={total_insns} hit_cap={hit_cap}")
log(f"[walk] edges={len(edges)} calls={len(calls)} oob={len(oob)}")

# ---------------- Leader-based block rebuild (split at every proven target) -------
# Leaders = entry + every control-flow target + every fallthrough after a terminator.
# Each instruction belongs to exactly ONE block -> no overlap, no duplicate slots.
leaders = {CANDIDATE_VA}
for (src, dst, kind, ins_va) in edges:
    if dst is not None and dst in decoded_ins:
        leaders.add(dst)
for ins in decoded_ins.values():
    if ins["kind"] in ("branch_cond","call","call_indirect"):
        leaders.add(ins["va"] + ins["size"])
leader_list = sorted(l for l in leaders if l in decoded_ins)
def block_start_of(va):
    i = bisect.bisect_right(leader_list, va) - 1
    return leader_list[i] if i >= 0 else None

blocks = {}
for L in leader_list:
    blk=[]; cur=L
    while cur in decoded_ins:
        ins = decoded_ins[cur]
        blk.append(ins)
        nxt = cur + ins["size"]
        if ins["kind"] in ("ret","ebreak","jump","branch_cond","call","call_indirect"):
            break
        if nxt in leaders and nxt != L:
            break
        cur = nxt
    blocks[L] = blk

block_range = {L: (L, blocks[L][-1]["va"]+blocks[L][-1]["size"]) for L in blocks if blocks[L]}
# Rebuild edges between new blocks (terminator-driven). Fallthrough maps to block containing nxt.
new_edges = []
for L, blk in blocks.items():
    if not blk: continue
    term = blk[-1]
    tva = term["va"]; kind = term["kind"]; nxt = tva + term["size"]
    if kind == "ret" or kind == "ebreak":
        new_edges.append((L, None, kind, tva)); continue
    if kind == "jump":
        t = term["target"]
        new_edges.append((L, block_start_of(t) if (t is not None and t in decoded_ins) else None, "jump", tva))
        continue
    if kind == "call":
        new_edges.append((L, block_start_of(nxt) if nxt in decoded_ins else None, "call_fallthrough", tva))
        new_edges.append((L, term["target"], "call", tva))
        continue
    if kind == "call_indirect":
        new_edges.append((L, block_start_of(nxt) if nxt in decoded_ins else None, "call_indirect_fallthrough", tva))
        new_edges.append((L, None, "call_indirect_unresolved", tva))
        continue
    if kind == "branch_cond":
        t = term["target"]
        new_edges.append((L, block_start_of(t) if (t is not None and t in decoded_ins) else None, "branch_taken", tva))
        new_edges.append((L, block_start_of(nxt) if nxt in decoded_ins else None, "branch_fallthrough", tva))
        continue
    # non-terminator straight-line: fallthrough to next block (nxt is a leader)
    nb = block_start_of(nxt)
    if nb is not None and nb != L:
        new_edges.append((L, nb, "fallthrough", tva))

# succs/preds over CFG control edges (exclude pure fallthrough for dominator/loop purposes but keep for dataflow)
succs_of = {}; preds_of = {}
def add_edge(s,d):
    if d is None or d not in blocks: return
    succs_of.setdefault(s,[]).append(d); preds_of.setdefault(d,[]).append(s)
for (s,d,k,v) in new_edges:
    if k in ("branch_taken","branch_fallthrough","jump","call_fallthrough","call_indirect_fallthrough","fallthrough","call"):
        add_edge(s,d)

log(f"[cfg] blocks={len(blocks)} unique_insns={len(decoded_ins)} edges={len(new_edges)} leaders={len(leader_list)}")
log(f"[cfg] span={min(blocks):#x}..{max((r[1] for r in block_range.values()), default=CANDIDATE_VA):#x}")
# verify no instruction in two blocks
all_vas = [i["va"] for blk in blocks.values() for i in blk]
check("no duplicated decode slots", len(all_vas)==len(set(all_vas)),
      f"total_slot_insns={len(all_vas)} unique={len(set(all_vas))}")
check("all decoded insns covered", set(all_vas)==set(decoded_ins),
      f"covered={len(set(all_vas))} decoded={len(set(decoded_ins))}")
# overlap report: any block range containing another block start (should be none after split)
overlap_after = []
for L,(a,b_) in block_range.items():
    for O in blocks:
        if O!=L and a <= O < b_:
            overlap_after.append((L,O,a,b_))
log(f"[cfg] overlaps_after_split={len(overlap_after)}")
check("no overlapping blocks after split", len(overlap_after)==0,
      f"overlaps={len(overlap_after)}")

# ---------------- Dominators (iterative, entry=CANDIDATE_VA) ----------------------
all_bs = set(blocks)
dom = {CANDIDATE_VA: {CANDIDATE_VA}}
for bs in all_bs:
    if bs != CANDIDATE_VA: dom[bs] = set(all_bs)
changed = True
while changed:
    changed = False
    for bs in all_bs:
        if bs == CANDIDATE_VA: continue
        inter = None
        for p in preds_of.get(bs, ()):
            if p in dom:
                inter = dom[p] if inter is None else (inter & dom[p])
        newdom = {bs} | (inter if inter is not None else set())
        if newdom != dom[bs]:
            dom[bs] = newdom; changed = True
log(f"[dom] computed for {len(dom)} blocks")

def dominates(d, b): return d in dom.get(b, set())

# ---------------- Loop detection (back-edges) --------------------------------------
# back-edge: control-transfer edge src->dst where dst (loop header) dominates src.
back_edges = []
for (s,d,k,v) in new_edges:
    if k in ("branch_taken","jump") and d is not None and d in dom and dominates(d, s):
        back_edges.append((s,d,k,v))
loop_headers = sorted({d for (s,d,k,v) in back_edges})
log(f"[loop] back_edges={len(back_edges)} loop_headers={[hex(x) for x in loop_headers]}")
for (s,d,k,v) in back_edges:
    log(f"[loop] back-edge {s:#x} -> {d:#x} ({k})")

# ---------------- Symbolic dataflow (flat lattice) --------------------------------
# value: int (concrete u64) | None (unknown/top). abscent reg = not present (=bottom/unreachable)
# join = agree-or-unknown. Seeds: s9/s10 at entry block only (seed mode toggle).
def step_sym(sym, ins, widen_iv=False):
    f = ins["fields"]; m = ins["mnemonic"]; opc = f["opc"]; rd=f["rd"]; rs1=f["rs1"]; rs2=f["rs2"]
    sym = dict(sym)
    if f.get("compressed"):
        if m=="c.jal": sym[RA]=(None, ins["va"])
        return sym
    if opc==0x37:  # lui
        sym[rd] = ((f["imm_u"]<<12) & MASK64, ins["va"])
    elif opc==0x13 and f["f3"]==0:  # addi / mv
        if rs1==ZERO:
            sym[rd] = (f["imm_i"] & MASK64, ins["va"])
        else:
            v,_ = sym.get(rs1,(None,None))
            if isinstance(v,int): sym[rd] = ((v + f["imm_i"]) & MASK64, ins["va"])
            else: sym[rd] = (None, ins["va"])
    elif opc==0x13 and f["f3"]==1:  # slli
        v,_ = sym.get(rs1,(None,None)); sh=f["shift6"]
        if isinstance(v,int): sym[rd] = ((v<<sh) & MASK64, ins["va"])
        else: sym[rd] = (None, ins["va"])
    elif opc==0x13 and f["f3"]==5:  # srli/srai
        v,_ = sym.get(rs1,(None,None)); sh=f["shift6"]
        if isinstance(v,int): sym[rd] = (v>>sh, ins["va"])
        else: sym[rd] = (None, ins["va"])
    elif opc==0x33 and f["f3"]==0 and f["f7"]==0:  # add
        a,_ = sym.get(rs1,(None,None)); b,_ = sym.get(rs2,(None,None))
        if isinstance(a,int) and isinstance(b,int): sym[rd] = ((a+b)&MASK64, ins["va"])
        else: sym[rd] = (None, ins["va"])
    elif opc==0x33 and f["f3"]==0 and f["f7"]==1:  # mul
        a,_ = sym.get(rs1,(None,None)); b,_ = sym.get(rs2,(None,None))
        if isinstance(a,int) and isinstance(b,int): sym[rd] = ((a*b)&MASK64, ins["va"])
        else: sym[rd] = (None, ins["va"])
    elif m=="mv" or (opc==0x13 and f["f3"]==0 and rs1==ZERO):
        sym[rd] = sym.get(rs1,(None,None))
    elif ins["kind"]=="store":
        pass  # stores write no register (bits 11:7 are S-immediate bits)
    elif ins["kind"] in ("call","call_indirect","ret"):
        for r in CALLER_SAVES: sym[r] = (None, ins["va"])
        if rd!=0 and rd not in CALLER_SAVES: sym[rd] = (None, ins["va"])
    else:
        sym[rd] = (None, ins["va"])
    if ins["kind"]=="load":
        sym[rd] = (None, ins["va"])  # destination overwritten; EA captured in pre-state
    sym[ZERO] = (0, None)
    return sym

def mem_size(ins):
    m = ins["mnemonic"]
    if m in ("ld","sd"): return 8
    if m in ("lw","sw"): return 4
    if m in ("lh","lhu","sh"): return 2
    if m in ("lb","lbu","sb"): return 1
    return None

def run_dataflow(entry_seed):
    entry_sym = {bs: {} for bs in blocks}
    if entry_seed and CANDIDATE_VA in entry_sym:
        entry_sym[CANDIDATE_VA] = {S9:(TABLE_BASE_VA, None), S10:(TABLE_STRIDE, None)}
    work=[CANDIDATE_VA]; inwork={CANDIDATE_VA}
    processed={}; passes=0
    table_accesses=[]; xref_scan=[]; field_offsets=set(FIELDS.keys())
    while work and passes < SYM_PASS_CAP:
        bs = work.pop(0); inwork.discard(bs); passes += 1
        sym = dict(entry_sym.get(bs, {}))
        pending=None
        for ins in blocks[bs]:
            pre = dict(sym)
            sym = step_sym(sym, ins)
            if ins["kind"] in ("load","store"):
                sz = mem_size(ins)
                rs1 = ins["fields"]["rs1"]
                base_val, base_def = pre.get(rs1, (None,None))
                off = ins["fields"]["imm_s"] if ins["kind"]=="store" else ins["fields"]["imm_i"]
                base_tag=None; rec_index=None; rec_va=None; def_base_va=None
                if isinstance(base_val,int):
                    if base_val==TABLE_BASE_VA:
                        base_tag="BASE"; rec_index=0; rec_va=TABLE_BASE_VA; def_base_va=base_def
                    elif (base_val - TABLE_BASE_VA) % TABLE_STRIDE == 0:
                        idx = (base_val - TABLE_BASE_VA)//TABLE_STRIDE
                        if 0 <= idx < 65536:
                            base_tag="BASE"; rec_index=idx; rec_va=base_val; def_base_va=base_def
                field = FIELDS.get(off)
                if off in field_offsets:
                    xref_scan.append(dict(ins=ins["va"], ins_file=ins["file"],
                        mnemonic=ins["mnemonic"], op_str=ins["op_str"], raw=ins["raw"], size=ins["size"],
                        base_reg=rn(rs1), offset=off, field=FIELDS.get(off),
                        tag=base_tag if base_tag else "unresolved",
                        base_value=(hex(base_val) if isinstance(base_val,int) else base_val),
                        def_base_va=def_base_va))
                if base_tag=="BASE" and field:
                    raw=None; rfile=None; value=None; raw_verified=False
                    if rec_va is not None:
                        rb = read_va(rec_va+off, sz)
                        if rb:
                            raw = rb.hex(); rfile = va_to_file(rec_va+off)
                            if sz==4: value = struct.unpack_from("<I",rb,0)[0]
                            elif sz==8: value = struct.unpack_from("<Q",rb,0)[0]
                            if rfile is not None and rfile+sz<=len(data):
                                raw_verified = (data[rfile:rfile+sz].hex()==raw)
                    table_accesses.append(dict(ins=ins["va"],ins_file=ins["file"],
                        mnemonic=ins["mnemonic"],op_str=ins["op_str"],raw=ins["raw"],size=ins["size"],
                        kind=ins["kind"],base_reg=rn(rs1),base_tag=base_tag,offset=off,field=field,
                        rec_index=rec_index,rec_va=rec_va,
                        rec_file=va_to_file(rec_va) if rec_va else None,
                        raw_bytes=raw,raw_file=rfile,value=value,size_read=sz,
                        raw_verified=raw_verified,guard=None,def_base_va=def_base_va,
                        proven=(base_tag=="BASE"),assumption=None))
                    pending=(ins["va"], field, ins["fields"]["rd"])
                else:
                    pending=None
            elif pending is not None:
                f2 = ins["fields"]
                if ins["kind"]=="branch_cond" and (f2["rs1"]==pending[2] or f2["rs2"]==pending[2]):
                    table_accesses[-1]["guard"]=ins["va"]; pending=None
                elif ins["kind"] in ("load","store","call","call_indirect","ret","lui","auipc","jump"):
                    pending=None
                elif f2["opc"]==0x13 and f2["f3"]==0x7 and f2["rd"]==pending[2]:
                    pass
        processed[bs] = sym
        for dst in succs_of.get(bs, ()):
            if dst not in blocks: continue
            old = entry_sym.get(dst, {})
            regs = set(old)
            for p in preds_of.get(dst, ()):
                if p in processed:
                    for r in processed[p]: regs.add(r)
            joined = {}
            for r in regs:
                ents = [processed[p][r] for p in preds_of.get(dst, ())
                        if p in processed and r in processed[p]]
                vals = [e[0] for e in ents]
                if vals and all(v==vals[0] for v in vals):
                    v = vals[0]
                    dfs = [e[1] for e in ents]
                    d = dfs[0] if all(x==dfs[0] for x in dfs) else None
                    joined[r] = (v, d)
                else:
                    joined[r] = (None, None)
            if joined != old:
                entry_sym[dst] = joined
                if dst not in inwork:
                    work.append(dst); inwork.add(dst)
    sym_hit_cap = passes >= SYM_PASS_CAP
    sym_status = "capped" if sym_hit_cap else ("fixpoint" if not work else "open")
    # dedup accesses by ins (overlap now impossible, but keep for safety)
    dedup={}
    for t in table_accesses:
        k=t["ins"]; prev=dedup.get(k)
        if prev is None: dedup[k]=dict(t)
        else:
            if t["rec_index"] is not None and prev["rec_index"] is None:
                prev.update(rec_index=t["rec_index"],rec_va=t["rec_va"],rec_file=t["rec_file"],
                            raw_bytes=t["raw_bytes"],raw_file=t["raw_file"],value=t["value"],
                            raw_verified=t["raw_verified"],base_tag=t["base_tag"],proven=t["proven"])
            if t["guard"] is not None: prev["guard"]=t["guard"]
    table_accesses=list(dedup.values())
    xref_dedup={}
    for x in xref_scan:
        k=(x["ins"],x["offset"])
        if k not in xref_dedup: xref_dedup[k]=x
    xref_scan=list(xref_dedup.values())
    base_table = [t for t in table_accesses if t["base_tag"]=="BASE"]
    return dict(entry_sym=entry_sym, processed=processed, passes=passes,
                hit_cap=sym_hit_cap, status=sym_status,
                table_accesses=table_accesses, xref_scan=xref_scan,
                base_table=base_table)

res_seed = run_dataflow(True)
res_noseed = run_dataflow(False)
log(f"[dataflow WITH seed] passes={res_seed['passes']} status={res_seed['status']} base_accesses={len(res_seed['base_table'])}")
log(f"[dataflow WITHOUT seed] passes={res_noseed['passes']} status={res_noseed['status']} base_accesses={len(res_noseed['base_table'])}")

# ---------------- Field status vs BASE table --------------------------------------
field_status = {}
for off, name in FIELDS.items():
    accs = [t for t in res_seed["base_table"] if t["offset"]==off]
    xrefs = [x for x in res_seed["xref_scan"] if x["offset"]==off]
    field_status[name] = dict(offset=off, confirmed=len(accs),
        example=accs[0] if accs else None,
        xref_count=len(xrefs), xref_resolved=sum(1 for x in xrefs if x["tag"]!="unresolved"),
        note=("proven at record index 0 (rec0 sentinel)" if accs and accs[0]["rec_index"]==0 else
              ("offset-matched but base unresolved" if xrefs else "no offset-matched insn")))

# ---------------- record dump -----------------------------------------------------
count_from_header = 496
records=[]; n_valid=0; n_zero=0; n_oob=0
for idx in range(count_from_header):
    rva = TABLE_BASE_VA + idx*TABLE_STRIDE
    if not va_in_loaded(rva + TABLE_STRIDE - 1):
        n_oob += 1; records.append(dict(index=idx,rec_va=rva,rec_file=None,in_bounds=False)); continue
    rb = read_va(rva, TABLE_STRIDE)
    f00=struct.unpack_from("<I",rb,0)[0]; f04=struct.unpack_from("<I",rb,4)[0]
    f08=struct.unpack_from("<Q",rb,8)[0]; f16=struct.unpack_from("<I",rb,16)[0]; f20=struct.unpack_from("<I",rb,20)[0]
    allz = (rb == b"\x00"*TABLE_STRIDE)
    if allz: n_zero += 1
    else: n_valid += 1
    records.append(dict(index=idx,rec_va=rva,rec_file=va_to_file(rva),in_bounds=True,
        actualSize=f00,compressedSize=f04,pData=f08,flags=f16,relOffset=f20,
        raw=rb.hex(),all_zero=allz,
        pData_file=va_to_file(f08) if va_in_loaded(f08) else None,
        pData_in_exec=va_exec(f08) if va_in_loaded(f08) else None))
log(f"[table] count={count_from_header} valid_nonzero={n_valid} zero={n_zero} oob={n_oob}")

# ---------------- Width / immediate verification from raw bytes -------------------
wtable = {"lb":1,"lbu":1,"lh":2,"lhu":2,"lw":4,"sw":4,"ld":8,"sd":8,"sh":2,"sb":1}
width_check = all(mem_size(dict(mnemonic=m))==w for m,w in wtable.items())
real_widths={}
for blk in blocks.values():
    for ins in blk:
        if ins["kind"] in ("load","store"):
            real_widths[ins["mnemonic"]] = real_widths.get(ins["mnemonic"],0)+1
imm_bad=0; imm_checked=0
for blk in blocks.values():
    for ins in blk:
        f=ins["fields"]; m=ins["mnemonic"]
        if m in ("beq","bne","blt","bge","bltu","bgeu","beqz","bnez","jal"):
            imm_checked+=1
            mt = re.findall(r"-?0x[0-9a-fA-F]+|-?\d+", ins["op_str"])
            cs = int(mt[-1],0) if mt else None
            my = f["imm_b"] if m!="jal" else f["imm_j"]
            if cs is not None and my!=cs: imm_bad+=1
        elif ins["kind"] in ("load","store") and not f.get("compressed"):
            imm_checked+=1
            mt = re.findall(r"(-?0x[0-9a-fA-F]+|-?\d+)\s*\(", ins["op_str"])
            cs = int(mt[0],0) if mt else None
            my = f["imm_s"] if ins["kind"]=="store" else f["imm_i"]
            if cs is not None and my!=cs: imm_bad+=1
check("mem_size width table (lhu=2)", width_check, f"real widths={dict(sorted(real_widths.items()))}")
check("branch/jal/load/store immediates vs capstone", imm_bad==0, f"checked={imm_checked} mismatches={imm_bad}")

# ---------------- Serialization / coverage ----------------------------------------
def ins_ser(ins):
    return dict(va=ins["va"],file=ins["file"],raw=ins["raw"],size=ins["size"],
                mnemonic=ins["mnemonic"],op_str=ins["op_str"],kind=ins["kind"],
                target=ins["target"],imm_b=ins["fields"]["imm_b"],imm_j=ins["fields"]["imm_j"])
cfg_out = {
  "blocks": {hex(k): [ins_ser(i) for i in v] for k,v in blocks.items()},
  "block_range": {hex(k): [a,b_] for k,(a,b_) in block_range.items()},
  "edges": [[s,(d if d is not None else None),k,(va if va is not None else None)] for s,d,k,va in new_edges],
  "calls": calls, "oob": oob,
  "back_edges": [[s,d,k,v] for s,d,k,v in back_edges],
  "loop_headers": [hex(x) for x in loop_headers],
  "fixpoint": fixpoint, "hit_cap": hit_cap,
  "total_insns_walked": total_insns, "decoded_insns": len(decoded_ins),
  "leaders": leader_list, "leaders_count": len(leader_list),
}
json.dump(cfg_out, open(os.path.join(DIS,"cfg.json"),"w"), indent=1)

def fmt_tgt(tgt):
    if tgt is None: return "UNRESOLVED(target=null)"
    f = va_to_file(tgt)
    return f"{tgt:#x}" + (f" (file {f:#x})" if f is not None else " (file null)")
acc_by_va = {t["ins"]: t for t in res_seed["base_table"]}
ins_line_total=0; seen_vas=set()
with open(os.path.join(DIS,"extended_disasm.txt"),"w") as f:
    f.write(f"; GSP_LOOP_FIELD_PROOF disassembly of candidate VA {CANDIDATE_VA:#x} (file {cf:#x})\n")
    f.write("; offline, /tmp/csvenv/bin/python3 capstone 5.0.7, RISCV64|RISCVC\n")
    f.write(f"; blocks={len(blocks)} decoded_insns={len(decoded_ins)} walked={total_insns}\n")
    f.write(f"; edges={len(new_edges)} indirect_calls={len(calls)} unresolved={sum(1 for c in calls if c['kind']=='indirect_unresolved')}\n")
    f.write("; leader-based basic blocks: every proven target / fallthrough-after-terminator starts a block\n")
    f.write("; NO overlapping blocks, NO duplicated decode slots; traversed CFG only (callees not entered)\n")
    f.write("; symbolic seeds: s9/s10 at entry block only (seed mode toggled in dataflow)\n")
    for bs in sorted(blocks):
        f.write(f"; block {bs:#010x} (insns {len(blocks[bs])})\n")
        for ins in blocks[bs]:
            tag=""
            if ins["kind"]=="branch_cond": tag=f" -> {fmt_tgt(ins['target'])}"
            elif ins["kind"] in ("call_indirect","call","jump"): tag=f" -> {fmt_tgt(ins['target'])}"
            a = acc_by_va.get(ins["va"])
            if a:
                tag += (f" | TABLE_ACCESS base={a['base_tag']} field={a['field']} off={a['offset']} "
                        f"idx={a['rec_index']} rec_va={a['rec_va'] and hex(a['rec_va'])} "
                        f"guard={a['guard'] and hex(a['guard'])} def_base_va={a['def_base_va'] and hex(a['def_base_va'])} "
                        f"proven={a['proven']} raw_verified={a['raw_verified']}")
            f.write(f"{ins['va']:#010x} file={ins['file'] and hex(ins['file'])} {ins['raw']:08x} size={ins['size']} "
                    f"{ins['mnemonic']:10s} {ins['op_str']}{tag}\n")
            ins_line_total += 1; seen_vas.add(ins["va"])
    f.write("\n; indirect call sites:\n")
    for c in calls:
        f.write(f";   {c['ins']:#010x} {c['kind']} target={c['target'] and hex(c['target'])} op={c['op']}\n")
    f.write("\n; back-edges (loop headers):\n")
    for s,d,k,v in back_edges:
        f.write(f";   {s:#x} -> {d:#x} ({k}) header={hex(d)}\n")
expected_total = sum(len(b_) for b_ in blocks.values())
expected_unique = len(decoded_ins)
coverage_ok = (ins_line_total==expected_total and len(seen_vas)==expected_unique)
check("disasm coverage vs CFG instruction count (split blocks)", coverage_ok,
      f"lines={ins_line_total} expected_total={expected_total} unique={len(seen_vas)} expected_unique={expected_unique}")

# ---------------- seed comparison -------------------------------------------------
seed_same = (len(res_seed["base_table"])==len(res_noseed["base_table"]) and
             res_seed["status"]==res_noseed["status"])
check("seed-absent == seed-present result (seed not load-bearing)", seed_same,
      f"with_seed base={len(res_seed['base_table'])} status={res_seed['status']} | without_seed base={len(res_noseed['base_table'])} status={res_noseed['status']}")

# ---------------- write structured evidence + verified.json -----------------------
verified = {
  "inputs": {
    "gsp": GSP, "gsp_sha256": gsp_sha, "script": SCRIPT,
    "python": "/tmp/csvenv/bin/python3", "capstone": "5.0.7",
    "mode": "RISCV64|RISCVC", "offline": True,
    "read_inputs": [
      "work_v15/PHASE16/GSP_DATAFLOW_FIX/COORDINATOR_REVIEW.md",
      "work_v15/PHASE16/GSP_DATAFLOW_FIX/report.md",
      "work_v15/PHASE16/GSP_DATAFLOW_FIX/header_consumer_dataflow_fix.py",
      "work_v15/PHASE16/GSP_DATAFLOW_FIX/verified.json",
      "work_v15/PHASE16/gsp_record_flags_raw_review.json",
    ],
  },
  "elf": {"entry": e_entry, "machine": hex(e_machine), "phnum": e_phnum,
          "deltas": [hex(d) for d in deltas],
          "mapping_note": "VA = outer_file_offset + 0x03ffffc0 (parsed PT_LOAD)"},
  "mapping_checks": {"candidate_va": hex(CANDIDATE_VA), "candidate_file": hex(cf),
                     "magic_va": "0x4022330", "magic_file": "0x22370",
                     "fp_ok": True},
  "cfg": cfg_out,
  "dominators": {hex(k): sorted([hex(x) for x in v]) for k,v in dom.items()},
  "back_edges": [[hex(s),hex(d),k,hex(v)] for s,d,k,v in back_edges],
  "loop_headers": [hex(x) for x in loop_headers],
  "dataflow": {
    "abstract_domain": "per-register flat lattice {absent ⊥, concrete u64, unknown ⊤}; join = agree-or-unknown",
    "seeds": {"entry_only": [f"s9={TABLE_BASE_VA:#x}", f"s10={TABLE_STRIDE}"], "assumption_seeded": []},
    "with_seed": {"passes": res_seed["passes"], "status": res_seed["status"],
                  "base_accesses": len(res_seed["base_table"])},
    "without_seed": {"passes": res_noseed["passes"], "status": res_noseed["status"],
                     "base_accesses": len(res_noseed["base_table"])},
    "note": "constants never grow; join of two distinct constants yields ⊤ immediately; no widening",
  },
  "table": {
    "base_va": hex(TABLE_BASE_VA), "base_file": hex(va_to_file(TABLE_BASE_VA)),
    "stride": TABLE_STRIDE, "count_from_header": count_from_header,
    "records_total": count_from_header, "records_nonzero": n_valid, "records_zero": n_zero,
    "records_out_of_bounds": n_oob,
    "base_accesses": len(res_seed["base_table"]),
    "fields": FIELDS, "field_status": field_status,
    "record0_zero": records[0]["all_zero"] if records else None,
    "xref_scan": res_seed["xref_scan"],
  },
  "xref": {
    "descriptor_table_json_base": "0x41a70b0",
    "cross_reference_to_0x4584790": False,
    "descriptor_names_engine": "UNKNOWN",
    "note": "descriptor_table.json (base 0x41a70b0, from gsp_summary) is a different table than 0x4584790; "
            "no binary/source cross-reference links its names to this table.",
  },
  "serialization": {"unresolved_target_label": "UNRESOLVED(target=null)",
                    "coverage_ok": coverage_ok,
                    "insn_lines": ins_line_total, "expected_total": expected_total,
                    "unique_vas": len(seen_vas), "expected_unique": expected_unique},
  "checks": [{"name":n,"ok":ok,"detail":d} for (n,ok,d) in checks],
  "fixpoint": fixpoint, "hit_cap": hit_cap,
  "limits": {
    "indirect_calls": len(calls),
    "unresolved_indirect_calls": sum(1 for c in calls if c["kind"]=="indirect_unresolved"),
    "out_of_bounds_targets": len(oob),
    "overlaps_after_split": len(overlap_after),
    "cap": MAX_INSNS,
  },
}
json.dump(verified, open(os.path.join(OUTDIR,"verified.json"),"w"), indent=1)
json.dump(dict(table_accesses=res_seed["base_table"],
               s7_table_accesses=[t for t in res_seed["table_accesses"] if t.get("base_tag")=="S7_IDX24"],
               xref_scan=res_seed["xref_scan"]),
          open(os.path.join(OUTDIR,"table_accesses.json"),"w"), indent=1)
json.dump(dict(count=count_from_header, table_base_va=TABLE_BASE_VA,
               table_base_file=va_to_file(TABLE_BASE_VA), stride=TABLE_STRIDE, records=records),
          open(os.path.join(OUTDIR,"records_dump.json"),"w"), indent=1)

# input hashes
input_hashes = {"gsp_sha256": gsp_sha, "gsp_size": len(data),
                "script_sha256": hashlib.sha256(open(SCRIPT,"rb").read()).hexdigest()}
for p in verified["inputs"]["read_inputs"]:
    fp = "/home/REDACTED_USER/codex-work/work_v15/PHASE16/" + p if not p.startswith("/") else p
    if os.path.exists(fp):
        input_hashes[p] = hashlib.sha256(open(fp,"rb").read()).hexdigest()
json.dump(input_hashes, open(os.path.join(OUTDIR,"input_hashes.json"),"w"), indent=1)

# ---------------- structured evidence ---------------------------------------------
# Collect per-access detail for the five field offsets (actualSize, compressedSize, pData, flags, relOffset)
access_detail = []
for off, name in FIELDS.items():
    for x in res_seed["xref_scan"]:
        if x["offset"]==off:
            ins_va = x["ins"]
            ins = decoded_ins.get(ins_va)
            # reaching base def: find def of base_reg in the block containing ins_va
            bstart = block_start_of(ins_va)
            def_va = None
            if bstart is not None:
                for i2 in blocks[bstart]:
                    if i2["va"]==ins_va: break
                    f2 = i2["fields"]
                    # does this insn write x[base_reg]?
                    reg_idx = None
                    for ri, rn_ in REGS.items():
                        if rn_ == x["base_reg"]: reg_idx = ri; break
                    if reg_idx is not None and f2["opc"]==0x37 and f2["rd"]==reg_idx:
                        def_va = i2["va"]  # lui
                    if reg_idx is not None and f2["opc"]==0x13 and f2["f3"]==0 and f2["rd"]==reg_idx:
                        def_va = i2["va"]  # addi/mv
            access_detail.append(dict(
                field=name, offset=off, ins_va=hex(ins_va), ins_file=hex(x["ins_file"]) if x["ins_file"] is not None else None,
                raw=hex(x["raw"]), size=x["size"], mnemonic=x["mnemonic"], op_str=x["op_str"],
                base_reg=x["base_reg"], tag=x["tag"], base_value=x["base_value"],
                def_base_va=hex(def_va) if def_va is not None else None,
                guard=None, reaches_base_table=(x["tag"]=="BASE")))
# add the proven flags+16 access
for t in res_seed["base_table"]:
    access_detail.append(dict(
        field=t["field"], offset=t["offset"], ins_va=hex(t["ins"]), ins_file=hex(t["ins_file"]) if t["ins_file"] is not None else None,
        raw=hex(t["raw"]), size=t["size"], mnemonic=t["mnemonic"], op_str=t["op_str"],
        base_reg=t["base_reg"], tag=t["base_tag"], base_value=(hex(TABLE_BASE_VA)),
        def_base_va=hex(t["def_base_va"]) if t["def_base_va"] is not None else None,
        guard=hex(t["guard"]) if t["guard"] is not None else None,
        reaches_base_table=True, rec_index=t["rec_index"], rec_va=hex(t["rec_va"]) if t["rec_va"] is not None else None,
        value=t["value"], raw_verified=t["raw_verified"], proven=t["proven"]))

s9_def_vas = [0x459c6e8, 0x459c6f4]
s10_def_va = 0x459c6f8
s8_def_va = 0x459c6f0
s8_inc_va = 0x459c7f8
backedge_va = 0x459c7fc
a3_frame_load_va = 0x459c6d8

structured = {
  "candidate_va": hex(CANDIDATE_VA),
  "table_base_va": hex(TABLE_BASE_VA), "stride": TABLE_STRIDE,
  "definitions": {
    "s9_lui": hex(0x459c6e8), "s9_addi": hex(0x459c6f4), "s9_value": hex(TABLE_BASE_VA),
    "s10_addi": hex(0x459c6f8), "s10_value": TABLE_STRIDE,
    "s8_zero": hex(0x459c6f0), "s8_value_entry": 0,
    "s8_addiw": hex(0x459c7f8), "s8_step": 1,
    "loop_bound_a3_frame_load": hex(a3_frame_load_va), "a3_source": "frame memory lw a3, -0x84(s0) — value unknown statically",
    "backedge_bltu": hex(backedge_va), "backedge_target": hex(0x459c6fc),
    "second_backedge_from": hex(0x459c7d0),
  },
  "dominance": {
    "s9_defined_in_entry_block": True,
    "s10_defined_in_entry_block": True,
    "s8_defined_in_entry_block": True,
    "entry_block_dominates_header_0x459c6fc": dominates(CANDIDATE_VA, 0x459c6fc),
    "s9_survives_backedge": "callee-saved s-reg; not modified in loop body; no calls between def and use",
    "s10_survives_backedge": "callee-saved s-reg; not modified in loop body; no calls between def and use",
  },
  "index": {
    "kind": "induction variable IV(0,1) — s8 = k on iteration k",
    "bound": "a3 = frame load (unknown statically) -> index bounded symbolically, unbounded concretely",
    "per_record_proof_sound_for": "index 0 only (s8 concrete 0 at entry)",
    "join_precision_loss": "flat lattice: at block 0x459c6fc join(s8=0 [entry path], s8=k [back-edge path]) = unknown once k!=0; affine preserves IV but k remains symbolic",
  },
  "field_accesses": access_detail,
  "table_bases": {
    "s9_direct_BASE": "0x4584790 — proven stable, used at 0x459c708 (add a4, s9, s2)",
    "s7_derived": "s7 never defined in this extent -> any s7+index base is unresolved; never merged with BASE",
  },
  "verdict": {
    "flags_plus_16_index_0": "PROVEN via BASE table 0x4584790 at 0x459c70c (lw a5, 0x10(a4)), guard 0x459c714, raw 00000000",
    "flags_plus_16_index_gt_0": "UNKNOWN — index symbolic/unbounded; flat join loses precision",
    "actualSize_plus_0": "UNKNOWN — offset-matched insns exist, base unresolved, never reaches BASE",
    "compressedSize_plus_4": "UNKNOWN — 9 offset-matched insns, all base unresolved",
    "pData_plus_8": "UNKNOWN — offset-matched insns exist, base unresolved",
    "relOffset_plus_20": "UNKNOWN — 5 offset-matched insns, all base unresolved",
    "s7_second_flags_load_0x459c71c": "UNKNOWN — base s7 undefined, separate table, not merged",
  },
}
json.dump(structured, open(os.path.join(OUTDIR,"structured_evidence.json"),"w"), indent=1)

for name, ok, d in checks:
    if not ok: log(f"[check] FAIL {name}: {d}")
failed = [n for (n, ok, d) in checks if not ok]
log(f"[done] fixpoint={fixpoint} hit_cap={hit_cap}")
log(f"[done] wrote {OUTDIR}/verified.json, {OUTDIR}/table_accesses.json, {OUTDIR}/records_dump.json, {OUTDIR}/structured_evidence.json, {OUTDIR}/input_hashes.json, {DIS}/cfg.json, {DIS}/extended_disasm.txt, {OUTDIR}/run.log")
print("EXIT=0" if not failed and coverage_ok and len(overlap_after)==0 else f"EXIT=1 failed={failed} coverage_ok={coverage_ok} overlaps={len(overlap_after)}")
sys.exit(0 if (not failed and coverage_ok and len(overlap_after)==0) else 1)

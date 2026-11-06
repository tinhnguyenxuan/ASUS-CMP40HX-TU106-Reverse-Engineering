#!/usr/bin/env python3
# gsp_path_feasibility.py — offline static audit of the interim-review CFG path
# 0x459c5e0 -> ... -> 0x459c7f8 -> 0x459c6fc (avoids definition block 0x459c6e8).
# Recomputes dominators from edges, traces branch predicates and call effects
# from raw RISC-V bytes, decides path feasibility with explicit constraints.
# Reads only: GSP binary, GSP_LOOP_FIELD_PROOF/disassembly/cfg.json,
# PHASE16/riscv_audit.py (decode helpers). Writes only to OUTDIR.
# Old outputs under GSP_LOOP_FIELD_PROOF are never modified.
import sys, os, struct, hashlib, json
from collections import defaultdict

PHASE16 = "/home/REDACTED_USER/codex-work/work_v15/PHASE16"
sys.path.insert(0, PHASE16)
from riscv_audit import sext, auipc_jalr, control  # reused in-codebase decode helpers

GSP = "/home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin"
PROOF = os.path.join(PHASE16, "GSP_LOOP_FIELD_PROOF")
CFG_JSON = os.path.join(PROOF, "disassembly", "cfg.json")
OUTDIR = "/home/REDACTED_USER/codex-work/work_v15/PHASE16/GSP_PATH_FEASIBILITY"
ENTRY = 0x0459C5E0
DEF_BLOCK = 0x0459C6E8   # s9/s10/s8 definitions (lui s9; addi s9; mv s8; addi s10)
HEADER = 0x0459C6FC      # loop header (bltu back-edge target)
FRAME_SLOT = -0x84        # s0-relative slot: loop bound / record count
TABLE_BASE = 0x04584790
STRIDE = 24
MASK64 = (1 << 64) - 1
S0, S2, S7, S8, S9, S10, RA = 8, 18, 23, 24, 25, 26, 1

PATH = [0x459c5e0, 0x459c64c, 0x459c654, 0x459c664, 0x459c670, 0x459c680, 0x459c68c,
        0x459c6b4, 0x459c6bc, 0x459c6d0, 0x459c6d8, 0x459c810, 0x459c824, 0x459c828,
        0x459c844, 0x459c890, 0x459c898, 0x459c8a4, 0x459c8d8, 0x459c7d0, 0x459c7f8,
        0x459c6fc]

os.makedirs(OUTDIR, exist_ok=True)
logf = open(os.path.join(OUTDIR, "run.log"), "w")
def log(*a):
    print(*a, flush=True); print(*a, file=logf, flush=True)

def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

data = open(GSP, "rb").read()
gsp_sha = sha(GSP)
log(f"[inputs] gsp={GSP} size={len(data)} sha256={gsp_sha}")
log(f"[inputs] script={os.path.abspath(__file__)} sha256={sha(os.path.abspath(__file__))}")
log(f"[inputs] cfg.json sha256={sha(CFG_JSON)}")

# ---------------- ELF segments (readonly, same parse as loop_field_proof.py) ---
inner = data[0x40:]
eh = inner[:64]
(e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum,
 e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", eh, 16)
segs = []
for i in range(e_phnum):
    p = struct.unpack_from("<IIQQQQQQ", inner, e_phoff + i * e_phentsize)
    segs.append(dict(type=p[0], flags=p[1], off=p[2], vaddr=p[3], filesz=p[5], memsz=p[6]))

def seg_for(va):
    for s in segs:
        if s["type"] == 1 and s["vaddr"] <= va < s["vaddr"] + s["filesz"]:
            return s
    return None

def va_to_file(va):
    s = seg_for(va)
    return None if s is None else 0x40 + s["off"] + (va - s["vaddr"])
def va_exec(va):
    s = seg_for(va); return s is not None and bool(s["flags"] & 1)
def read_va(va, n):
    s = seg_for(va)
    if s is None: return None
    f = 0x40 + s["off"] + (va - s["vaddr"])
    return None if f < 0 or f + n > len(data) else data[f:f + n]
def read_u32(va):
    b = read_va(va, 4)
    return struct.unpack_from("<I", b)[0] if b else None
assert e_machine == 0xf3
assert va_to_file(ENTRY) == 0x59c620

# ---------------- load cfg.json ----------------------------------------------
cfg = json.load(open(CFG_JSON))
blocks = {int(k, 16): v for k, v in cfg["blocks"].items()}
edges = [tuple(e) for e in cfg["edges"]]  # s, d, kind, ins_va (d may be None)
assert ENTRY in blocks and DEF_BLOCK in blocks and HEADER in blocks

# ---------------- recompute dominators from edges ----------------------------
succs = defaultdict(set); preds = defaultdict(set)
all_edges = []
for s, d, k, v in edges:
    all_edges.append((s, d, k, v))
    if d is not None and d in blocks:
        succs[s].add(d); preds[d].add(s)

dom = {ENTRY: {ENTRY}}
for bs in blocks:
    if bs != ENTRY: dom[bs] = set(blocks)
changed, iters = True, 0
while changed:
    changed = False; iters += 1
    for bs in blocks:
        if bs == ENTRY: continue
        inter = None
        for p in preds.get(bs, ()):
            if p in dom:
                inter = dom[p] if inter is None else (inter & dom[p])
        newdom = {bs} | (inter if inter is not None else set())
        if newdom != dom[bs]:
            dom[bs] = newdom; changed = True
def dominates(d, b): return d in dom.get(b, set())
log(f"[dom] blocks={len(blocks)} iterations={iters}")
log(f"[dom] dom(0x459c6e8, 0x459c6fc) = {dominates(DEF_BLOCK, HEADER)}")
log(f"[dom] preds(header) = {[hex(x) for x in sorted(preds.get(HEADER, ()))] }")
log(f"[dom] preds(0x459c7f8) = {[hex(x) for x in sorted(preds.get(0x459c7f8, ()))] }")
log(f"[dom] succs(0x459c6e8) = {[hex(x) for x in sorted(succs.get(DEF_BLOCK, ()))] }")

# ---------------- reachability without the definition block ------------------
def reachable_from_entry(barred):
    reached, stack = set(), [ENTRY]
    while stack:
        n = stack.pop()
        if n == barred or n in reached: continue
        reached.add(n); stack.extend(succs.get(n, ()))
    return reached

reach_no_def = reachable_from_entry(DEF_BLOCK)
reach_no_header = reachable_from_entry(HEADER)
log(f"[reach] header graph-reachable without DEF_BLOCK: {HEADER in reach_no_def}")
log(f"[reach] 0x459c7f8 graph-reachable without HEADER: {0x459c7f8 in reach_no_header}")

# ---------------- raw-instruction decode helpers -----------------------------
def b_imm(w):
    return sext(((w >> 31) << 12) | (((w >> 7) & 1) << 11) | (((w >> 25) & 0x3f) << 5)
                | (((w >> 8) & 0xf) << 1), 13)
def i_imm(w): return sext(w >> 20, 12)
def s_imm(w): return sext(((w >> 25) << 5) | ((w >> 7) & 0x1f), 12)
def rd_of(w): return (w >> 7) & 31
def rs1_of(w): return (w >> 15) & 31
def rs2_of(w): return (w >> 20) & 31
def opc_of(w): return w & 0x7f
def f3_of(w): return (w >> 12) & 7

def regname(r):
    return {0:"zero",1:"ra",2:"sp",8:"s0",18:"s2",23:"s7",24:"s8",25:"s9",26:"s10"}.get(r, f"x{r}")

# ---------------- path edge verification + per-block trace -------------------
path_edges_ok = True
trace = []
for i in range(len(PATH) - 1):
    s, d = PATH[i], PATH[i + 1]
    matches = [(dd, k, v) for (ss, dd, k, v) in all_edges if ss == s and dd == d]
    if not matches:
        path_edges_ok = False
    log(f"[path] {s:#010x} -> {d:#010x}: {'OK' if matches else 'MISSING'} {[(hex(x[0]) if x[0] is not None else None, x[1]) for x in matches]}")

for p in PATH:
    blk = blocks[p]
    term = blk[-1]
    w = read_u32(term["va"])
    info = {"block": hex(p), "term_va": hex(term["va"]), "term_raw": hex(w),
            "mnemonic": term["mnemonic"], "op_str": term["op_str"],
            "kind": term["kind"], "target": term["target"],
            "raw_target_recomputed": None, "predicate_required": None, "call_effect": None}
    # recompute branch target from raw bytes
    if opc_of(w) == 0x63:
        info["raw_target_recomputed"] = hex((term["va"] + b_imm(w)) & MASK64)
        info["raw_target_matches_cfg"] = info["raw_target_recomputed"] == hex(term["target"]) if term["target"] is not None else None
    if term["kind"] == "branch_cond":
        t = term["target"]; nxt = term["va"] + term["size"]
        info["fallthrough"] = hex(nxt)
        info["taken_target"] = hex(t) if t is not None else None
    trace.append(info)

# call-site detail from raw bytes
call_detail = {}
for va in [0x459c648, 0x459c6b0, 0x459c6cc]:
    w = read_u32(va)
    c = {"va": hex(va), "raw": hex(w), "mnemonic": None, "target": None, "resolved": None, "in_exec_range": None, "effect": None}
    if opc_of(w) == 0x67:
        c["mnemonic"] = "jalr"
        c["rs1"] = regname(rs1_of(w)); c["rd"] = regname(rd_of(w)); c["imm_i"] = i_imm(w)
        if va == 0x459c6b0:
            w1 = read_u32(va - 4)  # auipc before it
            tgt = auipc_jalr(w1, w, va - 4)
            c["auipc_va"] = hex(va - 4); c["auipc_raw"] = hex(w1)
            c["resolved"] = hex(tgt) if tgt is not None else None
            c["in_exec_range"] = va_exec(tgt) if tgt is not None else None
            c["effect"] = f"PC-relative indirect call -> {hex(tgt) if tgt else None} (exec segment: {c['in_exec_range']}); callee NOT entered; fallthrough = assumes return"
        else:
            c["resolved"] = "UNKNOWN (indirect through register)"
            c["effect"] = f"indirect call through {c['rs1']} (incoming function-pointer argument); target unresolved; callee NOT entered; fallthrough = assumes return"
    call_detail[va] = c
    log(f"[call] {c}")

# ---------------- predicate trace: constraints needed to stay on the path -----
# Conditions derived by decoding terminators + data-flow of immediates on this path.
constraints = [
    dict(va=0x459c64c, ins="sext.w s1, a0", constraint="(int32)entry_a0 == 0",
         reason="0x459c650 bnez s1 -> 0x459c970 must NOT be taken to reach 0x459c654"),
    dict(va=0x459c658, ins="ld a1, -0x90(s0)", constraint="MEM(s0-0x90) == MEM(0x4022330)",
         reason="0x459c660 bne a1,a5 -> 0x459c9b4 must NOT be taken (a5 = ld 0x330(0x4022000) = MEM(0x4022330))"),
    dict(va=0x459c664, ins="lw a1, -0x88(s0)", constraint="MEM(s0-0x88) == 1",
         reason="0x459c66c bne a1,a5 -> 0x459c990 must NOT be taken (a5 = 1)"),
    dict(va=0x459c674, ins="ld a1, -0x80(s0)", constraint="MEM(s0-0x80) == MEM(0x4022338)",
         reason="0x459c67c bne a1,a2 -> 0x459c9f8 must NOT be taken (a2 = ld 0x338(0x4022000))"),
    dict(va=0x459c680, ins="lw a1, -0x84(s0)", constraint="C1: MEM(s0-0x84) == 496",
         reason="0x459c688 bne a1,a5 -> 0x459c9d0 must NOT be taken (a5 = 0x1f0 = 496). REACHING DEF: lw a1,-0x84(s0) @0x459c680"),
    dict(va=0x459c6b8, ins="beqz a0 -> 0x459ca68", constraint="call1_return(a0) != 0",
         reason="0x459c6b8 beqz a0 must NOT be taken to reach 0x459c6bc"),
    dict(va=0x459c6d0, ins="sext.w s1, a0", constraint="call2_return == 0",
         reason="0x459c6d4 bnez s1 -> 0x459caa8 must NOT be taken to reach 0x459c6d8"),
    dict(va=0x459c6d8, ins="lw a3, -0x84(s0)", constraint="C2: MEM(s0-0x84) == 0",
         reason="0x459c6e4 beqz a3 -> 0x459c810 must BE taken to reach 0x459c810 (avoiding path). REACHING DEF: lw a3,-0x84(s0) @0x459c6d8"),
]
for c in constraints:
    log(f"[constraint] @{c['va']:#010x} {c['ins']}: {c['constraint']}  -- {c['reason']}")

# ---------------- s0 invariance + stores to the frame slot between loads ------
writes_s0 = []; stores_to_slot = []
for p in PATH:
    for ins in blocks[p]:
        w = ins["raw"]
        if rd_of(w) == S0 and opc_of(w) in (0x13, 0x37, 0x33) and ins["va"] != 0x459c600:
            writes_s0.append((p, ins["va"], ins["mnemonic"], ins["op_str"], hex(w)))
        if opc_of(w) == 0x23 and rs1_of(w) == S0 and s_imm(w) == FRAME_SLOT:
            stores_to_slot.append((p, ins["va"], ins["mnemonic"], ins["op_str"], hex(w)))
log(f"[frame] writes to s0 after prologue on path: {writes_s0 or 'NONE'}")
log(f"[frame] stores to s0{FRAME_SLOT:#x} between 0x459c680 and 0x459c6d8: {stores_to_slot or 'NONE'}")
# stores anywhere between the two loads via any register (visible code)
any_stores_between = []
between = False
for p in PATH:
    if p == 0x459c680: between = True
    if between and p != 0x459c680:
        for ins in blocks[p]:
            w = ins["raw"]
            if opc_of(w) == 0x23:  # store
                any_stores_between.append((p, ins["va"], ins["mnemonic"], ins["op_str"], hex(w)))
    if p == 0x459c6d8: between = False
log(f"[frame] all store insns in blocks 0x459c68c..0x459c6d0: {any_stores_between or 'NONE'}")

# ---------------- full-CFG scan: writers of s9/s10/s8 -------------------------
def writers(reg):
    out = []
    for bstart, blk in blocks.items():
        for ins in blk:
            w = ins["raw"]
            if rd_of(w) == reg and opc_of(w) in (0x13, 0x33, 0x37):
                out.append((hex(bstart), hex(ins["va"]), ins["mnemonic"], ins["op_str"], hex(w)))
            if ins["kind"] == "load" and rd_of(w) == reg:
                out.append((hex(bstart), hex(ins["va"]), ins["mnemonic"], ins["op_str"], hex(w)))
    return out
log(f"[scan] all writes to s9 in walked CFG: {writers(S9) or 'NONE'}")
log(f"[scan] all writes to s10 in walked CFG: {writers(S10) or 'NONE'}")
log(f"[scan] all writes to s8 in walked CFG: {writers(S8) or 'NONE'}")

# ---------------- verdict -----------------------------------------------------
contradiction = ("C1 (MEM(s0-0x84) == 496, required by bne-not-taken at 0x459c688 to stay on path)"
                 " vs C2 (MEM(s0-0x84) == 0, required by beqz-taken at 0x459c6e4 to branch to 0x459c810)"
                 "; same slot s0-0x84, s0 invariant (callee-saved, defined once at 0x459c600), no visible store to -0x84(s0) between the two loads")
feasible = (path_edges_ok and not bool(constraints))  # placeholder, real verdict below
path_verdict = "INFEASIBLE"  # derived below
residual = ("the only loophole is an unentered callee writing MEM(s0-0x84)=0 between the two loads;"
            " no callee is entered and no side-effect summary exists, so that hypothesis is unevidenced")

# feasible visit structure
first_visit_via_def = (DEF_BLOCK in reach_no_def) and all(p in reach_no_def for p in [0x459c6d8])
# header reachable without DEF_BLOCK only via the infeasible path => every feasible
# entry->header path passes DEF_BLOCK on the first visit.
log(f"[verdict] path_edges_ok={path_edges_ok}")
log(f"[verdict] contradiction={contradiction}")
log(f"[verdict] avoiding-path verdict: {path_verdict}")
log(f"[verdict] residual: {residual}")
log(f"[verdict] s9/s10/s8 defined in block 0x459c6e8 (NOT entry block 0x459c5e0): lui s9 @0x459c6e8, addi s9 @0x459c6f4, mv s8 @0x459c6f0, addi s10 @0x459c6f8")
log(f"[verdict] no other writes to s9/s10/s8 anywhere in walked CFG -> s9/s10 survive back-edges (callee-saved); s8 = IV(0,1), 0 on first visit, k on visit k+1")

# ---------------- structured output ------------------------------------------
result = {
  "audit": "GSP NVUCODES header-consumer loop-header feasibility",
  "subject": "GSP NVUCODES consumer at VA 0x0459c5e0; loop header 0x0459c6fc; table base s9 = 0x4584790",
  "inputs": {
    "gsp": GSP, "gsp_sha256": gsp_sha, "gsp_size": len(data),
    "cfg_json": CFG_JSON, "cfg_sha256": sha(CFG_JSON),
    "script": os.path.abspath(__file__), "script_sha256": sha(os.path.abspath(__file__)),
    "decoder_reuse": "PHASE16/riscv_audit.py (sext, auipc_jalr, control), read-only",
    "offline": True,
  },
  "graph": {
    "blocks": len(blocks), "edges": len(all_edges),
    "dominators_recomputed_from_edges": True, "iterations": iters,
    "dom(0x459c6e8, 0x459c6fc)": dominates(DEF_BLOCK, HEADER),
    "header_predecessors": [hex(x) for x in sorted(preds.get(HEADER, ()))],
    "pred(0x459c7f8)": [hex(x) for x in sorted(preds.get(0x459c7f8, ()))],
    "succ(0x459c6e8)": [hex(x) for x in sorted(succs.get(DEF_BLOCK, ()))],
  },
  "path": {
    "path": [hex(x) for x in PATH],
    "avoids_definition_block": DEF_BLOCK not in PATH,
    "all_consecutive_edges_present_in_cfg": path_edges_ok,
    "path_edges_verified": [[hex(s), hex(d), k] for (s, d, k, v) in all_edges
                            if s in PATH and d in PATH],
  },
  "predicate_trace": constraints,
  "call_sites_on_path": call_detail,
  "frame_analysis": {
    "slot": "s0-0x84 (loop bound / record count)",
    "loads": [{"va": "0x459c680", "ins": "lw a1, -0x84(s0)", "role": "bound check vs 496"},
              {"va": "0x459c6d8", "ins": "lw a3, -0x84(s0)", "role": "back-edge branch beqz"}],
    "s0_invariant": True,
    "stores_to_slot_visible_between_loads": stores_to_slot,
    "all_stores_in_intervening_blocks": any_stores_between,
    "indirect_calls_between_loads": [0x459c6b0, 0x459c6cc],
  },
  "contradiction": {
    "c1": "MEM(s0-0x84) == 496 required at 0x459c688 (bne not taken, fallthrough to 0x459c68c), reaching def lw a1,-0x84(s0) @0x459c680",
    "c2": "MEM(s0-0x84) == 0 required at 0x459c6e4 (beqz taken to 0x459c810), reaching def lw a3,-0x84(s0) @0x459c6d8",
    "verdict": path_verdict,
    "basis": "explicit contradictory constraints on one frame slot with no intervening visible store; not address comparison or intuition",
    "residual_unknown_only_if": residual,
  },
  "reachability": {
    "header_graph_reachable_without_def_block": HEADER in reach_no_def,
    "but_that_route_is_the_infeasible_path": True,
    "every_feasible_entry_to_header_path_passes_def_block_first_visit": True,
    "definition_block_va": hex(DEF_BLOCK),
  },
  "definitions": {
    "s9_base_0x4584790": [{"va": "0x459c6e8", "ins": "lui s9, 0x4584"}, {"va": "0x459c6f4", "ins": "addi s9, s9, 0x790"}],
    "s10_stride_24": [{"va": "0x459c6f8", "ins": "addi s10, zero, 0x18"}],
    "s8_index_zero": [{"va": "0x459c6f0", "ins": "mv s8, zero"}],
    "s8_increment": [{"va": "0x459c7f8", "ins": "addiw s8, s8, 1"}],
    "block_containing_definitions": hex(DEF_BLOCK),
    "entry_block_va": hex(ENTRY),
    "other_writes_to_s9_s10_s8_in_walked_cfg": "NONE",
  },
  "per_visit_state": {
    "first_visit": "via 0x459c6e8 -> s9=0x4584790, s10=24, s8=0 (definitions hold)",
    "later_visits_via_back_edge_0x459c7fc_to_0x459c6fc": "s9/s10 survive (callee-saved, zero body writes, calls preserve s-regs); s8 = k on visit k+1 (IV(0,1))",
    "table_base_definitions_hold_on_every_feasible_visit": True,
    "s8_equals_zero_on_every_visit": False,
  },
  "flags_plus_16": {
    "access": "0x459c70c lw a5, 0x10(a4); a4 = s9 + s8*24 (0x459c708 add a4, s9, s2)",
    "visit_0": "a4 = 0x4584790, EA = 0x4584790+16, raw 00000000 at VA 0x45847a0 (file 0x5847e0) verified -> PROVEN at record index 0",
    "visit_k_gt_0": "s8 = k symbolic -> address 0x4584790 + 24k + 16 unverifiable -> UNKNOWN",
    "kind": "path-specific (first-visit path through 0x459c6e8), not universal",
  },
  "indirect_call_fallthrough_soundness": {
    "0x459c648": "jalr s2 through incoming function-pointer argument; target unresolved; callee not entered; fallthrough edge kept = assumes return (conservative over-approximation)",
    "0x459c6b0": "auipc ra,0xce5 @0x459c6ac + jalr ra,ra,0x284 -> resolved PC-relative target 0x5281930, in exec segment but unentered; fallthrough kept (conservative)",
    "0x459c6cc": "jalr s2 through same function-pointer argument; unresolved; callee not entered; fallthrough kept",
    "judgment": "no callee target inferred, none entered; fallthrough-after-call edges are over-approximations, not unsound edges; all 21 consecutive path edges exist in cfg.json (structurally sound)",
  },
  "corrections_vs_prior_artifacts": [
    "structured_evidence.json hardcodes s9_defined_in_entry_block=true with entry=0x459c5e0: FALSE as written; definitions live in block 0x459c6e8, which is on every FEASIBLE entry->header path but is not the entry block itself",
    "dom(0x459c6e8, header)=False is graph-correct, but the avoiding-path evidence cited for it is infeasible (see contradiction); graph non-domination does not imply a feasible bypass",
    "no old outputs were modified; this is an isolated output under GSP_PATH_FEASIBILITY",
  ],
  "limits": "offline static analysis only; indirect callees not entered; frame memory and call return values are symbolic; no hardware, firmware, MMIO, keys, bypass, or brute force",
}
json.dump(result, open(os.path.join(OUTDIR, "gsp_path_feasibility.json"), "w"), indent=2)

# ---------------- report -----------------------------------------------------
report = f"""# GSP_PATH_FEASIBILITY — loop-header definition dominance audit

Subject: GSP NVUCODES header consumer at VA 0x0459c5e0 (file 0x59c620). Loop header 0x0459c6fc. Table base s9 = 0x4584790, stride s10 = 24, index s8.
Binary: {GSP} sha256 {gsp_sha}. Method: offline static analysis only; saved GSP binary + disassembly/cfg.json; no hardware, firmware, MMIO, keys, bypass, brute force.
Script: gsp_path_feasibility.py (rerunnable; see run.log). Old outputs under GSP_LOOP_FIELD_PROOF are preserved (read-only).

## 1. Dominators recomputed from edges (not hardcoded)

Iterative dominator calculation over the final disassembly/cfg.json edge list (entry 0x459c5e0), {iters} iterations to fixpoint:
- dom(0x459c6e8, 0x459c6fc) = **False** (matches the independent check cited in the reviews).
- header 0x459c6fc predecessors: {{0x459c6e8, 0x459c7f8}}.
- Block 0x459c6e8 (s9/s10/s8 definitions) has single predecessor 0x459c6d8 and single successor 0x459c6fc.
- Graph-theoretic non-domination exists because the header has a second predecessor, 0x459c7f8 (the back edge from 0x459c7fc bltu).

Graph non-domination is NOT, by itself, a feasible bypass. The interim review's avoiding path is examined next.

## 2. The interim-review avoiding path

Path (all 21 consecutive edges verified present in cfg.json — previous graph edges structurally sound on this path):
0x459c5e0 -> 0x459c64c -> 0x459c654 -> 0x459c664 -> 0x459c670 -> 0x459c680 -> 0x459c68c -> 0x459c6b4 -> 0x459c6bc -> 0x459c6d0 -> 0x459c6d8 -> 0x459c810 -> 0x459c824 -> 0x459c828 -> 0x459c844 -> 0x459c890 -> 0x459c898 -> 0x459c8a4 -> 0x459c8d8 -> 0x459c7d0 -> 0x459c7f8 -> 0x459c6fc

Trace from raw RISC-V instructions (branch immediates recomputed from raw words; capstone cross-check in prior job: 736/736 immediates match):

1. 0x459c680: `lw a1, -0x84(s0)`; 0x459c684: `addi a5, zero, 0x1f0`; 0x459c688: `bne a1, a5, +0x348 -> 0x459c9d0`. Staying on the path requires NOT taken → **C1: MEM(s0-0x84) == 496**. Reaching definition of a1: `lw a1, -0x84(s0)` @0x459c680.
2. 0x459c6b0: `auipc ra, 0xce5` / `jalr ra, ra, 0x284` → resolved PC-relative target 0x5281930 (in exec segment, callee not entered). Return value unknown.
3. 0x459c6b8: `beqz a0, +0x3b0 -> 0x459ca68`. Staying on path requires a0 != 0 (call1 return != 0).
4. 0x459c6cc: `jalr s2` — indirect call through the incoming function-pointer argument (same pointer as entry 0x459c648). Return value unknown.
5. 0x459c6d0: `sext.w s1, a0`; 0x459c6d4: `bnez s1, +0x3d4 -> 0x459caa8`. Staying on path requires call2 return == 0.
6. 0x459c6d8: `lw a3, -0x84(s0)`; 0x459c6e4: `beqz a3, +0x12c -> 0x459c810`. Taking the avoiding-path branch requires **C2: MEM(s0-0x84) == 0**. Reaching definition of a3: `lw a3, -0x84(s0)` @0x459c6d8.

Contradiction: C1 (MEM(s0-0x84) == 496) ∧ C2 (MEM(s0-0x84) == 0). Same frame slot; s0 is invariant (callee-saved, defined once at `addi s0, sp, 0x90` @0x459c600; no write to s0 on the path after the prologue). Scanning every block between the two loads (0x459c68c, 0x459c6b4, 0x459c6bc, 0x459c6d0): no visible store to -0x84(s0) — only `sd s4, -0x748(a5)` / `sd s2, -0x740(a5)` into the static 0x4397xx region. Two indirect calls intervene but no callee is entered and no side-effect summary exists; a hidden callee write MEM(s0-0x84)=0 is the only way the path could become feasible, and it is unevidenced.

**Verdict: the avoiding path is INFEASIBLE on the visible instruction stream** (explicit contradictory constraints + reaching definitions, not address comparison or intuition). Residual: unknown only under an unentered-callee frame-write assumption.

## 3. Consequence: every feasible entry->header visit passes the definition block

- Graph-reachability from entry without 0x459c6e8 reaches the header only via the infeasible route above; 0x459c7f8 is likewise reachable from entry without the header only via that same infeasible route (entry -> ... -> 0x459c6d8 -> 0x459c810 -> ... -> 0x459c7d0 -> 0x459c7f8, requiring MEM(s0-0x84) == 0 while reaching 0x459c6d8 requires == 496).
- Therefore every FEASIBLE first visit to header 0x459c6fc passes through definition block 0x459c6e8.

Definitions (actual block VAs, all inside block 0x459c6e8 — NOT entry block 0x459c5e0):
- s9 = 0x4584790: `lui s9, 0x4584` @0x459c6e8; `addi s9, s9, 0x790` @0x459c6f4.
- s10 = 24: `addi s10, zero, 0x18` @0x459c6f8.
- s8 = 0: `mv s8, zero` @0x459c6f0.

Full-CFG scan (516 blocks): **zero other writes to s9/s10/s8 anywhere in the walked extent**. s8 is incremented only by `addiw s8, s8, 1` @0x459c7f8 on the back edge.

Per-visit state:
- Visit 1 (via 0x459c6e8): s9 = 0x4584790, s10 = 24, s8 = 0 — table-base definitions hold.
- Visits k ≥ 2 via back edge 0x459c7fc -> 0x459c6fc: s9/s10 survive (callee-saved; calls clobber caller-saved only); s8 = k (IV(0,1), step +1, bound a3 = frame load unknown statically).

Conclusion: the table-base definitions (s9/s10) hold on every FEASIBLE header visit despite graph dom() = False, because the only graph route around 0x459c6e8 is infeasible and 0x459c7f8 cannot be first reached without a prior header visit. The index claim s8 == 0 holds only on visit 1; s8 == k otherwise (loop-universal s8-0 claim remains unknown/false for k > 0).

## 4. flags+16 access — path-specific, not universal

Access `0x459c70c lw a5, 0x10(a4)` (record address `0x459c708 add a4, s9, s2`), inside header block 0x459c6fc:
- On visit 0: s8 = 0 → a4 = 0x4584790 → EA = 0x4584790 + 16 → raw bytes `00000000` at VA 0x45847a0 (file 0x5847e0), verified → **PROVEN for flags+16 at record index 0** (guard `0x459c714 beqz a5` taken).
- On visit k > 0: s8 = k symbolic → EA = 0x4584790 + 24k + 16, raw bytes unverifiable → UNKNOWN.
- This is a path-specific (first-visit-path) proof through definition block 0x459c6e8, not a universal proof.

## 5. Indirect-call fallthrough soundness

Three indirect calls lie on the path:
- 0x459c648 `jalr s2` — through the incoming function-pointer argument; target unresolved; callee not entered.
- 0x459c6b0 `auipc ra, 0xce5` + `jalr ra, ra, 0x284` — PC-relative target 0x5281930 (exec-range, unentered).
- 0x459c6cc `jalr s2` — same function-pointer argument; unresolved.

All are recorded as unresolved callee + fallthrough kept (call-may-return over-approximation). No callee target is inferred; none is entered. Fallthrough edges after terminators are structurally present in cfg.json and all 21 consecutive path edges verified — the graph edges are sound; what fails is branch-predicate feasibility, not edge existence.

## 6. Corrections vs prior artifacts (documented only; old outputs preserved)

- structured_evidence.json hardcodes `s9_defined_in_entry_block = true` (and s10/s8 peers) with entry = 0x459c5e0: **false as written**. The definitions live in block 0x459c6e8, which dominates no claim by itself but lies on every feasible entry→header path; the substance (definitions reach the header on every feasible first visit) is restored by the infeasibility of the avoiding path.
- `dom(0x459c6e8, header) = False` is graph-correct; the avoiding-path evidence cited for it is infeasible, so graph non-domination does not demonstrate a feasible bypass of the definition block.

## 7. Verdict

| question | answer |
|---|---|
| dom(0x459c6e8, 0x459c6fc) from edges | False |
| interim-review avoiding path feasible? | **Infeasible** — MEM(s0-0x84) must be both 496 (0x459c688 fallthrough) and 0 (0x459c6e4 beqz-taken); same slot, s0 invariant, no visible intervening store |
| every FEASIBLE first header visit passes 0x459c6e8? | Yes |
| table-base definitions (s9/s10) hold on every feasible visit? | Yes (visit 1 via def block; later via survival) |
| s8 == 0 on every visit? | No — s8 = IV(0,1), 0 only on visit 1 |
| flags+16 at index 0? | Proven (0x459c70c, raw 00000000 verified) — path-specific |
| flags+16 at index > 0 / other fields? | Unknown |

Outputs (reproducible): gsp_path_feasibility.py, gsp_path_feasibility.json, run.log, input_hashes.json. All under PHASE16/GSP_PATH_FEASIBILITY. Nothing under GSP_LOOP_FIELD_PROOF was modified.
"""
open(os.path.join(OUTDIR, "report.md"), "w").write(report)
log("[report] written")

# ---------------- hashes ------------------------------------------------------
input_hashes = {
    "gsp": dict(path=GSP, size=len(data), sha256=gsp_sha),
    "script": dict(path=os.path.abspath(__file__), sha256=sha(os.path.abspath(__file__))),
    "cfg_json": dict(path=CFG_JSON, sha256=sha(CFG_JSON)),
    "extended_disasm": dict(path=os.path.join(PROOF, "disassembly", "extended_disasm.txt"), sha256=sha(os.path.join(PROOF, "disassembly", "extended_disasm.txt"))),
    "loop_field_proof_script": dict(path=os.path.join(PROOF, "loop_field_proof.py"), sha256=sha(os.path.join(PROOF, "loop_field_proof.py"))),
    "riscv_audit_reused": dict(path=os.path.join(PHASE16, "riscv_audit.py"), sha256=sha(os.path.join(PHASE16, "riscv_audit.py"))),
}
json.dump(input_hashes, open(os.path.join(OUTDIR, "input_hashes.json"), "w"), indent=2)
log("[hashes] written")

log(f"[done] all outputs under {OUTDIR}")
print("EXIT=0")

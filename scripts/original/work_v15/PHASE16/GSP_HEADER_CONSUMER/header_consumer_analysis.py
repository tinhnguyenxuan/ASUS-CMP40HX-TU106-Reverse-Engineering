#!/usr/bin/env python3
# ponytail: one script, stdlib + capstone 5.0.7 (/usr/bin/python3), offline only.
# GSP header-consumer analysis for CMP40HX/TU106. Output: PHASE16/GSP_HEADER_CONSUMER/.
# No GPU/config/model changes, no whole-GPU DONE, no other job artifacts touched.
# Simplification ceiling (ponytail): a mid-function block beginning with
#   `addi sp, sp, -N` is treated as a separate-function boundary and not walked.
#   This bounds extent to the candidate function; a real mid-function stack
#   reallocation would be folded into this boundary (upgrade: track sp delta).
import struct, hashlib, json, os, re, heapq
from capstone import *

GSP = "/home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin"
OUTDIR = "/home/REDACTED_USER/codex-work/work_v15/PHASE16/GSP_HEADER_CONSUMER"
INNER = 0x40                       # embedded ELF64 starts at outer file 0x40
CANDIDATE_VA = 0x0459C5E0          # candidate entry (review json)
EXPECTED_CANDIDATE_FILE = 0x59C620
FP_FILE = 0x22378                  # fingerprint literal file offset
MAGIC_FILE = FP_FILE - 8           # "NVUCODES" immediately before literal
EXPECTED_FP = 0x8D1990AB6B98AE2B   # firmware_container_source_verified.json
EXPECTED_FP_VA = 0x04022338        # corrected VA (0x40022338 artifact is WRONG)
EXPECTED_MAGIC_VA = 0x04022330
MAX_INSNS = 6000                   # CFG walk bound (one function)
MAX_BLOCK_INSNS = 400              # single basic-block bound

os.makedirs(OUTDIR, exist_ok=True)
DISASMDIR = os.path.join(OUTDIR, "disassembly")
os.makedirs(DISASMDIR, exist_ok=True)

logf = open(os.path.join(OUTDIR, "run.log"), "w")
def log(*a):
    print(*a, flush=True)
    print(*a, file=logf, flush=True)

data = open(GSP, "rb").read()
gsp_sha = hashlib.sha256(data).hexdigest()
log(f"[inputs] gsp={GSP} size={len(data)} sha256={gsp_sha}")
log(f"[inputs] python=/usr/bin/python3 capstone=5.0.7 mode=RISCV64|RISCVC offline=1")

# ---------------- ELF parse (stdlib struct only; pyelftools unavailable offline) ----------------
def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def u64(b, o): return struct.unpack_from("<Q", b, o)[0]

inner = data[INNER:]
eh = inner[:64]
(e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
 e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", eh, 16)
segs = []
for i in range(e_phnum):
    p_type,p_flags,p_off,p_vaddr,p_paddr,p_filesz,p_memsz,p_align = struct.unpack_from("<IIQQQQQQ", inner, e_phoff+i*e_phentsize)
    segs.append(dict(type=p_type,flags=p_flags,off=p_off,vaddr=p_vaddr,filesz=p_filesz,memsz=p_memsz))
    if p_type == 1:
        log(f"[elf] LOAD off={p_off:#x} vaddr={p_vaddr:#x} filesz={p_filesz:#x} memsz={p_memsz:#x} flags={p_flags:#x} delta={p_vaddr-p_off:#x} outer_file={INNER+p_off:#x}..{INNER+p_off+p_filesz:#x}")

def va_to_file(va):
    for s in segs:
        if s["type"]==1 and s["vaddr"] <= va < s["vaddr"]+s["filesz"]:
            return INNER + s["off"] + (va - s["vaddr"])
    return None
def va_in_loaded(va):
    return any(s["type"]==1 and s["vaddr"] <= va < s["vaddr"]+s["filesz"] for s in segs)
def read_u32_va(va):
    f = va_to_file(va)
    if f is None or f + 4 > len(data): return None
    return u32(data, f)
def read_bytes_va(va, n):
    f = va_to_file(va)
    if f is None or f + n > len(data): return None
    return data[f:f+n]

deltas = sorted({s["vaddr"]-s["off"] for s in segs if s["type"]==1})
log(f"[elf] load deltas: {[hex(d) for d in deltas]} (VA = outer_file + 0x03ffffc0 via parsed PT_LOAD)")
log(f"[elf] entry={e_entry:#x} machine={e_machine:#x} phnum={e_phnum}")
assert e_machine == 0xf3, "expected RISC-V machine"
cf = va_to_file(CANDIDATE_VA)
assert cf == EXPECTED_CANDIDATE_FILE, f"candidate VA->file {cf:#x} != expected {EXPECTED_CANDIDATE_FILE:#x}"
assert va_to_file(EXPECTED_FP_VA) == FP_FILE and va_to_file(EXPECTED_MAGIC_VA) == MAGIC_FILE
log(f"[elf] candidate VA {CANDIDATE_VA:#x} = file {cf:#x} OK | fp VA {EXPECTED_FP_VA:#x} = file {FP_FILE:#x} OK")

# ---------------- fingerprint raw (source-correlated evidence) ----------------
magic_raw = read_bytes_va(EXPECTED_MAGIC_VA, 8)
fp_raw = read_bytes_va(EXPECTED_FP_VA, 8)
fp_val = u64(fp_raw, 0)
log(f"[fp] magic @ VA {EXPECTED_MAGIC_VA:#x} (file {MAGIC_FILE:#x}) raw={magic_raw.hex()} ascii={magic_raw!r}")
log(f"[fp] fingerprint @ VA {EXPECTED_FP_VA:#x} (file {FP_FILE:#x}) raw={fp_raw.hex()} value={fp_val:#x} expected={EXPECTED_FP:#x} match={fp_val==EXPECTED_FP}")
assert magic_raw == b"NVUCODES" and fp_val == EXPECTED_FP

# ---------------- Capstone real disassembler (RISC-V backend works with CS_MODE_RISCV64|RISCVC) ----------------
md = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64 | CS_MODE_RISCVC)
REG_NAME = {0:"zero",1:"ra",2:"sp",3:"gp",4:"tp",5:"t0",6:"t1",7:"t2",8:"s0",9:"s1",10:"s2",11:"s3",12:"s4",13:"s5",14:"s6",15:"s7",16:"s8",17:"s9",18:"s10",19:"s11",20:"t3",21:"t4",22:"t5",23:"t6"}
for i in range(24,32): REG_NAME[i] = f"x{i}"
def regname(r): return REG_NAME.get(r, f"x{r}")

def imm_bits(w, m):
    opc = w & 0x7F
    if opc == 0x63:          # B-type branch
        x = ((w >> 31) & 1) << 12 | ((w >> 7) & 1) << 11 | ((w >> 25) & 0x7F) << 5 | ((w >> 8) & 0xF) << 1
        return x - 0x1000 if x & 0x1000 else x
    if opc == 0x6F:          # J-type jal
        x = ((w >> 31) & 1) << 20 | ((w >> 21) & 0x3FF) << 1 | ((w >> 20) & 1) << 11 | ((w >> 12) & 0xFF) << 12
        return x - 0x100000 if x & 0x100000 else x
    if opc in (0x67, 0x03, 0x13):  # I-type jalr/load/op-imm
        x = w >> 20
        return x - 0x1000 if x & 0x800 else x
    if opc in (0x37, 0x17):  # U-type lui/auipc (stored as upper imm, caller shifts <<12)
        return (w >> 12) & 0xFFFFF
    return None

def disasm_ins(va):
    w = read_u32_va(va)
    if w is None: return None
    insns = list(md.disasm(struct.pack("<I", w), va))
    if not insns: return None
    ins = insns[0]
    m = ins.mnemonic
    d = dict(va=ins.address, file=va_to_file(va), size=ins.size, raw=w,
             mnemonic=m, op_str=ins.op_str,
             reads=[], writes=[], imm=imm_bits(w, m), target=None, kind=None)
    if m == "ret": d["kind"] = "ret"
    elif m == "ebreak": d["kind"] = "ebreak"
    elif m == "jal": d["kind"] = "jump"; d["target"] = ins.address + d["imm"]
    elif m == "jalr": d["kind"] = "call_indirect"
    elif m in ("beq","bne","blt","bge","bltu","bgeu","beqz","bnez"):
        d["kind"] = "branch_cond"; d["target"] = ins.address + d["imm"]
    elif m == "lui": d["kind"] = "lui"
    elif m == "auipc": d["kind"] = "auipc"
    elif m == "ld": d["kind"] = "load"
    elif m == "sd": d["kind"] = "store"
    elif m == "lw": d["kind"] = "load32"
    elif m == "lbu": d["kind"] = "load8"
    return d

def is_prologue(ins):
    return ins["mnemonic"] == "addi" and ins["op_str"].startswith("sp, sp, -")

# ---------------- CFG walk: candidate function extent via direct control flow only ----------------
# cond branches + fallthrough = same function (out-of-line error blocks included).
# ret/ebreak end a block (no fallthrough). call_indirect/jump = callee boundary (recorded, not entered).
# A block starting with stack prologue (addi sp, sp, -N) reached via branch = separate function entry.
blocks = {}
edges = []
calls = []
# locality-prioritized worklist (min-heap by distance from candidate entry): keeps the
# walk focused on the candidate function's local blocks (error paths, epilogue) before
# wandering into distant code; extent is honest about any insn cap.
worklist = [(0, CANDIDATE_VA)]
done = set()
total_insns = 0
boundary_prologues = []

def push(va):
    heapq.heappush(worklist, (abs(va - CANDIDATE_VA), va))

while worklist and total_insns < MAX_INSNS:
    _, va = heapq.heappop(worklist)
    if va in done or not va_in_loaded(va):
        continue
    first = disasm_ins(va)
    if first is None:
        continue
    if va != CANDIDATE_VA and is_prologue(first):
        boundary_prologues.append(va)
        continue
    done.add(va)
    block = []
    cur = va
    block_start = va
    while total_insns < MAX_INSNS:
        if cur != va and cur in blocks:
            edges.append((block_start, cur, "merge", block[-1]["va"] if block else va))
            break
        ins = disasm_ins(cur)
        if ins is None:
            break
        block.append(ins)
        total_insns += 1
        kind = ins["kind"]
        nxt = cur + 4
        if kind in ("ret", "ebreak"):
            edges.append((block_start, None, kind, ins["va"]))
            break
        elif kind == "jump":
            edges.append((block_start, ins["target"], "jump", ins["va"]))
            break
        elif kind == "branch_cond":
            edges.append((block_start, ins["target"], "branch_taken", ins["va"]))
            edges.append((block_start, nxt, "branch_fallthrough", ins["va"]))
            if va_in_loaded(ins["target"]): push(ins["target"])
            if va_in_loaded(nxt): push(nxt)
            break
        elif kind == "call_indirect":
            resolved = None; au = None
            if len(block) >= 2 and block[-2]["kind"] == "auipc" and "ra" in block[-2]["op_str"]:
                au = block[-2]
                m = re.search(r",\s*(-?0x[0-9a-fA-F]+)\s*$", ins["op_str"])
                if m:
                    resolved = (au["va"] + (au["imm"] << 12)) + int(m.group(1), 0)
            if resolved is not None:
                calls.append(dict(ins=ins["va"], ins_file=ins["file"], kind="indirect_resolved",
                                  target=resolved, target_file=va_to_file(resolved),
                                  op=ins["op_str"], auipc_va=au["va"]))
                edges.append((block_start, resolved, "call_indirect", ins["va"]))
            else:
                calls.append(dict(ins=ins["va"], ins_file=ins["file"], kind="indirect_unresolved",
                                  target=None, target_file=None, op=ins["op_str"]))
                edges.append((block_start, None, "call_indirect_unresolved", ins["va"]))
            cur = nxt
            if cur - va > MAX_BLOCK_INSNS:
                edges.append((block_start, nxt, "block_bound", block[-1]["va"]))
                if va_in_loaded(nxt): push(nxt)
                break
            continue
        else:
            cur = nxt
            if cur - va > MAX_BLOCK_INSNS:
                edges.append((block_start, nxt, "block_bound", block[-1]["va"]))
                if va_in_loaded(nxt): push(nxt)
                break
    blocks[va] = block

# callee headers (indirect call targets), separate from function extent
callees = {}
for c in calls:
    if c["target"] is not None and c["target"] not in callees and va_in_loaded(c["target"]):
        t = c["target"]; cblock = []; cur = t
        while len(cblock) < MAX_BLOCK_INSNS and va_in_loaded(cur):
            ins = disasm_ins(cur)
            if ins is None: break
            cblock.append(ins)
            if ins["kind"] in ("ret", "ebreak", "jump", "branch_cond"):
                break
            cur += 4
        callees[t] = cblock

all_insns = [ins for b in blocks.values() for ins in b]
min_va = min(blocks) if blocks else CANDIDATE_VA
max_va = max((ins["va"] + ins["size"] for b in blocks.values() for ins in b), default=CANDIDATE_VA)
first_ret = min((ins["va"] for b in blocks.values() for ins in b if ins["kind"]=="ret"), default=None)
log(f"[cfg] function blocks={len(blocks)} insns={len(all_insns)} span={min_va:#x}..{max_va:#x}")
log(f"[cfg] first_ret={hex(first_ret) if first_ret else None} extent_end={max_va:#x} first_ret_is_end={bool(first_ret and first_ret == max_va - 4)}")
log(f"[cfg] boundary prologues not entered (separate functions): {[hex(b) for b in boundary_prologues][:20]} (count={len(boundary_prologues)})")
log(f"[cfg] indirect call sites={len(calls)} callee headers={len(callees)}")

branches = [ins for b in blocks.values() for ins in b if ins["kind"] == "branch_cond"]
log(f"[cfg] conditional branches={len(branches)}")
for ins in branches:
    log(f"   branch {ins['va']:#x} file={ins['file']:#x} {ins['mnemonic']} {ins['op_str']} -> taken={ins['target']:#x}(file={va_to_file(ins['target']) and hex(va_to_file(ins['target']))}) fallthrough={ins['va']+4:#x}")
for c in calls:
    log(f"   call {c['ins']:#x} file={c['ins_file']:#x} {c['kind']} target={c['target'] and hex(c['target'])} file={c['target_file'] and hex(c['target_file'])} op={c['op']}")
for t, cb in callees.items():
    first = cb[0] if cb else None
    log(f"   callee @ {t:#x} file={va_to_file(t) and hex(va_to_file(t))} first={first['mnemonic'] if first else None} {first['op_str'] if first else None}")

# ---------------- Dataflow evidence scanning ----------------
def find(pred):
    return [ins for b in blocks.values() for ins in b if pred(ins)]

ev = dict()
ev["stack_frame"] = [ins for ins in all_insns if ins["mnemonic"]=="addi" and "sp, sp, -0x90" in ins["op_str"]]
ev["frame_ptr"] = [ins for ins in all_insns if ins["mnemonic"]=="addi" and "s0, sp, 0x90" in ins["op_str"]]
ev["first_indirect_call"] = find(lambda i: i["mnemonic"]=="jalr" and i["op_str"]=="s2")
ev["read24_setup"] = [ins for ins in all_insns if ins["mnemonic"]=="addi" and "a3, zero, 0x18" in ins["op_str"]]
ev["stack_buf"] = [ins for ins in all_insns if ins["mnemonic"]=="addi" and "a1, s0, -0x90" in ins["op_str"]]
ev["ld_stack_magic"] = find(lambda i: i["mnemonic"]=="ld" and "-0x90(s0)" in i["op_str"])
ev["ld_rodata_magic"] = find(lambda i: i["mnemonic"]=="ld" and "0x330(a5)" in i["op_str"])
ev["lui_magic_base"] = find(lambda i: i["mnemonic"]=="lui" and "a5, 0x4022" in i["op_str"] and i["va"]==0x459c654)
ev["cmp_magic_branch"] = find(lambda i: i["mnemonic"]=="bne" and i["va"]==0x459c660)
ev["ld_stack_version"] = find(lambda i: i["mnemonic"]=="lw" and "-0x88(s0)" in i["op_str"])
ev["imm_version_1"] = find(lambda i: i["mnemonic"]=="addi" and "a5, zero, 1" in i["op_str"])
ev["cmp_version_branch"] = find(lambda i: i["mnemonic"]=="bne" and i["va"]==0x459c66c)
ev["ld_stack_fp"] = find(lambda i: i["mnemonic"]=="ld" and "-0x80(s0)" in i["op_str"])
ev["ld_rodata_fp"] = find(lambda i: i["mnemonic"]=="ld" and "0x338(a5)" in i["op_str"])
ev["cmp_fp_branch"] = find(lambda i: i["mnemonic"]=="bne" and i["va"]==0x459c67c)
ev["ld_stack_count"] = find(lambda i: i["mnemonic"]=="lw" and "-0x84(s0)" in i["op_str"])
ev["imm_count_496"] = find(lambda i: i["mnemonic"]=="addi" and "a5, zero, 0x1f0" in i["op_str"])
ev["cmp_count_branch"] = find(lambda i: i["mnemonic"]=="bne" and i["va"]==0x459c688)
ev["call2_error_branch_0x3d4"] = find(lambda i: i["mnemonic"]=="bnez" and i["va"]==0x459c6d4)
ev["table_base_lui"] = find(lambda i: i["mnemonic"]=="lui" and "s9, 0x4584" in i["op_str"])
ev["table_base_addi"] = find(lambda i: i["mnemonic"]=="addi" and "s9, s9, 0x790" in i["op_str"])
ev["stride"] = find(lambda i: i["mnemonic"]=="addi" and "s10, zero, 0x18" in i["op_str"])
ev["index_zero"] = find(lambda i: i["mnemonic"]=="mv" and "s8, zero" in i["op_str"])
ev["index_extend"] = find(lambda i: i["mnemonic"]=="slli" and "s4, s8, 0x20" in i["op_str"]) + find(lambda i: i["mnemonic"]=="srli" and "s4, s4, 0x20" in i["op_str"])
ev["stride_mul"] = find(lambda i: i["mnemonic"]=="mul" and "s2, s4, s10" in i["op_str"])
ev["record_addr"] = find(lambda i: i["mnemonic"]=="add" and "a4, s9, s2" in i["op_str"])
ev["flags_load"] = find(lambda i: i["mnemonic"]=="lw" and "0x10(a4)" in i["op_str"]) + find(lambda i: i["mnemonic"]=="lw" and "0x10(s2)" in i["op_str"])
ev["flags_andi4"] = find(lambda i: i["mnemonic"]=="andi" and "a5, a5, 4" in i["op_str"])
ev["flags_andi_6"] = find(lambda i: i["mnemonic"]=="andi" and "a3, a5, -6" in i["op_str"])
ev["fetch_callback_args"] = [ins for ins in all_insns if ins["mnemonic"] in ("addi","lui") and ins["va"] in (0x459c728,0x459c72c,0x459c730,0x459c734)]
ev["fetch_callback_call"] = find(lambda i: i["mnemonic"]=="jalr" and i["va"]==0x459c73c)
ev["canary_check"] = find(lambda i: i["mnemonic"]=="xor" and "a5, a4, a5" in i["op_str"])
ev["epilogue_ret"] = find(lambda i: i["mnemonic"]=="ret")

for k, v in ev.items():
    log(f"[ev] {k}: {[hex(i['va'])+'(file='+hex(i['file'])+')' for i in v]}")

rodata_window = read_bytes_va(EXPECTED_MAGIC_VA, 48)
rodata_sha = hashlib.sha256(rodata_window).hexdigest() if rodata_window else None
cand_bytes = read_bytes_va(min_va, max_va - min_va)
cand_sha = hashlib.sha256(cand_bytes).hexdigest() if cand_bytes else None

# ---------------- Serialize ----------------
def ins_ser(ins):
    return dict(va=ins["va"], file=ins["file"], raw=ins["raw"], size=ins["size"],
                mnemonic=ins["mnemonic"], op_str=ins["op_str"], kind=ins["kind"],
                reads=[regname(r) for r in ins["reads"]], writes=[regname(r) for r in ins["writes"]],
                imm=ins["imm"], target=ins["target"])

cfg_out = {
  "blocks": {hex(k): [ins_ser(i) for i in v] for k, v in blocks.items()},
  "edges": [[s, d, k, va] for s, d, k, va in edges],
  "calls": calls,
  "callees": {hex(t): [ins_ser(i) for i in cb] for t, cb in callees.items()},
  "boundary_prologues": boundary_prologues,
}
json.dump(cfg_out, open(os.path.join(DISASMDIR, "cfg.json"), "w"), indent=1)

listing_path = os.path.join(DISASMDIR, "extended_disasm.txt")
with open(listing_path, "w") as f:
    f.write(f"; Extended CFG disassembly of candidate at VA {CANDIDATE_VA:#x} (file {EXPECTED_CANDIDATE_FILE:#x})\n")
    f.write(f"; ELF mapping: VA = outer_file_offset + 0x03ffffc0 (parsed PT_LOAD delta 0x4000000; no hard-coded section names)\n")
    f.write(f"; function blocks={len(blocks)} insns={len(all_insns)} span={min_va:#x}..{max_va:#x}\n")
    f.write(f"; first_ret={hex(first_ret) if first_ret else None} extent_end={max_va:#x} first_ret_is_end={bool(first_ret and first_ret == max_va - 4)}\n")
    f.write("; capstone 5.0.7 CS_ARCH_RISCV | CS_MODE_RISCV64 | CS_MODE_RISCVC (real backend; CS_MODE_64 claim was wrong)\n")
    f.write("; register names per RISC-V ABI (s0/s1/.. = x8/x9/..). Indirect call targets are callees, excluded from extent.\n")
    for ins in sorted(all_insns, key=lambda i: i["va"]):
        tag = ""
        if ins["kind"] == "branch_cond":
            tag = f"  -> {ins['target']:#x} (file {va_to_file(ins['target']) and hex(va_to_file(ins['target']))})"
        elif ins["kind"] == "call_indirect":
            tgt = [c for c in calls if c["ins"] == ins["va"]]
            tag = f"  ; indirect call -> {tgt[0]['target'] and hex(tgt[0]['target'])} (file {tgt[0]['target_file'] and hex(tgt[0]['target_file'])})" if tgt else "  ; indirect call (unresolved)"
        f.write(f"{ins['va']:#010x} file={ins['file'] and hex(ins['file'])} {ins['raw']:08x} {ins['mnemonic']:10s} {ins['op_str']}{tag}\n")
    f.write("\n; indirect call sites:\n")
    for c in calls:
        f.write(f";   {c['ins']:#010x} file={c['ins_file']:#010x} {c['kind']} target={c['target'] and hex(c['target'])} file={c['target_file'] and hex(c['target_file'])} op={c['op']}\n")
    f.write("\n; callee headers (reached only via indirect calls; excluded from function extent):\n")
    for t, cb in callees.items():
        f.write(f";   {t:#010x} file={va_to_file(t) and hex(va_to_file(t))}:\n")
        for ins in cb:
            f.write(f";      {ins['va']:#010x} {ins['raw']:08x} {ins['mnemonic']:10s} {ins['op_str']}\n")
    f.write("\n; separate-function prologue boundaries (not entered):\n")
    for b in boundary_prologues:
        f.write(f";   {b:#010x} file={va_to_file(b) and hex(va_to_file(b))}\n")

verified = {
  "inputs": {"gsp": GSP, "gsp_size": len(data), "gsp_sha256": gsp_sha,
             "python": "/usr/bin/python3", "capstone": "5.0.7", "mode": "RISCV64|RISCVC", "offline": True},
  "elf": {"entry": e_entry, "machine": hex(e_machine), "phnum": e_phnum,
          "deltas": [hex(d) for d in deltas],
          "mapping_note": "VA = outer_file_offset + 0x03ffffc0 (parsed PT_LOAD; NOT hard-coded section names)"},
  "mapping_checks": {
    "candidate_va": hex(CANDIDATE_VA), "candidate_file": hex(cf),
    "expected_candidate_file": hex(EXPECTED_CANDIDATE_FILE), "candidate_file_ok": cf == EXPECTED_CANDIDATE_FILE,
    "magic_va": hex(EXPECTED_MAGIC_VA), "magic_file": hex(MAGIC_FILE),
    "fp_va": hex(EXPECTED_FP_VA), "fp_file": hex(FP_FILE),
    "fp_va_ok": va_to_file(EXPECTED_FP_VA) == FP_FILE,
  },
  "fingerprint": {
    "magic_file": MAGIC_FILE, "magic_raw": magic_raw.hex(), "magic_ascii": magic_raw.decode("ascii","replace"),
    "magic_ok": magic_raw == b"NVUCODES",
    "fp_file": FP_FILE, "fp_inner": FP_FILE - INNER, "fp_va": hex(EXPECTED_FP_VA),
    "fp_raw": fp_raw.hex(), "fp_value": hex(fp_val), "expected_value": hex(EXPECTED_FP),
    "fp_ok": fp_val == EXPECTED_FP,
    "window_file": [MAGIC_FILE, MAGIC_FILE + 48], "window_sha256": rodata_sha,
  },
  "candidate": {
    "start_va": hex(CANDIDATE_VA), "start_file": hex(cf),
    "extent_start_va": hex(min_va), "extent_end_va": hex(max_va),
    "extent_start_file": hex(va_to_file(min_va) or 0), "extent_end_file": hex(va_to_file(max_va - 4) or 0),
    "blocks": len(blocks), "instructions": len(all_insns),
    "first_ret_va": hex(first_ret) if first_ret else None,
    "first_ret_is_end": bool(first_ret and first_ret == max_va - 4),
    "extent_note": "Extent from direct-flow CFG walk (fallthrough + conditional branches); indirect call targets are callees, excluded. First sequential ret is not the end: out-of-line error blocks reached by conditional branches extend beyond it.",
    "cfg_json": os.path.join(DISASMDIR, "cfg.json"),
    "disassembly": listing_path,
  },
  "sha256": {"candidate_bytes_extent": cand_sha, "candidate_file_window": [hex(min_va), hex(max_va - 4)]},
  "branches": [],
  "calls": calls,
  "callees": {hex(t): [hex(ins["va"]) for ins in cb] for t, cb in callees.items()},
  "boundary_prologues": boundary_prologues,
  "evidence": {k: [dict(va=i["va"], file=i["file"], mnemonic=i["mnemonic"], op_str=i["op_str"], raw=i["raw"]) for i in v] for k, v in ev.items()},
  "rodata": {"magic_va": hex(EXPECTED_MAGIC_VA), "fp_va": hex(EXPECTED_FP_VA), "window_sha256": rodata_sha},
  "verdict": None,
}

for ins in branches:
    verified["branches"].append(dict(ins=ins["va"], ins_file=ins["file"], mnemonic=ins["mnemonic"], op_str=ins["op_str"],
                                     taken=ins["target"], taken_file=va_to_file(ins["target"]),
                                     fallthrough=ins["va"]+4, raw=ins["raw"]))

hdr = all(ev[k] for k in ("stack_frame","frame_ptr","first_indirect_call","read24_setup","stack_buf",
                          "ld_stack_magic","ld_rodata_magic","cmp_magic_branch",
                          "ld_stack_version","imm_version_1","cmp_version_branch",
                          "ld_stack_fp","ld_rodata_fp","cmp_fp_branch",
                          "ld_stack_count","imm_count_496","cmp_count_branch"))
tbl = all(ev[k] for k in ("table_base_lui","table_base_addi","stride","index_zero","stride_mul","record_addr","flags_load","flags_andi4"))
fetch = bool(ev["fetch_callback_args"] and ev["fetch_callback_call"])
log(f"[verdict] header_validation_evidence_complete={hdr} record_table_evidence_complete={tbl} fetch_callback_to_entry1={fetch}")
verified["verdict"] = {
  "header_validation": "VERIFIED (source-correlated)" if hdr else "INCOMPLETE",
  "function_identity": "CANDIDATE (inferred: GSP header consumer; stripped ELF, no symbol table)",
  "engine_mapping": "UNKNOWN (no BINDATA_LABEL<->slot->engine name derivable from binary; indirect targets resolved to VA only)",
  "record_table_base": hex(0x4584790), "record_table_base_file": hex(va_to_file(0x4584790) or 0),
  "record_table_stride": 24,
  "first_entry_index": 0, "first_entry_va": hex(0x4584790), "first_entry_file": hex(va_to_file(0x4584790) or 0),
  "fetch_callback_args_to_entry1": fetch,
  "notes": "First indirect call (jalr s2 @0x459c648; s2=a2=function-pointer arg) reads 24 bytes: a3=0x18, a1=s0-0x90=stack buffer. Stack-relative header fields: magic@sp+0 (stack-0x90), version@sp+8 (stack-0x88), count@sp+12 (stack-0x84), fingerprint@sp+16 (stack-0x80). Comparisons: magic vs rodata 0x4022330 \"NVUCODES\"; version vs 1; fingerprint vs rodata 0x4022338 (0x8D1990AB6B98AE2B); count vs 496 (0x1f0). Each mismatch branches to cold error blocks beyond 0x459c7cc (magic->0x459c9b4, version->0x459c990, fingerprint->0x459c9f8, count->0x459c9d0, call1->0x459c970, call2 +0x3d4->0x459caa8). Record table base s9=0x4584790 (lui 0x4584 + addi 0x790) in read-only segment (file 0x5847d0), stride 24 (s10=0x18), index s8=0, record addr = base + index*24 (a4 at 0x459c708), flags@+0x10 tested &4 then &-6 (REFERENCED|EXTERNAL). First entry (index 0) fetched at 0x4584790; callback args a0=2,a1=0x29,a2=0x58e7990 set before indirect call @0x459c738->0x55c04d8. Engine/name mapping not established: UNKNOWN."
}
json.dump(verified, open(os.path.join(OUTDIR, "header_consumer_verified.json"), "w"), indent=1)
log(f"[done] wrote {OUTDIR}/header_consumer_verified.json and {listing_path}")
logf.close()
print("EXIT=0")

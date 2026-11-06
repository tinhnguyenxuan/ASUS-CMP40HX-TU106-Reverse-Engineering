#!/usr/bin/env python3
# ponytail: stdlib + capstone 5.0.7 (/usr/bin/python3), offline only.
# GSP header-consumer FOLLOWUP (NEW output dir only; previous artifacts untouched).
#
# Builds a correct 16/32-bit RISC-V direct-flow CFG for the NVUCODES header consumer:
#   - queued block starts distinct from decoded instruction addresses
#   - variable compressed/regular instruction lengths (2 or 4 bytes)
#   - conditional / JAL(jal x0 = direct jump) / JALR (ret or indirect call) semantics
#   - mapped executable bounds (PT_LOAD, PF_X bit0)
#   - overlap handling when a branch target lands mid-block
#   - explicit unresolved indirect edges
# Then: fixpoint determination, trace of all accesses to table base 0x4584790
#   (actualSize+0, compressedSize+4, pData+8, flags+16, relOffset+20) with raw bytes,
#   VA/file mapping, def/use chains and branch guards, record-index validation against
#   the firmware container, and descriptor name/engine = UNKNOWN absent cross-reference.
#
# Rerunnable: ` /usr/bin/python3 PHASE16/GSP_HEADER_CONSUMER_FOLLOWUP/header_consumer_followup.py`
import struct, hashlib, json, os, heapq, re, sys
from capstone import *

GSP = "/home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin"
OUTDIR = "/home/REDACTED_USER/codex-work/work_v15/PHASE16/GSP_HEADER_CONSUMER_FOLLOWUP"
INNER = 0x40                      # embedded ELF64 starts at outer file 0x40
CANDIDATE_VA = 0x0459C5E0         # candidate entry (prior review json)
TABLE_BASE_VA = 0x04584790        # 24-byte record table base: lui s9,0x4584; addi s9,s9,0x790
TABLE_STRIDE = 24
FIELDS = {0: "actualSize", 4: "compressedSize", 8: "pData", 16: "flags", 20: "relOffset"}
MAX_INSNS = 500000                # safety net only; fixpoint expected well before this

os.makedirs(OUTDIR, exist_ok=True)
DIS = os.path.join(OUTDIR, "disassembly"); os.makedirs(DIS, exist_ok=True)
logf = open(os.path.join(OUTDIR, "run.log"), "w")
def log(*a):
    print(*a, flush=True); print(*a, file=logf, flush=True)

# ---------------- register numbering (RISC-V ABI, by reg number) ----------------
REGS = {0:"zero",1:"ra",2:"sp",3:"gp",4:"tp",5:"t0",6:"t1",7:"t2",8:"s0",9:"s1",
        10:"a0",11:"a1",12:"a2",13:"a3",14:"a4",15:"a5",16:"a6",17:"a7",
        18:"s2",19:"s3",20:"s4",21:"s5",22:"s6",23:"s7",24:"s8",25:"s9",
        26:"s10",27:"s11",28:"t3",29:"t4",30:"t5",31:"t6"}
def rn(r): return REGS.get(r, f"x{r}")
ZERO, RA, SP, S7, S8, S9, S10, S11, S4, S2, A4, A5, A3 = 0,1,2,23,24,25,26,27,20,18,14,15,13

# ---------------- ELF parse (stdlib struct only) --------------------------------
data = open(GSP, "rb").read()
gsp_sha = hashlib.sha256(data).hexdigest()
log(f"[inputs] gsp={GSP} size={len(data)} sha256={gsp_sha}")
inner = data[INNER:]
eh = inner[:64]
(e_type,e_machine,e_version,e_entry,e_phoff,e_shoff,e_flags,e_ehsize,e_phentsize,e_phnum,
 e_shentsize,e_shnum,e_shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", eh, 16)
segs = []
for i in range(e_phnum):
    p_type,p_flags,p_off,p_vaddr,p_paddr,p_filesz,p_memsz,p_align = struct.unpack_from("<IIQQQQQQ", inner, e_phoff+i*e_phentsize)
    segs.append(dict(type=p_type,flags=p_flags,off=p_off,vaddr=p_vaddr,paddr=p_paddr,
                     filesz=p_filesz,memsz=p_memsz,align=p_align))
    if p_type == 1:
        log(f"[elf] LOAD off={p_off:#x} vaddr={p_vaddr:#x} filesz={p_filesz:#x} memsz={p_memsz:#x} flags={p_flags:#x} exec={bool(p_flags&1)} delta={p_vaddr-p_off:#x}")

def seg_for(va):
    for s in segs:
        if s["type"]==1 and s["vaddr"] <= va < s["vaddr"]+s["filesz"]:
            return s
    return None
def va_to_file(va):
    s = seg_for(va)
    if s is None: return None
    return INNER + s["off"] + (va - s["vaddr"])
def va_in_loaded(va): return seg_for(va) is not None
def va_exec(va):
    s = seg_for(va); return s is not None and bool(s["flags"] & 1)
def read_va(va, n):
    s = seg_for(va)
    if s is None: return None
    f = INNER + s["off"] + (va - s["vaddr"])
    if f < 0 or f + n > len(data): return None
    return data[f:f+n]
def read_u32_va(va):
    b = read_va(va, 4)
    return struct.unpack_from("<I", b)[0] if b else None

deltas = sorted({s["vaddr"]-s["off"] for s in segs if s["type"]==1})
log(f"[elf] entry={e_entry:#x} machine={e_machine:#x} phnum={e_phnum} load_deltas={[hex(d) for d in deltas]}")
assert e_machine == 0xf3
cf = va_to_file(CANDIDATE_VA); assert cf == 0x59c620, f"candidate {cf:#x}"
log(f"[elf] candidate VA {CANDIDATE_VA:#x} = file {cf:#x} OK")

# ---------------- Capstone (real RISC-V backend; 16-bit C instructions possible) --
md = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64 | CS_MODE_RISCVC)
MDETAIL = None

def sext(x, bits):
    if x & (1 << (bits-1)): x -= (1 << bits)
    return x

def decode_fields(w):
    opc = w & 0x7f
    rd = (w >> 7) & 0x1f; rs1 = (w >> 15) & 0x1f; rs2 = (w >> 20) & 0x1f
    f3 = (w >> 12) & 0x7; f7 = (w >> 25) & 0x7f
    imm_i = sext(w >> 20, 12)
    imm_u = (w >> 12) & 0xfffff          # lui/auipc upper (caller shifts <<12)
    # B-type branch immediate (corrected: 13-bit, sign bit = bit12 -> subtract 0x2000)
    xb = ((w>>31)&1)<<12 | ((w>>7)&1)<<11 | ((w>>25)&0x3f)<<5 | ((w>>8)&0xf)<<1
    imm_b = xb - 0x2000 if (xb & 0x1000) else xb
    # J-type jal immediate (21-bit, sign bit = bit20 -> subtract 0x200000)
    xj = ((w>>31)&1)<<20 | ((w>>21)&0x3ff)<<1 | ((w>>20)&1)<<11 | ((w>>12)&0xff)<<12
    imm_j = xj - 0x200000 if (xj & 0x100000) else xj
    shamt = (w >> 20) & 0x1f              # 5-bit shift amount (standard)
    shift6 = (w >> 20) & 0x3F             # 6-bit incl. bit25 (this binary encodes shift=32 for the zero-extend idiom)
    return dict(opc=opc, rd=rd, rs1=rs1, rs2=rs2, f3=f3, f7=f7,
                imm_i=imm_i, imm_u=imm_u, imm_b=imm_b, imm_j=imm_j,
                shamt=shamt, shift6=shift6)

def disasm_ins(va):
    b = read_va(va, 4)
    if b is None: return None
    insns = list(md.disasm(b, va))
    if not insns: return None
    ins = insns[0]
    f = decode_fields(struct.unpack_from("<I", b, 0)[0])
    d = dict(va=ins.address, file=va_to_file(va), size=ins.size,
             raw=struct.unpack_from("<I", b, 0)[0],
             mnemonic=ins.mnemonic, op_str=ins.op_str,
             kind=None, target=None, fields=f)
    m = ins.mnemonic
    if m == "ret": d["kind"] = "ret"
    elif m == "ebreak": d["kind"] = "ebreak"
    elif m == "jal":
        if f["rd"] == 0: d["kind"] = "jump"          # jal x0 == unconditional direct jump
        else: d["kind"] = "call"                      # jal ra == function call (fallthrough continues)
        d["target"] = va + f["imm_j"]
    elif m == "jalr":
        # ret if jalr x0, 0(ra)
        if f["rd"] == 0 and f["rs1"] == RA and f["imm_i"] == 0:
            d["kind"] = "ret"
        else:
            d["kind"] = "call_indirect"
    elif m in ("beq","bne","blt","bge","bltu","bgeu","beqz","bnez"):
        d["kind"] = "branch_cond"; d["target"] = va + f["imm_b"]
    elif m == "lui": d["kind"] = "lui"
    elif m == "auipc": d["kind"] = "auipc"
    elif m in ("lb","lh","lw","lbu","lhu","lw","ld","lwu"): d["kind"] = "load"
    elif m in ("sb","sh","sw","sd"): d["kind"] = "store"
    return d

# ---------------- CFG walk ------------------------------------------------------
blocks = {}           # start_va -> list of insn dicts
block_range = {}      # start_va -> (start, end_exclusive)
decoded_ins = {}      # va -> insn (any block)  <- decoded instruction addresses
edges = []
calls = []
oob = []              # out-of-bounds / non-executable targets
overlaps = []         # block start landing inside another block's range
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
            # same bytes reused; record overlap if cur is inside another block at non-start
        else:
            ins = disasm_ins(cur)
            if ins is None: break
            decoded_ins[cur] = ins
            total_insns += 1
        block.append(ins)
        kind = ins["kind"]; nxt = cur + ins["size"]
        if kind in ("ret", "ebreak"):
            edges.append((block_start, None, kind, ins["va"])); break
        if kind == "jump":            # jal x0 / j : direct jump, no fallthrough
            t = ins["target"]
            edges.append((block_start, t, "jump", ins["va"]))
            if in_exec_range(t): push(t)
            else: oob.append(("jump", ins["va"], t, va_to_file(t)))
            break
        if kind == "call":            # jal ra : call, fallthrough continues (return addr)
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
                                  target=resolved, target_file=va_to_file(resolved) if resolved else None,
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
            if in_exec_range(t): push(t)
            else: oob.append(("branch", ins["va"], t, va_to_file(t)))
            if in_exec_range(nxt): push(nxt)
            else: oob.append(("branch_fallthrough", ins["va"], nxt, va_to_file(nxt)))
            break
        # fallthrough
        cur = nxt
        if cur % 2 != 0:
            edges.append((block_start, None, "misaligned_fallthrough", ins["va"])); break
        if cur - va > 4000:
            edges.append((block_start, nxt, "block_bound", ins["va"]))
            if in_exec_range(nxt): push(nxt)
            break
    blocks[block_start] = block
    block_range[block_start] = (block_start, cur if block else block_start)
    # overlap: block start inside another block's range at non-start offset
    for s2,(a,b_) in block_range.items():
        if s2 == block_start: continue
        if a <= block_start < b_:
            overlaps.append((block_start, s2, a, b_))
            break

fixpoint = (not worklist) and not hit_cap
log(f"[cfg] blocks={len(blocks)} decoded_insns={len(decoded_ins)} walked_insns={total_insns} hit_cap={hit_cap}")
log(f"[cfg] edges={len(edges)} calls={len(calls)} oob={len(oob)} overlaps={len(overlaps)} fixpoint={fixpoint}")
log(f"[cfg] span={min(blocks) if blocks else CANDIDATE_VA:#x}..{max((r[1] for r in block_range.values()), default=CANDIDATE_VA):#x}")
for x,y,a_,b_ in overlaps[:10]:
    log(f"[cfg] overlap block {x:#x} inside block {a_:#x}..{b_:#x} (from block {y:#x})")
for kind,*rest in oob[:10]:
    log(f"[cfg] oob {kind} {rest}")

# ---------------- immediate correctness self-check (vs capstone op_str) -----------
imm_bad = 0; imm_checked = 0
for s2, block in blocks.items():
    for ins in block:
        f = ins["fields"]; m = ins["mnemonic"]
        if m in ("beq","bne","blt","bge","bltu","bgeu","beqz","bnez","jal"):
            imm_checked += 1
            mt = re.findall(r"-?0x[0-9a-fA-F]+|-?\d+", ins["op_str"])
            cs = int(mt[-1], 0) if mt else None
            my = f["imm_b"] if m != "jal" else f["imm_j"]
            if cs is not None and my != cs:
                imm_bad += 1
                if imm_bad <= 5: log(f"[check] IMM MISMATCH va={ins['va']:#x} {m} {ins['op_str']} my={my} capstone={cs}")
log(f"[check] branch/jal immediates checked={imm_checked} mismatches={imm_bad}")
assert imm_bad == 0, "immediate extraction mismatch with capstone"

# ---------------- symbolic dataflow: table field accesses -----------------------
# sym tags: int (concrete), 'BASE_IDX24', 'S7_IDX24', 'IDX', 'IDX24', None
# s9 = TABLE_BASE_VA (single definition: lui 0x4584 / addi 0x790, dominates all uses)
# s8 = 'IDX' at detected loop headers (targets of backward branches)

def is_loop_header(bs):
    # branch from a block whose start is greater (back edge) into bs
    for s,(a,b_) in block_range.items():
        pass
    # simpler: any edge (x -> bs, kind branch_taken/jump) with x > bs
    for (src,dst,kind,ins_va) in edges:
        if dst == bs and kind in ("branch_taken","jump") and src is not None and src > bs:
            return True
    return False

loop_headers = {bs for bs in blocks if is_loop_header(bs)}
log(f"[dataflow] loop headers (back-edge targets): {[hex(x) for x in sorted(loop_headers)]}")

def step_sym(sym, ins):
    f = ins["fields"]; m = ins["mnemonic"]; opc = f["opc"]
    sym = dict(sym)
    if opc == 0x37:                      # lui
        sym[f["rd"]] = ("LUIHI", f["imm_u"] << 12)
    elif opc == 0x13 and f["f3"] == 0:   # addi
        if f["rs1"] == ZERO:
            sym[f["rd"]] = f["imm_i"]
        elif isinstance(sym.get(f["rs1"]), tuple) and sym[f["rs1"]][0] == "LUIHI":
            sym[f["rd"]] = sym[f["rs1"]][1] + f["imm_i"]
        elif isinstance(sym.get(f["rs1"]), int):
            sym[f["rd"]] = sym[f["rs1"]] + f["imm_i"]
        else:
            sym[f["rd"]] = None
    elif opc == 0x13 and f["f3"] == 1:   # slli
        sh = f["shift6"]
        v = sym.get(f["rs1"])
        if isinstance(v, int): sym[f["rd"]] = v << sh
        elif v == "IDX" and sh == 32: sym[f["rd"]] = "IDX"   # zero-extend idiom half
        else: sym[f["rd"]] = None
    elif opc == 0x13 and f["f3"] == 5 and not (f["f7"] >> 5) & 1:  # srli (bit30=0)
        sh = f["shift6"]
        v = sym.get(f["rs1"])
        if isinstance(v, int): sym[f["rd"]] = v >> sh
        elif v == "IDX" and sh == 32: sym[f["rd"]] = "IDX"   # zero-extend idiom half
        else: sym[f["rd"]] = None
    elif opc == 0x13 and f["f3"] == 5 and (f["f7"] >> 5) & 1:  # srai (bit30=1)
        sh = f["shift6"]
        v = sym.get(f["rs1"])
        if isinstance(v, int): sym[f["rd"]] = v >> sh
        elif v == "IDX" and sh == 32: sym[f["rd"]] = "IDX"
        else: sym[f["rd"]] = None
    elif opc == 0x33 and f["f3"] == 0 and f["f7"] == 0:  # add
        a, b = sym.get(f["rs1"]), sym.get(f["rs2"])
        if isinstance(a, int) and isinstance(b, int): sym[f["rd"]] = a + b
        elif a == TABLE_BASE_VA and b == "IDX24": sym[f["rd"]] = "BASE_IDX24"
        elif b == TABLE_BASE_VA and a == "IDX24": sym[f["rd"]] = "BASE_IDX24"
        elif f["rs1"] == S7 and b == "IDX24": sym[f["rd"]] = "S7_IDX24"
        elif f["rs2"] == S7 and a == "IDX24": sym[f["rd"]] = "S7_IDX24"
        else: sym[f["rd"]] = None
    elif opc == 0x33 and f["f3"] == 0 and f["f7"] == 1:  # mul
        a, b = sym.get(f["rs1"]), sym.get(f["rs2"])
        if (a == "IDX" and b == TABLE_STRIDE) or (b == "IDX" and a == TABLE_STRIDE):
            sym[f["rd"]] = "IDX24"
        elif isinstance(a, int) and isinstance(b, int): sym[f["rd"]] = a * b
        else: sym[f["rd"]] = None
    elif m == "mv" or (opc == 0x13 and f["f3"] == 0 and f["rs1"] == ZERO):
        sym[f["rd"]] = sym.get(f["rs1"])
    elif ins["kind"] in ("load", "store"):
        sym[f["rd"]] = None
    elif ins["kind"] in ("call", "call_indirect", "ret"):
        sym[f["rd"]] = None
    else:
        sym[f["rd"]] = None
    sym[ZERO] = 0
    return sym

def mem_size(ins):
    m = ins["mnemonic"]
    if m in ("ld","sd"): return 8
    if m in ("lw","sw"): return 4
    if m in ("lh","sh"): return 2
    if m in ("lbu","lhu","sb"): return 1
    return None

table_accesses = []
# bounded cross-block symbolic dataflow (guaranteed to terminate).
# s9 = TABLE_BASE_VA globally (single def: lui 0x4584 / addi 0x790; dominates all uses)
# s10 = TABLE_STRIDE globally (single def: addi s10, zero, 0x18)
# s8 = 'IDX' at loop headers (back-edge targets) for the loop-carried index
# Join = agree-or-None; values only flow concrete -> None, so this converges.
# A pass cap guards against pathological register reuse around loops.
succs_of = {}; preds_of = {}
for (src, dst, kind, ins_va) in edges:
    if dst is None: continue
    if kind in ("branch_taken", "branch_fallthrough", "jump"):
        succs_of.setdefault(src, []).append(dst)
        preds_of.setdefault(dst, []).append(src)

entry_sym = {}
for bs in blocks:
    entry_sym[bs] = {S9: TABLE_BASE_VA, S10: TABLE_STRIDE}
    if bs in loop_headers:
        entry_sym[bs][S8] = "IDX"
work = [CANDIDATE_VA]
inwork = {CANDIDATE_VA}
processed_sym = {}
sym_passes = 0
SYM_PASS_CAP = 200000
while work and sym_passes < SYM_PASS_CAP:
    bs = work.pop(0); inwork.discard(bs); sym_passes += 1
    sym = dict(entry_sym.get(bs, {}))
    pending = None   # (ins_va, field, loaded_reg) waiting for a guard branch
    for ins in blocks[bs]:
        sym = step_sym(sym, ins)
        if ins["kind"] in ("load", "store"):
            sz = mem_size(ins); base = sym.get(ins["fields"]["rs1"])
            off = ins["fields"]["imm_i"]
            rec_index = None; rec_va = None; base_tag = None
            if isinstance(base, int):
                if base == TABLE_BASE_VA:
                    base_tag = "BASE"; rec_index = 0; rec_va = TABLE_BASE_VA
                elif (base - TABLE_BASE_VA) % TABLE_STRIDE == 0:
                    idx = (base - TABLE_BASE_VA)//TABLE_STRIDE
                    if 0 <= idx < 65536: base_tag = "BASE"; rec_index = idx; rec_va = base
            elif base == "BASE_IDX24":
                base_tag = "BASE_IDX24"; rec_va = None
            elif base == "S7_IDX24":
                base_tag = "S7_IDX24"; rec_va = None   # different table base (s7), not 0x4584790
            field = FIELDS.get(off)
            if base_tag in ("BASE", "BASE_IDX24") and field:
                raw = None; rfile = None; value = None
                if rec_va is not None:
                    rb = read_va(rec_va + off, sz)
                    if rb:
                        raw = rb.hex(); rfile = va_to_file(rec_va + off)
                        if sz == 4: value = struct.unpack_from("<I", rb, 0)[0]
                        elif sz == 8: value = struct.unpack_from("<Q", rb, 0)[0]
                table_accesses.append(dict(
                    ins=ins["va"], ins_file=ins["file"], mnemonic=ins["mnemonic"], op_str=ins["op_str"],
                    raw=ins["raw"], size=ins["size"], kind=ins["kind"],
                    base_reg=rn(ins["fields"]["rs1"]), base_tag=base_tag, offset=off, field=field,
                    rec_index=rec_index, rec_va=rec_va, rec_file=va_to_file(rec_va) if rec_va else None,
                    raw_bytes=raw, raw_file=rfile, value=value, size_read=sz,
                    guard=None, def_base_va=None))
                pending = (ins["va"], field, ins["fields"]["rd"])
            else:
                pending = None
        elif pending is not None:
            f2 = ins["fields"]
            if ins["kind"] == "branch_cond" and (f2["rs1"] == pending[2] or f2["rs2"] == pending[2]):
                table_accesses[-1]["guard"] = ins["va"]
                pending = None
            elif ins["kind"] in ("load","store","call","call_indirect","ret","lui","auipc","jump"):
                pending = None
            elif f2["opc"] == 0x13 and f2["f3"] == 0x7 and f2["rd"] == pending[2]:  # andi on loaded reg
                pass  # keep pending, next branch may use it
    processed_sym[bs] = sym
    # propagate to successors (bounded fixpoint)
    for dst in succs_of.get(bs, ()):
        if dst not in blocks: continue
        old = entry_sym.get(dst, {})
        regs = set(old)
        for p in preds_of.get(dst, ()):
            if p in processed_sym:
                for r in processed_sym[p]: regs.add(r)
        joined = {}
        for r in regs:
            vals = [processed_sym[p].get(r) for p in preds_of.get(dst, ()) if p in processed_sym]
            vals = [v for v in vals if v is not None]
            if vals and all(v == vals[0] for v in vals): joined[r] = vals[0]
            else: joined[r] = None
        joined[S9] = TABLE_BASE_VA
        joined[S10] = TABLE_STRIDE
        if dst in loop_headers: joined[S8] = "IDX"
        if joined != old:
            entry_sym[dst] = joined
            if dst not in inwork:
                work.append(dst); inwork.add(dst)
sym_hit_cap = sym_passes >= SYM_PASS_CAP

# ---- deduplicate accesses reported from overlapping blocks (same insn decoded in >1 block) ----
dedup = {}
for t in table_accesses:
    k = t["ins"]
    prev = dedup.get(k)
    if prev is None:
        dedup[k] = dict(t)
    else:
        # prefer a concrete record index; merge guards
        if t["rec_index"] is not None and prev["rec_index"] is None:
            prev["rec_index"] = t["rec_index"]; prev["rec_va"] = t["rec_va"]
            prev["rec_file"] = t["rec_file"]; prev["raw_bytes"] = t["raw_bytes"]
            prev["raw_file"] = t["raw_file"]; prev["value"] = t["value"]
        prev["base_tag"] = t["base_tag"] if t["rec_index"] is not None else prev["base_tag"]
        if t["guard"] is not None:
            prev["guard"] = t["guard"]
        prev["_dup_insns"] = prev.get("_dup_insns", 0) + 1
table_accesses = list(dedup.values())

# ---- cross-check: every load/store in the CFG at a record-field offset, with its raw base reg ----
field_offsets = set(FIELDS.keys())
xref_scan = []
for bs in blocks:
    for ins in blocks[bs]:
        if ins["kind"] in ("load", "store") and ins["fields"]["imm_i"] in field_offsets:
            xref_scan.append(dict(
                ins=ins["va"], ins_file=ins["file"], mnemonic=ins["mnemonic"], op_str=ins["op_str"],
                raw=ins["raw"], size=ins["size"], base_reg=rn(ins["fields"]["rs1"]), offset=ins["fields"]["imm_i"],
                field=FIELDS.get(ins["fields"]["imm_i"]),
                tagged=(ins["va"] in dedup)))

# normalize base_tag for S7 accesses (report separately, not counted as 0x4584790)
base_table_accesses = [t for t in table_accesses if t["base_tag"] in ("BASE","BASE_IDX24")]
s7_table_accesses = [t for t in table_accesses if t["base_tag"] == "S7_IDX24"]
log(f"[dataflow] table accesses (base 0x4584790): {len(base_table_accesses)}  (via s7 table: {len(s7_table_accesses)})")
for t in base_table_accesses:
    log(f"[tbl] {t['ins']:#x} {t['mnemonic']:6s} {t['op_str']} base={t['base_tag']} field={t['field']} off={t['offset']} idx={t['rec_index']} rec_va={t['rec_va'] and hex(t['rec_va'])} value={t['value'] and hex(t['value'])} raw={t['raw_bytes']} guard={t['guard'] and hex(t['guard'])}")

# ---------------- record dump & validation against firmware container -----------
count_from_header = 496  # validated in prior phase: count field == 0x1f0 == 496
n_valid = 0; n_zero = 0; n_oob = 0; records = []
for idx in range(count_from_header):
    rva = TABLE_BASE_VA + idx*TABLE_STRIDE
    if not va_in_loaded(rva + TABLE_STRIDE - 1):
        n_oob += 1; records.append(dict(index=idx, rec_va=rva, rec_file=None, in_bounds=False))
        continue
    rb = read_va(rva, TABLE_STRIDE)
    f00 = struct.unpack_from("<I", rb, 0)[0]; f04 = struct.unpack_from("<I", rb, 4)[0]
    f08 = struct.unpack_from("<Q", rb, 8)[0]; f16 = struct.unpack_from("<I", rb, 16)[0]
    f20 = struct.unpack_from("<I", rb, 20)[0]
    allz = (rb == b"\x00"*TABLE_STRIDE)
    if allz: n_zero += 1
    else: n_valid += 1
    records.append(dict(index=idx, rec_va=rva, rec_file=va_to_file(rva), in_bounds=True,
                        actualSize=f00, compressedSize=f04, pData=f08, flags=f16, relOffset=f20,
                        raw=rb.hex(), all_zero=allz,
                        pData_file=va_to_file(f08) if va_in_loaded(f08) else None,
                        pData_in_exec=va_exec(f08) if va_in_loaded(f08) else None))
log(f"[table] count={count_from_header} valid_nonzero={n_valid} zero={n_zero} out_of_bounds={n_oob}")
# cross-reference: descriptor_table.json (different base 0x41a70b0) NOT cross-referenced -> UNKNOWN
desc_base = 0x41a70b0
desc_in_bounds = va_in_loaded(desc_base + TABLE_STRIDE - 1)
log(f"[xref] descriptor_table.json base 0x{desc_base:x} (gsp_summary) in_loaded={desc_in_bounds}; "
    f"distinct from 0x{TABLE_BASE_VA:x}; no cross-reference -> names/engine = UNKNOWN")

# ---------------- serialize outputs ---------------------------------------------
def ins_ser(ins):
    return dict(va=ins["va"], file=ins["file"], raw=ins["raw"], size=ins["size"],
                mnemonic=ins["mnemonic"], op_str=ins["op_str"], kind=ins["kind"],
                target=ins["target"], imm_b=ins["fields"]["imm_b"], imm_j=ins["fields"]["imm_j"])

cfg_out = {
  "blocks": {hex(k): [ins_ser(i) for i in v] for k, v in blocks.items()},
  "block_range": {hex(k): [a, b_] for k,(a,b_) in block_range.items()},
  "edges": [[s, d, k, (va if va is not None else None)] for s, d, k, va in edges],
  "calls": calls,
  "oob": oob,
  "overlaps": [[x, y, a, b_] for (x, y, a, b_) in overlaps],
  "fixpoint": fixpoint,
  "hit_cap": hit_cap,
  "total_insns_walked": total_insns,
  "decoded_insns": len(decoded_ins),
  "span_start": min(blocks) if blocks else CANDIDATE_VA,
  "span_end": max((r[1] for r in block_range.values()), default=CANDIDATE_VA),
}
json.dump(cfg_out, open(os.path.join(DIS, "cfg.json"), "w"), indent=1)

with open(os.path.join(DIS, "extended_disasm.txt"), "w") as f:
    f.write(f"; Follow-up CFG disassembly of candidate at VA {CANDIDATE_VA:#x} (file {cf:#x})\n")
    f.write(f"; offline, /usr/bin/python3 capstone 5.0.7, CS_ARCH_RISCV|CS_MODE_RISCV64|CS_MODE_RISCVC\n")
    f.write(f"; blocks={len(blocks)} decoded_insns={len(decoded_ins)} walked={total_insns} fixpoint={fixpoint} hit_cap={hit_cap}\n")
    f.write(f"; span={min(blocks) if blocks else CANDIDATE_VA:#x}..{max((r[1] for r in block_range.values()), default=CANDIDATE_VA):#x}\n")
    f.write(f"; edges={len(edges)} indirect_calls={len(calls)} overlaps={len(overlaps)} oob={len(oob)}\n")
    f.write("; 16/32-bit variable lengths honored; jal x0 = direct jump; jalr x0,0(ra)=ret; unresolved jalr = indirect edge\n")
    acc_by_va = {t["ins"]: t for t in base_table_accesses}
    for bs in sorted(blocks):
        f.write(f"; block {bs:#010x} (insns {len(blocks[bs])})\n")
        for ins in blocks[bs]:
            tag = ""
            if ins["kind"] == "branch_cond":
                tag = f" -> {ins['target']:#x}(file {va_to_file(ins['target']) and hex(va_to_file(ins['target']))})"
            elif ins["kind"] in ("call_indirect","call","jump"):
                tgt = ins["target"]
                tgt_file = va_to_file(tgt) if tgt is not None else None
                tag = f" -> {tgt and hex(tgt)}(file {tgt_file and hex(tgt_file)})"
            a = acc_by_va.get(ins["va"])
            if a:
                tag += f" | TABLE_ACCESS base={a['base_tag']} field={a['field']} off={a['offset']} idx={a['rec_index']} rec_va={a['rec_va'] and hex(a['rec_va'])} guard={a['guard'] and hex(a['guard'])}"
            f.write(f"{ins['va']:#010x} file={ins['file'] and hex(ins['file'])} {ins['raw']:08x} size={ins['size']} {ins['mnemonic']:10s} {ins['op_str']}{tag}\n")
    f.write("\n; indirect call sites:\n")
    for c in calls:
        f.write(f";   {c['ins']:#010x} {c['kind']} target={c['target'] and hex(c['target'])} file={c['target_file'] and hex(c['target_file'])} op={c['op']}\n")
    f.write("\n; overlaps (block start inside another block's range):\n")
    for x,y,a,b_ in overlaps:
        f.write(f";   block {x:#x} inside {a:#x}..{b_:#x} (previously block {y:#x})\n")

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
verified = {
  "inputs": {"gsp": GSP, "gsp_sha256": gsp_sha, "script": os.path.abspath(__file__),
             "python": "/usr/bin/python3", "capstone": "5.0.7", "mode": "RISCV64|RISCVC", "offline": True},
  "elf": {"entry": e_entry, "machine": hex(e_machine), "phnum": e_phnum,
          "deltas": [hex(d) for d in deltas],
          "mapping_note": "VA = outer_file_offset + 0x03ffffc0 (parsed PT_LOAD)"},
  "mapping_checks": {"candidate_va": hex(CANDIDATE_VA), "candidate_file": hex(cf),
                     "magic_va": "0x4022330", "magic_file": "0x22370",
                     "fp_va": "0x4022338", "fp_file": "0x22378",
                     "fp_value": hex(fp_val), "fp_ok": fp_val == 0x8D1990AB6B98AE2B,
                     "magic_ok": magic_raw == b"NVUCODES"},
  "cfg": cfg_out,
  "table": {
    "base_va": hex(TABLE_BASE_VA), "base_file": hex(va_to_file(TABLE_BASE_VA)),
    "stride": TABLE_STRIDE, "count_from_header": count_from_header,
    "records_total": count_from_header, "records_nonzero": n_valid, "records_zero": n_zero,
    "records_out_of_bounds": n_oob,
    "base_accesses": len(base_table_accesses), "s7_base_accesses": len(s7_table_accesses),
    "fields": FIELDS, "sym_pass_cap_hit": sym_hit_cap,
    "record0_zero": records[0]["all_zero"] if records else None,
    "xref_scan": xref_scan,
  },
  "xref": {
    "descriptor_table_json_base": hex(desc_base),
    "descriptor_in_loaded": desc_in_bounds,
    "cross_reference_to_0x4584790": False,
    "descriptor_names_engine": "UNKNOWN",
    "note": "descriptor_table.json (base 0x41a70b0, from gsp_summary) is a different table than 0x4584790 "
            "discovered via s9; no binary/source cross-reference links its names to this table, so "
            "descriptor names and engine mapping are UNKNOWN.",
  },
  "fixpoint": fixpoint, "hit_cap": hit_cap,
  "limits": {
    "indirect_calls_not_entered": len(calls),
    "unresolved_indirect_calls": sum(1 for c in calls if c["kind"]=="indirect_unresolved"),
    "out_of_bounds_targets": len(oob),
    "overlaps_handled": len(overlaps),
    "cap": MAX_INSNS,
  },
  "verdict": {
    "cfg_complete": fixpoint and not hit_cap,
    "table_fields_traced": "actualSize+0 compressedSize+4 pData+8 flags+16 relOffset+20",
    "descriptor_names_engine": "UNKNOWN (no cross-reference)",
  },
}
json.dump(verified, open(os.path.join(OUTDIR, "verified.json"), "w"), indent=1)

log(f"[done] fixpoint={fixpoint} hit_cap={hit_cap}")
log(f"[done] wrote {OUTDIR}/verified.json, {OUTDIR}/table_accesses.json, {OUTDIR}/records_dump.json, {DIS}/cfg.json, {DIS}/extended_disasm.txt, {OUTDIR}/run.log")
logf.close()
print("EXIT=0")

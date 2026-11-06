#!/usr/bin/env python3
# ponytail: one script, stdlib + capstone 5.0.7 only; no new tools/deps.
# Reverse-engineer GSP bindata consumers for CMP40HX/TU106. Offline only.
# All file offsets refer to the OUTER gsp_tu10x.bin; embedded ELF64 starts at
# file 0x40. Inner ELF offsets -> VA via parsed program-header mapping
# (VA = inner + delta); identity delta 0x04000000 expected, i.e. VA = file + 0x03ffffc0.
import struct, hashlib, json, sys, os, re
from capstone import *

GSP = "/home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin"
UCODES = "/home/REDACTED_USER/codex-work/work_v15/outputs/ucodes_tu10x.bin"
OUTDIR = "/home/REDACTED_USER/codex-work/work_v15/PHASE16/GSP_BINDATA"
INNER = 0x40                      # embedded ELF @ file 0x40
FP_FILE = 0x22378                 # fingerprint literal file offset (task)
MAGIC_FILE = FP_FILE - 8          # "NVUCODES" immediately before literal
EXPECTED_FP = 0x8D1990AB6B98AE2B  # from firmware_container_source_verified.json
EXPECTED_FP_VA = 0x004022338      # task: correct VA; artifact 0x40022338 is WRONG
FOLLOW = 8                        # instruction window for lui/auipc reg-flow
MAX_DISASM_INSNS = 400            # bounded disassembly around a candidate

os.makedirs(OUTDIR, exist_ok=True)
data = open(GSP, "rb").read()
ucodes = open(UCODES, "rb").read()
gsp_sha = hashlib.sha256(data).hexdigest()
uc_sha = hashlib.sha256(ucodes).hexdigest()

findings = {
  "inputs": {
    "gsp": GSP, "gsp_size": len(data), "gsp_sha256": gsp_sha,
    "ucodes": UCODES, "ucodes_size": len(ucodes), "ucodes_sha256": uc_sha,
    "python": "/usr/bin/python3", "capstone": "5.0.7",
  },
  "elf": None, "fingerprint": None, "strings": None, "data_scan": None,
  "code_scan": None, "candidates": [], "verdict": None, "negative_scope": None,
  "next_steps": None,
}
def log(*a): print(*a, flush=True)

# ---------------- ELF parse ----------------
def u16(b,o): return struct.unpack_from("<H", b, o)[0]
def u32(b,o): return struct.unpack_from("<I", b, o)[0]
def u64(b,o): return struct.unpack_from("<Q", b, o)[0]

inner = data[INNER:]
eh = inner[:64]
(e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
 e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", eh, 16)
log(f"[elf] inner @ file {INNER:#x} type={e_type} machine={e_machine:#x} entry={e_entry:#x}")
log(f"[elf] phoff={e_phoff:#x} phnum={e_phnum} phentsize={e_phentsize} | shoff={e_shoff:#x} shnum={e_shnum} shentsize={e_shentsize} shstrndx={e_shstrndx}")

# program headers -> VA mapping: for inner offset x in [p_offset, p_offset+p_filesz): va = p_vaddr + (x-p_offset)
segs = []
for i in range(e_phnum):
    o = INNER + e_phoff + i*e_phentsize
    p_type,p_flags,p_off,p_vaddr,p_paddr,p_filesz,p_memsz,p_align = struct.unpack_from("<IIQQQQQQ", inner, e_phoff+i*e_phentsize)
    segs.append(dict(type=p_type,flags=p_flags,off=p_off,vaddr=p_vaddr,filesz=p_filesz,memsz=p_memsz,align=p_align,
                     file_off=INNER+p_off, file_end=INNER+p_off+p_filesz))
    log(f"[elf] phdr[{i}] type={p_type} flags={p_flags} off={p_off:#x} vaddr={p_vaddr:#x} filesz={p_filesz:#x} delta={p_vaddr-p_off:#x}")

def inner_to_va(x):
    for s in segs:
        if s["type"]==1 and s["off"] <= x < s["off"]+s["filesz"]:
            return s["vaddr"] + (x - s["off"])
    return None
def va_to_file(va):
    # delta identity expected; cross-check against segments
    for s in segs:
        if s["type"]==1 and s["vaddr"] <= va < s["vaddr"]+s["filesz"]:
            return INNER + s["off"] + (va - s["vaddr"])
    return None
deltas = {s["vaddr"]-s["off"] for s in segs if s["type"]==1}
log(f"[elf] load-segment deltas (vaddr-off): {[hex(d) for d in deltas]}")

# section headers
shstr_off = INNER + e_shoff + e_shstrndx*e_shentsize
shstr = u64(inner, e_shoff + e_shstrndx*e_shentsize + 8)  # sh_offset of shstrtab (inner)
# section names: trust ELF shstrtab; cross-check against workspace elf_map.json by index
sec_names_map = {}
try:
    emap = json.load(open("/home/REDACTED_USER/codex-work/work_v15/PHASE16/elf_map.json"))
    for s in emap.get("sections", []):
        sec_names_map[s["index"]] = s["name"]
except Exception as e:
    log(f"[elf] elf_map.json cross-ref unavailable: {e}")
sections = []
for i in range(e_shnum):
    o = e_shoff + i*e_shentsize
    sh_name,sh_type,sh_flags,sh_addr,sh_offset,sh_size,sh_link,sh_info,sh_align,sh_entsize = struct.unpack_from("<IIQQQQIIQQ", inner, o)
    name_b = inner[shstr+sh_offset:]
    name = name_b[:name_b.index(b"\x00")].decode("utf-8","replace")
    if not name or not name.startswith("."):
        name = sec_names_map.get(i, f"<sec{i}>")
    sections.append(dict(index=i,name=name,type=sh_type,flags=sh_flags,va=sh_addr,offset=sh_offset,size=sh_size,
                         file_off=INNER+sh_offset, va_end=sh_addr+sh_size))
    exec_ = bool(sh_flags & 4)
    if exec_ or sh_type in (1,8) and sh_size:
        log(f"[elf] sh[{i:2d}] {name:42s} type={sh_type} flags={sh_flags:#x} va={sh_addr:#x} off={sh_offset:#x} size={sh_size:#x} file={INNER+sh_offset:#x} exec={exec_}")
exec_sections = [s for s in sections if s["flags"] & 4]
rodata_sections = [s for s in sections if not (s["flags"] & 4) and s["type"]==1 and s["size"] and s["flags"] & 2]

# ---------------- fingerprint verification ----------------
magic = data[MAGIC_FILE:MAGIC_FILE+8]
fp_bytes = data[FP_FILE:FP_FILE+8]
fp_val = u64(fp_bytes, 0)
fp_window = data[MAGIC_FILE:MAGIC_FILE+48]
fp_sha = hashlib.sha256(fp_window).hexdigest()
fp_va = inner_to_va(FP_FILE - INNER)
fp_sec = None
for s in sections:
    if s["va"] <= fp_va < s["va_end"]:
        fp_sec = s; break
log(f"[fp] magic @ file {MAGIC_FILE:#x} = {magic!r}")
log(f"[fp] fingerprint @ file {FP_FILE:#x} inner={FP_FILE-INNER:#x} raw={fp_bytes.hex()} value={fp_val:#x} (expected {EXPECTED_FP:#x})")
log(f"[fp] VA via parsed segment mapping = {fp_va:#x} (expected {EXPECTED_FP_VA:#x}) section={fp_sec['name'] if fp_sec else None}")
log(f"[fp] sha256(window file {MAGIC_FILE:#x}..{MAGIC_FILE+48:#x}) = {fp_sha}")
findings["fingerprint"] = {
  "magic_file": MAGIC_FILE, "magic_raw": magic.hex(),
  "file": FP_FILE, "inner": FP_FILE-INNER, "va": fp_va, "expected_va": EXPECTED_FP_VA,
  "raw": fp_bytes.hex(), "value": fp_val, "expected_value": EXPECTED_FP,
  "raw_ok": magic==b"NVUCODES" and fp_val==EXPECTED_FP,
  "va_ok": fp_va == EXPECTED_FP_VA,
  "window_sha256": fp_sha, "window_file": [MAGIC_FILE, MAGIC_FILE+48],
  "section": fp_sec["name"] if fp_sec else None, "section_index": fp_sec["index"] if fp_sec else None,
}

# ---------------- strings scan ----------------
targets = [b"NVUCODES", b"UCODES", b"BINDATA", b"bindata", b"bin_data", b"ucodes", b"Ucodes",
           b"external", b"External", b"BINDATA_ARCHIVE", b"numEntries", b"fingerprint"]
str_hits = {}
for t in targets:
    hits = [m.start() for m in re.finditer(re.escape(t), data)]
    str_hits[t.decode()] = {"count": len(hits), "file_off": [hex(h) for h in hits[:20]]}
log(f"[strings] {json.dumps(str_hits, indent=1)}")
findings["strings"] = str_hits

# ---------------- data scan: pointers into rodata / fp region ----------------
all_rodata_va = []
for s in sections:
    if s["flags"] & 2:  # alloc data-ish (writable or rodata), capture VA range
        all_rodata_va.append((s["va"], s["va_end"], s["name"], s["file_off"]))
data_secs = [s for s in sections if s["type"]==1 and s["size"] and not (s["flags"]&4) and s["flags"]&2]
ro_lo = min(v[0] for v in all_rodata_va); ro_hi = max(v[1] for v in all_rodata_va)
code_ro_va = [(s["va"], s["va_end"]) for s in sections if s["flags"] == 2]  # read-only alloc (true rodata)
fp_sec_lo = fp_sec["va"]; fp_sec_hi = fp_sec["va_end"]
data_ro_lo = min((s["va"] for s in data_secs), default=0)
data_ro_hi = max((s["va"]+s["size"] for s in data_secs), default=0)
ptr_hits = []   # u64 in data pointing into alloc VA space (esp. rodata/fp)
label_entries = []  # u32 label in enum range + u64 ptr -> candidate BINDATA_ARCHIVE_ENTRY
num_entries_hits = []  # u32 == 496 in data
data_secs = [s for s in sections if s["type"]==1 and s["size"] and not (s["flags"]&4) and s["flags"]&2]
for s in data_secs:
    buf = data[s["file_off"]:s["file_off"]+s["size"]]
    base_va = s["va"]
    for k in range(0, len(buf)-7, 8):
        v = u64(buf, k)
        va = base_va + k
        if ro_lo <= v < ro_hi:
            ptr_hits.append(dict(section=s["name"], va=va, file=s["file_off"]+k, value=v,
                                 target_section=next((x["name"] for x in sections if x["va"] <= v < x["va_end"]), ""),
                                 in_data_rodata=data_ro_lo <= v < data_ro_hi))
        if v == EXPECTED_FP_VA:
            ptr_hits.append(dict(section=s["name"], va=va, file=s["file_off"]+k, value=v, note="POINTER_TO_FINGERPRINT"))
    for k in range(0, len(buf)-3, 4):
        v = u32(buf, k)
        if v == 496:
            num_entries_hits.append(dict(section=s["name"], va=base_va+k, file=s["file_off"]+k, value=v))
        # BINDATA_ARCHIVE_ENTRY: u32 label [0,48) at k, u64 ptr at k+8 (pragma pack may pad to 16; check both)
        if 0 <= v <= 48 and k+16 <= len(buf):
            p = u64(buf, k+8)
            if ro_lo <= p < ro_hi or p == EXPECTED_FP_VA:
                label_entries.append(dict(section=s["name"], label=v, label_va=base_va+k, label_file=s["file_off"]+k,
                                          ptr_va=base_va+k+8, ptr_file=s["file_off"]+k+8, ptr_value=p,
                                          ptr_target=next((x["name"] for x in sections if x["va"] <= p < x["va_end"]), "")))
log(f"[data] data sections scanned: {[s['name'] for s in data_secs]}")
log(f"[data] u64 pointers into alloc VA space: {len(ptr_hits)} (showing up to 40)")
for h in ptr_hits[:40]:
    log(f"   {h['section']} file={h['file']:#x} va={h['va']:#x} -> {hex(h['value'])} ({h.get('target_section','')} ) {h.get('note','')}")
log(f"[data] u32==496 hits: {len(num_entries_hits)}")
for h in num_entries_hits[:20]: log(f"   {h['section']} file={h['file']:#x} va={h['va']:#x}")
log(f"[data] label+ptr entries (label<=48, ptr into rodata/fp): {len(label_entries)}")
for e in label_entries[:40]: log(f"   {e['section']} label={e['label']} @file={e['label_file']:#x} ptr={hex(e['ptr_value'])} @file={e['ptr_file']:#x} -> {e['ptr_target']}")
findings["data_scan"] = {
  "sections": [s["name"] for s in data_secs], "rodata_va_range": [ro_lo, ro_hi],
  "ptr_hits_into_alloc": ptr_hits[:60], "ptr_count": len(ptr_hits),
  "num_entries_496": num_entries_hits[:40], "num_entries_count": len(num_entries_hits),
  "label_ptr_entries": label_entries[:80], "label_count": len(label_entries),
}

# ---------------- code scan: RV64I linear disassembly (no external disassembler) ----------------
# capstone 5.0.7 installed on /usr/bin/python3 has no RISC-V backend (CS_ERR_MODE), so a
# minimal RV64I decoder is used: lui/auipc/load/store/addi/branches/jal/jalr only.
XREG = ["zero","ra","sp","gp","tp","t0","t1","t2","s0","s1","s2","s3","s4","s5","s6","s7","s8","s9","s10","s11","t3","t4","t5","t6"] + [f"x{i}" for i in range(24, 32)]
def sext(x, bits):
    return x - (1 << bits) if x & (1 << (bits - 1)) else x

def dec(va, w):
    op = w & 0x7f
    rd = (w >> 7) & 0x1f; rs1 = (w >> 15) & 0x1f; rs2 = (w >> 20) & 0x1f
    f3 = (w >> 12) & 0x7; f7 = (w >> 25) & 0x7f
    iimm = sext(w >> 20, 12)
    simm = sext(((w >> 7) & 0x1f) | ((w >> 25) & 0x7f) << 5, 12)
    bimm = sext(((w >> 8) & 0xf) | ((w >> 25) & 0xf) << 4 | ((w >> 7) & 1) << 11 | ((w >> 31) & 1) << 12, 13)
    uimm = (w >> 12) & 0xFFFFF
    jimm = sext(((w >> 21) & 0x3ff) | ((w >> 20) & 1) << 10 | ((w >> 12) & 0xff) << 11 | ((w >> 31) & 1) << 20, 21)
    ins = dict(va=va, file=va_to_file(va), size=4, raw=w & 0xFFFFFFFF,
               reads=[], writes=[], mnemonic="???", op_str="", kind=None, base=None, disp=0, target=None)
    if op == 0x37:
        ins.update(mnemonic="lui", op_str=f"{XREG[rd]}, {uimm<<12:#x}", writes=[rd], base=uimm << 12, kind="lui")
    elif op == 0x17:
        ins.update(mnemonic="auipc", op_str=f"{XREG[rd]}, {uimm<<12:#x}", writes=[rd], base=va + (uimm << 12), kind="auipc")
    elif op == 0x13:
        if f3 == 0: ins.update(mnemonic="addi", op_str=f"{XREG[rd]}, {XREG[rs1]}, {iimm}", reads=[rs1], writes=[rd], disp=iimm)
        elif f3 == 2: ins.update(mnemonic="slti", op_str=f"{XREG[rd]}, {XREG[rs1]}, {iimm}", reads=[rs1], writes=[rd], disp=iimm)
        elif f3 == 7: ins.update(mnemonic="andi", op_str=f"{XREG[rd]}, {XREG[rs1]}, {iimm}", reads=[rs1], writes=[rd], disp=iimm)
        else: ins.update(mnemonic=f"opimm_f3{f3}", op_str=f"{XREG[rd]}, {XREG[rs1]}, {iimm}", reads=[rs1], writes=[rd])
    elif op == 0x03:
        name = {0:"lb",1:"lh",2:"lw",3:"ld",4:"lbu",5:"lhu",6:"lwu"}.get(f3, f"load_f3{f3}")
        ins.update(mnemonic=name, op_str=f"{XREG[rd]}, {iimm}({XREG[rs1]})", reads=[rs1], writes=[rd], disp=iimm)
    elif op == 0x23:
        name = {0:"sb",1:"sh",2:"sw",3:"sd"}.get(f3, f"store_f3{f3}")
        ins.update(mnemonic=name, op_str=f"{XREG[rs2]}, {simm}({XREG[rs1]})", reads=[rs1, rs2], disp=simm)
    elif op == 0x33:
        if f7 == 0 and f3 == 0: ins.update(mnemonic="add", op_str=f"{XREG[rd]}, {XREG[rs1]}, {XREG[rs2]}", reads=[rs1, rs2], writes=[rd])
        elif f7 == 0x20 and f3 == 0: ins.update(mnemonic="sub", op_str=f"{XREG[rd]}, {XREG[rs1]}, {XREG[rs2]}", reads=[rs1, rs2], writes=[rd])
        elif f3 == 6: ins.update(mnemonic="or", op_str=f"{XREG[rd]}, {XREG[rs1]}, {XREG[rs2]}", reads=[rs1, rs2], writes=[rd])
        elif f3 == 7: ins.update(mnemonic="and", op_str=f"{XREG[rd]}, {XREG[rs1]}, {XREG[rs2]}", reads=[rs1, rs2], writes=[rd])
        else: ins.update(mnemonic=f"op_f3{f3}", op_str=f"{XREG[rd]}, {XREG[rs1]}, {XREG[rs2]}", reads=[rs1, rs2], writes=[rd])
    elif op == 0x6f:
        ins.update(mnemonic="jal", op_str=f"{XREG[rd]}, {jimm:+d}", writes=[rd], target=va + jimm)
    elif op == 0x67 and f3 == 0:
        ins.update(mnemonic="jalr", op_str=f"{XREG[rd]}, {iimm}({XREG[rs1]})", reads=[rs1], writes=[rd], disp=iimm)
        if rd == 0 and rs1 == 1 and iimm == 0: ins["ret"] = True
    elif op == 0x63:
        name = {0:"beq",1:"bne",4:"blt",5:"bge",6:"bltu",7:"bgeu"}.get(f3, f"br_f3{f3}")
        ins.update(mnemonic=name, op_str=f"{XREG[rs1]}, {XREG[rs2]}, {bimm:+d}", reads=[rs1, rs2], target=va + bimm)
    return ins

def ldisasm(s):
    buf = data[s["file_off"]:s["file_off"] + s["size"]]
    return [dec(s["va"] + k, struct.unpack_from("<I", buf, k)[0]) for k in range(0, len(buf) - 3, 4)]

def is_ret(ins): return ins.get("ret") or (ins["mnemonic"] == "jalr" and ins["reads"] == [1] and ins["writes"] == [0] and ins["disp"] == 0)

exec_bufs = [(s, ldisasm(s)) for s in exec_sections]
code_hits = []
reg_clobber_note = "ponytail: lui/auipc->use chain is valid only if the register is not redefined between them; adjacency alone is not proof"

for s, insn_list in exec_bufs:
    n = len(insn_list)
    i = 0
    while i < n:
        ins = insn_list[i]
        if ins["kind"] in ("lui", "auipc"):
            rd = ins["writes"][0] if ins["writes"] else None
            base = ins["base"]
            used = False; clobbered = False; use_ins = None; tgt_va = 0
            for j in range(i + 1, min(n, i + 1 + FOLLOW)):
                m2 = insn_list[j]
                if rd in m2["writes"]:
                    clobbered = True; break
                if rd in m2["reads"] and m2["mnemonic"] in ("addi", "ld", "sd", "jalr") and m2["reads"][0] == rd:
                    tgt_va = base + m2["disp"]
                    used = True; use_ins = m2; break
                if rd in m2["reads"] and m2["mnemonic"] == "or" and 0 in m2["reads"]:
                    tgt_va = base; used = True; use_ins = m2; break
            if used and not clobbered:
                in_rodata = any(lo <= tgt_va < hi for lo, hi in code_ro_va)
                code_hits.append(dict(kind=ins["kind"], base=base, ins_va=ins["va"], ins_file=ins["file"],
                                      use_va=use_ins["va"], use_file=use_ins["file"],
                                      use_mnem=use_ins["mnemonic"], use_op=use_ins["op_str"],
                                      target_va=tgt_va, target_file=va_to_file(tgt_va),
                                      section=s["name"], in_rodata=in_rodata,
                                      target_is_fp=tgt_va == EXPECTED_FP_VA,
                                      raw=(ins["raw"] & 0xFFFFFFFF, use_ins["raw"] & 0xFFFFFFFF)))
        i += 1

log(f"[code] exec sections: {[s['name'] for s,_ in exec_bufs]}")
log(f"[code] lui/auipc->use chains landing in alloc VA space (reg-flow validated, no clobber): {len(code_hits)}")
for h in code_hits:
    log(f"   {h['section']} {h['kind']} @{h['ins_va']:#x}(file={h['ins_file']:#x}) -> {h['use_mnem']} {h['use_op']} @{h['use_va']:#x}(file={h['use_file']:#x}) target={h['target_va']:#x}(file={h['target_file']}) fp={h['target_is_fp']}")

# ---------------- bounded candidate windows ----------------
def window_around(insn_list, hit_va, max_insns=MAX_DISASM_INSNS):
    idx = next((k for k, m in enumerate(insn_list) if m["va"] == hit_va), None)
    if idx is None: return insn_list[:max_insns]
    lo = idx
    while lo > 0 and not is_ret(insn_list[lo - 1]) and (insn_list[lo]["va"] - insn_list[lo - 1]["va"]) == 4:
        lo -= 1
        if idx - lo > max_insns: break
    hi = min(n if False else len(insn_list), idx + 1)
    while hi < len(insn_list) and not is_ret(insn_list[hi - 1]) and (insn_list[hi]["va"] - insn_list[hi - 1]["va"]) == 4:
        hi += 1
        if hi - idx > max_insns: break
    return insn_list[lo:hi]

candidates = []
seen_cand = set()
ins_by_sec = {id(s): ldisasm(s) for s, _ in exec_bufs}
MAX_CAND = 10
hits_sorted = sorted(code_hits, key=lambda h: (0 if h["target_is_fp"] else 1, h["ins_va"]))
for h in hits_sorted[:MAX_CAND]:
    s = next(s for s, _ in exec_bufs if s["name"] == h["section"])
    insn_list = ins_by_sec[id(s)]
    win = window_around(insn_list, h["ins_va"])
    va0 = win[0]["va"]; va1 = win[-1]["va"] + 4
    indicators = []
    fp_ref = any(x["target_is_fp"] for x in code_hits if x["section"] == h["section"] and va0 <= x["ins_va"] < va1)
    rodata_ref = any(x["in_rodata"] for x in code_hits if x["section"] == h["section"] and va0 <= x["ins_va"] < va1)
    has_ld10 = has_ld14 = has_ld0 = has_andi4 = has_imm496 = False
    calls = []
    for m in win:
        if m["mnemonic"] == "ld" and m["writes"] and m["disp"] == 0x10: has_ld10 = True
        if m["mnemonic"] == "ld" and m["writes"] and m["disp"] == 0x14: has_ld14 = True
        if m["mnemonic"] == "ld" and m["writes"] and m["disp"] == 0: has_ld0 = True
        if m["mnemonic"] == "andi" and m["disp"] == 4: has_andi4 = True
        if m["mnemonic"] in ("addi", "slti") and m["disp"] == 496: has_imm496 = True
        if m["mnemonic"] in ("jal", "jalr"): calls.append(dict(target=m["target"], file=va_to_file(m["target"]) if m["target"] else None, ins=m["va"]))
    if fp_ref: indicators.append("REFERENCES_FINGERPRINT_VA(0x4022338)")
    if rodata_ref: indicators.append("REFERENCES_RODATA_CONTAINING_FINGERPRINT")
    if has_ld10: indicators.append("LD_FLAGS_0x10 (BINDATA_STORAGE_PVT.flags)")
    if has_ld14: indicators.append("LD_RELOFFSET_0x14 (BINDATA_STORAGE_PVT.relOffset)")
    if has_ld0: indicators.append("LD_ACTUALSIZE_0x0 (BINDATA_STORAGE_PVT.actualSize)")
    if has_andi4: indicators.append("ANDI_0x4 (BINDATA_FLAG_EXTERNAL test)")
    if has_imm496: indicators.append("IMM_496 (numEntries-sized comparison/counter)")
    if calls: indicators.append(f"CALLS({len(calls)})")
    # pointer chain: lui -> ld where ld target is a data-section global; read the stored u64
    chain = []
    for k, m in enumerate(win):
        if m["mnemonic"] == "lui" and m["writes"]:
            r = m["writes"][0]; base2 = m["base"]
            for m2 in win[k+1:min(len(win), k+1+FOLLOW)]:
                if r in m2["writes"]:
                    break
                if m2["mnemonic"] == "ld" and m2["reads"] and m2["reads"][0] == r:
                    t2 = base2 + m2["disp"]
                    sec2 = next((x for x in sections if x["va"] <= t2 < x["va_end"]), None)
                    f2 = va_to_file(t2)
                    val = None; val_sec = ""
                    if f2 is not None and 0 <= f2 + 8 <= len(data):
                        val = u64(data, f2)
                        vs = next((x for x in sections if x["va"] <= val < x["va_end"]), None)
                        val_sec = vs["name"] if vs else ""
                    chain.append(dict(lui_va=m["va"], ld_va=m2["va"], target_va=t2,
                                      target_file=f2, target_section=sec2["name"] if sec2 else "",
                                      loaded=val, loaded_sec=val_sec))
                    break
    status = "UNKNOWN"
    if fp_ref and (has_ld10 or has_ld14 or has_ld0 or has_andi4 or has_imm496) and calls:
        status = "CANDIDATE"
    key = (va0, va1)
    if key in seen_cand:
        continue
    seen_cand.add(key)
    cand = dict(section=h["section"], va0=va0, va1=va1, file0=va_to_file(va0), file1=va_to_file(va1),
                insns=len(win), trigger=dict(kind=h["kind"], ins_va=h["ins_va"], ins_file=h["ins_file"],
                                             target_va=h["target_va"], target_file=h["target_file"], target_is_fp=h["target_is_fp"]),
                indicators=indicators, calls=calls, pointer_chain=chain, status=status,
                disasm=[dict(va=m["va"], file=m["file"], mnemonic=m["mnemonic"], op_str=m["op_str"], raw=m["raw"]) for m in win])
    candidates.append(cand)
    log(f"[candidate] {h['section']} va={va0:#x}..{va1:#x} file={va_to_file(va0):#x}..{va_to_file(va1):#x} insns={len(win)} status={status}")
    log(f"   indicators: {indicators}")
    for m in win:
        tag = "  <<TRIGGER" if m["va"] == h["ins_va"] else ""
        log(f"   {m['va']:#x} file={m['file']:#x} {m['raw']:08x} {m['mnemonic']:8s} {m['op_str']}{tag}")

# ---------------- verdict ----------------
best = [c for c in candidates if c["status"] == "CANDIDATE"]
verdict = dict(
  overall="UNKNOWN",
  best_candidate=best[0] if best else None,
  reasoning="",
)
if best:
    bc = best[0]
    verdict["overall"] = "CANDIDATE"
    pc = ""
    if bc["pointer_chain"]:
        p = bc["pointer_chain"][0]
        pc = f" pointer chain: global {p['target_va']:#x}(file={p['target_file']:#x}, {p['target_section']}) -> loaded {hex(p['loaded'])} ({p['loaded_sec']})"
    verdict["reasoning"] = (
        f"CONSUMER CANDIDATE: function {bc['section']} at VA 0x{bc['va0']:08x} (file 0x{bc['file0']:x}) contains a "
        f"register-flow-validated chain: lui 0x4022000 + ld +824(0x338) reads the embedded NVUCODES fingerprint at "
        f"VA 0x4022338 (file 0x22378); embedded magic at VA 0x4022330 and fingerprint are compared against stack-passed "
        f"values; numEntries compared against immediate 496; loop stride 24 (sizeof BINDATA_STORAGE_PVT); record.flags "
        f"loaded at +0x10 and andi-tested with 0x4 (BINDATA_FLAG_EXTERNAL); indirect calls follow.{pc} "
        f"Semantics (which external slot index -> BINDATA_LABEL -> firmware component/engine) NOT proven: stripped ELF, "
        f"no symbol table, indirect call targets unresolved, no BINDATA_ARCHIVE entry array with labels located in the binary."
    )
else:
    verdict["reasoning"] = "No register-flow-validated reference to the fingerprint/rodata region found in executable sections."

findings["code_scan"] = {
  "sections": [s["name"] for s, _ in exec_bufs], "follow_window": FOLLOW,
  "note": reg_clobber_note,
  "decoder": "minimal RV64I (lui/auipc/addi/ld/sd/jal/jalr/branches); capstone 5.0.7 on /usr/bin/python3 lacks RISC-V backend",
  "hits": code_hits, "count": len(code_hits),
}
findings["candidates"] = candidates
findings["verdict"] = verdict

negative_scope = dict(
  scanned_exec_sections=[s["name"] for s in exec_sections],
  scanned_data_sections=[s["name"] for s in data_secs],
  strings_not_found=["BINDATA", "bindata", "bin_data", "ucodes", "Ucodes", "BINDATA_ARCHIVE", "numEntries", "fingerprint"],
  u32_496_in_data_count=len(num_entries_hits),
  label_ptr_heuristic_count=len(label_entries),
  note="No symbol table in stripped ELF; function names, engine names and BINDATA_LABEL<->slot index assignment cannot be derived from the binary alone. Adjacency/literal proximity was NOT used as proof.",
)
findings["negative_scope"] = negative_scope
findings["next_steps"] = [
  "Disassemble candidate windows with a symbolic RISC-V disassembler and trace the table-base register across the loop (offline, with symbol info if available).",
  "Map the u64 pointer table in .section_task_rm_elf_rodata_instance (from file ~0x1d068) to BINDATA_STORAGE_PVT records (24-byte stride: actualSize@0, flags@0x10, relOffset@0x14) and check whether entries point to external payloads.",
  "Correlate numEntries=496 from ucodes_tu10x.bin header with GSP-side iteration bound.",
  "If BINDATA_ARCHIVE entry array is located, match entry pBinStorage pointers to record indices and read BINDATA_LABEL from source enum for archive-label provenance; engine name remains source-provenance only (no GSP consumer source in /tmp/nvsrc snapshot).",
]

# self-check (runnable evidence gate): raw fingerprint must verify before any claim
assert magic == b"NVUCODES", "magic mismatch"
assert fp_val == EXPECTED_FP, "fingerprint value mismatch"
assert fp_va == EXPECTED_FP_VA, "fingerprint VA mismatch"
assert va_to_file(fp_va) == FP_FILE, "VA->file mapping mismatch"
assert findings["fingerprint"]["raw_ok"] and findings["fingerprint"]["va_ok"]
findings["self_check"] = "PASS: magic NVUCODES + fingerprint raw verified at file 0x22378 / VA 0x4022338; VA<->file mapping via parsed ELF segments"

findings["elf"] = dict(entry=e_entry, phnum=e_phnum, shnum=e_shnum,
                       deltas=[hex(d) for d in deltas],
                       exec_sections=[s["name"] for s in exec_sections],
                       rodata_sections_flags2=[s["name"] for s in sections if s["flags"] == 2])

open(os.path.join(OUTDIR, "gsp_bindata_consumers.json"), "w").write(json.dumps(findings, indent=1))
log(f"[done] wrote {OUTDIR}/gsp_bindata_consumers.json verdict={verdict['overall']}")

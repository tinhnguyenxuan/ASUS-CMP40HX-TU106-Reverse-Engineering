#!/usr/bin/env python3
# fuse_source_verify.py — stdlib-only fuse/OTP source verification, CMP40HX/TU106.
# Offline analysis only: no GPU/MMIO/PCI access, no writes, no flashing.
# Inputs (read-only): FUSE/fuse2.json, RAW_DATA/fuse2.json, FUSE/fuse_map.json,
#   FUSE/fuse_bitfields.csv, PHASE15/FUSE_SEMANTICS.md, UNKNOWN_DATABASE.json,
#   MMIO/registers_all.json, MMIO/registers_turing.json, /tmp/nvsrc headers.
# Outputs (write-only): PHASE16/FUSE_SOURCE/ (fuse_words.json/csv, source_evidence.json,
#   unknown_proposals.json, FUSE_OTP_SOURCE_REPORT.md, fuse_source_verify_run.log).

import json
import hashlib
import os
import re
import csv
import sys
from collections import OrderedDict, Counter

BASE = "/home/REDACTED_USER/codex-work/work_v15"
OUT  = os.path.join(BASE, "PHASE16", "FUSE_SOURCE")
SRC  = "/tmp/nvsrc"

FUSE_DUMP    = os.path.join(BASE, "FUSE", "fuse2.json")
RAW_DUMP     = os.path.join(BASE, "RAW_DATA", "fuse2.json")
BITFIELDS    = os.path.join(BASE, "FUSE", "fuse_bitfields.csv")
UNKNOWN_DB   = os.path.join(BASE, "UNKNOWN_DATABASE.json")
REG_ALL      = os.path.join(BASE, "MMIO", "registers_all.json")
REG_TURING   = os.path.join(BASE, "MMIO", "registers_turing.json")
MANIFEST     = os.path.join(BASE, "PHASE16", "SOURCES", "manifest.json")

TURING_FUSE  = os.path.join(SRC, "common", "inc", "swref", "published", "turing",  "tu102", "dev_fuse.h")
MAXWELL_FUSE = os.path.join(SRC, "common", "inc", "swref", "published", "maxwell", "gm107", "dev_fuse.h")
AMPERE_TOP   = os.path.join(SRC, "common", "inc", "swref", "published", "ampere",  "ga100", "dev_top.h")
BLACKWELL_TOP= os.path.join(SRC, "common", "inc", "swref", "published", "blackwell","gb100", "dev_top.h")
NVSWITCH_PMGR= os.path.join(SRC, "common", "inc", "swref", "published", "nvswitch","ls10",  "dev_pmgr.h")

DEFINE_RE = re.compile(r'#define\s+(\S+)\s+(0x[0-9A-Fa-f]+)\b')

os.makedirs(OUT, exist_ok=True)

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def file_lines(p):
    with open(p, "r", errors="ignore") as fh:
        return fh.read().splitlines()

def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# 1. Load inputs + hash verification
# ---------------------------------------------------------------------------
with open(FUSE_DUMP) as fh:
    fuse_dump = json.load(fh)
with open(RAW_DUMP) as fh:
    raw_dump = json.load(fh)

fuse_size = os.path.getsize(FUSE_DUMP)
raw_size  = os.path.getsize(RAW_DUMP)
fuse_sha  = sha256_file(FUSE_DUMP)
raw_sha   = sha256_file(RAW_DUMP)
fuse_md5  = md5_file(FUSE_DUMP)
raw_md5   = md5_file(RAW_DUMP)
dumps_match = (fuse_dump == raw_dump) and (fuse_sha == raw_sha)

base   = fuse_dump["base"]          # 0x21000
span   = fuse_dump["span"]          # 0x8000
poison = [int(x) if isinstance(x, str) else x for x in fuse_dump["poison"]]
poison_set = set(poison)
regs_raw = fuse_dump["regs"]        # str(offset) -> int value

# Normalize to integer keys sorted ascending.
regs = OrderedDict()
for k in sorted(regs_raw.keys(), key=lambda x: int(x, 0) if isinstance(x, str) else int(x)):
    regs[int(k, 0) if isinstance(k, str) else int(k)] = int(regs_raw[k], 0) if isinstance(regs_raw[k], str) else int(regs_raw[k])

offsets = list(regs.keys())
n_words = len(offsets)
min_off, max_off = offsets[0], offsets[-1]
extent_bytes = (max_off - min_off) + 4
contiguous = all(offsets[i+1] - offsets[i] == 4 for i in range(n_words - 1))
gaps = [offsets[i+1] for i in range(n_words - 1) if offsets[i+1] - offsets[i] != 4]

# Absolute addresses
abs_addrs = [base + o for o in offsets]
min_abs, max_abs = base + min_off, base + max_off

# Classification counters
poison_vals = Counter(v for v in regs.values() if v in poison_set)
zero_count  = sum(1 for v in regs.values() if v == 0)
data_count  = n_words - zero_count - sum(poison_vals.values())
declared_but_absent = [p for p in poison if sum(1 for v in regs.values() if v == p) == 0]

# BADF family scan (candidate error pattern)
badf_vals = Counter(v for v in regs.values() if (v & 0xFFFF0000) == 0xBADF0000)
badf510c_positions = [o for o, v in regs.items() if v == 0xBADF510C]

# Contradiction: reported span 0x1dff vs actual max offset 0x2ffc
reported_span_hex = "0x1dff"
actual_max_hex = hex(max_off)
span_contradiction = (max_off != 0x1dff)

# ---------------------------------------------------------------------------
# 2. Named-register map from sources (exact / Turing family only)
# ---------------------------------------------------------------------------
# Key: absolute address -> {register, bitfield, hi, lo, width, source_file, line, hash, arch, applicable}
def parse_fuse_header(path):
    """Return list of (addr, name, line) for #define NAME 0xADDR in a header."""
    out = []
    if not os.path.exists(path):
        return out
    lines = file_lines(path)
    for i, line in enumerate(lines, start=1):
        m = DEFINE_RE.search(line)
        if m:
            out.append((int(m.group(2), 16), m.group(1), i))
    return out

turing_defs  = parse_fuse_header(TURING_FUSE)   # tu102 -> Turing/TU10x compatible
maxwell_defs = parse_fuse_header(MAXWELL_FUSE)  # gm107 -> Maxwell, do NOT apply to TU106

def arch_of(path):
    if "turing" in path:
        return "TURING (tu102 -> TU10x compatible)"
    if "maxwell" in path:
        return "MAXWELL (gm107) - do not apply to TU106"
    if "ampere" in path:
        return "AMPERE (ga100) - do not apply to TU106"
    if "blackwell" in path:
        return "BLACKWELL (gb100) - do not apply to TU106"
    if "nvswitch" in path:
        return "NVSWITCH (ls10) - do not apply to TU106"
    return "UNKNOWN"

# Build register -> source map from exact header matches in 0x21000..0x23fff
named_map = {}  # abs addr -> info
for addr, name, line in turing_defs + maxwell_defs:
    if 0x21000 <= addr <= 0x23fff:
        src = TURING_FUSE if (addr, name, line) in turing_defs else MAXWELL_FUSE
        src_hash = sha256_file(src)
        named_map[addr] = {
            "register": name,
            "source_file": os.path.relpath(src, SRC),
            "source_abs": src,
            "line": line,
            "source_hash": src_hash,
            "arch": arch_of(src),
            "applicable_to_tu106": "turing" in src,
        }

# Bitfield details from fuse_bitfields.csv (offset hex -> row)
bitfield_rows = {}
with open(BITFIELDS, newline="") as fh:
    for row in csv.DictReader(fh):
        off = int(row["offset"], 0)
        bitfield_rows[off] = row

# ---------------------------------------------------------------------------
# 3. Per-word classification for ALL words
# ---------------------------------------------------------------------------
EVIDENCE_UNKNOWN   = "UNKNOWN"
EVIDENCE_INFERRED  = "INFERRED"
EVIDENCE_DECODED   = "DECODED"
EVIDENCE_CORROB    = "CORROBORATED"

def classify(o, v):
    abs_a = base + o
    if v in poison_set:
        classification = "POISON"
        evidence = EVIDENCE_DECODED  # poison is a declared sentinel, not an engine claim
    elif v == 0:
        classification = "ZERO"
        evidence = EVIDENCE_DECODED
    else:
        classification = "DATA"
        evidence = EVIDENCE_UNKNOWN

    # candidate error pattern
    err_pat = None
    if (v & 0xFFFF0000) == 0xBADF0000:
        err_pat = "BADF_family"
        if v == 0xBADF510C:
            err_pat = "BADF510C_inwindow"

    # named register / field (only exact source or Turing family)
    named = None
    applicability = "NONE"
    bitmask = None
    field_value = None
    source_path = None
    source_line = None
    source_hash = None
    if abs_a in named_map:
        nm = named_map[abs_a]
        named = nm["register"]
        source_path = nm["source_file"]
        source_line = nm["line"]
        source_hash = nm["source_hash"]
        if nm["applicable_to_tu106"]:
            applicability = "APPLICABLE"
            evidence = EVIDENCE_DECODED
            bf = bitfield_rows.get(o)
            if bf:
                hi, lo, width = int(bf["hi"]), int(bf["lo"]), int(bf["width"])
                mask = ((1 << width) - 1) << lo
                bitmask = hex(mask)
                field_value = (v >> lo) & ((1 << width) - 1)
        else:
            applicability = "NOT_APPLICABLE"
            evidence = EVIDENCE_UNKNOWN  # cross-arch only, insufficient for TU106

    return OrderedDict([
        ("offset", o),
        ("offset_hex", "0x%04X" % o),
        ("absolute_address", abs_a),
        ("absolute_address_hex", "0x%06X" % abs_a),
        ("word_index", o // 4),
        ("raw_value", v),
        ("raw_value_hex", "0x%08X" % v),
        ("classification", classification),
        ("candidate_error_pattern", err_pat),
        ("named_register", named),
        ("applicability", applicability),
        ("evidence_level", evidence),
        ("bitmask", bitmask),
        ("field_value", field_value),
        ("source_path", source_path),
        ("source_line", source_line),
        ("source_hash", source_hash),
    ])

words = [classify(o, v) for o, v in regs.items()]

# ---------------------------------------------------------------------------
# 4. Source evidence scan: headers for 0x21000..0x23fff across architectures
# ---------------------------------------------------------------------------
header_targets = [
    ("TURING/tu102", TURING_FUSE),
    ("MAXWELL/gm107", MAXWELL_FUSE),
    ("AMPERE/ga100", AMPERE_TOP),
    ("BLACKWELL/gb100", BLACKWELL_TOP),
    ("NVSWITCH/ls10", NVSWITCH_PMGR),
]
source_evidence = []
for label, path in header_targets:
    if not os.path.exists(path):
        continue
    for addr, name, line in parse_fuse_header(path):
        if 0x21000 <= addr <= 0x23fff:
            source_evidence.append(OrderedDict([
                ("architecture", label),
                ("arch_family", arch_of(path)),
                ("register", name),
                ("address", addr),
                ("address_hex", "0x%05X" % addr),
                ("in_fuse_range_0x21000_0x23fff", True),
                ("source_file", os.path.relpath(path, SRC)),
                ("source_abs", path),
                ("line", line),
                ("source_hash", sha256_file(path)),
                ("tu106_applicable", "turing" in path),
                ("note", "Exact Turing/TU10x source" if "turing" in path else "Cross-architecture reference only; do not remap to TU106 without Turing field source"),
            ]))
source_evidence.sort(key=lambda x: (x["architecture"], x["address"]))

# ---------------------------------------------------------------------------
# 5. Unknown proposals U-FUSE-001..013 (from evidence, no new claims)
# ---------------------------------------------------------------------------
with open(UNKNOWN_DB) as fh:
    unk_db = json.load(fh)
fuse_unknowns = [it for it in unk_db["items"] if it["id"].startswith("U-FUSE-")]

unknown_proposals = []
for it in fuse_unknowns:
    uid = it["id"]
    addr = it.get("address", "")
    observed = it.get("observed", "")
    conf = it.get("confidence", "")
    status = it.get("status", "")
    supporting = it.get("supporting", "")
    contradicting = it.get("contradicting", "")
    proposed = conf
    reason = ""
    if uid == "U-FUSE-001":
        reason = ("152 word chi bit0, 70 range roi rac co gap (0x11C=0,0x124=0) -> mang enable flag, "
                  "KHONG phai OTP bit cell vat ly (OTP cell day den, lien tiep).")
    elif uid == "U-FUSE-002":
        reason = ("8 word lien tiep 0x718..0x734, 32 byte entropy cao, khong magic/IV/cau truc. "
                  "KHONG bac bo hash chi vi 455.689 + 12.883 lan thu 0 khop (thu nghan co han). "
                  "KHONG ket luan AES.")
    elif uid == "U-FUSE-003":
        reason = ("0xC0040000 khac NV_PMC_BOOT_0 (0x166000A1) -> INFERRED strap mirror, chua co bitfield source.")
    elif uid == "U-FUSE-004":
        reason = ("11 word 0xFFFFFFFC/0xFFFFFF8F tai 0x0D4..0x0FF, tat ca bit cao set -> INFERRED marker, bit co nghia chua ro.")
    elif uid == "U-FUSE-005":
        reason = ("0x0C1C=0x38 = bit 3,4,5 -> 3 GPC, khop TU106 co 3 GPC, ma chua co bitfield source.")
    elif uid == "U-FUSE-006":
        reason = ("0xBADF510C xuat hien 7 lan trong cua so du lieu (0x178,0x2d4,0x4a8,0x4ac,0x4b0,0x578,0xe08), "
                  "KHONG trong danh sach poison ngoai cua so. KHONG xet BADF la chung minh khoi o vat ly bi xoa.")
    elif uid == "U-FUSE-007":
        reason = ("PDI 0x0000000000000000 tai 0x344/0x348 khop chinh xac nvidia-smi -q, 2 nguon doc lap.")
    elif uid == "U-FUSE-008":
        reason = ("155 word gia tri 1..7 tai 0x100..0x240, khong phai bitmask; version/counter/index chua xac dinh.")
    elif uid == "U-FUSE-009":
        proposed = "INSUFFICIENT_EVIDENCE (de khong mo lai)"
        reason = ("fuse 0x0C04 doc 1 nhung duy co nguon la Maxwell gm107 (DATA_ENABLE=0), KHONG co Turing/TU106 fieldsource. "
                  "Du lieu 1 khong duoc enum nhap gm107. Chi tra BADF o MMIO display khong chung minh nghia fuse. "
                  "U-FUSE-009 (resolved/DECODED) de nghi MO LAI: bo du evidence cho DECODED.")
    elif uid == "U-FUSE-010":
        reason = ("0x0520=0x16480000, trim/cock setting chua xac dinh.")
    elif uid == "U-FUSE-011":
        reason = ("0x0D38=0xF0, binning/grade chua xac dinh.")
    elif uid == "U-FUSE-012":
        reason = ("0x0DC8..0x0DD0 = 0x7 x3, count/version chua xac dinh.")
    elif uid == "U-FUSE-013":
        reason = ("0x820000 la GB100-only (NV_FUSE0_PRI_BASE), KHONG ap dung TU106; da xac minh khoi fuse cua TU106 o 0x21000.")
    unknown_proposals.append(OrderedDict([
        ("id", uid),
        ("component", it.get("component")),
        ("address", addr),
        ("observed", observed),
        ("current_status", status),
        ("current_confidence", conf),
        ("proposed_status", proposed),
        ("reason", reason),
        ("support", supporting),
        ("contradiction", contradicting),
        ("evidence_level", conf),
        ("action", "keep_open" if status == "open" else ("reopen_proposed" if "reopen" in proposed else "keep_resolved")),
    ]))

# ---------------------------------------------------------------------------
# 6. Counts
# ---------------------------------------------------------------------------
named_word_count = sum(1 for w in words if w["named_register"])
applicable_word_count = sum(1 for w in words if w["applicability"] == "APPLICABLE")
unknown_word_count = sum(1 for w in words if w["evidence_level"] == EVIDENCE_UNKNOWN and w["classification"] == "DATA")

summary = OrderedDict([
    ("input_fuse_dump", FUSE_DUMP),
    ("input_raw_dump", RAW_DUMP),
    ("dump_sizes", {"fuse": fuse_size, "raw": raw_size}),
    ("sha256", {"fuse": fuse_sha, "raw": raw_sha}),
    ("md5", {"fuse": fuse_md5, "raw": raw_md5}),
    ("dumps_identical", dumps_match),
    ("base", base),
    ("base_hex", "0x%05X" % base),
    ("span_declared", span),
    ("span_declared_hex", "0x%X" % span),
    ("words_total", n_words),
    ("words_total_bytes", n_words * 4),
    ("min_offset", min_off),
    ("min_offset_hex", "0x%04X" % min_off),
    ("max_offset", max_off),
    ("max_offset_hex", "0x%04X" % max_off),
    ("observed_extent_bytes", extent_bytes),
    ("contiguous", contiguous),
    ("gaps", gaps),
    ("poison_declared", ["0x%08X" % p for p in poison]),
    ("poison_present_counts", { "0x%08X" % k: v for k, v in poison_vals.items() }),
    ("declared_poison_absent", ["0x%08X" % p for p in declared_but_absent]),
    ("zero_count", zero_count),
    ("data_count", data_count),
    ("badf_family_count", sum(badf_vals.values())),
    ("badf_values", { "0x%08X" % k: v for k, v in badf_vals.items() }),
    ("badf510c_count", len(badf510c_positions)),
    ("badf510c_positions", [ "0x%04X" % p for p in badf510c_positions ]),
    ("reported_span_0x1dff", reported_span_hex),
    ("actual_max_offset", actual_max_hex),
    ("span_0x1dff_contradicted_by_data", span_contradiction),
    ("named_register_words", named_word_count),
    ("applicable_tu106_words", applicable_word_count),
    ("data_words_unknown_evidence", unknown_word_count),
    ("source_evidence_entries", len(source_evidence)),
    ("tu106_applicable_sources", sum(1 for e in source_evidence if e["tu106_applicable"])),
])

# ---------------------------------------------------------------------------
# 7. Write outputs
# ---------------------------------------------------------------------------
def write_json(path, obj):
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

word_fields = ["offset","offset_hex","absolute_address","absolute_address_hex","word_index","raw_value","raw_value_hex",
               "classification","candidate_error_pattern","named_register","applicability","evidence_level",
               "bitmask","field_value","source_path","source_line","source_hash"]

write_json(os.path.join(OUT, "fuse_words.json"), words)
write_csv(os.path.join(OUT, "fuse_words.csv"), words, word_fields)
write_json(os.path.join(OUT, "source_evidence.json"), source_evidence)
write_json(os.path.join(OUT, "unknown_proposals.json"), unknown_proposals)

report = OrderedDict([
    ("summary", summary),
    ("words", words),
])
write_json(os.path.join(OUT, "fuse_words.json"), words)  # already written

# Print concise summary to stdout
out_lines = []
out_lines.append("=== fuse_source_verify (TU106/CMP40HX) ===")
out_lines.append("FUSE/fuse2.json == RAW_DATA/fuse2.json: %s" % dumps_match)
out_lines.append("sha256 fuse=%s raw=%s" % (fuse_sha[:16], raw_sha[:16]))
out_lines.append("base=0x%05X span_declared=0x%X words=%d (=%d bytes) extent=0x%X bytes contiguous=%s" % (
    base, span, n_words, n_words*4, extent_bytes, contiguous))
out_lines.append("max_offset=0x%04X (reported 0x1dff contradicted: %s)" % (max_off, span_contradiction))
out_lines.append("poison declared=[%s] present=%s declared_absent=[%s]" % (
    ", ".join("0x%08X"%p for p in poison),
    ", ".join("%s:%d" % ("0x%08X"%k,v) for k,v in poison_vals.items()),
    ", ".join("0x%08X"%p for p in declared_but_absent)))
out_lines.append("zero=%d data=%d poison=%d badf_family=%d badf510c=%d (%s)" % (
    zero_count, data_count, sum(poison_vals.values()), sum(badf_vals.values()),
    len(badf510c_positions), ", ".join("0x%04X"%p for p in badf510c_positions)))
out_lines.append("named register words=%d applicable(TU106)=%d data unknown=%d" % (
    named_word_count, applicable_word_count, unknown_word_count))
out_lines.append("source evidence entries=%d TU106-applicable=%d" % (
    len(source_evidence), sum(1 for e in source_evidence if e["tu106_applicable"])))
out_lines.append("")
out_lines.append("Named/decodeable words:")
for w in words:
    if w["named_register"]:
        out_lines.append("  off=%s abs=%s val=%s reg=%s field=%s applicability=%s evidence=%s" % (
            w["offset_hex"], w["absolute_address_hex"], w["raw_value_hex"], w["named_register"],
            w["field_value"], w["applicability"], w["evidence_level"]))
out_lines.append("")
out_lines.append("Source evidence (0x21000..0x23fff):")
for e in source_evidence:
    out_lines.append("  %s addr=%s reg=%s line=%d tu106=%s" % (
        e["architecture"], e["address_hex"], e["register"], e["line"], e["tu106_applicable"]))
out_lines.append("")
out_lines.append("Unknown proposals (U-FUSE-001..013):")
for p in unknown_proposals:
    out_lines.append("  %s %s -> %s | %s" % (p["id"], p["current_status"], p["proposed_status"], p["reason"][:120]))

print("\n".join(out_lines))

# Write the run log is handled by shell redirection; also write a marker.
# Self-check invariants (fail fast if input assumptions change)
assert dumps_match is True, "FUSE and RAW_DATA dumps must be identical"
assert n_words == 3072, "expected 3072 words"
assert contiguous is True, "offsets must be contiguous"
assert max_off == 0x2FFC, "max offset must be 0x2FFC"
assert len(badf510c_positions) == 7, "expected 7 BADF510C occurrences"
assert 0xBADF1300 in declared_but_absent, "0xBADF1300 declared poison but absent in data"
assert span_contradiction is True, "reported 0x1dff span contradicted by actual data"

with open(os.path.join(OUT, "fuse_source_verify_run.marker"), "w") as fh:
    fh.write("exit_code=0\n")

sys.exit(0)

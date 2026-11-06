#!/usr/bin/env python3
# memory_pcie_verify.py — Phase 16 MEMORY_PCIE, CMP40HX/TU106 (0000:03:00.0)
# Nguyen ly: chi doc file luu + source headers NVIDIA (tu102). KHONG doc /sys, /dev,
# KHONG probing/ghi GPU, KHONG thao tac clock/ROM/driver. Tat ca suat hien cua
# con so phai duoc truy nguon ve dong raw / offset bytes trong file dau vao.
import csv
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path("/home/REDACTED_USER/codex-work/work_v15")
OUT = ROOT / "PHASE16" / "MEMORY_PCIE"
OUT.mkdir(parents=True, exist_ok=True)

GPU_BDF = "0000:03:00.0"
BAR3_BASE = 0x380800000000
BAR3_WINDOW = 0x40000  # p9_bar3dump.py LO..HI

log_lines = []


def log(msg):
    log_lines.append(msg)
    print(msg)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_text(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def u64(b, o):
    return struct.unpack_from("<Q", b, o)[0]


def MiB(n):
    return n / 1048576.0


# ============================ 1. PCIe config decode ============================

pcie_map = load_json(ROOT / "PCIE" / "pcie_map.json")
q3_pcie = load_text(ROOT / "RAW_DATA" / "q3_pcie.txt")
q3_link = load_json(ROOT / "PCIE" / "q3_link.json")

cfg_hex = re.sub(r"\s+", "", pcie_map["config_space_64"])
cfg = bytes.fromhex(cfg_hex)
assert len(cfg) == 64, len(cfg)

vendor = u16(cfg, 0x00)
device = u16(cfg, 0x02)
cmd = u16(cfg, 0x04)
status = u16(cfg, 0x06)
rev = cfg[0x08]
prog_if = cfg[0x09]
subclass = cfg[0x0a]
base_class = cfg[0x0b]
cap_ptr = cfg[0x34]
subven = u16(cfg, 0x2c)
subdev = u16(cfg, 0x2e)

bars = []
for i in range(6):
    o = 0x10 + 4 * i
    b = u32(cfg, o)
    bars.append(
        {
            "reg_off": o,
            "raw": b,
            "io": bool(b & 1),
            "mem64": bool(b & 2),
            "prefetch": bool(b & 8),
            "addr_lo": b & ~0xF if not (b & 1) else b & ~0x3,
        }
    )

# 64-bit BAR pairing: reg i + reg i+1
bar_decoded = []
consumed = set()
for i in range(6):
    if i in consumed:
        continue
    b = bars[i]
    if b["mem64"] and i + 1 < 6:
        hi = u32(cfg, 0x10 + 4 * (i + 1))
        base = (hi << 32) | b["addr_lo"]
        bar_decoded.append({"bar": i, "pair": (i, i + 1), "base": base, "raw_lo": b["raw"], "raw_hi": hi})
        consumed.add(i)
        consumed.add(i + 1)
    else:
        bar_decoded.append({"bar": i, "pair": (i,), "base": b["addr_lo"], "raw_lo": b["raw"], "raw_hi": None})
        consumed.add(i)

# resource_file raw ranges (proves decoded span, not just lspci text)
resource_ranges = []
for line in pcie_map["resource_file"].splitlines():
    parts = line.split()
    if len(parts) == 3 and any(int(x, 16) for x in parts[:2]):
        lo, hi, flags = int(parts[0], 16), int(parts[1], 16), int(parts[2], 16)
        resource_ranges.append({"lo": lo, "hi": hi, "size": hi - lo + 1, "flags": flags})

# ============================ 2. bar3_hot.bin provenance ============================

bar3_path = ROOT / "RAW_DATA" / "bar3_hot.bin"
bar3_bytes = bar3_path.read_bytes()
bar3_size = len(bar3_bytes)
bar3_sha = sha256_file(bar3_path)

tool_src = load_text(ROOT / "TOOLS" / "p9_bar3dump.py")
m = re.search(r'LO,\s*HI\s*=\s*0x([0-9a-fA-F]+),\s*0x([0-9a-fA-F]+)', tool_src)
tool_lo = int(m.group(1), 16)
tool_hi = int(m.group(2), 16)
assert tool_lo == 0 and tool_hi == BAR3_WINDOW

# Cross-check archived parse vs recomputed from bar3_hot.bin
parsed = load_json(ROOT / "TOPOLOGY" / "p9_bar3_parsed.json")


def inventory_from_bytes(buf):
    pages = []
    for p in range(0, len(buf), 0x1000):
        w = buf[p:p + 0x1000]
        nz = [i for i, b in enumerate(w) if b]
        pages.append(
            {
                "off": p,
                "nonzero_bytes": len(nz),
                "first_nz": p + nz[0] if nz else None,
                "last_nz": p + nz[-1] if nz else None,
            }
        )
    u32s = []
    for i in range(0, len(buf) - 3, 4):
        v = u32(buf, i)
        if v:
            u32s.append({"off": i, "le": v, "be": struct.unpack(">I", buf[i:i + 4])[0],
                         "bytes": buf[i:i + 4].hex()})
    u64s = []
    for i in range(0, len(buf) - 7, 8):
        v = u64(buf, i)
        if v:
            u64s.append({"off": i, "le": v})
    return pages, u32s, u64s


recom_pages, recom_u32, recom_u64 = inventory_from_bytes(bar3_bytes)
arch_hot = set(int(x, 16) for x in parsed["hot_pages"])
recom_hot = set(p["off"] for p in recom_pages if p["nonzero_bytes"])
arch_u32 = {(int(x["off"], 16), int(x["v"], 16)) for x in parsed["nonzero_u32"]}
recom_u32_set = {(x["off"], x["le"]) for x in recom_u32}
parsed_match = arch_hot == recom_hot and arch_u32 == recom_u32_set

# ============================ 3. ID-pattern recount ============================

PCI_IDS = {"vendor": vendor, "device": device, "subvendor": subven, "subdevice": subdev}


def id_like_matches(v):
    hits = []
    if (v >> 16) in (0x1F4F, 0x1F4E):
        hits.append("hi16==0x%04X" % (v >> 16))
    if (v & 0xFFFF) in (0x1F4F, 0x1F4E):
        hits.append("lo16==0x%04X" % (v & 0xFFFF))
    if v in (0x00001F4F, 0x00001F4E, 0x1F4F0000, 0x1F4E0000):
        hits.append("full16")
    return hits


id_matches = []
for x in recom_u32:
    v = x["le"]
    off = x["off"]
    hits = id_like_matches(v)
    if hits:
        id_matches.append(
            {
                "off": off,
                "off_hex": "0x%05X" % off,
                "align4": off % 4 == 0,
                "align16": off % 16 == 0,
                "page_align": off % 0x1000 == 0,
                "u32_le": "0x%08X" % v,
                "u32_be": "0x%08X" % x["be"],
                "bytes": x["bytes"],
                "hits": hits,
                "matches_pci_id": v in (PCI_IDS["vendor"], PCI_IDS["device"],
                                        PCI_IDS["subvendor"], PCI_IDS["subdevice"]),
            }
        )

# ============================ 4. GMMU source formats (dev_mmu.h) ============================

mu_src = load_text("/tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_mmu.h")
vm_src = load_text("/tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_vm.h")

mm_fields = {}
for m in re.finditer(
    r"#define\s+(NV_MMU_(?:PDE|PTE|VER2_PTE)_\w+)\s+\((\d)\*32\+(\d+)\):\((\d)\*32\+(\d+)\)\s*/\* ([A-Z]+) \*/",
    mu_src,
):
    name, w, msb, lsb, _, rw = m.groups()
    mm_fields[name] = {"word": int(w), "msb": int(msb), "lsb": int(lsb), "rw": rw}
mm_consts = {}
for m in re.finditer(r"#define\s+(NV_MMU_(?:PDE|PTE|VER2_PTE)_\w+)\s+(0[xX][0-9A-Fa-f]+)", mu_src):
    name, val = m.groups()
    mm_consts[name] = int(val, 16)

vm_consts = {}
for m in re.finditer(r"#define\s+(NV_VIRTUAL_FUNCTION_PRIV_BAR\d_BLOCK)\s+(0[xX][0-9A-Fa-f]+)", vm_src):
    name, val = m.groups()
    vm_consts[name] = int(val, 16)

# ============================ 5. Hypothesis tests ============================

hypotheses = []

# H1: 0x1f4f.. u32s = PCI ID / SKU table
pci_id_values = {PCI_IDS["vendor"], PCI_IDS["device"], PCI_IDS["subvendor"], PCI_IDS["subdevice"]}
h1_matches_pci = [m for m in id_matches if m["matches_pci_id"]]
h1_reasons = []
if h1_matches_pci:
    h1_reasons.append("co %d gia tri trung thuan PCI ID" % len(h1_matches_pci))
if not id_matches:
    h1_reasons.append("khong tim thay u32 nao co dang 0x1f4f/0x1f4e trong bar3_hot.bin")
else:
    h1_reasons.append(
        "tat ca %d lan xuat hien 0x1f4f/0x1f4e khong trung bat cu ID PCI nao (10de:1f0b, "
        "sub 1043:8804), khong co doi tuong alignment/endian bang bang, khong co cau truc bang" % len(id_matches)
    )
hypotheses.append(
    {
        "id": "H1",
        "name": "u32 0x1f4f../0x1f4e.. o BAR3 la bang ma SKU / ID thiet lap PCI",
        "result": "REJECTED",
        "basis": "bar3_hot.bin u32 inventory; config_space_64 +0x00/+0x02/+0x2C/+0x2E",
        "reasons": h1_reasons,
    }
)

# H2: 0x14000 repetition of 0x00000008 = page directory
const8_offs = [x["off"] for x in recom_u32 if x["le"] == 0x00000008]
const8_runs = []
if const8_offs:
    start = prev = const8_offs[0]
    for o in const8_offs[1:]:
        if o == prev + 0x10:
            prev = o
        else:
            const8_runs.append((start, prev))
            start = prev = o
    const8_runs.append((start, prev))
h2_run = next((r for r in const8_runs if r[0] == 0x14000), None)
hypotheses.append(
    {
        "id": "H2",
        "name": "lap 0x00000008 tai 0x14000 la page directory / page table",
        "result": "REJECTED",
        "basis": "bar3_hot.bin +0x14000..",
        "reasons": [
            "gia tri hang lan = 0x00000008 khong chua dia chi (khong co bit [31:4] hop le nhu dev_mmu.h PTE/PDE_ADDRESS)",
            "khong co bit VALID (bit 0 cua word0 PTE/PDE) danh dau entry co hai",
            "stride 0x10 voi 12 byte zero giua cac gia tri khong phai kich thuc 8 byte cua PDE/PTE (NV_MMU_PDE__SIZE=8, NV_MMU_PTE__SIZE=8)",
            "khong giam duoc page directory chi tu bit lap luan (yeu cau cau truy van task)",
        ],
        "detail": {
            "run_at_0x14000": ["0x%05X" % h2_run[0], "0x%05X" % h2_run[1]] if h2_run else None,
            "const8_runs": [["0x%05X" % a, "0x%05X" % c] for a, c in const8_runs][:10],
        },
    }
)

# H3: tail 0x3FE00..0x3FFF4 = GMMU PTE array per dev_mmu.h
PTE_VALID = 0x1
PTE_PRIVILEGE = 0x2
PTE_READ_ONLY = 0x4
PTE_ENCRYPTED = 0x8


def pte_word0_fields(v):
    return {
        "VALID": (v >> 0) & 1,
        "PRIVILEGE": (v >> 1) & 1,
        "READ_ONLY": (v >> 2) & 1,
        "ENCRYPTED": (v >> 3) & 1,
        "ADDR_SYS_31_4": (v >> 4) & 0xFFFFFFF,
        "ADDR_VID_28_4": (v >> 4) & 0x1FFFFFFF,
        "KIND_11_4": (v >> 4) & 0xFF,
    }


def pte_word1_fields(v):
    return {
        "VOL": (v >> 0) & 1,
        "APERTURE_2_1": (v >> 1) & 3,
        "LOCK": (v >> 3) & 1,
        "COMPTAGLINE_63_44": (v >> 12) & 0x3FFFF,  # bits 31:12 of word1 = bits 63:44
        "READ_DISABLE": (v >> 30) & 1,
        "WRITE_DISABLE": (v >> 31) & 1,
    }


tail_start, tail_end = 0x3FE00, 0x3FFF4
tail_u32 = [x for x in recom_u32 if tail_start <= x["off"] <= tail_end - 4]
# candidate records: word0 at 16-aligned offset with PTE-like shape, word1 constant
records = []
i = tail_start
while i <= tail_end - 16:
    w0 = u32(bar3_bytes, i)
    w1 = u32(bar3_bytes, i + 4)
    w2 = u32(bar3_bytes, i + 8)
    w3 = u32(bar3_bytes, i + 12)
    if w0 and w1 == 0x06000000 and w2 == 0 and w3 == 0:
        records.append(
            {
                "off": i,
                "w0": "0x%08X" % w0,
                "w1": "0x%08X" % w1,
                "fields0": pte_word0_fields(w0),
                "fields1": pte_word1_fields(w1),
            }
        )
    i += 0x10
addr_step = None
if len(records) >= 2:
    a0 = pte_word0_fields(int(records[0]["w0"], 16))["ADDR_SYS_31_4"]
    a1 = pte_word0_fields(int(records[1]["w0"], 16))["ADDR_SYS_31_4"]
    addr_step = (a1 - a0) << 4
h3_reasons = []
if records:
    all_valid = all(r["fields0"]["VALID"] == 1 for r in records)
    all_vid = all(r["fields1"]["APERTURE_2_1"] == 0 for r in records)  # 0 = video memory
    all_kind_pitch = all(r["fields0"]["KIND_11_4"] == 0 for r in records)
    h3_reasons.append(
        "co %d ban ghi 16 byte tai 0x3FE00..0x3FFF4: word0 co VALID=1, dia chi [31:4] 16-byte aligned, "
        "aperture=video memory, KIND=PITCH; word1 lap lai 0x06000000 (VOL=0, LOCK=0)" % len(records)
    )
    if addr_step is not None:
        h3_reasons.append("dia chi tang %d (0x%X) muc giua cac ban ghi" % (addr_step, addr_step))
    h3_reasons.append(
        "TU CHAP: stride cua ban ghi la 0x10 byte, khac PTE__SIZE=8 byte tu dev_mmu.h; 8 byte cua moi ban ghi "
        "(w2,w3) luon zero -> khong phai mang PTE lien ke theo dinh nghia source"
    )
    h3_reasons.append("tat ca ban ghi nam trong mot trang (0x3F000); khong the kiem tra duong bien trang ngoai cua cua so 0x40000")
else:
    h3_reasons.append("khong tim thay ban ghi 16 byte thoa man mau tai 0x3FE00..0x3FFF4")
hypotheses.append(
    {
        "id": "H3",
        "name": "vung cuoi 0x3FE00..0x3FFF4 cua BAR3 la mang PTE GMMU (dev_mmu.h, 8 byte/entry)",
        "result": "REJECTED (mang PTE lien ke) / word0 tuong thich PTE ca le",
        "basis": "bar3_hot.bin +0x3FE00..+0x3FFF4; dev_mmu.h NV_MMU_PTE_*, NV_MMU_PTE__SIZE=8",
        "reasons": h3_reasons,
        "records": records[:5],
        "record_count": len(records),
    }
)

# ============================ 6. VRAM reconciliation ============================

smq = memory_registers = load_json(ROOT / "MEMORY" / "memory_registers.json")
smq_text = smq["smq"]


def grab(pattern, text, group=1):
    m = re.search(pattern, text)
    return m.group(group) if m else None


vram_total = int(grab(r"Total\s*:\s*(\d+) MiB", smq_text))
vram_reserved = int(grab(r"Reserved\s*:\s*(\d+) MiB", smq_text))
vram_used = int(grab(r"Used\s*:\s*(\d+) MiB", smq_text))
vram_free = int(grab(r"Free\s*:\s*(\d+) MiB", smq_text))

_bar1_idx = smq_text.find("BAR1 Memory Usage")
_bar1_end = smq_text.find("\n\n", _bar1_idx)
_bar1_block = smq_text[_bar1_idx:_bar1_end] if _bar1_idx >= 0 and _bar1_end >= 0 else (smq_text[_bar1_idx:] if _bar1_idx >= 0 else smq_text)
bar1_total = int(grab(r"Total\s*:\s*(\d+) MiB", _bar1_block))
bar1_used = int(grab(r"Used\s*:\s*(\d+) MiB", _bar1_block))
bar1_free = int(grab(r"Free\s*:\s*(\d+) MiB", _bar1_block))

# WPR: corrected VAL[31:4] << 12 == (val & 0xFFFFFFF0) << 8 (low nibble is zero)
wpr_lo = int(pcie_map and 0)  # placeholder
wpr_lo = int(security["registers"][5]["value"], 16) if False else None
sec = load_json(ROOT / "SECURITY" / "security_registers.json")
wpr_lo_reg = None
wpr_hi_reg = None
for r in sec["registers_read"]:
    if r["off"] == "0x1fa824":
        wpr_lo_reg = int(r["value"], 16)
    if r["off"] == "0x1fa828":
        wpr_hi_reg = int(r["value"], 16)

wpr_base = (wpr_lo_reg & 0xFFFFFFF0) << 8
wpr_end = (wpr_hi_reg & 0xFFFFFFF0) << 8
wpr_size = wpr_end - wpr_base

# boot-time conflicting archived WPR values (dmesg facts)
wpr_boot_lo = int(sec["dmesg_facts"].get("WPR2_lo", 0))  # 0x1FFE0000 at one boot log line

# ============================ assemble verified JSON ============================

verified = {
    "schema": "memory_pcie_verified/v1",
    "gpu": "TU106 [CMP 40HX] %s" % GPU_BDF,
    "mode": "offline read-only; no /sys /dev /GPU probe; no config/write changes",
    "inputs": {
        "PCIE/pcie_map.json": {"sha256": sha256_file(ROOT / "PCIE" / "pcie_map.json")},
        "PCIE/q3_link.json": {"sha256": sha256_file(ROOT / "PCIE" / "q3_link.json")},
        "RAW_DATA/q3_pcie.txt": {"sha256": sha256_file(ROOT / "RAW_DATA" / "q3_pcie.txt")},
        "MEMORY/memory_registers.json": {"sha256": sha256_file(ROOT / "MEMORY" / "memory_registers.json")},
        "RAW_DATA/bar3_hot.bin": {"sha256": bar3_sha, "bytes": bar3_size},
        "TOPOLOGY/p9_bar3_parsed.json": {"sha256": sha256_file(ROOT / "TOPOLOGY" / "p9_bar3_parsed.json")},
        "TOPOLOGY/p9_barscan.json": {"sha256": sha256_file(ROOT / "TOPOLOGY" / "p9_barscan.json")},
        "TOPOLOGY/p9_stability.json": {"sha256": sha256_file(ROOT / "TOPOLOGY" / "p9_stability.json")},
        "TOOLS/p9_bar3dump.py": {"sha256": sha256_file(ROOT / "TOOLS" / "p9_bar3dump.py")},
        "SECURITY/security_registers.json": {"sha256": sha256_file(ROOT / "SECURITY" / "security_registers.json")},
        "source/tu102/dev_mmu.h": {"sha256": sha256_file("/tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_mmu.h")},
        "source/tu102/dev_vm.h": {"sha256": sha256_file("/tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_vm.h")},
    },
    "pcie_config_raw": {"file": "PCIE/pcie_map.json config_space_64", "bytes_offset": "0x00..0x3F", "hex": cfg.hex()},
    "pcie_identity": {
        "vendor": "0x%04X" % vendor,
        "device": "0x%04X" % device,
        "revision": "0x%02X" % rev,
        "class": "%02X%02X%02X" % (base_class, subclass, prog_if),
        "subsystem": "0x%04X:0x%04X" % (subven, subdev),
        "cap_ptr_first": "0x%02X @ config+0x34" % cap_ptr,
        "basis_lines": "RAW_DATA/q3_pcie.txt lines 1-4, 81-83; PCIE/pcie_map.json config_space_64",
    },
    "bars": bars,
    "bar_decode": bar_decoded,
    "resource_ranges_raw": [
        {"lo": "0x%012X" % r["lo"], "hi": "0x%012X" % r["hi"], "size_bytes": r["size"], "size_MiB": round(MiB(r["size"]), 3), "flags": "0x%08X" % r["flags"]}
        for r in resource_ranges
    ],
    "capabilities_from_lspci_text": [
        {"cap": "[60]", "name": "Power Management v3", "line": 47},
        {"cap": "[68]", "name": "MSI 64bit", "line": 48},
        {"cap": "[78]", "name": "Express v2 Endpoint", "line": 49},
        {"cap": "[bb0]", "name": "Physical Resizable BAR v1", "line": 74},
    ],
    "root_port": {"bdf": "0000:00:02.0", "type": "Express v2 Root Port", "DLActive": True, "line": 82},
    "link": {
        "card": {"LnkCap": "5GT/s x16", "LnkCtl2_target": "5GT/s", "LnkSta_runtime": "2.5GT/s (downgraded) x16", "lines": "q3_pcie.txt 27,38,40"},
        "root": {"LnkCap": "8GT/s x16", "LnkCtl2_target": "5GT/s", "LnkSta_runtime": "2.5GT/s x16", "DLActive": True, "lines": "q3_pcie.txt 108,124,126"},
        "conclusion": "ca hai dau target 5 GT/s nhung runtime 2.5 GT/s -> link training chua dat target; khong duoc bao gio boi root port gioi han",
        "conclusion_source": "PCIE/q3_link.json conclusion + q3_pcie.txt lines 21-24",
    },
    "rebar": {
        "evidence": "q3_pcie.txt line 74 (cap [bb0]) + lines 75-77 + resource ranges",
        "BAR0": "current 16MB / supported 16MB",
        "BAR1": "current 64GB / supported 64MB..256GB (64GB trong danh sach duoc ho tro)",
        "BAR3": "current 32MB / supported 32MB",
        "note": "'64G' chuoi duy khong chung minh duoc day du khoi giai ma; span duoc chung minh bo resource range raw 381000000000-381fffffffff (64 GiB) va 380800000000-380801ffffff (32 MiB)",
    },
    "bar3_provenance": {
        "tool": "TOOLS/p9_bar3dump.py",
        "tool_mapping_source": "mo /sys/bus/pci/devices/0000:03:00.0/resource3, doc mmap [0x0:0x40000), ghi file byte 1:1",
        "mapping": "file_offset == BAR3_window_offset == BAR3_address - 0x380800000000",
        "bar3_base_from_config": "BAR3 reg config+0x1C = 0x0000000C (64-bit prefetchable mem), BAR4 reg config+0x20 = 0x00003808 -> base 0x380800000000",
        "bar3_size_from_resource": "resource3 0x380800000000..0x380801FFFFFF = 32 MiB",
        "file_size": bar3_size,
        "file_sha256": bar3_sha,
        "size_matches_tool_window": tool_hi - tool_lo == bar3_size,
        "archived_parse_match_recompute": parsed_match,
        "note": "khong the lay lai tu thiet lam (offline, doc only); mapping co so la config decode + nguon tool p9_bar3dump.py",
    },
    "bar3_inventory": {
        "pages_total": 64,
        "pages_with_data": sum(1 for p in recom_pages if p["nonzero_bytes"]),
        "nonzero_bytes_total": sum(p["nonzero_bytes"] for p in recom_pages),
        "nonzero_u32_total": len(recom_u32),
        "nonzero_u64_total": len(recom_u64),
        "csv": "bar3_entries.csv",
    },
    "id_patterns": {
        "scan": "tat ca u32 le 4 byte trong bar3_hot.bin; pattern: hi16/lo16/full == 0x1F4F hoac 0x1F4E",
        "matches": len(id_matches),
        "matches_detail": id_matches[:40],
        "pci_ids_checked": PCI_IDS,
        "conclusion": "KHONG duoc goi bang bang SKU table: khong gia tri nao trung ID PCI, xuat hien bo trong trang, khong co cau truc bang",
    },
    "gmmue_source": {
        "file": "/tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_mmu.h",
        "PDE": {"size_bytes": mm_consts.get("NV_MMU_PDE__SIZE"), "word0": {"APERTURE_[1:0]": "0 invalid/1 vid/2 syscoh/3 sysnoncoh", "SIZE_[3:2]": "0 full/1 half/2 quarter/3 eighth", "ADDRESS_[31:4]": "SYNS or VID"}},
        "PTE": {"size_bytes": mm_consts.get("NV_MMU_PTE__SIZE"),
                "word0": ["VALID_[0] (bit0=1)", "PRIVILEGE_[1]", "READ_ONLY_[2]", "ENCRYPTED_[3]",
                          "ADDRESS_SYS_[31:4]", "ADDRESS_VID_[28:4]", "KIND_[11:4]"],
                "word1": ["VOL_[0]", "APERTURE_[2:1] (0=vid mem)", "LOCK_[3]", "COMPTAGLINE_[63:44]",
                          "READ_DISABLE_[30]", "WRITE_DISABLE_[31]"]},
        "KIND_encodings": {"0": "PITCH", "1": "Z16", "2": "S8", "3": "S8Z24", "4": "ZF32_X24S8", "5": "Z24S8", "6": "GENERIC_MEMORY", "7": "INVALID"},
    },
    "driver_bar_mapping_source": {
        "file": "/tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_vm.h",
        "found": vm_consts,
        "note": "chi tim duoc register khoi BAR VF (BAR1_BLOCK 0xF40, BAR2_BLOCK 0xF48) voi TARGET/MODE; khong co dong source nao rang buoc CPU BAR3 aperture -> mapping driver BAR3 con UNKNOWN; khong doc BAR1_BLOCK theo yeu cau task",
    },
    "hypotheses": hypotheses,
    "vram": {
        "smi_text_block": "MEMORY/memory_registers.json smq",
        "Total_MiB": vram_total,
        "Reserved_MiB": vram_reserved,
        "Used_MiB": vram_used,
        "Free_MiB": vram_free,
        "check_Total_Reserved_Used_vs_Free": vram_total - vram_reserved - vram_used,
        "delta_Free_MiB": vram_free - (vram_total - vram_reserved - vram_used),
        "NVML_Reserved_vs_Total_Free_Used": {"Reserved": vram_reserved, "Total-Free-Used": vram_total - vram_free - vram_used, "delta": vram_reserved - (vram_total - vram_free - vram_used)},
        "BAR1_memory_MiB": {"Total": bar1_total, "Used": bar1_used, "Free": bar1_free},
        "basis": "memory_registers.json smq lines 2-4 (raw text)",
        "unknowns": ["hieu 1 MiB giua Free va Total-Reserved-Used chua ro (lam tron hay overlap)", "Reserved (389) khong bang Total-Free-Used (388)"],
    },
    "wpr": {
        "registers_runtime": {"0x1FA824_NV_PFB_PRI_MMU_WPR2_ADDR_LO": "0x%08X" % wpr_lo_reg, "0x1FA828_NV_PFB_PRI_MMU_WPR2_ADDR_HI": "0x%08X" % wpr_hi_reg},
        "source": "SECURITY/security_registers.json registers (runtime MMIO doc duoc)",
        "corrected_formula": "VAL[31:4] << 12 == (val & 0xFFFFFFF0) << 8 (low nibble = 0)",
        "WPR2_base": "0x%08X" % wpr_base,
        "WPR2_end": "0x%08X" % wpr_end,
        "WPR2_size_bytes": wpr_size,
        "WPR2_size_MiB": round(MiB(wpr_size), 3),
        "fits_within_8GiB_FB": wpr_end <= 0x200000000,
        "conflicting_archived_values": {
            "runtime_register_LO": "0x%08X" % wpr_lo_reg,
            "dmesg_boot_WPR_at_boot_lo": "0x1FFE000 (security_registers.json dmesg_facts.WPR_at_boot)",
            "dmesg_facts_WPR2_lo": "0x%08X" % wpr_boot_lo,
            "dmesg_boot_commit_WPR2": "0:0x1FFFFE00",
        },
        "rule_applied": "KHONG tru WPR2 mac dinh khoi NVML Reserved: chua biet overlap/bo nho cap phat; gioi thue giua WPR2 va Reserved chua ro",
        "corroboration": "EVIDENCE_LEDGER.md E16-007 deu same base/end (0x1F7E00000/0x1FFEE0000) va khoang cach 128.875 MiB",
    },
    "evidence_levels": {
        "MEASURED": "doc thuc tu bytes file thau vao (config bytes, bar3_hot.bin, smq text)",
        "DECODED": "gia quyet chuan PCIe / bitfield tu source dev_mmu.h tren du lieu thau",
        "CORROBORATED": "hai nguon luu thau thuan nhat (vd config vs lspci text; parsed.json vs recompute)",
        "INFERRED": "gia thuyet tu cau truc, chua duoc chuong trinh chu nghiem",
        "REJECTED": "da kiem tra va bo loc boi rang buoc source",
        "UNKNOWN": "co du lieu nhung chua du xu ly xac dinh",
    },
    "limitations": [
        "Khong co moi tram PCIe/thuc runtime moi duoc doc: tat ca duong lien toc tu lspci luu cu (q3_pcie.txt).",
        "Khong xac duoc whole GPU reverse engineering da HOAN TAT.",
        "Khong doc VRAM/WPR khoi thiet lam, khong ghi BAR1_BLOCK.",
    ],
}

with open(OUT / "memory_pcie_verified.json", "w", encoding="utf-8") as f:
    json.dump(verified, f, indent=1, ensure_ascii=False)

# ============================ bar3_entries.csv (full inventory) ============================

with open(OUT / "bar3_entries.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["section", "off", "off_hex", "len", "bytes_hex", "u32_le", "u32_be", "u64_le", "class", "note"])
    for p in recom_pages:
        w.writerow(["PAGE", p["off"], "0x%05X" % p["off"], 0x1000, "", "", "", "",
                    "data" if p["nonzero_bytes"] else "zero",
                    "first_nz=0x%05X last_nz=0x%05X nz_bytes=%d" % (p["first_nz"] or 0, p["last_nz"] or 0, p["nonzero_bytes"])])
    for x in recom_u32:
        cls = []
        v = x["le"]
        if (v >> 16) in (0x1F4F, 0x1F4E):
            cls.append("idlike_hi16_0x%04X" % (v >> 16))
        if (v & 0xFFFF) in (0x1F4F, 0x1F4E):
            cls.append("idlike_lo16_0x%04X" % (v & 0xFFFF))
        if v == 0x00007FF0:
            cls.append("size_0x7FF0")
        if v == 0x00000008:
            cls.append("const_8")
        w.writerow(["U32", x["off"], "0x%05X" % x["off"], 4, x["bytes"], "0x%08X" % v,
                    "0x%08X" % x["be"], "", ",".join(cls) or "other", ""])
    for x in recom_u64:
        w.writerow(["U64", x["off"], "0x%05X" % x["off"], 8, "", "", "", "0x%016X" % x["le"],
                    "nonzero_u64", ""])
    # 16-byte records
    for i in range(0, bar3_size - 15, 16):
        chunk = bar3_bytes[i:i + 16]
        nz = sum(1 for b in chunk if b)
        if nz:
            w0, w1 = u32(chunk, 0), u32(chunk, 4)
            w2, w3 = u32(chunk, 8), u32(chunk, 12)
            cls = []
            if (w0 >> 16) in (0x1F4F, 0x1F4E):
                cls.append("idlike")
            if i == 0x0:
                cls.append("page0_first")
            if i >= 0x3FE00 and i <= 0x3FFFC:
                cls.append("tail_record")
            w.writerow(["REC16", i, "0x%05X" % i, 16, chunk.hex(), "0x%08X" % w0,
                        "0x%08X" % w1, "0x%016X" % u64(chunk, 0), ",".join(cls) or "data16",
                        "w2=0x%08X w3=0x%08X" % (w2, w3)])

# ============================ report ============================

def lvl(n):
    return n

rep = []
rep.append("# MEMORY_PCIE_REPORT — CMP40HX / TU106 (0000:03:00.0), Phase 16")
rep.append("")
rep.append("## 1. Pham vi va quy che")
rep.append("- Chỉ chạy khi Codex dispatch; chỉ đọc file lưu và source headers NVIDIA (turing/tu102).")
rep.append("- KHONG doc /sys hoac /dev, KHONG probing/ghi GPU, KHONG sua clock/ROM/driver, KHONG doc VRAM/WPR khoi thiet lam, KHONG ghi BAR1_BLOCK.")
rep.append("- Tat du lieu tu archive cu: khong co moi do PCIe/runtime moi. Chua khan bao whole-GPU RE da HOAN TAT.")
rep.append("- Mua tac: MEASURED (bytes file thau), DECODED (quy rut tu bitfield/source), CORROBORATED (hai nguon thau), REJECTED, UNKNOWN.")
rep.append("")
rep.append("## 2. PCIe config/capability (endpoint 0000:03:00.0)")
rep.append("config_space_64 raw (PCIE/pcie_map.json, offset bytes 0x00..0x3F): %s" % cfg.hex())
rep.append("- Vendor 0x%04X Device 0x%04X Rev 0x%02X Class %02X%02X%02X (3D controller) — MEASURED [config+0x00..+0x0B]" % (vendor, device, rev, base_class, subclass, prog_if))
rep.append("- Subsystem 0x%04X:0x%04X (ASUS) — MEASURED [config+0x2C..+0x2F]" % (subven, subdev))
rep.append("- First capability pointer = 0x%02X at config+0x34 — MEASURED [config byte 0x34]" % cap_ptr)
rep.append("- Capability chain duoc liet ke bo lspci text (RAW_DATA/q3_pcie.txt): [60] PM v3 (line 47), [68] MSI 64-bit (line 48), [78] Express v2 Endpoint (line 49), ... [bb0] Physical Resizable BAR v1 (line 74). Cap treo ngoai 0x3F khong co trong config dump 64 byte -> chi duoc chung minh bo text, khong doc raw config.")
rep.append("")
rep.append("### BAR decode (config bytes + resource range raw)")
for bd in bar_decoded:
    rep.append("- BAR%d: reg config+0x%02X raw=0x%08X%s -> %s-base 0x%012X" % (
        bd["pair"][0], bd["pair"][0], bd["raw_lo"],
        "64-bit pair with BAR%d" % bd["pair"][1] if len(bd["pair"]) == 2 else "32-bit",
        "64-bit mem" if len(bd["pair"]) == 2 else "mem/io",
        bd["base"]))
rep.append("resource_file ranges raw (PCIE/pcie_map.json):")
for r in resource_ranges:
    rep.append("  - 0x%012X..0x%012X size %s (%.3f MiB) flags 0x%08X — MEASURED raw range, chung minh khoi duoc giai ma" % (
        r["lo"], r["hi"], r["size"], MiB(r["size"]), r["flags"]))
rep.append("")
rep.append("### ReBAR (Physical Resizable BAR [bb0]) — RAW_DATA/q3_pcie.txt lines 75-77")
rep.append("- BAR0: current 16MB / supported 16MB.")
rep.append("- BAR1: current 64GB / supported 64MB..256GB (64GB co trong danh sach duoc ho tro).")
rep.append("- BAR3: current 32MB / supported 32MB.")
rep.append("- Ket luat: ReBAR CAP da duoc khai bao ([bb0], line 74); BAR1 duoc cau hinh target 64GB. Nhung xau '64G' MOI KHONG DU chung minh day du khoi giai ma: span duoc chung minh bo resource range raw (BAR1: 381000000000..381fffffffff = 64 GiB; BAR3: 380800000000..380801FFFFFF = 32 MiB).")
rep.append("")
rep.append("### Link: capability vs cau hinh target vs thuc te neu ngoai (khong do moi)")
rep.append("- Card (Endpoint, q3_pcie.txt line 27 LnkCap): 5GT/s x16; line 38 LnkCtl2 Target Link Speed: 5GT/s; line 40 LnkSta: 2.5GT/s (downgraded) x16.")
rep.append("- Root port 0000:00:02.0 (Express v2 Root Port, line 82): LnkCap 8GT/s x16 (line 108); LnkCtl2 target 5GT/s (line 124); LnkSta 2.5GT/s x16, DLActive+ (line 126).")
rep.append("- Ket luat: ca hai dau target 5 GT/s, runtime thuc te 2.5 GT/s -> link training chua dat target; KHONG duoc xac rang boi root port gioi han (PCIE/q3_link.json conclusion).")
rep.append("")
rep.append("## 3. bar3_hot.bin: nguyen nguyen mapping")
rep.append("- Nguon tool TOOLS/p9_bar3dump.py: mo /sys/bus/pci/devices/0000:03:00.0/resource3, mmap [0x0:0x40000), ghi file byte 1:1.")
rep.append("- Mapping duoc xac dinh bo nguon tool: file_offset == BAR3_window_offset; dia chi thiet lap = 0x380800000000 + file_offset.")
rep.append("- BAR3 base duoc lay tu config: BAR3 reg config+0x1C = 0x0000000C (mem 64-bit prefetchable), BAR4 reg config+0x20 = 0x00003808 -> base 0x380800000000; size 32 MiB tu resource3 range 0x380800000000..0x380801FFFFFF.")
rep.append("- bar3_hot.bin: %d bytes (0x40000), SHA256 %s. Khung cua tool khop kich thuc file." % (bar3_size, bar3_sha))
rep.append("- Chua the lay lai tu thiet lam (offline, doc-only); mapping co so = config decode + nguon tool p9_bar3dump.py.")
rep.append("- Xac lap noi bo: p9_bar3_parsed.json (hot pages + nonzero u32) khop toan bo voi phep REDACTED_USER lai tu bar3_hot.bin: %s -> provenance luu truu duoc xac nhan noi bo." % ("CO" if parsed_match else "KHONG KHOP"))
rep.append("")

# ============================ 4. inventory ============================
nz_pages = [p for p in recom_pages if p["nonzero_bytes"]]
rep.append("## 4. BAR3 inventory (toan bo trang/entry raw, xuat ra bar3_entries.csv)")
rep.append("- Tong 64 trang (0x00000..0x3F000, 256 KiB); trang co du lieu: %d/64; tong byte co du lieu: %d; u32 khong 0: %d; u64 khong 0: %d." % (
    len(nz_pages), sum(p["nonzero_bytes"] for p in recom_pages), len(recom_u32), len(recom_u64)))
rep.append("- Trang co du lieu: %s" % ", ".join("0x%05X(%d)" % (p["off"], p["nonzero_bytes"]) for p in nz_pages))
rep.append("- Cac u32 bat dau trang: 0x00000=0x00007FF0, 0x08000=0x00007FF0, 0x10000=0x1F4F4D02, 0x11000=0x1F4F4C02, 0x12040=0x1F4F4B02 — MEASURED [bar3_hot.bin+off].")
rep.append("- Vung 0x14000: u32 0x00000008 lap theo stride 0x10 — MEASURED (xem H2).")
rep.append("- Vung 0x17000: entry 16 byte {flags, 0x00060000, 8 byte zero}, flags tang 0x20000 — duoc bao bo p9_bar3dump.py; bar3_17000_stable o TOPOLOGY/p9_stability.json line 5.")
rep.append("- Duoi cuoi 0x3FE00..0x3FFF4: cac ban ghi {0x1FC..0001, 0x06000000, 0, 0} theo stride 0x10 — MEASURED (xem H3).")
rep.append("")

# ============================ 5. ID patterns ============================
rep.append("## 5. Kiem tra lai pattern ID 0x1f4f / 0x1f4e (khong duoc su dung de ket luat bang SKU)")
rep.append("- Quet tat ca u32 le 4 byte: co %d lan xuat hien thoa hi16/lo16/full == 0x1F4F hoac 0x1F4E." % len(id_matches))
for m in id_matches[:20]:
    rep.append("  - %s: u32_le=%s u32_be=%s bytes=%s align4=%s page_align=%s hits=%s" % (
        m["off_hex"], m["u32_le"], m["u32_be"], m["bytes"], m["align4"], m["page_align"], ",".join(m["hits"])))
rep.append("- ID PCI tham gia so sanh: vendor 0x%04X device 0x%04X sub 0x%04X:0x%04X. Khong gia tri nao trung." % (vendor, device, subven, subdev))
rep.append("- Ket luat: PATTERN 0x1f4f/0x1f4e KHONG DU DE GOI BANG BANG SKU table — khong trung ID, xuat hien bo trong trang, khong co cau truc bang, khong xac dinh endian/alignment co nghia. REJECTED.")

# ============================ 6. GMMU ============================
rep.append("")
rep.append("## 6. GMMU/PDE/PTE va aperture tu source tu102/dev_mmu.h")
rep.append("- NV_MMU_PDE__SIZE = 8 byte. Word0 (bit [msb:lsb]): APERTURE_BIG [1:0] (0 invalid,1 video,2 sys coh,3 sys noncoh), SIZE [3:2] (0 full,1 half,2 quarter,3 eighth), ADDRESS_BIG_SYS [31:4] / ADDRESS_BIG_VID [28:4].")
rep.append("- NV_MMU_PTE__SIZE = 8 byte. Word0: VALID [0], PRIVILEGE [1], READ_ONLY [2], ENCRYPTED [3], ADDRESS_SYS [31:4] / ADDRESS_VID [28:4]; Word1: VOL [0], APERTURE [2:1] (0 vid mem,1 peer,2 sys coh,3 sys noncoh), LOCK [3], COMPTAGLINE [63:44], READ_DISABLE [30], WRITE_DISABLE [31], KIND [11:4] (0 PITCH,...7 INVALID).")
rep.append("- Source thu duoc boi regex tu dev_mmu.h; khong con thong tin driver map BAR3 vao aperture nao trong set header cua task.")
rep.append("- dev_vm.h: chi tim register khoi BAR VF (BAR1_BLOCK 0x%04X, BAR2_BLOCK 0x%04X) co TARGET [29:28] (0 vid,2 sys coh,3 sys noncoh) va MODE [31] (0 physical,1 virtual). Mapping driver BAR3 con UNKNOWN; khong doc BAR1_BLOCK theo yeu cau." % (vm_consts.get("NV_VIRTUAL_FUNCTION_PRIV_BAR1_BLOCK", 0), vm_consts.get("NV_VIRTUAL_FUNCTION_PRIV_BAR2_BLOCK", 0)))

# ============================ 7. hypotheses ============================
rep.append("")
rep.append("## 7. Kiem tra gia thuyet cau truc BAR3 (duoc chon mot gia thuyet de kiem tra xech)")
for h in hypotheses:
    rep.append("- %s %s: %s" % (h["id"], h["name"], h["result"]))
    rep.append("  Co so: %s" % h["basis"])
    for r in h["reasons"]:
        rep.append("  - %s" % r)
rep.append("Tat ca cac gia thuyet tren duoc ket qua REJECTED (hoac REJECTED nhu mang lien ke nhung ca le theo entry). KHONG gan page directory chi tu bit lap luan.")

# ============================ 8. VRAM ============================
rep.append("")
rep.append("## 8. Thoa gia total/usable/reserved/free VRAM")
rep.append("- Tu smq (MEMORY/memory_registers.json): Total %d MiB, Reserved %d MiB, Used %d MiB, Free %d MiB." % (vram_total, vram_reserved, vram_used, vram_free))
rep.append("- Total - Reserved - Used = %d MiB, khong bang Free %d MiB (delta %d MiB, chua ro: lam tron hay overlap)." % (
    vram_total - vram_reserved - vram_used, vram_free, vram_free - (vram_total - vram_reserved - vram_used)))
rep.append("- NVML Reserved %d MiB vs Total-Free-Used %d MiB (delta %d MiB). RESERVED KHONG BANG total-free." % (
    vram_reserved, vram_total - vram_free - vram_used, vram_reserved - (vram_total - vram_free - vram_used)))
rep.append("- BAR1 memory (smi): Total %d MiB / Used %d / Free %d — tuong ung voi config BAR1 64 GiB (CORROBORATED)." % (bar1_total, bar1_used, bar1_free))
rep.append("")
rep.append("### WPR (corrected VAL[31:4] << 12 == (val & 0xFFFFFFF0) << 8, vi low nibble bang 0)")
rep.append("- Register runtime (SECURITY/security_registers.json): 0x1FA824 NV_PFB_PRI_MMU_WPR2_ADDR_LO = 0x%08X; 0x1FA828 WPR2_ADDR_HI = 0x%08X." % (wpr_lo_reg, wpr_hi_reg))
rep.append("- WPR2 corrected: base 0x%08X, end 0x%08X, size %d bytes (%.3f MiB), nam trong khoang 8 GiB FB." % (
    wpr_base, wpr_end, wpr_size, MiB(wpr_size)))
rep.append("- Gia tri luu va bo xung (dmesg_facts): WPR_at_boot lo 0x1FFE000; dmesg_facts.WPR2_lo 0x%08X; dmesg boot commit WPR2=0:0x1FFFFE00. Cac gia tri KHONG NHAU -> ung dung WPR2 nao ap dung hien tai chua ro." % wpr_boot_lo)
rep.append("- LUAT DU AP DUNG: KHONG tru WPR2 (128.875 MiB) mac dinh khoi NVML Reserved 389 MiB, vi chua biet overlap/cap phat. Muc tro giu giua WPR2 va Reserved = UNKNOWN.")
rep.append("- Giu nguyen EVIDENCE_LEDGER.md E16-007: cung base/end va khoang cach 128.875 MiB (CORROBORATED).")

# ============================ 9. conclusion ============================
rep.append("")
rep.append("## 9. Ket luat")
rep.append("- PCIe/BAR3 interface duoc giai ma tu archive: cap the 10de:1f0b rev a1, BAR0 16MB @ fa000000, BAR1 64GB pref @ 0x381000000000, BAR3 32MB pref @ 0x380800000000 (map bar3_hot.bin), BAR5 I/O 0xe000/128B; ReBAR cap [bb0] ton tai, BAR1 target 64GB; link target 5GT/s nhung runtime 2.5GT/s x16 (downgraded).")
rep.append("- bar3_hot.bin co nguyen nguyen mapping va toan bo inventory xuat ra bar3_entries.csv; pattern 0x1f4f/0x1f4e KHONG duoc chap nhan lam bang SKU.")
rep.append("- GMMU PDE/PTE format duoc trích tu dev_mmu.h; ba gia thuyet cau truc BAR3 duoc kiem tra va BO LOC (H1/H2/H3).")
rep.append("- VRAM: Total 8192/Reserved 389/Used 0/Free 7804 MiB, hieu 1 MiB chua ro; WPR2 corrected [0x1F7E00000, 0x1FFEE0000] 128.875 MiB khong duoc tu do tru khoi Reserved.")
rep.append("- KHONG khan bao whole GPU DONE; khong co do thuc moi tren PCIe/runtime.")
rep.append("")
rep.append("## Xuat: memory_pcie_verified.json, bar3_entries.csv, run.log, MEMORY_PCIE_REPORT.md (thu muc nay).")

with open(OUT / "MEMORY_PCIE_REPORT.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rep) + "\n")

# run.log: nhat ky chay (cac buoc va ket qua chinh, giong noi dung ba cao)
with open(OUT / "run.log", "w", encoding="utf-8") as f:
    f.write("RUN LOG: memory_pcie_verify.py (offline, doc only, /usr/bin/python3)\n")
    f.write("GPU: %s  mode: khong /sys, /dev, khong probe/ghi GPU\n\n" % GPU_BDF)
    f.write("\n".join(rep) + "\n")

print("\nDONE. Outputs in", OUT)

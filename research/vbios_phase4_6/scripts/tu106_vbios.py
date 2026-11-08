#!/usr/bin/env python3
"""TU106 (CMP 40HX / RTX 2060S / RTX 2070) VBIOS read-only parser.

Field layout is backed by a published definition for every table this parses:
  PERFORMANCE v0x60  NVIDIA nvgpu include/nvgpu/bios.h
                     (vbios_pstate_header_6x, vbios_pstate_entry_6x,
                      vbios_pstate_entry_clock_6x, PERF_CLK_DOMAINS_IDX_MAX)
  CLOCKS v0x35       NVIDIA nvgpu vbios_clocks_table_35_* (10 clock domains)
  MEM TIMINGS MAPPING  NVIDIA MemoryClockTable spec v0x11
  MEM TIMINGS        NVIDIA MemoryTweakTable spec v0x20
  POWER BASE CLOCK   envytools nvbios/power.c case 0x20
  DCB                NVIDIA DCB 4.x spec
Everything else is reported as raw bytes and named from envytools P2_tbls[].

Read-only: never writes to a ROM file.

Pointer rule (NVIDIA BIT spec; image lengths parsed from PCIR, not hardcoded):
    file = image0_base + raw                    raw <  image0_len
    file = image0_base + raw + image1_len       raw >= image0_len
"""
from __future__ import annotations
import struct, sys, json, os

BIT_SIG = b"\xff\xb8BIT"

P2_NAMES = {
    0: "PERFORMANCE", 1: "MEMORY TIMINGS MAPPING", 2: "MEMORY TIMINGS",
    3: "VOLTAGE", 4: "THERMAL", 5: "THERMAL DEVICES", 6: "THERMAL COOLERS",
    7: "PERF SETTINGS SCRIPT", 8: "VOLT MAPPING", 9: "VENTURA",
    10: "POWER SENSE", 11: "POWER BUDGET", 12: "BOOST", 13: "CSTEP",
    14: "POWER BASE CLOCK", 15: "POWER TOPOLOGY", 16: "POWER LEAKAGE",
    17: "PERF TEST SPEC", 18: "THERMAL CHANNEL", 19: "THERMAL ADJUSTMENT",
    20: "THERMAL POLICY", 21: "PSTATE MEMORY CLK FREQ", 22: "FAN COOLERS",
    23: "POWER FAN_MGMT", 24: "DI/DT", 25: "FAN TEST", 26: "VOLTAGE RAIL",
    27: "VOLTAGE DEVICE", 28: "VOLTAGE POLICY", 29: "LOW POWER",
    30: "LOW POWER PCIe", 31: "LOW POWER PCIe-PLATFORM", 32: "LOW POWER GR",
    33: "LOW POWER MS", 34: "LOW POWER DI", 35: "LOW POWER GC6",
    36: "LOW POWER PSI", 37: "THERM MONITOR", 38: "OVERCLOCKING",
}

# pstate clock_entry index -> clock domain. NVIDIA nvgpu bios.h sizes the array
# as PERF_CLK_DOMAINS_IDX_MAX but does not name the indices; the order below is
# the GV HAL clock-domain order that the v0x35 clocks table lists its rows in,
# and it is confirmed by this ROM set: all 10 v0x35 row gates match, and index 2
# is independently DRAM (7001 MT/s at 1750 MHz native, x4).
CLK_DOMAINS = ("GPC", "XBAR", "DRAM", "SYS", "HUB", "VID", "PWR", "DISP",
               "PCIEGEN", "HOST")

# v0x35 row gates: (name, flags0 usage, param2 low nibble)
CLOCKS_35_ROWS = (("GPC", 1, 0x13), ("XBAR", 2, 0x24), ("DRAM", 1, 0x62),
                  ("SYS", 2, 0x35), ("HUB", 2, 0x71), ("VID", 2, 0x46),
                  ("PWR", 0, 0xFF), ("DISP", 1, 0x80), ("PCIEGEN", 2, 0x08),
                  ("HOST", 2, 0x57))

DCB_TYPES = {0: "CRT", 1: "TV", 2: "TMDS", 3: "LVDS", 5: "SDI",
             6: "DisplayPort", 0xE: "EOL", 0xF: "Skip"}

# Memory Tweak Table v0x20 timing bitfields: (name, CONFIG word index, shift,
# mask). NVIDIA MemoryTweakTable spec puts CONFIG0..CONFIG5 at entry + 0,4,8,
# 12,16,20. Single source of truth for parser, exporter and test: a wrong shift
# here must fail a test, not silently emit a plausible-looking timing.
# Devinit opcode mnemonics for the few that end a script section we do not
# interpret (NVIDIA open-gpu-doc Devinit spec). Only used to label the stop.
DEVINIT_OPNAMES = {0x5B: "INIT_SUB_DIRECT", 0x5C: "INIT_JUMP_DIRECT",
                   0x6A: "INIT_JUMP", 0x35: "INIT_FUNCTION", 0x71: "INIT_DONE",
                   0x5D: "INIT_DONE_CONDITION", 0x89: "INIT_JUMP_REL"}

MEM_TWEAK_FIELDS = (
    ("RC",      0,  0, 0xFF),  ("RFC",     0,  8, 0x1FF), ("RAS",  0, 17, 0x7F),
    ("RP",      0, 24, 0x7F),
    ("CL",      1,  0, 0x7F),  ("WL",      1,  7, 0x7F),  ("RD_RCD", 1, 14, 0x3F),
    ("WR_RCD",  1, 20, 0x3F),
    ("RPRE",    2,  0, 0x0F),  ("WPRE",    2,  4, 0x0F),  ("CDLR",   2,  8, 0x7F),
    ("WR",      2, 16, 0x7F),  ("W2R",     2, 24, 0x0F),  ("R2W",    2, 28, 0x0F),
    ("FAW",     3,  9, 0xFF),  ("CCDL",    3, 24, 0x0F),  ("CCDS",   3, 28, 0x0F),
    ("REFRESH", 4,  3, 0xFFF), ("RRD",     4, 15, 0x3F),
)


class Rom:
    """Bounds-checked, read-only view of one VBIOS image."""

    def __init__(self, data: bytes, name: str = "?"):
        self.d = data
        self.name = name
        self._images = None
        self._img0 = None

    # ---- primitives (bounds checked: raise instead of reading garbage) ------
    def _chk(self, off, n):
        if off < 0 or off + n > len(self.d):
            raise IndexError(f"{self.name}: read {n}B at {off:#x} outside ROM")
        return off

    def u8(self, off):  return self.d[self._chk(off, 1)]
    def u16(self, off): return struct.unpack_from("<H", self.d, self._chk(off, 2))[0]
    def u32(self, off): return struct.unpack_from("<I", self.d, self._chk(off, 4))[0]
    def bytes(self, off, n): return self.d[self._chk(off, n):off + n]
    def hex(self, off, n): return self.bytes(off, n).hex(" ")

    # ---- PCI image chain ---------------------------------------------------
    def images(self):
        """Every PCIR structure with vendor 0x10DE, ascending by offset.

        image_len is PCIR+0x10 in 512-byte blocks (PCI spec / DCB 4.x spec).
        Image 0 is the legacy x86 image, image 1 the EFI image.
        """
        if self._images is not None:
            return self._images
        out, i = [], 0
        while True:
            i = self.d.find(b"PCIR", i)
            if i < 0:
                break
            if self.u16(i + 4) == 0x10DE:
                out.append(dict(pcir=i, vendor=0x10DE, device=self.u16(i + 6),
                                image_len=self.u16(i + 0x10) * 512,
                                revision=self.u8(i + 12),
                                class_code=(self.u8(i + 13) | self.u8(i + 14) << 8
                                            | self.u8(i + 15) << 16)))
            i += 4
        out.sort(key=lambda e: e["pcir"])
        self._images = out
        return out

    def image0_base(self):
        """512-byte-aligned base of the legacy image (BIT lives inside it)."""
        if self._img0 is None:
            b = self.d.find(BIT_SIG)
            if b < 0:
                raise ValueError("no BIT table")
            self._img0 = b & ~0x1FF
        return self._img0

    def ptr(self, raw):
        imgs = self.images()
        base = self.image0_base()
        legacy_len = imgs[0]["image_len"] if imgs else 0
        efi_len = imgs[1]["image_len"] if len(imgs) > 1 else 0
        return base + raw + (efi_len if raw >= legacy_len else 0)

    def ptr_maps(self):
        imgs = self.images()
        return dict(image0_base=self.image0_base(),
                    legacy_len=imgs[0]["image_len"] if imgs else 0,
                    efi_len=imgs[1]["image_len"] if len(imgs) > 1 else 0,
                    image_count=len(imgs))

    def pci(self):
        im = self.images()[0]
        cls = im["class_code"]
        return dict(pcir=im["pcir"], signature="PCIR", vendor=im["vendor"],
                    device=im["device"], image_len=im["image_len"],
                    revision=im["revision"], class_code=cls,
                    class_name={0x030000: "VGA display controller",
                                0x030200: "3D controller (no display engine)"}.get(cls, "?"),
                    images=[dict(i=n, pcir=e["pcir"], image_len=e["image_len"],
                                 class_code=e["class_code"])
                            for n, e in enumerate(self.images())])

    # ---- BIT ---------------------------------------------------------------
    def bit(self):
        base = self.d.find(BIT_SIG)
        if base < 0:
            raise ValueError("no BIT table (0xffb8BIT)")
        if sum(self.d[base:base + self.u8(base + 8)]) & 0xFF:
            raise ValueError("BIT header checksum != 0")
        hlen, rlen, cnt = self.u8(base + 8), self.u8(base + 9), self.u8(base + 10)
        tokens = {}
        for k in range(cnt):
            o = base + hlen + k * rlen
            t, v = chr(self.u8(o)), self.u8(o + 1)
            ln, raw = self.u16(o + 2), self.u16(o + 4)
            tokens[t] = dict(ver=v, t_len=ln, raw=raw, file=self.ptr(raw), ent=o)
        return dict(base=base, ver=self.u16(base + 6), hlen=hlen, rlen=rlen,
                    count=cnt, tokens=tokens)

    # ---- Performance P2 directory ------------------------------------------
    def p2(self):
        tok = self.bit()["tokens"]["P"]
        if tok["ver"] != 2:
            raise ValueError(f"BIT 'P' version {tok['ver']} (expected 2)")
        out = {}
        for i in range(tok["t_len"] // 4):
            # nvgpu nvgpu_bios_get_perf_table_ptrs(): the pointer lives at
            # data_ptr + table_id * PERF_PTRS_WIDTH(4); `raw` is the value there,
            # `file` is where that value resolves to. Keep both apart: exporting
            # the resolved address as the pointer's own offset hides off-by-one
            # slot bugs.
            ptr_off = tok["file"] + i * 4
            raw = self.u32(ptr_off)
            if raw:
                out[i] = dict(name=P2_NAMES.get(i, f"slot{i}"),
                              ptr_off=ptr_off, raw=raw, file=self.ptr(raw))
        return out

    # ---- LOW POWER PCIe (slot 30) ------------------------------------------
    def lpwr_pcie(self, off=None):
        """Slot 30, structurally a {ver, hlen, entry_size, entry_count} table
        with 12-byte entries whose extent closes exactly on slot 31 in all
        three ROMs. Field semantics are NOT published: every entry is reported
        as raw bytes and the decode stops there.
        """
        if off is None:
            p = self.p2().get(30)
            if not p:
                return None
            off = p["file"]
        g = dict(hdr=off, ver=self.u8(off), hlen=self.u8(off + 1),
                 entry_len=self.u8(off + 2), count=self.u8(off + 3))
        g["size"] = g["hlen"] + g["count"] * g["entry_len"]
        g["end"] = off + g["size"]
        g["entries"] = [dict(idx=i, off=off + g["hlen"] + i * g["entry_len"],
                             raw=self.bytes(off + g["hlen"] + i * g["entry_len"],
                                            g["entry_len"]))
                        for i in range(g["count"])]
        return g

    # ---- PCIe settings script (NVINIT opcode 0x7A / 0x6E / 0x75 / 0xFF) ----
    def pcie_settings_script(self):
        """`nvinit_ptrs.pcie_settings_script_ptr` decoded per NVIDIA
        open-gpu-doc Devinit spec:

            INIT_ZM_REG     0x7A : addr(u32) data(u32)            -> reg = data
            INIT_NV_REG     0x6E : addr(u32) mask(u32) data(u32)  -> reg = (reg & mask) | data
            INIT_CONDITION  0x75 : condition(u8)                  -> rest is conditional
            EOL             0xFF : end

        Anything else stops the decode: re-syncing past an unknown operand size
        would invent writes. Ops after a 0x75 carry `cond` = the condition id
        and must not be read as an unconditional init path.
        """
        t = self.bit()["tokens"].get("I")
        if not t:
            return None
        ptr = self.u16(t["file"] + 0x12)     # nvinit_ptrs.pcie_settings_script_ptr
        if not ptr:
            return None
        off, out, cond = self.ptr(ptr), [], None
        for _ in range(0x400):
            op = self.u8(off)
            if op == 0xFF:
                out.append(dict(off=off, op="EOL"))
                break
            if op == 0x7A:
                out.append(dict(off=off, op="ZM_REG", addr=self.u32(off + 1),
                                data=self.u32(off + 5), len=9, cond=cond))
                off += 9
            elif op == 0x6E:
                out.append(dict(off=off, op="NV_REG", addr=self.u32(off + 1),
                                mask=self.u32(off + 5), data=self.u32(off + 9),
                                len=13, cond=cond))
                off += 13
            elif op == 0x75:
                cond = self.u8(off + 1)
                out.append(dict(off=off, op="CONDITION", cond=cond, len=2))
                off += 2
            else:
                name = DEVINIT_OPNAMES.get(op, "unhandled")
                out.append(dict(off=off, op=f"STOP {name} ({op:#04x})", len=0,
                                cond=cond))
                break
        return dict(ptr=ptr, off=self.ptr(ptr), ops=out)

    def hdr6(self, off):
        return dict(ver=self.u8(off), hlen=self.u8(off + 1),
                    b0=self.u8(off + 2), b1=self.u8(off + 3),
                    b2=self.u8(off + 4), b3=self.u8(off + 5))

    # ---- PERFORMANCE v0x60 (nvgpu vbios_pstate_*) --------------------------
    def perf_v60(self, off=None):
        """P-STATE table v0x60.

        Header 10 B (`vbios_pstate_header_6x`):
          +0 version 0x60, +1 header_size 10, +2 base_entry_size 5,
          +3 base_entry_count, +4 clock_entry_size 6, +5 clock_entry_count 10,
          +6 flags0 (bit0 PSTATES_REQUIRED, bit1 ARBITER_LOCK),
          +7 initial_pstate, +8 cpi_support_level, +9 cpi_features.

        Base entry 5 B (`vbios_pstate_entry_6x`):
          +0 pstate_level (0xFF = VBIOS_PERFLEVEL_SKIP_ENTRY),
          +1 flags0 (PSTATE_CAP 1:0, CUDA_NOT_SAFE 2, OVOC 3, DECREASE_THRESHOLD 4),
          +2 lpwr_entry_idx, +3 pcie_idx, +4 nvlink_idx.

        Clock entry 6 B (`vbios_pstate_entry_clock_6x` = {u16 param0, u32 param1}):
          param0[13:0] = nominal MHz;
          param1[13:0] = minimum MHz, param1[27:14] = maximum MHz.
        """
        if off is None:
            off = self.p2()[0]["file"]
        h = self.hdr6(off)
        if h["ver"] != 0x60:
            raise ValueError(f"perf version {h['ver']:#x} != 0x60")
        g = dict(hdr=off, ver=h["ver"], hdr_len=h["hlen"],
                 base_len=h["b0"], entry_cnt=h["b1"],
                 sup_len=h["b2"], sup_cnt=h["b3"],
                 flags0=self.u8(off + 6), initial_pstate=self.u8(off + 7),
                 cpi_support_level=self.u8(off + 8), cpi_features=self.u8(off + 9))
        g["pstates_required"] = g["flags0"] & 1
        g["arbiter_lock"] = (g["flags0"] >> 1) & 1
        g["entry_len"] = g["base_len"] + g["sup_len"] * g["sup_cnt"]
        g["size"] = g["hdr_len"] + g["entry_cnt"] * g["entry_len"]
        g["end"] = off + g["size"]
        g["entries"] = []
        e = off + g["hdr_len"]
        for i in range(g["entry_cnt"]):
            base = self.bytes(e, g["base_len"])
            subs = []
            s = e + g["base_len"]
            for j in range(g["sup_cnt"]):
                p0, p1 = struct.unpack("<HI", self.bytes(s, 6))
                subs.append(dict(off=s, idx=j,
                                 domain=CLK_DOMAINS[j] if j < len(CLK_DOMAINS) else f"dom{j}",
                                 nom=p0 & 0x3FFF, nom_raw=p0,
                                 mn=p1 & 0x3FFF, mx=(p1 >> 14) & 0x3FFF, p1_raw=p1))
                s += g["sup_len"]
            g["entries"].append(dict(idx=i, off=e, base=base.hex(" "),
                                     pstate=base[0], flags0=base[1],
                                     lpwr_idx=base[2], pcie_idx=base[3],
                                     nvlink_idx=base[4], pstate_cap=base[1] & 3,
                                     cuda_not_safe=(base[1] >> 2) & 1,
                                     ovoc=(base[1] >> 3) & 1,
                                     skip=(base[0] == 0xFF), subs=subs))
            e += g["entry_len"]
        return g

    # ---- CLOCKS v0x35 (nvgpu vbios_clocks_table_35_*) ---------------------
    def clocks_v35(self, off=None):
        """Clocks table v0x35: ten 11-byte rows in the GV HAL domain order.

        Header 9 B: version 0x35, header_size, entry_size 11, entry_count,
        clocks_hal, cntr_sampling_period_ms(u16), reference_window(u16).
        Row 11 B: flags0(usage 1:0), param0(u16 prog idx first/last),
        param1(u32), param2(u16: low nibble PRE_VOLT ordering idx,
        high nibble POST_VOLT), param3(u16 thresholds).
        """
        sig = bytes.fromhex("35 09 0b 0a")
        if off is None:
            off = self.d.find(sig)
            if off < 0:
                return None
        if self.d[off:off + 4] != sig:
            return None
        g = dict(hdr=off, ver=self.u8(off), hlen=self.u8(off + 1),
                 row_len=self.u8(off + 2), count=self.u8(off + 3),
                 clocks_hal=self.u8(off + 4),
                 sampling_ms=self.u16(off + 5), ref_window=self.u16(off + 7))
        g["rows"] = []
        r = off + g["hlen"]
        for i in range(g["count"]):
            b = self.bytes(r, g["row_len"])
            p2v = struct.unpack_from("<H", b, 7)[0]   # param2 follows flags0+param0+param1
            # param2 byte 0 = PRE_VOLT ordering idx (low nibble) / POST_VOLT (high nibble);
            # the row gates are on the whole byte, which equals the GV HAL ordering id.
            g["rows"].append(dict(idx=i, off=r, usage=b[0] & 0x1F,
                                  prog_first=b[1], prog_last=b[2], p2=p2v,
                                  pre_volt_idx=p2v & 0xF,
                                  post_volt_idx=(p2v >> 4) & 0xF,
                                  domain=CLOCKS_35_ROWS[i][0] if i < len(CLOCKS_35_ROWS)
                                  else f"row{i}",
                                  ordering=b[7],
                                  identity_ok=(i < len(CLOCKS_35_ROWS)
                                               and b[7] == CLOCKS_35_ROWS[i][2])))

            r += g["row_len"]
        return g

    # ---- MEMORY TIMINGS MAPPING = Memory Clock Table v0x11 -----------------
    def mem_clock_table(self, off=None):
        """NVIDIA MemoryClockTable v0x11. Header 26 B; TU106 uses base entry 60
        and strap entry 33 (spec's 20/26 are the original Fermi/Maxwell sizes),
        which the exact extent arithmetic confirms on all three ROMs."""
        if off is None:
            off = self.p2()[1]["file"]
        h = self.hdr6(off)
        g = dict(hdr=off, ver=h["ver"], hdr_len=h["hlen"],
                 base_len=h["b0"], strap_len=h["b1"],
                 strap_cnt=h["b2"], entry_cnt=h["b3"])
        g["entry_len"] = g["base_len"] + g["strap_len"] * g["strap_cnt"]
        g["size"] = g["hdr_len"] + g["entry_cnt"] * g["entry_len"]
        g["end"] = off + g["size"]
        g["entries"] = []
        e = off + g["hdr_len"]
        for i in range(g["entry_cnt"]):
            mn, mx = self.u16(e), self.u16(e + 2)
            g["entries"].append(dict(idx=i, off=e,
                                     min_mhz=mn & 0x3FFF, max_mhz=mx & 0x3FFF,
                                     min_raw=mn, max_raw=mx,
                                     rw0=self.u32(e + 8), rw1=self.u32(e + 12)))
            e += g["entry_len"]
        return g

    # ---- MEMORY TIMINGS = Memory Tweak Table v0x20 -------------------------
    def mem_tweak_table(self, off=None):
        if off is None:
            off = self.p2()[2]["file"]
        h = self.hdr6(off)
        g = dict(hdr=off, ver=h["ver"], hdr_len=h["hlen"],
                 base_len=h["b0"], ext_len=h["b1"],
                 ext_cnt=h["b2"], entry_cnt=h["b3"])
        g["entry_len"] = g["base_len"] + g["ext_len"] * g["ext_cnt"]
        g["size"] = g["hdr_len"] + g["entry_cnt"] * g["entry_len"]
        g["end"] = off + g["size"]
        g["entries"] = []
        e = off + g["hdr_len"]
        for i in range(g["entry_cnt"]):
            c = [self.u32(e + 4 * k) for k in range(6)]
            fields = {}
            for (name, w, sh, mask) in MEM_TWEAK_FIELDS:
                fields[name] = dict(cfg=w, word_off=e + 4 * w, shift=sh,
                                    mask=mask, raw=c[w],
                                    value=(c[w] >> sh) & mask)
            g["entries"].append(dict(
                idx=i, off=e, cfg=c, fields=fields,
                **{k: v["value"] for k, v in fields.items()}))
            e += g["entry_len"]
        return g

    # ---- POWER BASE CLOCK (slot 14) ---------------------------------------
    def power_base_clock(self, off=None):
        """POWER BASE CLOCK v0x20 (envytools nvbios/power.c case 0x20):
        +0 ver, +1 hlen, +2 rlen, +3 entriesnum, +4 secount, +5 selen;
        clock[j] = u16(entry + rlen + j*selen + 2) * 4.

        Only entries 0..2 decode to plausible clocks on TU106 — the remaining
        entries do not follow envytools' sub-record assumption, so their clock
        slots are flagged clocks_valid=False and must not be read as MHz.
        """
        if off is None:
            off = self.p2()[14]["file"]
        g = dict(hdr=off, ver=self.u8(off), hlen=self.u8(off + 1),
                 rlen=self.u8(off + 2), entry_cnt=self.u8(off + 3),
                 secount=self.u8(off + 4), selen=self.u8(off + 5))
        g["entry_len"] = g["rlen"] + g["selen"] * g["secount"]
        g["size"] = g["hlen"] + g["entry_cnt"] * g["entry_len"]
        g["end"] = off + g["size"]
        g["entries"] = []
        for i in range(g["entry_cnt"]):
            e = off + g["hlen"] + i * g["entry_len"]
            clocks = [self.u16(e + g["rlen"] + j * g["selen"] + 2) * 4
                      for j in range(g["secount"])]
            g["entries"].append(dict(idx=i, off=e, pstate=self.u8(e),
                                     clocks=clocks, clocks_valid=(i <= 2)))
        return g

    # ---- POWER BUDGET (slot 11) = nvgpu pwr_policy_3x ----------------------
    def power_budget(self, off=None):
        """POWER BUDGET / power policy v0x30.

        nvgpu `pwr_policy_3x_header_struct` (37 B) + `pwr_policy_3x_entry_struct`
        (46 B) describe the base layout. TU106 extends both: header 44 B (+7),
        entry 66 B (+20). The header still carries the extra table sizes, and
        with them the extent closes exactly on slot 15:

            44 + 20*66 + 15*14 + 13*13 = 1743   (CMP/2060S/2070: exact)

        Entry fields limit_min / limit_rated / limit_max are nvgpu names; on the
        class-1 entry they read 110/184/220 W (CMP) and 125/184/220 W (GeForce),
        which is why they are treated as milliwatts.
        """
        if off is None:
            off = self.p2()[11]["file"]
        g = dict(hdr=off, ver=self.u8(off), hlen=self.u8(off + 1),
                 entry_len=self.u8(off + 2), count=self.u8(off + 3),
                 base_sample_ms=self.u16(off + 4),
                 min_client_sample_ms=self.u16(off + 6),
                 rel_len=self.u8(off + 8), rel_cnt=self.u8(off + 9),
                 tgp_idx=self.u8(off + 10), rtp_idx=self.u8(off + 11),
                 mxm_idx=self.u8(off + 12), dnotifier_idx=self.u8(off + 13),
                 viol_len=self.u8(off + 34), viol_cnt=self.u8(off + 35))
        g["size"] = (g["hlen"] + g["count"] * g["entry_len"]
                     + g["rel_cnt"] * g["rel_len"] + g["viol_cnt"] * g["viol_len"])
        g["end"] = off + g["size"]
        g["entries"] = []
        e = off + g["hlen"]
        for i in range(g["count"]):
            f0 = self.u8(e)
            g["entries"].append(dict(
                idx=i, off=e, flags0=f0, class_id=f0 & 0xF, unit_bit=(f0 >> 4) & 1,
                limit_min=self.u32(e + 2), limit_rated=self.u32(e + 6),
                limit_max=self.u32(e + 10), flags1=self.u8(e + 38),
                raw=self.bytes(e, g["entry_len"])))
            e += g["entry_len"]
        g["rel"] = self.bytes(off + g["hlen"] + g["count"] * g["entry_len"],
                              g["rel_cnt"] * g["rel_len"])
        g["viol"] = self.bytes(g["end"] - g["viol_cnt"] * g["viol_len"],
                               g["viol_cnt"] * g["viol_len"])
        return g

    # ---- POWER TOPOLOGY (slot 15) = nvgpu pwr_topology_2x ------------------
    def power_topology(self, off=None):
        """POWER TOPOLOGY v0x20. Header and entry match nvgpu
        `pwr_topology_2x_header` (6 B) / `pwr_topology_2x_entry` (22 B) exactly,
        plus the relative block the header declares:

            6 + 20*22 + 15*27 = 851   (exact on all three ROMs)
        """
        if off is None:
            off = self.p2()[15]["file"]
        g = dict(hdr=off, ver=self.u8(off), hlen=self.u8(off + 1),
                 entry_len=self.u8(off + 2), count=self.u8(off + 3),
                 rel_len=self.u8(off + 4), rel_cnt=self.u8(off + 5))
        g["size"] = g["hlen"] + g["count"] * g["entry_len"] + g["rel_cnt"] * g["rel_len"]
        g["end"] = off + g["size"]
        g["entries"] = []
        e = off + g["hlen"]
        for i in range(g["count"]):
            f0 = self.u8(e)
            g["entries"].append(dict(
                idx=i, off=e, flags0=f0, class_id=f0 & 0xF,
                pwr_rail=self.u8(e + 1), param0=self.u32(e + 2),
                curr_corr_slope=self.u32(e + 6), curr_corr_offset=self.u32(e + 10),
                param1=self.u32(e + 14), param2=self.u32(e + 18)))
            e += g["entry_len"]
        return g

    # ---- THERMAL POLICY (slot 20) ------------------------------------------
    def thermal_policy(self, off=None):
        """Slot 20: {ver=0x10, hlen=10, entry 40, count 4} closes exactly on
        slot 21. No published field schema, so entries stay raw; only the header
        bytes are named positionally because they differ between cards.
        """
        if off is None:
            off = self.p2()[20]["file"]
        g = dict(hdr=off, ver=self.u8(off), hlen=self.u8(off + 1),
                 entry_len=self.u8(off + 2), count=self.u8(off + 3),
                 hdr_tail=self.bytes(off + 4, self.u8(off + 1) - 4))
        g["size"] = g["hlen"] + g["count"] * g["entry_len"]
        g["end"] = off + g["size"]
        g["entries"] = [dict(idx=i, off=off + g["hlen"] + i * g["entry_len"],
                             raw=self.bytes(off + g["hlen"] + i * g["entry_len"],
                                            g["entry_len"]))
                        for i in range(g["count"])]
        return g

    # ---- LOW POWER GR (slot 32) --------------------------------------------
    def lpwr_gr(self, off=None):
        """Slot 32: {ver=0x10, hlen=10, entry 5, count 5} closes exactly on
        slot 33. nvgpu's `nvgpu_bios_lpwr_gr_table_1x_header` is 7 B with 4-byte
        entries, so TU106 is 3 B wider per header and 1 B wider per entry:
        structure only, masks reported raw.
        """
        if off is None:
            off = self.p2()[32]["file"]
        g = dict(hdr=off, ver=self.u8(off), hlen=self.u8(off + 1),
                 entry_len=self.u8(off + 2), count=self.u8(off + 3),
                 hdr_tail=self.bytes(off + 4, self.u8(off + 1) - 4))
        g["size"] = g["hlen"] + g["count"] * g["entry_len"]
        g["end"] = off + g["size"]
        g["entries"] = []
        for i in range(g["count"]):
            o = off + g["hlen"] + i * g["entry_len"]
            raw = self.bytes(o, g["entry_len"])
            mask = struct.unpack_from("<I", raw, 0)[0]
            g["entries"].append(dict(
                idx=i, off=o, raw=raw, feature_mask=mask,
                bit0_gr=bool(mask & 0x1), bit4_rppg=bool(mask & 0x10),
                tail=raw[4:]))
        return g

    # ---- VFE 3x (slot 8) — voltage/frequency equation table ----------------
    def vfe_3x(self, off=None):
        """VFE (Variable/Equation) table v0x30 per nvgpu `vbios_vfe_3x_*`.

        Header 9 B: ver, hlen, var_esz, var_cnt, equ_esz, equ_cnt, polling_ms,
        var_rppm_cnt, equ_rppm_cnt.
        var entry 25 B (`vbios_vfe_3x_var_entry_struct`), equ entry 24 B
        (`vbios_vfe_3x_equ_entry_struct`).

        TU106 closes the extent only with the rppm blocks included:

            9 + 20*25 + 150*24 + 1335 = 5444

        where 1335 = 55*24 + 15 (var_rppm_cnt + equ_rppm_cnt = 55). The rppm
        region is 24-byte-periodic for ~95% of its bytes, so it is reported as
        55 raw 24-byte records plus a 15-byte tail, all UNKNOWN.

        Structure is PROVEN: every var `type` byte is in 0..7 and every equ
        `type` byte in 0..6 on all three ROMs, which a wrong stride would break.
        """
        if off is None:
            off = self.p2()[8]["file"]
        g = dict(hdr=off, ver=self.u8(off), hlen=self.u8(off + 1),
                 var_len=self.u8(off + 2), var_cnt=self.u8(off + 3),
                 equ_len=self.u8(off + 4), equ_cnt=self.u8(off + 5),
                 polling_ms=self.u8(off + 6),
                 var_rppm_cnt=self.u8(off + 7), equ_rppm_cnt=self.u8(off + 8))
        p2 = self.p2()
        nxt = [v["file"] for v in p2.values() if v["file"] > off]
        g["span"] = (min(nxt) - off) if nxt else 0

        g["vars"] = []
        o = off + g["hlen"]
        for i in range(g["var_cnt"]):
            g["vars"].append(dict(
                idx=i, off=o, type=self.u8(o),
                out_min=self.u32(o + 1), out_max=self.u32(o + 5),
                param0=self.u32(o + 9), param1=self.u32(o + 13),
                param2=self.u32(o + 17), param3=self.u32(o + 21)))
            o += g["var_len"]

        g["equs"] = []
        for i in range(g["equ_cnt"]):
            g["equs"].append(dict(
                idx=i, off=o, type=self.u8(o), var_idx=self.u8(o + 1),
                equ_next=self.u8(o + 2), out_min=self.u32(o + 3),
                out_max=self.u32(o + 7), param0=self.u32(o + 11),
                param1=self.u32(o + 15), param2=self.u32(o + 19),
                param3=self.u8(o + 23)))
            o += g["equ_len"]

        g["rppm_off"] = o
        n_rppm = g["var_rppm_cnt"] + g["equ_rppm_cnt"]
        avail = off + g["span"] - o
        g["rppm"] = []
        r = o
        for i in range(n_rppm):
            if r + 24 > off + g["span"]:
                break
            g["rppm"].append(dict(idx=i, off=r, raw=self.bytes(r, 24)))
            r += 24
        g["rppm_tail"] = self.bytes(r, max(0, off + g["span"] - r))
        g["extent_ok"] = (g["span"] == g["hlen"] + g["var_cnt"] * g["var_len"]
                          + g["equ_cnt"] * g["equ_len"] + n_rppm * 24
                          + len(g["rppm_tail"]))
        g["end"] = off + g["span"]
        return g

    # ---- LOW POWER index table (slot 29) -----------------------------------
    def lpwr_idx_table(self, off=None):
        """Slot 29: {ver=0x10, hlen=6, entry 7, count 5} closes exactly on slot 30.

        nvgpu `nvgpu_bios_lpwr_idx_table_1x_entry` is
        { pcie_idx, gr_idx, ms_idx, di_idx, gc6_idx } (5 B). TU106 adds 2 bytes.
        Verified: byte 0 equals the P-state `pcie_idx` for every live P-state on
        all three ROMs, and bytes 1..4 equal that entry's own low-power index.
        Byte 5 = 0xFF on all entries, byte 6 = entry index.
        """
        if off is None:
            off = self.p2()[29]["file"]
        g = dict(hdr=off, ver=self.u8(off), hlen=self.u8(off + 1),
                 entry_len=self.u8(off + 2), count=self.u8(off + 3),
                 sampling_period=self.u16(off + 4))
        g["size"] = g["hlen"] + g["count"] * g["entry_len"]
        g["end"] = off + g["size"]
        g["entries"] = []
        for i in range(g["count"]):
            o = off + g["hlen"] + i * g["entry_len"]
            b = self.bytes(o, g["entry_len"])
            g["entries"].append(dict(
                idx=i, off=o, raw=b, pcie_idx=b[0],
                gr_idx=b[1] if len(b) > 1 else None,
                ms_idx=b[2] if len(b) > 2 else None,
                di_idx=b[3] if len(b) > 3 else None,
                gc6_idx=b[4] if len(b) > 4 else None,
                b5=b[5] if len(b) > 5 else None,
                self_idx=b[6] if len(b) > 6 else None))
        return g

    def pstate_pcie_target(self, rom_pstate=None):
        """Resolve the chain the P-state table leaves dangling:

            P-state entry.lpwr_entry_idx -> slot 29 entry -> .pcie_idx
                                         -> slot 30 (LOW POWER PCIe) entry

        Returns one row per live P-state. `pcie_target` is the slot-30 entry it
        lands on; that entry's payload meaning is still UNKNOWN.
        """
        idx = self.lpwr_idx_table()
        live = self.lpwr_pcie()
        pf = rom_pstate or self.perf_v60()
        out = []
        for e in pf["entries"]:
            if e["skip"]:
                continue
            li = e["lpwr_idx"]
            tbl = idx["entries"][li] if li < len(idx["entries"]) else None
            tgt = live["entries"][tbl["pcie_idx"]] if (
                tbl is not None and tbl["pcie_idx"] < len(live["entries"])) else None
            out.append(dict(pstate=e["pstate"], lpwr_idx=li,
                            pcie_idx=e["pcie_idx"],
                            table_pcie_idx=None if tbl is None else tbl["pcie_idx"],
                            consistent=(tbl is not None
                                        and tbl["pcie_idx"] == e["pcie_idx"]),
                            pcie_target=None if tgt is None else tgt["idx"],
                            pcie_target_raw=None if tgt is None else tgt["raw"].hex()))
        return out

    # ---- DCB (NVIDIA DCB 4.x spec) ----------------------------------------
    def dcb(self, image=0):
        """Device Control Block. Entry byte 0 (little-endian Display Path word)
        bits 3:0 = Type: 0 CRT, 1 TV, 2 TMDS, 3 LVDS, 5 SDI, 6 DP,
        0xE = EOL, 0xF = Skip Entry. Anything else is an active path."""
        base = self.image0_base() + image
        p = self.u16(base + 0x36)
        if not p:
            return dict(ptr=0, entries=[], active=0, note="DCB pointer is 0")
        off = self.ptr(p)
        if self.u32(off + 6) != 0x4EDCBDCB:
            return dict(ptr=p, off=off, entries=[], active=0, note="bad DCB signature")
        g = dict(ptr=p, off=off, ver=self.u8(off), hdr=self.u8(off + 1),
                 cnt=self.u8(off + 2), len=self.u8(off + 3))
        g["entries"] = []
        for i in range(g["cnt"]):
            word = self.u32(off + g["hdr"] + i * g["len"])
            t = word & 0xF
            g["entries"].append(dict(idx=i, off=off + g["hdr"] + i * g["len"],
                                     raw=word, type=t,
                                     type_name=DCB_TYPES.get(t, f"rsvd{t:#x}"),
                                     edid_port=(word >> 4) & 0xF,
                                     head=(word >> 8) & 0xF,
                                     connector=(word >> 12) & 0xF,
                                     skip=(t == 0xF), eol=(t == 0xE)))
        g["active"] = sum(1 for e in g["entries"] if not e["skip"] and not e["eol"])
        return g

    # ---- table extent validation ------------------------------------------
    def extents(self):
        p2 = self.p2()
        starts = {v["file"] for v in p2.values()}
        out = []
        for slot, info in sorted(p2.items()):
            off = info["file"]
            h = self.hdr6(off)
            cands = {
                "base=b2 ext=b3 ec=b4 cnt=b5":
                    h["hlen"] + h["b3"] * (h["b0"] + h["b1"] * h["b2"]),
                "base=b2 ext=b4 ec=b5 cnt=b3":
                    h["hlen"] + h["b1"] * (h["b0"] + h["b2"] * h["b3"]),
                "base=b2 ext=b4 ec=b3 cnt=b5":
                    h["hlen"] + h["b3"] * (h["b0"] + h["b2"] * h["b1"]),
            }
            hit = [k for k, v in cands.items() if v and off + v in starts]
            out.append(dict(slot=slot, name=info["name"], off=off,
                            head=self.hex(off, 6), size=cands, match=hit))
        return out


def load(path, name=None):
    with open(path, "rb") as f:
        d = f.read()
    # ponytail: accept any padded size >= 0x0F0000; the 3 reference ROMs are 0xFF000
    if len(d) < 0xF0000:
        raise ValueError(f"{path}: too small ({len(d)} B)")
    return Rom(d, name or os.path.basename(path))


def summary(rom):
    bit, p2 = rom.bit(), rom.p2()
    return dict(file=rom.name, pci=rom.pci(), ptr=rom.ptr_maps(),
                bit=dict(base=bit["base"], ver=bit["ver"], count=bit["count"],
                         tokens={k: dict(ver=v["ver"], t_len=v["t_len"],
                                         raw=v["raw"], file=v["file"])
                                 for k, v in bit["tokens"].items()}),
                p2={k: dict(v) for k, v in p2.items()},
                perf=rom.perf_v60(),
                dcb={k: v for k, v in rom.dcb().items() if k != "entries"})


def compare(paths):
    """Table-by-table comparison of 2+ ROMs by structure, not file offset."""
    roms = [load(p) for p in paths]
    base = roms[0]
    p2 = base.p2()
    starts = sorted(v["file"] for v in p2.values())
    out = []
    for slot in sorted(p2):
        info = p2[slot]
        nxt = [s for s in starts if s > info["file"]]
        ln = min((nxt[0] - info["file"]) if nxt else 0x40, 0x4000)
        row = dict(slot=slot, name=info["name"], off=info["file"], span=ln)
        for r in roms[1:]:
            p = r.p2().get(slot)
            if not p:
                row[r.name] = "absent"
                continue
            a = base.d[info["file"]:info["file"] + ln]
            b = r.d[p["file"]:p["file"] + min(ln, len(r.d) - p["file"])]
            row[r.name] = f"{sum(1 for x, y in zip(a, b) if x == y)}/{min(len(a), len(b))} same"
        out.append(row)
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        print("usage: tu106_vbios.py parse   <rom> [rom...]")
        print("       tu106_vbios.py dump    <rom>")
        print("       tu106_vbios.py extents <rom>")
        print("       tu106_vbios.py compare <rom> <rom> [rom...]")
        return 2
    cmd, paths = argv[1], argv[2:]
    if cmd == "parse":
        for p in paths:
            print(json.dumps(summary(load(p)), indent=1))
    elif cmd == "compare":
        print(f"{'slot':>4} {'table':<24} {'CMP offset':>10} {'span':>5}  " +
              "  ".join(os.path.basename(p)[:10] for p in paths[1:]))
        for row in compare(paths):
            print(f"{row['slot']:>4} {row['name']:<24} {row['off']:#10x} {row['span']:>5}  " +
                  "  ".join(row[os.path.basename(p)] for p in paths[1:]))
    elif cmd == "extents":
        for p in paths:
            r = load(p)
            print("=" * 78)
            print(r.name, r.pci())
            for e in r.extents():
                print(f" s{e['slot']:2d} {e['name']:<24} {e['off']:#07x} {e['head']}"
                      f"  match={e['match']}")
    elif cmd == "dump":
        for p in paths:
            r = load(p)
            print("=" * 78)
            print(r.name, r.pci())
            print(" ptr map:", r.ptr_maps())
            pf = r.perf_v60()
            print(f"perf@{pf['hdr']:#x} ver={pf['ver']:#x} hdr={pf['hdr_len']} "
                  f"base={pf['base_len']} cnt={pf['entry_cnt']} sup={pf['sup_len']}x{pf['sup_cnt']} "
                  f"entry={pf['entry_len']} size={pf['size']} end={pf['end']:#x} "
                  f"flags0={pf['flags0']:#x} init_ps={pf['initial_pstate']:#x} "
                  f"cpi={pf['cpi_support_level']:#x}/{pf['cpi_features']:#x}")
            for e in pf["entries"]:
                print(f"  e{e['idx']} ps={e['pstate']:#04x} flags0={e['flags0']:#04x} "
                      f"cap={e['pstate_cap']} lpwr={e['lpwr_idx']:#x} pcie={e['pcie_idx']:#x} "
                      f"nvlink={e['nvlink_idx']:#x} skip={e['skip']}")
                print("     nom: " + " ".join(f"{s['domain']}={s['nom']}" for s in e["subs"]))
                print("     min: " + " ".join(f"{s['domain']}={s['mn']}" for s in e["subs"]))
                print("     max: " + " ".join(f"{s['domain']}={s['mx']}" for s in e["subs"]))
            ck = r.clocks_v35()
            if ck:
                print(f"clocks35@{ck['hdr']:#x} ver={ck['ver']:#x} rows={ck['count']} "
                      f"hal={ck['clocks_hal']} sampling={ck['sampling_ms']}ms")
                print("   " + " ".join(f"r{row['idx']}:{row['domain']}"
                                       f"={'M' if not row['identity_ok'] else ''}"
                                       f"{'FIXED' if row['usage'] == 0 else row['usage']}"
                                       for row in ck["rows"]))
            mct = r.mem_clock_table()
            print(f"memclk@{mct['hdr']:#x} base={mct['base_len']} strap={mct['strap_len']}"
                  f"x{mct['strap_cnt']} cnt={mct['entry_cnt']} size={mct['size']} end={mct['end']:#x}")
            mt = r.mem_tweak_table()
            print(f"memtweak@{mt['hdr']:#x} base={mt['base_len']} cnt={mt['entry_cnt']} "
                  f"size={mt['size']} end={mt['end']:#x}")
            bc = r.power_base_clock()
            print(f"pbc@{bc['hdr']:#x} ver={bc['ver']:#x} hlen={bc['hlen']} rlen={bc['rlen']} "
                  f"cnt={bc['entry_cnt']} sec={bc['secount']}x{bc['selen']} size={bc['size']}")
            for e in bc["entries"][:4]:
                print(f"   e{e['idx']} ps={e['pstate']:#04x} clocks={e['clocks']} "
                      f"valid={e['clocks_valid']}")
            d = r.dcb()
            print(f" dcb: {({k: v for k, v in d.items() if k != 'entries'})}")
            print(" dcb entries:", [(e["idx"], e["type_name"]) for e in d["entries"]])
    else:
        print(f"unknown command {cmd}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

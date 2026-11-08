#!/usr/bin/env python3
"""Self-checks for tu106_vbios.py against the three reference TU106 ROMs.

    python3 scripts/test_tu106_vbios.py [rom_dir]

Each block corresponds to a claim in docs/. Two regression guards at the top are
deliberately independent of the parser (they re-derive the value from raw bytes),
so a wrong parser offset cannot "prove itself right":

  regression 1  DCB entry type is the LOW NIBBLE of the display-path word
                (DCB 4.x spec: 0xF = Skip Entry, 0xE = EOL). Reading the whole
                byte counts 0x7F/0x8F as connectors -> 8/8 instead of 5/5.
  regression 2  PCIR image_len is at +0x10 in 512-byte blocks, not +0x0A
                (structure length 0x18/0x1C). Wrong offset gives 12288/14336
                instead of 0xF400/0xEC00.
"""
import os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tu106_vbios import load, Rom, CLK_DOMAINS, MEM_TWEAK_FIELDS

r_by_name = {}

ROMS = {"CMP40HX": "TU106.rom", "RTX2060S": "219827.rom", "RTX2070": "265590.rom"}
EXPECT_DEV = {"CMP40HX": 0x1F0B, "RTX2060S": 0x1F06, "RTX2070": 0x1F07}
EXPECT_LEGACY = {"CMP40HX": 0xF400, "RTX2060S": 0xEC00, "RTX2070": 0xEC00}
EXPECT_DCB_ACTIVE = {"CMP40HX": 0, "RTX2060S": 5, "RTX2070": 5}
EXPECT_CLOCKS = {"CMP40HX": (1468, 1648), "RTX2060S": (1468, 1648), "RTX2070": (1408, 1620)}


def _img_lens(raw):
    imgs = [m for m in range(len(raw)) if raw.startswith(b"PCIR", m)
            and struct.unpack_from("<H", raw, m + 4)[0] == 0x10DE]
    return [struct.unpack_from("<H", raw, m + 0x10)[0] * 512 for m in imgs], imgs


def regression_pcir_image_len(d):
    out = {}
    for k, fn in ROMS.items():
        raw = open(os.path.join(d, fn), "rb").read()
        lens, imgs = _img_lens(raw)
        struct_len = struct.unpack_from("<H", raw, imgs[0] + 0x0A)[0]
        assert struct_len in (0x18, 0x1C), hex(struct_len)   # NOT the image length
        assert lens[0] == EXPECT_LEGACY[k], (k, hex(lens[0]))
        assert lens[1] == 0x11000
        out[k] = lens[0]
    return out


def regression_dcb_type_nibble(d):
    out = {}
    for k, fn in ROMS.items():
        raw = open(os.path.join(d, fn), "rb").read()
        img0 = raw.find(b"\xff\xb8BIT") & ~0x1FF
        p = struct.unpack_from("<H", raw, img0 + 0x36)[0]
        lens, _ = _img_lens(raw)
        off = img0 + p + (lens[1] if p >= lens[0] else 0)
        assert struct.unpack_from("<I", raw, off + 6)[0] == 0x4EDCBDCB
        hdr, cnt, ln = raw[off + 1], raw[off + 2], raw[off + 3]
        words = [struct.unpack_from("<I", raw, off + hdr + i * ln)[0] for i in range(cnt)]
        types = [w & 0xF for w in words]
        active = sum(1 for t in types if t not in (0xE, 0xF))
        out[k] = (cnt, active, words)
    assert out["CMP40HX"][0] == 0 and out["CMP40HX"][1] == 0
    for k in ("RTX2060S", "RTX2070"):
        cnt, active, words = out[k]
        assert cnt == 16 and active == EXPECT_DCB_ACTIVE[k], (k, active)
        # whole-byte (wrong) reading would see 0x7F / 0x8F as connectors; the low
        # nibble says they are Skip entries.
        assert all((w & 0xF) == 0xF for w in words[4:7]), [hex(w) for w in words[4:7]]
    return out


def regression_p2_pointer_slot(d):
    """A P2 slot pointer lives at (P2 directory) + 4*N, and its value resolves
    elsewhere. v2 exported the resolved address as the pointer's own offset,
    which hides an off-by-one slot: slot N would look like slot N looked at the
    table address. Re-derive both from raw bytes here.

    The P2 directory address also has to come from the BIT record, not from the
    BIT entry offset: the version byte sits at record+1.
    """
    out = {}
    for k, fn in ROMS.items():
        raw = open(os.path.join(d, fn), "rb").read()
        bit_base = raw.find(b"\xff\xb8BIT")
        img0 = bit_base & ~0x1FF
        # header fields live at the BIT base, not at the 512-aligned image base
        hlen, rlen, cnt = raw[bit_base + 8], raw[bit_base + 9], raw[bit_base + 10]
        tok = None
        for i in range(cnt):
            o = bit_base + hlen + i * rlen
            if raw[o] == ord("P"):
                tok = (o, struct.unpack_from("<H", raw, o + 2)[0],
                       struct.unpack_from("<H", raw, o + 4)[0])
                break
        rec, t_len, t_off = tok
        assert raw[rec + 1] == 2, "BIT 'P' version byte is record+1"
        lens, _ = _img_lens(raw)
        p2 = img0 + t_off + (lens[1] if t_off >= lens[0] else 0)
        slots = {}
        for n in range(t_len // 4):
            v = struct.unpack_from("<I", raw, p2 + 4 * n)[0]
            if v:
                slots[n] = (p2 + 4 * n, v, img0 + v + (lens[1] if v >= lens[0] else 0))
        out[k] = (rec, p2, slots)
        # the advertised bug: reading at the target address is not the pointer
        assert struct.unpack_from("<I", raw, slots[0][2])[0] != slots[0][1]
    return out


def regression_mem_tweak_bitfield(d, rom_dir=None):
    """Re-extract four timing bitfields from raw CONFIG words with literal
    shifts. A wrong shift in MEM_TWEAK_FIELDS cannot pass this."""
    out = {}
    for k, fn in ROMS.items():
        raw = open(os.path.join(d, fn), "rb").read()
        r = r_by_name[k]
        mt = r.mem_tweak_table()
        for idx in (0, 14):
            e = mt["entries"][idx]
            w0 = struct.unpack_from("<I", raw, e["off"])[0]
            w1 = struct.unpack_from("<I", raw, e["off"] + 4)[0]
            w4 = struct.unpack_from("<I", raw, e["off"] + 16)[0]
            got = e["fields"]
            assert got["RC"]["raw"] == w0 and got["CL"]["raw"] == w1
            assert got["RC"]["value"] == (w0 & 0xFF)
            assert got["RFC"]["value"] == ((w0 >> 8) & 0x1FF)
            assert got["CL"]["value"] == (w1 & 0x7F)
            assert got["WL"]["value"] == ((w1 >> 7) & 0x7F)
            assert got["REFRESH"]["value"] == ((w4 >> 3) & 0xFFF)
            # every field must name the CONFIG word it actually came from
            for name, w, sh, mask in MEM_TWEAK_FIELDS:
                f = got[name]
                assert f["word_off"] == e["off"] + 4 * w, (name, hex(f["word_off"]))
                assert f["value"] == (e["cfg"][w] >> sh) & mask, name
            out.setdefault(k, {})[idx] = (got["RFC"]["value"], got["CL"]["value"])
    assert out["CMP40HX"][14] == (148, 20), out["CMP40HX"][14]
    assert out["RTX2060S"][14] == (180, 22), out["RTX2060S"][14]
    return out


def regression_pcie_script(d):
    """Decode the NVINIT PCIe settings script from raw bytes per the Devinit
    spec (0x7A = 9-byte ZM_REG, 0x6E = 13-byte NV_REG). The claim under test is
    that CMP and GeForce differ in exactly one bit of one write."""
    out = {}
    for k, fn in ROMS.items():
        raw = open(os.path.join(d, fn), "rb").read()
        bit_base = raw.find(b"\xff\xb8BIT")
        img0 = bit_base & ~0x1FF
        # header fields live at the BIT base, not at the 512-aligned image base
        hlen, rlen, cnt = raw[bit_base + 8], raw[bit_base + 9], raw[bit_base + 10]
        off = None
        for i in range(cnt):
            o = bit_base + hlen + i * rlen
            if raw[o] == ord("I"):
                p = struct.unpack_from("<H", raw, o + 4)[0]
                lens, _ = _img_lens(raw)
                nvinit = img0 + p + (lens[1] if p >= lens[0] else 0)
                sp = struct.unpack_from("<H", raw, nvinit + 0x12)[0]
                off = img0 + sp + (lens[1] if sp >= lens[0] else 0)
        writes, cur = [], off
        while True:
            op = raw[cur]
            if op == 0xFF:
                break
            if op == 0x7A:
                writes.append(("ZM", struct.unpack_from("<I", raw, cur + 1)[0],
                               struct.unpack_from("<I", raw, cur + 5)[0]))
                cur += 9
            elif op == 0x6E:
                a = struct.unpack_from("<I", raw, cur + 1)[0]
                m = struct.unpack_from("<I", raw, cur + 5)[0]
                v = struct.unpack_from("<I", raw, cur + 9)[0]
                writes.append(("NV", a, (m, v)))
                cur += 13
            elif op == 0x75:
                # INIT_CONDITION: everything after this point is conditional, so
                # the linear prefix ends here on purpose.
                break
            else:
                raise AssertionError(f"{k}: unexpected opcode {op:#x} at {cur:#x}")
        out[k] = writes
    assert [w[1] for w in out["CMP40HX"]] == [
        0x137C00, 0x8B900, 0x8C100, 0x88610, 0x8A088, 0x8B400, 0x1404]
    cmp_w = {w[1]: w[2] for w in out["CMP40HX"] if w[0] == "ZM"}
    gef_w = {w[1]: w[2] for w in out["RTX2060S"] if w[0] == "ZM"}
    diff = {a: (cmp_w[a], gef_w[a]) for a in cmp_w if cmp_w[a] != gef_w[a]}
    assert diff == {0x88610: (0x1, 0x1001)}, diff       # bit 12 only
    return out


def regression_power_budget_extent(d):
    """POWER BUDGET closes exactly only if the four block sizes in its own
    header are read at the right offsets. Recompute from raw bytes: a wrong
    header offset cannot close the table onto the next P2 start."""
    out = {}
    for k, fn in ROMS.items():
        raw = open(os.path.join(d, fn), "rb").read()
        r = r_by_name[k]
        p2 = r.p2()
        off = p2[11]["file"]
        ns = min(v["file"] for v in p2.values() if v["file"] > off)
        hlen, esz, cnt = raw[off + 1], raw[off + 2], raw[off + 3]
        rel_esz, rel_cnt = raw[off + 8], raw[off + 9]
        viol_esz, viol_cnt = raw[off + 34], raw[off + 35]
        tot = hlen + cnt * esz + rel_cnt * rel_esz + viol_cnt * viol_esz
        assert off + tot == ns, (k, tot, ns - off)
        out[k] = (hlen, esz, cnt, rel_esz, rel_cnt, viol_esz, viol_cnt)
    assert out["CMP40HX"] == (44, 66, 20, 14, 15, 13, 13), out["CMP40HX"]
    assert out["RTX2060S"] == out["CMP40HX"] == out["RTX2070"]
    return out


def run(d):
    global r_by_name
    r = {k: load(os.path.join(d, v), k) for k, v in ROMS.items()}
    r_by_name = r

    # --- regression guards (independent of the parser) ----------------------
    regression_pcir_image_len(d)
    regression_dcb_type_nibble(d)
    regression_p2_pointer_slot(d)
    regression_mem_tweak_bitfield(d)
    regression_pcie_script(d)
    regression_power_budget_extent(d)

    # --- PCI image chain ---------------------------------------------------
    for k, rom in r.items():
        imgs = rom.images()
        assert len(imgs) == 4, (k, len(imgs))          # 2 banks x (legacy + EFI)
        assert imgs[0]["device"] == EXPECT_DEV[k]
        assert imgs[0]["image_len"] == EXPECT_LEGACY[k]
        assert imgs[1]["image_len"] == 0x11000
        assert rom.image0_base() == 0x28600
        assert rom.ptr_maps() == dict(image0_base=0x28600,
                                      legacy_len=EXPECT_LEGACY[k],
                                      efi_len=0x11000, image_count=4)
        assert rom.pci()["class_code"] == (0x030200 if k == "CMP40HX" else 0x030000)

    # pointer rule must use the parsed legacy length, not a constant
    assert Rom.ptr(r["RTX2060S"], 0x232) == 0x28600 + 0x232
    assert Rom.ptr(r["RTX2060S"], 0xEC00) == 0x28600 + 0xEC00 + 0x11000
    assert Rom.ptr(r["CMP40HX"], 0xF3FF) == 0x28600 + 0xF3FF
    assert Rom.ptr(r["CMP40HX"], 0xF400) == 0x28600 + 0xF400 + 0x11000

    # --- BIT ---------------------------------------------------------------
    for k, rom in r.items():
        b = rom.bit()
        assert b["ver"] == 0x0100 and (b["hlen"], b["rlen"], b["count"]) == (12, 6, 17)
        assert rom.d[b["base"]:b["base"] + 2] == b"\xff\xb8"
        assert rom.d[b["base"] + 2:b["base"] + 6] == b"BIT\x00"
        assert set(b["tokens"]) == set("2BCDIMNPSTUVdipux")
        for tok in b["tokens"].values():
            assert 0 <= tok["file"] < len(rom.d)

    # --- P2 directory ------------------------------------------------------
    for k, rom in r.items():
        p2 = rom.p2()
        assert len(p2) == 40
        P = rom.bit()["tokens"]["P"]
        for slot, v in p2.items():
            # the pointer slot is P2 base + 4*N; the table it addresses is elsewhere
            assert v["ptr_off"] == P["file"] + 4 * slot, (k, slot)
            assert v["file"] == rom.ptr(v["raw"])
            assert v["file"] != v["ptr_off"] or slot == 0 and False
        assert p2[0]["ptr_off"] == P["file"] and p2[14]["ptr_off"] == P["file"] + 56
    assert r["CMP40HX"].bit()["tokens"]["P"]["t_len"] == 224   # 56 slots
    assert r["RTX2060S"].bit()["tokens"]["P"]["t_len"] == 196  # 49 slots

    # pcie_idx / lpwr_entry_idx are indices with no public target schema: the
    # ranges must at least be consistent with the tables the ROM does have.
    for k, rom in r.items():
        idx = {e["pcie_idx"] for e in rom.perf_v60()["entries"] if not e["skip"]}
        # CMP drops p-state 0x0A, and 0x0A is the only entry that uses
        # pcie_idx=1 -> the CMP ROM never references PCIe config entry 1.
        assert idx == ({0, 2} if k == "CMP40HX" else {0, 1, 2}), (k, idx)
        live = rom.lpwr_pcie()
        assert idx and max(idx) < live["count"], (k, idx, live["count"])
        lp = {e["lpwr_idx"] for e in rom.perf_v60()["entries"] if not e["skip"]}
        assert lp <= {0, 1, 2, 4}, (k, lp)

    # --- LOW POWER PCIe (slot 30): structural fit only ---------------------
    for k, rom in r.items():
        lp = rom.lpwr_pcie()
        assert (lp["ver"], lp["hlen"], lp["entry_len"], lp["count"]) == (0x10, 5, 12, 5)
        assert lp["size"] == 65 and lp["end"] == rom.p2()[31]["file"]
        assert all(len(e["raw"]) == 12 for e in lp["entries"])
    lp_cmp, lp_20 = r["CMP40HX"].lpwr_pcie(), r["RTX2060S"].lpwr_pcie()
    assert lp_cmp["entries"][0]["raw"] == bytes.fromhex("fffdfffffa481ffdfb9ff8ff")
    assert lp_20["entries"][0]["raw"] == bytes.fromhex("fffdfffffa481ffdf89ff8ff")
    # every entry differs at byte 8 only: CMP 0xfb, GeForce 0xf8 (bits 0 and 1)
    for a, b in zip(lp_cmp["entries"], lp_20["entries"]):
        diff = [i for i, (x, y) in enumerate(zip(a["raw"], b["raw"])) if x != y]
        assert diff == [8], (a["idx"], diff)
        assert (a["raw"][8], b["raw"][8]) == (0xFB, 0xF8), (a["raw"][8], b["raw"][8])

    # --- PCIe settings script ---------------------------------------------
    for k, rom in r.items():
        ps = rom.pcie_settings_script()
        ops = [o["op"] for o in ps["ops"]]
        assert ops == ["ZM_REG", "NV_REG", "NV_REG", "ZM_REG", "NV_REG", "ZM_REG",
                       "NV_REG", "CONDITION", "STOP INIT_SUB_DIRECT (0x5b)"], (k, ops)
        # CONDITION 86 on CMP, 82 on both GeForce: same script shape, different
        # fuse/strap condition id. Not decoded here.
        assert ps["ops"][7]["cond"] == (86 if k == "CMP40HX" else 82), (k, ps["ops"][7])
        assert [o["addr"] for o in ps["ops"] if "addr" in o] == [
            0x137C00, 0x8B900, 0x8C100, 0x88610, 0x8A088, 0x8B400, 0x1404]
        assert ps["ops"][1]["mask"] == 0xFFFFFFFF and ps["ops"][1]["data"] == 0
        assert ps["ops"][4]["mask"] == 0xFFFFFFFC and ps["ops"][4]["data"] == 3
        assert ps["ops"][6]["mask"] == 0xFFFFFBFF      # clears bit 10 of 0x1404
    # the only PCIe-script difference between CMP and GeForce is bit 12 of 0x88610
    cmp_z = [o for o in r["CMP40HX"].pcie_settings_script()["ops"] if o["op"] == "ZM_REG"]
    gef_z = [o for o in r["RTX2060S"].pcie_settings_script()["ops"] if o["op"] == "ZM_REG"]
    assert [(o["addr"], o["data"]) for o in cmp_z] != [(o["addr"], o["data"]) for o in gef_z]
    assert r["CMP40HX"].pcie_settings_script()["ops"][3]["data"] == 0x1
    assert r["RTX2060S"].pcie_settings_script()["ops"][3]["data"] == 0x1001
    assert (r["CMP40HX"].pcie_settings_script()["off"]
            != r["RTX2060S"].pcie_settings_script()["off"])

    # --- DCB (spec-correct nibble) -----------------------------------------
    for k, rom in r.items():
        dcb = rom.dcb()
        assert dcb["cnt"] == (0 if k == "CMP40HX" else 16)
        assert dcb["active"] == EXPECT_DCB_ACTIVE[k], (k, dcb["active"])
        names = [e["type_name"] for e in dcb["entries"] if not e["skip"]]
        if k == "CMP40HX":
            assert names == []
        else:
            assert names[0] == "DisplayPort" and "TMDS" in names
            assert all(e["type"] != 0xE for e in dcb["entries"])

    # --- PERFORMANCE v0x60: NVIDIA nvgpu vbios_pstate_6x -------------------
    for k, rom in r.items():
        pf = rom.perf_v60()
        assert (pf["ver"], pf["hdr_len"], pf["base_len"], pf["entry_cnt"],
                pf["sup_len"], pf["sup_cnt"]) == (0x60, 10, 5, 7, 6, 10)
        assert pf["entry_len"] == 65 and pf["size"] == 465
        assert pf["end"] == rom.p2()[14]["file"], "must end at POWER BASE CLOCK"
        assert pf["pstates_required"] == 1 and pf["initial_pstate"] == 0x07
        assert [s["domain"] for s in pf["entries"][0]["subs"]] == list(CLK_DOMAINS)
        assert len(pf["entries"]) == 7
        for e in pf["entries"]:
            assert len(e["subs"]) == 10
            for s in e["subs"]:
                assert pf["hdr"] <= s["off"] and s["off"] + 6 <= pf["end"]

    # skip entries carry no data (guards against reading unused records)
    for k, rom in r.items():
        for e in rom.perf_v60()["entries"]:
            if e["skip"]:
                assert all(s["nom"] == 0 and s["mn"] == 0 and s["mx"] == 0
                           for s in e["subs"]), k

    ps = {k: [e["pstate"] for e in rom.perf_v60()["entries"]] for k, rom in r.items()}
    assert ps["CMP40HX"] == [0x07, 0xFF, 0xFF, 0x0C, 0xFF, 0xFF, 0x0F]
    assert ps["RTX2060S"] == [0x07, 0x0A, 0xFF, 0x0C, 0x0D, 0xFF, 0x0F]
    assert ps["RTX2070"] == ps["RTX2060S"]

    # DRAM (index 2): nominal = memory data rate; 7001 = 14 Gbps.
    for k, rom in r.items():
        assert rom.perf_v60()["entries"][6]["subs"][2]["nom"] == 7001, k
        assert rom.perf_v60()["entries"][3]["subs"][2]["nom"] == 5001, k

    # HUB (4) and DISP (7): 27 MHz reference on CMP, real clocks on both GeForce.
    for k, rom in r.items():
        subs = rom.perf_v60()["entries"][6]["subs"]
        if k == "CMP40HX":
            assert (subs[4]["nom"], subs[4]["mn"], subs[4]["mx"]) == (27, 27, 27)
            assert (subs[7]["nom"], subs[7]["mn"], subs[7]["mx"]) == (27, 27, 27)
        else:
            assert (subs[4]["nom"], subs[4]["mx"]) == (540, 810), (k, subs[4])
            assert (subs[7]["nom"], subs[7]["mx"]) == (1080, 1330), (k, subs[7])

    # GPC (0) is identical on all three cards -> the P-state table does not
    # carry the boost clock and does not differentiate CMP from the GeForce.
    # CMP has fewer p-states, so compare the per-level GPC values, not the list
    # length (the extra GeForce levels reuse identical entries).
    gpc = {k: {(e["subs"][0]["nom"], e["subs"][0]["mn"], e["subs"][0]["mx"])
               for e in rom.perf_v60()["entries"] if not e["skip"]}
           for k, rom in r.items()}
    assert gpc["CMP40HX"] == gpc["RTX2060S"] == gpc["RTX2070"], gpc
    assert gpc["CMP40HX"] == {(645, 300, 645), (645, 300, 2100)}

    # The four bytes flagged by the earlier analysis (+0x27..+0x2B) are HUB
    # nominal/low/max, not a separate switch.
    seg = {k: rom.d[rom.perf_v60()["hdr"]:rom.perf_v60()["hdr"] + 0x2C]
           for k, rom in r.items()}
    assert seg["CMP40HX"][0x27:0x2C] == bytes([0x1B, 0x00, 0x1B, 0xC0, 0x06])
    assert seg["RTX2060S"][0x27:0x2C] == bytes([0xCA, 0x00, 0xCA, 0x80, 0x32])
    assert seg["RTX2070"][0x27:0x2C] == bytes([0xCA, 0x00, 0xCA, 0x80, 0x32])
    hub = r["CMP40HX"].perf_v60()["entries"][0]["subs"][4]
    assert (hub["nom"], hub["mn"], hub["mx"]) == (27, 27, 27)

    # --- CLOCKS v0x35: ten domains, identity = ordering byte --------------
    for k, rom in r.items():
        ck = rom.clocks_v35()
        assert ck and ck["ver"] == 0x35 and ck["count"] == 10 and ck["row_len"] == 11
        assert [row["identity_ok"] for row in ck["rows"]] == [True] * 10
        assert [row["domain"] for row in ck["rows"]] == list(CLK_DOMAINS)
        usage = {row["domain"]: row["usage"] for row in ck["rows"]}
        assert usage["PWR"] == 0 and usage["GPC"] == 1 and usage["DRAM"] == 1
        if k == "CMP40HX":
            assert usage["HUB"] == 0 and usage["DISP"] == 0
        else:
            assert usage["HUB"] == 2 and usage["DISP"] == 1

    # --- POWER BASE CLOCK: base / boost -----------------------------------
    for k, rom in r.items():
        bc = rom.power_base_clock()
        assert bc["ver"] == 0x20 and bc["entry_cnt"] == 17
        assert (bc["hlen"], bc["rlen"], bc["secount"], bc["selen"]) == (19, 1, 4, 10)
        assert bc["size"] == 716 and bc["end"] == rom.p2()[17]["file"]
        base, boost = bc["entries"][0]["clocks"][0], bc["entries"][2]["clocks"][0]
        assert (base, boost) == EXPECT_CLOCKS[k], (k, base, boost)
        assert bc["entries"][10]["pstate"] == 0xFF

    # --- memory tables -----------------------------------------------------
    for k, rom in r.items():
        mc = rom.mem_clock_table()
        assert mc["ver"] == 0x11 and mc["size"] == 2756
        assert mc["end"] == rom.p2()[2]["file"]
        assert (mc["hdr_len"], mc["base_len"], mc["strap_len"],
                mc["strap_cnt"], mc["entry_cnt"]) == (26, 60, 33, 10, 7)
        for a, b in zip(mc["entries"], mc["entries"][1:]):
            assert b["min_mhz"] == a["max_mhz"] + 1 or a["idx"] == 1
        mt = rom.mem_tweak_table()
        assert mt["ver"] == 0x20 and mt["size"] == 4446
        assert mt["end"] == rom.p2()[29]["file"]
        assert (mt["hdr_len"], mt["base_len"], mt["entry_cnt"]) == (6, 74, 60)
        assert mt["entries"][0]["CL"] == 24 and mt["entries"][0]["RFC"] == 210
        assert mt["entries"][0]["RC"] == 78 and mt["entries"][0]["WR"] == 27
        assert [mt["entries"][i]["CL"] for i in range(4)] == [24, 23, 22, 20]


    # --- POWER BUDGET / TOPOLOGY / THERMAL POLICY / LOW POWER GR -----------
    def next_by_addr(rom, slot):
        off = rom.p2()[slot]["file"]
        return min(v["file"] for v in rom.p2().values() if v["file"] > off)

    for k, rom in r.items():
        pb = rom.power_budget()
        assert (pb["ver"], pb["hlen"], pb["entry_len"], pb["count"]) == (0x30, 44, 66, 20)
        assert pb["size"] == 1743 and pb["end"] == next_by_addr(rom, 11)
        assert (pb["rel_len"], pb["rel_cnt"], pb["viol_len"], pb["viol_cnt"]) == (14, 15, 13, 13)
        e = pb["entries"][2]
        assert e["class_id"] == 1 and e["limit_rated"] > 100000, (k, e["limit_rated"])
        assert e["limit_min"] < e["limit_rated"] < e["limit_max"]

        pt = rom.power_topology()
        assert (pt["ver"], pt["hlen"], pt["entry_len"], pt["count"]) == (0x20, 6, 22, 20)
        assert pt["size"] == 851 and pt["end"] == next_by_addr(rom, 15)
        assert (pt["rel_len"], pt["rel_cnt"]) == (27, 15)
        assert pt["entries"][0]["class_id"] == 2 and pt["entries"][0]["pwr_rail"] == 0xDF

        tp = rom.thermal_policy()
        assert (tp["ver"], tp["hlen"], tp["entry_len"], tp["count"]) == (0x10, 10, 40, 4)
        assert tp["size"] == 170 and tp["end"] == next_by_addr(rom, 20)

        lg = rom.lpwr_gr()
        assert (lg["ver"], lg["hlen"], lg["entry_len"], lg["count"]) == (0x10, 10, 5, 5)
        assert lg["size"] == 35 and lg["end"] == next_by_addr(rom, 32)

    # default/rated/max GPU power limit, class-1 entry, in mW
    w = {k: [e["limit_min"] for e in rom.power_budget()["entries"] if e["class_id"] == 1]
         for k, rom in r.items()}
    rated = {k: [e["limit_rated"] for e in rom.power_budget()["entries"]
                 if e["class_id"] == 1] for k, rom in r.items()}
    capped = {k: [e["limit_max"] for e in rom.power_budget()["entries"]
                  if e["class_id"] == 1] for k, rom in r.items()}
    assert w == {"CMP40HX": [110000], "RTX2060S": [125000], "RTX2070": [125000]}, w
    # CMP's default limit equals the 2060S; it is NOT a lower ceiling.
    assert rated == {"CMP40HX": [184000], "RTX2060S": [184000], "RTX2070": [185000]}, rated
    assert capped == {"CMP40HX": [220000], "RTX2060S": [220000], "RTX2070": [222000]}, capped

    # POWER TOPOLOGY is byte-identical across the three cards
    ptb = {k: rom.d[rom.power_topology()["hdr"]:rom.power_topology()["end"]]
           for k, rom in r.items()}
    assert ptb["CMP40HX"] == ptb["RTX2060S"] == ptb["RTX2070"]

    # THERMAL POLICY: CMP differs from both GeForce at exactly one header byte
    tpt = {k: rom.thermal_policy()["hdr_tail"] for k, rom in r.items()}
    assert tpt["CMP40HX"][0] == 0xFF and tpt["RTX2060S"][0] == 0x02
    assert sum(a != b for a, b in zip(tpt["CMP40HX"], tpt["RTX2060S"])) == 1
    # LOW POWER GR header is identical; only one feature mask differs
    lgt = {k: rom.lpwr_gr()["hdr_tail"] for k, rom in r.items()}
    assert lgt["CMP40HX"] == lgt["RTX2060S"] == lgt["RTX2070"]
    lge = {k: [e["raw"].hex() for e in rom.lpwr_gr()["entries"]] for k, rom in r.items()}
    # entry = u32 feature_mask (little-endian) + 1 tail byte. Phase 4 said
    # "bit 27" from the byte position; the actual u32 XOR is 0x8 => bit 3.
    assert lge["CMP40HX"][0] == "e7ffffff01", lge["CMP40HX"][0]
    assert lge["RTX2060S"][0] == "efffffff01", lge["RTX2060S"][0]
    assert lge["CMP40HX"][1:] == lge["RTX2060S"][1:]
    for k, rom in r.items():
        m = rom.lpwr_gr()["entries"][0]["feature_mask"]
        assert m & 0x1, k                      # bit 0 GR, set everywhere
        assert not (m & 0x10), k               # bit 4 RPPG clear everywhere
        assert bool(m & 0x8) == (k != "CMP40HX"), (k, hex(m))
    # only bit 3 differs between CMP and GeForce, in entry 0 only
    masks = {k: [e["feature_mask"] for e in rom.lpwr_gr()["entries"]]
             for k, rom in r.items()}
    assert masks["CMP40HX"][0] ^ masks["RTX2060S"][0] == 0x8
    assert masks["CMP40HX"][1:] == masks["RTX2060S"][1:]

    # --- VFE 3x (slot 8): structure closes only with the rppm blocks -------
    for k, rom in r.items():
        v = rom.vfe_3x()
        assert (v["ver"], v["hlen"], v["var_len"], v["var_cnt"],
                v["equ_len"], v["equ_cnt"]) == (0x30, 9, 25, 20, 24, 150)
        assert v["span"] == 5444 and v["extent_ok"]
        assert len(v["vars"]) == 20 and len(v["equs"]) == 150
        assert len(v["rppm"]) == v["var_rppm_cnt"] + v["equ_rppm_cnt"] == 55
        assert len(v["rppm_tail"]) == 15
        # a wrong stride would put non-type bytes here
        assert all(e["type"] <= 0x07 for e in v["vars"]), k
        assert all(e["type"] <= 0x06 for e in v["equs"]), k
        # 0xFF = VBIOS_VFE_3X_EQU_ENTRY_IDX_INVALID is legal
        assert all(e["var_idx"] < 20 or e["var_idx"] == 0xFF
                   for e in v["equs"]), k

    # --- display token 'U' -------------------------------------------------
    for k, rom in r.items():
        u = rom.bit()["tokens"]["U"]
        raw = rom.bytes(u["file"], u["t_len"])
        if k == "CMP40HX":
            assert raw[:2] == b"\x00\x00", "CMP: display script pointer is 0"
            assert raw[2] == 0x02
        else:
            assert raw[:2] != b"\x00\x00" and raw[2] == 0x00

    # --- bounds guard ------------------------------------------------------
    for bad in ((-1, 1), (len(r["CMP40HX"].d) - 1, 4)):
        try:
            r["CMP40HX"].bytes(*bad)
        except IndexError:
            pass
        else:
            raise AssertionError(f"out-of-bounds read {bad} was not rejected")

    print("ok: all TU106 VBIOS self-checks passed")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CMP_ROM_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "roms")))

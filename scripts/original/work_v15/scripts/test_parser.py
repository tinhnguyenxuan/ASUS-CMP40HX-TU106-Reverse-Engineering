#!/usr/bin/env python3
"""A10: unit test parser tren ROM thuc. Chay: python3 test_parser.py"""
import hashlib
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vbios_parser import bitmap, images, perf_tables, ptr, table, vfe  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROM = os.path.join(HERE, "..", "outputs", "CMP40HX_ORIGINAL_1MB.bin")
T4 = os.path.join(HERE, "..", "outputs", "cmp40hx_t4.bin")

ROM_SHA = "dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec"
T4_SHA = "aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb"


def test_hash():
    rom = open(ROM, "rb").read()
    t4 = open(T4, "rb").read()
    assert len(rom) == 1048576
    assert len(t4) == 495616
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA
    assert hashlib.sha256(t4).hexdigest() == T4_SHA
    # T4 = rom[0:0x79000] sua 19 byte; ngoai 19 byte do phai trung khop
    d = [i for i in range(len(t4)) if rom[i] != t4[i]]
    assert len(d) == 19
    assert all(rom[i] == t4[i] for i in range(len(t4)) if i not in set(d))


def test_ptr_formula():
    rom = open(ROM, "rb").read()
    assert ptr(0) == 0x28600
    assert ptr(0x0000) == 0x28600
    # 0xF400 = 0x28600+0xF400 = 0x37A00 (dung bang, khong cong them)
    # con tro chi so tren "anh ao": legacy ++ (phan sau EFI trong ROM that)
    # nen p >= 0xF400 phai nhay qua CA khoi EFI (0x11000)
    assert ptr(0xF3FF) == 0x379FF, "byte cuoi legacy"
    assert ptr(0xF400) == 0x48A00, "vuot nguong -> nhay qua EFI"
    # cross-check ground truth: PERF_PTRS[1] = 0x1B000 -> 0x54600
    assert ptr(0x1B000) == 0x54600
    assert ptr(0x1000) == 0x29600, "duoi nguong khong cong"
    # cross-check: BIT con tro thuc te
    b = bitmap(rom)
    assert b["tokens"] == 17
    assert b["map"]["0x50"]["file_off"] > 0x28600


def test_checksum():
    rom = open(ROM, "rb").read()
    t4 = open(T4, "rb").read()
    for im in images(rom):
        if im["name"] in ("bank1", "bank2", "NPDE"):
            continue
        assert (sum(rom[im["start"]:im["end"]]) & 0xFF) == 0, im["name"]
        if im["end"] <= len(t4):
            assert (sum(t4[im["start"]:im["end"]]) & 0xFF) == 0, f"T4 {im['name']}"

    # cong thuc sua checksum
    d = [i for i in range(len(t4)) if rom[i] != t4[i] and i != 0x767FF]
    delta = sum(t4[i] - rom[i] for i in d)
    assert (rom[0x767FF] - delta) & 0xFF == t4[0x767FF]


def test_vfe():
    rom = open(ROM, "rb").read()
    t4 = open(T4, "rb").read()
    v = vfe(rom)
    assert v["slot_base"] == 0x56699
    assert v["slot_stride"] == 24
    assert v["slot_count"] == 150
    assert v["var_stride"] == 25
    assert v["var_count"] == 20

    # slot 0 = REL, type 1 constant, var_idx 10
    s0 = v["slots"][0]
    assert s0["type"] == 1 and s0["var_idx"] == 10
    assert s0["off"] == 0x56699
    assert abs(s0["c0"] - 1068750.0) < 1
    assert s0["c1"] == 0 and s0["c2"] == 0

    # selector khong doi
    assert rom[0x2D384:0x2D387] == b"\x00\x01\x03"
    assert t4[0x2D384:0x2D387] == b"\x00\x01\x03"

    # T4 nang ca 2 len 1125000
    v4 = vfe(t4)
    for i in (0, 1):
        assert abs(v4["slots"][i]["c0"] - 1125000.0) < 1, i
        assert abs(v4["slots"][i]["lo"] - 1125000.0) < 1, i

    # var[7] = MHz, var[13] = uV
    assert 1900 < v["vars"][7]["lo"] < 2000
    assert 2300 < v["vars"][7]["hi"] < 2400
    assert 400000 < v["vars"][13]["lo"] < 500000
    assert 1200000 < v["vars"][13]["hi"] < 1300000


def test_perf_tables():
    rom = open(ROM, "rb").read()
    ts = perf_tables(rom)
    assert len(ts) == 40, f"mong 40 bang, thay {len(ts)}"
    for t in ts:
        assert t["size"] == t["hdr"] + t["esz"] * t["cnt"]
        assert t["off"] + t["size"] <= len(rom)


def test_payload_boundary():
    rom = open(ROM, "rb").read()
    # 0x79000 = NVGIf container thu 2 -> bien gioi that
    assert rom[0x79000:0x79005] == b"NVGIf"
    assert rom[0:0x5] == b"NVGIf"
    # vung 0x78400..0x79000 la padding FF
    assert set(rom[0x78400:0x79000]) == {0xFF}
    # sau 0x79000 co du lieu that
    assert set(rom[0x79000:0x79100]) != {0xFF}


def test_diff_bytes():
    rom = open(ROM, "rb").read()
    t4 = open(T4, "rb").read()
    d = [i for i in range(len(t4)) if rom[i] != t4[i]]
    assert len(d) == 19, f"mong 19 byte, thay {len(d)}"
    assert d[-1] == 0x767FF
    assert all(0x5669C <= i <= 0x566BE for i in d[:-1])


def demo():
    """Self-check chay duoc: python3 test_parser.py"""
    fns = [test_hash, test_ptr_formula, test_checksum, test_vfe,
           test_perf_tables, test_payload_boundary, test_diff_bytes]
    for f in fns:
        f()
        print(f"  PASS  {f.__name__}")
    print(f"\n  {len(fns)}/{len(fns)} test pass")


if __name__ == "__main__":
    demo()

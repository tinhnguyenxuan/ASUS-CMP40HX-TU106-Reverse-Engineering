#!/usr/bin/env python3
import hashlib
import json
import pathlib
import struct

ROOT = pathlib.Path(__file__).resolve().parents[1]
inventory = json.loads((ROOT / "evidence/firmware_capability_inventory.json").read_text())
record = inventory[0]
firmware = pathlib.Path(record["path"])
blob = firmware.read_bytes()
sections = [s for s in record["inner_elf"]["sections"] if s["type"] != 8 and s["size"]]


def file_offset(va, size=1):
    for section in sections:
        if section["va"] <= va and va + size <= section["va"] + section["size"]:
            return section["file_offset"] + va - section["va"]
    raise ValueError(f"unmapped VA {va:#x}")


def word(va):
    return struct.unpack_from("<I", blob, file_offset(va, 4))[0]


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def decode_store(va):
    insn = word(va)
    assert insn & 0x7F == 0x23
    return {
        "va": hex(va),
        "funct3": (insn >> 12) & 7,
        "base_register": (insn >> 15) & 31,
        "source_register": (insn >> 20) & 31,
        "displacement": signed(((insn >> 25) << 5) | ((insn >> 7) & 31), 12),
    }


strings = {}
for va, expected in (
    (0x040B3010, b"RMRunFub\0"),
    (0x040B3020, b"RMFubUseCaseMask\0"),
    (0x040B3038, b"RmDisableDisplay\0"),
):
    offset = file_offset(va, len(expected))
    assert blob[offset:offset + len(expected)] == expected
    strings[hex(va)] = expected[:-1].decode()

# Function prologue at 0x04b30030 saves a1 into s3.
assert word(0x04B30050) == 0x00058993  # addi s3,a1,0

stores = [decode_store(va) for va in (0x04B30130, 0x04B30128, 0x04B30138)]
assert stores == [
    {"va": "0x4b30130", "funct3": 0, "base_register": 19, "source_register": 15, "displacement": 0x328},
    {"va": "0x4b30128", "funct3": 2, "base_register": 19, "source_register": 15, "displacement": 0x32C},
    {"va": "0x4b30138", "funct3": 2, "base_register": 19, "source_register": 15, "displacement": 0x334},
]

# The only statically encoded direct call to the worker is in its wrapper.
assert word(0x04B301E0) & 0x7F == 0x17
jalr = word(0x04B301E4)
target = 0x04B301E0 + signed(word(0x04B301E0) & 0xFFFFF000, 32) + signed(jalr >> 20, 12)
assert target == 0x04B30030

# A downstream gate reads the same second-argument field. When nonzero it
# branches to a path that writes zero to the caller's byte output; when zero
# the fall-through writes one.
assert word(0x04B20F80) == 0x3345A783  # lw a5,0x334(a1)
assert word(0x04B20F84) == 0x04079463  # bnez a5,0x48 -> 0x04b20fcc
assert word(0x04B20F88) == 0x00100513  # addi a0,zero,1
assert word(0x04B20F8C) == 0x00A48023  # sb a0,0(s1)
assert word(0x04B20FE0) == 0x00000513  # addi a0,zero,0
assert word(0x04B20FE4) == 0x00A48023  # sb a0,0(s1)

# Three explicit HAL/object-table construction paths install this consumer at
# slot +0x158. (A fourth address construction at 0x05572fe8 feeds shared code.)
consumer_install_sites = []
for hi_va, lo_va, store_va, reg in (
    (0x05571A18, 0x05571A1C, 0x05571A20, 12),
    (0x05571B28, 0x05571B2C, 0x05571B30, 15),
    (0x05572800, 0x05572804, 0x05572808, 12),
):
    hi = word(hi_va)
    lo = word(lo_va)
    store = decode_store(store_va)
    assert hi & 0x7F == 0x37 and (hi >> 7) & 31 == reg
    assert lo & 0x7F == 0x13 and (lo >> 7) & 31 == reg and (lo >> 15) & 31 == reg
    address = (signed(hi & 0xFFFFF000, 32) + signed(lo >> 20, 12)) & 0xFFFFFFFFFFFFFFFF
    assert address == 0x04B20F54
    assert store["funct3"] == 3 and store["base_register"] == 10
    assert store["source_register"] == reg and store["displacement"] == 0x158
    consumer_install_sites.append(hex(hi_va))

assert word(0x04B20FA8) == 0x1B053783  # ld a5,0x1b0(a0), fallback dispatch
assert word(0x04B20FAC) == 0x000780E7  # jalr a5

# The a0+0x737 prerequisite is cached earlier during object initialization from
# another virtual/HAL call through slot +0xb8 of that same object.
assert word(0x04B72790) == 0x0B84B783  # ld a5,0xb8(s1)
assert word(0x04B72794) == 0x00048513  # addi a0,s1,0
assert word(0x04B72798) == 0x000780E7  # jalr a5
assert word(0x04B7279C) == 0x72A48BA3  # sb a0,0x737(s1)

# Site A independently suppresses a HAL predicate at a1+0x1c8 when
# RmDisableDisplay==1. Its missing-key path checks the cached +0x737 byte.
assert word(0x04840390) == 0x1C84B783  # ld a5,0x1c8(s1)
assert word(0x0484039C) == 0x000780E7  # jalr a5
assert word(0x048403D4) == 0x6DD94783  # lbu a5,0x6dd(s2)
assert word(0x048403DC) == 0x73794783  # lbu a5,0x737(s2)
assert word(0x048403E4) == 0x6D094783  # lbu a5,0x6d0(s2)
assert word(0x048403EC) == 0xF809C783  # lbu a5,-0x80(s3) == a0+0x4f80

# The recovered HAL-table constructor installs two concrete predicates used by
# the site-B fallback (+0x1b0) and site-A final dispatch (+0x1c8).
assert word(0x05571BAC) == 0x04B1A7B7
assert word(0x05571BB0) == 0xEA478793
assert word(0x05571BB4) == 0x1AF53823  # 0x04b19ea4 -> +0x1b0
assert word(0x05571BD0) == 0x04B1A7B7
assert word(0x05571BD4) == 0x01878793
assert word(0x05571BD8) == 0x1CF53423  # 0x04b1a018 -> +0x1c8

# Both predicates read register selector/offset 0x3814 via accessor +0x108 in
# the HAL object. The first returns whether mask 0x000c0000 is nonzero; the
# second returns bit 27. The source-level register/field names remain unproved.
for va in (0x04B19EB8, 0x04B1A02C):
    assert word(va) == 0x1085B803  # ld a6,0x108(a1)
for va in (0x04B19EC0, 0x04B1A034):
    assert word(va) == 0x00004637  # lui a2,4
for va in (0x04B19ED0, 0x04B1A044):
    assert word(va) == 0x81460613  # addi a2,a2,-0x7ec => 0x3814
assert word(0x04B19EF8) == 0x000C0737  # lui a4,0xc0 => 0x000c0000
assert word(0x04B19EFC) == 0x00E57533  # and a0,a0,a4
assert word(0x04B19F10) == 0x00A03533  # snez a0,a0
assert word(0x04B1A078) == 0x41B5551B  # sraiw a0,a0,27
assert word(0x04B1A080) == 0x00157513  # andi a0,a0,1

# The wrapper has one literal pointer occurrence, in a read-only function table.
needle = struct.pack("<Q", 0x04B301B8)
positions = []
cursor = 0
while True:
    cursor = blob.find(needle, cursor)
    if cursor < 0:
        break
    positions.append(cursor)
    cursor += 1
assert positions == [0x33E90]

result = {
    "firmware": str(firmware),
    "sha256": hashlib.sha256(blob).hexdigest(),
    "worker": "0x04b30030",
    "second_argument_copy": {"va": "0x04b30050", "from": "a1", "to": "s3"},
    "configuration_names": strings,
    "conditional_field_stores": stores,
    "wrapper": "0x04b301b8",
    "wrapper_direct_call_site": "0x04b301e0",
    "wrapper_pointer_file_offsets": [hex(x) for x in positions],
    "downstream_gate": {
        "entry": "0x04b20f54",
        "field_read": "0x04b20f80: lw a5,0x334(a1)",
        "zero_field_fallthrough": "writes byte 1 to caller output at 0x04b20f8c",
        "nonzero_field_branch": "writes byte 0 to caller output at 0x04b20fe4",
        "other_prerequisites": ["byte at *(a0+0x790)+0x88", "byte at a0+0x737"],
        "installed_function_slot": "three explicit construction paths store the consumer at a0+0x158",
        "explicit_install_address_sites": consumer_install_sites,
        "first_prerequisite_false_fallback": "indirect call through a0+0x1b0",
        "second_prerequisite_writer": "0x04b72790 loads slot +0xb8 from the same object, calls it, and 0x04b7279c caches its return byte at +0x737",
    },
    "site_a_gate": {
        "entry": "0x04840310",
        "rm_disable_display_one": "bypasses the +0x1c8 HAL predicate and returns byte zero",
        "normal_dispatch": "indirect call through second argument +0x1c8",
        "missing_key_prerequisites": ["a0+0x6dd", "a0+0x737", "a0+0x6d0", "a0+0x4f80"],
    },
    "recovered_hal_predicates": {
        "+0x1b0": {"target": "0x04b19ea4", "register_selector": "0x3814", "result": "(word & 0x000c0000) != 0"},
        "+0x1c8": {"target": "0x04b1a018", "register_selector": "0x3814", "result": "(word >> 27) & 1"},
        "semantic_limit": "No exact-tag source field definition for selector 0x3814 or these bits was recovered.",
    },
    "limits": [
        "The second argument's original class/type name is not recovered.",
        "The stores prove cached configuration fields, not runtime reachability or effective target values.",
        "A value of one for RmDisableDisplay is a software policy input, not evidence that display silicon or PCB routes exist.",
    ],
}
(ROOT / "evidence/display_object_fields.json").write_text(json.dumps(result, indent=2) + "\n")
print("3 names, 3 conditional stores, site-A/site-B gates, 3 table installs, +0x737 writer, +0x1b0/+0x1c8 predicates, wrapper and table pointer PASS")

# Additional structure-copy checks: +0x334 is copied with neighboring config fields.
# These checks do not assert that every destination aliases the worker object.
for va, expected in {
    0x0460B5E8: 0x32D4A423,  # sw a3,0x328(s1)
    0x0460B5F0: 0x32D4A623,  # sw a3,0x32c(s1)
    0x0460B5F8: 0x32D4A823,  # sw a3,0x330(s1)
    0x0460B600: 0x32D4AA23,  # sw a3,0x334(s1)
    0x0460B604: 0x1B093683,  # ld a3,0x1b0(s2)
    0x0460B608: 0x32D4BC23,  # sd a3,0x338(s1)
    0x04616FA4: 0x33492703,  # lw a4,0x334(s2)
    0x04616FB4: 0x16E4A423,  # sw a4,0x168(s1)
}.items():
    assert word(va) == expected

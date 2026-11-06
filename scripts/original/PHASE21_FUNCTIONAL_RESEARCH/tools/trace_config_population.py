"""Offline, bounded evidence for configuration node construction and type-1 writes.

Run with a Python environment containing Capstone. No device access.
"""
from pathlib import Path
import hashlib
import json
import struct
import capstone

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'PHASE21_FUNCTIONAL_RESEARCH/evidence'
item = json.loads((OUT / 'firmware_capability_inventory.json').read_text())[0]
blob = Path(item['path']).read_bytes()
assert hashlib.sha256(blob).hexdigest() == item['sha256']
sections = [s for s in item['inner_elf']['sections'] if s['type'] != 8 and s['size']]


def offset(va, size=4):
    matches = [s for s in sections if s['va'] <= va and va + size <= s['va'] + s['size']]
    assert len(matches) == 1
    return matches[0]['file_offset'] + va - matches[0]['va']


def sx(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


checks = []
for pc, width, base, source, displacement in [
    (0x54f4684, 3, 10, 0, 0),
    (0x54f4714, 0, 19, 0, 0x18),
    (0x54f471c, 3, 19, 14, 0),
    (0x54f4720, 3, 20, 19, 0),
    (0x54f4878, 2, 10, 18, 0x10),
    (0x54f48d4, 0, 15, 14, 0x18),
    (0x54f48dc, 2, 15, 18, 0x10),
    (0x54f48e0, 2, 15, 14, 0x14),
    (0x54f4b18, 0, 15, 20, 0x18),
    (0x54f4b1c, 2, 15, 18, 0x10),
    (0x54f4b20, 2, 15, 14, 0x14),
    (0x54f4bf8, 0, 9, 15, 0x18),
    (0x54f4bfc, 2, 9, 19, 0x14),
    (0x54f4ed0, 0, 9, 15, 0x18),
    (0x54f4ed4, 2, 9, 18, 0x14),
    (0x54f4ef4, 0, 15, 0, 0),
    (0x54f50b8, 0, 15, 14, -0x794),
    (0x54f51a0, 0, 20, 0, 0x110),
    (0x54f6010, 0, 20, 15, 0x110),
]:
    raw = struct.unpack_from('<I', blob, offset(pc))[0]
    assert raw & 127 == 0x23
    assert (raw >> 12) & 7 == width
    assert (raw >> 15) & 31 == base
    assert (raw >> 20) & 31 == source
    assert sx(((raw >> 25) << 5) | ((raw >> 7) & 31), 12) == displacement
    checks.append({'pc': hex(pc), 'raw': hex(raw), 'width_bytes': 1 << width,
                   'base_reg': base, 'source_reg': source, 'displacement': displacement})

control_checks = []
for pc, expected in [(0x54f4c64, 0x54f465c), (0x54f4f44, 0x54f465c),
                     (0x54f50bc, 0x54f4b50), (0x54f51a8, 0x54f4a5c),
                     (0x54f5f98, 0x54f4e18)]:
    first, second = struct.unpack_from('<II', blob, offset(pc, 8))
    assert first & 127 == 0x17 and second & 0x707f == 0x67
    assert (first >> 7) & 31 == (second >> 15) & 31
    actual = (pc + sx(first & 0xfffff000, 32) + sx(second >> 20, 12)) & ~1
    assert actual == expected
    control_checks.append({'kind': 'call', 'pc': hex(pc), 'target': hex(actual)})
for pc, expected in [(0x54f506c, 0x54f5fd4), (0x54f5078, 0x54f5f60),
                     (0x54f5080, 0x54f5170), (0x54f5174, 0x54f50c4)]:
    raw = struct.unpack_from('<I', blob, offset(pc))[0]
    assert raw & 127 == 0x63
    imm = ((raw >> 31) << 12) | (((raw >> 7) & 1) << 11)
    imm |= (((raw >> 25) & 63) << 5) | (((raw >> 8) & 15) << 1)
    actual = pc + sx(imm, 13)
    assert actual == expected
    control_checks.append({'kind': 'branch', 'pc': hex(pc), 'target': hex(actual)})

calls = []
for section in sections:
    if not section['flags'] & 4:
        continue
    start = section['file_offset']
    for pos in range(start, start + section['size'] - 7, 2):
        first, second = struct.unpack_from('<II', blob, pos)
        if first & 127 != 0x17 or second & 0x707f != 0x67:
            continue
        if (first >> 7) & 31 != (second >> 15) & 31:
            continue
        pc = section['va'] + pos - start
        target = (pc + sx(first & 0xfffff000, 32) + sx(second >> 20, 12)) & ~1
        if target in (0x54f465c, 0x54f482c, 0x54f4910, 0x54f4a5c, 0x54f4b50, 0x54f4e18, 0x54f4f98):
            calls.append({'pc': hex(pc), 'target': hex(target), 'return_reg': (second >> 7) & 31})

md = capstone.Cs(capstone.CS_ARCH_RISCV, capstone.CS_MODE_RISCV64 | capstone.CS_MODE_RISCVC)
windows = []
for low, high in [(0x54f465c, 0x54f482c), (0x54f482c, 0x54f4910),
                  (0x54f4910, 0x54f4a5c), (0x54f4a5c, 0x54f4b50),
                  (0x54f4b50, 0x54f4cb8), (0x54f4e18, 0x54f4f98),
                  (0x54f4f98, 0x54f6064)]:
    pos = offset(low, high - low)
    data = blob[pos:pos + high - low]
    instructions = list(md.disasm(data, low))
    assert sum(ins.size for ins in instructions) == len(data)
    windows.append({'low': hex(low), 'high': hex(high), 'file_offset': hex(pos),
                    'sha256': hashlib.sha256(data).hexdigest(),
                    'instructions': [{'pc': hex(ins.address), 'raw': ins.bytes.hex(),
                                      'mnemonic': ins.mnemonic, 'operands': ins.op_str}
                                     for ins in instructions]})

result = {'input': {'path': item['path'], 'sha256': item['sha256']},
          'capstone_version': capstone.__version__, 'raw_store_checks': checks,
          'raw_control_checks': control_checks,
          'adjacent_call_candidates': calls, 'windows': windows,
          'limits': ['Candidate calls use halfword-aligned adjacent AUIPC/JALR only; not exhaustive xrefs or reachability.',
                     'Helper names and memory allocator/copy semantics are not established by call shape.',
                     'No effective runtime configuration values or hardware restoration proved; system-info key mapping corroborated separately.']}
(OUT / 'gsp_config_population.json').write_text(json.dumps(result, indent=2) + '\n')
print(f'{len(checks)} raw store checks PASS; {len(control_checks)} raw control checks PASS; {len(windows)} bounded windows fully decoded; {len(calls)} call candidates')

"""Offline raw checks and bounded extraction of NVKV system-info callback use."""
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


def offset(va, count=4):
    matches = [s for s in sections if s['va'] <= va and va + count <= s['va'] + s['size']]
    assert len(matches) == 1
    return matches[0]['file_offset'] + va - matches[0]['va']


def word(pc):
    return struct.unpack_from('<I', blob, offset(pc))[0]


def sx(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


checks = []
first, last = word(0x54fa058), word(0x54fa068)
assert first & 127 == 0x37 and (first >> 7) & 31 == 10
assert last & 0x707f == 0x13 and (last >> 7) & 31 == 10 and (last >> 15) & 31 == 10
target = sx(first & 0xfffff000, 32) + sx(last >> 20, 12)
assert target == 0x54f4f98
checks.append({'kind': 'callback_address', 'first_pc': '0x54fa058', 'last_pc': '0x54fa068',
               'register': 'a0', 'value': hex(target),
               'scope': 'intervening instructions write a1/a3/a2, not a0'})
for pc, expected in [(0x54fa06c, 0x4678290), (0x54fa3dc, 0x54f9fd0)]:
    first, second = word(pc), word(pc + 4)
    assert first & 127 == 0x17 and second & 0x707f == 0x67
    assert (first >> 7) & 31 == (second >> 15) & 31
    actual = (pc + sx(first & 0xfffff000, 32) + sx(second >> 20, 12)) & ~1
    assert actual == expected
    checks.append({'kind': 'direct_transfer', 'pc': hex(pc), 'target': hex(actual),
                   'link_register': (second >> 7) & 31})
for pc in [0x46783b8, 0x467845c, 0x4678500, 0x467852c]:
    value = word(pc)
    assert value & 0x707f == 0x67 and (value >> 7) & 31 == 1
    assert (value >> 15) & 31 == 21 and value >> 20 == 0
    checks.append({'kind': 'callback_invocation', 'pc': hex(pc), 'target_register': 's5'})

expected_table = [0x467850c, 0x467848c, 0x46783f8, 0x46783d0, 0x467837c, 0x4678468]
table = list(struct.unpack_from('<6I', blob, offset(0x4091524, 24)))
assert table == expected_table
checks.append({'kind': 'opcode_dispatch_table', 'va': '0x4091524', 'entries': [hex(v) for v in table]})
md = capstone.Cs(capstone.CS_ARCH_RISCV, capstone.CS_MODE_RISCV64 | capstone.CS_MODE_RISCVC)
windows = []
for low, high in [(0x54f9fd0, 0x54fa0e4), (0x4678290, 0x4678638), (0x54fa2e4, 0x54fa3e4)]:
    pos = offset(low, high - low)
    data = blob[pos:pos + high - low]
    instructions = list(md.disasm(data, low))
    assert sum(i.size for i in instructions) == len(data)
    windows.append({'low': hex(low), 'high': hex(high), 'file_offset': hex(pos),
                    'sha256': hashlib.sha256(data).hexdigest(),
                    'instructions': [{'pc': hex(i.address), 'raw': i.bytes.hex(),
                                      'mnemonic': i.mnemonic, 'operands': i.op_str} for i in instructions]})

result = {'input': {'path': item['path'], 'sha256': item['sha256']},
          'capstone_version': capstone.__version__, 'raw_checks': checks, 'windows': windows,
          'limits': ['Bounded static instructions and data, not runtime reachability or complete transport/host producer.',
                     'NVKV identification corroborated by local snapshotted header; exact-tag header retrieval was unavailable.']}
(OUT / 'gsp_nvkv_callback.json').write_text(json.dumps(result, indent=2) + '\n')
print(f'{len(checks)} raw checks PASS; {len(windows)} bounded windows fully decoded')

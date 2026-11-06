import importlib.util
from pathlib import Path
import random
import struct
import unittest

import capstone

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audit', HERE / 'riscv_audit.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class DecoderTests(unittest.TestCase):
    def setUp(self):
        self.md = capstone.Cs(capstone.CS_ARCH_RISCV, capstone.CS_MODE_RISCV64 | capstone.CS_MODE_RISCVC)

    def test_known_backward_jal_and_true_va(self):
        self.assertEqual(a.jal(0xc8dff06f, 0x4f57930), (0x4f575bc, 0))

    def test_jal_extremes_and_random_against_capstone(self):
        rng = random.Random(16)
        offsets = [-1048576, -1048574, -4096, -2048, -2, 0, 2, 2048, 4096, 1048574]
        offsets += [rng.randrange(-524288, 524288) * 2 for _ in range(1000)]
        for imm in offsets:
            u = imm & 0x1fffff
            w = (((u >> 20) & 1) << 31) | (((u >> 1) & 1023) << 21)
            w |= (((u >> 11) & 1) << 20) | (((u >> 12) & 255) << 12) | 0xef
            ins = next(self.md.disasm(struct.pack('<I', w), 0x4000000))
            oracle = int(ins.op_str.split(',')[-1].strip(), 0)
            self.assertEqual(a.jal(w, 0x4000000), (0x4000000 + oracle, 1))
            self.assertEqual(oracle, imm)

    def test_non_jal_rejected(self):
        with self.assertRaises(ValueError):
            a.jal(0x13, 0)

    def test_auipc_pair_uses_own_pc_and_signed_halves(self):
        w1 = 0xfffff097  # auipc ra,-4096
        w2 = (0xffd << 20) | (1 << 15) | (1 << 7) | 0x67
        self.assertEqual(a.auipc_jalr(w1, w2, 0x4000000), 0x3ffeffc)
        self.assertEqual(a.auipc_jalr(0x0031f097, 0x9fc080e7, 0x4f57600), 0x5275ffc)

    def test_auipc_zero_and_register_mismatch(self):
        self.assertIsNone(a.auipc_jalr(0x17, 0x8067, 0x1000))
        self.assertIsNone(a.auipc_jalr(0x97, 0x100e7, 0x1000))

    def test_compressed_control_exhaustive_against_capstone(self):
        tested = 0
        for w in range(65536):
            c = a.control(w, 0x4000000, 2)
            if not c or c['kind'] not in ('branch', 'jump'):
                continue
            ins = next(self.md.disasm(w.to_bytes(2, 'little'), 0x4000000))
            self.assertIn(ins.mnemonic, ('c.j', 'c.beqz', 'c.bnez'))
            oracle = int(ins.op_str.split(',')[-1].strip(), 0)
            self.assertEqual(c['target'], 0x4000000 + oracle)
            tested += 1
        self.assertEqual(tested, 6144)

    def test_rv64_c_addiw_is_not_rv32_c_jal(self):
        self.assertIsNone(a.control(0x2085, 0x1000, 2))

    def test_compressed_indirect_and_return(self):
        self.assertEqual(a.control(0x8082, 0, 2)['kind'], 'return')
        self.assertEqual(a.control(0x9782, 0, 2)['kind'], 'indirect_call')
        self.assertEqual(a.control(0x8782, 0, 2)['kind'], 'indirect_jump')
        self.assertEqual(a.control(0x9002, 0, 2)['kind'], 'trap')

    def test_lengths(self):
        for h, expected in [(0, 2), (0x13, 4), (0x1f, 6), (0x3f, 8), (0x7f, 10), (0x607f, 22)]:
            self.assertEqual(a.instruction_length(h), expected)
        with self.assertRaises(ValueError):
            a.instruction_length(0x707f)

    def test_instruction_walk_handles_halfword_aligned_word(self):
        elf = object.__new__(a.Elf)
        elf.data = bytes.fromhex('01006ff0dfc8')
        rows = list(elf.instructions(dict(offset=0, va=0x1000, size=6)))
        self.assertEqual([(x[1], x[2]) for x in rows], [(0x1000, 2), (0x1002, 4)])

    def test_truncated_instruction_rejected(self):
        elf = object.__new__(a.Elf)
        elf.data = b'\x13\x00'
        with self.assertRaises(ValueError):
            list(elf.instructions(dict(offset=0, va=0, size=2)))


class FirmwareEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = (HERE.parent / 'outputs/gsp_tu10x.bin').read_bytes()
        cls.elf = a.Elf(cls.data)

    def test_inner_elf_header(self):
        self.assertEqual(self.elf.entry, 0x4009000)
        self.assertEqual(len(self.elf.sections), 37)

    def test_true_section_and_segment_mapping_agree(self):
        for va in (0x41a70b0, 0x4f575bc, 0x4f5733c):
            off = self.elf.at(va)
            segments = [p for p in self.elf.segments if p['type'] == 1 and p['va'] <= va < p['va'] + p['filesz']]
            self.assertTrue(segments)
            self.assertTrue(all(off == p['offset'] + va - p['va'] for p in segments))

    def test_table_and_loop_offsets(self):
        self.assertEqual(self.elf.at(0x41a70b0), 0x1a70f0)
        self.assertEqual(self.elf.at(0x4f575bc), 0xf575fc)
        self.assertEqual(self.data[self.elf.at(0x4f575bc):][:4], bytes.fromhex('b7741a04'))

    def test_old_mapping_is_not_validated_by_signature(self):
        self.assertNotEqual(self.data[self.elf.at(0x4f575fc):][:4], bytes.fromhex('b7741a04'))

    def test_no_file_bytes_for_nobits_or_unmapped_va(self):
        for va in (0x5646000, 0x55d1000, 0, 0xdeadbeef):
            with self.assertRaises(ValueError):
                self.elf.at(va)

    def test_table_names_resolve_without_suffix_guessing(self):
        names = []
        for i in range(186):
            off = self.elf.at(0x41a70b0 + i * 32, 32)
            ptr = struct.unpack_from('<Q', self.data, off + 16)[0]
            names.append(self.elf.cstring(ptr))
        self.assertEqual(len(set(names)), 186)
        self.assertEqual(names[0], 'NOT_SET')
        self.assertEqual(names[-1], 'MODS_RULES_SRAM')

    def test_capstone_known_branch_targets(self):
        self.assertEqual(a.control(0x0260063, 0x1000, 4)['kind'], 'branch')
        self.assertEqual(a.control(0x40091263, 0x4f575b8, 4)['target'], 0x4f579bc)


if __name__ == '__main__':
    unittest.main()

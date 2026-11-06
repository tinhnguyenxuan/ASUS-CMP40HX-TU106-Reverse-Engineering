#!/usr/bin/env python3
"""Tim caller cua dispatcher GSP-RM @0x04F575FC trong gsp_tu10x.bin (offline, read-only)."""
import struct, os
ROOT='/home/REDACTED_USER/.hermes/cache/scratch/cmp40hx_research'
gsp=open(ROOT+'/outputs/gsp_tu10x.bin','rb').read()
print(f'gsp_tu10x.bin size: {len(gsp):,} B')

# vaddr base = 0x4000000, dispatcher vaddr = 0x04F575FC
# offset trong file = 0x04F575FC - 0x4000000 = 0xF575FC (neu nam trong phan text duoc map)
DISP_VADDR = 0x04F575FC
DISP_OFFSET = DISP_VADDR - 0x4000000
print(f'Dispatcher vaddr: 0x{DISP_VADDR:08X}, file offset: 0x{DISP_OFFSET:08X} ({DISP_OFFSET:,})')

# Kiem tra byte tai offset do
if 0 <= DISP_OFFSET < len(gsp):
    b = gsp[DISP_OFFSET:DISP_OFFSET+4]
    print(f'Byte at dispatcher offset: {b.hex()}')
    w = struct.unpack('<I', b)[0]
    print(f'Word: 0x{w:08X} (opcode bits[6:0] = {w & 0x7F:02X})')

# Quet tim cac instruction tham chieu den dispatcher
# Pattern 1: lui x, 0x04F57 (imm20 = 20 bit cao cua 0x04F575FC)
# RISC-V LUI: opcode 0x37, imm20 = bits[31:12]
LUI_IMM = (DISP_VADDR >> 12) & 0xFFFFF
print(f'\\nLUI imm20 for dispatcher high 20 bits: 0x{LUI_IMM:05X}')

# Pattern 2: auipc + jalr: auipc x, imm20 where target = PC + (imm20 << 12)
# Can't easily compute without knowing PC of each instruction, so scan for auipc then check following jalr

# Pattern 3: lui + addi + jalr (like dispatcher itself)

# Quet toan bo file (step 4 byte, co the bo qua RVC 2 byte, nhung caller co the la RVC)
# De an toan, quet step 2 byte va disasm moi instruction

try:
    from capstone import Cs, CS_ARCH_RISCV, CS_MODE_RISCV64
    md = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64)
    md.detail = True
except ImportError:
    print('capstone not available via import, trying /usr/bin/python3...')
    import subprocess, sys
    # will fall through

print('\\n=== Scanning for caller candidates ===')
callers = []
# Quet step 4 (instruction 32-bit) trong khoang vaddr text
# Section .tu10x_text_instance vaddr 0x04588000, size 17,010,688 B
# File offset cho section nay can biet tu section header. De don gian, quet toan bo file.
# Nhung chi quan ly vaddr >= 0x4000000

# Chuan bi mang vaddr->file_offset mapping (approximate: vaddr - 0x4000000)
# Quet toan bo file step 4
for fo in range(0, len(gsp) - 3, 4):
    w = struct.unpack('<I', gsp[fo:fo+4])[0]
    if (w & 0x7F) == 0x37:  # LUI
        rd = (w >> 7) & 0x1F
        imm20 = (w >> 12) & 0xFFFFF
        # sign extend
        if imm20 & 0x80000:
            imm20 |= 0xFFF00000
        val = imm20 << 12
        if val == (DISP_VADDR & 0xFFFFF000):
            vaddr_approx = 0x4000000 + fo
            callers.append((fo, vaddr_approx, 'LUI', f'rd=x{rd}, imm20=0x{imm20:05X}'))

print(f'Found {len(callers)} LUI matching dispatcher high 20 bits')
for fo, vaddr, typ, detail in callers[:20]:
    print(f'  file_off=0x{fo:06X} (~vaddr 0x{vaddr:08X}): {typ} {detail}')

if len(callers) > 20:
    print(f'  ... and {len(callers)-20} more')

# Quet JALR (opcode 0x67, bits[14:12] = 0 for jalr)
print('\\n=== Scanning for JALR instructions ===')
jalrs = []
for fo in range(0, len(gsp) - 3, 4):
    w = struct.unpack('<I', gsp[fo:fo+4])[0]
    if (w & 0x7F) == 0x67 and ((w >> 12) & 0x7) == 0:  # JALR
        rd = (w >> 7) & 0x1F
        rs1 = (w >> 15) & 0x1F
        imm12 = (w >> 20) & 0xFFF
        if imm12 & 0x800:
            imm12 |= 0xF000
        jalrs.append((fo, 0x4000000 + fo, rd, rs1, imm12))

print(f'Found {len(jalrs)} JALR instructions')
print('First 30 JALR:')
for fo, vaddr, rd, rs1, imm in jalrs[:30]:
    print(f'  file_off=0x{fo:06X} (~vaddr 0x{vaddr:08X}): jalr x{rd}, {imm}(x{rs1})')

# Luu ket qua
import json
os.makedirs(ROOT+'/PHASE15', exist_ok=True)
json.dump({
 'dispatcher_vaddr': DISP_VADDR,
 'dispatcher_file_offset': DISP_OFFSET,
 'lui_matches': [{'file_off': fo, 'vaddr': vaddr, 'detail': d} for fo, vaddr, t, d in callers],
 'jalr_count': len(jalrs),
 'jalr_first30': [{'file_off': fo, 'vaddr': vaddr, 'rd': rd, 'rs1': rs1, 'imm12': imm} for fo, vaddr, rd, rs1, imm in jalrs[:30]],
}, open(ROOT+'/PHASE15/gsp_dispatcher_caller.json','w'), indent=1)
print('\\nSaved PHASE15/gsp_dispatcher_caller.json')

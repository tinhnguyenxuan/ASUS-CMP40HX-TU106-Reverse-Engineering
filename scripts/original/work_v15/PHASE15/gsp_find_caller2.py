#!/usr/bin/env python3
"""Tim JAL instruction nhay thang den dispatcher @0x04F575FC (RISC-V JAL opcode 0x6F)."""
import struct, os, json
ROOT='/home/REDACTED_USER/.hermes/cache/scratch/cmp40hx_research'
gsp=open(ROOT+'/outputs/gsp_tu10x.bin','rb').read()
DISP_VADDR = 0x04F575FC

def sign_extend_imm20_jal(imm):
    # JAL imm20: bit[31] = sign, bit[11], bit[19:12], bit[20]
    sign = (imm >> 31) & 1
    val = ((imm & 0xFF000) >> 12) | ((imm & 0x000FF000) >> 1) | ((imm & 0x00100000) >> 11) | (sign << 19)
    if val & 0x80000:
        val |= 0xFFF00000
    return val << 1

jal_to_dispatcher = []
total_jal = 0
for fo in range(0, len(gsp) - 3, 4):
    w = struct.unpack('<I', gsp[fo:fo+4])[0]
    if (w & 0x7F) == 0x6F:  # JAL
        total_jal += 1
        rd = (w >> 7) & 0x1F
        imm = w >> 12
        target = (0x4000000 + fo) + sign_extend_imm20_jal(imm)
        if target == DISP_VADDR:
            jal_to_dispatcher.append({'file_off': fo, 'vaddr': 0x4000000+fo, 'rd': rd, 'imm': imm})

print(f'Total JAL instructions: {total_jal:,}')
print(f'JAL directly to dispatcher 0x{DISP_VADDR:08X}: {len(jal_to_dispatcher)}')
for j in jal_to_dispatcher:
    print(f'  file_off=0x{j["file_off"]:06X} (~vaddr 0x{j["vaddr"]:08X}): jal x{j["rd"]}, imm=0x{j["imm"]:05X}')

# Tim AUIPC + JALR pairs: auipc x, imm20 (target = PC + imm<<12), followed by jalr using same reg
# Scan for auipc (opcode 0x17)
auipc_jalr = []
for fo in range(0, len(gsp) - 7, 4):
    w1 = struct.unpack('<I', gsp[fo:fo+4])[0]
    w2 = struct.unpack('<I', gsp[fo+4:fo+8])[0]
    if (w1 & 0x7F) == 0x17:  # AUIPC
        rd1 = (w1 >> 7) & 0x1F
        imm20 = (w1 >> 12) & 0xFFFFF
        if imm20 & 0x80000:
            imm20 |= 0xFFF00000
        # Check if w2 is JALR using rd1
        if (w2 & 0x7F) == 0x67 and ((w2 >> 12) & 0x7) == 0:
            rs1 = (w2 >> 15) & 0x1F
            imm12 = (w2 >> 20) & 0xFFF
            if imm12 & 0x800:
                imm12 |= 0xF000
            if rs1 == rd1:
                auipc_jalr.append({'auipc_off': fo, 'jalr_off': fo+4, 'rd': rd1, 'auipc_imm': imm20, 'jalr_imm': imm12})

print(f'\nAUIPC+JALR pairs (same reg): {len(auipc_jalr):,}')
# Filter pairs where target could be dispatcher
# target = auipc_PC + (imm20<<12) + jalr_imm12
candidates = []
for p in auipc_jalr:
    auipc_vaddr = 0x4000000 + p['auipc_off']
    # next PC after auipc = auipc_vaddr + 4
    base = auipc_vaddr + 4 + ((p['auipc_imm'] & 0xFFFFF) << 12)
    if p['auipc_imm'] & 0x80000:
        base = auipc_vaddr + 4 + ((p['auipc_imm'] | 0xFFF00000) << 12)
    target = base + p['jalr_imm']
    if target == DISP_VADDR:
        candidates.append(p)

print(f'AUIPC+JALR pairs targeting dispatcher: {len(candidates)}')
for c in candidates:
    print(f'  auipc_off=0x{c["auipc_off"]:06X} jalr_off=0x{c["jalr_off"]:06X} rd=x{c["rd"]} auipc_imm=0x{p["auipc_imm"]:05X} jalr_imm=0x{p["jalr_imm"]:04X}')

os.makedirs(ROOT+'/PHASE15', exist_ok=True)
json.dump({
 'dispatcher_vaddr': DISP_VADDR,
 'total_jal': total_jal,
 'jal_to_dispatcher': jal_to_dispatcher,
 'auipc_jalr_pairs': len(auipc_jalr),
 'auipc_jalr_to_dispatcher': candidates,
}, open(ROOT+'/PHASE15/gsp_dispatcher_caller.json','w'), indent=1)
print('\\nSaved PHASE15/gsp_dispatcher_caller.json')

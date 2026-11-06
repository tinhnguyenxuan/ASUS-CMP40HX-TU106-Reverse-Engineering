# PHASE16 — GSP callback verified (đường đi đã thấy, không mở rộng CFG)

source: /home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin
sha256: 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b
bin_size: 22901632
capstone: true
callback_block: VA 0x04f575bc..0x04f57658 (83195324..83195480), file 0xf575fc..0xf5768c, backing section[27].section_task_rm_elf_text_instance, 39 insns

Target block along fall-through path (DECODED):
  0x04f575d4 file=0xf57614 raw=83b70903 ld a5, 0x30(s3)      callback ptr = *(s3+0x30)
  0x04f575d8 file=0xf57618 raw=035684f7 lhu a2, -0x88(s0)    a2 = stack u16
  0x04f575dc file=0xf5761c raw=13850900 mv a0, s3            a0 = context ptr
  0x04f575e0 file=0xf57620 raw=e7800700 jalr ra, a5, 0       <- CALL (indirect)
Post-call block:
  0x04f57644 file=0xf57684 raw=9700fbff auipc ra, 0xfffb0  -> val 0x4f07644 (0x4f075ec + 0x58)
  0x04f57648 file=0xf57688 raw=e78080fa jalr ra, ra, -0x58 -> target 0x04f075ec = entry_helper (0x04f075ec, file=0xf0762c, raw=130101fc)
  0x04f5764c file=0xf5768c raw=93050500 mv a1, a0            <- after jalr return only
  0x04f57650 file=0xf57690 raw=e31205f8 bnez a0, -0x7c -> 0x04f575d4

Register facts at the CALL (0x04f575e0), window 0x04f575bc..0x04f575e0 (straight-line last-write, chua xac minh CFG toan cuc):
  a0: LAST-WRITE `mv a0, s3` @ 0x04f575dc (raw 13850900). DEF: a0 = s3 (con tro context). PATH: fall-through tu block 0x04f575d4. CALL-CLOBBER: a0 caller-saved, gia tri la tham so luc goi, bi ghi de sau jalr tra ve.
  a1: KHONG co lenh ghi a1 trong cua so -> chua co LAST-WRITE o duong di nay. a1 = gia tri nhap cua ham luu tai s4 (mv s4, a1 @ 0x04f57378, van ban truoc). TREN DUONG DI VONG LAP (xac minh): a1 duoc dat bang `mv a1, a0` @ 0x04f5764c SAU KHI helper 0x04f075ec tra ve, sau it nhat `bnez a0` @ 0x04f57650 quay ve block 0x04f575d4. SU KHAC: `mv a1, s4` @ 0x04f57621 la tham so a1 CUA HELPER, khong phai cua callback. CLOSURE: "a1 = tra ve helper tai diem goi callback" CHUA DUOC BY CHUNG tai dia diem nay; "a1 = s4 tai diem goi callback" cua ban cu CHUA DUOC XAC THUC trong cua so nay.
  a2: LAST-WRITE `lhu a2, -0x88(s0)` @ 0x04f575d8 (raw 035684f7). DEF: a2 = u16 f00 cua entry luu tai stack s0-0x88. PATH: fall-through tu block dau. CALL-CLOBBER: a2 caller-saved. Helper 0x04f075ec nhan con tro struct entry va co the boi bien nho -> khong buoc a2 == entry.f00 goc phai tien boi helper store analysis.

Call edge: branch bnez a0 @ 0x04f57650 targets 0x04f575d4 (loop back). No other CALL between mv a1,a0 (0x04f5764c) and the callback.
predecessors_of_callback: [] (empty); fallthrough into callback: 1 (0x04f575dc mv a0,s3). Full CFG / all predecessors NOT verified.

Conclusion (DECODED, observed fall-through path only): at 0x04f575e0, a0=s3, a2=stack u16, indirect call jalr ra,a5 via *(s3+0x30). callback TARGET: UNKNOWN. a1 at call: UNKNOWN (not the helper return; a1=s4 is post-call). Do not treat a1=s4 as fact at the call.

entry0: VA 0x041a70b0 / file 0x1a70f0 (section .section_task_rm_elf_rodata_instance), raw32=00000000ff000000000100000000000000601a040000000001ff000000000000.
  f00=0x0000 (u16@0), f04=0x000000FF (u32@4), f08=0x00 (u8@8), f10=0x00000000041A6000 (u64@0x10), f18=0xFF01 (u16@0x18; byte0=0x01, byte1=0xFF, chi cau truc bit, chua gan semantic nhom/subtype).
  f10 = VA 0x041A6000 -> mapping ELF -> file 0x1a6040 -> bounded ASCII "NOT_SET" (xac thuc tu byte, khong su doan).
  SUA so voi ban cu: ban GSP_AUDIT.md §5 viet f10 = 0x41A600 (THIEU SO 0 -> SAI) va raw byte +0x10/+0x18 bi dich/dao LE (`601a0400`, `ff000000`) -> SAI. Gia tri thuc: f10 = 0x041A6000, raw +0x10 = `00 60 1a 04`, raw +0x18 = `01 ff`.
  WPR: raw LO/HI o GSP_AUDIT §6 (0x01F7E000 / 0x01FFEE00) da doi chieu SECURITY/p8_wpr.json (NV_PFB_PRI_MMU_WPR2_ADDR_LO/HI @ 0x1fa824/0x1fa828) -> KHOP. Chua tim saiot "thieu so 0" cu the o cac dong do; neu sai o khac can chi dia chi, khong bi so moi.

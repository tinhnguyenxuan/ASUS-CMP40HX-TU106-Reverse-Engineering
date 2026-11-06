# PHASE16 — GSP/RM audit (phần GSP, làm trước theo lệnh phiên)

## 1. Phạm vi và nguồn
- Chỉ phân tích offline, read-only trên file trong `work_v15/`. Không đọc/viết phần cứng, không flash/MMIO/fuse/PCI, không reload driver, không reboot.
- Nguồn chính: `outputs/gsp_tu10x.bin` (ELF nội bộ, offset 0x40), sha256 `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`, 22.9 MB.
- Công cụ: `PHASE16/riscv_audit.py` (pure-Python decoder, import không cần capstone — `import capstone` chỉ nằm trong hàm `audit()`), kết quả chéo bằng script độc lập `/home/REDACTED_USER/.hermes/cache/scratch/phase16_repro.py` (không dùng capstone).
- Mức nhãn: `DECODED` (đã giải mã từ byte/đầu ra công cụ), `INFERRED` (suy luận hợp lý, chưa chứng minh hoàn toàn), `UNKNOWN` (chưa có bằng chứng).

## 2. Mapping ELF virtual address ↔ file offset (DECODED)
ELF nội bộ bắt đầu tại file offset `0x40`, 37 section. Section offsets đã bị cộng thêm 64 (header ELF) nên hiệu lực thực:

`VA = file_offset + 0x3FFFFC0`  (KHÔNG phải +0x04000000)

Chứng nhận thô tại 6 mốc (raw bytes + địa chỉ):

| VA | File offset | Raw bytes (LE) | Delta VA−file | Giải mã |
|---|---|---|---|---|
| 0x04F575BC | 0xF575FC | B7 74 1A 04 | 0x3FFFFC0 | LUI s1, 0x41A7 (vòng lặp dispatcher) |
| 0x04F5733C | 0xF5737C | F2 01 01 13 | 0x3FFFFC0 | ADDI sp, sp, -0xE0 (prologue hàm chứa dispatcher) |
| 0x04F57930 | 0xF57970 | 6F F0 DF C8 | 0x3FFFFC0 | JAL x0, imm -0x374 → 0x4F575BC |
| 0x04F575E0 | 0xF57620 | E7 80 07 00 | 0x3FFFFC0 | JALR ra, a5, 0 (gọi callback qua con trỏ) |
| 0x041A70B0 | 0x1A70F0 | 00 00 00 00 … | 0x3FFFFC0 | Đầu bảng descriptor (xem §5) |
| 0x04F06C18 | 0xF06C58 | 97 00 05 00 | 0x3FFFFC0 | AUIPC ra, imm20=5 (caller) |

Ánh xạ cũ `VA = file_offset + 0x04000000` là SAI (lệch 64 byte, đặt nhầm mọi VA). Hàm `Elf.at()` trong `riscv_audit.py` đã hiện thực đúng delta này (`offset` đã bao gồm +64 header).

## 3. Decoder RISC-V (DECODED)
Hàm `jal`, `auipc_jalr`, `control` trong `riscv_audit.py` kiểm chứng độc lập trên raw bytes (script scratch, không dùng capstone):

- `jal(0xC8DFF06F, pc=0x4F57930) = (0x4F575BC, 0)`: imm sext21 = −0x374, rd = x0 → **lùi về 0x4F575BC, không phải call**.
- `auipc_jalr(0x00050097, 0x724080E7, pc=0x4F06C18) = 0x4F5733C`: AUIPC đưa ra = 0x4F06C18 + 0x50000 = 0x4F56C18, JALR cộng imm 0x724 → **0x4F5733C**.

## 4. Caller / callback GSP (DECODED và INFERRED)
**Caller (DECODED):** tại VA `0x04F06C18` (file `0xF06C58`, `97 00 05 00`) + `0x04F06C1C` (file `0xF06C5C`, `E7 80 40 72`) là cặp AUIPC/JALR gọi vào **0x04F5733C** (đầu hàm chứa vòng lặp dispatcher, prologue `ADDI sp,sp,-0xE0`). Khác với yêu cầu cũ "gọi trực tiếp 0x4F575FC": caller gọi hàm chứa dispatcher, vòng lặp nằm bên trong hàm đó.

**Vòng lặp (DECODED):** `JAL x0` `0xC8DFF06F` tại VA `0x04F57930` (file `0xF57970`) nhảy về `0x04F575BC` (lùi 0x374 byte, rd=x0) → đây là canh-back-edge của vòng lặp, KHÔNG phải lệnh gọi hàm.

**Callback tại VA `0x04F575E0` (file `0xF57620`):**
```
04f575d4  83b70903   ld   a5, 0x30(s3)     <- con trỏ callback từ context+0x30
04f575d8  f7845603   lhu  a2, -0x88(s0)    <- a2 = u16 lấy từ stack (field f00)
04f575dc  00098513   mv   a0, s3           <- a0 = con trỏ context
04f575e0  e7800700   jalr ra, a5, 0        <- gọi INDIRECT qua con trỏ trên
```
- `ld a5, 0x30(s3)` ✓ lấy con trỏ từ `s3+0x30` (không phải từ entry).
- `lhu a2, -0x88(s0)` ✓ a2 đọc u16 từ stack = field `f00` (entry+0x00, đã được helper trước đó lưu tại stack−0x88).
- `mv a0, s3` ✓ a0 = context.
- `jalr ra, a5` ✓ gọi giữa qua con trỏ callback, ra lưu về về về ra.
- `a1` tại điểm gọi callback (`jalr ra,a5` @ `0x04F575E0`): **không có last-write trong cửa sổ disassembled (`0x04F575BC..0x04F575E0`) → UNKNOWN**. `mv a1,a0` @ `0x04F5764C` nằm SAU khi `jalr` trở về, nên `a1=s4` không phải đối số tại điểm gọi. Giá trị trả của helper `0x04F075EC` (entry @ file `0xF0762C`) không chảy vào `a1` tại địa điểm này → khẳng định "a1 là return của helper 0x04F075EC" **bị bác bỏ cho đường đi này**; cần ngữ cảnh caller cha (UNKNOWN).
- Cảnh báo f10 qua a2: **bị bác bỏ** — a2 mang f00 (u16 stack); f10 (u64@entry+0x10) lưu tại stack−0x78, không truyền qua a2. entry[0] f10 bounded ASCII = `NOT_SET` (không phải thiếu chữ 0); f18 = 0xFF01 (byte0=1, byte1=255), nghĩa nhóm/subtype: UNKNOWN.

**Hàm chứa dispatcher (`0x04F5733C..0x04F57B20`, candidate boundary):** prologue lưu s0..s8, ra, s2, s3; s3=context, s1=con trỏ entry, s8=end=base+0x1740. Mỗi vòng: đọc 5 field entry vào struct stack (−0xE0..−0x68), gọi callback `*(s3+0x30)` với `(a0=ctx, a1=s4, a2=f00)`, nếu trả != 0 thì dừng, s1 += 32, so sánh end.

**INFERRED:** `0x04F5733C` là hàm điều phối bảng descriptor (contain vòng lặp). **UNKNOWN:** đích thực của hàm callback (con trỏ tại `*(s3+0x30)` chưa được giải quyết), caller cha của `0x04F06C18`, ngữ nghĩa toàn bộ field entry ngoài `f18` (mã nhóm/subtype).

## 5. Bảng descriptor entry[0] (DECODED)
Tại VA `0x041A70B0` / file `0x1A70F0`, 32 byte thô:

`00000000 ff000000 00 00000000 601a0400 00000000 ff000000 00000000`

| Trường | Offset | Kích thước | Giá trị entry[0] | Nhận xét |
|---|---|---|---|---|
| f00 | +0x00 | u16 | 0x0000 | mã nhóm/subtype |
| f04 | +0x04 | u32 | 0x000000FF | |
| f08 | +0x08 | u8 | 0x00 | |
| +0x0C | — | padding | 00 00 00 | không đọc |
| f10 | +0x10 | u64 | 0x000000000041A6000 | con trỏ/tham số callback (không phải name_ptr tự do) |
| f18 | +0x18 | u16 | 0xFF01 | nhóm 0xFF, subtype 0x01 |

Layout 5 trường `u16,u32,u8,pad,u64,u16` khớp disassembly (ld/lw/lbu/ld/lhu tại +0x00/+0x04/+0x08/+0x10/+0x18), bác bỏ layout cũ của P3 (f00 là name_ptr, f08 u32, f10 u32 id...). 186 entry, stride 32, span 0x1740 → end `0x41A87F0` (khớp `lui s8,1; addi s8,s8,0x740` → 0x1000+0x740 = 0x1740). 186/186 tên ASCII phân giải được (theo `descriptor_table.json` của script).

## 6. Kết quả kế toán bổ sung (đã chạy lại data_audit.py, khớp litteralmente)
- `verify_all.py` (legacy): **161 PASS, 0 FAIL** (không phải 162) — các PASS này chỉ chứng minh sự hiện hiện/tính nhất quán của dữ liệu lưu trữ, KHÔNG chứng minh ngữ nghĩa GPU.
- WPR: raw LO `0x01F7E000` (33021952), HI `0x01FFEE00` (33549824); theo Turing `dev_fb.h` VAL[31:4]<<12 → LO `0x1F7E0000` (8453619712), HI `0x1FFEE0000` (8588754944), chênh lệch decoded bound **128.875 MiB** (135135232 bytes). Số lấy từ `PHASE16/mmio_audit.json` (VAL28bit), không tính lại từ `phase16_repro.py` (mask20bit của script đó sai). Không được trừ raw để nói 0.50 MiB; vùng vật lý và sự chồng lên NVML Reserved chưa được thiết lập.
- MMIO corrected_stats: POISON 3278 + UNINIT_FF 72 + DATA 141 + ZERO 355 + MIXED 201 = **4047** trang được phân loại, **49 trang chưa phân loại** (trong 4096 trang 16 MiB).
- Firmware container `ucodes_tu10x.bin`: magic `NVUCODES`, 8.8 MB; quét cấu trúc tìm **38 ứng viên payload** (không chặt thành 11 blob cứng trước khi có spec định dạng); blob6 vs blob8: 125.696 byte so sánh, **24 byte khác**, trong đó 2 byte ngoài cửa sổ timestamp ở relative **0x6F3E** và **0xB659** (cả hai: b6=0x21, b8=0x1F).
- Fuse: 3072 word (0..12284, liên tục), 352 data / 518 zero / 2202 poison, 152 word =1 (INFERRED cờ enable, không phải OTP cell vật lý), PDI từ words `0x0000000000000000` khớp nvidia-smi; ý nghĩa OTP cell vật lý = UNKNOWN.

## 7. Lời khuyên bước tiếp theo (theo thứ tự)
1. Fuse/OTP: ngữ nghĩa 352 word data, cờ 152 ones, biệt OTP vật lý vs shadow/register trạng thái.
2. Firmware: xác thực định dạng container trước khi khẳng định "11 blob"; so sánh blob6/8.
3. VBIOS: kiểm toán parser 38 record BIT, key block, shadow diff (14 byte).
4. MMIO: chi tiết bitfield register, mã poison, vị trí 49 trang chưa phân loại.
**KHÔNG kết luận toàn GPU đã reverse engineering xong** — vẫn còn nhiều unknown (xem `UNKNOWN_DATABASE.json`: 45 mục, 35 open, 10 resolved).

## SỬA LỖI / CẬP NHẬT (luot kiem tra callback, lay tu gsp_callback_verify.py + gsp_callback_verified.json; giu nguyen van ban cu o tren lam lich su)

### Sai 1: a1 tai diem goi callback (GSP_AUDIT §4)
- Van ban cu: "a1 tai diem goi = s4 ... Khong thay gia tri tra cua helper 0x04F075EC chao vao a1 tai dia diem nay ... can nghia context caller cha".
- Sua (tu byte thuc): trong cua so `0x04F575BC..0x04F575E0` KHONG co lenh ghi a1. Block `0x04F575D4` (va nen callback @ `0x04F575E0`) trong cua so chi duoc den qua `bnez a0, -0x7c` tai `0x04F57650` (target REDACTED_USER duoc = `0x04F575D4`, KHONG sai dia chi). Truoc do co `mv a1, a0` tai `0x04F5764c`, va `a0` do la ket qua cua helper `0x04F075EC` duoc goi bang cặp `auipc ra,0xfffb0` @ `0x04F57644` + `jalr ra,ra,-0x58` @ `0x04F57648` -> target REDACTED_USER DUOC TU RAW = `0x04F075EC` (file `0x0F0762C`), khong phai con so `0x4F56B500` cu. Ket luan chinh xac: co trinh tu `helper(0x04F075EC) -> mv a1,a0 -> bnez a0 quay ve block callback 0x04F575D4`; tai diem goi callback tren duong di vong lap, `a1 = ket qua helper`, KHONG phai `s4`. `mv s4, a1` @ `0x04F57378` (van ban truoc) truyen vao tham so **a1 cua helper** @ `0x04F57621` (`mv a1, s4`), khong phai thuc the cua callback lan dau trong cua so. `a1 = s4` tai diem goi callback CHUA DUOC XAC THUC trong cua so nay; co the co predecessor ngoai cua so chua quet -> UNKNOWN.
- a0 tai goi: LAST-WRITE `mv a0, s3` @ `0x04F575DC` (a0 = context). a2 tai goi: LAST-WRITE `lhu a2, -0x88(s0)` @ `0x04F575D8` (a2 = u16 f00 tren stack). Cung cap: DEF/LAST-WRITE/PATH/CALL-CLOBBER (a0-a7 caller-saved; gia tri la tham so luc goi, CALL-CLOBBER sau khi jalr tra ve).
- Dich callback qua `jalr ra, a5` @ `0x04F575E0`, `a5 = *(s3+0x30)`: **UNKNOWN**, khong ep ket luan. predecessors vao callback trong cua so: [] (chi co fall-through tu `0x04F575DC`).

### Sai 2: entry[0] f10 va raw byte (GSP_AUDIT §5)
- Van ban cu: f10 = `0x000000000041A600`; raw `... 601a0400 00000000 ff000000 ...`; f18 = "nhom 0xFF, subtype 0x01".
- Sua (tu byte thuc tai file `0x1A70F0`, VA `0x041A70B0`, section `.section_task_rm_elf_rodata_instance`): raw32 = `00000000 ff000000 00010000 00000000 00601a04 00000000 01ff0000 00000000`. f00=0x0000, f04=0x000000FF, f08=0x00, **f10 = 0x00000000041A6000** (ban cu `0x41A600` THIEU SO 0 -> SAI), f18 = 0xFF01 (byte0=0x01, byte1=0xFF, **chi cau truc bit, chua gan semantic nhom/subtype**). f10 tro VA `0x041A6000` -> mapping ELF -> file `0x1A6040` -> bounded ASCII `"NOT_SET"` (xac thuc tu byte, khong su doan). Raw +0x10 = `00 60 1a 04` (khong phai `60 1a 04 00` dich LE/word), raw +0x18 = `01 ff` (khong phai doc tai vi tri sai).

### Sai 3: WPR (GSP_AUDIT §6)
- Da doi chieu raw LO `0x01F7E000`, HI `0x01FFEE00` voi `SECURITY/p8_wpr.json` (NV_PFB_PRI_MMU_WPR2_ADDR_LO/HI @ `0x1fa824`/`0x1fa828`) -> KHOP. Chua tim saiot "thieu so 0" cu the o cac dong do; neu sai o khac, can chi dia chi, khong bi so moi.

### Cap nhat CHECKPOINT.json
- `verified_this_turn.gsp_callback`: them target helper `0x04F075EC` (REDACTED_USER tu raw), bnez ve `0x04F575D4`, a1 = ket qua helper tren duong di vong lap (khong phai s4 tai diem goi), callback target UNKNOWN.
- `verified_this_turn.descriptor_table`: f10 sua `0x41A6000` (raw `00 60 1a 04...`), f18 chi bit (0xFF01), chua gan semantic.
- Lich su cu duoc luu trong mang `corrections_this_turn` duoi day.

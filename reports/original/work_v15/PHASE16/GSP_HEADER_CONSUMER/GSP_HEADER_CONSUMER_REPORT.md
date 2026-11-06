# GSP_HEADER_CONSUMER_REPORT — CMP40HX/TU106 (offline)

## 1. Môi trường và phương pháp
- Binary: /home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin (embedded ELF64 tại file 0x40, machine RISC-V 0xf3, entry 0x4009000).
- Script: PHASE16/GSP_HEADER_CONSUMER/header_consumer_analysis.py, chạy bởi /usr/bin/python3 (Python 3.12.3), capstone 5.0.7. Toàn bộ offline.
- Không sửa artifact của job khác, không chạm checkpoint chung, không thay đổi GPU/config/model, không gọi whole-GPU DONE.
- Mapping ELF<->file: tự lấy từ PT_LOAD qua stdlib `struct`, delta vaddr-off = 0x4000000 cho tất cả segment có dữ liệu, tức VA = outer_file_offset + 0x03ffffc0. Không hard-code tên section/NOBITS.
- Trình giải mã: Capstone thật `CS_ARCH_RISCV | CS_MODE_RISCV64 | CS_MODE_RISCVC`. Khẳng định cũ "Capstone lacks RISC-V backend" là SAI (lỗi dùng sai `CS_MODE_64` -> `CS_ERR_MODE`). Tên thanh ghi in theo ABI RISC-V (s0/s1/... = x8/x9/...), không dùng op_str của minimal decoder cũ làm bằng chứng.

## 2. Inputs và kiểm tra bản đồ (map)
- gsp_tu10x.bin: 22,901,632 B, sha256 = 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b.
- Mapping candidate: VA 0x459c5e0 = file 0x59c620 (khớp expected). Fingerprint VA 0x4022338 = file 0x22378 (khớp); artifact global_va 0x40022338 là SAI, đã loại.
- Tất cả con trỏ nhánh/goal trong cửa sổ 후보 đều nằm trong segment có dữ liệu (va_in_loaded = true).

## 3. Extent của hàm candidate (CFG có bounds, không lấy return đầu tiên làm hết)
- Đầu hàm: VA 0x459c5e0 (file 0x59c620).
- Duyệt CFG trực tiếp (fallthrough + nhánh điều kiện); goal qua con trỏ hàm (jalr/auipc+jalr) coi là hàm callee riêng, KHÔNG tính vào extent của hàm này. Dừng block tại ret/ebreak/nhánh/goal. Giới hạn 6000 lệnh (chưa fixpoint toàn bộ do vùng nhánh dày).
- Extent đã duyệt: VA 0x459c5e0 .. 0x45a0fb0 (file 0x59c620 .. 0x5a0fec), 603 block, 6000 lệnh.
- Return đầu tiên 0x459c7cc (file 0x59c80c) KHÔNG là kết thúc hàm: nó là mã không tới được (nằm sau `ebreak` @0x459c760, không có edge CFG vào). Ret đầu tiên tới được = 0x459cc2c, cũng không phải hết hàm — các nhánh điều kiện dẫn các block lỗi ngoài cửa sổ 124 lệnh cũ.
- Goal indirect call được giải (auipc+jalp, tính từ bytes):
  * 0x459c6b0 (auipc ra,0xce5 @0x459c6ac + jalr ra,ra,0x284) -> 0x5281930 (file 0x1281970)
  * 0x459c73c (auipc ra,0x1024 @0x459c738 + jalr ra,ra,-0x260) -> 0x55c04d8 (file 0x15c0518)
  * 0x459c750 (auipc ra,9 @0x459c74c + jalr ra,ra,0x7f8) -> 0x45a5f44 (file 0x5a5f84)
- Các goal jalr khác không có auipc liền trước -> unresolved (đã lưu, không bịa dix).

## 4. Xác thực dataflow header (raw/CFG/call-argument, không copy thành fact)
Gọi qua con trỏ hàm đầu tiên (`jalr s2` @0x459c648; s2 = a2 = con trỏ hàm đối số) đọc 24 byte vào stack:
- a3 = 0x18 (24 byte) @0x459c628; a2 = 0 @0x459c62c; a1 = s0 - 0x90 = buffer stack @0x459c630.
- Khung stack 0x90; s0 = sp + 0x90 (@0x459c5e0 `addi sp,sp,-0x90`, @0x459c600 `addi s0,sp,0x90`).

Bố cục header 24 byte trên stack (sp = s0 - 0x90):
| Vị trí stack | Trường | Lệnh đọc | So sánh với | Nhánh sai |
|---|---|---|---|---|
| sp+0x00 = stack-0x90 | magic (8B) | `ld a1, -0x90(s0)` @0x459c658 | rodata 0x4022330 "NVUCODES" | `bne a1,a5 -> 0x459c9b4` @0x459c660 |
| sp+0x08 = stack-0x88 | version (u32) | `lw a1, -0x88(s0)` @0x459c664 | 1 | `bne a1,a5 -> 0x459c990` @0x459c66c |
| sp+0x0c = stack-0x84 | count (u32) | `lw a1, -0x84(s0)` @0x459c680 | 496 (0x1f0) | `bne a1,a5 -> 0x459c9d0` @0x459c688 |
| sp+0x10 = stack-0x80 | fingerprint (u64) | `ld a1, -0x80(s0)` @0x459c674 | rodata 0x4022338 | `bne a1,a2 -> 0x459c9f8` @0x459c67c |

Rodata (qua PT_LOAD, không hard-code):
- `lui a5, 0x4022` @0x459c654; `ld a5, 0x330(a5)` -> 0x4022330 @0x459c65c. Raw file 0x22370 = `4e5655434f444553` = "NVUCODES".
- `ld a2, 0x338(a5)` -> 0x4022338 @0x459c678. Raw file 0x22378 = `2bae986bab90198d`, u64 LE = 0x8D1990AB6B98AE2B, khớp firmware_container_source_verified.json.

Nhánh `call1` lỗi: `bnez s1, 0x320` @0x459c650 -> 0x459c970 (sai sau gọi con trỏ hàm đọc 24 byte).
Nhánh `call2` lỗi (+0x3d4 như yêu cầu): `bnez s1, 0x3d4` @0x459c6d4 -> 0x459caa8.

Tất cả target nhánh được tính toán từ immediate trong raw bytes, không từ op_str của decoder cũ.

## 5. Vòng lặp bảng bản ghi (record table)
- Cơ sở bảng s9 = 0x4584790: `lui s9, 0x4584` @0x459c6e8, `addi s9, s9, 0x790` @0x459c6f4. Nằm segment read-only, file 0x5847d0. (Đây là ứng viên địa chỉ bảng toàn cục; nguồn tên bảng chưa có trong nhị phân.)
- Chỉ số s8 = 0 @0x459c6f0 (`mv s8, zero`).
- Bước s10 = 0x18 = 24 @0x459c6f8 (`addi s10, zero, 0x18`).
- Mở rộng chỉ số: `slli s4, s8, 0x20` @0x459c6fc; `srli s4, s4, 0x20` @0x459c700 (zero-extend 32-bit chỉ số).
- Địa chỉ bản ghi: `mul s2, s4, s10` @0x459c704 (index * 24); `add a4, s9, s2` @0x459c708 (a4 = bảng + index*24).
- Bản ghi đầu tiên (index 0) -> 0x4584790 (file 0x5847d0). -> Chứng minh index và viẹc tính đến ít nhất 1 entry.
- flags@+0x10: `lw a5, 0x10(a4)` @0x459c70c; `andi a5, a5, 4` @0x459c710 (kiểm tra BINDATA_FLAG_EXTERNAL 0x4); `beqz a5 -> 0x459c7f8` @0x459c714 (bỏ qua nếu không external).
- flags&-6 (REFERENCED|EXTERNAL): `lw a5, 0x10(s2)` @0x459c71c (s2 = s7 + index*24); `andi a3, a5, -6` @0x459c720; `beqz a3 -> 0x459c828` @0x459c724.
- actualSize@+0 và relOffset@+20: KHÔNG có lệnh trong vùng đã duyệt đọc trực tiếp hai trường này trên con trỏ bảng (chỉ flags@+0x10 được thấy) -> cần source hoặc quét sâu hơn, coi là chưa chứng minh từ nhị phân.
- Gọi fetch callback tới ít nhất 1 entry: trước indirect call @0x459c738 (`auipc ra,0x1024` + `jalr ra,ra,-0x260` -> 0x55c04d8) thiết lập `a0 = 2` @0x459c730, `a1 = 0x29` @0x459c72c, `a2 = 0x58e7990` (@0x459c728 `lui a2,0x58e8` + @0x459c734 `addi a2,a2,-0x670`), với chỉ số s8 = 0 đã dùng để tính địa chỉ bản ghi đầu tiên.

## 6. Pseudocode (kèm bằng chứng lệnh)
```
// VÀO: a0, a1, a2(con trỏ hàm đọc header), ...   [jalr s2 @0x459c648]
sp -= 0x90; save s0..s11, ra                       [0x459c5e0..0x459c618]
s0 = sp + 0x90                                     [0x459c600]
s2 = a2; s5 = a1                                   [0x459c620, 0x459c624]
a3 = 0x18; a2 = 0; a1 = s0 - 0x90                 [0x459c628, 0x459c62c, 0x459c630]  // đọc 24 byte vào stack buf
a5 = *(u64*)(0x4203000 - 0x6d0 = 0x4202930);       [0x459c634, 0x459c61c lui s6,0x4203]
*(u64*)(s0 - 0x78) = a5; s3 = ra; s4 = a0          [0x459c638, 0x459c640, 0x459c644]
ret1 = s2(a0=s4, a1=stack, a2=0, a3=24)            [0x459c648 jalr s2]  <- đọc header 24B vào stack
if (sext.w(ret1) != 0) goto 0x459c970              [0x459c64c, 0x459c650]
// stack header: magic@sp+0(stack-0x90), ver@sp+8(stack-0x88), cnt@sp+0xc(stack-0x84), fp@sp+0x10(stack-0x80)
if (*(u8*)(sp+0) != "NVUCODES" @0x4022330) goto 0x459c9b4   [0x459c654-0x459c660]
if (*(u32*)(sp+8) != 1) goto 0x459c990               [0x459c664-0x459c66c]
if (*(u64*)(sp+0x10) != 0x8D1990AB6B98AE2B @0x4022338) goto 0x459c9f8  [0x459c674-0x459c67c]
if (*(u32*)(sp+0xc) != 496) goto 0x459c9d0           [0x459c680-0x459c688]
s7 = ret1                                          [0x459c6b4]
if (s7 == 0) goto 0x459ca68                          [0x459c6b8]
// vong lap bang ghi, co so 0x4584790, buoc 24, chi so bat dau 0
index = 0                                          [0x459c6f0 mv s8,zero]
table = 0x4584790                                  [0x459c6e8 lui + 0x459c6f4 addi]
stride = 24                                        [0x459c6f8]
loop:
  addr = table + zero_extend(index)*24             [0x459c6fc-0x459c708]
  flags = *(u32*)(addr + 0x10)                     [0x459c70c lw a5,0x10(a4)]
  if ((flags & 4) == 0) goto loop_inc              [0x459c710, 0x459c714 beqz -> 0x459c7f8]
  flags2 = *(u32*)(s7 + index*24 + 0x10)           [0x459c718 add s2=s7,s2; 0x459c71c lw]
  if ((flags2 & -6) == 0) goto 0x459c828           [0x459c720 andi -6; 0x459c724 beqz]
  // fetch callback, chi so index = 0 da duoc REDACTED_USER den entry dau tien
  a0=2; a1=0x29; a2=0x58e7990; call_indirect -> 0x55c04d8  [0x459c728-0x459c73c]
  ... (cac goi tiep theo, engine mapping chua xac dinh)
loop_inc:
  index++; if (index < count) goto loop_body       [0x459c7f8 addiw s8,s8,1; bltu s8,a3,-0x100]
epilogue / tra ve                                  [cac ret @0x459cc2c va sau]
```

## 7. Phân loại kết quả
| Thành phần | Trạng thái | Cơ sở |
|---|---|---|
| Vị trí/raw/hash magic + fingerprint | VERIFIED (source-correlated) | Raw file 0x22370/0x22378, VA qua PT_LOAD, sha256 cửa sổ, assert trong script PASS |
| Mapping file<->VA | VERIFIED | PT_LOAD parsed, cross-check 0x459c5e0=0x59c620, 0x4022338=0x22378 |
| Chuỗi validation header (magic/ver/count/fp vs stack) | VERIFIED (source-correlated) | Lệnh + raw + target nhánh tính toán đúng |
| Ý định hàm (tiêu thụ header GSP) | CANDIDATE (inferred) | ELF bị strip, không ký hiệu; suy từ chuỗi dữ liệu |
| Cơ sở bảng (0x4584790), bước 24, chỉ số, flags@+0x10 | VERIFIED (lệnh) | Lệnh + raw trong CFG |
| Gọi fetch callback tới entry đầu tiên | VERIFIED (lệnh) | a0/a1/a2設 trước goal @0x459c738, chỉ số s8=0 |
| actualSize@+0 / relOffset@+20 trên con trỏ bảng | CHƯA CHỨNG MINH | Không thấy lệnh đọc trực tiếp trong vùng duyệt |
| Con trỏ global 0x4202930 (giá trị 0x77F2058F82306A67) | CHƯA PHÂN GIẢI | Không trỏ vào segment nào có tên |
| Mapping chỉ số slot -> BINDATA_LABEL -> engine/ten thành phần | UNKNOWN | Không có bảng nhãn, không ký hiệu, goal chưa rõ tên |

## 8. Kiểm tra raw/hash/map (tự kiểm tra trong script, EXIT=0)
- gsp sha256: 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b
- Magic raw: 4e5655434f444553 ("NVUCODES") @ file 0x22370 / VA 0x4022330
- Fingerprint raw: 2bae986bab90198d = u64 0x8D1990AB6B98AE2B @ file 0x22378 / VA 0x4022338
- Cửa sổ 48B rodata sha256: a4214709bdbacc57f670fa7bb2b8551d7f1fe162873aa2377538a2fea81ff6dd
- Candidate extent (0x459c5e0..0x45a0fb0) sha256: 9dec7a344a735e630a05195284c89b35649a1e500f762f6b96098f3bd7345152
- Tat ca assert (magic, fingerprint, VA<->file mapping) da PASS.

## 9. File đầu ra (PHASE16/GSP_HEADER_CONSUMER/)
- header_consumer_analysis.py — script chạy (stdlib + capstone, offline).
- run.log — xuất chạy, EXIT=0.
- disassembly/cfg.json — CFG: blocks, edges, goal, callee headers, ranh giới hàm riêng.
- disassembly/extended_disasm.txt — danh sách lệnh mở rộng (raw/VA/file/mnemonic/operands, nhánh + goal).
- header_consumer_verified.json — kết quả có cấu trúc (mapping, fingerprint, extent, nhánh, goal, bằng chứng, phân loại).
- GSP_HEADER_CONSUMER_REPORT.md — báo cáo này (file đang xem).

## 10. Không làm
- Không gọi whole-GPU DONE. Không sửa artifact hoặc checkpoint chung của job khác. Không thay đổi GPU/config/model. Không giả định engine mapping; ghi UNKNOWN khi chưa đủ bằng chứng.

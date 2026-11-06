# T1_CORRECTED_FINDINGS.md

## Tong ket ket qua kiem toan lai bo dam chuong T1 (SEC2 + VBIOS)

### 1. Tat ca ket qua cu cua Capstone RISC-V+C bo SEC2 — LỌT BỎ

| Ket qua cu | Vi tri | Phan loai | Ly do |
|---|---|---|---|
| `c.lui t3, 0xfffe3` | 0x238 | FALSE DECODE | Falcon ISA ≠ RISC-V |
| `lb zero, 0x4f(t3)` | 0x206 | FALSE DECODE | Falcon ISA ≠ RISC-V |
| `lb sp, -0x25d(t3)` | 0x35A2 | FALSE DECODE | Falcon ISA ≠ RISC-V |
| `sb s2, 0x522(zero)` | 0x04990 | FALSE DECODE | Falcon ISA ≠ RISC-V |
| `sw zero, 0x7e0(s2)` | 0x0188C | FALSE DECODE | Falcon ISA ≠ RISC-V |
| `jal t0, 0xd0010` | 0x0006A | FALSE DECODE | Falcon ISA ≠ RISC-V |
| Fuse 0x522 → 0x524 | — | UNKNOWN | Không có bằng chứng address-space mapping |
| MMIO base 0xFFFE3000 | — | UNKNOWN | ISA sai, không suy được |

### 2. Bý chứng SEC2 dưọc xác minh (từ dmesg + file hệ thống)

- `image.bin.zst` (61184 bytes sau giải nén) tồn tại tại `/lib/firmware/nvidia/tu102/sec2/`
- `tu106/sec2/` là symlink toàn bộ tới `tu102/sec2/`
- `desc.bin.zst` metadata: image_size=61184, ngày "Wed Mar 29 16:9:32 2023"
- SEC2 image prefix (`d000790000fe0400bda47e10fd00f802`) được tìm thấy tại offset 0x49DE00 trong `ucodes_tu10x.bin`
- Driver load `ucodes_tu10x.bin` + `gsp_tu10x.bin` (không load sec2/image.bin.zst trực tiếp)
- Dmesg: `kgspCmp40SanitizeSec2AfterExploit`, `s_clearCmp40Sec2ExploitDmem`, `FWSEC_COMPLETE_GSP_UNTOUCHED`
- SEC2 được dùng trong cmpunlocker compute path, GSP không bị modify

### 3. Bý chứng VBIOS stock vs t4

| Thuộc tính | Stock | T4 |
|---|---|---|
| Kích thước | 1,048,576 bytes | 495,616 bytes |
| PCIR entries | 8 (4 entry 0x10DE:0x1F0B) | 4 (2 entry 0x10DE:0x1F0B) |
| DCB entries | 2 (0x2d9b2, 0xa69b2) | 1 (chỉ 0x2d9b2) |
| DCB version | 170 (0xAA, non-standard) | 170 (0xAA) |
| DCB entry_count | 0 | 0 |
| "CONNECTOR" string | 2 (0x2cbd3, 0xa5bd3) | 1 (chỉ 0x2cbd3) |
| "CONNECTOR" thực tế | ASCII "CONNECT THE PCIe POWER CABLE(S)" | Tương tự |
| BITB header | Không có | Không có |

T4 bị cắt tại 0x79000, thiếu 552,960 bytes (86% có data).

### 4. 19 byte khác nhau — không được phân loại

Tất cả nằm sau PCIR 0x53059 (0x5669C–0x566BE, 0x767FF). Không có BIT header, không có DCB entries (entry_count=0), không thể xác định section/chức năng. **Không được gọi là connector config.**

### 5. Đối chiếu display: VBIOS / fuse / GSP / PDISP

- **VBIOS:** Không có BIT header, DCB version không chuẩn, 0 entries → không có bằng chứng cấu hình display hợp lệ.
- **Fuse 0x21C04:** = 0x00000001 (host gate FALSE, DATA=1 ≠ ENABLE=0).
- **GSP:** 615.78.08 loaded, FWSEC_COMPLETE_GSP_UNTOUCHED → không có RmDisableDisplay bypass.
- **SEC2:** Dùng trong cmpunlocker compute path (SS0/SS1), không mở display.
- **PDISP:** Display Attached: No, Display Active: Disabled.

**Kết luận:** Display của CMP 40HX bị khóa ở mức fuse/hardware. Không có bằng chứng VBIOS modification hoặc SEC2 exploit có thể mở display hay khôi phục 128 CUDA cores.

### 6. Danh sach file da xuat

| File | Noi dung |
|---|---|
| `results/T1/SEC2_ISA_VALIDATION.md` | ISA Falcon ≠ RISC-V, tất cả disassembly Capstone là false decode |
| `results/T1/SEC2_FIRMWARE_PROVENANCE.md` | SEC2 nhim trong ucodes_tu10x.bin, driver load path, dmesg bằng chứng |
| `results/T1/VBIOS_BIT_PCIR_COMPARISON.md` | Stock vs T4 so sánh, T4 bị cắt, DCB, PCIR, không có BITB |
| `results/T1/DISPLAY_COPROC_BIT_ANALYSIS.md` | Đối chiếu fuse/GSP/PDISP, kết luận display khóa ở mức hardware |
| `results/T1/T1_CORRECTED_FINDINGS.md` | Tổng kết, phân loại tất cả kết quả cũ |

### 7. Han che va buoc bu

- Không có disassembler Falcon ISA chính thống → không thể phân tích mã máy SEC2.
- Không được phép flash ROM, ghi MMIO, kích hoạt doorbell, sửa SEC2 firmware, đốt OTP/RIR (theo ràng buộc).
- Không có bằng chứng trực tiếp SEC2 điều khiển display output.

# ponytail: All Capstone RISC-V+C SEC2 results discarded as false decode (Falcon ≠ RISC-V). SEC2 confirmed in ucodes_tu10x.bin at 0x49DE00, used in cmpunlocker compute path only. VBIOS: T4 truncated, no BIT header, DCB non-standard. Display locked at fuse 0x21C04=1, GSP untouched. No evidence VBIOS/SEC2 can unlock display or SM.

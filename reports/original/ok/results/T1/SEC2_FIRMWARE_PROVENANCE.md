# SEC2_FIRMWARE_PROVENANCE.md

## Ket qua kiem toan nguon goc SEC2 firmware

### 1. File ton tai tren may muc tieu (<REDACTED_LAB_IP>)

| Duong dan | Kich thuoc (raw) | Kich thuoc (giai nen) | Loai |
|---|---|---|---|
| `/lib/firmware/nvidia/tu102/sec2/image.bin.zst` | 13110 bytes | 61184 bytes | SEC2 image |
| `/lib/firmware/nvidia/tu102/sec2/desc.bin.zst` | 123 bytes | 656 bytes | Descriptor metadata |
| `/lib/firmware/nvidia/tu102/sec2/sig.bin.zst` | 135 bytes | ? bytes | Signature |
| `/lib/firmware/nvidia/tu106/sec2/image.bin.zst` | symlink | symlink → tu102/sec2/image.bin.zst | Symlink |
| `/lib/firmware/nvidia/tu106/sec2/desc.bin.zst` | symlink | symlink → tu102/sec2/desc.bin.zst | Symlink |
| `/lib/firmware/nvidia/tu106/sec2/sig.bin.zst` | symlink | symlink → tu102/sec2/sig.bin.zst | Symlink |

**SHA-256 (raw .zst files):**
- image.bin.zst: `8d8797d821ac955825bb40ccb12108348422144cdb7919c952e40cc443f0395b`
- desc.bin.zst: `c432fb8c989d749cf4046db2f35011528b0b8375dc9c58fef00424b210933ff8`
- sig.bin.zst: `59243de3e173148abb8acddd39f6f6470da9984d4cd9bd87355941b951f6d30f`

### 2. Metadata tu desc.bin.zst (giai nen, 656 bytes)

| Offset | Gia tri (LE u32) | Nghia |
|---|---|---|
| 0x00 | 0x0000028C (652) | Tong kich thuoc descriptor |
| 0x04 | 0x0000EF00 (61184) | Kich thuoc image SEC2 (khop voi giai nen image.bin.zst) |
| 0x08 | 0x00000003 (3) | Phíen bản? |
| 0x0C-0x27 | Chuỗi ngày "Wed Mar 29 16:9:32 2023" | Ngày xử lý/build |
| 0x54 | 0x00000190 (400) | Offset/kich thuoc? |
| 0x58 | 0x0000FD00 (64768) | Offset/kich thuoc? |
| 0x5C | 0x0000FD00 (64768) | Offset/kich thuoc? |
| 0x60 | 0x00000200 (512) | Page size / alignment? |
| 0x64 | 0x0000ED00 (60672) | Offset/kich thuoc? |
| 0x78 | 0x00001F64 (8036) | Offset? |
| 0x7C | 0x00004C00 (19456) | Offset? |
| 0x80 | 0x000051BC (20924) | Offset? |
| 0x84 | 0x00000006 (6) | So luong? |
| 0x88 | 0x00000005 (5) | So luong? |
| 0x8C | 0x00002000 (8192) | Alignment? |

**Ngon ngu:** desc.bin.zst dủng du̠ng dấu phầt hiện "image_size = 61184" khóa khớp với image.bin.zst đầu gián nén. Tuy nhiên, cung các trường offset/kích thước khác chưa có tài liệu chính thấc NVIDIA để gán nhiệm, có thể là section table hoặc load address table.

### 3. Duong tải firmware thuc te của driver 615.78.08

`modinfo nvidia` cho ra:
- `firmware: nvidia/615.78.08/ucodes_tu10x.bin` (8,837,632 bytes)
- `firmware: nvidia/615.78.08/gsp_tu10x.bin` (22,901,632 bytes)

**KHÔNG có** tham chiếu trực tiếp đến `sec2/image.bin.zst` trong danh sách firmware của module nvidia.

### 4. SEC2 dưọc nhim vào ucodes_tu10x.bin

Prefix 16 byte đầu của SEC2 image (`d000790000fe0400bda47e10fd00f802`) **được tìm thấy tại offset 0x49DE00** trong `/lib/firmware/nvidia/615.78.08/ucodes_tu10x.bin`.

**Kết luận:** SEC2 không được load như một file độc lập. Nó được nhim vào `ucodes_tu10x.bin` (microcode bundle cho TU10x), được driver nvidia load tại khởi tạo kernel. `tu106` dùng cùng `ucodes_tu10x.bin` (TU106 thuộc họ TU10x).

### 5. Bý chứng tư dmesg (kernel log, read-only)

Driver 615.78.08 đã load và ghi log sau (từ `dmesg`, read-only):

```
NVRM: GPU0 kgspCmp40SanitizeSec2AfterExploit: CMP40_COMPUTE_UNLOCK_V534: NATIVE_CLEANUP_DMEM_PRESERVED_PASS
NVRM: GPU0 s_clearCmp40Sec2ExploitDmem: CMP40_COMPUTE_UNLOCK_V526: FULL_DMEM_ZERO_PASS [0x00000000,0x00010000)
NVRM: GPU0 kgspBootstrap_TU102: CMP40_COMPUTE_UNLOCK_V274: FWSEC_COMPLETE_GSP_UNTOUCHED idx=96
NVRM: GPU0 kgspExecuteBooterLoad_TU102: CMP40_BOOTER_COMPAT_V552: UNLOCK_BOOTER=610.57.04 GSP_BOOTER=615.78.08
```

**Nhận xét:**
- SEC2 được nhắc đến rõ ràng trong code path của cmpunlocker (`Cmp40SanitizeSec2AfterExploit`, `clearCmp40Sec2ExploitDmem`).
- SEC2 DMEM được xóa sạch (zeroed) sau khi exploit chạy.
- GSP được đánh dấu là `UNTOUCHED` — không bị modify bởi SEC2 exploit.
- Đây là bằng chứng driver **thực sự sử dụng SEC2** trong quá trình khởi tạo CMP 40HX.

### 6. Phan loai ket qua cũ

| Ket qua cũ | Phân loại | Lý do |
|---|---|---|
| `c.lui t3, 0xfffe3` tại 0x238 | FALSE DECODE | Falcon ISA ≠ RISC-V |
| `lb zero, 0x4f(t3)` tại 0x206 | FALSE DECODE | Falcon ISA ≠ RISC-V |
| `sb s2, 0x522(zero)` tại 0x04990 | FALSE DECODE | Falcon ISA ≠ RISC-V |
| `jal t0, 0xd0010` tại 0x0006A | FALSE DECODE | Falcon ISA ≠ RISC-V |
| Fuse 0x522 liên quan đến 0x524 | UNKNOWN | Không có bằng chứng address-space mapping |
| SEC2 có MMIO base 0xFFFE3000 | UNKNOWN | ISA sai → không thể suy ra MMIO base |

## Ghi chú PONYTAIL

# ponytail: SEC2 is embedded in ucodes_tu10x.bin at 0x49DE00, not a standalone file. Driver loads ucodes_tu10x.bin + gsp_tu10x.bin. All Capstone RISC-V+C disassembly is false decode (Falcon ≠ RISC-V). dmesg confirms SEC2 is used in cmpunlocker path but GSP untouched.

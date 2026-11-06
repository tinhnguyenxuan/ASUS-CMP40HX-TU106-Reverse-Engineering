# FW_PAYLOAD_ISA_REPORT — PHASE16 (CMP40HX / TU106 ucode container)

## 1. Phạm vi và ràng buộc (đã tuân thủ)
- Chỉ phân tích file offline: `outputs/ucodes_tu10x.bin` (8,837,632 B) và `PHASE16/firmware_container_source_verified.json` (496 slots, 38 external payload).
- Source: `/tmp/nvsrc` (bindata + Falcon/RISC-V descriptors), `/tmp/envytools` (envydis đã build). Các file nguồn cũng được sao chép vào `PHASE16/SOURCES/` với manifest + sha256.
- Không cài tool mới (stdlib Python 3 only). capstone **không có** trong /usr/bin/python3 → không disassemble RISC-V qua CS_MODE_RISCV64|CS_MODE_RISCVC được; đánh giá cấu trúc duy nhất, công nhận là chưa chứng minh ISA.
- Không gọi GPU, không thay config/model/driver, không xử lý signature/key, không bruteforce, không gọi checksum/version khi chưa có consumer.
- Xuất riêng tại `PHASE16/FW_PAYLOAD_ISA/`, không ghi checkpoint chung.

## 2. Input artifacts
| File | SHA256 |
|------|--------|
| outputs/ucodes_tu10x.bin | (xem payload_isa_verified.json, input_sha256) |
| PHASE16/firmware_container_source_verified.json | 496 records; 38 external (class=external, flags=0x04, cSize=0) |

Source headers dùng để tra cứu (sourcehash = sha256 của nội dung file nguồn; 줄 số theo snapshot /tmp/nvsrc):
- `BINDATA_UCODES_BIN_HEADER` / `BINDATA_STORAGE_PVT`: `nvidia/src/kernel/core/bin_data_pvt.h`, lignes 60-114.
- `BINDATA_LABEL` enum: `nvidia/inc/kernel/core/bin_data.h`, lignes 43-84+ — **lưu ý: đây là index per-label PBINDATA_STORAGE, KHÔNG phải global slot index**; không dùng làm slot.
- `RM_RISCV_UCODE_DESC`: `nvidia/arch/nvalloc/common/inc/rmRiscvUcode.h`, lignes 36-93 (version 1-5 theo comment).
- `RM_FLCN_BL_DESC` / `RM_FLCN_BL_IMG_HEADER` / `RM_FLCN_BL_DMEM_DESC`: `nvidia/arch/nvalloc/common/inc/rmflcnbl.h`, lignes 45-145.
- `nvfw_hs`: **không tìm thấy** trong snapshot /tmp/nvsrc.
- Generated firmware descriptor instances: **không tìm thấy** (chỉ có khai báo con trỏ `RM_RISCV_UCODE_DESC *pGspRmBootUcodeDesc` trong `g_kernel_gsp_nvoc.h`; không có initializer instance nào trong snapshot).

## 3. Phase 1 — Inventory toàn bộ 38 payload
Xem chi tiết trong `payload_isa_verified.json` (mảng `inventory`): slot, offset, actualSize, compressedSize, pData, flags, relOffset, sha256, entropy, headerraw (32 byte đầu), bounded strings (chạy in-print ≥4 byte), zero-padding runs ≥16 byte.

5 payload entropy thấp nhất (đáng kiểm ISA):
| slot | offset | size | entropy | headerraw (16B) |
|------|--------|------|---------|-----------------|
| 493 | 0x85E500 | 62,720 | 2.424 | d000790000fe0400bda47e10fd00f802 |
| 487 | 0x81BF00 | 147,712 | 2.786 | d000f00000fe0400bda47e10fb00f802 |
| 20 | 0x002F00 | 122,880 | 3.481 | d0c0ff0000fe0400bda47e10fe00f802 |
| 490 | 0x840000 | 124,160 | 3.798 | d000f00000fe0400bda47e10fb00f802 |
| 481 | 0x7D2800 | 143,360 | 4.198 | d000f00000fe0400bda47e10fb00f802 |

Nhận định: các payload `d0*` chia sẻ header 16 byte (`d0 00 XX 00 00 fe 04 00 bd a4 7e 10 XX 00 f8 02`) — **không phải** RM_FLCN_BL_IMG_HEADER (biên trái vượt biên, chưa căn 256). Các payload entropy≈8.0 (slots 21-24, 151-154, 452, 453, 456, 459, 460, 464-469, 473, 474, 477, 478) không có cấu trúc ISA nhận diện được; từ chối giả thuyết "là code thực thi", **không kết luận đây là AES** (entropy alone không chứng minh mã hóa, theo yêu cầu).

## 4. Phase 2 — Tra cứu source và kiểm tra giả thuyết layout tại offset 0 của mỗi payload
Tất cả giả thuyết dưới đều được kiểm tra theo struct thực từ source (biến thể lengths/offsets so với actualSize), rồi **từ chối khi bất hợp lệ**:

| Hypothesis | Chấp nhận | Lý do từ chối (dấu hiệu phổ biến) |
|------------|-----------|-----------------------------------|
| RM_RISCV_UCODE_DESC @ offset 0 | 0/38 | version=0 (ngoài tập 1-5 theo comment rmRiscvUcode.h); nhiều trường offset+size vượt payload (ví dụ manifestOffset=3 chồng descriptor); |
| RM_FLCN_BL_IMG_HEADER @ offset 0 | 0/38 | codeSize=0 hoặc codeOffset+codeSize vượt payload; dataOffset+dataSize vượt payload; offset không chia 256 |
| Payload entropy cao là code ISA | 0 (không chấp nhận) | entropy 7.99-8.0, không có cấu trúc lệnh; không kết luận AES |

Kết luận Phase 2: **không hipótesis layout từ source nào khớp toàn bộ bytes tại offset 0 của payload**. Header `d0*` và bảng offset + chuỗi timestamp nhúng (slots 33/35) là cấu trúc thực tế quan sát được, chưa khớp với struct source đã có trong snapshot. BINDATA_LABEL không dùng làm global slot.

## 5. Phase 3 — Disassemble 4 ứng viên thấp entropy (ít nhất 2, đã đủ)
Tool: `/tmp/envytools/build/envydis/envydis -i -n -m falcon -b 0 -d <skip> -l 150 <file>` (envydis đã có sẵn; hỗ trợ `falcon` qua `ed_getisa`, xem `/tmp/envytools/envydis/core.c` lignes 47-69). Chọn code-start bằng longest initial valid-instruction prefix (không disassemble header/padding làm lệnh; không lấy toàn padding làm instruction hợp lệ).

| slot | offset | code-start | prefix hợp lệ | hợp lệ/tổng | ratio | Engine (độ tin cậy) |
|------|--------|------------|---------------|-------------|-------|---------------------|
| 493 | 0x85E500 | +0x10 | 11 | 63/170 | 0.371 | Falcon (medium) |
| 487 | 0x81BF00 | +0x10 | 11 | 68/175 | 0.389 | Falcon (medium) |
| 490 | 0x840000 | +0x10 | 11 | 63/170 | 0.371 | Falcon (medium) |
| 20 | 0x002F00 | +0x24 | 17 | 35/258 | 0.136 | Falcon (medium) |

Mẫu lệnh thực (slot 493, từ +0x10, giữ raw + offset):
```
0x0010: 98 9f 09  ld b32 $r15 D[$r9+0x24]
0x0013: 98 9e 0a  ld b32 $r14 D[$r9+0x28]
0x0016: 98 93 12  ld b32 $r3  D[$r9+0x48]
0x0019: 98 91 0f  ld b32 $r1  D[$r9+0x3c]
0x001c: b6 f5 08  shr b32 $r15 0x8
0x001f: b6 e4 18  shl b32 $r14 0x18
0x0022: 98 9a 13  ld b32 $r10 D[$r9+0x4c]
0x0025: fd ef 05  or $r14 $r15
...
0x0034: fe 9b 00  mov $xtargets $r9
```
slot 20 (từ +0x24): `shl b32`, `ld b32`, `or`, `mov $xtargets $r15` — cùng họ Falcon, dùng các Falcon special register `$xcbase` / `$xtargets` và addressing `D[$r9+imm]`.

Nhận định engine: **Falcon ISA (mã Falcon/TU106-era ucode)** cho 4 ứng viên, độ tin cậy **medium** — có chuỗi lệnh hợp lệ liên tiếp bao gồm các lệnh Falcon đặc quyền ($xcbase/$xtargets, context load), nhưng tỉ lệ lệnh hợp lệ trong cửa sổ bịa trộn (có bytes không decode được, có thể là bảng/data canh giữa), và chưa có consumer cross-check (không gọi GPU/MMIO). Không khẳng định đây là "full Falcon ucode validated"; coi là ISA-level identification, không phải execution proof.

RISC-V: slots 32-37, 150-156 có header 96 byte dạng bảng offset (giống RM_RISCV_UCODE_DESC skeleton) nhưng **bị từ chối** (version=0 không trong 1-5; trường offset+size vượt biên). Capstone chưa cài và không được cài thêm → **không disassemble RISC-V**; engine identity = **UNKNOWN**, bằng chứng giữ nguyên (header bytes, offset table, chuỗi timestamp nhúng).

## 6. Phase 4 — blob6 / blob8 theo extents mới (loại zero padding)
Nguồn bằng chứng: `FIRMWARE/q8_blobdiff.json` (đã đọc lại, không sinh lại file blob cũ vì không có artifact cũ trong workspace).

- blob6 = slot 33 @ 0x0b7c00; blob8 = slot 35 @ 0x0f5400; extent so sánh = 125,696 B.
- diff_count = 24 byte trong 4 run (chấp nhận theo bản ghi):
  - 2 run 1 byte (outliers, **không phải timestamp**): offset 0x6f3e (blob6=0x21, blob8=0x1f) và offset 0x6b59 → **0xb659** (blob6=0x21, blob8=0x1f).
  - 2 run 20 byte = chuỗi timestamp nhúng ("Dec 31 2024 ..." @ 0x7200, "Dec 31 2024 ..." @ 0xb7b8 trên blob6; tương ứng "Jan 2 2025" trên blob8) → **dữ liệu, không phải trường version/consumer**.
- Vị trí 0x6f3e và 0xb659 so với metadata đã kiểm tra: nằm **bên trong extent của slot 33/35**, ở vùng dữ liệu/bảng offset (header 0 byte và RM_RISCV_UCODE_DESC/RM_FLCN_BL_IMG_HEADER đã bị từ chối theo Phase 2). **Không xác định được là code hay header** vì không có layout hypothesis nào chấp nhận cho slot 33/35. Không gọi checksum/version — chưa có consumer xác định trong source snapshot.
- File bằng chứng chi tiết: `payload_isa_verified.json` → `blob_diff`.

## 7. Kết luận
- Đã xác định cấu trúc/engine bằng bằng chứng cho 4 payload thấp entropy: **Falcon ISA**, code bắt đầu tại payload +0x10 (slot 493, 487, 490) và +0x24 (slot 20), kèm raw/offset trong `disasm` của `payload_isa_verified.json`; độ tin cậy medium.
- Các giả thuyết layout từ source tại offset 0 (RM_RISCV_UCODE_DESC, RM_FLCN_BL_IMG_HEADER) đều **bị từ chối** (lengths/offsets bất hợp lệ); BINDATA_LABEL không phải global slot; không có generated firmware descriptor instance trong snapshot.
- Các payload entropy≈8.0: từ chối là code ISA, **không kết luận AES**; engine **UNKNOWN**.
- Slots 32-37/150-156 (dạng bảng offset + timestamp): cấu trúc nhận diện được nhưng version=0 không khớp source; capstone thiếu → không disassemble RISC-V; engine **UNKNOWN**, bằng chứng tìm kiếm vẫn giữ.
- blob6/blob8: 24 byte sai khác = 2 byte outlier (0x6f3e, 0xb659: 0x21 vs 0x1f) + 2 chuỗi timestamp; không gọi checksum/version.

## 8. File sản xuất (PHASE16/FW_PAYLOAD_ISA/)
- `payload_isa_verify.py` — script chạy lại (chuỗi lệnh ở đầu file).
- `run.log` — nhật ký chạy thực của script.
- `payload_isa_verified.json` — toàn bộ accepted/rejected hypotheses (sourcehash/line), rawoffsets, disasm bounded (raw + offset), engine identity confidence, inventory 38 payload, blob_diff evidence.
- `FW_PAYLOAD_ISA_REPORT.md` — báo cáo này.
- `work/` — trích xuất tạm các payload ứng viên (p493.bin, p487.bin, p490.bin, p20.bin) cho việc tái điều tra.

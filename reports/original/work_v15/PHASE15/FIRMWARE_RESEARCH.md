# PHASE15/FIRMWARE_RESEARCH.md — Nghiên cứu 11 blob firmware Falcon

## 1. Mục tiêu

Tìm cấu trúc metadata/header của từng blob, xác định blob chứa code/data/vùng chưa rõ, phân biệt RISC-V/Falcon ISA/data section, tìm load address/engine mapping/mailbox. Không brute-force khoá, không bypass security.

## 2. Dữ liệu gốc

| Trường | Giá trị |
|---|---|
| Source | `FIRMWARE/P4_FIRMWARE.md`, `FIRMWARE/firmware_inventory.json`, `TOOLS/fw_entropy.py` |
| File | `ucodes_tu10x.bin` (8,837,632 B) |
| Container | NVUCODES, ver=1, header_size=0x1F0, hash `0x8D1990AB6B98AE2B` |
| Entry table | `@0x1F0`, stride 32, marker `04 00 00 00` + offset u32 |
| Số blob | 11 |

## 3. Bảng 11 blob (đã phân loại)

| # | Offset | Size | Entropy | Nội dung xác định được |
|---|---|---|---|---|
| 0 | `0x002F00` | 122,880 | 3.481 | **Dữ liệu, không phải code Falcon** (INFERRED) |
| 1 | `0x020F00` | 122,880 | 7.998 | Không nén được, nội dung khác 2/3/4 |
| 2 | `0x03EF00` | 122,880 | 7.998 | Giống blob 1 |
| 3 | `0x05CF00` | 122,880 | 7.998 | Giống blob 1 |
| 4 | `0x07AF00` | 122,880 | 7.998 | Giống blob 1 |
| 5 | `0x098F00` | 126,208 | 4.915 | Plaintext, khác blob[7] 41% |
| 6 | `0x0B7C00` | 125,696 | 4.898 | Plaintext, **≡ blob[8] (24 B khác)** |
| 7 | `0x0D6700` | 126,208 | 4.916 | Plaintext, khác blob[5] 41% |
| 8 | `0x0F5400` | 125,696 | 4.898 | Plaintext, **≡ blob[6]** |
| 9 | `0x113F00` | 132,096 | 4.953 | Plaintext |
| 10 | `0x134300` | 7,575,296 | 7.261 | Hỗn hợp, lớn nhất |

**Đếm lại đúng:** 11 blob = 4 không nén được (4 nội dung khác nhau) + 6 plaintext (~5 nội dung duy nhất, vì 6≡8) + 1 hỗn hợp + 1 dữ liệu.

## 4. `blob[6]` ≡ `blob[8]` (PHÁT HIỆN QUAN TRỌNG NHẤT P4)

- XOR `blob[6]^blob[8]`: entropy 0.0033, nonzero 0.0% → gần như bằng 0.
- 24 byte khác ở 4 cặp vị trí: `0x6F3E` (1 B), `0x7200..0x7213` (20 B), `0xB659` (1 B), `0xB7B8..0xB7CB` (20 B).
- **Kết luận:** hai blob trùng nhau 99.98%, khác đúng 24 byte → **cùng firmware, bản build khác nhau 2 ngày** (build timestamp ASCII: `Dec 31 2024` vs `Jan 2 2025`).

## 5. 4 blob entropy cao — KHÔNG nén được (DECODED, không kết luận AES)

| Thuật toán | Tỷ lệ nén | Kết luận |
|---|---|---|
| zlib | 1.001 | Không giảm byte |
| lzma | 0.999 | Không giảm byte |

- `distinct byte = 256/256` → cả 256 giá trị byte đều xuất hiện.
- `max_freq ≈ 1/256` → phân bố gần đều.
- **KHÔNG kết luận "là AES"** (C3: entropy cao không phân biệt AES vs nén tối đa).
- **KHÔNG kết luận "là LZMA/zstd"**.
- Không có magic, header, IV, salt trong 16 byte đầu.

## 6. `blob[0]` không phải code Falcon

- 3 lệnh đầu decode được (`mov $r0 0xffc0`, `mov $sp $r0`, `clear b32 $r10`, `lcall 0xfe10`, `exit`) → **trùng hợp byte pattern**.
- Toàn bộ 122,880 B: 93.1% unknown instruction từ 4 offset thử (`0x00`, `0x04`, `0x08`, `0x10`, `0x20`).
- Entropy 3.481 (quá thấp cho code), nonzero 37%, không magic `fuc`/`NVFU`.
- **Kết luận (INFERRED):** data segment / bảng tham số, không phải text segment.

## 7. Mục BLOCKED (theo yêu cầu đề bài)

| # | Phần | Lý do BLOCKED |
|---|---|---|
| 1 | Nghĩa 4 blob entropy cao | Không nén được, không magic, không IV. **Không thể phân biệt AES vs nén** từ dữ liệu hiện có. Cần: khoá giải mã (không có trong driver công khai) hoặc mẫu plaintext-known. |
| 2 | Disasm `blob[0]` thành code | 93.1% unknown từ 4 offset. **Không phải code Falcon.** Cần: xác định đây là bảng gì trước. |
| 3 | 24 byte khác blob[6]/blob[8] | Chưa biết là version / patch / checksum. |
| 4 | Entry directory chỉ có offset+size | Không có trường engine / load address → không map blob → engine nào. |
| 5 | SEC2/PMU/FECS/GPCCS riêng biệt | Không có trường trong container định danh engine. |

## 8. Function inventory / call graph / mailbox / RPC

**Chưa làm** (COVERAGE.md mục 4: function inventory = chưa làm, call graph = chưa làm, E/startup/message queue = KHÔNG LÀM). Phụ thuộc vào việc xác định load address và engine mapping (BLOCKED tại mục 7,#4).

## 9. Quy tắc an toàn

- Không brute-force khoá.
- Không trích xuất bí mật / khoá bảo mật.
- Không triển khai bypass security.
- Không giả định entropy cao = AES.

---
**Ponytail:** phân tích dựa trên firmware_inventory.json đã có. Không viết tool disasm mới (envydis chỉ Falcon, capstone không có RISC-V objdump — đã xác nhận). Thêm phân tích khi có tài nguyên disasm RISC-V lớn hơn.

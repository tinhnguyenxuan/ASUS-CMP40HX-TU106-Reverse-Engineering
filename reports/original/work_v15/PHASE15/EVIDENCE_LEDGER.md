# PHASE15/EVIDENCE_LEDGER.md — Sổ bằng chứng Phase 15

Mỗi mục: nguồn / hash / offset / output thực tế / diễn giải / độ tin.
Quy ước độ tin: **CAO** = đo trực tiếp hoặc khớp ground truth độc lập; **TRUNG BÌNH** = suy ra từ cấu trúc đã kiểm; **THẤP** = giả thuyết chưa kiểm.

## E15-01 — Phân tích 352 word fuse data

| Trường | Giá trị |
|---|---|
| Source | `FUSE/fuse2.json` (dump BAR0 aperture `0x021000`, read-only) |
| SHA-256 fuse2.json | (file dump, không băm lại trong P15) |
| Output | 352 DATA / 518 ZERO / 2,202 POISON; 126 distinct giá trị |
| Mã poison | `0xBADF5040`, `0xBADF1300`, `0xBADF1100` |
| Diễn giải | Khối fuse TU106 thực span `0x1DFF` (không phải `0x1800`); `0x820000` là GB100, không áp TU106 |
| Độ tin | **CAO** (tái lập từ dump) |

## E15-02 — 152 word = 1 (U-FUSE-001)

| Trường | Giá trị |
|---|---|
| Source | `PHASE15/fuse_analysis.json` (tính từ fuse2.json) |
| Output | 152 offset có giá trị `0x00000001`, phân tán 70 range, có gaps |
| Diễn giải | Không phải OTP bit cell vật lý (gaps, bit 0 duy nhất) → INFERRED enable flag/version |
| Độ tin | **TRUNG BÌNH** (cấu trúc rõ, không có tên register) |

## E15-03 — fuse +0x0718 32 byte entropy cao (U-FUSE-002)

| Trường | Giá trị |
|---|---|
| Source | `PHASE15/fuse_analysis.json` |
| Output | 8 word: `0x57c095dc 0x839cf28e 0xbf493942 0x51c51e03 0x64375730 0xca078f03 0xe13b9d22 0x1e38c5b9` |
| Diễn giải | Không phải hash PDI (đã exhaustive search 0 khớp). 4 giả thuyết mới: public key hash / nonce / trim / version stamp |
| Độ tin | **UNKNOWN** |

## E15-04 — Dispatcher GSP-RM @ 0x04F575FC

| Trường | Giá trị |
|---|---|
| Source | `GSP/Q1_CONSUMER.md` (disasm capstone RISC-V) |
| Output | base `0x041A70B0`, stride 32, span `0x1740` = 186 entry; layout `u16@0,u32@4,u8@8,u64@0x10,u16@0x18` |
| Diễn giải | `u64@+0x10` là tham số callback (quá `a2`), KHÔNG phải name_ptr; callback từ context `+0x30`, không từ entry |
| Độ tin | **CAO** (đọc từ code thực) |

## E15-05 — 4 giả thuyết u64@+0x10 đều bị bác bỏ

| Trường | Giá trị |
|---|---|
| Source | `PHASE15/GSP_DISPATCH_ANALYSIS.md §7` |
| Output | Suffix merging: `_MIN` ambiguous 126 lần; offset pool chỉ 16/370; u16 không phải độ dài; u64 là tham số callback |
| Diễn giải | Cần đọc hàm callback `jalr a5` để tra tên entry |
| Độ tin | **CAO** (4 giả thuyết có bằng chứng bác bỏ) |

## E15-06 — Key block VBIOS 38 record × 32 byte

| Trường | Giá trị |
|---|---|
| Source | `VBIOS/P2_VBIOS.md` |
| Output | Layout: `sig@0, ver@2, f4@4, f8@8, flags@0xC, hash@0x10`; 38 record, image #2 toàn `0xFF` |
| Diễn giải | `f4` không phải timestamp (9/38); hash không khớp vùng ROM (0/912); 5 field chưa biết nghĩa |
| Độ tin | **CAO** (layout), **UNKNOWN** (ngữ nghĩa 5 field) |

## E15-07 — 12 digest NPDS-0x70 (U-VBIOS-003)

| Trường | Giá trị |
|---|---|
| Source | `VBIOS/P2_VBIOS.md` |
| Output | 12 × 32 byte tại `0x076800..0x078400`, 0/1,365,939 phép thử khớp |
| Diễn giải | Không biết hàm băm, không biết đầu vào |
| Độ tin | **UNKNOWN** |

## E15-08 — 11 blob firmware (P4)

| Trường | Giá trị |
|---|---|
| Source | `FIRMWARE/P4_FIRMWARE.md` |
| Output | blob[6] ≡ blob[8] (24 B khác = build timestamp); 4 blob entropy 7.998 không nén được; blob[0] không phải code (93.1% unknown) |
| Diễn giải | Không kết luận AES (C3); 4 nội dung khác nhau; blob[0] = data segment |
| Độ tin | **CAO** (cấu trúc), **UNKNOWN** (ngữ nghĩa 4 blob mã hoá) |

## E15-09 — Mã trả về MMIO/poison

| Trường | Giá trị |
|---|---|
| Source | `PHASE15/MMIO_SEMANTICS.md` |
| Output | `0xBADF5040/1300/1301/1100/510C/0000`, `0xBAD00100` (25 trang), `0xFFFFFFFF` (72 trang) |
| Diễn giải | `0xBAD00100` khác họ `0xBADFxxxx` → mã mới chưa biết; `0xFFFFFFFF` GPU tự trả về, chưa xác nhận ai |
| Độ tin | **CAO** (đo được), **UNKNOWN** (ngữ nghĩa 2 mã mới) |

## E15-10 — Sửa mâu thuẫn số unknown

| Trường | Giá trị |
|---|---|
| Source | `UNKNOWN_DATABASE.json` (nguồn sự thật) |
| Output | 45 items: 35 open, 10 resolved |
| Sửa | MASTER_REPORT.md cũ ghi "37 unknown (32 open, 5 resolved)" → **SAI**; CHECKPOINT.json cũ ghi "40/31/9" → **SAI** |
| Độ tin | **CAO** (đọc trực tiếp JSON) |

---
**Ponytary:** mỗi bằng chứng có source và hash (khi có). Không ghi bằng chứng speculative.

## E15-11 — Phân tích bit pattern 352 word fuse data

| Trường | Giá trị |
|---|---|
| Source | `PHASE15/fuse_deep.json` (tính từ `FUSE/fuse2.json`) |
| Output | 352 DATA / 518 ZERO / 2,202 POISON; 126 distinct giá trị |
| Bit 0 set | 249/352 word (70.7%) |
| Bit 31 set | 62/352 word (17.6%) → nghi valid/entry flag |
| Diễn giải | Bit 0 dominan nhất quán với 152 word =1; bit 31 có thể là valid flag của bảng entries fuse |
| Độ tin | **CAO** (tính toán trực tiếp từ dump) |

## E15-12 — Giá trị recurring đặc biệt trong fuse data

| Trường | Giá trị |
|---|---|
| Source | `PHASE15/fuse_deep.json` |
| Output | `0x8000004F` ×5 (@`0x1710..0x1740`), `0x80000043` ×3 (@`0x174C..0x1764`), `0xFFFFFF8F` ×5 (@`0xD8..0xF4`), `0xFFFFFFFC` ×4 (@`0xD4..0xF0`) |
| Diễn giải | `0xFFFFFF8F` khớp `RESET_PLM`/`PLM_FECS` từ dmesg; `0x8000004F/0x43` ở vùng `0x1700..0x1780` (33 word liên tiếp) nghi là bảng entries fuse với valid flag (bit 31) |
| Độ tin | **TRUNG BÌNH** (giá trị rõ, nghĩa chưa xác định) |

## E15-13 — fuse `+0x0718`: CRC32/Adler32 (không phải SHA-256 PDI hash)

| Trường | Giá trị |
|---|---|
| Source | `PHASE15/fuse_deep.py` + `PHASE15/fuse_deep.json` |
| Output | CRC32(raw 32 byte) = `0x719E0687`; Adler32 = `0xF9630E16`; CRC32 per word và per pair đều không khớp giá trị known nào |
| Diễn giải | 32 byte entropy cao, không phải hash PDI (đã exhaustive SHA-256 0 khớp), CRC32/Adler32 cũng không khớp → 4 giả thuyết mới (public key hash, nonce booter, chip trim, version stamp) |
| Độ tin | **UNKNOWN** |

## E15-14 — Phân biệt OTP vật lý vs shadow/register

| Trường | Giá trị |
|---|---|
| Source | `PHASE15/FUSE_SEMANTICS.md §9` |
| Output | Quy tắc: chỉ coi là OTP vật lý khi có cross-check nguồn độc lập (PDI khớp `nvidia-smi -q`). `fuse+0x0000` = `0xC0040000` ≠ `NV_PMC_BOOT_0` = `0x166000A1` → INFERRED strap mirror, không phải OTP trực tiếp |
| Diễn giải | NGÃN NGỪA việc coi tất cả giá trị trong fuse aperture là OTP vật lý |
| Độ tin | **CAO** (quy tắc phân loại rõ ràng) |

## E15-15 — Sửa mâu thuẫn số unknown (nguồn sự thật)

| Trường | Giá trị |
|---|---|
| Source | `UNKNOWN_DATABASE.json` |
| Output | 45 items: 35 open, 10 resolved |
| Sửa | `MASTER_REPORT.md` cũ ghi "37 unknown (32 open, 5 resolved)" → **SAI**; `CHECKPOINT.json` cũ ghi "40/31/9" → **SAI** |
| Độ tin | **CAO** (đọc trực tiếp JSON) |

# FUSE_OTP_SOURCE_REPORT.md — CMP40HX / TU106 fuse & OTP source verification (PHASE16)

## 1. Lệnh chạy & đầu vào (read-only, offline)

Lệnh:
```
/usr/bin/python3 PHASE16/FUSE_SOURCE/fuse_source_verify.py > PHASE16/FUSE_SOURCE/fuse_source_verify_run.log 2>&1
```
Exit code: 0. Tất cả assert tự kiểm tra trong script đều pass.

Đầu vào (không sửa):
- `FUSE/fuse2.json` — sha256 `0e770041019aa3e4ac25733429589867a03c5542e83bc89f6937878c6e5c4ecc`, 55233 B
- `RAW_DATA/fuse2.json` — sha256 `0e770041019aa3e4ac25733429589867a03c5542e83bc89f6937878c6e5c4ecc`, 55233 B
- `FUSE/fuse_map.json`, `FUSE/fuse_bitfields.csv`, `PHASE15/FUSE_SEMANTICS.md`, `UNKNOWN_DATABASE.json`, `MMIO/registers_all.json`, `MMIO/registers_turing.json`
- Header nguồn: `/tmp/nvsrc/.../turing/tu102/dev_fuse.h` (sha256 `f96f637c...9fa30d`), `.../maxwell/gm107/dev_fuse.h` (sha256 `1b83b306...ca25c1`), ampere/ga100, blackwell/gb100, nvswitch/ls10

Hai dump JSON **byte-identical** (sha256 + md5 khớp, nội dung dict bằng nhau).

## 2. Chuẩn hóa offset / span / extent (mâu thuẫn đã tìm được)

| Trường | Giá trị |
|---|---|
| base (aperture thật) | `0x21000` |
| span khai báo | `0x8000` (32768 B) |
| Tổng word dump | 3072 (= 12288 B) |
| Offset min/max | `0x0000` / `0x2FFC` |
| Extent quan sát (thực tế dump) | `0x3000` bytes (12288 B) |
| Contiguous / gaps | Co / không có |
| 3072 word ≠ 7680 B | 3072 word = 12288 B, Không phải 7680 B |
| Báo cáo span cũ `0x1DFF` | **BỊ SOTO** bởi dữ liệu thật: max offset `0x2FFC`, không phải `0x1DFF` |

Phân biệt: extent quan sát (`0x3000` B, 3 trang 4 KB) < aperture/cell span khai báo (`0x8000` B). Trang `0x2000..0x2FFF` toàn poison `0xBADF1100` → kết luận fuse khối kết thúc trước `0x22000`, phần còn lại của span không được dump.

## 3. Phân loại tất cả 3072 word (xem `fuse_words.json` + `fuse_words.csv`)

Mỗi word có: absolute_address, offset, raw_value, classification, candidate_error_pattern, named_register/field (chỉ khi source exact / Turing family hỗ trợ), bitmask/field_value, source_path+line+hash, applicability, evidence_level. Không gán tên dựa trên trùng giá trị.

| Classification | Số word |
|---|---|
| DATA | 352 |
| ZERO | 518 |
| POISON | 2202 |
| Tổng | 3072 |

Poison khai báo vs thực:
- `0xBADF5040`: 410 lần (có trong dữ liệu)
- `0xBADF1100`: 1792 lần (có trong dữ liệu)
- `0xBADF1300`: **khai báo là poison nhưng không xuất hiện** (0 lần) → mâu thuẫn trong metadata

Candidate error pattern `BADF*`:
- `0xBADF510C`: 7 lần, trong cửa sổ dữ liệu tại offset `0x0178, 0x02D4, 0x04A8, 0x04AC, 0x04B0, 0x0578, 0x0E08` → **KHÔNG** phải poison ngoài cửa sổ, không coi là chứng minh khối OTP vật lý bị xóa.
- Tổng BADF família: 2209 (410 + 1792 + 7).

## 4. Register có tên + nguồn (chỉ áp khi exact / Turing family)

| Offset | Địa chỉ | Giá trị | Register (nguôn) | Field | Áp TU106 | Mức bằng chứng |
|---|---|---|---|---|---|---|
| `0x0378` | `0x021378` | `0x00000000` | `NV_FUSE_OPT_NVDEC_DISABLE` (turing/tu102/dev_fuse.h:31) | bits 2:0 = 0 | Áp được | DECODED |
| `0x074C` | `0x02174C` | `0x00000001` | `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS` (turing/tu102/dev_fuse.h:26) | bit 0 = 1 | Áp được | DECODED |
| `0x0C04` | `0x021C04` | `0x00000001` | `NV_FUSE_STATUS_OPT_DISPLAY` (maxwell/gm107/dev_fuse.h:27) | — | **Không áp** | UNKNOWN |

Lưu ý: NVDEC_DISABLE = 0 chỉ có nghĩa trường disable = 0, **không tự chứng minh** engine NVDEC đang hoạt động.

## 5. Quét header 0x21000..0x23fff (xem `source_evidence.json`, 7 mục)

| Kiến trúc | Địa chỉ | Register | Nguồn | Áp TU106 |
|---|---|---|---|---|
| TURING/tu102 | `0x21378` | NV_FUSE_OPT_NVDEC_DISABLE | tu102/dev_fuse.h:31 | Có |
| TURING/tu102 | `0x2174C` | NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS | tu102/dev_fuse.h:26 | Có |
| MAXWELL/gm107 | `0x21C04` | NV_FUSE_STATUS_OPT_DISPLAY | gm107/dev_fuse.h:27 | **Không** |
| NVSWITCH/ls10 | `0x21644` | NV_GPIO_RM_INTR_MSK_GPIO_LIST_1 | ls10/dev_pmgr.h:88 | **Không** |
| AMPERE/ga100 | `0x224FC` | NV_PTOP_DEVICE_INFO_CFG | ga100/dev_top.h:29 | **Không** |
| BLACKWELL/gb100 | `0x224FC` | NV_PTOP_DEVICE_INFO_CFG | gb100/dev_top.h:27 | **Không** |
| BLACKWELL/gb100 | `0x224FC` | NV_PTOP0_DEVICE_INFO_CFG | gb100/dev_top.h:52 | **Không** |

Chỉ 2 mục Turing/TU10x được áp cho fuse TU106. Maxwell/Ampere/Blackwell/NVSwitch là đối chiếu kiến trúc khác, **không đủ DECODED** cho TU106.

PDI: fuse `0x344/0x348` = `0x0000000000000000` khớp `nvidia-smi -q` (2 nguồn độc lập) → GPC/TPC/PDIstrap: PDI đã có nguồn thật (CORROBORATED); các field GPC/TPC/strap còn lại không có bitfield Turing → giữ UNKNOWN, không đọc lại NVML (archived-corroboration chỉ).

## 6. Đề nghị trạng thái U-FUSE-001..013 (xem `unknown_proposals.json`, 13 mục)

| ID | Hiện tại | Đề nghị | Lý do ngắn |
|---|---|---|---|
| U-FUSE-001 | open | INFERRED (giữ open) | 152 word chỉ bit0, 70 range rời rạc có gap → mảng enable flag, không phải OTP bit cell vật lý |
| U-FUSE-002 | open | BLOCKED (giữ open) | 8 word 0x718..0x734, 32 byte entropy cao, không cấu trúc; không bác hash do thử hữu hạn; không kết luận AES |
| U-FUSE-003 | open | UNKNOWN (giữ open) | 0xC0040000 ≠ NV_PMC_BOOT_0 → strap mirror bị suy, chưa có bitfield |
| U-FUSE-004 | open | INFERRED (giữ open) | 11 word 0xFFFFFFFC/0xFFFFFF8F, bit cao set, nghĩa bit chưa rõ |
| U-FUSE-005 | open | INFERRED (giữ open) | 0x0C1C=0x38 → 3 bit set = 3 GPC khớp TU106, nhưng chưa có bitfield nguồn |
| U-FUSE-006 | open | UNKNOWN (giữ open) | 0xBADF510C 7 lần trong dữ liệu, không trong danh sách poison; không xem BADF là chứng minh block OTP bị xóa |
| U-FUSE-007 | resolved | CORROBORATED (giữ resolved) | PDI khớp nvidia-smi, 2 nguồn độc lập |
| U-FUSE-008 | open | UNKNOWN (giữ open) | 155 word giá trị 1..7, không phải bitmask |
| U-FUSE-009 | resolved | **Đề nghị MỞ LẠI** → INSUFFICIENT_EVIDENCE | Dùng nguồn Maxwell gm107 (DATA_ENABLE=0) mà dữ liệu đọc là 1 (không nằm trong enum); không có Turing/TU106 fieldsource → không đủ DECODED |
| U-FUSE-010 | open | UNKNOWN (giữ open) | 0x0520=0x16480000 |
| U-FUSE-011 | open | UNKNOWN (giữ open) | 0x0D38=0xF0 |
| U-FUSE-012 | open | UNKNOWN (giữ open) | 0x0DC8..0x0DD0 = 0x7 x3 |
| U-FUSE-013 | resolved | DECODED (giữ resolved) | 0x820000 là GB100-only, không áp TU106 |

Nguyên則 지켜 được: không bác bỏ OTP cell do word =1 rời rác; không khẳng định 32B không phải hash do thử hữu hạn; không xem BADF là chứng minh block vật lý bị xóa.

## 7. Output artifacts (PHASE16/FUSE_SOURCE/, không chạm global CHECKPOINT/COORDINATION/UNKNOWN_DATABASE hay fw/GSP)

- `fuse_source_verify.py` — script stdlib, exit code 0
- `fuse_source_verify_run.log` — stdout + stderr + exit_code
- `fuse_words.json` — 3072 word, toàn trường phân loại
- `fuse_words.csv` — 3072 dòng, cùng trường
- `source_evidence.json` — 7 mục header 0x21000..0x23fff
- `unknown_proposals.json` — 13 đề nghị U-FUSE-001..013

## 8. Kết luận ngắn

Hai dump fuse khớp byte. Phân loại 3072 word: 352 DATA / 518 ZERO / 2202 POISON. Chỉ 2 register có nguồn Turing/TU10x chính xác (NVDEC_DISABLE=0, GSP_DEBUG_DIS=1). DISPLAY @0x21C04 chỉ có nguồn Maxwell → U-FUSE-009 đề nghị mở lại. Poison `0xBADF1300` khai báo nhưng không có trong dữ liệu. Báo span `0x1DFF` bị số據 thật bác (max offset `0x2FFC`, extent `0x3000` B). Tất cả unknown U-FUSE-001..013 giữ rõ trạng thái, không đưa kết luận vượt quá bằng chứng.

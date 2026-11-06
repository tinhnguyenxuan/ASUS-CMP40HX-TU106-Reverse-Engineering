# PHASE15/NEW_DISCOVERIES.md — Danh sách phát hiện mới trong Phase 15

Tất cả phát hiện dưới đây là **offline, read-only**, không chạm card, không ghi MMIO/OTP, không flash.

## FUSE/OTP (P0)

| ID | Phát hiện | Bý túc | Confidence |
|---|---|---|---|
| D-P15-001 | 352 word data có 126 distinct giá trị; 3 mã poison (`0xBADF5040`, `0xBADF1300`, `0xBADF1100`) | PHASE15/fuse_analysis.json | CAO (tái lập từ dump) |
| D-P15-002 | 152 word =1 phân tán 70 range, không phải mảng OTP liên tiếp → INFERRED enable flag/version, không phải OTP bit cell | FUSE_SEMANTICS.md §4 | TRUNG BÌNH |
| D-P15-003 | fuse `+0x0718` = 32 byte entropy cao, không phải hash PDI (đã exhaustive search 0 khớp); 4 giả thuyết mới | FUSE_SEMANTICS.md §5 | UNKNOWN |
| D-P15-004 | `0xBADF510C` xuất hiện trong vùng có dữ liệu (7 lần) → ô fuse bị khóa, không phải lỗi bus | FUSE_SEMANTICS.md §6 | TRUNG BÌNH |

## GSP-RM (P1)

| ID | Phát hiện | Bý túc | Confidence |
|---|---|---|---|
| D-P15-005 | Dispatcher @`0x04F575FC`; layout entry 5 trường (u16@0, u32@4, u8@8, u64@0x10, u16@0x18), stride 32, span 0x1740 | GSP_DISPATCH_ANALYSIS.md | CAO (đọc từ code) |
| D-P15-006 | `u64@+0x10` là tham số callback (qua `a2`), KHÔNG phải name_ptr; `u16@+0x18` = `{group:8,subtype:8}` | GSP_DISPATCH_ANALYSIS.md | CAO |
| D-P15-007 | 4 giả thuyết về `u64@+0x10` đều bị bác bỏ có bằng chứng | GSP_DISPATCH_ANALYSIS.md §7 | CAO |

## Firmware (P2)

| ID | Phát hiện | Bý túc | Confidence |
|---|---|---|---|
| D-P15-008 | 11 blob: 4 entropy 7.998 (không nén được, không phân biệt AES/nén), 6 plaintext (~5 nội dung duy nhất) | EVIDENCE_LEDGER.md E09 | CAO |

## VBIOS (P3)

| ID | Phát hiện | Bý túc | Confidence |
|---|---|---|---|
| D-P15-009 | Key block 38 record × 32 B layout giải được; `f4` không phải timestamp, hash không khớp vùng nào | (cần viết VBIOS_UNKNOWN_FIELDS.md) | TRUNG BÌNH |

## MMIO/Topology (P4)

| ID | Phát hiện | Bý túc | Confidence |
|---|---|---|---|
| D-P15-010 | Poison codes BAR0: `0xBADF5040/1300/1100/1301/510C/0000`, `0xBAD00100` (25 trang), `0xFFFFFFFF` (72 trang) | COVERAGE.md §9.4 | CAO |

---
**Ponytail:** mỗi phát hiện có bằng chứng trong file tham chiếu. Thêm phát hiện mới khi vòng SELECT UNKNOWN → VERIFY tạo ra bằng chứng bổ sung.

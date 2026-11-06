# PHASE15/VBIOS_UNKNOWN_FIELDS.md — 5 field chưa biết trong key block VBIOS

## 1. Mục tiêu

Giải nghĩa các field chưa biết trong bảng record 32 byte (key block) tại `0x003000..0x0034BF`, 38 record, và 12 digest NPDS type-0x70.

## 2. Dữ liệu gốc

| Trường | Giá trị |
|---|---|
| Source | `VBIOS/P2_VBIOS.md`, `VBIOS/vbios_crossrefs.json`, `TOOLS/nvgi_block.py` |
| Vị trí key block | `0x003000..0x0034BF` (image #1), `0x07C000..` toàn `0xFF` (image #2) |
| Số record | 38 × 32 byte = 1,216 byte |
| Digest NPDS-0x70 | 12 × 32 byte tại `0x076800..0x078400` |

## 3. Layout record 32 byte (GIẢI ĐƯỢC layout, chưa giải nghĩa field)

| Offset | Size | Field | Giá trị mẫu | Trạng thái |
|---|---|---|---|---|
| `+0x00` | 2 | `sig` | `0x6700` (37 record), `0x6701` (1 record) | **UNKNOWN** — nghĩa sig? |
| `+0x02` | 2 | `ver` | `0x0200/0x0300/0x0400/0x0600` | **UNKNOWN** — version/build? |
| `+0x04` | 4 | `f4` | Bội số `0x20` (38/38), max `0xF9FC88A0` | **UNKNOWN** — không phải timestamp (9/38 hợp lý, 29 record 1972–2102) |
| `+0x08` | 4 | `f8` | `0x1669xxxx/0x166axxxx/0x166bxxxx/0x1687dxxx` | **UNKNOWN** — 10 nhóm, tăng dần theo ver |
| `+0x0C` | 4 | `flags` | byte thấp `{0xFF,0xFC,0xF8,0xF0,0xF3}`, byte cao `{0x00,0x79}` | **UNKNOWN** |
| `+0x10` | 16 | `hash` | 16 byte entropy cao, không trùng lặp | **UNKNOWN** — của cái gì? |

## 4. Mẫu record thực

```
#0  0x3000 ver=0x0200 f4=0xEE2DD2C0 f8=0x16692CC5 flags=0x000000FF hash=9C0CAA10345BAAC1BCA3876844D552D4
#2  0x3040 ver=0x0300 f4=0xC49BDF40 f8=0x166AB5B7 flags=0x007900F8 hash=39BC9EE7002D4AE2A7A39806BD1224C1
#34 0x3440 ver=0x0600 f4=0xC96BD9E0 f8=0x1687D040 flags=0x007900F8 hash=A892787FBF8EF50C73DEDAFACA3D50BC
```

## 5. Giả thuyết đã bị bác bỏ (có bằng chứng)

| Giả thuyết | Bằng chứng bác bỏ |
|---|---|
| `f4` là unix timestamp | Chỉ 9/38 trong dải 2000–2030; 29 record rơi vào 1972–2102 (vô lý) |
| `hash` là SHA-256/MD5/SHA-1 của vùng ROM | 0/912 phép thử khớp (6 vùng × 4 thuật toán × 38 record) |
| `hash` là SHA-256 của chính record (loại trừ 16 byte hash) | Không khớp (đã thử) |

## 6. Field chưa biết (UNKNOWN)

### 6.1 `sig` (`+0x00`)
- `0x6700` × 37 record, `0x6701` × 1 record (record đặc biệt, đang ở cuối hoặc đầu bảng).
- **Confidence:** UNKNOWN.

### 6.2 `ver` (`+0x02`)
- `0x0200` × 2, `0x0300` × 16, `0x0400` × 16, `0x0600` × 4.
- `f8` tăng dần theo `ver` → nghi là **version/build ID** của record.
- **Confidence:** INFERRED (version ID), chưa chứng minh.

### 6.3 `f4` (`+0x04`)
- Bội số `0x20` ở 38/38 record.
- Nghi là **checksum 27-bit dịch trái** hoặc **hash rút gọn**.
- **Confidence:** INFERRED (checksum), chưa chứng minh.

### 6.4 `f8` (`+0x08`)
- Cùng họ `0x166xxxxx`, tăng dần theo `ver`.
- Nghi **version/build ID** cấp cao hơn `ver`.
- **Confidence:** INFERRED.

### 6.5 `flags` (`+0x0C`)
- Byte thấp trùng họ màu `0xF0–0xFF` với fuse `0x00D4..0x00F4` (`0xFFFFFFFC`, `0xFFFFFF8F`).
- **Liên hệ chưa chứng minh** — ghi nhận trùng hợp, không kết luận.
- **Confidence:** UNKNOWN.

### 6.6 `hash` (`+0x10`, 16 byte)
- Entropy cao, không trùng lặp giữa các record.
- 0/912 phép thử khớp với hash vùng ROM.
- **Confidence:** UNKNOWN.

## 7. NPDS type-0x70 — 12 digest (UNKNOWN)

| Trường | Giá trị |
|---|---|
| Vị trí | `0x076800..0x078400` |
| Số digest | 12 × 32 byte |
| Thử khớp | 0 / 1,365,939 phép thử trên toàn ROM |
| **Confidence:** | UNKNOWN — không biết hàm băm, không biết đầu vào |

## 8. Kết luận

- Layout record **đã giải** (5 field, kích thước rõ ràng).
- **5/6 field chưa biết nghĩa** (chỉ `sig` có thể nhận biết là signature từ giá trị).
- Không đặt tên field nào (giữ `f4`, `f8` trung tính) để tránh sai sự thật.
- **Cần:** ROM TU106 khác để đối chiếu pattern `f4`/`f8`/`hash` (nếu cùng pattern → cấu trúc chuẩn TU106).

---
**Ponytail:** không brute-force hash, không đặt tên speculative. Thêm field mới khi có ROM đối chứng.

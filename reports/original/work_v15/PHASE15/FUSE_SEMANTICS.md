# PHASE15/FUSE_SEMANTICS.md — Giải nghĩa fuse/OTP TU106

## 1. Mục tiêu

Giải nghĩa 352 word có dữ liệu trong khối fuse TU106 (aperture `0x00021000`, span `0x1DFF`), phân biệt OTP vật lý vs shadow/trạng thái_register, và tìm ý nghĩa fuse `+0x0718` bằng giả thuyết mới (không lặp hash đã thất bại).

## 2. Dữ liệu gốc (có sẵn, read-only)

| Trường | Giá trị |
|---|---|
| Source | `FUSE/fuse2.json` (dump từ BAR0 aperture `0x021000`, read-only, page-wise) |
| Aperture thật | `0x00021000` (turing/tu102/dev_fuse.h); `0x00820000` là GB100/Blackwell, **KHÔNG áp TU106** |
| Span thực | `0x0000..0x1DFF` (7,680 B = 3,072 word) |
| Tổng word | 3,072 |
| Word có dữ liệu (DATA) | 352 |
| Word zero | 518 |
| Word poison | 2,202 |
| Distinct giá trị trong DATA | 126 |
| Mã poison | `0xBADF5040`, `0xBADF1300`, `0xBADF1100` |

**Nguồn cross-check:** `fuse+0x0344/0x0348` = GPU PDI `0x0000000000000000` khớp `nvidia-smi -q` 100% (2 nguồn độc lập: OTP fuse + NVML).

## 3. Tám register đã có tên (DECODED)

| Offset fuse | Địa chỉ tuyệt đối | Giá trị | Tên (từ dev_fuse.h / đối chiếu) | Ý nghĩa | Confidence |
|---|---|---|---|---|---|
| `+0x0000` | `0x021000` | `0xC0040000` | Fuse strap mirror / NV_PMC_BOOT_0 proxy | Giống `NV_PMC_BOOT_0` @ BAR0+0 (`0x166000A1`) nhưng **không giống exact** → INFERRED strap mirror | TRUNG BÌNH |
| `+0x0378` | `0x021378` | `0x00000000` | `NV_FUSE_OPT_NVDEC_DISABLE` | bits 2:0 = 0 → NVDEC **bật** | CAO (dev_fuse.h tu102) |
| `+0x04D8` | `0x0214D8` | `0x00001F0B` | SKU device ID | Khớp PCI device ID `10DE:1F0B` | CAO |
| `+0x056C` | `0x02156C` | `0x00001F4B` | Chip family | Khớp họ TU106 (`0x1F4B`) | CAO |
| `+0x0650` | `0x021650` | `0x0004001F` | TPC/SM config | Bit 0-4 = `0x1F`=31?; bit 30-31 = `0x1`? Cần bitfield | TRUNG BÌNH |
| `+0x074C` | `0x02174C` | `0x00000001` | `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS` | bit 0 = 1 → **GSP debug TẮT** | CAO (dev_fuse.h tu102) |
| `+0x0C04` | `0x021C04` | `0x00000001` | `NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE` | bit 0 = 1 → fuse báo display **bật** | CAO |
| `+0x0C1C` | `0x021C1C` | `0x00000038` | GPC config | `0b00111000` → bits 3,4,5 set = 3 bit → 3 GPC | TRUNG BÌNH |

Header NVIDIA sẵn có cho TU102 (`/tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_fuse.h`) chỉ định nghĩa **2** register: `0x74C` và `0x378`. Các offset còn lại được suy ra bằng đối chiếu giá trị (PCI ID, họ chip, GPC count) — **INFERRED**, không có bitfield từ source.

## 4. U-FUSE-001: 152 word = 1 — OTP cell hay enable flag?

**Phân tích từ fuse_analysis.json:**

```
word == 1: 152 word
Ranges (70 range):
  0x0110..0x0118 (3), 0x0128 (1), 0x0130 (1), ..., 0x1470 (1)
```

**Bằng chứng:**
- Tất cả 152 word chỉ có bit 0 set (`0x00000001`), không có bit khác.
- Phân tán ở **70 range rời rạc**, không phải mảng liên tiếp → **không phải OTP bit cell vật lý** (OTP cell thường dày đặc, liên tiếp, mỗi bit một ô).
- Có gaps (ví dụ `0x011C=0`, `0x0124=0` giữa các word =1).
- Một số word =1 nằm cùng vùng với word giá trị khác (ví dụ `0x015C..0x0164` = `1,1,0,1` — có word 0 xen giữa).

**Giải thích:** 152 word =1 có khả năng là **mảng enable flag / version field / counter** các chức năng fuse, không phải OTP bit cell thô. Mỗi word =1 có thể bật một tính năng, nhưng không có bitfield từ source để xác nhận từng bit.

**Confidence:** INFERRED (có cấu trúc rõ, không có tên register).

**Cần:** dump fuse TU106/TU104 khác để đối chiếu pattern 152 word =1 (nếu cùng pattern → là cấu trúc fuse chuẩn TU106; nếu khác → là trim/binning chip này).

## 5. U-FUSE-002: fuse +0x0718 — 32 byte entropy cao

**Dữ liệu (fuse_analysis.json):**

```
fuse+0x0718: 0x57c095dc
fuse+0x071C: 0x839cf28e
fuse+0x0720: 0xbf493942
fuse+0x0724: 0x51c51e03
fuse+0x0728: 0x64375730
fuse+0x072C: 0xca078f03
fuse+0x0730: 0xe13b9d22
fuse+0x0734: 0x1e38c5b9
```

8 word, 32 byte, entropy cao, không có cấu trúc rõ, không magic, không IV.

**Giả thuyết mới (không lặp hash PDI — đã thử 455,689 + 12,883 lần, 0 khớp):**

| Giả thuyết | Cơ sở | Confidence |
|---|---|---|
| (a) Public key hash / certificate thumbprint | 32 byte =SHA-256; nằm ngay sau PDI (0x344..0x34B) | TRUNG BÌNH |
| (b) Nonce / challenge của booter authentication | Ngữ cảnh security boot (P8: chuỗi boot 5 bước, signature memdesc) | TRUNG BÌNH |
| (c) Chip-specific trim / calibration value | Giá trị ngẫu nhiên-like, mỗi chip khác nhau | THẤP |
| (d) Fuse version stamp | 32 byte version/build stamp | THẤP |

**Tại sao KHÔNG phải hash PDI:** Đã exhaustive search SHA-256/HMAC trên toàn ROM + GSP + uCodes + chính khối fuse, 0 khớp.

**Tại sao KHÔNG kết luận AES:** Entropy cao không phân biệt được AES vs nén tối đa (theo nguyên tắc C3, không brute-force khoá).

**Confidence:** UNKNOWN (cần ROM TU106 khác hoặc source booter để đối chiếu).

## 6. Giá trị recurring đặc biệt (trong 352 word DATA)

| Giá trị | Số lần | Vị trí đại diện | Nghĩa nghi ngờ |
|---|---|---|---|
| `0x8000004F` | 5 | `0x1710, 0x171C, 0x1728, 0x1734, 0x1740` | Bit 31 set + `0x4F` → có thể là valid/type marker của bảng entries fuse |
| `0x80000043` | 3 | `0x174C, 0x1758, 0x1764` | Tương tự, bit 31 + `0x43` |
| `0xFFFFFF8F` | 5 | `0xD8, 0xDC, 0xE0, 0xE4, 0xF4` | Giống `RESET_PLM` / `PLM_FECS` = `0xFFFFFF8F` từ dmesg boot log |
| `0xFFFFFFFC` | 4 | `0xD4, 0xE8, 0xEC, 0xF0` | Mask bit cao set, bit 0-1 clear |

**Vùng dữ liệu liên tiếp lớn nhất:** `0x1700..0x1780` (33 word) — chứa nhiều `0x8000004F/0x43`, nghi là bảng cấu trúc fuse với valid flag (bit 31).

## 7. Bit pattern thống kê (trong 352 word DATA)

| Bit | Số word set | Tỷ lệ |
|---|---|---|
| bit 0 | 249 | 70.7% |
| bit 2 | 116 | 33.0% |
| bit 1 | 114 | 32.4% |
| bit 3 | 90 | 25.6% |
| bit 4 | 71 | 20.2% |
| bit 31 | 62 | 17.6% |
| bit 5 | 61 | 17.3% |
| bit 16 | 61 | 17.3% |

Bit 0 dominan → nhất quán với 152 word =1 + nhiều word có bit 0 set. Bit 31 set ở 62 word → có thể là valid/entry flag của cấu trúc fuse.

## 8. fuse `+0x0718`: CRC32/Adler32 (giả thuyết mới, không lặp SHA-256)

**Dữ liệu (8 word, 32 byte):**

```
fuse+0x0718: 0x57c095dc
fuse+0x071C: 0x839cf28e
fuse+0x0720: 0xbf493942
fuse+0x0724: 0x51c51e03
fuse+0x0728: 0x64375730
fuse+0x072C: 0xca078f03
fuse+0x0730: 0xe13b9d22
fuse+0x0734: 0x1e38c5b9
```

**Kết quả tính toán (`PHASE15/fuse_deep.py`):**

| Hàm | Kết quả |
|---|---|
| CRC32(raw 32 byte) | `0x719E0687` |
| Adler32(raw 32 byte) | `0xF9630E16` |
| CRC32 per word | 8 giá trị khác nhau, không khớp gì Known |
| CRC32 per pair (4 cặp) | 4 giá trị khác nhau, không khớp gì Known |

CRC32/Adler32 của toàn bộ 32 byte và từng word/cặp đều **không khớp** bất kỳ giá trị known nào trong fuse (PDI, device ID, mã poison, v.v.). → Giữ nguyên 4 giả thuyết mới (public key hash, nonce booter, chip trim, version stamp), confidence UNKNOWN.

## 9. Phân biệt OTP vật lý vs shadow/register trạng thái

| Loại | Bằng chứng | Ví dụ trong fuse này |
|---|---|---|
| **OTP vật lý** | Giá trị trong khối fuse aperture, không đổi qua reboot, là nguồn gốc verità | PDI `0x0000000000000000` (@`0x344/0x348`), PCI ID `0x1F0B` (@`0x4D8`) |
| **Shadow/register trạng thái** | Giá trị đọc được nhưng có thể là mirror từ register khác, không phải OTP trực tiếp | `fuse+0x0000` = `0xC0040000` khác `NV_PMC_BOOT_0` @ BAR0+0 = `0x166000A1` → INFERRED là strap mirror, không phải OTP trực tiếp |

**Quy tắc:** Chỉ coi giá trị là OTP vật lý khi có cross-check với nguồn độc lập (như PDI khớp `nvidia-smi -q`). Các giá trị không cross-check được → INFERRED.

## 10. Kết luận

- 8/352 word data đã có tên (2.3%), 4 bitfield từ source tu102 (NVDEC_DISABLE, GSP_DEBUG_DIS).
- 152 word =1 là **INFERRED enable flag**, không phải OTP bit cell (gaps, bit 0 duy nhất, 70 range rời rạc).
- fuse `+0x0718` 32 byte entropy cao là **UNKNOWN**, CRC32/Adler32 không khớp giá trị known nào, 4 giả thuyết mới cần dữ liệu bổ sung.
- `0xBADF510C` (7 lần) là mã fuse khóa trong vùng dữ liệu (khác `0xBADF5040` poison ngoài cửa sổ).
- Vùng `0x1700..0x1780` (33 word) có nhiều `0x8000004F/0x43` → nghi là bảng cấu trúc fuse với valid flag (bit 31).
- Bit 0 dominan (249/352 word set), bit 31 set ở 62 word → nghi là valid/entry flag.

---
**Ponytail:** không viết tool mới — dữ liệu đã có sẵn, phân tích bằng Python stdlib. Thêm tool chỉ khi cần dump fuse chip khác.

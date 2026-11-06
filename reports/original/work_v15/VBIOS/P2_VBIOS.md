# P2 — VBIOS REVERSE ENGINEERING TOÀN PHẦN (TU106 CMP 40HX)

Trạng thái: **ĐẠT** — 2 cấu trúc mới giải được, 1 giả thuyết cũ bị bác bỏ.
Bằng chứng: `VBIOS/vbios_crossrefs.json`, `TOOLS/nvgi_block.py`.

---

## 1. PHÁT HIỆN #1 — ROM 1 MiB KHÔNG phải "bank1 + bank2 khác nhau"

Báo cáo trước kết luận "2 bank, bank1 660,992 B, bank2 387,584 B, giống hệt
100%". **SAI SỐ ĐO.**

Đo lại toàn bộ (MEASURED, `TOOLS/nvgi_block.py`):

```
ban 1: 0x000000..0x079000  (495,616 B)
ban 2: 0x079000..0x0F2000  (495,616 B)
byte khac: 1,212 / 495,616 = 0.245%
cum khac: DUY NHAT 0x3000..0x34BF (1,216 B)
sau 0x0F2000: 57,344 B, khong phai toan 0xFF (51,523 byte FF + 5,201 byte 00)
```

### 1.1 Cấu trúc thật

| Vùng | Kích thước | Nội dung |
|---|---:|---|
| `0x000000..0x079000` | 495,616 B | **image #1** (= payload T4) |
| `0x079000..0x0F2000` | 495,616 B | **image #2** — bản sao y hệt, trừ 1 vùng |
| `0x0F2000..0x100000` | 57,344 B | NMX container (`RIBILU`, `PPID`, `G001.0000.02.04`, `Generic`) |

**Bác bỏ** kết luận cũ "bank1 660,992 B". Ranh giới thật là **`0x79000`**, và
`0x79000` là magic `NVGIf` **của image #2**, không phải container khác loại.

### 1.2 Vì sao có 1,216 byte khác

Vùng `0x3000..0x34BF` chứa **bảng record khoá/chứng chỉ**:
- image #1: 38 record có dữ liệu.
- image #2: **toàn `0xFF`** (0/38 record).

Nghĩa là: **image #1 đã được ký/đăng ký, image #2 để trống**. Đây không phải
"hai bản sao dư thừa" mà là **một bản đã kích hoạt + một bản chưa**.

Độ tin: **CAO** (đo trực tiếp, đếm chính xác).

---

## 2. PHÁT HIỆN #2 — Cấu trúc RECORD 32 BYTE trong NVGI key block

Vị trí: `0x003000..0x0034BF`, **38 record × 32 byte = 1,216 byte chính xác**.

### 2.1 Layout đã giải mã (DECODED)

```
offset  size  field            ghi chu
+0x00   2     sig              0x6700 (37 record) / 0x6701 (1 record)
+0x02   2     ver              0x0200 / 0x0300 / 0x0400 / 0x0600
+0x04   4     f4               luon la boi so cua 0x20 (38/38)
+0x08   4     f8               0x1669xxxx / 0x166axxxx / 0x166bxxxx / 0x1687dxxx
+0x0C   4     flags            byte thap ∈ {0xFF,0xFC,0xF8,0xF0,0xF3},
                                byte cao ∈ {0x00, 0x79}
+0x10   16    hash             16 byte entropy cao, khong trung lap
```

Mẫu thật:

```
#0  0x3000 ver=0x0200 f4=0xEE2DD2C0 f8=0x16692CC5 flags=0x000000FF hash=9C0CAA10345BAAC1BCA3876844D552D4
#2  0x3040 ver=0x0300 f4=0xC49BDF40 f8=0x166AB5B7 flags=0x007900F8 hash=39BC9EE7002D4AE2A7A39806BD1224C1
#34 0x3440 ver=0x0600 f4=0xC96BD9E0 f8=0x1687D040 flags=0x007900F8 hash=A892787FBF8EF50C73DEDAFACA3D50BC
```

### 2.2 Phân bố (MEASURED)

| ver | Số record | `f8` (nhóm) |
|---|---:|---|
| `0x0200` | 2 | `0x16692CC5`, `0x16692CC6` |
| `0x0300` | 16 | `0x166AB5B7/B8`, `0x166B07DF/E0`, `0x166B08E9`, `0x166B0A76` |
| `0x0400` | 16 | `0x166B1BC1`, `0x166B4533`, `0x166B457E` |
| `0x0600` | 4 | `0x1687D040`, `0x1687D041` |

`f8` chia thành **10 giá trị nhóm**, mỗi nhóm 1–4 record. `ver` tăng theo nhóm.

### 2.3 Giả thuyết đã bị bác bỏ

| Giả thuyết | Bằng chứng bác bỏ |
|---|---|
| `f4` là **unix timestamp** | Chỉ **9/38** trong dải 2000..2030; 29 record rơi vào 1972–2102 vô lý |
| `hash` là SHA-256/MD5/SHA-1 của vùng ROM | **0/912 phép thử** khớp (6 vùng × 4 thuật toán × 38 record) |
| image #2 là "bank dự phòng giống hệt" | Khác **1,216 B** — vùng record toàn `0xFF` |

### 2.4 Còn UNKNOWN

- `sig 0x6700` nghĩa là gì? (`0x6701` chỉ 1 record — đặc biệt)
- `f4` là gì? Không phải timestamp, không phải offset (max `0xF9FC88A0` >
  kích thước file). **Bội số `0x20` ở 38/38 record** — nghi là checksum 27-bit
  dịch trái, hoặc hash rút gọn.
- `f8` là gì? Cùng họ `0x166xxxxx`, tăng dần theo `ver`. Nghi **version/build ID**.
- 16 byte hash: của cái gì?
- `flags` byte thấp trùng họ màu `0xF0-0xFF` với fuse `0x00D4..0x00F4`
  (`0xFFFFFFFC`, `0xFFFFFF8F`) — **liên hệ chưa chứng minh**, ghi nhận trùng hợp.

Không đặt tên field nào. Giữ nguyên `f4`, `f8` như khoá trung tính.

---

## 3. PHÁT HIỆN #3 — NMX container ở tail (đã biết một phần)

`0x0F2000..0x100000` (57,344 B): 51,523 byte `0xFF`, 5,201 byte `0x00`,
7 string ASCII:

```
RIBILU
G001.0000.02.04     (x2)
Generic             (x2)
PPIDCMP40HX-8G#REDACTED   (x2)
```

Đã phân tích ở phiên trước (`NPDE`, `PPID`, `IMG`, `OBD`). Không lặp lại.

---

## 4. Cross-reference graph các bảng

```
NVGIf #1 @0x000000
  ├─ PCI ROM header          @0x0000
  ├─ NVGI key block          @0x003000..0x0034BF   [38 record, MỚI GIẢI]
  ├─ legacy x86 image        @0x028600..0x037A00   checksum 0x00
  ├─ EFI image               @0x037A00..0x048A00   checksum 0x00
  ├─ NPDS type-0xE0 #1       @0x048A00..0x054000   checksum 0x00
  ├─ NPDS type-0xE0 #2       @0x054000..0x076800   checksum 0x00
  │    └─ VFE @0x05649C (150 slot × 24 B, 20 var × 25 B)
  │         └─ selector @0x2D384 = REL/ALT/OV/BOOT/VMIN
  ├─ NPDS type-0x70          @0x076800..0x078400   checksum 0x00 (12 digest)
  └─ padding 0xFF            @0x078400..0x079000

NVGIf #2 @0x079000   <- ban sao, key block @0x7C000 TOAN 0xFF

NMX container @0x0F2000..0x100000
  └─ PPID / IMG / OBD / RIBILU / JFFS / GXIP / OEMP
```

---

## 5. Trạng thái P2

| Mục đề bài | Trạng thái |
|---|---|
| A. Parse toàn ROM gốc (không chỉ payload) | **ĐẠT** — 1,048,576 B |
| B. Giải mã image header / pointer / checksum / metadata | **ĐẠT MỘT PHẦN** — 9 image + key block 38 record |
| C. Phân tích bank thứ hai + NVGIf chưa giải | **ĐẠT** — xác định là bản sao, khác 1,216 B |
| D. Với mỗi table: ver/off/len/count/stride/fields/refs | **ĐẠT MỘT PHẦN** — 40 bảng PERF + VFE + key block |
| E. Tìm byte/bit parser chưa giải thích | **ĐẠT** — 5 field UNKNOWN trong key block |
| F. Cross-reference graph | **ĐẠT** — mục 4 |
| G. Board identity / memory / boot / straps / feature flags | **ĐẠT MỘT PHẦN** — PPID, IMG, OBD |
| H. So sánh ROM TU106 công khai | **KHÔNG LÀM** — không có ROM TU106 khác trong tay |
| I. Cải thiện parser hỗ trợ unknown/malformed/version khác | **ĐẠT** — parser chấp nhận mọi ver, giữ field chưa biết |
| J. Test cho từng table decoder | **ĐẠT** — `scripts/test_parser.py` 7/7 PASS |

**Coverage P2:**
- Byte ROM: **1,048,576 / 1,048,576** đã phân vùng (**100%**)
- Bảng có cấu trúc giải được: **42** (40 PERF + VFE + key block)
- Field UNKNOWN còn lại: **5** (trong key block) + 12 digest NPDS-0x70
- Byte chưa giải nghĩa nghĩa: phần NMX container nội bộ + hash trong key block

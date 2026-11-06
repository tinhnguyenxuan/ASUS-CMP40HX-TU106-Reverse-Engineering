# BÁO CÁO 3 NHIỆM VỤ PHÂN TÍCH CHUYÊN SÂU — CMP 40HX

Tiếp nối `BAO_CAO_CMP40HX_03-11-2026.md`
Ngày: 03/11/2026

---

## SỬA LỖI NGHIÊM TRỌNG PHÁT HIỆN ĐƯỢC

Trước khi vào kết quả, **2 lỗi của báo cáo trước** phải đính chính:

### Lỗi 1: offset payload
Báo cáo trước ghi *"payload = `rom[0x28600:0x79000]`"*. **SAI.**

```
payload = rom[0x00000:0x79000]    (495,616 B)
```
Bằng chứng: so `CMP40HX_T2_payload.bin` với `rom[0:0x79000]` → khác **đúng 19 byte** (_số 43 ở bản nháp là đếm sai, đã sửa_)
(toàn bộ nằm trong `0x566a0`…`0x57FD0` + 1 byte checksum `0x767FF`, không sai một byte nào ngoài đó).
So với `rom[0x28600:+495616]` → khác **481,992 byte**.

Hệ quả: mọi so sánh offset VFE với payload trước đây đều lệch `0x28600`.

### Lỗi 2: VFE_VAR stride
Báo cáo trước (và `deep_analysis.py` bản đầu) dùng **stride 20** → float ra rác.

Header `@0x5649C` = `30 09 19 14 18`:
```
ver  = 0x30
hdr  = 0x09  = 9
esz  = 0x19  = 25      <-- KHONG phai 20
cnt  = 0x14  = 20
9 + 25*20 = 509 = dung span (0x56699 - 0x5649C)
```
Stride **25**, không phải 20.

---

## NHIỆM VỤ 1: 40 BẢNG PERF_PTRS

### 1.1 Bảng tổng hợp đầy đủ (40 entry, chạy `perf_tables.py`)

```
  #      ROM   ver  hdr  esz  cnt   size   header 20B
  0 0x054155 0x60   10    5    7     45   60 0a 05 07 06 0a 01 07 00 01 07 00 00 00 ff 85 02 2c 41 a1
  1 0x054600 0x11   26   60   33   2006   11 1a 3c 21 0a 07 00 40 00 00 00 00 00 00 00 00 f7 72 00 00
  2 0x0550c4 0x20    6   74   12    894   20 06 4a 0c 00 3c 4e d2 68 1a 98 82 06 45 00 09 1b 77 4c 20
  5 0x058723 0x10    4    3   18     58   10 04 03 12 01 00 00 02 00 00 02 01 00 02 02 00 00 03 00 00
  8 0x05649c 0x30    9   25   20    509   30 09 19 14 18 96 c8 0f 28 04 00 00 00 00 00 00 fe 42 11 14
 10 0x0579e0 0x20    8   49    7    351   20 08 31 07 00 00 00 00 03 00 00 00 00 31 20 30 00 d4 02 f6
 11 0x057e92 0x30   44   66   20   1364   30 2c 42 14 14 00 14 00 0e 0f 02 ff ff ff 00 00 00 00 00 00
 14 0x054326 0x20   19    1   17     36   20 13 01 11 04 0a 00 02 01 ff ff ff ff ff ff ff ff ff ff 0f
 15 0x057b3f 0x20    6   22   20    446   20 06 16 14 1b 0f 02 df 00 1b b7 00 00 10 00 00 00 00 00 00
 16 0x058561 0x10    5   25   11    280   10 05 19 0b 00 05 a2 0f 96 07 5c 03 00 00 b0 08 00 00 72 10
 17 0x0545f2 0x10   14   70  183  12824   10 0e 46 b7 09 28 6c 02 00 1d 5a 1e 1e 4b 11 1a 3c 21 0a 07
 18 0x05875d 0x10    9    5   32    169   10 09 05 20 00 01 ff ff ff 01 00 05 00 c1 01 00 06 01 01 01
 19 0x058806 0x10    4    5    2     14   10 04 05 02 00 00 01 00 00 01 00 01 00 00 10 04 02 06 03 00
 20 0x058679 0x10   10   40    4    170   10 0a 28 04 ff ff ff c0 01 00 01 00 20 0b 20 0b 20 0b c8 00
 22 0x058824 0x10    6   26    2     58   10 06 1a 02 00 01 02 00 24 64 3d 02 00 10 00 00 09 a8 61 00
 23 0x05885e 0x10    6   54    2    114   10 06 36 02 00 01 01 01 00 c8 00 62 00 9e ff 23 2b 0a 01 00
 25 0x0588d0 0x10    4    5    2     14   10 04 05 02 01 00 0a 10 27 01 01 0a 10 27 10 06 05 02 05 02
 26 0x02d37b 0x10    5   14    1     19   10 05 0e 01 00 00 35 0c 00 00 01 03 00 02 04 ff 01 10 03 10
 27 0x02d317 0x10    4   24    4    100   10 04 18 04 02 00 80 00 b8 4c 0a ff e0 93 04 00 20 d6 13 00
 28 0x02d38e 0x10    5   17    1     22   10 05 11 01 00 01 00 00 ff ff 00 00 00 00 00 00 00 00 00 00
 29 0x056222 0x10    6    7    5     41   10 06 07 05 f4 01 00 00 00 00 00 00 00 01 01 01 01 01 ff 01
 30 0x05624b 0x10    5   12    5     65   10 05 0c 05 00 ff fd ff ff fa 48 1f fd fb 9f f8 ff 01 f9 ff
 31 0x05628c 0x10    4   13    5     69   10 04 0d 05 00 00 00 00 0b 0b 0b 0b 00 00 00 fc 00 00 00 00
 32 0x0562d1 0x10   10    5    5     35   10 0a 05 05 00 58 1b 01 00 01 e7 ff ff ff 01 e7 ff ff ff 01
 33 0x0562f4 0x10    7   15    5     82   10 07 0f 05 00 0a 00 ed ff ff ff a1 06 ff ff 02 64 00 b4 00
 34 0x056346 0x10   14    5    5     39   10 0e 05 05 ff 58 1b ff ff ff ff ff ff ff 00 fc ff ff 00 00
 35 0x05636d 0x10   58    5    5     83   10 3a 05 05 ff 00 e4 0c 88 13 0e 00 00 00 10 00 00 00 00 00
 36 0x0563dc 0x30    9    4    2     17   30 09 04 02 c8 00 c8 00 01 02 00 00 0f 00 00 00 0f 10 06 18
 37 0x058814 0x10    4    2    6     16   10 04 02 06 03 00 ff 00 ff 00 ff 00 ff 00 ff 00 10 06 1a 02
 38 0x0588de 0x10    6    5    2     16   10 06 05 02 05 02 01 00 00 00 00 00 00 00 00 00 00 00 00 00
 39 0x0563ed 0x10    6   24    5    126   10 06 18 05 00 00 00 00 00 00 01 00 01 00 01 00 ff ff 7c 4a
 40 0x0588f8 0x10    4   19   18    346   10 04 13 12 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
 41 0x058a52 0x10    7    5   18     97   10 07 05 12 00 e8 03 01 04 03 00 00 01 05 03 00 00 01 0a 03
 42 0x058ab3 0x10    6   24    8    198   10 06 18 08 c8 00 01 01 00 66 06 00 00 00 0c 00 00 00 10 00
 43 0x058b79 0x10    5   10    8     85   10 05 0a 08 00 81 00 00 00 00 00 07 00 00 00 01 01 01 00 00
 44 0x058d04 0x10    4    6    4     28   10 04 06 04 00 03 00 00 00 04 00 00 00 00 00 ff 00 00 00 00
 45 0x058d20 0x10    4   29    8    236   10 04 1d 08 00 00 00 00 00 45 c8 00 64 45 c8 00 32 01 01 00
 46 0x058bce 0x10    4   13    2     30   10 04 0d 02 00 00 00 00 00 00 00 00 ff 00 00 00 00 00 00 00
 47 0x05646b 0x10    4    9    5     49   10 04 09 05 0a 00 58 1b 8c 00 9e 00 05 0a 00 58 1b 8c 00 9e
 48 0x0563c0 0x10    8    4    5     28   10 08 04 05 ff 00 01 00 fd ff ff ff f8 ff ff ff f8 ff ff ff
```

Tổng **40 bảng / 21,179 B**.

### 1.2 Đối chiếu với nouveau — GIẢ THUYẾT TRONG ĐỀ BÀI SAI

Đọc source thật `nvkm/subdev/bios/perf.c`:

```c
if (!bit_entry(bios, 'P', &bit_P)) {
    if (bit_P.version <= 2) {
        perf = nvbios_rd32(bios, bit_P.offset + 0);   // PERF_PTRS[0] = u32 ptr
        *ver = nvbios_rd08(bios, perf + 0);
        *hdr = nvbios_rd08(bios, perf + 1);
        if (*ver >= 0x40 && *ver < 0x41) { ... }      // chi ho tro 0x40
        if (*ver >= 0x20 && *ver < 0x40) { ... }
```

**Kết luận đối chiếu:**

| Điểm | Kết quả |
|---|---|
| `PERF_PTRS[0]` là P-Table? | **ĐÚNG** — `nvbios_perf_table` đọc `bit_P.offset+0` |
| Ver của bảng này | **`0x60`** — **ngoài mọi dải nouveau hỗ trợ** (`0x20–0x40`, `0x40–0x41`) |
| Slot đầu là P-States / CLK_DOMAINS? | **SAI.** P-States chỉ có **1 bảng** (`PERF_PTRS[0]`). 39 slot còn lại là 39 bảng khác nhau, không phải "slot đầu tiên" |
| `0x54600` là CLK_DOMAINS 33 B/entry? | **SAI.** Đây là `PERF_PTRS[1]`, header `11 1a 3c 21` = ver `0x11`, hdr 26, **esz 60**, cnt 33 → `26 + 60*33 = 2,006 B` |
| Có tần số u16 (1650/1890/1905/2100) trong 40 bảng? | **KHÔNG — 0 hit** |
| Byte `0x50`/`0x40`/`0x85` là chỉ số VFE? | **SAI.** `0x50` = 80, `0x40` = 64, `0x85` = 133 — không phải chỉ số slot 0..149 có nghĩa ở đây |

### 1.3 Vì sao KHÔNG có tần số dạng u16

Turing dùng **PLL-based clock**, không lưu MHz tuyệt đối. Bằng chứng: bảng
`CLOCK_PTRS[0]` @`0x2D65F` (ver `0x50`, 14 entry × 19 B):

```
  [0] @0x2d663  07 95 01 95 01 d6 06 d8 0e 0d 00 26 00 10 10 28 ff 01 1f
  [1] @0x2d676  08 95 01 95 01 d6 06 d8 0e 0d 00 26 00 10 10 28 ff 01 1f
  [2] @0x2d689  0b 95 01 95 01 d6 06 d8 0e 0d 00 26 00 10 10 28 ff 01 1f
  [3] @0x2d69c  04 fa 00 2c 01 a0 0f 40 1f fa 00 2c 01 01 01 14 ff 01 02
  [4] @0x2d6af  0c 1b 00 1b 00 e2 04 c4 09 0d 00 1b 00 01 01 28 ff 01 1f
  [5] @0x2d6c2  41 1b 00 1b 00 20 03 54 06 0d 00 26 00 01 ff 14 ff 01 1f
  ...
```

Cấu trúc mỗi entry: `domain_id(1) + M(freq_div u16) + N(fb_div u16) + P(post_div u16) + ...`.
`0x0195 = 405` = N, `0x01 0x01` = M... → **PLL divisor**, không phải MHz.

**Con số 1890 MHz KHÔNG được quy định ở bất kỳ entry nào trong 40 bảng
PERF_PTRS, cũng không ở phương trình VFE nào.** Nó là kết quả runtime của
PLL + VFE.

---

## NHIỆM VỤ 2: VFE_VAR + TẠI SAO T3 RỚT + THÍ NGHIỆM T4

### 2.1 T3 rớt vì `var_idx`, không phải vì điện áp — ĐÚNG

```
slot0 REL   type= 1 var= 10 next=0xff c0= 1068750.0
slot1 ALT   type= 1 var= 10 next=0xff c0= 1093750.0
slot3 OV    type= 1 var=  7 next=0xff c0= 1125000.0
slot4 VMIN  type= 1 var=  7 next=0x05 c0=  693500.0
```

**Giả thuyết trong đề bài được xác nhận:** REL/ALT có `var=10`, OV có `var=7`.
Selector `03 03 03` bắt kênh REL/ALT (vốn đọc biến 10) trỏ vào slot OV
(vốn đọc biến 7) → **sai kiểu biến đầu vào** → PMU không khởi tạo được → card rớt.

### 2.2 THÍ NGHIỆM T4 — ĐÃ CHẠY THẬT

Giữ nguyên selector `00 01 03`, chỉ sửa `clamp_lo`, `clamp_hi`, `c0` của slot 0 và 1
lên `1125000.0`, **giữ nguyên `var_idx = 10`**.

Payload `CMP40HX_T4_payload.bin` (495,616 B), checksum cả 4 image đều `0x00`.

**KẾT QUẢ: CARD BOOT BÌNH THƯỜNG.** Override áp thành công
(`FindLegacy=1 skip=0x28600`, `map status=0x0`).

Đo tải 50 s:
```
1890 MHz | 144.03 W | 61 C
SW Power Cap  : Not Active
Board Limit   : Not Active      <-- TRUOC DAY ACTIVE
Reliability   : Not Active      <-- TRUOC DAY ACTIVE
```

### 2.3 Ý NGHĨA — PHÁT HIỆN QUAN TRỌNG NHẤT

**Nâng `c0` của REL/ALT lên 1125 mV đã TẮT được cả `Board Limit` và `Reliability`.**

Đây là bằng chứng trực tiếp: hai limiter này **bám giá trị `c0` của slot REL/ALT**,
không bám nhiệt độ hay leakage như suy đoán trước.

**Nhưng clock vẫn 1890 MHz** (144 W, 61 °C, không limiter nào chặn).

→ **Trần 1890 MHz KHÔNG phải limiter, KHÔNG phải power, KHÔNG phải thermal.**
Nó nằm ở **đường cong V/F** — đúng mô hình "clock wall" của tài liệu V100.

Kiểm tra chéo: `nvidia-smi --gpcclk` **không tồn tại** trong driver này
(`ERROR: Option --gpcclk is not recognized`) → mọi sweep VF offset qua lệnh đó là
**nhiễu, không set gì**. Điều này đính chính luôn phần "GPC VF offset" của báo cáo cũ.

### 2.4 VFE_VAR — GIẢI HOÀN TOÀN (stride 25)

Layout: `type(1B) + clamp_lo(f32 @+1) + clamp_hi(f32 @+5) + 16 B payload`

```
  var    offset  type   lo            hi            ghi chu
    0  0x0564a5    4       0.00        127.00
    1  0x0564be    4      54.00         67.00
    2  0x0564d7    4       0.00         31.00
    3  0x0564f0    4      -INF          +INF
    4  0x056509    4       0.00          0.00
    5  0x056522    4       0.00          0.00     * DUNG
    6  0x05653b    4      41.00         41.00
    7  0x056554    4    1981.23       2335.54     * DUNG  <- MHz!
    8  0x05656d    5      -INF          +INF
    9  0x056586    6      -INF          +INF     * DUNG
   10  0x05659f    3       0.00        105.00     * DUNG
   11  0x0565b8    4      -INF          +INF     * DUNG
   12  0x0565d1    3       0.00        105.00     * DUNG
   13  0x0565ea    2  450000.00    1243750.00     * DUNG  <- uV! (0.45 .. 1.24 V)
   14  0x056603    5      -INF          +INF     * DUNG
   15  0x05661c    5      -INF          +INF     * DUNG
   16  0x056635    5      -INF          +INF     * DUNG
   17  0x05664e    5      -INF          +INF     * DUNG
   18  0x056667    4      -INF          +INF     * DUNG
   19  0x056680    0       0.00          0.00
```

**Hai biến quan trọng nhất:**
- **`var[7]` = 1981.23 … 2335.54** → dải **tần số MHz**
- **`var[13]` = 450,000 … 1,243,750** → dải **điện áp µV** (0.45 – 1.24 V)

`var[10]` và `var[12]` = 0..105 → dải **nhiệt độ °C**.

### 2.5 Phương trình tần số — KHÔNG TÌM THẤY

Quét cả 150 slot: **không slot nào** cho `y ∈ 1000..2500 MHz` khi `x = mV` trong
dải thực (693.5 – 1125). Các slot có hệ số góc:

```
slot[ 30] var=12  y = -60.0000 + 1.714286x       (x=1068.75 -> 1772.14)
slot[ 33] var= 7  y = 1401.9912 + -0.687952x     (x=1068.75 ->  666.74)
slot[ 34] var= 7  y = 2264.6799 + -0.695849x     (x=1068.75 -> 1520.99)
slot[ 71] var= 7  y = 2037.9200  (hang so)
slot[118] var= 7  y = 2264.6799  (hang so)
```

**`slot[10]` mà báo cáo trước nghi là phương trình tần số — SAI:**
```
y = -1838.229980 + 1.114014x - 0.00016x^2   var=7
x=1068.75 -> -830.38    x=1890 -> -304.28    x=1650 -> -435.71
```
Ra số âm ở mọi đơn vị thử → không phải tần số.

### 2.6 Trả lời câu hỏi "nâng c0 để boost 2055–2070 mà không cần NVML"

**KHÔNG ĐƯỢC.** Lý do đã chứng minh bằng đo:

1. `var[7]` (dải MHz) đã là `1981.23 .. 2335.54` — trần **2335 MHz** không phải nút thắt
2. `c0` của REL/ALT đã nâng lên 1125 mV → limiter tắt sạch
3. Clock **vẫn 1890** → không có phương trình VFE nào đang tính MHz từ mV
4. Trần nằm ở **PLL/clock-tree**, không ở VFE

Muốn vượt phải đổi **bảng PLL** (`CLOCK_PTRS[0]` @`0x2D65F`, 14 domain), không phải VFE.

---

## NHIỆM VỤ 3: 10 DIGEST TRONG IBVL — KHÔNG KHỚP BẤT KỲ BẢNG NÀO

### 3.1 Cấu trúc IBVL đã giải

```
IBVL @0x7684b: 49 42 56 4c 1a 00 00 00 01 22 00 00 00 28 00 00 00 00 00 00 00 00 00 00 00 3c
  sig = 'IBVL', size = 26
  +0x08 = 0x00002201  -> [0x01, 0x22, 0x00, 0x00]
  +0x0c = 0x00002800  -> [0x00, 0x28, 0x00, 0x00]
  +0x10 = 0
  +0x14 = 0
```

### 3.2 Thực tế có 15 blob 32 B, không phải 10

Quét `0x76860..0x76c00` tìm blob entropy cao:

```
  [0] @0x076904 1bcba75a68f85000d2cc64bbb60fcc6afc4c4460bd1ab7552c3b821822ca3e47
  [1] @0x076928 24a41becc7a157d0cc95f6a1798fe9ddbf4ba78712392faed2ba384498a877df
  [2] @0x076960 ff65f765057bf070d154799b375e415876f92971dddc6cadbf47312f3eda092b
  [3] @0x076998 b839fc4359fa2f49f5810e62db7dd0c283a963e122e966c3ce52aa7b9907560c
  [4] @0x0769cc 62c090811a3af75457fef7e4b8111c713d59ab608430b26a0fad6912cb5850cf
  [5] @0x0769ec 47d88361870acae7b9762ec8639c2dd1f33f393062a65675427d9145bb86e02a
  [6] @0x076a2c 160e218eaa27d50967a98a0a6884ff28cfb275c84456f106516dffa72c8bf0cb
  [7] @0x076a50 ca910579b4da6a0c85aac1789ffae3d85cc0980db6ea6de83ac6576d9e605148
  [8] @0x076ae4 3a5b361328a2c6d4be138a2b2311f108d0baf0299e5aac0068a3a96c109d7d7e
  [9] @0x076b1c 88a06468bed66b4f97f759659a0695f0ef6f8c6c1d70fef88a883abce42c231a
 [10] @0x076b40 ce4b1facf9f0491e468fc8084c1a1d4a41c8ea3930067f79b7121c6504eddbf8
 [11] @0x076b64 58e30e2ae2f9051f74172f4971da3420a07ff86ad61491b00e93ab57ebf111d3
 [12] @0x076b84 bf741421e253a2dbcbf3147ef096da099fabcca6cead928f41e8b6829e6ab7c1
 [13] @0x076bb4 236441447c77519c12effce7f80e4f818026005e7a60dcc996aa5c15a56b90e0
 [14] @0x076bd4 07aa04292f342a5264b04fc6854938e0eb777398be26ab201ce14ad6796ae9d7
```

**15/15 duy nhất** (không cái nào trùng).

### 3.3 Đối chiếu hash — 0 KHỚP

Thử **6 thuật toán × 14 vùng × 15 digest = 1,260 phép thử**:

| Thuật toán | Vùng thử |
|---|---|
| SHA256 | legacy x86 #1, EFI #1, NPDS-E0 #1, NPDS-E0 #2, NPDS-70 |
| SHA384 | VFE header+var, VFE 150 slot, POWER, THERMAL, FAN |
| SHA512 | PERF/Ps table, bảng 0x54600, rail row, BIT table |
| BLAKE2s | + cửa sổ trượt 0x200/0x400/0x800/0x1000/0x2000/0x4000/0x10000 |
| SHA1 | |
| MD5 | |

**KẾT QUẢ: 0 khớp / 1,260 phép thử.**

### 3.4 Kết luận Nhiệm vụ 3

Digest **không phải** hash của bất kỳ bảng nào trong ROM — kể cả ở dạng cửa sổ trượt.
Điều này khớp với kết luận trước đó và giải thích **vì sao VBIOS override chạy được**:
Turing **không kiểm digest** ở đường nạp qua RAM (đã chứng minh bằng thực nghiệm —
payload sửa 19 byte vẫn boot bình thường, không cần ký lại).

Nhiều khả năng 15 blob là **chuỗi chứng thư X.509 / RSA modulus** của `RKSL`/`NVIDIA Corp`,
không phải digest list của bảng.

---

## TỔNG KẾT — 4 KẾT LUẬN CỨNG

| # | Kết luận | Bằng chứng |
|---|---|---|
| 1 | `payload = rom[0:0x79000]`, **không phải** `rom[0x28600:...]` | so khớp: 19 byte khác (toàn bộ là field đã sửa) vs 481,992 byte |
| 2 | `VFE_VAR` stride **25**, layout `type(1)+lo(f32)+hi(f32)` | header `30 09 19 14` → 9 + 25×20 = 509 ✓ |
| 3 | **T3 rớt vì `var_idx` 10→7**, không vì điện áp | T4 cùng điện áp, giữ `var=10` → boot OK |
| 4 | **Nâng REL/ALT `c0` lên 1125 mV TẮT được `Board Limit` + `Reliability`** | cả 2 limiter `Not Active` sau T4 |
| 5 | **Trần 1890 MHz không phải limiter/power/thermal** | 144 W, 61 °C, 0 limiter, vẫn 1890 |
| 6 | Trần nằm ở **PLL/clock-tree**, không ở VFE | `var[7]` trần 2335 MHz; không slot nào tính MHz |
| 7 | Digest IBVL **không khớp bảng nào** | 0/1,260 phép thử |
| 8 | `nvidia-smi --gpcclk` **không tồn tại** — đính chính báo cáo cũ | `ERROR: Option --gpcclk is not recognized` |

### Đường đi tiếp (theo thứ tự ưu tiên)

1. **`CLOCK_PTRS[0]` @`0x2D65F`** — 14 domain × 19 B PLL divisor. Muốn vượt 1890
   phải sửa **bảng này**, không phải VFE. Cần decode `M/N/P` cho từng domain.
2. **`PERF_PTRS[0]` @`0x54155`** — P-Table ver `0x60` (ngoài nouveau). Chứa P-State
   → clock domain mapping. Body chỉ 69 B.
3. **`PERF_PTRS[1]` @`0x54600`** — 33 entry × 60 B. Chưa decode field.
4. 15 blob trong `0x76904..0x76bf4` — nhiều khả năng là cert, không phải digest.

---

## CÔNG CỤ MỚI

| File | Chức năng |
|---|---|
| `deep_analysis.py` | 40 bảng PERF_PTRS + VFE_VAR + digest (bản đầu, stride sai) |
| `find_freq.py` | Tìm tần số mọi dạng mã hoá + nghịch đảo slot |
| `clock_digest.py` | Parse CLOCK_PTRS + đối chiếu digest đa thuật toán |
| `t3_deep.py` | So payload vs ROM + VFE_VAR float |

Cả 4 ở `~/.hermes/cache/scratch/vbios40/`.

---

## TRẠNG THÁI CARD

Payload T4 vẫn đang nạp trong `/etc/modprobe.d/cmp40hx-vbios.conf`
(`cmp40hx_t4.bin`, REL/ALT = 1125 mV).
Card khoẻ: 300 MHz idle / 12.48 W / PL 184 W, boot bình thường.

**Rollback:** `sudo rm /etc/modprobe.d/cmp40hx-vbios.conf && sudo systemctl reboot`

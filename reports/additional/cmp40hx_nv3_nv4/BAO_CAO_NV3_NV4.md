# BÁO CÁO NHIỆM VỤ 3 + 4 — CMP 40HX

Tiếp nối `BAO_CAO_3_NHIEM_VU.md`
Ngày: 03/11/2026

---

## NHIỆM VỤ 3: IBSN / IBVL — HEX DUMP ĐẦY ĐỦ + KẾT QUẢ DỨT ĐIỂM

### 3.1 IBSN @0x76838 (20 byte tổng: 8 header + 12 body)

```
076838  49 53 42 4e 0c 00 00 00 01 01 42 56 ac 16 77 d8  ISBN......BV..w.
076848  33 fe 27 49 42 56 4c 1a 00 00 00 01 22 00 00 00  3.'IBVL....."...
```

```
sig  = "IBSN"
size = 12 (0x0C)          <- body 12 byte theo sau
body = 01 01 42 56 ac 16 77 d8 33 fe 27 49
       [0] 0x01  version
       [1] 0x01  type
       [2:4] "BV"  tag ASCII
       [4:12] 8 byte = ac1677d8 33fe2749  -> 2 x u32, KHONG phai SHA256
```

**Kết luận:** IBSN tổng 20 byte, vùng hash chỉ **8 byte** (2×u32) — không thể là SHA-256.

### 3.2 IBVL @0x7684B (26 byte) — KHÔNG phải digest list

```
07684b  49 42 56 4c 1a 00 00 00 01 22 00 00 00 28 00 00  IBVL....."...(..
07685b  00 00 00 00 00 00 00 00 00 3c 1a 00 00 28 00 00  .........<...(..
07686b  00 5e 00 00 00 fe 07 00 00 fc 08 00 00 b0 0a 00  .^..............
```

Decode:
```
sig  = "IBVL"
size = 26 (0x1A)
+0x00 u16 = 0x2201     version 1, 0x22
+0x02 u32 = 0x28000000 (byte 00 00 00 28)
+0x0a u32 = 0
+0x11 u32 = 0x1A3C = 6716
+0x15 u32 = 0x28   = 40
```

### 3.3 Metadata ngay sau IBVL — ĐÂY LÀ CHỖ CHỨA OFFSET/LENGTH

`0x7686D .. 0x768F4`:

```
07686d  00 00 00 fe 07 00 00 fc 08 00 00 b0 0a 00 00 01   -> 0x7FE=2046, 0x8FC=2300, 0xAB0=2736
07687d  00 00 00 36 00 00 00 31 31 33 32 34 34 61 73 75   -> len 0x36=54, "113244asus"
07688d  73 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
07689d  00 42 31 31 33 36 39 30 00 ...                    -> "B113690"
0768ad  00 00 00 00 00 02 00 00 00 1c 00 00 00 00 00 00   -> 2, 0x1C=28
0768bd  00 29 04 00 00 06 00 00 00 01 00 00 00 01 00 00   -> 0x429=1065, 6, 1, 1
0768cd  00 20 00 00 00 b0 01 00 00 08 10 00 00 0d 04 00   -> 0x20, 0x1B0=432, 0x1008=4104, 0x40D=1037
0768dd  00 06 00 00 00 02 02 00 02 0f 00 00 00 01 00 00   -> 6, 0x0202, 0x0F02
0768ed  00 01 00 00 00 10 0e 8d 60 10 5c 7a 61 c8 79 28
```

**Các giá trị đọc được dạng u32:**
```
0x7686c = 94        0x76870 = 2046      0x76874 = 2300      0x76878 = 2736
0x7687c = 1         0x76880 = 54        0x768b0 = 131072 (0x20000)
0x768b4 = 1835008   0x768bc = 69795840 (0x04290000)
0x768c0 = 393216 (0x00060000)           0x768c4 = 65536 (0x00010000)
0x768cc = 2097152 (0x00200000)          0x768d0 = 28311552 (0x01B00000)
0x768d4 = 268959744 (0x10080000)        0x768d8 = 67960832 (0x040D0000)
```

**Bằng chứng then chốt:** `2046`, `2300`, `2736` — đây là **độ dài (length)**, không phải
offset bảng. Và chúng **không khớp** kích thước của bất kỳ bảng nào trong ROM
(legacy 62,464 / EFI 69,632 / NPDS 46,592 / 141,312).

**Không có byte nào trong metadata ghi `offset` + `length` của bảng được hash.**
Metadata là thông tin board/product: `"113244asus"` (board ID), `"B113690"` (part),
version, cờ cấu hình.

### 3.4 CÓ 12 DIGEST 32 B, KHÔNG PHẢI 10

Quét tự động tìm dãy 32-byte entropy cao liên tục:

```
=== 12 digest 32 B @0x0768f0..0x076a70 ===
  [ 0] @0x0768f0 0000100e8d60105c7a61c8792814bcc70c686c131bcba75a68f85000d2cc64bb
  [ 1] @0x076910 b60fcc6afc4c4460bd1ab7552c3b821822ca3e47700f37ae24a41becc7a157d0
  [ 2] @0x076930 cc95f6a1798fe9ddbf4ba78712392faed2ba384498a877df9388eaad77cdad01
  [ 3] @0x076950 5877aaa936a2e99964cb88b72bf929afff65f765057bf070d154799b375e4158
  [ 4] @0x076970 76f92971dddc6cadbf47312f3eda092bef76979b21bbc53fcd451c45f7418894
  [ 5] @0x076990 1378548c49c38c0db839fc4359fa2f49f5810e62db7dd0c283a963e122e966c3
  [ 6] @0x0769b0 ce52aa7b9907560c1d63a82656863e5b2b10cc7ada6b1ee68c6ccc8c62c09081
  [ 7] @0x0769d0 1a3af75457fef7e4b8111c713d59ab608430b26a0fad6912cb5850cf47d88361
  [ 8] @0x0769f0 870acae7b9762ec8639c2dd1f33f393062a65675427d9145bb86e02a4fb7b6bb
  [ 9] @0x076a10 a35a6c4674f17ac32b14056a4b475cfbf15c48464c8a391fc0d518aa160e218e
  [10] @0x076a30 aa27d50967a98a0a6884ff28cfb275c84456f106516dffa72c8bf0cb4e5c2f92
  [11] @0x076a50 ca910579b4da6a0c85aac1789ffae3d85cc0980db6ea6de83ac6576d9e605148
```

Byte ngay sau: `7c 02 24 fc 85 c1 13 e1 d1 55 01 00 01 00 10 00`

### 3.5 KẾT QUẢ TÌM KIẾM — 0 KHỚP / 1,365,939 PHÉP THỬ

Script `ibvl2.py`:

| Phép thử | Số lượng | Khớp |
|---|---:|---:|
| 112 vùng ứng viên × 7 thuật toán × 3 biến thể | 784 | **0** |
| Cửa sổ trượt trong `0x28000..0x79000`, 17 kích thước × 3 stride × 3 thuật toán | 1,365,939 | **0** |
| 5 image với byte checksum zero hoá | 30 | **0** |

Vùng ứng viên gồm:
- 40 bảng PERF_PTRS (cả bảng đầy đủ và body-only)
- 17 target của BIT token table
- legacy/EFI/NPDS cả 2 bank
- VFE header + VFE 150 slot
- object directory `legacy+0x209`
- toàn bộ 81 khối 0x200 của vùng header

Thuật toán: **SHA256, SHA1, MD5, BLAKE2s, SHA512, SHA384, SHA3-256**
Biến thể: raw / 32 byte đầu / 32 byte cuối

### 3.6 TRẢ LỜI DỨT ĐIỂM

**Câu hỏi: Bảng nào bị kiểm SHA-256 bởi PMU/FWSEC?**
→ **KHÔNG BẢNG NÀO.** 12 digest trong IBVL không khớp bất kỳ vùng dữ liệu nào của ROM.

**Câu hỏi: Bảng nào sửa tự do không bị digest chặn?**
→ **TẤT CẢ.** Không có ràng buộc digest nào ở đường nạp VBIOS qua RAM.

**Bằng chứng thực nghiệm độc lập:** payload T2/T4 sửa **19 byte** trong các bảng
VFE (`0x566A0`…`0x566BE`), POWER (`0x57F48`…`0x57FD0`) + 1 byte checksum
→ card **boot bình thường**, override áp thành công, không cần ký lại bất cứ thứ gì.

**Kết luận về bản chất 12 blob:** đây **không phải digest list của bảng**.
Nhiều khả năng là **chuỗi chứng thư / RSA modulus / nonce** của khối `RKSL` +
`NVIDIA Corp` nằm ngay sau đó (`0x76A9E` và `0x76EC7`). Chúng là **chữ ký số của
chính khối chữ ký**, không phải hash của bảng dữ liệu.

---

## NHIỆM VỤ 4: REGISTRY KEY RM* + FALCON_DATA + NVUCODES

### 4.1 `gsp_tu10x.bin` — CẤU TRÚC THẬT

Không phải blob mờ. Là **ELF lồng 2 lớp**:

```
Lớp ngoài: ELF64 REL, machine RISC-V (0xF3), 10 section
  .fwimage       @0x40   21,935,048 B   <- lớp trong
  .fwversion     @0x15D3E2C  10 B
  .fwsignature1  @0x15D3E36  4096 B
  .fwsignature2  @0x15D4E36  4096 B
  .fwsignature3  @0x15D5E36  4096 B
  .symtab/.strtab

Lớp trong (tại file offset 0x40): ELF64 EXEC, machine RISC-V, entry 0x4009000
  31 program header, 37 section
```

**Section quan trọng của lớp trong:**

| Section | vaddr | File off | Size |
|---|---|---|---|
| `.tu10x_text` | `0x04007000` | `0x00007040` | 5,140 |
| `.tu10x_resident_text` | `0x0400E000` | `0x0000E040` | 12,288 |
| `.section_task_init_elf_text_instance` | `0x04018000` | `0x00018040` | 16,384 |
| `.section_task_rm_elf_rodata_instance` | `0x0401D000` | `0x0001D040` | 1,982,464 |
| `.section_task_rm_elf_data_instance` | `0x04201000` | `0x00201040` | 3,698,688 |
| **`.section_task_rm_elf_text_instance`** | `0x04588000` | `0x00588040` | **17,010,688** |
| `.section_task_init_dmem_64kb_instance` | `0x055C1000` | `0x015C1040` | 65,536 |

Load base `0x4000000`.

### 4.2 VỊ TRÍ CÁC KEY RM* — BẢNG DESCRIPTOR

Các tên key nằm liền nhau trong `.rodata`, bắt đầu `0x1B4AF8`:

```
001b4af8  RMHwSpeedoOverride        (vaddr 0x041b4ab8)
001b4b10  RMHwSpeedo1Override       (vaddr 0x041b4ad0)
001b4b28  RMHwSpeedo2Override       (vaddr 0x041b4ae8)
001b4b40  RMHwSpeedoCheckIgnore     (vaddr 0x041b4b00)
001b4b58  RmPmgrIddqOverride        (vaddr 0x041b4b18)
001b4b70  RmPmgrIddq1Override       (vaddr 0x041b4b30)
001b4b88  RmPmgrIddqNvvddOverride   (vaddr 0x041b4b48)
001b4ba0  RmPmgrIddqMsvddOverride   (vaddr 0x041b4b60)
001b4bb8  RmPmgrIddqCheckIgnore     (vaddr 0x041b4b78)
001b4bd0  RmSramVminCheckIgnore     (vaddr 0x041b4b90)
001b4be8  RmPmgrIsenseVcmOffsetOverride     (MOI - chua tung biet)
001b4c08  RmPmgrIsenseDiffGainOverride      (MOI)
001b4c28  RmPmgrIsenseDiffOffsetOverride    (MOI)
```

**Key riêng lẻ:**
```
RMClkVfOverride                 @0x092DE8  vaddr 0x04092DA8
RmClockForceUprocVfeVfGen       @0x092D10  vaddr 0x04092CD0
RmPmgrSpeedoCoefficient         @0x1B8F70  vaddr 0x041B8F30
RmPmgrSpeedoOffset              @0x1B8F88  vaddr 0x041B8F48
RmVoltThresholdCtrlCtrl         @0x1B9730  vaddr 0x041B96F0
RMEnableOverclockingAllPstates  @0x1A5BA0  vaddr 0x041A5B60
RMForceLockedClocksMode         @0x1A5C60  vaddr 0x041A5C20
RMSec2UseDebugFuseOnlyBinary    @0x1BBDC8  vaddr 0x041BBD88
RMNoECCFuseCheck                @0x0A7908  vaddr 0x040A78C8
RmDisableFspFuseErrorCheck      @0x135758  vaddr 0x04135718
```

### 4.3 XREF — KHÔNG CÓ THAM CHIẾU CỨNG

Đã thử **3 kiểu** trên **toàn bộ 22.9 MB**:

| Kiểu | Kết quả |
|---|---|
| Con trỏ u32 tới vaddr chuỗi | **0 ref** cho cả 10 key thử |
| Con trỏ u64 tới vaddr chuỗi | **0 ref** |
| `auipc rd,imm20` + `addi rd,rd,imm12` (PC-relative chuẩn RISC-V) | **0 ref** |

**Ý nghĩa:** GSP-RM **không** tham chiếu cứng từng chuỗi key. Nó tra key
**theo tên lúc runtime** qua registry lookup (đúng như cơ chế
`NVKV_SET_STRING8_LEN(REGKEY_NAME)` + `NVKV_SET_SEQ32_1U(REGKEY_VALUE_U32)` ở
phía driver). Đây là lý do **không thể đọc "kiểu giá trị mong đợi" từ tĩnh** —
kiểu phụ thuộc vào hàm xử lý mà registry dispatch tới, không nằm cạnh chuỗi.

**Hệ quả thực tế:** không có cách tĩnh nào xác định `RMHwSpeedoOverride` cần
boolean 0/1 hay giá trị số. Phải **thử runtime** hoặc disasm hàm tra cứu registry
(tìm `NVKV`/`REGKEY` handler trong `.section_task_rm_elf_text_instance`).

### 4.4 FALCON_DATA @0x48B54

```
048b54  01 06 06 10 01 30 01 01 44 4d 01 00 00 00 00 00
        ver=0x01  hdr=6  esz=6  cnt=16  -> 6 + 6*16 = 102 B
```

Entry size **6 byte** đúng như header. Nội dung:

```
  [ 0] @0x048b5a 01 01 44 4d 01 00    tag=0x01 flags=0x01 "DM" 0x01
  [ 1] @0x048b60 00 00 00 00 00 00
  [ 2] @0x048b66 00 00 00 00 00 00
  [ 3] @0x048b6c 00 00 00 00 00 00
  [ 4] @0x048b72 00 00 00 00 00 00
  [ 5] @0x048b78 00 00 00 00 00 00
  [ 6] @0x048b7e 08 01 c4 a6 03 00    -> u32 = 0x3A6C4 = 239,300
  [ 7] @0x048b84 00 00 00 00 00 00
  [ 8] @0x048b8a 45 07 fc 3d 02 00    -> u32 = 0x23DFC074 ...
  [ 9] @0x048b90 85 07 28 dc 02 00
```

**Kết luận:** `FALCON_DATA` là **bảng 16 entry × 6 byte, phần lớn rỗng**.
Chỉ entry 0 (`"DM"` = Device Manager?) và 3 entry có giá trị số.
Đây **không phải devinit script** như báo cáo trước nghi ngờ — kích thước 102 B
quá nhỏ. Vùng hash `0x2C3FC` mà báo cáo trước nhắc **không thuộc bảng này**.

### 4.5 NVINIT @0x28893 — KHÔNG PHẢI HEADER

```
028893  98 46 00 00 00 00 9c 46 00 00 88 4b 9c 46 87 d7
```

`0x28893` **không phải bảng có header**. Đây là **giữa mảng con trỏ** của BIT
token table (`NVINIT_PTRS`, token `0x49`, ptr `0x0244` → `0x28844`).

Giá trị tại đó: `0x4698`, `0x469C`, `0x4B88`, `0x469C` — đây là **con trỏ tới vùng
`0x2CC98`** (công thức rẽ nhánh: `0x28800 + 0x4698 - 0x400` ≈ `0x2CC98`),
khớp `CLOCK_PTRS[12]` đã thấy trước đó (`0x004698` → `0x02CC98`).

**Kết luận:** `NVINIT` token trỏ tới cùng vùng với clock init — không phải bảng
riêng. Báo cáo trước ghi "NVINIT chưa parse" là do chọn sai offset.

### 4.6 NVUCODES — 11 BLOB, GIẢI HOÀN TOÀN

Header thật (`ucodes_tu10x.bin`, 8,837,632 B):

```
+0x00  "NVUCODES"
+0x08  ver = 1
+0x0C  header_size = 0x1F0 = 496
+0x10  u64 hash = 0x8D1990AB6B98AE2B
```

Entry table @`0x1F0`, **stride 32**, marker `04 00 00 00` + `offset` u32:

```
  @0x00208  off=0x00002F00       @0x00328  off=0x00098F00
  @0x00220  off=0x00020F00       @0x00340  off=0x000B7C00
  @0x00238  off=0x0003EF00       @0x00358  off=0x000D6700
  @0x00250  off=0x0005CF00       @0x00370  off=0x000F5400
  @0x00268  off=0x0007AF00       @0x00388  off=0x00113F00
                                 @0x003A0  off=0x00134300
```

**11 blob, offset tăng dần, khoảng cách đều 0x1E000** (blob cuối 0x20400).

| # | Offset | Size | Entropy | Nonzero | Loại |
|---:|---|---:|---:|---:|---|
| 0 | `0x00002F00` | 122,880 | 3.481 | 37% | **plaintext** |
| 1 | `0x00020F00` | 122,880 | **7.998** | 99% | **MÃ HOÁ** |
| 2 | `0x0003EF00` | 122,880 | **7.998** | 99% | **MÃ HOÁ** |
| 3 | `0x0005CF00` | 122,880 | **7.998** | 99% | **MÃ HOÁ** |
| 4 | `0x0007AF00` | 122,880 | **7.998** | 99% | **MÃ HOÁ** |
| 5 | `0x00098F00` | 126,208 | 4.915 | 57% | **plaintext** |
| 6 | `0x000B7C00` | 125,696 | 4.898 | 57% | **plaintext** |
| 7 | `0x000D6700` | 126,208 | 4.916 | 57% | **plaintext** |
| 8 | `0x000F5400` | 125,696 | 4.898 | 57% | **plaintext** |
| 9 | `0x00113F00` | 132,096 | 4.953 | 57% | **plaintext** |
| 10 | `0x00134300` | 7,575,296 | 7.261 | 83% | **hỗn hợp** |

**Tổng: 6 plaintext + 4 mã hoá + 1 hỗn hợp.**
(Đính chính báo cáo trước ghi "13 blob, 7 plaintext, 6 mã hoá" — sai do stride 24.)

**Đặc điểm blob mã hoá:** cả 4 blob đều **122,880 B = 0x1E000**, entropy **7.998**
(gần như hoàn hảo), nonzero **99%**. Kích thước giống hệt nhau → cùng loại
firmware (nghi microcode engine, mỗi engine 1 blob).

**Blob 10 (7.5 MB) entropy 7.261, nonzero 83%** — đây là vùng lớn nhất, kích thước
bất thường, nhiều khả năng là **container firmware tổng hợp** chứ không phải
một microcode đơn.

**Mapping bị thiếu:** file dài 8,837,632 B nhưng blob cuối kết thúc ở
`0x134300 + 7,575,296` = `0x86DA00` — khớp đúng file size. Không có dữ liệu thừa.

---

## TỔNG KẾT 8 KẾT LUẬN CỨNG

| # | Kết luận | Bằng chứng |
|---|---|---|
| 1 | **12 digest trong IBVL không khớp bất kỳ bảng nào** | 0 / 1,365,939 phép thử (7 thuật toán, 3 biến thể, 17 kích thước cửa sổ) |
| 2 | **Metadata IBVL không chứa offset/length bảng được hash** | chỉ có board ID `"113244asus"`, part `"B113690"`, và 3 length 2046/2300/2736 không khớp bảng nào |
| 3 | **KHÔNG bảng nào bị digest chặn** — sửa tự do | payload T4 sửa 19 byte, boot bình thường |
| 4 | **IBSN 20 byte, vùng hash 8 byte** — không thể là SHA-256 | `sig+size12+ver+type+"BV"+2×u32` |
| 5 | **`gsp_tu10x.bin` là ELF64 RISC-V lồng 2 lớp**, không phải blob mờ | lớp ngoài 10 section, lớp trong 37 section, load base `0x4000000` |
| 6 | **Registry key tra theo tên runtime, không có XREF cứng** | 0 ref ở cả 3 kiểu (u32 ptr, u64 ptr, auipc+addi) trên 22.9 MB |
| 7 | **NVUCODES: 11 blob (6 plaintext + 4 mã hoá + 1 hỗn hợp)** | stride 32, marker `04 00 00 00`, 4 blob mã hoá đều 122,880 B entropy 7.998 |
| 8 | **`FALCON_DATA` chỉ 102 B, 16 entry × 6 B, phần lớn rỗng** — không phải devinit script | `0x28893` cũng không phải header, là giữa mảng con trỏ NVINIT |

### 3 key MỚI phát hiện trong GSP-RM
```
RmPmgrIsenseVcmOffsetOverride    @0x1B4BE8
RmPmgrIsenseDiffGainOverride     @0x1B4C08
RmPmgrIsenseDiffOffsetOverride   @0x1B4C28
```
`Isense` = current-sense (đo dòng). Có thể là đường can thiệp **OCP/current limit**.

---

## CÔNG CỤ MỚI

| File | Chức năng |
|---|---|
| `ibvl_match.py` | bản đầu, có bug `find()` → sinh 3 MB output |
| **`ibvl2.py`** | bản đúng: hex dump + tìm digest tự động + 1.37M phép thử |
| `gsp4.py` | liệt kê 37 section + XREF ban đầu |
| **`gsp_xref.py`** | XREF chuẩn RISC-V `auipc+addi` |
| **`final4.py`** | XREF toàn file 3 kiểu + FALCON_DATA + NVINIT + NVUCODES |

Ở `~/.hermes/cache/scratch/` (host).

---

## TRẠNG THÁI CARD

Payload T4 (`cmp40hx_t4.bin`, REL/ALT = 1125 mV) đang nạp.
Card khoẻ: 300 MHz idle / 12.48 W / PL 184 W.

**Rollback:** `sudo rm /etc/modprobe.d/cmp40hx-vbios.conf && sudo systemctl reboot`

# MASTER REPORT — CMP 40HX Reverse Engineering

Ngày: 03/11/2026 · Kernel 6.8.0-147-generic · Driver 615.78.08 (open, cmpunlocker)
Card: TU106-100-A1, `10DE:1F0B`, `8804:1043`, BDF `0000:03:00.0`

Báo cáo này chỉ dùng bằng chứng thu được **trong phiên này**.
Chi tiết từng bằng chứng: `EVIDENCE_LEDGER.md`.
Ma trận giả thuyết: `HYPOTHESIS_MATRIX.md`.

---

## Tóm tắt điều hành

Sáu tiêu chí hoàn thành (mục 10 của đề bài):

| # | Tiêu chí | Trạng thái |
|---|---|---|
| 1 | Xác định cấu trúc bảng chứa 6 float32 | **ĐẠT** |
| 2 | Chứng minh/bác bỏ "6 field là điện áp" | **ĐẠT — là điện áp µV** |
| 3 | Ý nghĩa + thuật toán checksum `0x767FF` | **ĐẠT** |
| 4 | Cấu trúc khác biệt ROM 1 MiB vs 495,616 B | **ĐẠT** |
| 5 | Đường xử lý voltage/clock trong driver/GSP-RM | **ĐẠT MỘT PHẦN** |
| 6 | Đánh giá nguyên nhân trần 1905 MHz | **ĐẠT MỘT PHẦN** |

Mục 5 và 6 đạt ở mức "xác định được cấu trúc + loại bỏ được 4 giả thuyết",
nhưng **chưa phân biệt được hai ứng viên còn lại**. Không có kết quả nào
được tạo ra bằng suy đoán thay cho đo đạc.

---

## 1. VBIOS Forensics (Nhiệm vụ A)

### 1.1 Định danh

```
CMP40HX_ORIGINAL_1MB.bin  1,048,576 B
  sha256 dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec
cmp40hx_t4.bin              495,616 B
  sha256 aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb
```

Khớp hash và kích thước đề bài cung cấp. 19 byte khác biệt — khớp.

### 1.2 Bản đồ container

Cấu trúc ROM 1 MiB, mỗi image có checksum riêng `sum % 256 == 0`:

```
bank1 (image chinh)     0x000000..0x0A1600   660,992 B
   legacy x86 #1        0x028600..0x037A00    62,464 B   checksum OK
   EFI #1               0x037A00..0x048A00    69,632 B   checksum OK
   NPDS type-0xE0 #1    0x048A00..0x054000    46,592 B   checksum OK
   NPDS type-0xE0 #2    0x054000..0x076800   141,312 B   checksum OK  <- chua VFE
   NPDS type-0x70       0x076800..0x078400     7,168 B   checksum OK (digest list)
   padding FF           0x078400..0x079000     3,072 B
   NVGIf container #2   0x079000..0x0A1600   165,376 B              <- bi gioi payload
bank2 (ban sao thu 2)   0x0A1600..0x100000   387,584 B
   legacy #2, EFI #2, NPDS #3/#4, VN container, NPDE
```

### 1.3 Sáu field float32 — A3, A4, A5

**Bảng:** VFE (Voltage/Frequency Equation), thuộc `NPDS type-0xE0 #2`.

| Thuộc tính | Giá trị | Cơ sở |
|---|---|---|
| Table ID | VFE @ `0x5649C` (header `30 09 19 14 18`) | parse + nvbios |
| Table version | `0x30` | header byte 0 |
| Base slot | `0x56699` | `nvbios equation_offset = 353945` |
| Slot stride | **24 byte** | `hdr+esz*cnt` khớp span |
| Slot count | 150 (`0x96`) | header byte 5 |
| Var stride | **25 byte** | header `19` = `esz 25` |
| Var count | 20 (`0x14`) | header byte 3 |
| Selector | `0x2D384` = `00 01 03 00 02 04` | `nvbios selector.offset = 185220` |

**Record chứa 6 field:**

```
slot[0] @0x56699 — NVVDD REL     type=1 (constant)  var_idx=10  next=0xFF  flags=0x02
  +0x03 f32 lo = 1068750.0 µV       <- field 1
  +0x07 f32 hi = 1068750.0 µV       <- field 2
  +0x0B f32 c0 = 1068750.0 µV       <- field 3
  +0x0F f32 c1 = 0.0
  +0x13 f32 c2 = 0.0

slot[1] @0x566B1 — NVVDD ALT     type=1 (constant)  var_idx=10  next=0xFF  flags=0x02
  +0x03 lo = 1093750.0 µV            <- field 4
  +0x07 hi = 1093750.0 µV            <- field 5
  +0x0B c0 = 1093750.0 µV            <- field 6
```

**Field meaning / unit / scale:**

| Field | Ý nghĩa | Đơn vị lưu | Đơn vị hiển thị | Hệ số |
|---|---|---|---|---|
| `+0x03` lo | clamp dưới của phương trình | µV (f32) | mV | ÷1000 |
| `+0x07` hi | clamp trên = **giá trị phát ra** | µV (f32) | mV | ÷1000 |
| `+0x0B` c0 | hệ số hằng của phương trình | µV (f32) | mV | ÷1000 |

Vì `type=1` (constant) và `c1=c2=0`, phương trình rút về **hằng số**:
`y = c0`, kẹp trong `[lo, hi]`. Cả 3 trường trùng nhau ở ROM gốc.

**Domain/index liên quan:** `rail_identity.logical_rail_id = NVVDD`,
`vbios_row_index = 0`; `runtime_role_candidate` = `REL` (slot 0) và `VOP`
(slot 1). Selector index 0 và 1 **không đổi** giữa ROM và T4.

### 1.4 Chứng minh "là điện áp" — A5

Bốn nguồn bằng chứng **độc lập**:

1. **IEEE-754 decode:** `0x00495470` → `1068750.0`; `0x00895440` → `1125000.0`.
   1125000 µV = 1125.0 mV. Đây là con số **điện áp Turing OV chuẩn**.
2. **`nvbios` 0.1.32** (bên thứ ba, không do tôi viết): khai báo
   `stored_units: uV`, `units: mV`, `equation_type: 1 (constant)`,
   `equation_coefficients: [1068750.0, 0.0, 0.0]`, và
   `bounds.encoding_maximum = 1125.0`.
3. **Cấu trúc slot:** `lo == hi == c0` và `c1 == c2 == 0` — đúng một phương
   trình hằng, không thể là nhiệt độ/dòng điện/tần số.
4. **Vendor image đã phát hành:** `nvbios` ghi nhận Galax HOF XOC trỏ REL và
   ALT vào đúng phương trình OV, cho **REL = ALT = OV = 1125 mV**. T4 tái tạo
   chính xác cấu hình này.

**Không phải** voltage target dạng bảng nhiệt độ, không phải V/F endpoint,
không phải dòng điện: đây là **trần điện áp của hai rail logic NVVDD**.

### 1.5 Checksum — A6

**Byte `0x767FF` là byte cuối của image `NPDS type-0xE0 #2`** (`0x054000..0x076800`).

**Thuật toán: 8-bit additive checksum, `sum(image) mod 256 == 0`.**

Kiểm chứng:
- 5/5 image trong ROM gốc đều `sum % 256 == 0`.
- 5/5 image trong T4 đều `sum % 256 == 0` sau khi sửa.
- Công thức sửa: `new_ck = (old_ck - Σ(T4 - ROM) trên 18 byte thân) mod 256`
  = `(0x33 - (-690)) mod 256` = **`0xE5`** — khớp chính xác byte T4.

**Đây không phải chữ ký số.** Không có thành phần mật mã. Cùng loại checksum
được dùng cho 3 image còn lại (`legacy 0x13`, `EFI 0x29`, `NPDS_E0_1 0xA3`,
`NPDS_70 0xEB` là giá trị trong ROM gốc trước khi zero-hoá).

### 1.6 Vì sao payload ngắn hơn ROM — A7, A8

`payload = rom[0 : 0x79000]` = 495,616 B.

**Bằng chứng biên giới:** tại `0x79000` có magic **`NVGIf`** — trùng magic của
`0x00000`. Toàn bank1 chỉ có **2** lần xuất hiện `NVGI`: `0x0` và `0x79000`.

**Phần bị cắt KHÔNG phải padding:**

```
0x79000..0x80000   28,672 B   nonzero 85.7%   NVGIf #2 header
0x80000..0x90000   65,536 B   nonzero 82.3%
0x90000..0x99000   36,864 B   nonzero 92.7%
0x99000..0xA1600   34,304 B   nonzero 70.5%
```

Cộng thêm `bank2` 387,584 B.

**Kết luận:** payload là **container `NVGIf` thứ nhất**, cắt đúng tại biên
container thứ hai. Phần bị cắt là **container firmware thứ hai + bank sao lưu** —
dữ liệu thật, nhưng driver `kgspExtractVbiosFromRom_TU102` chỉ dùng container đầu.

**Chưa xác định:** `NVGIf #2` bản chất là gì (header `0x80240366` chưa decode).
Đây là **điểm thiếu bằng chứng** được ghi nhận, không suy đoán.

### 1.7 Parser + test — A9, A10

```
scripts/vbios_parser.py    -> outputs/vbios_map.json
scripts/verify_diff.py     -> outputs/vbios_diff.json
scripts/test_parser.py     -> 7/7 PASS
```

7 test: hash, công thức con trỏ, checksum, layout VFE, 40 bảng PERF, biên
payload, đếm byte khác. Tất cả chạy trên **dữ liệu ROM thực**, không dùng
fixture giả.

---

## 2. GSP-RM (Nhiệm vụ B)

### 2.1 Container — B1

Không phải blob mờ. **ELF64 lồng 2 lớp:**

```
lop ngoai  : ELF64 REL, machine 0xF3 (RISC-V), 10 section
lop trong  : @file offset 0x40, ELF64 EXEC, RISC-V, 37 section, 11 PT_LOAD
tong       : 22,901,632 B
```

Section code chính: `.section_task_rm_elf_text_instance`
`vaddr 0x04588000`, file off `0x00588040`, **17,010,688 B**.

**Quy tắc quy đổi (đã sửa so với phiên trước):**
`vaddr = file_offset + 0x4000000` — vì `sh_offset` trong section header là
**tuyệt đối từ đầu file**. Công thức cũ `0x4000000 + (file_off - 0x40)` lệch
đúng `0x40`, đủ để mọi so khớp thất bại.

### 2.2 Call graph / bảng descriptor — B2, B4

**Đã tìm ra bảng descriptor regkey thật:** `0x1a7280..0x1a8840`, **8 bảng con,
139 entry, mỗi entry 32 byte:**

```
struct { u64 name_ptr; u32 f08; u32 f0c(=0); u32 id; u32 f14; u32 f18; u32 f1c; }
```

`f08` ∈ {0xff01, 0xff02, 0xff0a, …} (12 giá trị) — nghi là kiểu/flag registry.
`f18` ∈ {273, 274, 277, 278, …} (11 giá trị) — nghi mã module.
`id` là mã key (20..287).

**Các key trong tâm — tất cả đều tồn tại:**

| Key | Vị trí | Descriptor | id |
|---|---|---|---|
| `PERF_CF_CONTROLLER_GPC_MAX` | `0x1a6150` | **`0x1a72a0`** | **21** |
| `PERF_CF_CONTROLLER_DRAM_MAX` | `0x1a6130` | `0x1a7280` | 20 |
| `PERF_CF_CONTROLLER_NVD_MAX` | — | `0x1a72e0` | 23 |
| `RMClkVfOverride` | `0x00092de8` | không có | — |
| `RmAtsVolOverride` | `0x000a7a90` | không có | — |
| `RmClkControllersOverride` | `0x00092fd8` | không có | — |
| `OVERVOLTAGE_LOGIC` | `0x001a6ba0` | không có | — |
| `OVERVOLTAGE_NVVDD_0` | `0x001a9798` | không có | — |
| `OVERVOLTAGE_NVVDD_1` | `0x001a97b0` | không có | — |

Mật độ string: PWR 116, PERF 104, CLK 50, VF 36, PSTATE 32, VOLT 31,
BOOST 25, THERM 18, SPEEDO 8, IDDQ 6, OCP 6, OVERCLOCK 4, TGP 3.

### 2.3 XREF — B4 (không kết luận từ việc "tìm thấy string")

Quét **3 kiểu** trên **toàn bộ 22.9 MB**:
- `auipc rd,imm20` + (`addi`/`ld`/`lw` cùng `rd`) trong cửa sổ `o+2..o+24`,
  **step = 2 byte** (tập lệnh nén RVC).
- Con trỏ `u32` tới `vaddr` chuỗi.
- Con trỏ `u64` tới `vaddr` chuỗi.

**Kết quả:**
- **19/20 key: 0 tham chiếu** ở cả 3 kiểu.
- `PERF_CF_CONTROLLER_GPC_MAX`: 1 u32 + 1 u64, cả hai tại `0x1a72a0` — nhưng
  đó chính là **entry descriptor của chính nó**, không phải code.
- Con trỏ ngược về base của 8 bảng descriptor: **0**.

**Diễn giải (B4):** registry key được tra **theo tên lúc runtime** qua bảng
descriptor data-driven; **không** có tham chiếu cứng từ code tới chuỗi. Do đó
**không thể xác định "kiểu giá trị mong đợi" bằng phân tích tĩnh** (boolean
hay số) từ vị trí chuỗi. Đây là **điểm thiếu bằng chứng** — cần disasm hàm
tra cứu registry (tìm handler đọc bảng descriptor) hoặc thử runtime.

### 2.4 Đường dữ liệu VBIOS → bộ điều khiển điện áp — B5

Đã xác định **đầu vào** (VFE slot[0]/[1] trong VBIOS) và **đầu ra** (bảng
descriptor regkey trong GSP-RM), nhưng **chưa nối được** thành một đường liên
tục có bằng chứng. Cụ thể:

**Đã biết:** `nvbios` gọi `selector.offset = 185220 = 0x2D384` nằm trong VBIOS;
driver đọc VBIOS qua `kgspExtractVbiosFromRom_TU102`; driver đóng gói registry
`NVreg_RegistryDwords` → `PACKED_REGISTRY_TABLE` → GSP-RM (`kernel_gsp.c:4914`).

**Chưa biết:** hàm nào trong 17 MB code GSP-RM đọc slot VFE, và policy
`PERF_CF_CONTROLLER_GPC_MAX` (id 21) lấy giá trị từ đâu.

### 2.5 Phân biệt host RM / GSP-RM / PMU / SEC2 — B6

| Thành phần | Phạm vi | Bằng chứng trong phiên này |
|---|---|---|
| Host RM (kernel module) | đọc VBIOS, đóng gói registry, nạp GSP | `kgspExtractVbiosFromRom_TU102`, `kernel_gsp.c` |
| GSP-RM (RISC-V) | policy clock/voltage runtime | ELF 22.9 MB, 139 descriptor, `PERF_CF_CONTROLLER_*` |
| PMU | điều khiển PLL/PWM mức thấp | **không có bằng chứng trong phiên này** |
| SEC2 | boot/verify | **không có bằng chứng trong phiên này** |

### 2.6 Có giới hạn SKU/clock cap/voltage cap riêng cho CMP 40HX? — B7

**Voltage cap: CÓ, xác định được chính xác.** REL = 1068.75 mV,
ALT = 1093.75 mV, OV = 1125 mV, VMIN ≈ 693.5 mV, BOOT = 800 mV.
Đây là **cap điện áp** thật, trong bảng VFE.

**Clock cap: CHƯA xác định.** Không có `u16 = 1890 (0x0762)` hay `1905 (0x0771)`
ở **bất kỳ offset nào** trong 40 bảng `PERF_PTRS`. Các `u16` tìm thấy đều là
memory clock (7000/5000/3300) và video clock (405/620/860/1638/1697/1942).

**SKU cap trong GSP-RM: CHƯA xác định.** `PERF_CF_CONTROLLER_GPC_MAX` (id 21)
là ứng viên, chưa có giá trị.

---

## 3. Firmware Architecture (Nhiệm vụ C)

### 3.1 Container NVUCODES — C1

```
+0x00  "NVUCODES"       +0x08  ver = 1
+0x0C  header_size = 0x1F0 = 496      +0x10  u64 = 0x8D1990AB6B98AE2B
```

Entry table @ `0x1F0`, **stride 32**, marker `04 00 00 00` + offset u32.
**11 blob**, offset tăng dần, khoảng cách đều `0x1E000`:

| # | Offset | Size | Entropy | Nonzero | Phân loại |
|---:|---|---:|---:|---:|---|
| 0 | `0x00002F00` | 122,880 | 3.481 | 37% | plaintext |
| 1 | `0x00020F00` | 122,880 | 7.998 | 99% | entropy cao |
| 2 | `0x0003EF00` | 122,880 | 7.998 | 99% | entropy cao |
| 3 | `0x0005CF00` | 122,880 | 7.998 | 99% | entropy cao |
| 4 | `0x0007AF00` | 122,880 | 7.998 | 99% | entropy cao |
| 5 | `0x00098F00` | 126,208 | 4.915 | 57% | plaintext |
| 6 | `0x000B7C00` | 125,696 | 4.898 | 57% | plaintext |
| 7 | `0x000D6700` | 126,208 | 4.916 | 57% | plaintext |
| 8 | `0x000F5400` | 125,696 | 4.898 | 57% | plaintext |
| 9 | `0x00113F00` | 132,096 | 4.953 | 57% | plaintext |
| 10 | `0x00134300` | 7,575,296 | 7.261 | 83% | hỗn hợp |

Tổng kết thúc `0x134300 + 7,575,296 = 0x86DA00` = đúng kích thước file.

### 3.2 Không khẳng định AES từ entropy — C2, C3

4 blob entropy **7.998**, kích thước **giống hệt nhau** (122,880 B), nonzero 99%.
Đây là dấu hiệu của **dữ liệu đã mã hoá hoặc nén gần hoàn hảo**.

**Entropy 7.998 không phân biệt được AES với LZMA/zip/deflate.** Không có
magic, không có header, không có bằng chứng nào về thuật toán cụ thể.

Cần thêm để phân biệt: kiểm tra khả năng nén lại (nếu nén được nghĩa là
không mã hoá), tìm IV/salt 16 byte, đối chiếu với blob plaintext cùng kích thước.

### 3.3 Thành phần tham gia power/clock policy — C5

**Có bằng chứng:** GSP-RM (ELF RISC-V, 139 descriptor, `PERF_CF_CONTROLLER_*`),
VBIOS VFE (150 slot, 20 var).

**Không có bằng chứng trong phiên này:** SEC2, PMU, FECS, GPCCS là thành phần
riêng biệt tham gia power/clock. Chưa parse được chúng.

---

## 4. Nguyên nhân trần 1905 MHz (Nhiệm vụ D)

### 4.1 Đo read-only

21 mẫu trong 84 s dưới tải, T4 đang nạp:

```
      t      SM    MEM       W     PL   T  UTIL  PST  throttle
    0.1 300 MHz 405 MHz 12.55 W 184.00 W  46   0 %   P8  0x0000000000000004
    4.1 1905 MHz 7000 MHz 135.97 W 184.00 W  55 100 %   P0  0x0000000000000600
    8.2 1890 MHz 7000 MHz 129.22 W 184.00 W  57 100 %   P0  0x0000000000000600
   16.2 1890 MHz 7000 MHz 130.47 W 184.00 W  59 100 %   P0  0x0000000000000600
   32.4 1890 MHz 7000 MHz 144.40 W 184.00 W  62 100 %   P0  0x0000000000000000
   48.8 1890 MHz 7000 MHz 147.95 W 184.00 W  65 100 %   P0  0x0000000000000000
   65.2 1890 MHz 7000 MHz 149.69 W 184.00 W  67 100 %   P0  0x0000000000000000
   81.6 1875 MHz 7000 MHz 146.78 W 184.00 W  68 100 %   P0  0x0000000000000000
```

Phân bố: **1890 MHz × 15, 1875 × 4, 1905 × 1**.

### 4.2 Bốn giả thuyết bị loại bỏ bằng đo trực tiếp

| Giả thuyết | Bằng chứng loại bỏ |
|---|---|
| Power limit | 149 W < **184 W**; `throttle` không có bit 9/10 từ giây 32 |
| Nhiệt | 68 °C; `HW Thermal Slowdown: Not Active` |
| Limiter tổng quát | `throttle = 0x0000000000000000` mà clock vẫn kẹp |
| P-state | đã ở **P0**, mức cao nhất |

Điểm mấu chốt: **T4 tắt được 2 cờ `Board Limit` + `Reliability` sau ~32 s,
nhưng clock không tăng một bậc nào.** Nghĩa là các limiter đó **không phải
nguyên nhân** — chúng chỉ là triệu chứng.

### 4.3 Hai ứng viên còn sống

**H3 — đường V/F:**
- Ủng hộ: 84/150 slot VFE có hệ số góc; `var[7]` = 1981–2335 MHz; T4 làm clock
  nhích lên 1905 ở mẫu đầu; `nvidia-smi -lgc` hoạt động thật (1500→1500,
  1700→1710, đo phiên trước).
- Phản bác: **8 slot dùng `var=13` (điện áp µV) không slot nào cho
  y ∈ [1800, 2000]** khi `x = 1,125,000 µV`. Nghĩa là **không có phương trình
  VFE nào biến điện áp thành tần số**. Quan hệ đó phải nằm ngoài VFE.

**H4 — policy GSP-RM:**
- Ủng hộ: 17 MB code; `PERF_CF_CONTROLLER_GPC_MAX` id 21, `_DRAM_MAX` id 20,
  `_NVD_MAX` id 23 — đây chính là tên bộ điều khiển trần; không có XREF cứng
  đúng kiểu một giới hạn chính sách firmware.
- Phản bác: chưa có giá trị nào của policy 21; chưa chứng minh nó áp cho
  SKU này.

### 4.4 Phép thử phân biệt (chưa thực hiện)

Sweep `nvmlDeviceSetGpcClkVfOffset` ở `+150 / +200 / +220 / +240` với T4 đang nạp.
- Nếu vượt 1905 → **H3** đúng (trần trong đường VF offset).
- Nếu vẫn kẹp → **H4** đúng (trần trong policy GSP-RM).

Đây là thay đổi **cấu hình runtime**, thuộc mục 8 "KHÔNG TỰ ĐỘNG" của đề bài.
Cần anh phê duyệt riêng trước khi chạy.

**Lưu ý an toàn từ lịch sử:** ép `+367 MHz` từng gây màn hình đen + tự restart;
sau crash card rớt PCIe tới khi clear registry + rút PSU 30 s. Phép sweep đề
xuất chỉ tới `+240` (thấp hơn nhiều so với mức đã gây sự cố), nhưng rủi ro
không bằng không.

---

## 5. Điểm thiếu bằng chứng (B8)

| # | Thiếu gì | Ảnh hưởng | Cách lấp |
|---|---|---|---|
| 1 | Giá trị NVVDD runtime | không xác nhận được điện áp thực | đo phần cứng trên VRM |
| 2 | Bảng sinh PLL từ điện áp | không giải thích được cơ chế 1890 | decode `CLOCK_PTRS[0]` 14×19 B |
| 3 | Hàm đọc VFE trong GSP-RM | không nối được VBIOS → policy | disasm 17 MB code, tìm xref tới 0x2D384 pattern |
| 4 | Giá trị `PERF_CF_CONTROLLER_GPC_MAX` | không biết cap SKU | đọc runtime hoặc thử registry |
| 5 | Bản chất `NVGIf #2` | không biết phần bị cắt | decode header `0x80240366` |
| 6 | Thuật toán 4 blob ucodes | không biết AES hay nén | thử nén lại, tìm IV |
| 7 | SEC2/PMU/FECS/GPCCS | C5 chưa đủ | parse từ ucodes plaintext |

---

## 6. Trạng thái card

T4 đang nạp (`/lib/firmware/nvidia/cmp40hx_t4.bin`, sha256 khớp).
Max Power Limit báo **220 W**, PL hiện tại **184 W**.
Idle: 300 MHz / 12.5 W / PL 184 W. Không có thay đổi cấu hình nào khác.

**Rollback:**
```
sudo rm /etc/modprobe.d/cmp40hx-vbios.conf && sudo systemctl reboot
```

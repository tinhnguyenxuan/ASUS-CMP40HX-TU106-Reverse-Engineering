# EVIDENCE LEDGER — CMP 40HX

Mỗi mục: nguồn / hash / offset / output thực tế / diễn giải / độ tin.
Quy ước độ tin: **CAO** = đo trực tiếp hoặc khớp ground truth độc lập;
**TRUNG BÌNH** = suy ra từ cấu trúc đã kiểm; **THẤP** = giả thuyết chưa kiểm.

---

## E01 — Định danh file

| Trường | Giá trị |
|---|---|
| Source | `outputs/CMP40HX_ORIGINAL_1MB.bin` |
| SHA-256 | `dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec` |
| Size | 1,048,576 B |
| Source | `outputs/cmp40hx_t4.bin` |
| SHA-256 | `aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb` |
| Size | 495,616 B |
| Output | `VERIFIED` — khớp hash đề bài cung cấp |

Độ tin: **CAO** (băm lại trực tiếp).

---

## E02 — 19 byte khác biệt

Command: `scripts/verify_diff.py`

```
0x05669c: 0x70 -> 0x40    0x05669d: 0x76 -> 0x54    0x05669e: 0x82 -> 0x89
0x0566a0: 0x70 -> 0x40    0x0566a1: 0x76 -> 0x54    0x0566a2: 0x82 -> 0x89
0x0566a4: 0x70 -> 0x40    0x0566a5: 0x76 -> 0x54    0x0566a6: 0x82 -> 0x89
0x0566b4: 0xb0 -> 0x40    0x0566b5: 0x83 -> 0x54    0x0566b6: 0x85 -> 0x89
0x0566b8: 0xb0 -> 0x40    0x0566b9: 0x83 -> 0x54    0x0566ba: 0x85 -> 0x89
0x0566bc: 0xb0 -> 0x40    0x0566bd: 0x83 -> 0x54    0x0566be: 0x85 -> 0x89
0x0767ff: 0x33 -> 0xe5
```

18 byte đầu = 6 field float32 (3 byte thấp mỗi field; byte cao `0x49` giữ nguyên).
Byte 19 = checksum.

Độ tin: **CAO**.

---

## E03 — Xác định 6 field float32 là điện áp microvolt

**Bằng chứng độc lập #1 — IEEE-754 decode:**

| Offset | ROM (µV) | T4 (µV) | ROM (mV) | T4 (mV) |
|---|---:|---:|---:|---:|
| `0x5669C` | 1,068,750 | 1,125,000 | 1068.75 | 1125.00 |
| `0x566A0` | 1,068,750 | 1,125,000 | 1068.75 | 1125.00 |
| `0x566A4` | 1,068,750 | 1,125,000 | 1068.75 | 1125.00 |
| `0x566B4` | 1,093,750 | 1,125,000 | 1093.75 | 1125.00 |
| `0x566B8` | 1,093,750 | 1,125,000 | 1093.75 | 1125.00 |
| `0x566BC` | 1,093,750 | 1,125,000 | 1093.75 | 1125.00 |

**Bằng chứng độc lập #2 — `nvbios` 0.1.32 (công cụ bên thứ ba):**

```
key: nvvdd_rel_fixed_mv
  equation_offset: 353945 = 0x56699      <- TRUNG base slot[0]
  equation_type: 1                       <- constant equation
  equation_coefficients: [1068750.0, 0.0, 0.0]
  stored_units: uV
  units: mV
  bounds: {encoding_minimum: 1068.75, encoding_maximum: 1125.0,
           minimum: 1068.75, maximum: 1093.75}

key: nvvdd_alt_fixed_mv
  equation_offset: 353969 = 0x566B1      <- TRUNG base slot[1]
  equation_coefficients: [1093750.0, 0.0, 0.0]
  bounds: {encoding_minimum: 1093.75, encoding_maximum: 1125.0}

key: nvvdd_ov_equation_max_mv
  equation_offset: 354017 = 0x566E1      <- TRUNG base slot[3]
  current: 1125.0
  runtime_role_candidate: OV
```

**Bằng chứng độc lập #3 — quan hệ min/max/c0 trong slot:**

slot[0]: `lo = hi = c0 = 1068750.0`, `c1 = c2 = 0`
slot[1]: `lo = hi = c0 = 1093750.0`, `c1 = c2 = 0`

Cả 3 trường trùng nhau và hệ số góc bằng 0 → đây là **phương trình hằng**,
đúng như `nvbios` gọi `equation_type: 1`.

**Bằng chứng độc lập #4 — cấu hình vendor đã biết:**
`nvbios` ghi nhận *"the Galax HOF XOC image points REL and ALT at the OV
equation (REL = ALT = OV = 1125 mV)"*. T4 làm đúng điều này: REL và ALT đều
thành 1125 mV, bằng OV. Đây là cấu hình mà một nhà sản xuất đã phát hành.

**Kết luận:** 6 field là **điện áp NVVDD, đơn vị microvolt**.
REL (reliability voltage) và ALT (alternative/VOP) nâng từ 1068.75 / 1093.75
lên **1125 mV** = mức trần OV (overvoltage) mà chính VBIOS đã khai báo.

Độ tin: **CAO** cho "là điện áp µV". Độ tin **CAO** cho "là REL/ALT".
Độ tin **THẤP** cho "firmware chấp nhận giá trị này khi chạy" — xem E07.

---

## E04 — Checksum: `sum(image) mod 256 == 0`

Command: `scripts/verify_diff.py`, `scripts/test_parser.py::test_checksum`

```
image        vung                      ROM     T4  ket luan
legacy1      0x028600..0x037a00        0x00  0x00  OK
EFI1         0x037a00..0x048a00        0x00  0x00  OK
NPDS_E0_1    0x048a00..0x054000        0x00  0x00  OK
NPDS_E0_2    0x054000..0x076800        0x00  0x00  OK
NPDS_70      0x076800..0x078400        0x00  0x00  OK
```

Byte `0x767FF` là **byte checksum của image NPDS_E0_2**, tại vị trí
`0x076800 - 1` (byte cuối image).

Công thức sửa:
```
Σ(T4 - ROM) trên 18 byte thân = -690
new_ck = (old_ck - Σ(Δ)) mod 256
       = (0x33 - (-690)) mod 256
       = 0xE5            <- khớp CHÍNH XÁC byte T4
```

Tương đương: sau khi sửa, tổng toàn image vẫn `≡ 0 (mod 256)`.
Thuật toán là **8-bit additive checksum**, không phải CRC, không phải SHA.
Đây chỉ là kiểm tra toàn vẹn — **không phải chữ ký**, không có thành phần mật mã.

Độ tin: **CAO** (số học tái lập được, 5/5 image đều thoả).

---

## E05 — Vì sao payload = 495,616 B

Command: `scripts/verify_diff.py`, `scripts/test_parser.py::test_payload_boundary`

```
ROM 1 MiB:
  bank1  0x000000..0x0A1600   660,992 B
  bank2  0x0A1600..0x100000   387,584 B
  bank1 == bank2 ? False

payload = rom[0:0x79000] = 495,616 B
```

**Bằng chứng biên giới:** `0x79000` bắt đầu bằng magic **`NVGIf`**.

```
0x79000  4e 56 47 49 66 03 24 80 2c 03 00 00 43 10 04 88  NVGIf...$...,...C..
         02 02 00 00 24 00 00 00 00 00 04 d4 71 44 00 01
0x00000  4e 56 47 49 ...                                  NVGIf (container 1)
```

Chỉ có **2** hit `NVGI` trong toàn bank1: `0x0` và `0x79000`.

**Nội dung bị cắt (`0x79000..0xA1600` = 165,376 B):** KHÔNG phải padding.

```
0x79000..0x80000   28,672 B  nonzero 85.7%   "NVGIf" container 2
0x80000..0x90000   65,536 B  nonzero 82.3%   du lieu
0x90000..0x99000   36,864 B  nonzero 92.7%   du lieu
0x99000..0xA1600   34,304 B  nonzero 70.5%   du lieu
```

**Vùng `0x78400..0x79000` (3,072 B)** là `0xFF` toàn bộ — padding căn lề cuối
NPDS_70, không phải dữ liệu.

**`bank2` (`0x0A1600..0x100000`) là bản sao thứ hai** của image. Không có
magic `NVGI` trong bank2.

**Kết luận:** payload 495,616 B là **container thứ nhất (`NVGIf` #1) cắt tại
biên `NVGIf` #2**. Phần bị cắt là **container firmware thứ hai + bản bank thứ
hai** — dữ liệu thật, nhưng driver `kgspExtractVbiosFromRom_TU102` chỉ dùng
container đầu.

**Chưa xác định (THẤP):** `NVGIf #2` là gì. Header `0x80240366` chưa decode.
Chưa biết nó có phải firmware/BIOS kép cho chế độ khác hay không.

Độ tin: **CAO** cho biên giới; **THẤP** cho bản chất `NVGIf #2`.

---

## E06 — Cấu trúc record chứa 6 field

**Container:** `NPDS` type `0xE0` #2, `0x054000..0x076800` (141,312 B).

**Bảng rail (Turing rail 1x)** @ `0x5649C`:
```
30 09 19 14 18 96 c8 0f 28 04 00 00 00 00 00 00 fe 42 11 14 01 01 00 00
ver=0x30  hdr_size=9  entry_size=25  count=20  row_index=24
```

**VFE (Voltage/Frequency Equation) table** — header `30 09 19 14 18`:

| Trường | Giá trị |
|---|---|
| Base slot | `0x56699` |
| Slot stride | **24 byte** |
| Slot count | **150** (`0x96`) |
| Var base | `0x564A5` |
| Var stride | **25 byte** |
| Var count | **20** (`0x14`) |

**Layout slot 24 byte** (float **không căn lề 4** — đọc unaligned):

```
+0x00 u8   type          (1=constant, 2=minmax-ish, 3=?, 4=compare)
+0x01 u8   var_idx       (biến đầu vào x)
+0x02 u8   next          (255 = không nối)
+0x03 f32  lo            (clamp dưới)
+0x07 f32  hi            (clamp trên)
+0x0B f32  c0            (hệ số hằng)
+0x0F f32  c1            (hệ số bậc 1)
+0x13 f32  c2            (hệ số bậc 2)
+0x17 u8   flags         (0x02)
```

**Slot chứa 6 field:**

| Offset | Slot | Trường trong slot | Vai trò |
|---|---|---|---|
| `0x5669C` | slot[0] | `+0x03` lo | NVVDD **REL** |
| `0x566A0` | slot[0] | `+0x07` hi | NVVDD **REL** |
| `0x566A4` | slot[0] | `+0x0B` c0 | NVVDD **REL** |
| `0x566B4` | slot[1] | `+0x03` lo | NVVDD **ALT/VOP** |
| `0x566B8` | slot[1] | `+0x07` hi | NVVDD **ALT/VOP** |
| `0x566BC` | slot[1] | `+0x0B` c0 | NVVDD **ALT/VOP** |

**Selector** @ `0x2D384` = `00 01 03 00 02 04`:
`REL=0, ALT=1, OV=3, BOOT=0, VMIN=2, ?=4` — **không đổi** giữa ROM và T4.

Độ tin: **CAO** (khớp `nvbios equation_offset`, `selector.offset = 185220 = 0x2D384`).

---

## E07 — Đo runtime: trần 1905 MHz KHÔNG do limiter, KHÔNG do power

Command: `scripts/sample_load.py` (target `<REDACTED_LAB_IP>`, T4 đang nạp)

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

  SM clock duoi tai: min=1875 max=1905 tb=1888 MHz
  phan bo: [(1890, 15), (1875, 4), (1905, 1)]
  throttle active: {'0x0000000000000004', '0x0000000000000000', '0x0000000000000600'}
```

**Đọc bit throttle:** `0x0000...0000` = không cờ nào bật.
`0x0000...0600` = bit 9 + bit 10 (`SW Power Cap` + `Board Limit`).

**Sự kiện quyết định:** từ giây **32.4** trở đi, throttle = **`0x0000...0000`**
(hoàn toàn sạch) nhưng clock **vẫn kẹp 1890 MHz** ở **149 W < PL 184 W**, nhiệt
độ **68 °C**.

Với T4 (REL/ALT = 1125 mV), hai cờ `Board Limit` và `Reliability` chuyển sang
`Not Active` sau ~32 s — nhưng **clock không tăng một bậc nào**.

Độ tin: **CAO** (đo trực tiếp 21 mẫu, tái lập được).

---

## E08 — GSP-RM: cấu trúc ELF và bảng descriptor

Command: `scripts/gsp_scan.py`, `scripts/gsp_descriptors.py`

**Container (B1):**
```
file 22,901,632 B
lop ngoai: ELF64 REL, machine 0xF3 (RISC-V), 10 section
lop trong @0x40: ELF64 EXEC, machine RISC-V, 37 section, 11 PT_LOAD

.section_task_rm_elf_rodata_instance   vaddr 0x0401D000  1,982,464 B
.section_task_rm_elf_data_instance     vaddr 0x04201000  3,698,688 B
.section_task_rm_elf_text_instance     vaddr 0x04588000 17,010,688 B
```

**Quy tắc quy đổi vaddr (đã sửa):** `sh_offset` trong section header là
**tuyệt đối từ đầu file**, nên `vaddr = file_offset + 0x4000000` cho mọi
section trong `PT_LOAD`. Công thức cũ `0x4000000 + (file_off - 0x40)` **sai
0x40**.

**Bảng descriptor regkey** @ `0x1a7280..0x1a8840`, **entry 32 byte**:

```
{u64 name_ptr; u32 f08; u32 f0c=0; u32 id; u32 f14; u32 f18; u32 f1c}
```

8 bảng, **139 entry** đọc được. `f08` có 12 giá trị (0xff02, 0xff01, 0xff0a…),
`f18` là mã module (273, 274, 277, 278…), `id` là mã key.

**Các key trong tâm (B3) — TẤT CẢ đều tồn tại:**

| Key | File offset | Descriptor entry | id |
|---|---|---|---|
| `PERF_CF_CONTROLLER_GPC_MAX` | `0x1a6150` | `0x1a72a0` | **21** |
| `PERF_CF_CONTROLLER_DRAM_MAX` | `0x1a6130` | `0x1a7280` | 20 |
| `PERF_CF_CONTROLLER_NVD_MAX` | — | `0x1a72e0` | 23 |
| `RMClkVfOverride` | `0x00092de8` | không có | — |
| `RmAtsVolOverride` | `0x000a7a90` | không có | — |
| `RmClkControllersOverride` | `0x00092fd8` | không có | — |
| `OVERVOLTAGE_LOGIC` | `0x001a6ba0` | không có | — |
| `OVERVOLTAGE_NVVDD_0` | `0x001a9798` | không có | — |
| `OVERVOLTAGE_NVVDD_1` | `0x001a97b0` | không có | — |

**Mật độ string theo chủ đề:** PWR 116, PERF 104, CLK 50, VF 36, PSTATE 32,
VOLT 31, BOOST 25, THERM 18, SPEEDO 8, IDDQ 6, OCP 6, OVERCLOCK 4, TGP 3.

**XREF (B4):** quét `auipc+addi` step=2 với cửa sổ `o+2..o+24`, cộng u32/u64
pointer, trên **toàn bộ 22.9 MB**:
- 19/20 key: **0 tham chiếu** ở cả 3 kiểu
- `PERF_CF_CONTROLLER_GPC_MAX`: **1 u32 + 1 u64**, cả hai tại `0x1a72a0` —
  nhưng đó chính là **entry descriptor của chính nó**, không phải code.
- Con trỏ ngược về base của 8 bảng descriptor: **0**

**Kết luận B4:** Không có XREF cứng nào từ code tới chuỗi key. Registry key
được tra **theo tên lúc runtime** qua bảng descriptor data-driven. Do đó
**không thể đọc "kiểu giá trị mong đợi" bằng phân tích tĩnh** từ vị trí chuỗi.

Độ tin: **CAO** cho cấu trúc + vị trí; **CAO** cho "không có XREF cứng".

---

## E09 — Firmware container (C1)

Command: `scripts/gsp_scan.py` + phân tích `ucodes_tu10x.bin`

**NVUCODES header:**
```
+0x00  "NVUCODES"
+0x08  ver = 1
+0x0C  header_size = 0x1F0 = 496
+0x10  u64 = 0x8D1990AB6B98AE2B
```

Entry table @ `0x1F0`, **stride 32**, marker `04 00 00 00` + offset u32.
**11 blob**, offset tăng dần, khoảng cách đều `0x1E000`:

| # | Offset | Size | Entropy | Nonzero | Loại |
|---:|---|---:|---:|---:|---|
| 0 | `0x00002F00` | 122,880 | 3.481 | 37% | plaintext |
| 1 | `0x00020F00` | 122,880 | **7.998** | 99% | entropy cao |
| 2 | `0x0003EF00` | 122,880 | **7.998** | 99% | entropy cao |
| 3 | `0x0005CF00` | 122,880 | **7.998** | 99% | entropy cao |
| 4 | `0x0007AF00` | 122,880 | **7.998** | 99% | entropy cao |
| 5 | `0x00098F00` | 126,208 | 4.915 | 57% | plaintext |
| 6 | `0x000B7C00` | 125,696 | 4.898 | 57% | plaintext |
| 7 | `0x000D6700` | 126,208 | 4.916 | 57% | plaintext |
| 8 | `0x000F5400` | 125,696 | 4.898 | 57% | plaintext |
| 9 | `0x00113F00` | 132,096 | 4.953 | 57% | plaintext |
| 10 | `0x00134300` | 7,575,296 | 7.261 | 83% | hỗn hợp |

**C2 — không khẳng định AES từ entropy (theo yêu cầu C3):**
4 blob entropy 7.998, kích thước giống hệt nhau (122,880 B), nonzero 99%.
Đây là **dấu hiệu của dữ liệu đã mã hoá hoặc nén gần hoàn hảo**. Entropy cao
**không phân biệt** được AES với LZMA/zip. Không có bằng chứng thuật toán cụ
thể nào từ dữ liệu hiện có.

Độ tin: **CAO** cho header/offset/size/entropy; **THẤP** cho "là AES".

---

## E10 — Fuse / OTP (không thực hiện trong phiên này)

Theo quy tắc an toàn mục 8, **không ghi fuse**. Dữ liệu fuse đã có từ phiên
trước (`fuse_tu106.json`, 1536 word) nhưng **không dùng làm bằng chứng mới**
trong báo cáo này vì chưa đối chứng lại.

---

## Bảng tổng hợp độ tin

| Kết luận | Độ tin | Cơ sở |
|---|---|---|
| 6 field = điện áp NVVDD µV | **CAO** | IEEE-754 + nvbios + hằng số + vendor image |
| REL/ALT nâng lên 1125 mV | **CAO** | slot[0]/[1] + selector không đổi |
| Checksum 8-bit additive | **CAO** | 5/5 image + công thức khớp byte |
| Payload = `rom[0:0x79000]` | **CAO** | magic `NVGIf` tại biên |
| Phần cắt là dữ liệu thật | **CAO** | nonzero 70–93% |
| `NVGIf #2` là gì | **THẤP** | header chưa decode |
| GSP-RM 139 entry descriptor | **CAO** | parse + đếm |
| Không có XREF cứng tới key | **CAO** | quét 3 kiểu trên 22.9 MB |
| Trần 1905 không do limiter | **CAO** | throttle `0x0` mà clock kẹp |
| 4 blob ucodes mã hoá | **TRUNG BÌNH** | entropy — không phân biệt AES/nén |

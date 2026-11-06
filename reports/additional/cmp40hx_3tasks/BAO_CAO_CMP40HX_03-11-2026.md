# BÁO CÁO RE CMP 40HX — TỪ LÚC GIAO ĐẾN BÂY GIỜ

Card: NVIDIA CMP 40HX (TU106-100-A1), `10DE:1F0B`, subsystem `8804:1043`
Board: CG161P REV 2.00 (PCB ASUS DUAL-RTX2060S-O8G-EVO-V2)
Host: X99-TF + E5-2696 v3, kernel 6.8.0-147-generic
Ngày: 03/11/2026

---

## 1. KẾT QUẢ LỚN NHẤT: VBIOS OVERRIDE QUA RAM CHẠY ĐƯỢC

Đây là điều **trước đây bị chặn hoàn toàn** và là nền tảng cho mọi thí nghiệm sau.

### Chuỗi log chứng minh (dmesg)
```
_kgspVbiosOverridePrepare: enter prepare
  disable(49,0) mode(0,2) size(0,495616)      <- 3 key doc duoc, mode=2, size dung
  readBinary status=0x0 actual=495616 want=495616   <- file doc thanh cong
  FindLegacy=1  skip=0x28600  pciId=0x1f0b10de      <- tim thay dung 1 legacy image
  creating memdesc allocSize=331776                 <- cap phat bo nho
  map status=0x0  va=FFFFD18401169000               <- map vao GSP thanh cong
```
Sau đó `nvidia-smi` báo **`Max Power Limit: 240.00 W`** thay vì 220 W mặc định, và
`nvidia-smi -pl 240` ăn thật (184 → 240 W).

### Cấu hình đã dùng
`/etc/modprobe.d/cmp40hx-vbios.conf`:
```
options nvidia NVreg_RegistryDwords="RmLinuxVbiosOverride=2;RmLinuxVbiosOverrideSize=495616"
options nvidia NVreg_RegistryBinaryFilePerDevice="pci=0000:03:00.0;RmLinuxVbiosOverrideImage=cmp40hx_xxx.bin"
```
Payload đặt tại `/lib/firmware/nvidia/` (driver dùng `request_firmware`).

### Ba lỗi đã tìm ra và sửa
| Lỗi | Triệu chứng | Nguyên nhân thật |
|---|---|---|
| Payload 312.5 KiB | booter fail `0x29`, card rớt PCIe | Thiếu `0x76800–0x79000` (NPDS type-0x70 digest list). Payload đúng = **495,616 B** theo `nvbios normalize`, kernel tự skip `0x28600` |
| Gộp 3 key vào 1 directive | card rớt | Parser `RegistryBinaryFilePerDevice` coi mọi value là đường dẫn file → `=2` bị hiểu là file `nvidia/2`. Phải **tách 2 directive** |
| Nghi thiếu cmpunlocker | — | Sai. `grep -c CMP40_COMPUTE_UNLOCK` = 4 hit, cả 2 patch đều có |

### Điều này chứng minh gì
Docs `Panchovix/nvidia-vbios-vix-loader` ghi *"not tested on any Turing GPU"*.
Đây là **lần đầu VBIOS override qua RAM được xác nhận chạy trên Turing/CMP**.
Không flash ROM. Sai thì `rm modprobe.d` + reboot là sạch.

---

## 2. VFE (VOLTAGE/FREQUENCY EQUATION) — LAYOUT ĐÚNG

Trước đây đoán sai (`base 0x5669C`, float align 4). **Ground truth lấy từ `nvbios fields`:**

```
nvvdd_rel_equation_max_mv  equation_offset = 353945 = 0x56699
nvvdd_alt_equation_max_mv  equation_offset = 353969 = 0x566B1  (+24)
nvvdd_ov_equation_max_mv   equation_offset = 354017 = 0x566E1  (+48)
nvvdd_vmin_mv              equation_offset = 354041 = 0x566F9  (+24)
selector index             offset          = 185220 = 0x2D384
```

### Layout slot 24 byte (float KHÔNG align 4)
```
+0   u8   type       1 = constant/quadratic, 3 = clamp pair, 4 = opaque
+1   u8   var_idx    biến đầu vào đã dùng (7, 12, 255=none, 9, 13...)
+2   u8   next       0xff = hết chuỗi
+3   f32  clamp_lo
+7   f32  clamp_hi
+11  f32  c0
+15  f32  c1
+19  f32  c2
+23  u8   flags      0x02
```
Công thức: `y = c0 + c1*x + c2*x²`, clamp vào `[clamp_lo, clamp_hi]`.

### Kiểm chứng 4/4 hằng số điện áp khớp `nvbios`
| Slot | Vai trò | c0 (µV) | Ground truth | |
|---|---|---|---|---|
| 0 | REL | 1,068,750 | 1068.75 mV | OK |
| 1 | ALT | 1,093,750 | 1093.75 mV | OK |
| 3 | OV | 1,125,000 | 1125.0 mV | OK |
| 4 | VMIN | 693,500 | 693.5 mV | OK |

`selector @0x2D384 = 00 01 03` → REL=slot0, ALT=slot1, OV=slot3.
**VMIN không nằm trong selector array** — lấy từ `equation_offset 354041` → slot 4.

### Thống kê 150 slot
- 66 hằng số, 68 tuyến tính, 16 bậc 2
- type: 1 → 89 slot, 3 → 25, 0 → 29, 2 → 6, 4 → 1
- var hay dùng: 7 (56 slot), 12 (37), none (29), 9 (11), 13 (8)

### Slot đáng chú ý đã giải
- `slot[7] = 50000 − 714.2857x` trên `[0, 75000]`; `714.2857 = 50000/70` → **PWM fan 50000→0 trên dải 0..70**
- `slot[10] = −1838.23 + 1.114014x − 0.00016x²`; `−c0/a = 1650.1` = boot clock 1650 MHz
- `slot[41]` / `slot[44]` chênh **1366.1 mV**, hệ số **317.5163 µV/nấc**, lặp 10 lần

Công cụ: `vfe_real.py` (có assert 4/4 hằng số).

---

## 3. CHECKSUM VBIOS — ĐÃ GIẢI (kết luận cũ SAI)

**Thuật toán: `sum(bytes từ đầu image đến hết) % 256 == 0`**

Xác nhận bằng thực nghiệm: sửa 1 byte → tổng lệch đúng `+1`.

### 9/9 image đều hợp lệ
| Image | Offset | Byte checksum |
|---|---|---|
| legacy #1 | `0x028600`–`0x037A00` | `0x13` @`0x379FF` |
| EFI #1 | `0x037A00`–`0x048A00` | `0x29` @`0x489FF` |
| NPDS-E0 #1 | `0x048A00`–`0x054000` | `0xA3` @`0x53FFF` |
| NPDS-E0 #2 | `0x054000`–`0x076800` | `0x33` @`0x767FF` |
| NPDS-70 | `0x076800`–`0x078400` | `0xEB` @`0x783FF` |
| legacy #2 | `0x0A1600`–`0x0B0A00` | `0x13` |
| EFI #2 | `0x0B0A00`–`0x0C1A00` | `0x29` |
| NPDS-E0 #3 | `0x0C1A00`–`0x0CD000` | `0xA3` |
| NPDS-E0 #4 | `0x0CD000`–`0x0EF800` | `0x33` |

Kết luận cũ "checksum chưa giải" là **SAI do cộng sai biên** (`0x76800` thay vì `0x78400`).
Không có chữ ký crypto nào được kiểm tra ở đường này.

---

## 4. PERF_PTRS — TOÀN BỘ 40 BẢNG ĐÃ GIẢI

`PERF_PTRS` @`0x288D4`, **56 con trỏ u32**, 49 con trỏ khác null.

### Công thức con trỏ (rẽ nhánh có điều kiện)
```
at = 0x28600 + ptr
if ptr >= 0xF400:  at += 0x11000    # nhảy qua EFI image
```

### Layout header — xác nhận 100% bằng 3 bảng đã biết
```
byte0 = ver
byte1 = hdr_size
byte2 = entry_size
byte3 = count
```
- THERMAL `10 0a 28 04` → 4 × 40 B  ✓
- FAN     `10 06 1a 02` → 2 × 26 B  ✓
- POWER   `30 2c 42 14` → 20 × 66 B ✓

### Địa chỉ đã xác định
| PERF_PTRS | ROM | Bảng |
|---|---|---|
| [8] `0x1CE9C` | `0x5649C` | VFE rail header |
| [11] `0x1E892` | `0x57E92` | POWER TABLE (20 × 66 B) |
| [20] `0x1F079` | `0x58679` | THERMAL (4 × 40 B) |
| [22] `0x1F224` | `0x58824` | FAN (2 × 26 B) |
| [26] `0x4D7B` | `0x2D37B` | rail row (selector VFE) |
| [2] `0x1BAC4` | `0x550C4` | timing set (12 × 74 B) |

Tổng: **40 bảng / 21,179 B** = 11% vùng legacy+EFI+NPDS1.

### Phát hiện: PERF_PTRS[17] và [1] trỏ CÙNG vùng
`0x545F2 + 14 = 0x54600`. Nghĩa là `0x545F2` chỉ là **header 14 B dẫn vào bảng `0x54600`**,
không phải bảng 183 × 70 B riêng như header gợi ý.

Bảng `0x54600` có **stride 33 B thật**, mỗi entry chứa cặp pattern
`05 64 xx 50 06 05 00` / `01 85 01 40` → **đây là script cấu hình thanh ghi**,
không phải bảng số liệu. Disasm x86 ra rác → đây là **opcode engine riêng của NVIDIA**
(devinit sequencer), chưa decode được sang `(addr, data)`.

Công cụ: `perf_tables.py` (có assert khớp THERMAL/FAN/POWER).

---

## 5. BẢN ĐỒ CONTAINER 1 MB — ĐÃ MAP 100%

```
0x000000–0x028600  header + BIT + cac bang nho
0x028600–0x037A00  legacy x86 #1     (0xF400,   PCIR@0x28770)
0x037A00–0x048A00  EFI #1            (0x11000,  PCIR@0x37A1C)
0x048A00–0x054000  NPDS type 0xE0 #1 (0xB600)   <- self-test + devinit script
0x054000–0x076800  NPDS type 0xE0 #2 (0x22800)  <- NOP padding + 11 khoi PCGI
0x076800–0x078400  NPDS type 0x70    (0x1C00)   <- KHOI CHU KY
0x078400–0x079000  toan 0xFF
0x0A1600–0x0B0A00  legacy x86 #2  (BAN SAO Y HET #1)
0x0B0A00–0x0C1A00  EFI #2        (BAN SAO Y HET #1)
0x0C1A00–0x0CD000  NPDS-E0 #3    (BAN SAO)
0x0CD000–0x0EF800  NPDS-E0 #4    (BAN SAO)
0x0EF800–0x0F9E00  container "VN" #2 (khoi chu ky + tag)
0x0F9E00–0x0FA500  container "VN" #3 = NPDE
0x0FA500–0x100000  du lieu con lai
```

**Hai bank giống hệt 100%** — 0 byte khác trên 62,464 B legacy + 69,632 B EFI.
ROM chứa 2 bản sao y nhau, không phải 2 cấu hình khác nhau.

### Checksum không phải `sum(whole ROM)` — mỗi image tự có checksum riêng.

---

## 6. KHỐI CHỮ KÝ — ĐÃ GIẢI CẤU TRÚC

Tại `0x076838`:
```
IBSN @0x76838  sig 'IBSN', size 12, ver 1.1, type 'BV', 3 word hash
IBVL @0x7684b  sig 'IBVL', size 26, ver 1, count 14
  @0x76884  "13244asus"      <- BOARD ID thuc
  @0x7689a  "B113690..."     <- serial/part
  ...14 entry x 32 B, trong do 10 entry toan hash ngau nhien = SIGNED DIGEST LIST
RKSL @0x76a9e  "NVPartner Prod" + len 0x39
NVIDIA @0x76ac1  len 0x23/0x79/0x09 + 32 B hash = cert/pubkey
NVIDIA Corp @0x76ec7  + 48 B hash
```

---

## 7. NPDE — CONTAINER PART NUMBER (vùng chưa ai reverse)

Tại `0x0F9E40`, header `NPDE 00 01 0c 00 2e 00 80 04` (ver 0, hdr 1, count 0x0C=12),
gồm 6 sub-block:

| Offset | Block | Nội dung |
|---|---|---|
| `0x0F9FE0` | `ISBN` | size 16, ver 3.1, `"RIBILU"` |
| `0x0F9FEA` | `RIBI` | `"RIBILU"` + `"RI"` + `0x40` |
| `0x0FA000` | `JFFS` | ver 2, len 0x40 |
| `0x0FA0B7` | `GXIP` | 4 entry |
| **`0x0FA298`** | **`PPID`** | **`"CMP40HX-8G#REDACTED"`** |
| `0x0FA401` | `OEMP` | ver 1, len 0x70 |

**`PPID` = part number + serial thật của card.**

Các tag con bên trong: `.ROM` `0xFA080`, `ROM` `0xFA090`, `IMG` `0xFA110` =
**`"G001.0000.02.04"`** (version image), `OBD` `0xFA190` (vendor `"Generic"`),
`RPR` `0xFA0AF`, `BBO` `0xFA0AC`, `OEM` `0xFA2D0/0xFA300/0xFA380/0xFA480`.

---

## 8. HAI KHỐI LỚN NPDS-E0 — ĐÃ MỞ

### NPDS-E0 #1 @`0x048A00` (46,592 B)
- `UUUU` @`0x48F04` = `55 AA 33 CC F0 0F FF 00 / 00 FF` → **self-test pattern VRAM**
  (walking-1, walking-0, address-line test)
- `IJOA` @`0x493E0` = hash 64 B entropy cao
- `PCIR` @`0x53059`, `RGIS` @`0x53070`, `RFRD` @`0x537E3` với tham số `0b f4 f9 a6` lặp lại
  → **script khởi tạo memory dạng opcode**, không phải dữ liệu

### NPDS-E0 #2 @`0x054000` (141,312 B)
- Mở đầu `2e 8b c0` lặp hàng nghìn lần = `mov eax,eax` (x86 NOP) → **padding alignment**
- 11 khối `PCGI` @`0x5674d`, stride 192/288 B
- `LEZD` @`0x5a5a0` = vùng hash
- `PERF_PTRS[17]` trỏ **vào trong** khối này (`0x545F2`)

---

## 9. FUSE / OTP — DUMP QUA BAR0

Source mở chỉ có **3** register fuse (không đủ), nên phải dump thật.

Tool: `fuse_dump.py` — đọc `0x21000–0x22800` theo từng u32 (tránh sập card:
bài học cũ là đọc >64 KB liên tục làm sập máy).

### Kết quả
```
1536 word doc duoc
 339 word CO DU LIEU
 673 word = 0xBADFxxxx  (khoi bi chan / khong decode)
 518 word = 0
   6 word = 0xFFFFFFFF
```

### Đối chiếu chéo — KHỚP 100% với dữ liệu cũ
| Offset | Giá trị | Ý nghĩa |
|---|---|---|
| `+0x650` | `0x0004001F` | TPC mask |
| `+0x624` | `0x0000001F` | GPC/TPC enable |
| `+0x4D8` | `0x00001F0B` | **PCI device ID** |
| `+0x56C` | `0x00001F4B` | device ID thứ 2 |

### Vùng hash entropy cao
- `0x21718` (32 B) — nghi **SHA256**
- `0x21B20` (80 B) — nghi **HMAC**

### Source mở chỉ có 3 register fuse
```
NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS  0x0002174C
NV_FUSE_OPT_NVDEC_DISABLE         0x00021378
NV_FUSE_STATUS_OPT_DISPLAY        0x00820C04
```
HAL stub cho TU106 (`gpuGetPrimaryFuseBaseAddr_b2b553`,
`gpuarchGetGpcFuseStatusOffset_b2b553`) đều là `xor eax,eax; ret`
→ **driver Linux không đọc fuse**. Fuse do **GSP-RM** xử lý.

---

## 10. GSP-RM: 923 REGISTRY KEY — BỀ MẶT KHAI THÁC THẬT

Trích từ `gsp_tu10x.bin` (22.9 MB). Cơ chế truyền đã xác nhận trong source:
```
NVreg_RegistryDwords  ->  PACKED_REGISTRY_TABLE (DWORD)
                      ->  NVKV REGKEY_NAME + REGKEY_VALUE_U32
                      ->  GSP-RM
```
(`kernel_gsp.c:4914 "encoding registry entries"`, `_kgspEncodePackedRegistryKeys`)
Driver **không parse** các key `RM*` — chỉ chuyển tiếp nguyên vẹn xuống GSP.

### Nhóm FUSE/OTP
`RmDisableFspFuseErrorCheck`, `RMNoECCFuseCheck`, `RMSec2UseDebugFuseOnlyBinary`,
`RMROPL2FuseMaskForFModel`

### Nhóm PVS / leakage bin (quan trọng nhất)
```
RMHwSpeedoOverride, RMHwSpeedo1Override, RMHwSpeedo2Override
RMHwSpeedoCheckIgnore
RmPmgrIddqOverride, RmPmgrIddq1Override
RmPmgrIddqNvvddOverride, RmPmgrIddqMsvddOverride
RmPmgrIddqCheckIgnore
RmPmgrSpeedoCoefficient, RmPmgrSpeedoOffset
```

### Nhóm VFE / điện áp
```
RMClkVfOverride                  <- GHI DE BANG V/F
RmClockForceUprocVfeVfGen        <- EP SINH VFE/VF
RmSramVminCheckIgnore
RmVoltThresholdCtrlCtrl
RmVoltPowerUpDelayUsOverride, RmVoltPowerDownDelayUsOverride
```

### Nhóm clock
`RmClkControllersOverride`, `RMForceLockedClocksMode`, `RMEnableOverclockingAllPstates`,
`RmBootGspRmWithBoostClocks`, `RMDisableGpuStateLoadBoost`

**Đây là đường khai thác không cần flash, không cần sửa VBIOS.**

---

## 11. THÍ NGHIỆM ĐÃ LÀM (và kết quả)

### Payload đã thử
| Payload | Nội dung | Kết quả |
|---|---|---|
| stock | ROM gốc | Max PL 220 W |
| pl240 | `power_max_w=240` | Max PL 240 W, `-pl 240` ăn thật |
| VMAX | REL 1093.75 + ALT 1125 | Max PL 220 W (không đổi) |
| T1 | PL 250 + REL/ALT max | Max PL 250 W |
| T2 | 17 field (PL 250, conn 250, OCP 220 A, REL 1093.75) | Max PL 250 W, verify ok |
| T3 | T2 + `follow_ov` (selector `03 03 03`) | **CARD RỚT** — rollback |

### Đo tải thật (CUDA FMA burn)
```
T2 (PL 250 W, conn 250 W, OCP 220 A, REL 1093.75):
  1890 MHz | 138.9 W | 63 C | power.limit 250 W
  SW Power Cap      : Not Active
  Board Limit       : ACTIVE
  Reliability       : ACTIVE
```

### `-lgc` chứng minh clock control hoạt động thật
| Lệnh | Kết quả |
|---|---|
| `-lgc 1500` | 1500 MHz / 73.2 W |
| `-lgc 1700` | 1710 MHz / 95.1 W |
| `-lgc 1890` | 1890 MHz / 140.2 W |
| `-lgc 1950` | **1875 MHz** |
| `-lgc 2100` | **1875 MHz** |

→ Trần cứng **1875–1890 MHz** dù lock cao hơn.

### Kết luận về trần 1890 MHz
- **Không nghẽn điện**: 139 W trên trần 250 W
- **Không nghẽn nhiệt**: 63 °C trên ngưỡng 89 °C
- **`SW Power Cap: Not Active`**
- Nâng connector/slot/OCP/REL đều **không dịch được trần**
- → Trần nằm ở **V/F curve / clock wall**, đúng mô hình tài liệu V100
- `Reliability: Active` bám **đường cong REL phụ thuộc leakage/nhiệt**, không phải hằng số
- `nvvdd_rel_alt_follow_ov` (selector `03 03 03`) **không hợp lệ trên Turing** → card rớt

### Giới hạn tool chính thức (`nvbios fields`)
```
REL  ∈ [1068.75 .. 1093.75] mV   (read-only ngoài dải)
ALT  ∈ [1093.75 .. 1125.0 ] mV
OV   = 1125.0 mV                (read-only)
VMIN ∈ [400 .. 993.75] mV
```

---

## 12. CÔNG CỤ ĐÃ VIẾT

| File | Dòng | Chức năng |
|---|---|---|
| `vfe_real.py` | 100 | Parser VFE 150 slot, assert 4/4 hằng số |
| `perf_tables.py` | 60 | Liệt kê 40 bảng PERF_PTRS, assert 3 bảng đã biết |
| `fuse_dump.py` | 33 | Dump fuse/OTP qua BAR0 theo u32 |
| `load.cu` | 41 | CUDA FMA burn để đo tải |
| `patch_payload.py` | 115 | Sửa 12 field + 3 bản copy điện áp, có guard thứ tự |
| `make_payload.py` | 93 | Cắt payload từ ROM, verify 1 legacy image |
| `power_table.py` | 93 | Parse POWER TABLE `0x57E92` |
| `vfe_slots.py` | 117 | Parser VFE cũ (base sai, giữ để đối chiếu) |

Tất cả ở `~/.hermes/cache/scratch/vbios40/` (host) và script copy sang `/tmp` target.

---

## 13. ĐIỀU ĐÃ ĐÓNG (kết luận chắc chắn)

| Vấn đề | Kết luận | Bằng chứng |
|---|---|---|
| +128 CUDA | **Bất khả thi ở tầng silicon** | `fuse+0x650 = 0x0004001F`, `tpc_nr 0x502608 = 0x00040005` read-only, GPC0 TPC5 trả `0xBADF1300` |
| Display | **Không decode ra BAR0** | `DISP 0x610000`, `SOR 0x616000`, `DAC 0x61C110` = `0xBADF1301` |
| PCIe Gen3 | **Bất khả thi** | `LnkCap2: 2.5–5 GT/s` |
| cmpunlocker | **Chạy tốt** | Tensor ~63×, INT8 ~33× |
| NVENC | **Sống thật (73%)** | đo trực tiếp |
| NVDEC | **Chưa chứng minh** | — |
| Điện áp runtime qua userspace | **4 đường đều âm tính** | BAR0 probe, ioctl hook, NVML, GSP scan |
| Checksum VBIOS | **`sum % 256 == 0`** | 9/9 image, sửa 1 byte → lệch +1 |
| Chữ ký crypto được kiểm | **KHÔNG** | đường override chỉ kiểm legacy image + checksum |
| VBIOS override qua RAM | **CHẠY ĐƯỢC** | log đầy đủ + PL đổi thật |
| Trần 1890 MHz | **V/F curve**, không phải power/thermal | `-lgc` đo 5 mức + limiter flags |

---

## 14. CÒN LẠI — CHƯA GIẢI

### Ưu tiên cao
1. **`PERF_PTRS[17]` / bảng `0x54600`** — script cấu hình thanh ghi, stride 33 B,
   chứa cặp `05 64 xx 50 06 05 00` / `01 85 01 40`. **Chưa decode được sang `(addr, data)`**.
   Đây là nơi chứa tham số khoá cứng lúc boot.
2. **6 blob mã hoá trong `ucodes_tu10x.bin`** — entropy 7.99, chưa giải.
   7/13 blob plaintext đã tách được.
3. **GSP-RM registry key chưa thử** — `RMHwSpeedoOverride`, `RmPmgrIddqNvvddOverride`,
   `RMClkVfOverride`, `RmClockForceUprocVfeVfGen`. Key đã xác nhận vào được module
   nhưng **chưa chứng minh GSP có phản ứng**.

### Ưu tiên trung bình
4. **10 digest entry trong `IBVL`** — chính xác cái gì được ký (object nào).
5. **`RIBI` / `JFFS` / `GXIP` / `OEMP`** — chỉ mới đọc header, chưa parse nội dung.
6. **Vùng `0x054800–0x055800`** chỉ 40% dữ liệu — điểm mù lớn nhất.
7. **`IJOA` / `LEZD`** — 2 vùng hash chưa xác định thuật toán.

### Ưu tiên thấp
8. `FALCON_DATA 0x48B54` devinit script — chưa parse.
9. `NVINIT 0x28893` — chưa parse.
10. `PERF_CF 0x588DE` — `entry_size` đọc ra sai.

---

## 15. CẢNH BÁO AN TOÀN

- **TUYỆT ĐỐI KHÔNG flash ROM thật.** Chip `U11` SOIC-8 208 mil, **1.8 V** —
  CH341A 3.3 V sẽ cháy chip.
- Mọi thay đổi qua **RAM override** — `rm /etc/modprobe.d/cmp40hx-vbios.conf` + reboot là sạch.
- Đọc BAR0 phải **theo cửa sổ ≤64 KB** — đọc 16 MB liên tục đã làm sập máy.
- Ghi `XVE 0x88004` làm sập link PCIe.
- Selector `03 03 03` (`follow_ov`) **làm rớt card** trên Turing — đã rollback.
- `/tmp` bị xoá sau reboot → phải tạo lại `/tmp/.ap` và build lại `load` mỗi lần.

---

*Hết báo cáo.*

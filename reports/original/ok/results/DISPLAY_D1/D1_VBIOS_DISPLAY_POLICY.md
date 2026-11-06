# D1-D — VBIOS DISPLAYLESS CONFIGURATION

**Parser:** `/home/REDACTED_USER/.hermes/cache/scratch/vbios3.py` — spec-exact, không dùng offset cố định giữa các ROM
**Spec đối chiếu:** NVIDIA open-gpu-doc *BIOS Information Table* rev 1 + nouveau `nvkm/subdev/bios/bit.c`, `dcb.c`

---

## 1. Provenance & hash các ROM

| ROM | SHA-256 | Size | Device PCI | BIT_i version |
|---|---|---|---|---|
| **CMP 40HX gốc** | `dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec` | 1.048.576 B | `0x1F0B` | `00.D9.00.CF.00` (90.06.67.00.06) |
| CMP variant 253219 | `bbdac1e982f4a1e6b5a442633dbdf96ea07f5a0cc1bc7836c6267caf6c8b6a78` | 1.047.040 B | `0x1F0B` | `00.D9.00.CF.00` |
| GeForce RTX 2060S #246948 | `c468ac52bfea803a7784b02c3f0a4005115660b0087e06302056ab27a9332dcf` | 1.047.040 B | `0x1F06` | `00.F8.00.02.4D` |
| GeForce RTX 2060S #268920 | `0a2fd8782e7bfc5b74edf1a6609b76157626cfe130188a584f0caed4a58c9cb9` | 1.047.040 B | `0x1F06` | `00.F8.00.02.4D` |
| GeForce RTX 2070 #265590 | `560f2be1bee834c3d6acccbc5b0eaba47d3be5b9bce2ef2a40b97e1e898a0db8` | 1.047.040 B | `0x1F07` | `00.F8.00.02.4D` |

⚠️ Hai file `input/ASTRA_CMP40HX_HANDOFF/03_VBIOS/geforce/*.rom` (3358 B) là **trang HTML**, không phải ROM. Đã loại khỏi phân tích.

VBIOS đang chạy trên target: `nvidia-smi` báo `90.06.67.00.06` = khớp `BIT_i` của CMP gốc. `0x1F0B` khớp `10DE:1F0B`.

---

## 2. Cách parse (pointer-driven, không offset cố định)

### 2.1 BIT — theo `nvkm/subdev/bios/bit.c`

```c
bios->bit_offset = nvbios_findstr(bios->data, bios->size, "\xff\xb8" "BIT", 5);
entries = rd08(bit_offset + 10);
stride  = rd08(bit_offset + 9);
entry   = bit_offset + 12;
struct bit_entry { u8 id; u8 version; u16 length; u16 offset; };
```

**Kiểm chứng trên CMP gốc:**
```
'\xff\xb8BIT' @ file 0x287B0 → bit_offset = 0x287B0
  byte@+9  stride  = 6
  byte@+10 entries = 17
  table @ 0x287BC
```

17 token, id là **ký tự ASCII** — tất cả hợp lệ:

| id | ASCII | ver | len | off | Ý nghĩa (theo spec NVIDIA) |
|---|---|---|---|---|---|
| 0x32 | `2` | 01 | 4 | 0x0232 | I2C pointers |
| 0x42 | `B` | 02 | 37 | 0x023E | BIOSDATA |
| 0x43 | `C` | 02 | 44 | 0x0263 | Clock pointers |
| 0x44 | `D` | 01 | 4 | 0x028F | **DCB pointer** |
| 0x49 | `I` | 01 | 36 | 0x0293 | I2C scripts |
| 0x4D | `M` | 02 | 29 | 0x02B7 | Mobile/MXM |
| 0x4E | `N` | 00 | 0 | 0x0000 | (rỗng) |
| 0x50 | `P` | 02 | 224 | 0x02D4 | Performance table ptrs |
| 0x53 | `S` | 02 | 24 | 0x03B4 | String ptrs |
| 0x54 | `T` | 01 | 2 | 0x03CC | TMDS ptrs |
| **0x55** | **`U`** | **01** | **5** | **0x03CE** | **Display Control/Programming ptrs** |
| 0x56 | `V` | 01 | 6 | 0x03D3 | Virtual field ptrs |
| 0x78 | `x` | 01 | 8 | 0x03D9 | MXM config |
| 0x64 | `d` | 01 | 2 | 0x03E1 | DP table ptrs |
| 0x70 | `p` | 02 | 4 | 0x03E3 | Falcon ucode |
| 0x75 | `u` | 01 | 13 | 0x03E7 | UEFI driver data |
| 0x69 | `i` | 02 | 104 | 0x03F4 | **Version string** |

Không còn byte lạc. Parse **hợp lệ 17/17**.

### 2.2 DCB — theo `nvkm/subdev/bios/dcb.c` (ver ≥ 0x30)

```c
dcb = rd16(image + 0x36);        // image-relative trên dump PCI ROM BAR
ver = rd08(dcb);                 // phải >= 0x30
rd32(dcb + 6) == 0x4EDCBDCB      // signature
hdr = rd08(dcb+1); cnt = rd08(dcb+2); elen = rd08(dcb+3);
entry[k] = rd32(dcb + hdr + k*elen)  // bitfield: or[31:28] loc[21:20] bus[19:16]
                                     //           conn[15:12] heads[11:8] i2c[7:4] type[3:0]
```

**Kiểm chứng:** `image = 0x28600` (khớp `vendor=10DE`, `device=1F0B`), `rd16(image+0x36) = 0x53AC` → DCB @ `0x2D9AC`.
- `ver = 0x41` ✓ (DCB 4.1)
- `rd32(0x2D9AC+6) = 0x4EDCBDCB` ✓ signature đúng
- `hdr = 0x23`, `cnt = 0`, `elen = 8`

---

## 3. Kết quả §C — `NO_DISPLAY_SUBSYSTEM` (BIT token `U`)

### 3.1 Spec NVIDIA

*BIT_DISPLAY_PTRS* (rev 1):
| Field | Width | Ý nghĩa |
|---|---|---|
| Display Scripting Table Pointer | 16 | con trỏ bảng script display |
| **Display Control Flags** | **8** | `[0:0]` white overscan border · **`[1:1]` NO_DISPLAY_SUBSYSTEM: Display subsystem isn't included in the GPU (used for displayless coproc)** · `[2:2]` DISPLAY_FPGA · `[3:3]` VBIOS avoids touching mempool · `[4:4]` Offset PCLK · `[5:5]` Boot with DP hotplug disabled · `[6:6]` Allow DP sink detection by DPCD read |
| SLI Table Header Pointer | 16 | con trỏ SLI header |

Bố cục 5 byte: `u16 scriptPtr, u8 flags, u16 sliPtr`.

### 3.2 Giá trị thực tế (image-relative đã áp dụng)

| ROM | `U` off | file offset | raw 5 byte | **flags** | `NO_DISPLAY_SUBSYSTEM` |
|---|---|---|---|---|---|
| **CMP 40HX gốc** | `0x03CE` | `0x289CE` | `00 00 02 00 00` | **`0x02`** | **1** ✅ |
| CMP 253219 | `0x03CE` | `0x289CE` | `00 00 02 00 00` | `0x02` | **1** |
| GeForce 2060S #246948 | `0x03A2` | `0x289A2` | `8F 4E 00 00 00` | **`0x00`** | **0** ✅ |
| GeForce 2060S #268920 | `0x03A2` | `0x289A2` | `8F 4E 00 00 00` | `0x00` | **0** |
| GeForce 2070 #265590 | `0x03A2` | `0x289A2` | `8F 4E 00 00 00` | `0x00` | **0** |

Flags bit-by-bit:

| Bit | CMP `0x02` | GeForce `0x00` |
|---|---|---|
| 0 — white overscan border | 0 | 0 |
| **1 — NO_DISPLAY_SUBSYSTEM** | **1** | **0** |
| 2 — DISPLAY_FPGA | 0 | 0 |
| 3 — VBIOS avoids mempool | 0 | 0 |
| 4 — Offset PCLK between heads | 0 | 0 |
| 5 — Boot with DP hotplug disabled | 0 | 0 |
| 6 — Allow DP sink by DPCD read | 0 | 0 |
| 7 — Reserved | 0 | 0 |

**Cực kỳ sạch:** CMP bật **đúng một bit** (bit 1). GeForce **không bật bit nào**. Đây là khác biệt một bit, đúng như spec.

**Xác minh lại bằng chứng cũ: ĐÚNG.** CMP = 1, GeForce TU106 = 0.

---

## 4. Kết quả §C — DCB entry count

| ROM | DCB ver | sig | hdr | **entry_count** | **real output entries** | Phân loại |
|---|---|---|---|---|---|---|
| **CMP 40HX gốc** | `0x41` | ✓ `4EDCBDCB` | `0x23` | **0** | **0** | Bảng rỗng hoàn toàn |
| CMP 253219 | `0x41` | ✓ | `0x23` | **0** | **0** | Bảng rỗng |
| GeForce 2060S #246948 | `0x41` | ✓ | `0x23` | **16** | **7** | 2× DP + 5× TMDS + 2× EOL |
| GeForce 2060S #268920 | `0x41` | ✓ | `0x23` | **16** | **5** | 1× DP + 4× TMDS |
| GeForce 2070 #265590 | `0x41` | ✓ | `0x23` | **16** | **5** | 1× DP + 4× TMDS |

Chi tiết GeForce 2060S #246948 (đủ 7 output thật):
```
[ 0] DP    or=2 loc=0 conn=0 heads=15 i2c=6 conf=0x04600020
[ 1] TMDS  or=2 loc=0 conn=0 heads=15 i2c=6 conf=0x00020020
[ 2] TMDS  or=2 loc=0 conn=1 heads=15 i2c=5 conf=0x00020010
[ 3] TMDS  or=4 loc=0 conn=2 heads=15 i2c=7 conf=0x00020010
[ 4] DP    or=4 loc=0 conn=3 heads=15 i2c=8 conf=0x04600020
[ 5] TMDS  or=4 loc=0 conn=3 heads=15 i2c=8 conf=0x00020020
[ 6] TMDS  or=1 loc=0 conn=4 heads=15 i2c=3 conf=0x00020030
[ 7] EOL   (kết thúc logic)
[ 8] EOL
[ 9-15] Unused
```

**Xác minh lại bằng chứng cũ: ĐÚNG, kèm đính chính.** CMP `entry_count = 0` (không phải "bảng thiếu vài entry" — bảng **rỗng hoàn toàn**, header `hdr=0x23` vẫn còn nhưng không có entry nào). GeForce = 16 entry, trong đó **5–7 là output thật** — phần còn lại là `Unused`/`EndOfLine`. Con số "16 entry" là tổng, không phải số cổng.

---

## 5. BIOSDATA `B+32`

### 5.0 QUY TẮC CON TRỎ — điểm sửa quan trọng nhất

Mọi `offset` trong token BIT là **image-relative**, không phải ROM tuyệt đối. Công thức:

```
file_offset = image_base + token_offset
```

Kiểm chứng trên CMP: `image_base = 0x28600`, token `U` offset `0x03CE` → file `0x289CE`.
Nếu đọc tuyệt đối `0x03CE` sẽ ra vùng mã VGA rác. Đây chính là lỗi trong bản nháp đầu của báo cáo này — **đã sửa và có `--selftest` chặn tái phát**.

Parser: `/home/REDACTED_USER/.hermes/cache/scratch/vbios_final.py` (`--selftest` kiểm 5 quy tắc).

### 5.1 Giá trị thực đo (đã xác minh)

| ROM | `B` file offset | `length` | `B+28` | `B+32` | `BIOS_VERSION` |
|---|---|---|---|---|---|
| **CMP 40HX gốc** | `0x2883E` | 37 | `0x36` | **`0x12`** | `90.06.67.00` ✅ khớp `nvidia-smi` |
| CMP 253219 | `0x2883E` | 37 | `0x36` | **`0x12`** | `90.06.67.00` |
| GeForce 2060S #246948 | `0x2883E` | 37 | `0x36` | **`0x10`** | `90.06.44.00` |
| GeForce 2060S #268920 | `0x2883E` | 37 | `0x36` | **`0x10`** | `90.06.4C.00` |
| GeForce 2070 #265590 | `0x2883E` | 37 | `0x36` | **`0x10`** | `90.06.3D.00` |

**Xác nhận bằng chứng cũ: ĐÚNG.** `B+32` = `0x12` trên CMP, `0x10` trên GeForce. `BIOS_VERSION` đọc ra khớp chính xác số VBIOS mà `nvidia-smi` báo (`90.06.67.00.06`) — đây là **kiểm chứng độc lập** rằng offset `B` là đúng.

### 5.2 Vai trò `Module Map External 0` (B+0x1C = B+28)

Theo spec NVIDIA, `BIT_BIOSDATA` v2 kết thúc bằng byte **`Module Map External 0`**:

| Bit | Ý nghĩa |
|---|---|
| 0 | Underflow and Error Reporting — *"should never be enabled on production VBIOSes"* |
| **1** | **Coproc Build. Set when a VBIOS is intended to work as a coprocessor and does not support any displays** |
| 2–4 | Reserved |

Bố cục 37 byte:
```
0x00-0x03  BIOS Version (32)        0x14-0x15  Data Range Table Ptr (16)
0x04       BIOS OEM Version (8)     0x16-0x17  ROMpacks Ptr (16)
0x05       BIOS Checksum (8)        0x18-0x19  Applied ROMpacks Ptr (16)
0x06-0x07  INT15 POST Callbacks     0x1A       Applied ROMpack Max (8)
0x08-0x09  INT15 SYSTEM Callbacks   0x1B       Applied ROMpack Count (8)
0x0A-0x0B  Frame Count (16)         0x1C       Module Map External 0 (8)  ← B+28
0x0C-0x0F  Reserved (32)            0x1D-0x20  Compression Info Ptr (32)
0x10       Max Heads at POST (8)    0x21-0x24  không định nghĩa trong spec rev 1
0x11       Memory Size Report (8)             (B+32 nằm trong vùng này)
0x12       hScale Factor (8)
0x13       vScale Factor (8)
```

### 5.3 Kết quả đọc `Coproc Build` (B+28 bit1)

`B+28 = 0x36` trên **cả 5 ROM** ⇒ `0x36 = 0b00110110` ⇒ bit1 = **1** ⇒ **`Coproc Build = 1` trên TẤT CẢ**, kể cả GeForce.

⇒ **`Coproc Build` KHÔNG phân biệt được CMP với GeForce.** Nó không phải cờ displayless riêng của CMP trong bộ ROM này.

### 5.4 `B+32` — cái gì phân biệt thật, nhưng vai trò CHƯA rõ

| Giá trị | ROM |
|---|---|
| `0x12` | CMP 40HX (cả hai biến thể) |
| `0x10` | GeForce 2060S ×2, GeForce 2070 |

`0x12` vs `0x10` khác nhau ở **bit 1**. `B+32` nằm trong vùng `0x21–0x24` mà **spec NVIDIA rev 1 không định nghĩa** cho `BIT_BIOSDATA` v2 (bản ghi khai báo 37 byte nhưng spec chỉ mô tả tới `0x20`).

⇒ **Kết luận đúng:** `B+32` **tương quan** với CMP (0x12) vs GeForce (0x10) trên 5/5 ROM, nhưng **vai trò kỹ thuật CHƯA XÁC ĐỊNH**. Không được dùng làm bằng chứng nhân quả. Có thể là trường mở rộng nội bộ của NVIDIA, có thể liên quan coproc, có thể là cờ debug — **không đủ dữ liệu**.

### 5.5 So với `NO_DISPLAY_SUBSYSTEM` (token `U`)

Cờ này mới là cờ **có định nghĩa spec** và **phân biệt đúng**:

| ROM | `U` file offset | raw 5 byte | flags | `NO_DISPLAY_SUBSYSTEM` (bit 1) |
|---|---|---|---|---|
| **CMP 40HX gốc** | `0x289CE` | `00 00 02 00 00` | **`0x02`** | **1** ✅ |
| CMP 253219 | `0x289CE` | `00 00 02 00 00` | `0x02` | **1** |
| GeForce 2060S #246948 | `0x289A2` | `8F 4E 00 00 00` | **`0x00`** | **0** ✅ |
| GeForce 2060S #268920 | `0x289A2` | `8F 4E 00 00 00` | `0x00` | **0** |
| GeForce 2070 #265590 | `0x289A2` | `8F 4E 00 00 00` | `0x00` | **0** |

Bố cục `BIT_DISPLAY_PTRS` v1 (5 byte): `u16 scriptPtr, u8 flags, u16 sliPtr`.
- CMP: `scriptPtr = 0x0000`, `flags = 0x02`, `sliPtr = 0x0000`
- GeForce: `scriptPtr = 0x4E8F`, `flags = 0x00`, `sliPtr = 0x0000`

CMP có `flags = 0x02` = **chỉ đúng bit NO_DISPLAY_SUBSYSTEM**, mọi bit khác 0. GeForce có `flags = 0x00` = **không bit nào bật**. Đây là khác biệt sạch, một bit, đúng như spec mô tả.

**Xác nhận bằng chứng cũ: ĐÚNG** (CMP=1, GeForce=0).

---

## 6. Tìm code xử lý `NO_DISPLAY_SUBSYSTEM` / `Coproc Build`

### 6.1 Trong open-gpu-kernel-modules 615.78.08

```
grep -rni "coproc|noDisplaySubsystem|NO_DISPLAY" src/   → 0 hit liên quan
```
Chỉ có hit không liên quan: `x86emuOp_esc_coprocess_*` (emulator FPU), `NV0073_CTRL_SPECIFIC_HDCP_CTRL_CMD_READ_LINK_STATUS_NO_DISPLAY` (HDCP), `NVKMS_MODE_VALIDATION_NO_DISPLAYPORT_BANDWIDTH_CHECK` (bandwidth).

⇒ RM **không đọc** hai cờ này. RM không tự parse BIT/DCB; VBIOS được đưa cho devinit/GSP xử lý.

### 6.2 Trong GSP 615.78.08

GSP cũng không tham chiếu literal `0x21C04`/`0x820C04`; cửa sổ fuse không bị chạm (xem D1-A §4.1). Việc GSP có đọc BIT_U hay không **chưa xác định** (bảng tra gián tiếp, xem D1-C §2.4).

### 6.3 Điểm đứt

**Không tìm được consumer của `NO_DISPLAY_SUBSYSTEM` hoặc `Coproc Build` trong bất kỳ thành phần nào đọc được offline.** Đây là **đứt chuỗi thật**, không phải suy đoán.

Đánh giá hệ quả:
- Nếu consumer nằm trong devinit (thực thi trên GPU ở POST) → không phân tích được offline.
- Nếu consumer nằm trong GSP → cần thêm thời gian reverse bảng tra.

**Nhưng:** việc này **không ảnh hưởng kết luận D1.** Gate fuse (D1-A) độc lập và đã chặn trước. `NO_DISPLAY_SUBSYSTEM` chỉ là **dấu hiệu thiết kế** cho biết NVIDIA đã build ROM này theo nhánh displayless — nó xác nhận **ý định**, không phải **cơ chế**.

---

## 7. `NO_DISPLAY_SUBSYSTEM` ≠ bằng chứng SOR/PHY hỏng (yêu cầu C.6)

`NO_DISPLAY_SUBSYSTEM=1` chỉ nói: **"subsystem display không được đưa vào GPU"** theo nghĩa sản phẩm. Nó **không** nói:
- cổng DP/HDMI có bị cắt khỏi die hay không
- PHY có hoạt động hay không
- board có linh kiện hay không

Ba câu hỏi đó thuộc lớp D — xem `D1_PDISP_SOR_PHY_EVIDENCE.md`. Kết luận lớp C: **trung tính** với khả năng phần cứng.

---

## 8. `Sửa VBIOS là đủ chưa?` (yêu cầu C.5)

**KHÔNG đủ.** Ba lý do độc lập:

1. **Gate fuse chạy trước VBIOS.** `kdispStatePreInitLocked` đọc `0x021C04` từ silicon, không hỏi VBIOS. Sửa ROM không đổi được giá trị đó.
2. **`NO_DISPLAY_SUBSYSTEM` có thể nằm trong devinit/GSP** — không xác định được consumer, nên không biết sửa có hiệu lực không.
3. **Gate thứ ba `ipver == 0xFFFFFFFF`** (`gpu.c:6033-6036`) — nếu hardware/GSP báo display engine disabled thì HAL display rỗng, không CRTC, dù ROM nói gì.

---

## 9. Vì sao ROM CMP nhỏ hơn GeForce 495 KB (dữ liệu cũ, xác minh lại)

| | CMP (1 MB dump) | CMP t4 derivative | GeForce |
|---|---|---|---|
| File size | 1.048.576 | **495.616** | 1.047.040 |
| Imagetrong PCIR | 12.288 / 14.336 B | (thiếu) | 12.288 / 14.336 B |

`cmp40hx_t4_derivative.bin` (`aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb`) chỉ 495.616 B = **file bị cắt**, không phải VBIOS hoàn chỉnh — nó thiếu phần lớn dữ liệu DCB/BIT phía sau. Đây là ROM đã bị cắt bớt trong quá trình thí nghiệm trước, **không dùng làm tham chiếu**.

---

## 10. Hash

| Đối tượng | Giá trị |
|---|---|
| Parser | `/home/REDACTED_USER/.hermes/cache/scratch/vbios3.py` |
| Output | `/home/REDACTED_USER/.hermes/cache/scratch/vbios_v3.json` |
| Spec | `download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html` |
| nouveau refs | `torvalds/linux` master: `nvkm/subdev/bios/bit.c`, `nvkm/subdev/bios/dcb.c` |

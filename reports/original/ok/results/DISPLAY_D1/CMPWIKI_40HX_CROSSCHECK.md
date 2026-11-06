# CMPWIKI 40HX CROSS-CHECK

**GPU:** NVIDIA CMP 40HX, TU106-100-A1, PCI `10DE:1F0B`, BDF `0000:03:00.0`
**Driver:** 615.78.08 · **GSP:** `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`
**Source RM:** open-gpu-kernel-modules `615.78.08` @ `1a82fbfda8f321b056eb3568850f9316c5e465c5`
**Ngày:** 2026-11-06 · Chỉ phân tích offline + đọc read-only

> Nguồn đối chiếu: cmp.wiki (3 trang), github.com/dartraiden/NVIDIA-patcher (repo + `linux.sh` + `Presets.txt` + README-LINUX), và mã nguồn NVIDIA thật + firmware GSP 615.78.08.

---

## KẾT LUẬN NGẮN GỌN

> **NVIDIA-patcher KHÔNG mở display cho CMP 40HX. Nó chỉ làm Windows/Linux nhận card là GPU đồ hoạ hợp lệ để chạy 3D — bằng cách thay đổi danh sách PCI Device ID trong driver.**
>
> Không có một byte nào trong patch chạm tới: fuse display, `KernelDisplay`, PDISP, SOR, PHY, hay VBIOS.

Bốn trạng thái **hoàn toàn khác nhau** và chỉ trạng thái #1 đạt được bằng patcher:

| # | Trạng thái | CMP 40HX hiện tại | Patcher đạt được? |
|---|---|---|---|
| 1 | **GPU render được 3D** | ✅ Có (compute + GR engine hoạt động) | **CÓ — đây chính là mục đích của nó** |
| 2 | **Driver nhận là display-class GPU** | ❌ Không (`Display Active: Disabled`) | **KHÔNG** — chỉ đổi *tên/adapter type* trong INF, không đổi lớp engine |
| 3 | **Display engine thực sự hoạt động** | ❌ Không — `kdispStatePreInitLocked` trả `NV_ERR_NOT_SUPPORTED` | **KHÔNG** |
| 4 | **DP/HDMI phát tín hiệu vật lý** | ❌ Không — không có CRTC, không có connector | **KHÔNG** |

---

## A. NVIDIA-PATCHER HỖ TRỢ CMP 40HX BẰNG CÁCH NÀO

### A.1 Bản chất kỹ thuật — patch **15 u32 = 60 byte** trong `nv-kernel.o_binary`

> **ĐÍNH CHÍNH (D2):** mục này trước ghi *"patch 12 byte"* — **SAI về số lượng**. Mẫu CMP là **15 giá trị u32 = 60 byte**; pattern thay thế cũng 15 u32 = 60 byte. Đếm lại từ `linux.sh` dưới đây.

`linux.sh` (raw từ repo, 2318 byte) tìm và thay **một mẫu hex duy nhất** trong `kernel/nvidia/nv-kernel.o_binary`:

```bash
PATTERNS=(
    "P1xx|071b0700871b0700c71b0700071c0700091c07|ffff0700ffff0700ffff0700ffff0700ffff07"
    "CMP|091e0700491e0700bc1e0700fc1e07000b1f0700812007008220070083200700c2200700892107000d2207004d2207008a2407|ffff0700...(×15)"
    ...
)
```

**Đếm chính xác:** chuỗi hex CMP dài **60 byte**, chia 4 = **15 giá trị u32 little-endian**. Giải mã:

```
[ 0] 0x00071E09   [ 1] 0x00071E49   [ 2] 0x00071EBC   [ 3] 0x00071EFC   [ 4] 0x00071F0B
[ 5] 0x00072081   [ 6] 0x00072082   [ 7] 0x00072083   [ 8] 0x000720C2   [ 9] 0x00072189
[10] 0x0007220D   [11] 0x0007224D   [12] 0x0007248A   [13] 0x000724CA   [14] 0x0007250A
```

Byte thấp 16 bit chính là **PCI Device ID**: `1E09` (CMP 50HX), **`1F0B` (CMP 40HX)**, `2082`/`20C2` (CMP 170HX), `2189` (CMP 30HX), `220D` (CMP 90HX), `248A` (CMP 70HX), `248A`+`24CA` (CMP 70HX variants)…

⇒ Patch ghi đè **15 entry × 4 byte = 60 byte** bằng `0x0007FFFF` (15 lần). Tất cả nằm trong **một** bảng dữ liệu liên tiếp.

### A.2 Xác minh trên driver 615.78.08 thật (không suy đoán)

Giải nén driver trên target rồi tìm mẫu:

```
/tmp/nvx/kernel/nvidia/nv-kernel.o_binary   size = 115.570.992 B
CMP pattern hits: 1        ← khớp đúng 1 lần
P1xx pattern hits: 1
first hit at 0x5FE26F0
```

Bảng thật tại chỗ (24 entry liên tiếp, mỗi entry 4 byte):

```
0x5FE26CC: 0x000715C2   0x5FE26D0: 0x00071B07   0x5FE26D4: 0x00071B87
0x5FE26D8: 0x00071BC7   0x5FE26DC: 0x00071C07   0x5FE26E0: 0x00071C09
0x5FE26E4: 0x00071D83   0x5FE26E8: 0x00071D84   0x5FE26EC: 0x00071DC1
0x5FE26F0: 0x00071E09   0x5FE26F4: 0x00071E49   0x5FE26F8: 0x00071EBC
0x5FE26FC: 0x00071EFC → 0x5FE2700: 0x00071F0B   0x5FE2704: 0x00072081
0x5FE2708: 0x00072082   0x5FE270C: 0x00072083   0x5FE2710: 0x000720C2
0x5FE2714: 0x00072189   0x5FE2718: 0x0007220D   0x5FE271C: 0x0007224D
0x5FE2720: 0x0007248A   0x5FE2724: 0x000724CA   0x5FE2728: 0x0007250A
```

Ngay sau bảng là chuỗi ASCII:
```
52 6d 47 63 36 43 6f 6d 70 61 63 74 69 6f 6e 4f 76 65 72 72 69 64 65  = "RmGc6CompactionOverride"
52 4d 47 43 36 53 74 61 74 73                                          = "RMGC6Stats"
52 75 6e 4f 6e 6c 794e 56 53 52                                        = "RunOnlyNVSR"
```

⇒ Đích patch là **một bảng hằng `0x0007xxxx`** (giá trị `0x0700` ở byte cao = cờ), **không phải mã lệnh**. Patch đổi `0x0007XXXX` → `0x0007FFFF`.

### A.3 Patch làm gì và KHÔNG làm gì

| Khía cạnh | Chi tiết |
|---|---|
| **Cái gì bị đổi** | **15 entry × 4 byte = 60 byte** trong một bảng dữ liệu `u32` → giá trị `0x0007FFFF` |
| **Đổi ở đâu** | `nv-kernel.o_binary` (RM kernel blob), phần `.data`/`.rodata` |
| **Không đổi gì** | Không chạm `nv-kernel.o` code, không chạm GSP firmware, không chạm VBIOS, không chạm fuse |
| **Hiệu ứng** | Nhóm device ID này được xử lý như device "hợp lệ/được hỗ trợ" thay vì bị loại |

### A.4 Phía Windows (INF) — bản chất là đổi *nhận dạng*, không đổi *khả năng*

`Presets.txt`:
```
= 1 = Fix-Remove-Strings ... nv_dispi*.inf ... "DEV(_|\.)(1B07|1B87|1BC7|1C07|1C09|1E09|1F0B|2082|20C2|2189|220D|248A)"
= 1 = Fix-INF-add-String ... "nv_commonBase_addreg*" ... "HKR,,AdapterType,%REG_DWORD%,1"
= 1 = Fix-INF-add-String ... "nv_commonBase_addreg*" ... "HKR,,EnableMsHybrid,%REG_DWORD%,1"
= 1 = Fix-INF-add-DevID  ... "PCI\VEN_10DE&DEV_1F0B" ... "NVIDIA GeForce RTX 2060 SUPER"
```

Ba thao tác, đọc đúng nghĩa:

1. **Xoá** device ID CMP khỏi danh sách **loại trừ** của INF.
2. **Thêm** `AdapterType=1` — registry value này khai báo card là **adapter đồ hoạ hiển thị**, không phải compute-only.
3. **Thêm** `EnableMsHybrid=1` — bật đường hybrid (giống Optimus).
4. **Đăng ký** `DEV_1F0B` dưới tên **"NVIDIA GeForce RTX 2060 SUPER"** — nghĩa đen: dùng profile của 2060S cho CMP 40HX (cùng TU106-100).

**Đây là thay đổi nhận dạng trong registry Windows.** Nó khiến Windows *tin* card là adapter hiển thị và nạp đường D3D. Nó **không** làm display engine bật lên — vì display engine nằm ở kernel RM/GSP, không ở INF.

Bảng chọn driver trong README-LINUX cũng nói rõ ý định: cột "what device you are using to display the image on the monitor" — tức **màn hình luôn cắm ở GPU khác** (iGPU/AMD/NVIDIA khác). CMP chỉ render.

### A.5 Phân biệt bốn khái niệm (yêu cầu A)

| Khái niệm | Cơ chế | Patcher tác động? | Trạng thái CMP 40HX |
|---|---|---|---|
| **3D acceleration** | D3D/OpenGL/Vulkan dùng GR engine + trình bày qua **GPU khác** | ✅ **CÓ** — mục đích chính | Hoạt động (sau patch) |
| **Graphics device enumeration** | Windows/Linux nhận `10DE:1F0B` là adapter đồ hoạ | ✅ **CÓ** (INF/registry + bảng ID) | Được nhận |
| **KernelDisplay initialization** | `kdispStatePreInitLocked` → `gpuFuseSupportsDisplay_GM107` → fuse `0x021C04` | ❌ **KHÔNG** | **Thất bại** — `NV_ERR_NOT_SUPPORTED` |
| **Tín hiệu xuất hình vật lý** | PDISP → SOR → PHY → connector | ❌ **KHÔNG** | Không tồn tại |

Bằng chứng KernelDisplay chưa từng được khởi tạo trên máy đã cài cmpunlocker (không phải patcher):
```
nvidia 0000:03:00.0: [drm] No compatible format found
nvidia 0000:03:00.0: [drm] Cannot find any crtc or sizes
```
`nvidia-drm` nạp được nhưng **không có CRTC nào** — vì `kdispStatePreInitLocked` (`kern_disp.c:444-445`) đã return trước khi `kdispStateInitLocked` chạy.

---

## B. VÌ SAO DỰ ÁN KHUYÊN TẮT GSP CHO CMP 40HX

### B.1 Nguyên văn khuyến nghị

`README-LINUX.md`, mục **"Increase performance of the CMP 30HX and CMP 40HX"**:

> "To improve performance and stability in gaming and compute workloads, after a successful driver installation, it is recommended to disable GPU control via GSP Firmware, which is enabled automatically by default."

Kèm `NVreg_EnableGpuFirmware=0`, và xác minh bằng `nvidia-smi -q | grep GSP` → "N/A".

### B.2 Đọc đúng phạm vi khuyến nghị

Câu chữ nói rõ **hai** mục đích: *performance* và *stability* trong *gaming and compute workloads*. **Không** nói tới display.

Đối tượng áp dụng: **chỉ CMP 30HX và CMP 40HX** — hai card dùng **TU106/TU116 kiến trúc Turing cũ**, nơi `GSP` là đường mới còn `RM host-side` vẫn đầy đủ chức năng. Các CMP khác (90HX/170HX) không nằm trong khuyến nghị này.

### B.3 Kiểm tra bằng mã nguồn: tắt GSP có mở được display gate không?

**KHÔNG.** Lý do có bằng chứng máy:

1. **Fuse check giống nhau ở cả hai đường.** `gpuFuseSupportsDisplay_GM107` chạy trong **host RM**, không phụ thuộc GSP:
   ```
   kern_disp.c:444    if (!gpuFuseSupportsDisplay_HAL(pGpu)) return NV_ERR_NOT_SUPPORTED;
   ```
   Tắt GSP (`EnableGpuFirmware=0`) chuyển sang RM chạy trên host — **cùng hàm, cùng fuse `0x021C04`, cùng kết quả**.

2. **GSP không tham gia quyết định này.** Đã kiểm trên ELF 615.78.08:
   - Literal `0x00021C04`: **0 hit** toàn file
   - Literal `0x00820C04`: **0 hit**
   - `lui 0x21` + `lw/addi 0xC04`: **0 hit** trong `.rm_text` (0x1039000 byte)

3. **Nouveau cũng chặn ở đúng fuse đó.** `pramin_init()` đọc `0x021c04`, bit 0 = 1 → `-ENODEV`, trước cả VBIOS parse. Nouveau không có GSP.

⇒ **Kết luận B:** khuyến nghị tắt GSP là **cải thiện tương thích/hiệu suất**, **không liên quan đến display gates**. Nó hạ tầng quản lý xuống RM host — nơi driver Turing đã trưởng thành — giảm overhead và tránh lỗi GSP trên card bị cắt. Display vẫn bị chặn y hệt.

### B.4 Một quan sát phụ đáng ghi

Việc tắt GSP **có thể** có ý nghĩa *nếu* ai đó muốn patch đường display — vì khi đó chỉ cần sửa một nhánh (host RM), không phải sửa cả host RM **và** firmware GSP. Nhưng đó là hệ quả kỹ thuật của việc tắt GSP, **không** phải lý do dự án đưa ra.

---

## C. PHƯƠNG PHÁP OPT/RECONFIG/OVR TỪ 170HX — ÁP DỤNG ĐƯỢC CHO TU106?

### C.1 Mô hình của cmp.wiki

Từ `Full_SM_unlock` (nguyên văn @akuchen):

> "a TPC is off when its OTP fuse bit (OPT) is set, or when its soft reconfiguration bit (RECONFIG) is set and the override bit (OVR) is not, written as `STATUS = OPT | (RECONFIG & ~OVR)`"

Ba tầng: **OPT** (fuse cháy, không đảo được) · **RECONFIG** (bit mềm) · **OVR** (bit ghi đè).

Log thật khi unlock 70→74 SM (cây 610.43.03):
```
RECONF: REENABLE gpc3 elig=0x1 OVR 0x0->0x1 STATUS 0x1->0x0
```

Và giới hạn đã cộng đồng xác nhận:
> "Ctrl_opt is remove only, not additive" — @Humvee55
> "The effective mask is OTP OR software control, so fused-off SMs cannot be re-enabled this way, only more can be disabled"

### C.2 Đây là mô hình **GA100**, không phải TU106

`Fuses_and_floorsweep_maps` mở đầu: *"Every CMP 170HX carries a full GA100 die"*. Toàn bộ register (OPT_GPC_DISABLE, OPT_FBP_DISABLE, RIR, EN_SW_OVERRIDE) là của **GA100/Ampere**.

**Không được bê register GA100 sang TU106.** Với TU106, `tu102/dev_fuse.h` chỉ có 2 định nghĩa fuse liên quan:
```c
#define NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS   0x0002174C
#define NV_FUSE_OPT_NVDEC_DISABLE          0x00021378
```
Không có `OPT_GPC_DISABLE`, không có `OPT_TPC_DISABLE`, không có `RECONFIG`, không có `OVR` — **trong header công bố của Turing**.

### C.3 Tìm cơ chế tương đương trên TU106 — bằng chứng trực tiếp

**Kết quả: KHÔNG tìm thấy cơ chế OPT/RECONFIG/OVR nào cho display trên TU106.**

Sau đây là những gì đã kiểm tra và loại trừ:

| Kiểm tra | Kết quả |
|---|---|
| `NV_FUSE_STATUS_OPT_DISPLAY` quyền truy cập | **`R-I4R`** = Read-only. Không có đường ghi. |
| Ghi vào `0x21C04` trong toàn bộ RM source | **0 store** |
| Tên `RECONFIG` / `OVR` / `EN_SW_OVERRIDE` trong `swref/published/turing/` | **0 hit** |
| Cửa sổ fuse thứ hai (đọc raw OTP độc lập) | Không có — chỉ `0x21000` |
| `GET_TPC_RECONFIG_MASK` (0x208001E7) | Trả `NV_ERR_NOT_SUPPORTED` trên card này (T6) |

### C.4 Cái TU106 **thực sự** có: một flag trạng thái display trong GSP-RM

Đây là **cơ chế tương đương gần nhất** tìm được, nhưng nó là **bit phần mềm trong GSP**, không phải fuse:

Handler `NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` (`0x20800A4B`):
```
Dispatch record @0x04061958:  cmd=0x20800A4B size=0x4 const=0x040704C8 handler=0x04B9F5CC flags=0x000000C0
```

Disassembly handler `0x04B9F5CC` (code bytes thật):
```
4b9f5e8: 83 37 05 16   ld  a5, 0x160(a0)          # pGpu->pGspStaticInfo-ish
4b9f5ec: b7 24 00 00   lui s1, 0x2
4b9f5f0: 13 89 05 00   mv  s2, a1                  # s2 = out params (ipVersion*)
4b9f5f4: 03 b5 87 0e   ld  a0, 0xe8(a5)            # base
4b9f5f8: b3 04 95 00   add s1, a0, s1              # s1 = base + 0x2000
4b9f5fc: 83 b9 04 f6   ld  s3, -0xa0(s1)           # s3 = *(base + 0x1F60)
4b9f600: 63 86 09 00   beqz s3, 0x4b9f60c          # nếu s3==0 -> ipVersion=0
4b9f604: 83 47 a5 6e   lbu a5, 0x6ea(a0)           # a5 = display-state byte
4b9f608: 63 96 07 02   bnez a5, 0x4b9f634          # nếu !=0 -> nhánh phức tạp
4b9f60c: 93 07 00 00   li  a5, 0x0
4b9f610: 23 20 f9 00   sw  a5, 0x0(s2)             # *ipVersion = 0  <-- DISPv0000
...
4b9f634: 83 b5 04 f5   ld  a1, -0xb0(s1)
4b9f638: 97 70 0e 00   auipc ra, 0xe7
4b9f63c: e7 80 80 cc   jalr -0x338(ra)             # gọi hàm lấy ipVersion thật
4b9f640: 63 0e 05 00   beqz a0, 0x4b9f65c
4b9f644: b7 77 00 00   lui a5, 0x7
4b9f648: b3 89 f9 00   add s3, s3, a5
4b9f64c: 83 c7 89 46   lbu a5, 0x468(s3)
4b9f650: 63 84 07 02   beqz a5, 0x4b9f678
4b9f654: 93 07 40 00   li  a5, 0x4          -> ipVersion = 4
4b9f678: 93 07 30 00   li  a5, 0x3          -> ipVersion = 3
```

**Đọc được từ đây:**
- `ipVersion = 0` (⇒ `DISPv0000`) khi `s3 == 0` **hoặc** byte `0x6EA(base) == 0`.
- Đường lấy ipVersion thật gọi qua con trỏ `-0xb0(s1)` = `*(base+0x1F50)` — một callback slot, không phải hằng số.
- 11 site `sb ...,0x6ea(rs1)` ghi byte này (tại `0x4A128D4`, `0x4B6F3EC`, `0x4C89784`, `0x4C95FDC`, `0x5306DE4`, `0x530713C`, `0x5307604`, `0x53076C4`, `0x5382D2C`, `0x5382F08`, `0x538314C`).

**Nhưng:** handler này **chưa bao giờ được gọi** trên CMP 40HX — host chặn ở `kern_disp.c:444` trước khi gửi control. Nên giá trị `ipVersion` thật của card này hiện **chưa biết**.

### C.5 Trả lời trực tiếp câu C

| Câu hỏi | Trả lời |
|---|---|
| Có cơ chế OPT/RECONFIG/OVR cho **display** trên TU106? | **Không tìm thấy.** Không có định nghĩa trong header Turing công bố; `NV_FUSE_STATUS_OPT_DISPLAY` là read-only. |
| Có cơ chế tương đương **khác loại**? | **Có** — bit trạng thái `0x6EA` trong struct GSP + `s3 = *(base+0x1F60)`, quyết định `ipVersion = 0` hay giá trị thật. Nhưng đây là **trạng thái phần mềm**, không phải fuse, và **không ghi được từ host**. |
| Học được gì từ 170HX? | **Phương pháp**: tách OPT / RECONFIG / OVR, và luôn hỏi "cái nào cháy cứng, cái nào ghi đè được". Kết quả áp dụng cho TU106: **không có tầng OVR nào cho display được công bố.** |
| Điều KHÔNG được làm | Sao chép `EN_SW_OVERRIDE`, `RIR fuse burn`, `OPT_TPC_DISABLE` của GA100 sang TU106. Đó là register khác chip, khác block. |

---

## D. ĐỐI CHIẾU VỚI DỮ LIỆU CMP 40HX ĐÃ XÁC MINH

| Dữ kiện | Giá trị | Nguồn/xác minh |
|---|---|---|
| `0x021C04` | **`0x00000001`** | Đọc BAR0 read-only; `0x21378=0`, `0x2174C=1` làm đối chứng cửa sổ fuse thật |
| `BIT_U NO_DISPLAY_SUBSYSTEM` | **1** | Token `U` @ image+0x03CE → file `0x289CE`, raw `00 00 02 00 00`, flags `0x02` |
| `DCB entry_count` | **0** | DCB @ `0x2D9AC`, ver `0x41`, sig `0x4EDCBDCB`, `hdr=0x23`, `cnt=0` |
| Host `kdispStatePreInitLocked` | **Từ chối** | `kern_disp.c:444-445` → `NV_ERR_NOT_SUPPORTED` |
| `nvidia-drm` | Không CRTC | dmesg: `Cannot find any crtc or sizes` |
| `nvidia-smi` | `Display Attached: No`, `Display Active: Disabled` | đọc trên target |

### D.1 Ba cờ displayless độc lập, cùng bật

```
[1] Silicon : 0x021C04 = 1                    → RM từ chối tạo display
[2] VBIOS   : NO_DISPLAY_SUBSYSTEM = 1        → build theo nhánh coproc/displayless
[3] VBIOS   : DCB entry_count = 0             → không có connector nào được khai báo
```

Ba cờ này **không nhân quả với nhau** — chúng là ba dấu hiệu của cùng một quyết định sản phẩm, ở ba tầng khác nhau (silicon / policy / bảng dữ liệu board).

### D.2 Đối chiếu GeForce TU106 cùng die

| | CMP 40HX (`1F0B`) | RTX 2060S (`1F06`) | RTX 2070 (`1F07`) |
|---|---|---|---|
| BIOS | `90.06.67.00` | `90.06.44.00` | `90.06.3D.00` |
| `0x021C04` | **1** | *chưa đo* | *chưa đo* |
| `NO_DISPLAY_SUBSYSTEM` | **1** | **0** | **0** |
| DCB `entry_count` | **0** | **16** (7 output thật) | **16** (5 output thật) |
| `B+32` | `0x12` | `0x10` | `0x10` |
| `B+28` (Module Map Ext 0) | `0x36` | `0x36` | `0x36` |

Ghi chú trung thực: `B+32` khác nhau (0x12 vs 0x10) nhưng **vai trò chưa xác định** — spec NVIDIA rev 1 không định nghĩa offset này trong `BIT_BIOSDATA` v2 (bản ghi khai báo 37 byte nhưng spec chỉ mô tả tới `0x20`). Không dùng nó làm bằng chứng.

---

## E. PHÂN LOẠI BỐN TRẠNG THÁI — KHÔNG ĐÁNH ĐỒNG

### E.1 Định nghĩa và trạng thái thực tế

#### ① GPU có thể render 3D — **CÓ**

- GR engine hoạt động; `CMP40_COMPUTE_UNLOCK` chạy thành công (`SS0=0x88888888`, `RESET_PLM=0x000000ff`).
- GSP ready: `CMP40_GSP_READY_V551: feature=0x000000f3 ss0=0x88888888`.
- Sau khi cài patcher, D3D/Vulkan/OpenGL render được **vào bộ nhớ frame**, xuất qua GPU khác.
- **Không liên quan display**: 3D render không cần PDISP, không cần SOR, không cần PHY.

#### ② Driver nhận là display-class GPU — **KHÔNG** (trên Linux, driver gốc)

- `nvidia-drm` nạp, tạo `minor 1`, nhưng: **`Cannot find any crtc or sizes`**.
- `nvidia-smi`: `Display Active: Disabled`.
- Trên **Windows** với patcher: Windows *nhận* card như adapter đồ hoạ (INF + `AdapterType=1`) — nhưng đó là **nhận dạng ở tầng PnP/registry**, không phải "display engine đang chạy".
- Phân biệt cốt lõi: **được liệt kê là adapter** ≠ **có CRTC để quét ra màn hình**.

#### ③ Display engine thực sự hoạt động — **KHÔNG**

- `kdispStatePreInitLocked` return `NV_ERR_NOT_SUPPORTED` tại `kern_disp.c:444-445`.
- Không chạy: `NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` (0x20800A4B), `gpuInitDispIpHal`, `kdispStateInitLocked`, `kdispInitBrightcStateLoad`.
- `KernelDisplay` object **được tạo** (`ENG_CLASS_KERNEL_DISPLAY → IS_FW_CLIENT = TRUE`) rồi **bị huỷ** (`gpuDestroyMissingEngine`).
- `DISPv0000` HAL nếu có ai gọi = HAL rỗng, không CRTC.
- **Chưa đo được** `ipVersion` thật (handler chưa từng chạy).

#### ④ DP/HDMI phát tín hiệu vật lý — **KHÔNG**

- Không có CRTC ⇒ không có display pipeline.
- DCB `entry_count = 0` ⇒ VBIOS **không khai báo connector nào** (không DP, không TMDS, không eDP).
- Không có connector được enumerate: sysfs chỉ có `card0-DP-1` **của card khác** ở `04:00.0`.
- **Chưa xác định** PCB có linh kiện DP/HDMI hay không — cần boardview/ảnh mặt sau card.

### E.2 Bảng phân loại dứt khoát

| Trạng thái | Đạt được bằng patcher? | Đạt được bằng cmpunlocker? | Đạt được bằng sửa VBIOS? | Điều kiện thực sự cần |
|---|---|---|---|---|
| ① Render 3D | **✅ CÓ** | ✅ (compute) | ❌ | — (đã có) |
| ② Driver nhận display-class | một phần (Windows registry) | ❌ | ❌ | Bỏ gate fuse ở silicon |
| ③ Display engine chạy | ❌ | ❌ | ❌ | Gate fuse + `ipVersion != 0` + tạo được KernelDisplay |
| ④ Tín hiệu DP/HDMI | ❌ | ❌ | ❌ (DCB rỗng là hệ quả, không phải nguyên nhân) | ③ + DCB connector entries + linh kiện PCB + PHY hoạt động |

### E.3 Cái gì thực sự ngăn display — xếp theo tầng

```
TẦNG SILICON   fuse 0x021C04 bit0 = 1  (R-I4R, read-only)
   ↓  gpuFuseSupportsDisplay_GM107 → NV_FALSE
TẦNG DRIVER    kern_disp.c:444 return NV_ERR_NOT_SUPPORTED
   ↓  KernelDisplay bị huỷ, class DISPLAY_COMMON gỡ khỏi classDB
TẦNG GSP       (chưa chạy tới) ipVersion path → 0 nếu sbox 0x6EA = 0
   ↓
TẦNG VBIOS     NO_DISPLAY_SUBSYSTEM=1, DCB cnt=0  ← nhất quán với silicon
   ↓
TẦNG BOARD     (chưa kiểm PCB) connector/PHY linh kiện
```

**Điều kiện cần để khôi phục display, xếp theo thứ tự bắt buộc:**

1. **Gate silicon phải mở.** Hoặc `0x021C04` bit0 phải đọc ra 0 — điều này **không làm được** qua phần mềm (`R-I4R`, 0 store trong toàn bộ RM, GSP không chạm). Cần: thay die, hoặc tìm được cửa sổ/đường đọc khác chưa biết.
2. **`ipVersion != 0`** từ GSP/hardware (handler `0x04B9F5CC`). Hiện **chưa đo được**.
3. **VBIOS phải khai báo connector** (DCB entry > 0) — hiện `cnt=0`.
4. **Board phải có linh kiện DP/HDMI** — **chưa kiểm**.
5. **PHY/SOR phải hoạt động** — **chưa kiểm**.

Bước 1 là chốt chặn tuyệt đối. Mọi nỗ lực ở bước 2–5 đều vô nghĩa nếu bước 1 chưa mở.

---

## F. NHỮNG GÌ CMP.WIKI NÓI VỀ 40HX — VÀ NHỮNG GÌ NÓ KHÔNG NÓI

### F.1 Có nói

| Nội dung | Nguyên văn / nguồn |
|---|---|
| CMP 40HX = `1F0B`, có trong open-gpu-kernel-modules | *"NVIDIA's open kernel module source lists the other CMP models by PCI device ID: … CMP 40HX `1F0B` …"* |
| cmpunlocker **chỉ** làm 170HX | @_j3ns: *"I'm going to stick to 170HX only"* (2026-09-14) |
| 170HX là GA100, 40HX là chip khác | *"Every CMP 170HX carries a full GA100 die"* — 40HX là TU106 |
| Mô hình OPT/RECONFIG/OVR là của GA100 | `STATUS = OPT \| (RECONFIG & ~OVR)` — ngữ cảnh 170HX |
| Có dự án riêng mở GR engine cho 90HX/70HX | Icyoung/cmpunlocker `tools/gr_unlock`, patch driver đóng `610.43.02`, *"enables the Graphics (GR) engine (3D, display output, OpenGL/Vulkan/CUDA graphics)"* trên `220d`/`248a` — **không** phải 40HX |
| Ý tưởng dùng GPU khác xuất hình | *"letting a display GPU own the window and presentation queue while the CMP renders to a texture, or a virtual display such as Xvfb, or NVIDIA PRIME render offload; untested on a CMP"* |

### F.2 KHÔNG nói

- **Không** có mục nào về khôi phục display cho CMP 40HX.
- **Không** có dữ liệu fuse/register TU106 nào.
- **Không** có ai trong export báo từng thấy CMP 40HX xuất hình.
- Wiki tự giới hạn phạm vi: *"Nothing on this page is CMP 170HX unlock work unless the entry says so… these notes are here because the questions keep coming, and they are thinner than the 170HX pages."*
- Export Discord bắt đầu 2026-10-04 — **thiếu toàn bộ trao đổi trước đó** về các card khác.

⇒ Trạng thái display của CMP 40HX **không có tiền lệ cộng đồng** trong nguồn này. Không có bằng chứng ai đã làm được, cũng không có bằng chứng ai đã chứng minh là không thể.

---

## G. TỔNG KẾT

| Mệnh đề | Trạng thái |
|---|---|
| Patcher cho CMP 40HX render 3D bằng cách đổi device-ID table + INF/registry | **PROVEN** — mẫu hex khớp 1 lần trong `nv-kernel.o_binary` 115.570.992 B, bảng 24 entry tại `0x5FE26CC` |
| Patcher **không** mở display | **PROVEN** — không chạm fuse, KernelDisplay, PDISP, SOR, PHY, VBIOS |
| Tắt GSP giúp display | **BÁC BỎ** — cùng gate fuse trong host RM; GSP 0 hit trên cửa sổ fuse |
| Có cơ chế OPT/RECONFIG/OVR cho display trên TU106 | **KHÔNG TÌM THẤY** — `R-I4R`, 0 store, không header |
| CMP 40HX hiện render 3D được | **CÓ** |
| CMP 40HX hiện là display-class GPU đang hoạt động | **KHÔNG** |
| Display engine CMP 40HX đang chạy | **KHÔNG** |
| CMP 40HX phát được tín hiệu DP/HDMI | **KHÔNG** |
| Khôi phục display khả thi | **CHƯA CHỨNG MINH ĐƯỢC, cũng CHƯA BÁC BỎ ĐƯỢC** — chốt chặn là fuse silicon read-only |

---

## H. HASH VÀ ĐƯỜNG DẪN

| Đối tượng | Giá trị |
|---|---|
| GSP wrapper | `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b` |
| GSP inner ELF | `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85` |
| CMP VBIOS gốc | `dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec` |
| Source RM | tag `615.78.08` @ `1a82fbfda8f321b056eb3568850f9316c5e465c5` |
| `nv-kernel.o_binary` (615.78.08) | 115.570.992 B, CMP pattern @ `0x5FE26F0`, bảng bắt đầu `0x5FE26CC` |
| Parser VBIOS | `/home/REDACTED_USER/.hermes/cache/scratch/vbios_final.py` (kèm `--selftest`) |
| Dispatch record `0x20800A4B` | vaddr `0x04061958`, handler `0x04B9F5CC`, payload `0x4` |
| Nguồn web | cmp.wiki ×3, github.com/dartraiden/NVIDIA-patcher (repo + `linux.sh` + `Presets.txt` + `docs/README-LINUX.md`), download.nvidia.com/open-gpu-doc BIT spec, torvalds/linux nouveau |

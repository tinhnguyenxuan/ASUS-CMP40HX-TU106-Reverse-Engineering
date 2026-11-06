# D1-A — PRODUCER CỦA `NV_FUSE_STATUS_OPT_DISPLAY` @ 0x021C04

**GPU:** NVIDIA CMP 40HX, TU106-100-A1, PCI 10DE:1F0B, BDF 0000:03:00.0
**Driver:** 615.78.08 · **GSP:** `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`
**Source đối chiếu:** open-gpu-kernel-modules tag `615.78.08` @ `1a82fbfda8f321b056eb3568850f9316c5e465c5`
**Ngày:** 2026-11-06 · Phân tích offline + đọc MMIO read-only

---

## 1. Định danh thanh ghi

`src/common/inc/swref/published/maxwell/gm107/dev_fuse.h:27-29`
```c
#define NV_FUSE_STATUS_OPT_DISPLAY        0x00021C04 /* R-I4R */
#define NV_FUSE_STATUS_OPT_DISPLAY_DATA           0:0 /* R-IVF */
#define NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE 0x00000000 /* R---V */
```

- Quyền truy cập khai báo: **`R-I4R`** — Read, Inner, 4-byte, **Read-only**.
- Field duy nhất: `DATA[0:0]`, giá trị "enabled" = `0x0`.

### 1.1 Register thuộc block nào trên TU106 — chứng minh bằng số học địa chỉ

`dev_fuse.h` của TU102 **không** định nghĩa `0x21C04`; nó chỉ có:

`src/common/inc/swref/published/turing/tu102/dev_fuse.h`
| Register | TU102 | GA100 (`dev_fuse.h`) | Δ |
|---|---|---|---|
| `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS` | `0x0002174C` | `0x0082074C` | `0x7FF000` |
| `NV_FUSE_OPT_NVDEC_DISABLE` | `0x00021378` | `0x00820378` | `0x7FF000` |

Hai register độc lập, khác block chức năng, cùng lệch đúng `0x7FF000`. Đây là **dịch chuyển cửa sổ (window relocation)**, không phải trùng hợp:

```
TU106 fuse window base = 0x820000 − 0x7FF000 = 0x21000
0x21C04 = 0x21000 + 0xC04     (offset nội bộ cửa sổ = 0xC04)
0x820C04 = 0x820000 + 0xC04   (cùng offset 0xC04 trên GA100)
```

⇒ `0x21C04` thuộc **fuse block** (cửa sổ `0x21000`), không phải PDISP/SOR/PGRAPH. Giá trị `0xC04` là ô fuse status OPT, không phải display logic.

**Mức tin cậy: PROVEN** (số học khớp trên hai register độc lập + định nghĩa header).

---

## 2. Đường đọc trong NVIDIA RM

### 2.1 HAL dispatch cho TU106

`src/nvidia/generated/g_gpu_nvoc.c:2094-2098`
```c
2094|    // gpuFuseSupportsDisplay -- halified (5 hals) body
2095|    if (( ((chipHal_HalVarIdx >> 5) == 1UL) && ((1UL << (chipHal_HalVarIdx & 0x1f)) & 0x000003e0UL) ))
2096|         /* ChipHal: TU102 | TU104 | TU106 | TU116 | TU117 */
2097|    {
2098|        pThis->__gpuFuseSupportsDisplay__ = &gpuFuseSupportsDisplay_GM107;
2099|    }
```
TU106 nằm trong mask `0x3e0` ⇒ dùng `gpuFuseSupportsDisplay_GM107`.

### 2.2 Thân hàm đọc

`src/nvidia/src/kernel/gpu/arch/maxwell/kern_gpu_gm107.c:62-73`
```c
66|NvBool
67|gpuFuseSupportsDisplay_GM107
68|(
69|    OBJGPU *pGpu
70|)
71|{
72|    return GPU_FLD_TEST_DRF_DEF(pGpu, _FUSE, _STATUS_OPT_DISPLAY, _DATA, _ENABLE);
73|}
```

Macro mở rộng thành `GPU_REG_RD32(pGpu, NV_FUSE_STATUS_OPT_DISPLAY)`, rồi so sánh `DATA` với `DATA_ENABLE (0x0)`.

### 2.3 Fuse base = 0 trên TU106 ⇒ địa chỉ tuyệt đối chính là 0x21C04

`src/nvidia/generated/g_gpu_nvoc.c:2889` — `gpuGetPrimaryFuseBaseAddr_b2b553` trả về **0** cho TU102/TU104/TU106. Do đó phép đọc không cộng base:
```
địa chỉ thực = BAR0 + 0 + 0x21C04 = BAR0 + 0x21C04
```

**Đính chính (kiểm toán):** thanh ghi MMIO này nằm trong **BAR0** (`resource0`), không phải BAR1. Bằng chứng: chương trình đọc read-only mở `/sys/bus/pci/devices/0000:03:00.0/resource0` và `mmap` 16 MiB đầu — đọc ra `0x0 = 0x166000A1` (NV_PMC_BOOT_0, đúng giá trị định danh chip) cùng các ô fuse. BAR1 là cửa sổ instmem/PRAMIN, không chứa `0x21C04` (offset < 16 MiB).
```
Kiểm chứng bằng `nvidia.ko` trên target: literal `0x00021C04` xuất hiện **đúng 1 lần** trong 36.118.136 byte module (cùng với `0x21378` 1 lần, `0x2174C` 1 lần). Không có bản sao thứ hai ⇒ chỉ một điểm đọc.

### 2.4 So sánh với GA100 — GA100 mới là bên cộng base

`gpuFuseSupportsDisplay_GA100` gọi `gpuGetPrimaryFuseBaseAddr_HAL(pGpu) + NV_FUSE_ZB_STATUS_OPT_DISPLAY`. Bản GM107 (dùng cho Turing) **không** cộng base. Vì base TU106 = 0, hệ quả giống nhau; nếu base TU106 khác 0 thì GM107 sẽ đọc sai. Đây là khác biệt kiến trúc, không phải lỗi ở đây.

**Mức tin cậy: PROVEN.**

---

## 3. Đường đọc trong Nouveau

`drivers/gpu/drm/nouveau/nvkm/subdev/bios/shadowramin.c`, `pramin_init()` (nguyên văn, Linux master):

```c
	/* we can't get the bios image pointer without PDISP */
	if (device->card_type >= GA100)
		addr = nvkm_rd32(device, 0x820c04);
	else
	if (device->card_type >= GM100)
		addr = nvkm_rd32(device, 0x021c04);
	else
	if (device->card_type >= NV_C0)
		addr = nvkm_rd32(device, 0x022500);

	if (addr & 0x00000001) {
		nvkm_debug(subdev, "... display disabled\n");
		return ERR_PTR(-ENODEV);
	}
```

**Điều kiện thực tế (kiểm toán xác nhận):** TU106 có `card_type >= GM100` và `< GA100` ⇒ đọc `0x021C04`. Trên CMP 40HX giá trị là `0x00000001`, nên `addr & 1 == 1` → **`nvkm_debug` "... display disabled" → return `ERR_PTR(-ENODEV)`**.

Ba điểm cần đúng:

1. **Comment của chính NVIDIA** — *"we can't get the bios image pointer without PDISP"* — nghĩa là biến `addr` này **không phải** một cờ display thuần tuý; nó là **con trỏ/giá trị cần cho PDISP**, và bit 0 là dấu hiệu display bị tắt.
2. **Chặn trước toàn bộ VBIOS parse.** `pramin_init` là shadow method; fail ⇒ `nvbios_shadow` fail ⇒ `nvkm_bios_new` fail. Nouveau **không đọc được VBIOS** trên card này, nên không bao giờ tới PDISP init.
3. ⚠️ **Không coi đường PRAMIN này là toàn bộ gate display.** Nó chỉ là gate **của Nouveau**. Đường NVIDIA RM dùng hàm riêng (`gpuFuseSupportsDisplay_GM107`, §2) — đọc **cùng thanh ghi, cùng bit**, nhưng ở vị trí khác trong luồng khởi tạo và không phụ thuộc PRAMIN. Hai consumer độc lập của cùng một fuse, không phải một gate duy nhất.

**Mức tin cậy: PROVEN** (code nguyên văn từ upstream + giá trị silicon đo được).

---

## 4. Nguồn khởi tạo trước khi host RM đọc

### 4.1 GSP-RM 615.78.08: **không tìm thấy đường đọc literal** tới cửa sổ fuse 0x21000

Ba phép tìm độc lập trên `gsp_tu10x_615.78.08_inner.elf` (SHA-256 `cd83bb04…3a2cfe85`):

| Tìm kiếm | Kết quả |
|---|---|
| Literal dword `0x00021C04` toàn file | **0 hit** |
| Literal dword `0x00820C04` toàn file | **0 hit** |
| `lui rd, 0x21` trong `.rm_text` (0x4588000, 0x1039000 B) | 36 hit — **không** hit nào theo sau bởi `lw/addi 0xC04` (kiểm 4 mẫu gần nhất: `0x648`, `0x640`, `0x654` — bảng khác) |
| `lui rd, 0x82` trong `.rm_text` | 6 hit — tất cả là `lui a1,0x82; addi a1,a1,0x24` = `0x8224` (**SPI flash config**), không phải fuse |

⚠️ **Giới hạn của kết luận này (kiểm toán):** "không tìm thấy literal" **không** chứng minh "GSP không có consumer". Có ít nhất ba cách GSP vẫn đọc được mà không để lại literal:
1. Địa chỉ fuse base lấy từ **bảng cấu hình** (NVKV/NVGMC_SC) chứ không hard-code.
2. Địa chỉ được tính qua **con trỏ hàm/callback slot** (như `*(base+0x1F50)` ở handler `0x04B9F5CC`).
3. Đọc qua **fuse HAL** dùng chung, tham số hoá theo chip.

Kết luận đúng phạm vi: **không có bằng chứng GSP là producer/consumer của bit này**, và **chưa loại trừ được** GSP/devinit đọc nó qua đường gián tiếp. Xem T-B1 (§6) để phân biệt.

### 4.1b Điều đã loại trừ được chắc chắn

Điều duy nhất loại trừ được **bằng chứng cứng**, không phải bằng vắng mặt literal:
- **Không phần mềm nào ghi vào `0x21C04`.** Header khai báo `R-I4R` (read-only). `grep -rn "21C04"` trên toàn bộ 147 MB source RM → chỉ có khai báo và macro test, **0 store**. Đây là bằng chứng loại trừ lớp firmware/software-**configured**, không phải loại trừ lớp firmware/devinit-**đọc**.

### 4.2 Không có driver/software nào ghi vào 0x21C04

`grep -rn "21C04|0x21c04"` trên toàn bộ source RM (147 MB) → chỉ có khai báo header và macro test, **không có store**.
Header khai báo `R-I4R` (read-only). Không có `IOR`/`IOW` path.

### 4.3 Giá trị sống trên silicon

Đọc read-only qua BAR0 (chương trình `/tmp/rd21604`, mmap `resource0` PROT_READ, không ghi):

```
0x021000 = 0xC0040000     ← cửa sổ fuse; byte thấp 00 00 04 C0: hợp lệ
0x021378 = 0x00000000     ← NVDEC_DISABLE = 0 (NVDEC enabled)
0x02174C = 0x00000001     ← SECURE_GSP_DEBUG_DIS = 1
0x021C00 = 0x00000000
0x021C04 = 0x00000001     ← OPT_DISPLAY DATA=1
0x021C08 = 0x0000000F
```

**Đối chứng nội tại:** `0x21378=0` và `0x2174C=1` là hai ô fuse **khác block** đọc ra giá trị khác nhau, có ý nghĩa riêng. Nếu cửa sổ fuse không được route đúng, cả ba sẽ trả cùng một hằng số rác. Chúng không như vậy ⇒ **cửa sổ 0x21000 đang trả dữ liệu fuse thật.**

`0x21C04=1 ≠ DATA_ENABLE(0)` ⇒ hàm trả `NV_FALSE` ⇒ `kdispStatePreInitLocked` trả `NV_ERR_NOT_SUPPORTED`.

---

## 5. Phân biệt bốn lớp (yêu cầu A.5)

| Lớp | Kết luận | Bằng chứng |
|---|---|---|
| **Raw OTP fuse** | **SUPPORTED, chưa PROVEN** | Đọc được từ cửa sổ fuse, hai ô anh em trả giá trị khác nhau ⇒ cửa sổ thật. Nhưng chưa có phép đọc nào phân biệt shadow-latch với raw OTP trên TU106. |
| **Hardware-latched fuse state** | **CHƯA LOẠI TRỪ ĐƯỢC — đây là khe hở chính** | Không có phép đọc nào trong giới hạn D1 phân biệt shadow-latch với raw OTP. Không được coi "giữ nguyên sau reboot" là bằng chứng. |
| **Firmware/software-configured** | **LOẠI TRỪ được phần *ghi*, chưa loại trừ phần *đọc*** | Không phần mềm nào **ghi** vào `0x21C04` (`R-I4R`, 0 store trong 147 MB RM). Nhưng GSP/devinit **có thể đọc** giá trị này qua đường gián tiếp và **có thể** đã set nó ở reset — chưa loại trừ (§4.1). |
| **SKU policy / devinit** | **CÓ, song song — không thay thế** | VBIOS CMP đặt `NO_DISPLAY_SUBSYSTEM=1` và `DCB entry_count=0` (xem D1-VBIOS). Đây là gate **thứ hai**, độc lập với fuse. Việc devinit **có ghi** `0x21C04` hay không: **chưa xác định**. |

### Những gì KHÔNG được dùng làm bằng chứng (đúng như prompt yêu cầu)

- ❌ "Giá trị giữ nguyên sau reboot" ⇒ **không** dùng. Shadow register cũng giữ nguyên nếu cùng điều kiện latch.
- ❌ "Nouveau đọc 0x21C04 và bỏ cuộc" ⇒ **không** dùng làm toàn bộ gate. Nouveau chỉ là consumer thứ hai.
- ❌ "`tu102/dev_fuse.h` không định nghĩa 0x21C04" ⇒ **không** dùng để nói register không tồn tại. §1.1 chứng minh nó tồn tại qua dịch chuyển cửa sổ.
- ❌ "Không tìm thấy instruction ghi" ⇒ **không** dùng để kết luận raw OTP. Ngược lại: nó chỉ loại trừ lớp firmware/software.

---

## 6. Đường dữ liệu bị đứt ở đâu

Chuỗi đã xác định **đầy đủ đến mức consumer**, và consumer đã được chứng minh:

```
OTP fuse cell (offset 0xC04 trong block fuse)      ← PRODUCER: không đọc được offline
        │  (latch ở reset — cơ chế chưa xác định)
        ▼
MMIO 0x021C04 = 0x00000001                          ← ĐỌC ĐƯỢC, read-only, R-I4R
        │  GPU_REG_RD32, base=0
        ▼
gpuFuseSupportsDisplay_GM107()                      ← kern_gpu_gm107.c:66-73
        │  GPU_FLD_TEST_DRF_DEF(_FUSE,_STATUS_OPT_DISPLAY,_DATA,_ENABLE)
        │  1 != 0 ⇒ NV_FALSE
        ▼
kdispStatePreInitLocked_IMPL() : kern_disp.c:444-445
        │  if (!gpuFuseSupportsDisplay_HAL(pGpu)) return NV_ERR_NOT_SUPPORTED;
        ▼
engstateIsPresent → NV_FALSE
        │  gpu.c:1748-1755: engine missing ⇒ gpuDestroyMissingEngine()
        ▼
KernelDisplay object bị huỷ, class DISPLAY_COMMON bị gỡ khỏi classDB
        ▼
nvidia-drm: "Cannot find any crtc or sizes"          ← QUAN SÁT ĐƯỢC TRÊN TARGET
```

### Điểm đứt chính xác

**Đứt tại ranh giới silicon: từ ô OTP vật lý đến giá trị MMIO đọc được.**

Không có đường phần mềm nào để quan sát raw OTP trên TU106 từ host:
- Không có cửa sổ MMIO thứ hai đọc raw OTP độc lập với shadow (đã kiểm: chỉ `0x21000`).
- Không gọi được `RmDisableFwseclic`/`RmDisableSec2` qua host (đã xác định ở T1–T8).
- SEC2 firmware là NVIDIA Falcon ISA, không có disassembler trên target.

### Phép kiểm tra phân biệt còn lại (khả thi, read-only)

| # | Phép kiểm | Phân biệt được gì | Điều kiện |
|---|---|---|---|
| **T-A1** | Đọc `0x21C04` ngay sau `echo 1 > /sys/bus/pci/devices/…/reset` **trước khi** load driver, qua `pci_mmap_resource` | Nếu = 1 trước khi bất kỳ firmware nào chạy ⇒ giá trị do silicon/devinit ROM set, không phải GSP | Cần kernel module đọc BAR sớm; chưa làm |
| **T-A2** | Flash ROM GeForce TU106 lên card, đọc lại `0x21C04` | Nếu vẫn = 1 ⇒ fuse thắng VBIOS (H2). Nếu = 0 ⇒ VBIOS điều khiển được (H1) | ⚠️ Flash — **ngoài giới hạn an toàn D1**, cần quyết định riêng của anh Tĩnh |
| **T-A3** | So sánh `0x21C04` trên một CMP 40HX thứ hai | Nếu mọi CMP 40HX đều = 1 ⇒ SKU-level fuse programming, không phải lỗi riêng die | Cần card thứ hai |

---

## 7. Kết luận mục A

| Mệnh đề | Trạng thái |
|---|---|
| Display đang bị vô hiệu trong môi trường hiện tại | **PROVEN** — `0x21C04=1`, gate trả `NV_ERR_NOT_SUPPORTED`, dmesg "Cannot find any crtc" |
| Nguyên nhân được chứng minh ở mức phần cứng (raw OTP) | **CHƯA PROVEN** — chỉ SUPPORTED; khe hở shadow-latch chưa đóng |
| Bit này chứng minh được là raw OTP bất biến | **CHƯA PROVEN** — không có phép đọc/ghi nào trong giới hạn D1 phân biệt được |

Đúng như yêu cầu: **không đánh đồng ba mệnh đề.**

### Điều đã đóng được so với T1–T6

- T1–T6 nói "UNKNOWN". Nay: producer **không phải** GSP (0 hit), **không phải** RM (0 store), **không phải** Nouveau (read-only). Chỉ còn silicon.
- T1–T6 nói "hard-fused". Nay: **chưa chứng minh**. Chỉ chứng minh được "không phần mềm nào trong hệ thống ghi được vào đây" — mệnh đề yếu hơn và khác về bản chất.
- T1–T6 nói "impossible". Nay: ghi rõ ba phép kiểm phân biệt còn lại và điều kiện thực hiện.

---

## 8. Hash tham chiếu

| Đối tượng | SHA-256 |
|---|---|
| GSP wrapper `gsp_tu10x.bin` | `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b` |
| GSP inner ELF | `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85` |
| `nvidia.ko` trên target | 36.118.136 byte, literal `0x21C04` × 1 |
| Source RM | tag `615.78.08`, commit `1a82fbfda8f321b056eb3568850f9316c5e465c5` |

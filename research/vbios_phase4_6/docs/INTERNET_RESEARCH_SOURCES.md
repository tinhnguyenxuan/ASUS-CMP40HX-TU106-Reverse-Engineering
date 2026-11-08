# NGUỒN NGHIÊN CỨU INTERNET — TU106 / CMP 40HX

> **Publication edition (V5):** This is a curated ROM/source-analysis extract from the supplied `vbiosrel6(2).zip`. Host telemetry, game tests, benchmark steps and Windows/Linux collectors are intentionally omitted. It is historical research, **not** new hardware verification. See [integrated report](../../../docs/TU106_VBIOS_PHASE4_6.md).


**Ngày truy cập:** 2026-11-07 · **bản v3**
**Nguyên tắc:** chỉ ghi cái đã đọc thật, kèm URL + symbol + (nếu có) commit. Mỗi mục nêu
**dùng để làm gì**. Mục §10 ghi lại những nơi **đã tra và không có** — để lần sau không
tra lại.

---

## 1. NVIDIA nvgpu `bios.h` — schema chính thức của mọi bảng Turing

**File:** `drivers/gpu/nvgpu/include/nvgpu/bios.h` — 52.845 byte
**URL đã đọc:** https://raw.githubusercontent.com/OE4T/linux-nvgpu/patches-rel-36/drivers/gpu/nvgpu/include/nvgpu/bios.h
**Repo gốc:** https://github.com/NVIDIA/nvgpu (mirror OE4T vì layout nhánh NVIDIA đổi)

Đây là header BIOS HAL do **NVIDIA viết**, chứa định nghĩa cấu trúc VBIOS đầy đủ cho
Turing — đúng phần `NVIDIA/open-gpu-kernel-modules` không có.

### 1.1 P-STATE v0x60
```c
#define VBIOS_PSTATE_TABLE_VERSION_6X        0x60U
#define VBIOS_PSTATE_HEADER_6X_SIZE_10       (10U)
#define VBIOS_PSTATE_BASE_ENTRY_6X_SIZE_5    0x5U
#define VBIOS_PSTATE_CLOCK_ENTRY_6X_SIZE_6   6U
#define VBIOS_PSTATE_CLOCK_ENTRY_6X_COUNT    10U
#define PERF_CLK_DOMAINS_IDX_MAX             (32U)
#define VBIOS_PERFLEVEL_SKIP_ENTRY           0xFFU

struct vbios_pstate_header_6x {
    u8 version, header_size, base_entry_size, base_entry_count,
       clock_entry_size, clock_entry_count, flags0, initial_pstate,
       cpi_support_level, cpi_features;
};
struct vbios_pstate_entry_6x {
    u8 pstate_level, flags0, lpwr_entry_idx, pcie_idx, nvlink_idx;
    struct vbios_pstate_entry_clock_6x nvgpu_clockEntry[PERF_CLK_DOMAINS_IDX_MAX];
};
struct vbios_pstate_entry_clock_6x { u16 param0; u32 param1; };

/* flags0 header */  PSTATES_MASK 0x1 / ARBITER_LOCK_MASK 0x2
/* flags0 entry  */  PSTATE_CAP 0x3 (RM_DEFAULT/GLITCHY/WAIT_VBLANK),
                    CUDA 0x4 (SAFE/NOT_SAFE), OVOC 0x8, DECREASE_THRESHOLD 0x10
/* clock        */  PARAM0_NOM_FREQ_MHZ 0x00003FFF,
                    PARAM1_MIN_FREQ_MHZ 0x00003FFF,
                    PARAM1_MAX_FREQ_MHZ 0x0FFFC000 (shift 14)
```
**Dùng để:** thay toàn bộ suy luận số học của v1; giải mã header (10 B), base entry (5 B),
clock entry (6 B × 10), `0xFF = SKIP`, min/max của `param1`.

**Quan trọng:** `PERF_CLK_DOMAINS_IDX_MAX = 32` chỉ **định cỡ mảng**, không đặt tên index.
Không có `PERF_CLK_DOMAINS_IDX_GPC` hay tương tự. Đây là lý do phải định danh domain từ
bảng v0x35 (§1.2), không phải từ header này.

### 1.2 CLOCKS v0x35 — nguồn định danh 10 domain
```c
struct vbios_clocks_table_35_header {
    u8 version, header_size, entry_size, entry_count, clocks_hal;
    u16 cntr_sampling_periodms, reference_window;
};
struct vbios_clocks_table_35_entry {
    u8 flags0; u16 param0; u32 param1; u16 param2; u16 param3;
};
NV_VBIOS_CLOCKS_TABLE_1X_ENTRY_FLAGS0_USAGE_FIXED   0x00U
NV_VBIOS_CLOCKS_TABLE_1X_ENTRY_FLAGS0_USAGE_MASTER  0x01U
NV_VBIOS_CLOCKS_TABLE_1X_ENTRY_FLAGS0_USAGE_SLAVE   0x02U
..._PARAM2_PROG_PRE_VOLT_ORDERING_IDX   bits 3:0
..._PARAM2_PROG_POST_VOLT_ORDERING_IDX  bits 7:4
..._PARAM1_SLAVE_MASTER_DOMAIN          bits 3:0
..._PARAM1_MASTER_FREQ_OC_DELTA_MIN/MAX_MHZ
```
**Dùng để:** giải mã bảng `0x2FB80`/`0x2FAA0`/`0x2FA90` (10 row × 11 B), lấy `usage` và
`ordering idx`. Ba giá trị USAGE là **toàn bộ** những gì spec nói — không có mô tả hệ quả.

### 1.3 Memory Clock v0x11 / Memory Tweak v0x20 / power sensors
`VBIOS_MEMORY_CLOCK_HEADER_11_2_SIZE = 26`,
`struct vbios_memory_clock_header_1x {version, header_size, base_entry_size,
strap_entry_size, strap_entry_count, entry_count, ...}`,
`VBIOS_MEMORY_CLOCK_BASE_ENTRY_11_2_SIZE = 20`,
`struct pwr_sensors_2x_header {version, header_size, table_entry_size,
num_table_entries, u32 ba_script_pointer}`.
**Dùng để:** xác nhận `ver 0x11` + `hlen 26` của slot 1 khớp tuyệt đối; base 60 / strap 33 /
entry 60 của TU106 là bản mở rộng, kiểm bằng extent.

### 1.4 FCT — dễ nhầm với domain index
```c
struct vbios_fct_1x_entry { u8 flags0; u8 clk_domain_idx; u16 param0; ... };
NV_VBIOS_FCT_1X_ENTRY_PARAM0_ID_SYS 0x00 / _LTC 0x01 / _XBAR 0x02
                     / _GPC0 0x03 ... _GPC5 0x08 / _GPCS 0x09
```
**Dùng để:** ghi lại **cảnh báo** — đây là enum khác (ID controller), **không** dùng làm
tên domain cho P-STATE. Nếu ai dùng nó, thứ tự sẽ sai (SYS=0 thay vì GPC=0).

### 1.5 LPWR index table — nơi `lpwr_entry_idx` trỏ tới
```c
struct nvgpu_bios_lpwr_idx_table_1x_header { u8 version, header_size, entry_size,
        entry_count; u16 base_sampling_period; };
struct nvgpu_bios_lpwr_idx_table_1x_entry {
        u8 pcie_idx, gr_idx, ms_idx, di_idx, gc6_idx; };
```
**Dùng để:** xác định `lpwr_entry_idx` là index vào bảng 5-byte, mỗi entry lại trỏ tiếp
sang 5 bảng low-power. Slot 29 của ROM decode ra `esz = 7` — **rộng hơn 2 byte** so với
struct này ⇒ ghi UNKNOWN, không ép schema.

### 1.6 Những gì `bios.h` **không** có
- Không đặt tên 32 slot `PERF_CLK_DOMAINS_IDX_*`.
- **Không có struct cho bảng PCIe config** mà `pcie_idx` trỏ tới.
- Không có schema POWER BUDGET / POWER TOPOLOGY / THERMAL POLICY.

---

## 2. nvgpu `common/vbios/bios.c` — CONSUMER thật của P2 directory

**URL:** https://raw.githubusercontent.com/OE4T/linux-nvgpu/patches-rel-36/drivers/gpu/nvgpu/common/vbios/bios.c
(23.042 byte)

`nvgpu_bios_get_perf_table_ptrs()` (dòng 676–730):
```c
perf_table_id_offset = *(u32 *)(bios->data + ptoken->data_ptr
                                + table_id * U16(PERF_PTRS_WIDTH));   /* = 4 */
...
if (perf_table_id_offset > g->bios->base_rom_size) {
        u32 tmp_index = nvgpu_safe_add_u32(g->bios->expansion_rom_offset,
                                           perf_table_id_offset);
        perf_table_ptr = &g->bios->data[tmp_index];
} else {
        perf_table_ptr = &g->bios->data[perf_table_id_offset];
}
```
Và `nvgpu_bios_parse_rom()` (dòng 290–345):
```c
if (code_type == PCI_DATA_STRUCTURE_CODE_TYPE_VBIOS_BASE)
        base_rom_size = pci_data.image_len * PCI_ROM_IMAGE_BLOCK_SIZE;   /* x512 */
if (code_type == PCI_DATA_STRUCTURE_CODE_TYPE_VBIOS_UEFI)
        expansion_rom_offset = pci_data.image_len * PCI_ROM_IMAGE_BLOCK_SIZE;
```

**Dùng để:** chứng minh **hai** điều mà v2 chỉ suy ra:
1. Con trỏ P2 slot N nằm tại `data_ptr + 4*N` (không phải tại bảng đích).
2. `raw > legacy_len` ⇒ cộng `efi_len`. Đây đúng là quy tắc `Rom.ptr()`.

Đây là nguồn cho lỗi export đã sửa ở v3 (`file_offset` vs `target_offset`).
Ghi chú biên: nvgpu dùng `>`, parser dùng `>=`; chỉ khác khi `raw == legacy_len` và không
ROM nào trong bộ này rơi vào đó.

---

## 3. NVIDIA open-gpu-doc

Repo: https://github.com/NVIDIA/open-gpu-doc · commit `9fdf5c4` (2026-06-09)

### 3.1 `Devinit/devinit.xml` (340.814 byte) — **nguồn mới quan trọng nhất ở v3**

Bảng opcode đầy đủ (`<opcode id=... value=...>`). Các opcode dùng trong bài:

| opcode | id | layout |
|---|---|---|
| `0x7A` | `INIT_ZM_REG` | addr(32) data(32) → **9 B**, `reg = data` |
| `0x6E` | `INIT_NV_REG` | addr(32) mask(32) data(32) → **13 B**, `reg = (reg & mask) \| data` |
| `0x75` | `INIT_CONDITION` | condition(8) → 2 B |
| `0x5B` | `INIT_SUB_DIRECT` | gọi chương trình con |
| `0xFF` | `EOL` | — |

**Dùng để:** giải mã `nvinit_ptrs.pcie_settings_script_ptr` (§2.3 của báo cáo chính) thành
7 lệnh ghi + 1 condition + 1 subcall, và tìm ra khác biệt **1 bit** giữa CMP và GeForce ở
register `0x0088610`.

### 3.2 Các spec khác

| spec | dùng để | giới hạn |
|---|---|---|
| `BIOS-Information-Table/` | token BIT, thứ tự pointer P v2 | không có schema field PERFORMANCE |
| `virtual-p-state-table/` | quy ước header, `0xFF = SKIP`, **"structure will change in Pascal and later"** | bảng Fermi–Maxwell; v3 **không** mượn nữa |
| `MemoryClockTable/` | ver 0x11, hlen 26, base 20, strap 26, `[13:0] = MHz` | base/strap là size gốc |
| `MemoryTweakTable/` | ver 0x20, hlen 6, base 76, ext 12; bitfield CONFIG0..CONFIG5 | base 76 vs ROM 74 |
| `DCB/DCB-4.x-Specification.html` | **Type = bits 3:0**; `0xE` EOL, `0xF` Skip | — |
| `turing/tu102/`, `volta/gv100/` | chỉ `kind_macros.h`, MMU/MSI | **không** có perf/power/clock-domain |

---

## 4. envytools

Repo: https://github.com/envytools/envytools · commit `f102b82381f3f11cee113d16374c87091db039d9`

| symbol | dùng để |
|---|---|
| `nvbios/bit.c:envy_bios_parse_bit()` (75-78) | `ver = u16(+6)`, `hlen=+8`, `rlen=+9`, `cnt=+10`, checksum |
| `nvbios/bit.c:bit_types[]` | `{'C',2}` Clock (**không có parser**), `{'P',2}`, `{'p',2}`, `{'U',1}` (**không parser**) |
| `nvbios/power.c:P2_tbls[]` | tên 40 slot P2 — **chỉ tên**, gồm `LOW POWER PCIe` = slot 30 |
| `nvbios/power.c:envy_bios_parse_power_base_clock()` case 0x20 | `+1 hlen, +2 rlen, +3 cnt, +4 secount, +5 selen`, `clock[j] = u16(entry+rlen+j*selen+2)*4` |
| `nvbios/bios.h:struct envy_bios_power_perf` | chỉ có `offset` ⇒ **envytools không parse PERFORMANCE** |
| `rnndb/bus/punits.xml` | `PUNITS @0x022400`, `DESIGN_GPC_COUNT`, `HW_TPC_DISABLE_MASK`… nhưng variant dừng ở **GM107** ⇒ không dùng được cho Turing |
| `rnndb/bus/pci.xml` | PCI config-space bitfield (device side), không phải PCIe domain |

**Giới hạn phải nêu:** không parser cho PERFORMANCE, CLEAR: không có mục nào cho
`0x409658`, `0x409660`, `0x0088610`, `0x0088B900`. POWER BUDGET có parser nhưng extent
không khớp TU106.

---

## 5. Nouveau / Linux DRM

`drivers/gpu/drm/nouveau/nvkm/subdev/bios/perf.c` (master @ 2026-11-07)

- `nvbios_perf_table()`: chỉ `ver >= 0x20 && < 0x40` và `ver == 0x40`. **Không có nhánh 0x60.**
- `nvbios_perfSp()` case 0x40: `(rd16 & 0x3fff) * 1000` — tiền lệ mask `0x3FFF`; v3 dùng
  mask chính thức từ `nvgpu bios.h`.
- `nvbios_perf_entry()`: `perf + hdr + idx*(len + snr*ssz)` — cùng công thức extent.

`include/nvkm/subdev/clk.h` + `nvkm/subdev/clk/{gk104,gf100,base}.c`:
- `struct nvkm_domain { enum nv_clk_src name; u8 bios; u8 flags; const char *mname;
  int mdiv; }` — `bios` = **sub-entry index trong bảng perf**.
- `gk104`: `gpc=0, hubk07=1, rop=2, mem=3, hubk06=4, hubk01=5, vdec=6, pmu=7`.
- `gf100`: `hubk06=0, hubk01=1, copy=2, gpc=3, rop=4, mem=5, …`
- **Dùng để:** (a) khái niệm "index domain trong bảng perf" là có thật trong nouveau;
  (b) **thứ tự thay đổi theo chip** ⇒ không suy được sang Turing; (c) enum
  `nv_clk_src_hubk06/hubk01/hubk07` chứng minh **"HUB" là tên clock domain có từ trước
  Turing**, không phải display hub — dùng cho §3.4 báo cáo chính.

Không có `nvkm/subdev/bios/pcie.c`: danh sách file của `subdev/bios/` (46 file) **không**
có mục PCIe ⇒ không có consumer nào cho `pcie_idx`.

---

## 6. NVIDIA open-gpu-kernel-modules

Repo: https://github.com/NVIDIA/open-gpu-kernel-modules · commit `e6a2e01` (620.70.06)

- `src/nvidia/src/kernel/gpu/vbios/kern_vbios.c` (1.279 dòng) — `grep -i perf` = **0 hit**.
- `.../arch/turing/kern_vbios_tu102.c` (1.127 dòng) — chỉ FWSEC/ROM directory:
  `NV_ROM_DIRECTORY_IDENTIFIER 0x44524652 ("RFRD")`, `FALCON_APPLICATION_INTERFACE_HEADER_V1`,
  `NV_BCRT_HASH_INFO_*`.
- `src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080clk.h` — chỉ
  `NV2080_CTRL_CLK_PMUMON_CLK_DOMAINS_SAMPLE {gpcClkFreqKHz, dramClkFreqKHz,
  nvdClkFreqKHz, activeGpcClkFreqKHz}` — **4 domain**, không phải 10.
- `ctrl2080perf.h`, `src/nvidia/inc/kernel/gpu/perf/*` — không có enum 10 domain.

**Kết luận:** schema VBIOS perf/power của Turing **không** nằm trong repo mở này.
Đây là lý do `pcie_idx` và `PCIEGEN` vẫn UNKNOWN: consumer thật nằm trong RM/GSP-RM
closed-source.

---

## 7. `Panchovix/nvidia-vbios-vix-editor` — nguồn của bảng 10 domain

https://github.com/Panchovix/nvidia-vbios-vix-editor
Đọc: `src/nvidia_vbios/rom/tables.py` (2.100 dòng), `docs/turing.md`, `NOTICE.md`

```python
TURING_CLOCK_ROWS = (('GPC',1,0x13), ('XBAR',2,0x24), ('DRAM',1,0x62),
                     ('SYS',2,0x35), ('HUB',2,0x71), ('VID',2,0x46),
                     ('PWR',0,0xFF), ('DISP',1,0x80), ('PCIEGEN',2,0x08),
                     ('HOST',2,0x57))
TURING_CLOCK_HEADER = bytes.fromhex('35 09 0b 0a 03 e8 03 00 00')
```
(gate mỗi row: `flags0 usage`, `byte+7 ordering`, `byte+8 == 0`, `ff ff`)

- `docs/turing.md`: "The tables are decoded by structure, checked on the **25 Turing
  images** examined (desktop, laptop, Max-Q, Quadro, TITAN, two XOC; TU102–TU117)."
- `NOTICE.md` chỉ nguồn `OE4T/linux-nvgpu` `include/nvgpu/bios.h` (MIT) → §1.
- `TURING_RAIL_HEADER = 10 05 0e 01 00` (khớp slot 8), `TURING_VFE_PREFIX = 30 09 19 14 18`
  (khớp slot 32).

**Dùng để:** tìm ra bảng v0x35 và thứ tự 10 domain. **Đã kiểm lại độc lập** trên 3 ROM:
10/10 row khớp ở cả ba.
**Cảnh báo:** repo này **không** decode P-STATE v0x60 thành từng field ⇒ không dùng làm
nguồn cho phần P-STATE.

---

## 8. Cộng đồng CMP 40HX

### 8.1 `Cyridd/cmpunlocker` — đúng `10de:1f0b`
https://github.com/Cyridd/cmpunlocker · `README.md`, `docs/how-it-works.md`

- "**Compute / SM configuration unlock** — changes the protected GSP/SEC2 initialization
  state": ghi `SS0 = 0x88888888`, `SS1 = 0x00000008`, `FECS_PLM = 0xFFFFFF8F` trong pha
  privileged của SEC2 Booter.
- "**There is no global FP32/FP16 lock.**" FP32 ≈ 8,3–9 TFLOPS trước **và** sau unlock.
  "Ordinary raster games already ran at normal performance before the compute patch."
- Tensor WMMA `1,1 → 72 TFLOPS`; INT8 `1 → 34 TOPS`.
- "**The CMP 40HX is restricted to PCIe Gen1 x16 (2.5 GT/s) by default.**"
  `NVreg_RegistryDwords="RmForceEnableGen2=1;RMPcieLinkSpeed=0x1"`; Gen3 "not implemented".
- ReBAR selector 7 → 8 GiB BAR1.
- Vulkan: `vkCmdBindPipeline` → `NVC597_CALL_MME_MACRO(52)` arg `0xf0` =
  `240 × (PIPE_NOP + WAIT_FOR_IDLE)`; emitter ở file offset `0xb20c2d`, `0xdcbf60`.
- "**None of these modifications flashes the VBIOS.**"

### 8.2 `cmp.wiki`
https://cmp.wiki/wiki/Risers_and_bifurcation · https://cmp.wiki/wiki/Gen2_link_retrain
- "An unmodified card links at **x4**. The card's lanes 4 to 15 have **no AC-coupling
  capacitors** fitted … the stock link is Gen1 x4 (about 0.85 GB/s)."
- Tách **speed** (phần mềm) khỏi **width** (cần mod tụ).
- "The silicon was never fused to Gen1; … There is no physical Gen2-disable fuse."

### 8.3 `Consensus-Protocol/cmp170hx` — `docs/hardware/vbios.md` (GA100, không phải TU106)
- "**The community unlock does not touch the VBIOS at all.**"
- Bản đồ vùng ROM NVIDIA: `NVGI` @0, vùng MAC-verified, FwSec tail không ký, mirror
  `+0x60000`, InfoROM cuối.

### 8.4 Thông số công bố (dùng kiểm chứng decode clock)
CMP 40HX 1470/1650 MHz, 8 GB GDDR6 14 Gbps, 185 W, TU106-100-A1.
RTX 2060 SUPER 1470/1650, 175 W. RTX 2070 1410/1620, 175 W.

---

## 9. Nguồn nội bộ dự án

| tài liệu | dùng để |
|---|---|
| `CMP40HX_INDEPENDENT_REVIEW/results/ROM4/ROM4_BYTE_COMPARE.md` | baseline diff 3 ROM |
| `work_v15/PHASE16/VBIOS_PERF/PERF_SCHEMA_REPORT.md` | mô hình "45 byte" — **bị bác bỏ** |
| `work_v15/VBIOS/P2_VBIOS.md` | cấu trúc ảnh/khe |
| `…/results/TPC5_LIVE/EXPLOIT_LIVE_20261106.md` | `0x021C38 = 0x20`; `0x021040` ghi được; `CTRL_OPT_TPC_GPC0` bounce |
| `…/05_PHASE21_EXTRACTS/VBIOS_DISPLAY_ANALYSIS.md` | `0x409660` chỉ **đọc** ở condition |
| `BAO_CAO_TONG_HOP_PHASE15_20.md` | SS0 `0x409664`, SS1 `0x40966C` |

---

## 10. ĐÃ TRA VÀ **KHÔNG** CÓ — đừng tra lại

| nơi tra | tìm gì | kết quả |
|---|---|---|
| `NVIDIA/nvgpu` mọi file `.c` | `pcie_idx` được dereference | **0 hit** — chỉ có trong 2 struct ở `bios.h` |
| `OE4T/linux-nvgpu` `common/vbios/*.c` | parser PERFORMANCE / POWER | không có; chỉ BIT + devinit + falcon |
| `open-gpu-kernel-modules` `gpu/vbios/` | perf/power parser | **0 hit** (grep -i perf) |
| `open-gpu-doc` index | spec perf/power/clock-domain cho Turing | chỉ BIT, DCB, Devinit, MemoryClockTable, MemoryTweakTable, vP-state, Falcon |
| `open-gpu-doc/Devinit` | tên register `0x0088610`, `0x0088B900` | spec chỉ có opcode, **không** có register map |
| `envytools/rnndb` | `0x0088610`, `0x021C38`, `0x1404` | không có |
| `envytools/rnndb/bus/punits.xml` | disable-mask register Turing | variant dừng ở **GM107** |
| nouveau `subdev/bios/` | file PCIe table | **không có** `pcie.c` |
| nouveau `perf.c` | nhánh v0x60 | **không có** |
| Sourcegraph (`sourcegraph.com/.api/search/stream`) | `vbios_clocks_table_35`, `PERF_CLK_DOMAINS_IDX_MAX`, `nvgpu_bios_lpwr_idx_table_1x_entry` | **0 hit** — OE4T/linux-nvgpu không được index; chỉ `vix-editor` có `vbios_clocks_table_35` |
| grep.app API | code search | chặn bởi Vercel checkpoint (HTTP 200 + HTML) |
| TechPowerUp VBIOS download | thêm ROM Turing để đối chiếu chéo | URL `…/vgabios/<id>/<id>.rom` trả **HTML** 118 KB, không phải ROM ⇒ cần tải tay qua trình duyệt |

---

## 11. MÂU THUẪN ĐÃ PHÁT HIỆN VÀ CÁCH XỬ LÝ

| # | mâu thuẫn | xử lý |
|---|---|---|
| 1 | Báo cáo cũ: perf "size = 45". Số học: 465. | `nvgpu bios.h` xác nhận 10 clock entry × 6 B ⇒ 465. Mô hình 45 bị loại. |
| 2 | `work_v15/scripts/vbios_parser.py` đọc BIT ở `0x287B2` → `hdr 17, stride 70, cnt 50`. | `bit.c:75-78` đọc từ base `0x287B0`: `ver u16(+6)=0x0100`, `hlen 12`, `rlen 6`, `cnt 17`; checksum xác nhận. |
| 3 | ROM4 report: "2060S 7 connector, 2070 4". | DCB `Type` là **nibble**: `0x7F/0x8F` = Skip. Đúng **5 / 5** (CMP 0). |
| 4 | v1: `PCIR+0x0A` là image length. | Đó là structure length. Image length ở `+0x10` ⇒ `0xF400`/`0xEC00`. |
| 5 | v2: export địa chỉ **bảng đích** làm `file_offset` của con trỏ. | nvgpu `bios.c:713` cho thấy con trỏ ở `data_ptr + 4*N`. Tách `file_offset` / `target_offset`. |
| 6 | v2: export `P["file"]` cho version của BIT `'P'`. | Version là byte `+1` của record tại `P["ent"]`. |
| 7 | envytools MemoryClockTable base 20/strap 26; TweakTable base 76. | Size gốc; TU106 dùng 60/33 và 74 — extent của ROM là chuẩn cho ROM. |
| 8 | envytools có parser POWER BUDGET / THERMAL POLICY. | Extent không khớp TU106 ⇒ không áp schema, giữ UNKNOWN. |
| 9 | "nouveau parse được perf v0x60". | `perf.c` master không có nhánh 0x60. |
| 10 | `FCT param0.id` (SYS/LTC/XBAR/GPC0…) dễ bị dùng làm domain index. | Là enum khác; định danh domain dùng `ordering idx` của v0x35 (10/10). |
| 11 | nvgpu dùng `>` cho ngưỡng ảnh; parser dùng `>=`. | Chỉ khác ở `raw == legacy_len`, không ROM nào chạm; ghi rõ trong code + báo cáo. |
| 12 | v2 gọi `PCIEGEN 1/3` là "STRONGLY SUPPORTED" mà không nêu đơn vị. | v3: giữ STRONGLY SUPPORTED cho **tương quan**, tách riêng "đơn vị = UNKNOWN". |

---

## 12. TÁI LẬP

```bash
mkdir -p src && cd src
git clone --depth 1 https://github.com/NVIDIA/open-gpu-doc.git ogdoc
git clone --depth 1 https://github.com/envytools/envytools.git
git clone --depth 1 https://github.com/Panchovix/nvidia-vbios-vix-editor.git vixed
git clone --depth 1 --filter=blob:none --sparse \
    https://github.com/NVIDIA/open-gpu-kernel-modules.git ogkm
cd ogkm && git sparse-checkout set src/nvidia/src/kernel/gpu/vbios \
    src/nvidia/inc/kernel/gpu/vbios src/common/sdk/nvidia/inc

# schema chính thức + consumer:
curl -O https://raw.githubusercontent.com/OE4T/linux-nvgpu/patches-rel-36/\
drivers/gpu/nvgpu/include/nvgpu/bios.h
curl -O https://raw.githubusercontent.com/OE4T/linux-nvgpu/patches-rel-36/\
drivers/gpu/nvgpu/common/vbios/bios.c
# nouveau:
curl -O https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/\
nouveau/nvkm/subdev/bios/perf.c
```

Commit/tag đã đọc: `ogdoc 9fdf5c4`, `envytools f102b82`, `ogkm e6a2e01`,
`nvgpu` @ `OE4T/linux-nvgpu:patches-rel-36` (`bios.h` 52.845 B, `bios.c` 23.042 B),
nouveau `master` @ 2026-11-07.

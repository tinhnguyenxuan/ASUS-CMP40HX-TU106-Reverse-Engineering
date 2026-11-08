# PHASE 4 — RESEARCH SOURCES

> **Publication edition (V5):** This is a curated ROM/source-analysis extract from the supplied `vbiosrel6(2).zip`. Host telemetry, game tests, benchmark steps and Windows/Linux collectors are intentionally omitted. It is historical research, **not** new hardware verification. See [integrated report](../../../docs/TU106_VBIOS_PHASE4_6.md).


Nguồn **mới** dùng trong Phase 4. Nguồn của Phase 1–3 giữ nguyên trong
`docs/INTERNET_RESEARCH_SOURCES.md` — không lặp lại ở đây.

Mỗi mục: URL, symbol, **dùng để làm gì**, và **giới hạn**.

---

## 1. NVIDIA nvgpu `bios.h` — phần mới dùng trong Phase 4

**URL:** https://raw.githubusercontent.com/OE4T/linux-nvgpu/patches-rel-36/drivers/gpu/nvgpu/include/nvgpu/bios.h
(`OE4T/linux-nvgpu`, nhánh `patches-rel-36`, file 52.845 B — đã đọc ở Phase 1–3)

Những struct Phase 4 mới khai thác:

### 1.1 POWER BUDGET — `pwr_policy_3x` (dòng 782–830)
```c
#define VBIOS_POWER_POLICY_VERSION_3X            0x30U
#define VBIOS_POWER_POLICY_3X_HEADER_SIZE_25     0x25U     /* 37 */
struct pwr_policy_3x_header_struct {
    u8 version, header_size, table_entry_size, num_table_entries;
    u16 base_sample_period, min_client_sample_period;
    u8 table_rel_entry_size, num_table_rel_entries;
    u8 tgp_policy_idx, rtp_policy_idx, mxm_policy_idx, dnotifier_policy_idx;
    u32 d2_limit, d3_limit, d4_limit, d5_limit;
    u8 low_sampling_mult, pwr_tgt_policy_idx, pwr_tgt_floor_policy_idx,
       sm_bus_policy_idx, table_viol_entry_size, num_table_viol_entries;
};
#define VBIOS_POWER_POLICY_3X_ENTRY_SIZE_2E      0x2EU     /* 46 */
struct pwr_policy_3x_entry_struct {
    u8 flags0, ch_idx;
    u32 limit_min, limit_rated, limit_max;
    u32 param0, param1, param2, param3, limit_batt;
    u8 flags1, past_length, next_length;
    u16 ratio_min, ratio_max;
    u8 sample_mult; u32 filter_param;
};
#define ..._FLAGS0_CLASS_MASK 0xFU
#define ..._FLAGS0_CLASS_HW_THRESHOLD 0x5U
#define ..._FLAGS0_LIMIT_UNIT_MASK 0x10U
```

**Dùng để:** giải mã slot 11. Điểm quyết định: header có `table_rel_entry_size`,
`num_table_rel_entries`, `table_viol_entry_size`, `num_table_viol_entries` ⇒ **bốn khối
con**, và `44 + 20*66 + 15*14 + 13*13 = 1743` đóng chính xác.

**Giới hạn:** TU106 header 44 B (không phải 37), entry 66 B (không phải 46). 7 + 20 byte
mở rộng **chưa đọc**. `class_id` ngoài giá trị 5 **chưa có tên**.

### 1.2 POWER TOPOLOGY — `pwr_topology_2x` (dòng 749–780)
```c
struct pwr_topology_2x_header { u8 version, header_size, table_entry_size,
        num_table_entries, rel_entry_size, num_rel_entries; };
struct pwr_topology_2x_entry { u8 flags0, pwr_rail; u32 param0,
        curr_corr_slope, curr_corr_offset, param1, param2; };
#define ..._FLAGS0_CLASS_SENSOR 0x1U
#define ..._PARAM1_SENSOR_INDEX_MASK 0xFFU
#define ..._PARAM1_SENSOR_PROVIDER_INDEX_MASK 0xFF00U
```
**Dùng để:** khớp **100%** với slot 15 (6 B header, 22 B entry), extent `6+20*22+15*27 = 851`.

**Giới hạn:** `CLASS_SENSOR = 1` **không xuất hiện** trong ROM ⇒ enum không phủ bảng TU106.
Khối `rel` (27 B × 15) không có schema.

### 1.3 LOW POWER GR — `nvgpu_bios_lpwr_gr_table_1x` (dòng 1187–1206)
```c
struct nvgpu_bios_lpwr_gr_table_1x_header { u8 version, header_size, entry_size,
        entry_count, default_entry_idx; u16 idle_threshold_us;
        u8 adaptive_gr_multiplier; };
struct nvgpu_bios_lpwr_gr_table_1x_entry { u32 feautre_mask; };
#define NV_VBIOS_LPWR_GR_FEATURE_MASK_GR_MASK   GENMASK(0,0)
#define NV_VBIOS_LPWR_GR_FEATURE_MASK_GR_RPPG_MASK GENMASK(4,4)
```
**Dùng để:** xác định entry là feature mask. TU106 rộng hơn (header 10 vs 7, entry 5 vs 4).

### 1.4 VFE 3x — `vbios_vfe_3x_header_struct` (dòng 341–365)
```c
struct vbios_vfe_3x_header_struct { u8 version, header_size,
        vfe_var_entry_size, vfe_var_entry_count,
        vfe_equ_entry_size, vfe_equ_entry_count, polling_periodms,
        vfe_var_rppm_entry_count, vfe_equ_rppm_entry_count; };
#define VBIOS_VFE_3X_HEADER_SIZE_09   0x09U
#define VBIOS_VFE_3X_VAR_ENTRY_SIZE_19 0x19U
struct vbios_vfe_3x_var_entry_struct { u8 type; u32 out_range_min,
        out_range_max, param0..param3; };
```
**Dùng để:** xác định slot 8 "VOLT MAPPING" **là** bảng VFE (`ver=0x30, hlen=9, esz=25`)
chứ không phải voltage-rail table như v3 giả định.

**Giới hạn:** `9 + 20*25 + 150*24 = 4109` ≠ span 5444 ⇒ **còn thiếu khối** (rppm / equ_rppm).
Chưa giải mã được. Không đoán.

### 1.5 `nvgpu_bios_lpwr_idx_table_1x_entry` (dòng 1152)
```c
struct nvgpu_bios_lpwr_idx_table_1x_entry {
        u8 pcie_idx, gr_idx, ms_idx, di_idx, gc6_idx; };
```
**Dùng để:** chứng minh `pcie_idx` **là** một khái niệm có thật (index vào bảng low-power
PCIe) — nhưng struct này thuộc **LPWR index table**, không phải P-state entry.

**Giới hạn:** slot 29 của ROM có `esz = 7`, không phải 5 ⇒ không khớp.

---

## 2. NVIDIA open-gpu-doc — `Devinit/devinit.xml`

**URL:** https://github.com/NVIDIA/open-gpu-doc/blob/master/Devinit/devinit.xml
(bản local: 340.814 B, đã đọc ở Phase 3 cho PCIe script; Phase 4 dùng lại)

Bảng opcode (`<opcode id= value= conditionflag=>`), tổng **~140 opcode**. Các opcode dùng:

| value | id | layout | conditionflag |
|---|---|---|---|
| `0x7A` | `INIT_ZM_REG` | addr(32) data(32) → 9 B | honors |
| `0x6E` | `INIT_NV_REG` | addr(32) mask(32) data(32) → 13 B | skipswrite |
| `0x75` | `INIT_CONDITION` | condition(8) → 2 B | failsets |
| `0x5B` | `INIT_SUB_DIRECT` | gọi chương trình con | honors |
| `0xFF` | `EOL` | — | ignores |

Văn bản gốc cho `INIT_NV_REG`:
> "This opcode first reads the specified privileged register. It then performs a logical AND
> on the read value using the AND mask, then a logical OR on the value using the OR mask."

**Dùng để:** giải mã PCIe settings script thành 7 lệnh ghi + 1 condition + 1 subcall; tìm ra
`0x0088610 = 0x1` (CMP) vs `0x1001` (GeForce).

**Giới hạn:** spec **không** có register map. Không trả lời được `0x88610` là gì.

---

## 3. Nouveau — dùng cho 4C và 4E

### 3.1 `nvkm/subdev/pci/gp100.c`
**URL:** https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/nouveau/nvkm/subdev/pci/gp100.c
(43 dòng)

```c
static const struct nvkm_pci_func
gp100_pci_func = {
        .cfg = { .addr = 0x088000, .size = 0x1000 },
        .msi_rearm = gp100_pci_msi_rearm,
};
```
`gp100_pci_msi_rearm()` chỉ ghi `0x0704`. **Không có** code link-speed.

**Dùng để:** (a) xác định block PCI của Turing ở MMIO `0x088000` size `0x1000`;
(b) `0x88610 = PPCI + 0x610`; (c) chứng minh nouveau **không** can thiệp link speed ⇒
không phải consumer.

### 3.2 `nvkm/engine/device/base.c` — `nv166_chipset` (dòng ~2408)
**URL:** https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/nouveau/nvkm/engine/device/base.c

```c
static const struct nvkm_device_chip nv166_chipset = {
        .name = "TU106",
        .acr  = { 0x00000001, tu102_acr_new },
        .gr   = { 0x00000001, tu102_gr_new },
        .sec2 = { 0x00000001, tu102_sec2_new },
        .ce   = { 0x0000001f, tu102_ce_new },   /* 5 copy engines */
        ...
};
```
**Dùng để:** chứng minh nouveau **không** phân nhánh theo device id (1F06/1F07/1F0B dùng
chung một chipset entry). `.ce = 0x1f` ⇒ **5 copy engine** (dùng cho 4A/4G).

### 3.3 `nvkm/subdev/clk/*` — `nv_clk_src_hubk06/hubk01/hubk07`
**Dùng để:** "HUB" là tên clock domain **có từ trước Turing**, không phải display hub.
(Đã dùng ở v3; Phase 4 dùng lại cho 4D.)

---

## 4. Microsoft Learn — dùng cho 4A

### 4.1 CASO
**URL:** https://learn.microsoft.com/en-us/windows-hardware/drivers/display/supporting-caso

Trích dẫn trực tiếp:
> "This article describes how a WDDM driver can support cross-adapter resource scan-out
> (CASO), reducing the number of copies between GPUs and cross-adapter resources **from two
> to one**. This feature is available starting in **Windows Server 2022 and Windows 11**."

> "Starting in Windows 8.1 (WDDM 1.3) … the rendering is done on a render adapter … and then
> **two copies** are done … Copy 1 is from the render adapter resource to a cross-adapter
> resource. Copy 2 is from the cross-adapter resource to the display adapter resource."

> "If the display adapter supports CASO, the system only does the **first copy** … and then
> **scans out from the cross-adapter surface directly**."

Ba tier qua `DXGK_VIDMMCAPS`:

| tier | bit | ý nghĩa |
|---|---|---|
| 1 | `CrossAdapterResource` | copy to/from |
| 2 | `CrossAdapterResourceTexture` | SRV/UAV/RTV |
| 3 | `CrossAdapterResourceScanout` | scan-out (CASO) |

> "Each higher tier of support must guarantee the support of the tier(s) below it."

### 4.2 Hybrid DDI / dList
**URL:** https://learn.microsoft.com/en-us/windows-hardware/drivers/display/hybrid-system-ddi

> "A *dList* is a list of applications that need cross-adapter shared surfaces for
> high-performance rendering on the discrete GPU. […] **The operating system itself doesn't
> determine which GPU an application should run on.** Instead, the Direct3D runtime calls
> **pfnQueryDListForApplication2** at most once during Direct3D initialization."

Đăng ký qua INF: `UserModeDListDriverName`, `UserModeDListDriverNameWow`.

**Dùng để:** (a) đường đi chính xác 1 vs 2 copy; (b) ai quyết định game chạy GPU nào;
(c) điều kiện để chỉ có 1 copy.

**Giới hạn:** không nói gì về CMP; không có API công khai để hỏi "adapter này tier mấy"
(tra qua `dxdiag`/registry hoặc suy từ hành vi).

---

## 5. Nguồn cộng đồng — 4F

### 5.1 `Cyridd/cmpunlocker`
**URL:** https://github.com/Cyridd/cmpunlocker (`README.md`, `docs/how-it-works.md`)

Các claim được trích:
- "**The CMP 40HX is restricted to PCIe Gen1 x16 (2.5 GT/s) by default.**"
  `NVreg_RegistryDwords="RmForceEnableGen2=1;RMPcieLinkSpeed=0x1"`
- Vulkan: `vkCmdBindPipeline` → `NVC597_CALL_MME_MACRO(52)` arg `0xf0` = 240 ×
  (`PIPE_NOP` + `WAIT_FOR_IDLE`); emitter offset `0xb20c2d`, `0xdcbf60`
- "**There is no global FP32/FP16 lock.**" FP32 8,3–9 TFLOPS trước **và** sau
- Tensor WMMA 1,1 → 72 TFLOPS; INT8 1 → 34 TOPS
- `SS0 = 0x88888888`, `SS1 = 0x00000008`, `FECS_PLM = 0xFFFFFF8F`
- "**None of these modifications flashes the VBIOS.**"

**Giới hạn (quan trọng):** không nêu **driver version**, không nêu **hash module**, không
nêu **tên game** được thử, không có **disassembly công khai** của macro 52. Vì vậy mức tối
đa là **STRONGLY SUPPORTED** cho báo cáo, **HYPOTHESIS** cho cơ chế.

### 5.2 `cmp.wiki`
**URL:** https://cmp.wiki/wiki/Risers_and_bifurcation · https://cmp.wiki/wiki/Gen2_link_retrain
- "lanes 4 to 15 have **no AC-coupling capacitors** fitted" ⇒ x4 là **phần cứng**
- "The silicon was never fused to Gen1; … no physical Gen2-disable fuse" ⇒ Gen1 là **policy**

**Dùng để:** tách **width** (phần cứng) khỏi **speed** (phần mềm).

---

## 6. Nguồn đã tra và KHÔNG có — Phase 4

| tra ở | tìm | kết quả |
|---|---|---|
| `rnndb/bus/pci.xml` | tên thanh ghi `PPCI+0x610` | chỉ đặt tên config-space `0x00..0x3F` |
| `rnndb/bus/punits.xml` | disable-mask Turing | variant dừng ở **GM107** |
| `rnndb/` toàn bộ | `0x88610`, `0x8b900`, `0x1404` | không có |
| `ogdoc/Devinit` | register map | chỉ opcode |
| `nvgpu` mọi `.c` | `pcie_idx` dereference | **0 hit** |
| `ogkm` `gpu/vbios/` | perf/power parser | **0 hit** |
| `ogkm` `gpu/gpu.c` | `0x1F0B` | **0 hit** (chỉ `HAL_IMPL_TU106`) |
| nouveau `subdev/bios/` | `pcie.c` | không tồn tại |
| nouveau `pci/gp100.c` | link speed | không có |
| Sourcegraph | `vbios_pstate_entry_6x` | 0 hit (repo không được index) |
| grep.app | code search | Vercel checkpoint |
| TechPowerUp VBIOS DB | ROM mới | **HTTP 200 nhưng 0 link ROM** — trang cần JS |
| Microsoft Learn | URL `cross-adapter-scanout`, `gpu-scheduler` | **404** (đúng URL là `supporting-caso`) |
| `DirectX-Specs/d3d/CrossAdapterResource.md` | spec cross-adapter | **404** — không tồn tại ở path đó |

---

## 7. Tái lập

```bash
cd src
# nvgpu (schema power/topology/lpwr/vfe)
curl -O https://raw.githubusercontent.com/OE4T/linux-nvgpu/patches-rel-36/\
drivers/gpu/nvgpu/include/nvgpu/bios.h
# devinit opcode table
curl -O https://raw.githubusercontent.com/NVIDIA/open-gpu-doc/master/Devinit/devinit.xml
# nouveau: block PCI + chipset + copy engines
curl -O https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/\
nouveau/nvkm/subdev/pci/gp100.c
curl -O https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/\
nouveau/nvkm/engine/device/base.c
```

Commit/tag đã đọc Phase 4: `nvgpu @ OE4T/linux-nvgpu:patches-rel-36`,
`open-gpu-doc master` (devinit.xml 340.814 B), `linux master` @ 2026-11-07.
Microsoft Learn truy cập 2026-11-07 (`supporting-caso`, `hybrid-system-ddi`).

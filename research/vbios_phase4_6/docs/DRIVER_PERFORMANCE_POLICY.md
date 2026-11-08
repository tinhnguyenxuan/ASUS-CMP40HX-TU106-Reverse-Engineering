# DRIVER PERFORMANCE POLICY — Phase 5D

> **Publication edition (V5):** This is a curated ROM/source-analysis extract from the supplied `vbiosrel6(2).zip`. Host telemetry, game tests, benchmark steps and Windows/Linux collectors are intentionally omitted. It is historical research, **not** new hardware verification. See [integrated report](../../../docs/TU106_VBIOS_PHASE4_6.md).


**Câu hỏi:** có code nào trong driver/firmware tiêu thụ `pcie_idx`, Performance v0x60,
Power Budget, Low Power GR, các trường thermal — và có nhánh riêng cho Device ID
`10DE:1F0B` không?

**Môi trường:** không có binary driver, không có GSP-RM, không có máy Windows. Đây là
**bản đồ nơi cần tìm**, kèm những gì đã loại trừ được bằng nguồn mở.

---

## 0. KẾT QUẢ

| # | Nội dung | Mức |
|---|---|---|
| 1 | Nouveau: **không** phân nhánh theo device id; một `nv166_chipset` cho 1F06/1F07/1F0B | PROVEN |
| 2 | nvgpu: chỉ Tegra, không có đường dGPU TU106 | PROVEN |
| 3 | open-gpu-kernel-modules: phân nhánh theo **chip** (`HAL_IMPL_TU106`), không theo device id | PROVEN |
| 4 | Không nguồn mở nào **dereference** `pcie_idx` | PROVEN (absence) |
| 5 | Không nguồn mở nào parse Performance v0x60, Power Budget, Low Power GR | PROVEN (absence) |
| 6 | Nouveau **không** có code link-speed cho Turing (`gp100_pci.c` chỉ MSI rearm) | PROVEN |
| 7 | Nơi **duy nhất** còn có thể chứa policy riêng: GSP-RM binary + RM closed + userspace driver | UNKNOWN |
| 8 | `0x88610` = `PPCI + 0x610` (block PCIe), **không có tên** trong mọi register map công khai | STRONGLY SUPPORTED / UNKNOWN |

---

## 1. BA NGUỒN MỞ — TRA CÓ HỆ THỐNG

### 1.1 Nouveau (Linux, open)

`drivers/gpu/drm/nouveau/nvkm/engine/device/base.c`:

```c
static const struct nvkm_device_chip
nv166_chipset = {
        .name = "TU106",
        .acr  = { 0x00000001, tu102_acr_new },
        .bios = { 0x00000001, nvkm_bios_new },
        .pci  = { 0x00000001, gp100_pci_new },
        .gr   = { 0x00000001, tu102_gr_new },
        .sec2 = { 0x00000001, tu102_sec2_new },
        .ce   = { 0x0000001f, tu102_ce_new },     /* 5 copy engines */
        ...
};
```

Một entry cho cả ba device id. Không `switch (device->device_id)`. Grep `1F0B` trong toàn
bộ `nvkm/` = 0 hit.

`nvkm/subdev/pci/gp100.c` (43 dòng, dùng cho TU106):

```c
static void gp100_pci_msi_rearm(struct nvkm_pci *pci)
{
        nvkm_pci_wr32(pci, 0x0704, 0x00000000);
}
static const struct nvkm_pci_func gp100_pci_func = {
        .cfg = { .addr = 0x088000, .size = 0x1000 },
        .msi_rearm = gp100_pci_msi_rearm,
};
```

**Không có** code đọc/ghi link speed, không có `LnkCap`, không có `gen2`. ⇒ Nouveau không
thể là nơi áp policy PCIe cho CMP.

`nvkm/subdev/bios/perf.c`: chỉ `ver 0x20–0x40` và `0x40`. Không có **v0x60**.
`nvkm/subdev/bios/` không có `pcie.c`, không có `lpwr.c`, không có `pwrpolicy.c`.

### 1.2 nvgpu (NVIDIA, mở, nhưng cho Tegra)

Có **schema** (`bios.h`) nhưng **không có consumer**:
- `pcie_idx` xuất hiện 2 lần trong `bios.h` (struct 6x và 4x), **0 lần** trong `.c`.
- `vbios_pstate_*`, `pwr_policy_3x_*`, `pwr_topology_2x_*`, `nvgpu_bios_lpwr_gr_*`:
  **không** có hàm parse nào trong `common/vbios/`.
- `common/vbios/bios.c` chỉ parse BIT, NVINIT, falcon ucode, và **P2 pointer table**
  (`nvgpu_bios_get_perf_table_ptrs`) — tức nó *biết chỗ* các bảng nhưng **không đọc nội dung**.

⇒ nvgpu là **từ điển**, không phải consumer. Đây là lý do các bảng decode được mà không
chứng minh được tác động.

### 1.3 open-gpu-kernel-modules (NVIDIA, mở, cho Linux dGPU)

`src/nvidia/src/kernel/gpu/gpu.c:4743`:
```c
case HAL_IMPL_TU106:
        *gpuImpl = GPU_IMPLEMENTATION_TU106;
```
`HAL_IMPL_TU106` = **chip**, không phải device id. Grep `1F0B` trong
`src/nvidia/src/kernel/gpu/` = **0 hit**.

`src/nvidia/src/kernel/gpu/vbios/kern_vbios.c` (1279 dòng): `grep -i perf` = **0 hit**.
`arch/turing/kern_vbios_tu102.c` (1127 dòng): chỉ FWSEC/ROM directory
(`NV_ROM_DIRECTORY_IDENTIFIER 0x44524652 "RFRD"`, `FALCON_APPLICATION_INTERFACE_HEADER_V1`).

`ctrl2080clk.h` chỉ có 4 domain (`gpcClkFreqKHz, dramClkFreqKHz, nvdClkFreqKHz,
activeGpcClkFreqKHz`), không phải 10.

⇒ Repo mở **không** chứa đường đọc VBIOS perf/power. Phần đó ở RM binary và GSP-RM.

---

## 2. NƠI POLICY THẬT SẼ NẰM

| tầng | file/thành phần | mở? | có thể chứa policy cho 1F0B? |
|---|---|---|---|
| UEFI/Devinit | VBIOS script | có (trong ROM) | **có** — nhưng chỉ qua condition table |
| PMU firmware | `pmu_*.bin` trong ROM/GSP package | không | có |
| **GSP-RM** | `gsp_rm.bin` / `gsp_tu10x.bin` | **không** | **cao nhất** |
| RM kernel (Linux) | `nv-kernel-module` binary | không | cao |
| RM userspace (Windows) | `nvapi64.dll`, `nvwgf2umx.dll` | không | cao |
| Nouveau | `nvkm/*` | có | **không** (đã kiểm) |
| nvgpu | `common/*` | có | **không** (Tegra) |

### 2.1 Cách tìm trong GSP-RM (khi có binary)

```bash
# 1. lấy binary từ firmware package
ls /lib/firmware/nvidia/*/gsp_*.bin
# 2. tìm chuỗi device id (little-endian PCI id trong code thường là immediate)
strings -a gsp_tu10x.bin | grep -i "1f0b\|1F0B"
# 3. tìm offset của pstate entry: pattern 5-byte base entry rồi 6-byte clock
#    struct vbios_pstate_entry_6x { u8 ps, u8 flags, u8 lpwr, u8 pcie, u8 nvlink }
#    -> tìm chỗ đọc byte +3 (pcie_idx) gần một bảng switch
objdump -D -b binary -m i386 gsp_tu10x.bin | grep -n "0x3(%e..)" | head
```

Đây là **phân tích tĩnh**, hợp pháp cho nghiên cứu tương thích ở nhiều nơi, nhưng **không**
làm trong repo này vì không có binary. Không patch, không chạy.

### 2.2 Dấu hiệu cần tìm

Nếu GSP-RM có nhánh riêng cho CMP, dấu hiệu sẽ là:
- một bảng so sánh device id (`0x1F0B`, `0x1F06`, `0x1F07`) **trước** khi nạp pstate;
- hoặc một cờ "no display present" (đọc từ PCI class `0x030200` hoặc từ DCB rỗng);
- hoặc một biến "product segment" (CMP/GeForce/Quadro) đọc từ InfoROM.

**Giả thuyết đáng theo:** một card CMP **không có display engine** ⇒ GSP-RM phải xử lý khác
ở phần display, và có thể **tắt luôn** một số feature đi kèm display (ví dụ một phần
graphics scheduling hoặc present path). Đây là HYPOTHESIS, không phải kết luận.

---

## 3. `0x88610` VÀ CONDITION 82/86

### 3.1 Vị trí

`0x0088610 - 0x088000 = 0x610` trong block `PPCI` (nouveau `gp100_pci_func.cfg`,
`.addr = 0x088000, .size = 0x1000`).

`envytools/rnndb/bus/pci.xml` đặt tên block nhưng chỉ đặt tên **config space `0x00..0x3F`**
qua group `nv_pci`. `+0x610` nằm ngoài, **không có tên**.

Không khẳng định là công tắc Gen1/Gen3. Xem `docs/TU106_PCIE_REGISTER_DEEP_REVERSE.md` §2.

### 3.2 Condition 82 / 86

`INIT_CONDITION` (opcode `0x75`) mang **id** của một điều kiện; nội dung điều kiện nằm trong
`condition_table_ptr` (`nvinit_ptrs + 0x06`). Chưa parse bảng đó.

**Đã thử parse condition table trong Phase 5 — KHÔNG được.** Ghi lại đầy đủ để lần sau
không làm lại:

| bước | kết quả |
|---|---|
| `nvinit_ptrs.condition_table_ptr` (`+0x06`) | CMP raw `0x469c` → file `0x2cc9c`; 2060S `0x466e` → `0x2cc6e` |
| byte đầu | `30 c0 61 40 00 00 00 10 …` |
| đọc như `{ver, hlen, cnt}` | `ver=0x30`, `hlen=0xc0=192`, `cnt=0x61=97` — **không kiểm chứng được** |
| thử `cnt` offset u16 | **thất bại**: u16 đầu tiên là `0xc030` = chính 2 byte header, không phải offset. Không monotonic, max `0xe8d0` vượt bảng |
| thử entry 12 B | phần thân có pattern `08 23 61 00 | 80 00 00 00 | 80 00 00 00` lặp lại — **hợp lý** nhưng không có schema để xác nhận |
| so 1 KB giữa CMP và 2060S | **370 byte khác nhau** ⇒ bảng này **có** khác biệt SKU (khác với POWER TOPOLOGY) |

Kết luận: **cấu trúc UNKNOWN**. Có ít nhất một dạng entry 12 byte và bảng **khác nhau** giữa
CMP và GeForce, nhưng không đủ để nói điều kiện 82/86 làm gì.

**Điều đáng chú ý:** đây là bảng **duy nhất** tới giờ tìm được mà (a) có khác biệt CMP↔GeForce
và (b) có khả năng là **logic điều kiện** (không chỉ là tham số). Nếu một ngày có schema, nó
là ứng viên số một cho "policy riêng của CMP".

Cần: schema condition table (không có trong `devinit.xml` — spec chỉ mô tả opcode
`INIT_CONDITION`, không mô tả bảng), hoặc disassembly RM.

---

## 4. NHỮNG GÌ KHÔNG ĐƯỢC KẾT LUẬN

| câu | vì sao |
|---|---|
| "CMP bị giới hạn trong firmware" | chưa có GSP-RM, chưa có bằng chứng |
| "CMP không bị giới hạn" | vắng bằng chứng ≠ bằng chứng vắng |
| "`0x88610` là công tắc Gen1" | không có register name |
| "Condition 86 là policy CMP" | chỉ biết id khác nhau |
| "Nouveau chạy được CMP nên firmware không giới hạn" | Nouveau không dùng GSP-RM theo cùng đường; nó tự nạp GR ucode |

---

## 5. KẾT LUẬN

1. **Ba nguồn mở đều không có** nhánh theo `1F0B` và **không có consumer** cho bất kỳ bảng
   nào trong số: Performance v0x60, Power Budget, Low Power GR, thermal.
2. Đó là lý do Phase 3–5 decode được **cấu trúc** nhưng không chứng minh được **tác động**.
3. Policy thật (nếu có) nằm ở **GSP-RM** và **RM closed** — cả hai không có trong repo.
4. **Condition table đã thử và thất bại**: có khác biệt CMP↔GeForce (370/1024 byte) nhưng
   không có schema ⇒ UNKNOWN. Đây vẫn là ứng viên số một cho "policy riêng CMP" **nếu** tìm
   được schema.
5. Hai việc đắt hơn: disassembly GSP-RM (cần binary), và đo runtime (cần card).

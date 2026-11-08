# TU106 PCIe REGISTER DEEP REVERSE — Phase 4C

> **Publication edition (V5):** This is a curated ROM/source-analysis extract from the supplied `vbiosrel6(2).zip`. Host telemetry, game tests, benchmark steps and Windows/Linux collectors are intentionally omitted. It is historical research, **not** new hardware verification. See [integrated report](../../../docs/TU106_VBIOS_PHASE4_6.md).


**Bản:** Phase 4, sau v3. Kế thừa `docs/VBIOS_FIELD_REVERSE_ENGINEERING.md` §2, không lặp lại.
**Môi trường:** không có GPU NVIDIA trong phiên này. Mọi phát biểu về *link thật* là
**chưa đo**. Chỉ dữ liệu ROM + nguồn công khai.

---

## 0. KẾT LUẬN NGẮN

| # | Nội dung | Mức |
|---|---|---|
| 1 | `0x0088610` nằm trong block **PPCI** (`0x088000`, size `0x1000`) theo nouveau `gp100_pci_func` ⇒ offset trong block = **+0x610** | STRONGLY SUPPORTED |
| 2 | Không có register map công khai nào đặt tên `PPCI+0x610` ⇒ **không** được gọi là công tắc Gen1/Gen3 | UNKNOWN |
| 3 | Ghi `0x1` (CMP) vs `0x1001` (GeForce) là **sự kiện đọc được**, khác 1 bit | PROVEN |
| 4 | Condition id 86 (CMP) vs 82 (GeForce) — cùng script, khác nhánh fuse/strap | PROVEN (giá trị), UNKNOWN (nghĩa) |
| 5 | `pcie_idx` **không** được dereference ở bất kỳ nguồn mở nào | UNKNOWN |
| 6 | Ứng viên đích của `pcie_idx`: slot 30 chỉ là **khớp số lượng** (5 entry ≥ index 2), không phải bằng chứng | HYPOTHESIS |
| 7 | Byte 8 của 5 entry slot 30: `0xFB` (CMP) vs `0xF8` (GeForce) — bật bit 0,1 | PROVEN (giá trị) |
| 8 | PCIe **speed** và **width** là hai vấn đề khác nhau; width x4 nếu có là do thiếu tụ AC, ROM không sửa được | STRONGLY SUPPORTED (cộng đồng) |

> **Cảnh báo bắt buộc:** báo cáo này **không** khẳng định card đang chạy Gen1 x4. Dữ liệu
> live của chính card phải thắng tài liệu cộng đồng. Xem §5.

---

## 1. BA THANH GHI VÀ BA CÁCH ĐỌC SAI

PCIe settings script (NVINIT, `nvinit_ptrs+0x12`) của CMP gồm 7 lệnh ghi vô điều kiện,
rồi `INIT_CONDITION`, rồi `INIT_SUB_DIRECT`. Giải mã theo `ogdoc/Devinit/devinit.xml`:

| # | opcode | addr | CMP | GeForce |
|---|---|---|---|---|
| 1 | ZM_REG `0x7A` | `0x00137C00` | `0x180` | `0x180` |
| 2 | NV_REG `0x6E` | `0x0008B900` | `& 0xFFFFFFFF \| 0` | giống |
| 3 | NV_REG `0x6E` | `0x0008C100` | `& 0xFFFFFFFF \| 0` | giống |
| 4 | ZM_REG `0x7A` | **`0x00088610`** | **`0x00000001`** | **`0x00001001`** |
| 5 | NV_REG `0x6E` | `0x0008A088` | `& 0xFFFFFFFC \| 3` | giống |
| 6 | ZM_REG `0x7A` | `0x0008B400` | `0x58E` | giống |
| 7 | NV_REG `0x6E` | `0x00001404` | `& 0xFFFFFBFF \| 0` | giống |
| 8 | CONDITION `0x75` | — | **86** | **82** |
| 9 | SUB_DIRECT `0x5B` | — | dừng | dừng |

Ba cách đọc sai cần tránh:

1. **"`0x88610 = 0x1` nghĩa là Gen1"** — không có định nghĩa nào cho bit 12 của thanh ghi
   này. Bit 12 là chỗ *khác nhau*, không phải chỗ *được đặt tên*.
2. **"Condition 86/82 là policy CMP"** — đây là **id** của một điều kiện trong condition
   table; nội dung điều kiện đó chưa đọc. Id khác nhau chứng minh *nhánh khác nhau*, không
   chứng minh *nhánh đó làm gì*.
3. **"Script này cấu hình link speed"** — script chạy ở devinit, có thể chỉ set PCIe
   capability/ASPM/L1. Chưa có consumer.

---

## 2. `0x0088610` NẰM Ở ĐÂU — CÓ NGUỒN

Nouveau, `nvkm/subdev/pci/gp100.c` (dùng cho TU106: `nv166_chipset .pci = gp100_pci_new`):

```c
static const struct nvkm_pci_func
gp100_pci_func = {
        .cfg = { .addr = 0x088000, .size = 0x1000 },
        .msi_rearm = gp100_pci_msi_rearm,       /* wr32(pci, 0x0704, 0) */
};
```

⇒ Với Turing, block PCI của GPU được ánh xạ tại MMIO **`0x088000`, dài `0x1000`**.
`0x0088610 - 0x088000 = 0x610`.

`envytools/rnndb/bus/pci.xml` đặt tên các block:

```xml
<array offset="0x88000" name="PPCI"     stride="0x1000" length="1" variants="NV40-">
<array offset="0x8a000" name="PPCI_HDA" stride="0x1000" length="1" variants="GT215-">
<array offset="0x8c000" name="PPCI_2"   stride="0x1000" length="1" variants="GK104-">
```

Ánh xạ 7 thanh ghi vào block:

| addr | block rnndb | offset trong block | ghi chú |
|---|---|---|---|
| `0x00137C00` | — | — | ngoài mọi block PCIe đã biết |
| `0x0008B900` | (0x8b000) | +0x900 | block không có tên trong rnndb |
| `0x0008C100` | **PPCI_2** | +0x100 | GK104+ |
| **`0x00088610`** | **PPCI** | **+0x610** | trong cửa sổ config-space |
| `0x0008A088` | **PPCI_HDA** | +0x088 | GT215+ |
| `0x0008B400` | (0x8b000) | +0x400 | block không tên |
| `0x00001404` | — | — | block khác (không phải PCIe) |

**Điểm quan trọng:** `PPCI` là cửa sổ MMIO vào **PCI configuration space** của chính GPU.
`+0x610` nằm ngoài 256 byte config chuẩn, tức vùng **extended configuration space**.
Theo bố cục PCIe, `0x610` là capability mở rộng — nhưng Turing là PCIe 3.0, và các
capability ở `0x610` (Physical Layer 16.0 GT/s) chỉ tồn tại trên thiết bị Gen4+.

⇒ **HYPOTHESIS**: `0x88610` là một thanh ghi nội bộ trong cửa sổ PPCI, không phải
config-space thuần. Chưa phân biệt được vì rnndb chỉ đặt tên phần `0x00..0x3F`.

**Phép thử phân biệt (read-only):**
```bash
# nếu 0x88610 là config-space mirror thì đọc nó phải bằng read của config 0x610
sudo setpci -s 03:00.0 610.l        # config-space, không ghi
sudo nvapeek 0x88610                 # nếu có tool; hoặc devmem qua BAR0
```
Hai giá trị bằng nhau ⇒ là mirror. Khác nhau ⇒ thanh ghi nội bộ.

---

## 3. `pcie_idx` — TRUY HẾT BA NGUỒN, KHÔNG CÓ CONSUMER

| nguồn | tìm gì | kết quả |
|---|---|---|
| `nvgpu` `include/nvgpu/bios.h` | khai báo | có: `u8 pcie_idx` trong `vbios_pstate_entry_6x` (dòng 612) và struct 4x (1153) |
| `nvgpu` `**/*.c` | dereference | **0 hit** |
| `open-gpu-kernel-modules` `src/nvidia/src/kernel/gpu/vbios/` | perf/power parser | **0 hit** (`grep -i perf`) |
| nouveau `nvkm/subdev/bios/` (46 file) | file PCIe | **không có** `pcie.c` |
| nouveau `perf.c` | nhánh v0x60 | **không có** (chỉ 0x20–0x40) |
| Sourcegraph (public index) | `vbios_pstate_entry_6x`, `PERF_CLK_DOMAINS_IDX_MAX` | **0 hit** — repo nvgpu không được index |
| `envytools/nvbios/power.c` | `P2_tbls[]` | chỉ có **tên** slot, không có parser PCIe |

**Kết luận:** consumer thật nằm trong RM/GSP-RM (closed source). `pcie_idx` = **UNKNOWN**.

### 3.1 Ứng viên slot 30 — và vì sao đó chỉ là giả thuyết

Slot 30 "LOW POWER PCIe" khớp cấu trúc `{ver=0x10, hlen=5, esz=12, cnt=5}` với extent
đóng chính xác lên slot 31 ở cả 3 ROM. `pcie_idx` ∈ {0,1,2} ⇒ **vừa** 5 entry.

Đó là **khớp số lượng**, không phải bằng chứng. Ba lý do để nghi ngờ:
1. Không có consumer đọc slot 30 trong bất kỳ nguồn mở nào.
2. `lpwr_entry_idx` (0,1,2,4) cũng là index, và nvgpu nói nó trỏ vào **LPWR index table**
   5-byte — slot 29 có `esz=7`, không khớp. Nên ít nhất một trong hai ánh xạ sai.
3. Tên slot 30 là "LOW POWER PCIe", tức bảng **low-power**, không phải bảng **cấu hình
   link**. Nếu P-state muốn chọn cấu hình PCIe thì bảng low-power là chỗ lạ.

⇒ **HYPOTHESIS**, cần disassembly RM để đóng.

---

## 4. PHÂN BIỆT GENERATION / WIDTH / ASPM / TRAINING / RT-PM

Năm thứ này thường bị gộp thành "PCIe bị giới hạn". Chúng khác nhau về nơi cấu hình và
cách đo:

| khái niệm | cấu hình ở đâu | ROM có trường? | đo bằng |
|---|---|---|---|
| **Generation** (2.5/5/8 GT/s) | Link Control 2 / driver policy | `PCIEGEN` domain = 1/3 (UNKNOWN unit) | `LnkSta` speed |
| **Width** (x1..x16) | phần cứng + Link Control | **không** | `LnkSta` width |
| **ASPM / L1** | Link Control, Devinit script | có thể (script có L1 regs) | `LnkCtl` bits, `lspci -vv` |
| **Link training** | khởi tạo, sau đó cố định | không | không đo được sau boot |
| **Runtime PM** (D3, ASPM L1.2) | driver | không | `runtime_status`, GPUView gaps |

**Điểm không được bỏ qua:** CMP là card **x4** nếu PCB thiếu tụ AC lane 4–15 — đó là
**width**, không phải generation, và **ROM không sửa được**. Ngược lại Gen1→Gen2 là
**generation**, sửa được bằng phần mềm (cộng đồng: `RmForceEnableGen2=1`).

Vì vậy khi đo phải đọc **cả hai** con số, không chỉ một.

---

# block base kiểm chứng:
sudo setpci -s $BDF CAP_EXP+0x0c.l    # Link Capabilities
sudo setpci -s $BDF CAP_EXP+0x10.l    # Link Status (speed+width ở đây)
```
Script đầy đủ: `scripts/phase4/collect_linux.sh` (chỉ đọc; không có `-pl`, không có
`setpci ... w`).

### 5.2 Windows 11 (read-only)
```powershell
Get-PnpDevice -Class Display | Select FriendlyName, InstanceId, Status
Get-PnpDeviceProperty -InstanceId <id> -KeyName DEVPKEY_PciDevice_CurrentLinkSpeed
Get-PnpDeviceProperty -InstanceId <id> -KeyName DEVPKEY_PciDevice_CurrentLinkWidth
dxdiag /t dx.txt
```
Script: `scripts/phase4/collect_windows.ps1`.

### 5.3 Bảng ghi kết quả (điền sau khi chạy)

| | CMP 40HX | 2060S | 2070 |
|---|---|---|---|
| `LnkCap` max speed | | | |
| `LnkCap` max width | | | |
| `LnkSta` current speed | | | |
| `LnkSta` current width | | | |
| `PCIEGEN` (ROM) | 1 | 3 | 3 |
| khớp? | | | |

Nếu `LnkSta` = **8 GT/s** trên CMP ⇒ `PCIEGEN = 1` **không** phải link speed, và toàn bộ
giả thuyết "ROM giới hạn Gen1" sai. Đó là kết quả hoàn toàn có thể và phải chấp nhận.

---

## 6. NHỮNG GÌ ĐÃ TRA VÀ KHÔNG CÓ

| tra ở | tìm | kết quả |
|---|---|---|
| `envytools/rnndb/bus/pci.xml` | tên thanh ghi `PPCI+0x610` | chỉ đặt tên config-space `0x00..0x3F` qua `nv_pci` group |
| `rnndb/bus/punits.xml` | `HW_TPC_DISABLE_MASK` Turing | variant dừng ở **GM107** |
| `ogdoc/Devinit/devinit.xml` | tên thanh ghi | spec chỉ có opcode, không có register map |
| `ogdoc` toàn bộ | block PCIe Turing | không có |
| `ogkm` `gpu/vbios/` | PCIe config parser | không có (chỉ FWSEC/ROM dir) |
| nouveau `pci/gp100.c` | link speed code | **không có** (chỉ MSI rearm + cfg window) |
| Sourcegraph | `0x88610`, `NV_PCIE` Turing | 0 hit hữu ích |

---

## 7. CẦN GÌ ĐỂ ĐÓNG CÁC UNKNOWN NÀY

1. **`pcie_idx`**: disassembly GSP-RM (binary `gsp_rm.bin` trong firmware package) —
   tìm consumer của `vbios_pstate_entry_6x` + 3. Hoặc RM API `NV2080_CTRL_PERF_*`.
2. **`0x88610`**: một Turing register map, hoặc đọc/ghi thử trên card **không** thuộc
   diện bảo hành (không làm trong repo này).
3. **Condition 86/82**: parse condition table của token `I` (`condition_table_ptr` tại
   `nvinit_ptrs+0x06`) — khả thi read-only, là việc tiếp theo rẻ nhất.
4. **Width thật**: mod tụ là can thiệp phần cứng, ngoài phạm vi repo.

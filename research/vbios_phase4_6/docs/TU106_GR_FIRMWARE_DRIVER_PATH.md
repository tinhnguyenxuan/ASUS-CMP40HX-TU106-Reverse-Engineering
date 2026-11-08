# GR / FIRMWARE / DRIVER PATH — Phase 4E

> **Publication edition (V5):** This is a curated ROM/source-analysis extract from the supplied `vbiosrel6(2).zip`. Host telemetry, game tests, benchmark steps and Windows/Linux collectors are intentionally omitted. It is historical research, **not** new hardware verification. See [integrated report](../../../docs/TU106_VBIOS_PHASE4_6.md).


**Câu hỏi:** đường khởi tạo graphics từ VBIOS tới ứng dụng, và liệu có chỗ nào phân nhánh
theo Device ID `1F0B` để áp chính sách riêng cho CMP.

**Môi trường:** phân tích tĩnh + đối chiếu nguồn mở. Không exploit, không flash, không ghi MMIO.

---

## 0. KẾT LUẬN NGẮN

| # | Nội dung | Mức |
|---|---|---|
| 1 | Chain: VBIOS → Devinit → (PMU/GSP-RM hoặc ACR/SEC2) → FECS/GPCCS → GR → app | STRONGLY SUPPORTED |
| 2 | **Nouveau không phân nhánh theo Device ID**: một entry `nv166_chipset` cho cả 1F06/1F07/1F0B | PROVEN |
| 3 | nvgpu **không hỗ trợ** dGPU TU106 (chỉ Tegra) ⇒ không thể là nơi có policy | PROVEN |
| 4 | open-gpu-kernel-modules phân nhánh theo **chip** (`HAL_IMPL_TU106`), không theo device id | PROVEN |
| 5 | Nơi **có thể** phân nhánh theo `1F0B`: GSP-RM (closed), hoặc VBIOS (device id nằm trong PCIR) | UNKNOWN |
| 6 | `0x4096xx` / `0x021C38`: là **địa chỉ literal trong script** / **thanh ghi đọc live**, không phải unlock | PROVEN (vị trí), UNKNOWN (nghĩa) |
| 7 | Số SM/TPC: fuse → SEC2/GSP → driver, **không** có bảng trong ROM | STRONGLY SUPPORTED |

---

## 1. CHUỖI KHỞI TẠO

```
VBIOS (BIT/P2, Devinit script)
   |
   +-- Devinit (INIT_* opcodes) : lập trình PCIe, memory, clocks, thermal
   |
   +-- chọn đường quản lý:
   |      (a) PMU firmware  — Turing có PMU, luôn có
   |      (b) GSP-RM        — firmware lớn, thay RM phần lớn (mặc định trên Turing)
   |      (c) driver RM     — phần còn lại trong nvidia.ko/sys
   |
   +-- ACR (Authenticated Code Region) nạp ucode vào các Falcon:
   |      SEC2 -> bootstrap, ghi cấu hình bảo vệ (SS0/SS1/FECS_PLM)
   |      FECS  (Front-End Context Switch)  — scheduler cấp GPC/TPC
   |      GPCCS (GPC Context Switch)        — scheduler trong từng GPC
   |
   +-- GR engine init: nạp ucode GR, set ZBC, L2, SM config
   |
   +-- ứng dụng: D3D12/Vulkan -> UMD -> KMD -> channel -> GR
```

Nguồn cho từng mắt: `nvkm/engine/device/base.c` (chipset→engine mapping),
`nvkm/subdev/acr/*` (ACR/SEC2), `nvkm/engine/gr/tu102.c`, `nvkm/falcon/*`.

---

## 2. CÓ PHÂN NHÁNH THEO `1F0B` KHÔNG? — TRA BA NGUỒN MỞ

### 2.1 Nouveau — KHÔNG

`drivers/gpu/drm/nouveau/nvkm/engine/device/base.c`, bài `nv166_chipset`:

```c
static const struct nvkm_device_chip
nv166_chipset = {
        .name = "TU106",
        .acr = { 0x00000001, tu102_acr_new },
        .gr  = { 0x00000001, tu102_gr_new },
        .sec2= { 0x00000001, tu102_sec2_new },
        ...
};
```

Một struct cho **cả ba** device id (1F06, 1F07, 1F0B). Không có `switch (device_id)` nào
trong đường GR/ACR/SEC2. ⇒ **Nouveau không thể** áp policy riêng cho CMP. **PROVEN.**

### 2.2 nvgpu — KHÔNG LIÊN QUAN

`nvgpu` là driver cho GPU **Tegra** (SoC). Không có đường dGPU TU106. Việc nó có định nghĩa
`vbios_pstate_*` chỉ vì định dạng VBIOS dùng chung, không phải vì nó chạy trên card rời.

### 2.3 open-gpu-kernel-modules — theo CHIP, không theo device id

`src/nvidia/src/kernel/gpu/gpu.c:4743`:

```c
case HAL_IMPL_TU106:
        *gpuImpl = GPU_IMPLEMENTATION_TU106;
```

`HAL_IMPL_TU106` là **chip**, không phải device id. Không tìm thấy `0x1F0B` / `1F0B` trong
`src/nvidia/src/kernel/gpu/`. Phần đọc device id và phân nhánh nằm trong RM closed
(`nv-kernel-module` binary) và GSP-RM.

### 2.4 Nơi duy nhất device id xuất hiện: VBIOS

Device id nằm trong **PCIR** (`+0x06`), và ROM CMP là `0x1F0B`. Một script Devinit **có thể**
đọc nó qua opcode condition (`INIT_CONDITION` / `INIT_NV_REG_CONDITION_DIRECT`) — nhưng điều
kiện đó đọc **thanh ghi**, không đọc PCI config một cách trực tiếp. Chưa tìm thấy script nào
nhánh theo device id trong 3 ROM này.

⇒ **Kết luận:** nếu có policy riêng cho CMP, nó nằm trong **GSP-RM** (firmware binary đóng)
hoặc trong **chính sách của driver userspace** (xem 4F). **UNKNOWN**, và không thể đóng bằng
nguồn mở.

---

## 3. CÁC ĐỊA CHỈ `0x4096xx` — PHÂN BIỆT BỐN LOẠI

Đây là chỗ dễ sai nhất. Bốn thứ khác nhau:

| loại | nghĩa | ví dụ |
|---|---|---|
| **literal trong script** | một con số xuất hiện trong byte stream devinit | `0x409664` trong token `I` |
| **lệnh được mã hoá** | opcode + operand tạo thành một phép ghi | `0x7A 0x00000000 ...` |
| **nhánh có điều kiện** | opcode nằm sau `INIT_CONDITION`, chỉ chạy nếu cond đúng | mọi thứ sau `0x75` |
| **phép ghi quan sát được** | đọc/ghi thật trên card | `0x021C38 = 0x20` (phiên trước) |

| address | trong ROM? | loại | ghi chú |
|---|---|---|---|
| `0x409658` | có (token `I`) | literal, cạnh condition | cặp với `0x40965C` |
| `0x40965C` | có | literal | idem |
| `0x409660` | có | **đọc** bit16 (`0x10000`) | điều kiện, **không** phải ghi |
| `0x409664` (SS0) | có | literal | tên "SS0" từ nghiên cứu cộng đồng, không phải NVIDIA |
| `0x40966C` (SS1) | có | literal | idem |
| `0x021C38` | **không** | thanh ghi đọc live | phiên trước: `0x20` ⇒ TPC5 tắt (HYPOTHESIS) |
| `0x021040` | **không** | thanh ghi ghi live | phiên trước: ghi được, sticky |

**Về dải địa chỉ:** `0x00400000` là base của block GR trên nhiều chip NVIDIA, nên
`0x4096xx = GR + 0x96xx`. Nhưng **không có register map Turing công khai** để đặt tên cho
`GR+0x9658` hay `GR+0x9664`. Ghi **UNKNOWN** cho nghĩa; **PROVEN** cho vị trí.

Tương tự `0x021C38`: dải `0x00021xxx` thường là một block cấu hình chip; rnndb chỉ có
`PUNITS @ 0x022400` (khác dải) và variant dừng ở GM107. Không đặt tên được.

> **Không** gọi các địa chỉ này là "unlock". Một condition record không phải unlock. Một
> literal trong script không phải unlock. Tên "SS0/SS1" là **nhãn do cộng đồng đặt**, không
> phải thuật ngữ NVIDIA trong bất kỳ tài liệu mở nào đã tra.

---

## 4. SỐ SM/TPC DO AI QUYẾT ĐỊNH

| tầng | có thể thay đổi số SM? | bằng chứng |
|---|---|---|
| **fuse** trên die | có — mask cứng | `HW_TPC_DISABLE_MASK` trong rnndb (nhưng variant dừng GM107); fuse là nguồn cuối |
| **VBIOS** | **không** — không có bảng SM/TPC | POWER TOPOLOGY giống hệt 3 card; không slot P2 nào chứa count |
| **SEC2 bootstrap** | có thể ghi đè cấu hình bảo vệ | `cmpunlocker` mô tả ghi `SS0/SS1/FECS_PLM` ở pha privileged |
| **GSP-RM** | có thể, theo policy | đóng |
| **driver userspace** | không (không thấy SM) | — |

Thực nghiệm phiên trước (`results/TPC5_LIVE/`): ghi `CTRL_OPT_TPC_GPC0 |= 0x20` từ ring-0
qua BAR0 sau khi bật `0x021040` vẫn **bounce** ⇒ tầng bảo vệ nằm dưới, không phải ở thanh
ghi đó. Đó là bằng chứng **âm** có giá trị: đường "bật TPC bằng MMIO" không hoạt động.

---

## 5. GRAPHICS SCHEDULER VÀ CONTEXT SWITCH

- **FECS** (Front-End Context Switch) giữ runlist cấp cao, quyết định channel nào chạy trên
  GPC nào. **GPCCS** làm việc đó trong từng GPC.
- Context switch có chi phí; nếu CMP có ít GPC/TPC hơn, chi phí tương đối tăng.
- Không có metric công khai "context switch latency" cho Turing ngoài GPUView/Nsight.

**Giả thuyết chưa kiểm chứng:** nếu CMP có ít SM hơn (34 vs 36) thì mỗi lần context switch
ảnh hưởng tỉ lệ lớn hơn — nhưng đây là hiệu ứng bậc hai, không giải thích chênh lệch lớn.

---

## 6. NHỮNG GÌ CẦN ĐỂ ĐÓNG

1. **GSP-RM binary**: `gsp_rm.bin` (trong `/lib/firmware/nvidia/<ver>/`). Disassembly tĩnh
   là hợp pháp trong nhiều nước cho mục đích nghiên cứu/tương thích, nhưng **không** làm
   trong repo này (không có binary, không có môi trường). Cần: tìm chuỗi `1F0B`, tìm hàm đọc
   `vbios_pstate_entry_6x` + offset 3.
2. **Register map Turing**: không có công khai. Cách gần nhất là đọc live trên card và so
   với hành vi, nhưng đó là thực nghiệm, không phải tĩnh.
3. **Số SM thật**: `deviceQuery` (M17) — 1 phút, quyết định H4.

---

## 7. KẾT LUẬN

- Đường khởi tạo **không** có chỗ nào trong nguồn mở phân nhánh theo `1F0B`.
- Nếu có policy riêng, nó ở **GSP-RM** hoặc **driver userspace**, cả hai đều đóng.
- Các địa chỉ `0x4096xx` là **dữ liệu**, không phải cơ chế. Chưa có bằng chứng chúng làm gì.
- **Không** kết luận "RT Core bị khoá ở tầng firmware" — không có bằng chứng cho cả chiều
  khẳng định và chiều phủ định.

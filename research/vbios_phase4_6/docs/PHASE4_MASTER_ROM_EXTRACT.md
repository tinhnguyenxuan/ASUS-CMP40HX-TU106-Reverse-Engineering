# PHASE 4 — MASTER REPORT (VI)

> **Bản tuyển chọn cho GitHub:** chỉ giữ phần phân tích cấu trúc ROM, điều kiện/bằng chứng và giới hạn kết luận; các mục tổ chức đo/test trực tiếp không nằm trong bản này.


**Repo:** `TU106_VBIOS_RE`, tiếp từ v3.
**Ngày:** 2026-11-07.
**Ba ROM:** CMP 40HX (`10DE:1F0B`), RTX 2060 SUPER (`1F06`), RTX 2070 (`1F07`).
**Môi trường:** Ubuntu, **không có GPU NVIDIA, không có máy Windows**. Vì vậy: **không có
phép đo nào đã chạy trong Phase 4**. Mọi kết luận là ROM + nguồn công khai + thiết kế đo.

---

## 1. PHASE 4 ĐÃ LÀM ĐƯỢC GÌ (kết quả cụ thể, không phải kế hoạch)

### 1.1 Giải mã thêm 3 bảng — nhóm UNKNOWN lớn nhất đã đóng

| bảng | trước | sau | cách |
|---|---|---|---|
| **POWER BUDGET** (slot 11) | UNKNOWN | **cấu trúc PROVEN**, giá trị STRONGLY SUPPORTED | nvgpu `pwr_policy_3x` + extent `44+20*66+15*14+13*13 = 1743` **đóng chính xác** |
| **POWER TOPOLOGY** (slot 15) | UNKNOWN | **PROVEN** | `pwr_topology_2x` khớp 100%: `6+20*22+15*27 = 851` |
| **THERMAL POLICY** (slot 20) | UNKNOWN | **cấu trúc PROVEN**, field UNKNOWN | `10+4*40 = 170` đóng chính xác |
| **LOW POWER GR** (slot 32) | UNKNOWN | **cấu trúc PROVEN**, mask UNKNOWN | `10+5*5 = 35` đóng chính xác |

Điểm mấu chốt của phương pháp: **header tự khai báo kích thước của cả bốn khối con**
(entries, rel, viol). v3 thất bại vì chỉ dùng layout của envytools (bản gốc, không có khối
rel/viol). Khi đọc đủ bốn con số từ header, extent đóng tuyệt đối.

### 1.2 Kết quả power — phát hiện quan trọng nhất của Phase 4

```
POWER BUDGET entry 2 (class_id = 1):
  CMP    : limit_min 110000  limit_rated 184000  limit_max 220000   (mW)
  2060S  : limit_min 125000  limit_rated 184000  limit_max 220000
  2070   : limit_min 125000  limit_rated 185000  limit_max 222000
```

⇒ **CMP có cùng công suất mặc định và cùng trần với RTX 2060 SUPER.**
Khác biệt duy nhất: `limit_min` **thấp hơn 15 W** — tức cho phép hạ xuống thấp hơn, không
phải siết xuống. Đây là **bác bỏ** giả thuyết "VBIOS bóp công suất CMP".

### 1.3 PCIe — ba khác biệt độc lập, và một cảnh báo

| # | khác biệt | giá trị | mức |
|---|---|---|---|
| 1 | `PCIEGEN` domain (P-state idx 8) nom/min/max | CMP **1/1/1** vs GeForce **3/3/3** | STRONGLY SUPPORTED (tương quan), **UNKNOWN** (đơn vị) |
| 2 | PCIe settings script, reg `0x0088610` | CMP `0x00000001` vs GeForce `0x00001001` | PROVEN (giá trị) |
| 3 | `LOW POWER PCIe` slot 30, byte 8 × 5 entry | CMP `0xFB` vs GeForce `0xF8` | PROVEN (giá trị) |

Cộng thêm: `CONDITION` id 86 (CMP) vs 82 (GeForce) trong PCIe script.

**Cảnh báo bắt buộc:** *không* gọi `0x88610` là công tắc Gen1/Gen3. `0x88610` nằm trong
block `PPCI` (base `0x088000`, size `0x1000`, theo nouveau `gp100_pci_func`) tại `+0x610`,
nhưng **không có register map Turing** đặt tên cho offset đó. Và **dữ liệu live phải thắng
tài liệu cộng đồng** — nếu `LnkSta` báo 8 GT/s thì `PCIEGEN = 1` không phải link speed.

### 1.5 Firmware/driver — không có nhánh theo `1F0B` trong nguồn mở

- nouveau: một `nv166_chipset` cho cả 1F06/1F07/1F0B, **không** switch theo device id.
- nvgpu: chỉ Tegra, không liên quan dGPU.
- open-gpu-kernel-modules: phân nhánh theo **chip** (`HAL_IMPL_TU106`), không theo device id.
⇒ Policy riêng (nếu có) nằm trong **GSP-RM** hoặc **driver userspace**. Cả hai đóng.

## 2. NHỮNG GÌ VẪN CHƯA CHỨNG MINH ĐƯỢC

| # | câu hỏi | vì sao chưa |
|---|---|---|
| 1 | Card CMP thật sự chạy PCIe gen/width nào | chưa chạy M01 trên máy có card |
| 2 | `PCIEGEN = 1` có nghĩa Gen1 không | không consumer công khai; cần `LnkSta` |
| 3 | `0x88610` bit 12 làm gì | không register map Turing |
| 4 | `pcie_idx` trỏ bảng nào | nvgpu không dereference; RM đóng |
| 5 | Byte 8 của `LOW POWER PCIe` nghĩa gì | không schema |
| 6 | Byte `+4` của THERMAL POLICY (0xFF vs 0x02) | không schema |
| 7 | Bit 27 của `LOW POWER GR` entry 0 | nvgpu chỉ đặt tên bit 0 và 4 |
| 8 | VF curve / voltage map | VFE extent không đóng (còn thiếu khối) |
| 9 | Strap bộ nhớ nào active | không có trường trong ROM |
| 10 | Số SM/TPC thật (34 hay 36) | cần `deviceQuery` |
| 11 | Game chạy trên CMP hay adapter khác | cần GPUView |
| 12 | Tensor có bị cap trên driver hiện tại | cần M06 |
| 13 | RT Core có chậm không | cần M08 + M10, và không có metric RT unit |
| 14 | Có policy riêng cho `1F0B` trong GSP-RM | binary đóng, không có trong repo |

---

## 3. ĐIỀU KHÔNG ĐƯỢC NÓI (đã kiểm lại)

Theo yêu cầu phương pháp #4, các câu sau **không** xuất hiện như kết luận trong bất kỳ tài
liệu Phase 4:

| câu | vì sao không được nói |
|---|---|
| "chắc chắn không có RT lock" | chưa đo RT; GPC giống nhau không loại trừ RT unit |
| "ROM không thể throttle" | ROM có `limit_min/max`; runtime policy có thể khác |
| "RT Core bình thường" | không có metric, không có phép đo |
| "27 MHz HUB/DISP là xung thật" | chỉ là giá trị trong bảng; chưa đọc NV_PCLK |
| "bảng giống byte ⇒ policy giống" | `POWER TOPOLOGY` giống byte nhưng đó là *cảm biến*, không phải policy |

Cách nói được dùng thay thế: "trong các bảng đã decode, không có trường nào…", "chưa có
bằng chứng cho…", "cần phép đo Mxx để phân biệt".

---


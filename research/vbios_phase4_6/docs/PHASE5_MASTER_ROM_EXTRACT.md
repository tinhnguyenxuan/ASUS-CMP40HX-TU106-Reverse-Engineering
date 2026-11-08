# PHASE 5 — MASTER REPORT (VI)

> **Bản lưu trữ lịch sử:** không phải kết luận cập nhật hay xác minh độc lập; xem [bảng đính chính và tiến triển Phase 1–6](../../../docs/TU106_VBIOS_PHASE1_5_HISTORY.md). Phép đo/test game thực tế đã lược khỏi bản xuất bản này.


**Tiếp từ:** `TU106_VBIOS_RE` Phase 4. Không làm lại Phase 1–4.
**Ngày:** 2026-11-07.
**Môi trường:** Ubuntu, **không GPU NVIDIA, không máy Windows** ⇒ **không có phép đo runtime
nào trong Phase 5**. Mọi kết luận là ROM + nguồn công khai + thiết kế đo.

---

## 1. SÁU LỖI ĐÃ SỬA (A)

| lỗi | đúng | ai phát hiện |
|---|---|---|
| "LOW POWER GR bit 27" | **bit 3** của u32 LE (`0xFFFFFFE7` vs `0xFFFFFFEF`, XOR `0x8`) | yêu cầu Phase 5 |
| power/clock "bị bác bỏ" | **KHÔNG KHÁC TRONG ROM**; runtime chưa đo | yêu cầu Phase 5 |
| `resource0_wc` trong collector | bỏ — không đọc raw MMIO | yêu cầu Phase 5 |
| dxdiag/registry làm bằng chứng CASO | phải dùng `D3DKMTQueryAdapterInfo(KMTQAITYPE_CROSSADAPTERRESOURCE_SUPPORT)` | yêu cầu Phase 5 |
| "2 copy = 2 lần PCIe" | chỉ đúng nếu resource ở adapter khác; phải xác định vị trí | yêu cầu Phase 5 |
| M02 lẫn trong nhóm read-only | tách `4C-MUTATING` | yêu cầu Phase 5 |

Guard: `scripts/phase5/test_phase5.py` fail nếu bất kỳ chuỗi sai nào quay lại, nếu
`resource0_wc` trở lại trong code, hoặc nếu M02 mất nhãn mutating.

---

## 2. VFE — GIẢI MÃ ĐẦY ĐỦ CẤU TRÚC (B)

### 2.1 Cấu trúc

Slot 8 **không phải** "VOLT MAPPING" như v3 tưởng, mà là **bảng phương trình V/F**:

```
9 (header) + 20×25 (var) + 150×24 (equ) + 55×24 (rppm) + 15 (tail) = 5444 B
```
Extent đóng **chính xác** lên slot 10 ở cả 3 ROM.

Header khớp `vbios_vfe_3x_header_struct` của nvgpu:
`ver=0x30, hlen=9, var 25×20, equ 24×150, poll=200, rppm 15/40`.

**Kiểm chứng stride:** mọi `type` byte của var ∈ 0..7 và của equ ∈ 0..6 — đúng enum NVIDIA.
Stride sai sẽ đọc ra byte rác ngay. Đây là guard mạnh hơn extent.

### 2.2 Phát hiện mới: giá trị là **float32**

`out_range_min/max` không phải số nguyên. Đọc thô được:

| hex | float32 | nhận xét |
|---|---|---|
| `0x42240000` | **41.0** | ngưỡng |
| `0x42700000` | **60.0** | ngưỡng |
| `0x00000000` | 0.0 | |
| `0x7F7FFFFF` | **±3.4028e38** | = FLT_MAX, dùng làm "không giới hạn" |
| `0xC2D20000` | **−105.0** | |

Một chuỗi toàn giá trị hợp lý như vậy ⇒ **PROVEN** là float32.

### 2.3 So ba ROM — sửa lại kết luận sơ bộ

| | CMP vs 2060S | CMP vs 2070 |
|---|---|---|
| byte | **5444/5444 giống** | 5240/5444 (204 B khác) |
| var entry | 0/20 khác | 3/20 khác |
| equ entry | 0/150 khác | 25/150 khác |

⇒ **CMP trùng hoàn toàn với 2060S**, khác 2070. Khác biệt đáng chú ý: var 6 (type
`SENSED_FUSE`) = `[41.0, 41.0]` trên CMP/2060S, `[60.0, 60.0]` trên 2070.

**HYPOTHESIS:** 41/60 là ngưỡng nhiệt °C. Chưa có consumer xác nhận đơn vị ⇒ không kết luận.

**Hệ quả:** VFE **không thể** là nguyên nhân CMP chậm hơn 2060S — hai bảng giống từng byte.

---

## 3. LOW POWER GR — BIT 3 (B)

```
CMP     E7 FF FF FF 01  -> u32 LE 0xFFFFFFE7   bit3 = 0
GeForce EF FF FF FF 01  -> u32 LE 0xFFFFFFEF   bit3 = 1
```
Chỉ **một** bit khác nhau, chỉ ở **entry 0**. Hai bit **có tên** (0 GR, 4 RPPG) giống nhau ở
cả 3 card ⇒ không phân biệt gì.

Bit 3 **không có tên** trong mọi header công khai và **không có consumer**.
⇒ **UNKNOWN**. Không gọi là throttle, không gọi là RT lock.

---

## 4. DRIVER / FIRMWARE (D)

| nguồn mở | có nhánh theo `1F0B`? | có consumer cho pstate/power/lpwr? |
|---|---|---|
| nouveau | **không** (một `nv166_chipset`) | **không** |
| nvgpu | không liên quan (Tegra) | **không** (chỉ có schema) |
| open-gpu-kernel-modules | **không** (`HAL_IMPL_TU106` = chip) | **không** |

⇒ Policy thật (nếu có) ở **GSP-RM** hoặc **RM closed**. Cả hai không có trong repo.

`0x88610` = `PPCI + 0x610` (block PCIe `0x088000`, size `0x1000` theo nouveau
`gp100_pci_func`). Không có tên trong mọi register map công khai ⇒ **không** gọi là công tắc
Gen1/Gen3.

**Condition table 82/86 — đã thử, thất bại:** bảng ở `0x2cc9c` (CMP) / `0x2cc6e` (2060S),
**370/1024 byte khác nhau** giữa CMP và GeForce, có pattern entry 12 B
(`08 23 61 00 | 80 00 00 00 | 80 00 00 00`) nhưng **không có schema** để giải mã.
Đây là bảng **duy nhất** tìm được vừa khác SKU vừa có khả năng là logic điều kiện ⇒ ứng viên
số một nếu có schema.

---

## 7. ĐIỀU KHÔNG ĐƯỢC NÓI (đã kiểm bằng guard)

| câu | lý do |
|---|---|
| "chắc chắn không có RT lock" | chưa đo RT, không có metric |
| "ROM không thể throttle" | ROM có `limit_min/max`; runtime policy có thể khác |
| "RT Core bình thường" | không có phép đo |
| "27 MHz HUB/DISP là xung thật" | chưa đọc NV_PCLK |
| "bit 27" | sai — là bit 3 |
| "CASO đang bật" (suy từ dxdiag/registry) | không phải nguồn hợp lệ |
| "2 copy = 2 lần PCIe" | phụ thuộc vị trí resource |

---

## 8. GIỚI HẠN CỦA PHASE 5

- **Không có số đo nào.** Bộ thu đã viết, chưa chạy.
- **Không có ROM thứ tư.** H12 không đóng được.
- **Không có GSP-RM binary.** H2/H3 cơ chế không đóng được.
- **Condition table không có schema** ⇒ 82/86 vẫn UNKNOWN.
- VFE: `equ.param0..2` và 55 rppm record **chưa** giải mã ngữ nghĩa.

---


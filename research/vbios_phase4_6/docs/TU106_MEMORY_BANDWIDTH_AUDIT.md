# MEMORY / VRAM / L2 / ReBAR AUDIT — Phase 4G

> **Publication edition (V5):** This is a curated ROM/source-analysis extract from the supplied `vbiosrel6(2).zip`. Host telemetry, game tests, benchmark steps and Windows/Linux collectors are intentionally omitted. It is historical research, **not** new hardware verification. See [integrated report](../../../docs/TU106_VBIOS_PHASE4_6.md).


**Câu hỏi:** CMP có bị giảm băng thông VRAM, hay vấn đề nằm ở PCIe/host-visible memory?

---

## 0. CẢNH BÁO PHƯƠNG PHÁP

> **Bảng Memory Timings giống nhau KHÔNG chứng minh cùng timing profile đang chọn.**
>
> Ba ROM có chung bảng `MEMORY TIMINGS MAPPING` (7 dải tần) và `MEMORY TIMINGS` (60 strap),
> nhưng **không có gì trong ROM nói strap nào đang active**. Strap được chọn bởi
> strapping phần cứng + devinit + (có thể) PMU, không phải bởi một trường "strap = N".
>
> Ngược lại, v3 đã tìm ra CMP **khác** GeForce ở strap 12–17 (RFC 148 vs 180, REFRESH 6 vs 4).
> Nhưng nếu strap đang dùng là strap 0, thì khác biệt ở strap 14 **không ảnh hưởng gì**.

---

## 1. DỮ LIỆU ROM ĐÃ CÓ

### 1.1 Memory Clock Table v0x11 (slot 1)

`ver=0x11, hlen=26, base=60, strap=33, strap_cnt=10, cnt=7` → `2756 B`, đóng đúng.

7 dải tần (giống cả 3 ROM):

| # | min–max (MHz) | tương đương |
|---|---|---|
| 0 | 0–540 | ≤ 1,08 Gbps |
| 1 | 541–1249 | ~2,5 Gbps |
| 2 | 2005–4699 | ~8–18,8 Gbps |
| 3 | 4700–5500 | ~18,8–22 |
| 4 | 5501–6300 | ~22–25,2 |
| 5 | 6301–6700 | ~25,2–26,8 |
| 6 | 6701–16383 (2070: 6701–**9000**) | ≥ 26,8 |

Hai điều đọc được:
- CMP và 2060S cho dải 6 tới **16383**, 2070 chỉ tới **9000**. Đây là **khác biệt thật**
  giữa 2070 và hai card kia — có thể là giới hạn bảng của BIOS 2070, không phải giới hạn HW.
- Lỗ hổng `1250..2004` có ở cả 3 ⇒ đặc điểm chung, không phải lỗi.

**Không** đọc được: strap nào active.

### 1.2 Memory Tweak Table v0x20 (slot 2)

`ver=0x20, hlen=6, base=74, cnt=60` → `4446 B`. 19 bitfield × 60 strap.

Strap 0 (14 Gbps): `CL=24 WL=5 RC=78 RFC=210 RAS=52 RP=26 RD_RCD=26 WR=27 FAW=16`.

### 1.3 Khác biệt CMP vs GeForce

| strap | field | CMP | 2060S/2070 |
|---|---|---|---|
| 14 | RFC | 148 | 180 |
| 14 | RAS | 37 | 42 |
| 14 | FAW | 16 | 24 |
| 14 | CL | 20 | 22 |
| 15 | RFC | 126 | 150 |
| 12–17 | REFRESH | **6** | **4** |
| 46+ | toàn bộ | có data | 2070 = 0 |

**Đọc đúng:** CMP có timing **chặt hơn** ở các strap đó (RFC/RAS/FAW/CL nhỏ hơn) nhưng
**REFRESH lớn hơn** (refresh thưa hơn = ít tốn bandwidth hơn). Hai chiều ngược nhau ⇒
không thể kết luận "CMP tệ hơn" từ bảng này.

---

## 3. PCIe / HOST-VISIBLE / ReBAR

### 3.1 Ba loại băng thông khác nhau, đừng gộp

| loại | đường | lý thuyết | đo bằng |
|---|---|---|---|
| **VRAM bandwidth** | GDDR6 ↔ L2 ↔ SM | ~448 GB/s | `clpeak --global-bandwidth` |
| **PCIe device↔host** | VRAM ↔ system RAM | Gen1 x4 ≈ 0,85 · Gen3 x16 ≈ 15,75 GB/s | `nvbandwidth -t host_to_device` |
| **host-visible / BAR1** | CPU ghi trực tiếp vào VRAM | phụ thuộc BAR1 size | ReBAR check + memcpy test |

Ba con số chênh nhau **hàng chục lần**. Mọi kết luận "memory chậm" phải nói rõ loại nào.

### 3.2 ReBAR

```bash
lspci -vv -s 03:00.0 | grep -A2 "Region 1"     # BAR1 size
cat /sys/bus/pci/devices/0000:03:00.0/resource   # dòng thứ 2 = BAR1
```
- BAR1 = 256 MB ⇒ ReBAR tắt ⇒ mọi transfer lớn phải qua **bounce buffer** trong system RAM.
- BAR1 = 8 GB ⇒ ReBAR bật ⇒ CPU có thể map toàn bộ VRAM.

Với CMP, cộng đồng (`cmpunlocker`) nói ReBAR selector 7 → 8 GiB, tức **có thể** bật. Nhưng
ReBAR **không** làm PCIe nhanh hơn — nó chỉ bỏ bounce buffer. Không nhầm hai thứ.

### 3.3 Vì sao host-visible quan trọng với CMP

CMP không có display ⇒ frame phải qua adapter khác (4A). Nếu cross-adapter resource nằm ở
**system memory** thay vì VRAM, đường đi là:

```
VRAM(CMP) --PCIe--> RAM --PCIe--> VRAM(display GPU)
```

Hai lần qua PCIe **mỗi frame**. 1080p60 BGRA = 8,3 MB × 2 × 60 = **1 GB/s** — vượt Gen1 x4.
Đây là lý do phép đo M03 (host↔device) quan trọng hơn M04 (VRAM) để giải thích FPS.

---

## 4. COPY ENGINE / DMA

- Mỗi GPU có ≥1 copy engine (CMP: TU106 có 5 CE theo `nv166_chipset .ce = 0x1f` = 5 instances).
- Copy engine dùng để: cross-adapter copy, texture upload, mipmap gen.
- **Copy engine và compute/graphics chạy song song** — nên copy không nhất thiết chặn render,
  nhưng nó **chiếm PCIe bandwidth**, và nếu cùng lúc texture streaming cần PCIe thì tranh nhau.

Đo: GPUView CE track (M12), hoặc Nsight Systems "CUDA HW" + "Copy Engine".

---

## 6. NHỮNG GÌ CHƯA BIẾT

| | trạng thái |
|---|---|
| strap active trên card | **UNKNOWN** |
| VRAM vendor (Micron/Samsung) | **UNKNOWN** từ ROM — xem 4H; có thể đọc qua `nvidia-smi -q -d MEMORY` (một số driver hiện part number) |
| BAR1 size thực tế | **UNKNOWN** |
| L2 throughput riêng | **UNKNOWN** — không có metric công khai |
| PCIe thực tế (gen/width) | **UNKNOWN** — xem 4C §5 |

---

## 7. KẾT LUẬN

1. ROM **không** nói strap nào active ⇒ mọi suy luận "timing CMP xấu hơn" từ bảng là
   **HYPOTHESIS**, không phải kết luận.
2. Ba loại băng thông phải đo riêng: VRAM (~448), PCIe (0,85–15,75), host-visible (BAR1).
3. Với CMP, **PCIe bandwidth** là con số quan trọng hơn VRAM, vì mọi frame hiển thị phải
   qua nó (4A) và vì Gen1 x4 nhỏ hơn băng thông cần cho cross-adapter 1080p60.
4. ReBAR giúp bỏ bounce buffer, **không** tăng tốc PCIe. Không nhầm.

# MULTI-ROM SCHEMA INFERENCE — Phase 4H

> **Publication edition (V5):** This is a curated ROM/source-analysis extract from the supplied `vbiosrel6(2).zip`. Host telemetry, game tests, benchmark steps and Windows/Linux collectors are intentionally omitted. It is historical research, **not** new hardware verification. See [integrated report](../../../docs/TU106_VBIOS_PHASE4_6.md).


**Mục tiêu:** khi có nhiều ROM TU106, field nào thay đổi theo model / PCB / VRAM vendor /
PCIe policy / TDP, và field nào bất biến (⇒ thuộc về chip, không thuộc về board).

**Trạng thái:** **KHÔNG lấy được ROM mới trong phiên này.** Chi tiết ở §1. Tool đã sẵn sàng
(§3) và chạy đúng trên 3 ROM hiện có.

---

## 0. VÌ SAO CẦN NHIỀU ROM

Với **một** ROM, không phân biệt được ba loại field:

| loại | nghĩa | cách nhận biết |
|---|---|---|
| **chip-invariant** | giống mọi TU106 | cần ≥2 ROM khác board |
| **board-specific** | theo PCB/BOM | cần ≥2 ROM cùng model khác hãng |
| **SKU-specific** | theo model (2060S/2070/CMP) | cần ≥2 model |
| **VRAM-vendor** | theo Micron/Samsung | cần 2 ROM cùng model khác vendor |

Hiện có 3 ROM, mỗi cái **một** model, **một** board ⇒ chỉ tách được SKU-specific. Mọi kết
luận "chip-invariant" hiện tại chỉ là "giống ở 3 mẫu", không phải chứng minh.

---

## 1. ĐÃ THỬ LẤY ROM MỚI — KHÔNG ĐƯỢC

| nguồn | cách thử | kết quả |
|---|---|---|
| TechPowerUp VBIOS DB | `GET https://www.techpowerup.com/vgabios/?architecture=TU106` | **HTTP 200, 118 KB HTML**, nhưng **0 link** `href="/vgabios/<id>/..."` — trang render bằng JS |
| TechPowerUp direct ROM | `…/vgabios/<id>/<id>.rom` | trả **HTML**, không phải ROM (đã thử ở v3) |
| TechPowerUp `?model=` filter | cùng vấn đề | không có dữ liệu trong HTML tĩnh |

⇒ Cần **tải tay qua trình duyệt** (JS chạy được), hoặc một mirror ROM công khai khác.
Đây là **blocker**, không phải "không có ROM nào tồn tại".

**Không** commit ROM của bên thứ ba vào repo này: quyền phân phối chưa xác nhận, và ROM
chứa MAC/serial trong một số vùng. Tool nhận **đường dẫn**, không nhận nội dung.

---

## 2. DANH SÁCH ROM CẦN (ưu tiên giảm dần)

| # | loại | vì sao cần | tìm field gì |
|---|---|---|---|
| 1 | **CMP 40HX thứ hai** (khác board) | tách chip-invariant khỏi board | `POWER BUDGET e2`, `THERMAL POLICY +4`, `LPWR_GR e0`, `LPWR_PCIE e0` |
| 2 | **RTX 2060 SUPER** khác hãng (ASUS/MSI/EVGA) | board variance | `limit_min/rated/max`, `VFE` |
| 3 | **RTX 2070** revision khác | board variance | idem |
| 4 | **TU106 + Micron** vs **TU106 + Samsung** | VRAM vendor | `MEMORY TIMINGS` strap 0, `MEMORY CLOCK` rw0/rw1 |
| 5 | **TU104/TU116/TU117** | domain order có giữ nguyên không | `CLOCKS v0x35` ordering, `PSTATE` 10 domain |
| 6 | **RTX 2060 (TU106-200 non-S)** | SKU giữa 2060S và 2070 | TDP, clock |

Mục 5 không phải TU106 nhưng trả lời câu hỏi "10 domain có phải đặc trưng Turing hay TU106" —
quan trọng cho việc dùng `PCIEGEN` index 8 ở card khác.

---

## 3. TOOL — CHẠY ĐƯỢC NGAY

```bash
python3 scripts/phase4/multi_rom_diff.py rom_a.rom rom_b.rom [rom_c.rom ...] -o diff.csv
```

So sánh **theo cấu trúc** (P2 slot → parser → field), **không** theo file offset. Cột
`varies` = `yes` nếu field khác giữa các ROM.

52 field được so, nhóm: `PCI`, `PWR_BUDGET`, `PWR_TOPO`, `CLOCKS35`, `PSTATE`,
`PSTATE_TOP`, `PBC`, `MEMCLK`, `MEMTWEAK`, `THERMAL`, `LPWR_GR`, `LPWR_PCIE`, `PCIE_SCRIPT`.

### 3.1 Kết quả trên 3 ROM hiện có (baseline)

`52 fields, 30 vary`. Phân loại:

**Bất biến (22 field)** — ứng viên chip-invariant:
- `PCI class` (`0x030200` vs `0x030000`) — *không* bất biến, đây là SKU.
- `PWR_TOPO entries=20`, `first_rail=0xdf` — **giống hệt**
- `PCIE_SCRIPT`: 7 thanh ghi giống nhau, chỉ 1 giá trị khác
- `PSTATE_TOP` các domain không đổi: `GPC_nom=645`, `XBAR_nom=855`, `VID_nom=555`,
  `PWR_nom=540`, `DRAM_nom=7001`
- `MEMTWEAK s0_*` (strap 0 giống nhau)

**Biến thiên (30 field)** — ứng viên SKU/board:
- `PWR_BUDGET gpu_limit_min` (110k vs 125k) — **SKU**
- `PWR_BUDGET gpu_limit_rated` (184k vs 185k) — **SKU**
- `PBC base/boost` (1468/1648 vs 1408/1620) — **SKU**
- `PSTATE_TOP HUB/DISP/PCIEGEN` — **SKU** (3 domain đã biết)
- `MEMTWEAK s14/s15` — **SKU hoặc VRAM vendor** (chưa tách được)
- `THERMAL hdr_tail` — **SKU**
- `LPWR_GR e0`, `LPWR_PCIE e0` — **SKU**
- `PCIE_SCRIPT cond` (86 vs 82) — **SKU**
- `MEMCLK last_max` (16383 vs 9000) — **SKU** (2070 khác)

**Chú ý seductive trap:** `PBC hdr_tail = ff ff` giống nhau không có nghĩa PBC giống nhau —
v3 đã thấy `+9..+0x12` là `ff×10` (CMP) vs `03 09 ff×8` (GeForce). Tool lấy 2 byte đầu nên
báo "giống". Đây là ví dụ sống của việc **cột "varies=no" không chứng minh field bất biến** —
phải xem đủ độ dài field.

> **Sửa ngay:** `PBC hdr_tail` phải đọc đủ 10 byte. Ghi nhận, và trong lần chạy sau dùng
> `rom.hex(bc["hdr"] + 9, 10)`.

---

## 4. QUY TẮC SUY LUẬN (không vi phạm)

1. **Tương quan không phải nhân quả.** Nếu `gpu_limit_rated` khác giữa 2060S (184) và 2070
   (185), đó là *quan hệ đồng biến*, không chứng minh TDP quyết định field đó.
2. **≥2 ROM mới được gọi "invariant".** Hiện có 1 ROM/model ⇒ mọi "invariant" là giả thuyết.
3. **Phải loại trừ biến gây nhiễu.** Hai ROM khác hãng thường khác cả BIOS version, VRAM,
   và board — không tách được từng biến nếu không có nhóm đối chứng.
4. **Không commit ROM.** Chỉ commit CSV kết quả diff + đường dẫn/hash, và chỉ khi chủ ROM
   đồng ý.

---

## 5. KẾ HOẠCH KHI CÓ ROM

```bash
# 1. nhóm theo model, mỗi nhóm ≥2 ROM
python3 scripts/phase4/multi_rom_diff.py cmp_a.rom cmp_b.rom -o cmp.csv
python3 scripts/phase4/multi_rom_diff.py s2060_a.rom s2060_b.rom -o s2060.csv

# 2. field nào varies trong CÙNG model  => board-specific
# 3. field nào invariant trong cùng model nhưng khác giữa model => SKU-specific
# 4. field nào invariant ở mọi ROM => chip-invariant (mức STRONGLY SUPPORTED, không PROVEN)
# 5. đối chiếu với UNKNOWN_FIELDS.csv: field nào còn UNKNOWN mà varies => ưu tiên decode
```

Dòng trong `data/TU106_UNKNOWN_FIELDS.csv` được ưu tiên:
`THERMAL POLICY`, `LPWR_GR bit 3`, `LPWR_PCIE byte 8`, `POWER BUDGET class`, `VFE`.
Nếu các field này **invariant** ở 3 ROM hiện có mà **varies** khi thêm ROM ⇒ chúng mang
thông tin board, đáng decode hơn.

---

## 6. KẾT LUẬN

1. **Không lấy được ROM mới** (TechPowerUp cần JS). Blocker cụ thể, không phải thiếu nỗ lực.
2. **Tool đã sẵn sàng** và đã chạy: `scripts/phase4/multi_rom_diff.py`, 52 field, 30 biến thiên.
3. **Chưa thể tách** chip-invariant / board / VRAM-vendor với 1 ROM mỗi model.
4. **Không** dùng tương quan làm nhân quả; **không** commit ROM bên thứ ba.
5. Việc cần làm: tải tay 4–6 ROM (ưu tiên CMP thứ hai + 2060S khác hãng), rồi chạy một lệnh.

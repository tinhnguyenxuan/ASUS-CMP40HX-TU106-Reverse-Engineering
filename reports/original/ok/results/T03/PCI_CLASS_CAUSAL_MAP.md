# T03 — Bản đồ nhân quả PCI class / Device ID (CMP 40HX • TU106 • CG161P R2)

Ngày: 2026-11-05 (+07). Làm lại từ đầu, tự chạy tuần tự, không subagent. Phạm vi: offline + tra cứu công khai (R0) — không đổi strap, không MMIO/PCI config, không SSH.

## 0. Tóm tắt (≤10 dòng)

1. Netlist 6 strap: **VERIFIED** trực tiếp từ CAD (STRAP3 = G1/BM5, R258 pull-up, R261 pull-down).
2. EnvyTools PSTRAPS (G80+, trích xuất trực tiếp): Set1 bit4 = PCI class (0 = 0x030200 3D, 1 = 0x030000 VGA); Set0 bits 10-13/28/30 = DEVICE_ID bits; PSTRAPS MMIO 0x101000-0x101FFF [NV3+] BAR0; sample-at-reset từ pull trên bus RAM; bit31 = override enable — **VERIFIED ở mức tài liệu**, nhưng doc coverage dừng GK104, **không có TU106**.
3. lspci quan sát (1 sample): CMP 40HX = class 0302 (3D controller), device 0x1F0B, rev a1. RTX 2070/2060 SUPER (cũng TU106) = class 0300 (VGA compatible controller). Cùng die TU106, class khác.
4. Ánh x chân BM5/BK5/BJ5 → bit PSTRAPS trên TU106: **UNKNOWN** — EnvyTools không có bảng pin-to-bit TU106; tên net 'STRAP3' ≠ chỉ số bit.
5. Strap→PCI class / Device ID / display: **UNKNOWN** — không có direct-family TU106 source; class 0300 KHÔNG phải bằng chứng xuất hình.

## 1. Ba đường nhân quả (tách riêng)

### 1.1 Strap → PCI class

Chain lý thuyết: mức STRAP lúc reset → latch PSTRAPS (MMIO 0x101000-0x101FFF) → bit class (Set1 bit4) → 0x030200 (3D) ↔ 0x030000 (VGA) lúc enumerate.

Cơ chế (EnvyTools, G80+, không phải TU106-specific):
- Bit4 của strap set 1 chọn class: 0 = 0x030200 (3D controller), 1 = 0x030000 (VGA controller).
- Bit31 STRAPSx_PRIMARY cho phép BIOS/driver ghi đè sau reset → strap chỉ hiệu lực nếu không bị override.

Trạng thái: **EXTRAPOLATION G80+→TU106 [INFERRED]**. Không có bảng pin-to-bit TU106 ⇒ không biết BM5/BK5/BJ5 ánh xạ bit nào.

### 1.2 Strap → Device ID

Chain lý thuyết: STRAP5:3 → DEVID_SEL (N18E laptop [S2]); Set0 bits 10-13 + bit28 + bit30 = 6 bit DEVID [S1, G80+].

Không có bảng per-ID cho TU106 ⇒ **UNKNOWN**. Không gian ID TU106 công khai: 0x1F02 (RTX 2070), 0x1F06 (RTX 2060 SUPER), 0x1F0B (CMP 40HX, NVIDIA supportedchips chính thức), 0x1F0E, 0x1F10-0x1F15, 0x1F91. CMP 40HX = 0x1F0B.

Lưu ý số học (KHÔNG phải bằng chứng strap): 0x1F0B khác 0x1F06 ở bit1, khác 0x1F02 ở bit0 — khoảng cách số KHÔNG suy ra semantics strap.

Dữ liệu phủ định: strap-mod trên TU116/CMP 30HX (issue #569) — hệ thống nhận 'Basic Display Adapter', Device ID GIỮ NGUYÊN (không đổi 21C9) ⇒ ID có thể bị neo bởi fuse/firmware, không tự do đổi bằng strap.

### 1.3 Strap → display gate

**Không source/caller nào** nối strap trực tiếp → enable display. Hiển thị cần đủ chuỗi:
- Tuyến vật lý: IFPD_L0-3 / IFPA_L0-3, IFPD_AUX, HPD (T01: netlist GeForce có; BOM CMP chưa biết)
- VBIOS: display init / DCB / connector table (T05: DCB entry_count=0)
- Display engine + chính sách fuse (T04: fuse 0x21C04=1, DATA bit0=1 ≠ ENABLE encoding 0 ⇒ gpuFuseSupportsDisplay = false ⇒ gate FALSE)
- Driver: nếu Device ID không đổi, driver GeForce không bind dù class 0300.

Đổi class chỉ đổi enumeration. "VGA Compatible Controller" không tự tạo tín hiệu ở connector. "Đổi strap → có hình" là claim **CHƯA CHỨNG MINH**.

## 2. Quan sát 1 sample + diễn giải thay đổi

Quan sát (1 sample, không chứng minh nhân quả):
- class 0302, device 0x1F0B, rev a1 (pcie_map.json)
- STRAP5:3 ≈ 000 (photo INFERRED, chưa đo logic)

Cùng họ TU106 nhưng class khác (RTX 2070/2060S = 0300, CMP 40HX = 0302) cho thấy class có thể thay đổi trong cùng family, nhưng nguyên nhân có thể là fuse/firmware/devinit, không nhất thiết strap.

Kết luận hợp lệ duy nhất: quan sát **CONSISTENT** với giả thuyết, **chưa VERIFIED**.

## 3. Điều kiện để R258/R261 ảnh hưởng class (tất cả phải thỏa)

(a) BM5 thực sự là strap input điều khiển class/DEVID trên TU106 — **chưa chứng minh**;
(b) Strap được latch tại reset/power-good;
(c) Không có override PSTRAPS (bit31 primary) trước khi dùng;
(d) Tổ hợp STRAP5:3 sau điền là hàng hợp lệ của bảng (tránh vùng undefined);
(e) Cold boot sau khi điền (strap không đọc lại khi warm).

Nếu (a) sai → (b)-(e) vô nghĩa.

## 4. Điều KHÔNG suy ra được về display (từ strap)

- DCB/connector table VBIOS CMP (chưa dump; T05 entry_count=0)
- Cấu hình output: DP lane count, mapping HDMI/DVI
- Enable state display engine + fuse display
- Tuyến vật lý trên bản CMP: cặp vi sai, AC-coupling, ESD, AUX/HPD còn lắp hay không (CAD chỉ là design GeForce)
- Chính sách FWSEC/devinit
- Driver: ID không đổi → driver GeForce không bind

→ "Đổi strap → có hình" là **CHƯA CHỨNG MINH**. Ngay cả class 0300 + ID GeForce cũng chưa đủ (cần VBIOS tương thích; flash VBIOS GeForce ngoài phạm vi và khuyên KHÔNG làm khi chưa ghi hiện trạng).

## 5. Next discriminators (thứ tự ưu tiên)

1. Đọc hiệu dụng PSTRAPS (offset TU106 đã xác minh, read-only) → bit class thực + bit31 override.
2. Dump VBIOS CMP (SPI ROM, chỉ đọc) → tìm strap table / DCB / display init.
3. So strap table VBIOS 0x1F0B vs 0x1F02/0x1F06 (cần ROM đối chiếu có provenance).
4. Đo continuity 12 footprint khi ngắt nguồn → chốt population thật.

## 6. Claims cũ bị bác bỏ / điều chỉnh

- "STRAP3 đơn lẻ quyết định VGA/3D": **CHƯA ĐƯỢC CHỨNG MINH** trên TU106 — N18E chỉ cho thấy nhóm STRAP5:3 (multi-bit) quyết định trên laptop N18E, không đủ căn cứ để kết luận về TU106/CMP 40HX; không thể gọi là bị bác bỏ.
- "Class 0300 = có xuất hình": **BỊ BÁO BỌ** — class chỉ là enumeration metadata, không phải bằng chứng xuất hình.
- "Strap đổi × ID GeForce giữ nguyên (TU116)": **HỢP LÝ** như bằng chứng ID có thể bị neo fuse/firmware, không tự do strap.

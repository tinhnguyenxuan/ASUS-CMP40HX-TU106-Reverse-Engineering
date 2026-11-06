# T01 — Báo cáo định tuyến display PCB (CG161P R2 / CMP 40HX)

Ngày phân tích: 2026-11-05. Làm lại từ đầu, tự chạy tuần tự, không subagent. Phân tích trực tiếp file GenCAD `CG161P_R2_boardview.cad` (40,939 dòng). Không tin conclusion cũ.

## 1. Thành phần chính từ CAD (xem trực tiếp)

| Refdes | Vị trí (PLACE) | Lớp | Xoay | Hình dạng (SHAPE) | Ghi chú |
|--------|---------------|-----|------|-------------------|---------|
| G1 (GPU TU106) | 3277.362, 1967.008 | TOP | 270.00 | BGA_2228_P070_375X375 | Chip chính |
| J1 (DisplayPort) | -1402.953, 2935.158 | TOP | 270.00 | S_DISPLAY_20P_5HOLD_LF3 | Cổng DP |
| J5 (DVI dual-link) | -1639.961, 589.173 | TOP | 270.00 | SO_DVI_24P_4HD_RA_C1_LF3 | Cổng DVI |
| J10 (HDMI) | -1466.772, 1853.346 | TOP | 270.00 | SO_HDMI_38P_9H_C1_COLAY_LF3 | 2×HDMI footprint |

## 2. Chuỗi tín hiệu đã xác minh trực tiếp từ CAD (NODE → NODE)

### DP (J1)

| Tín hiệu | Đường đi (CAD) | Trạng thái |
|----------|---------------|------------|
| IFPD_L0 (lane 0+) | J1 pin1 ← C47 pin2 ← C47 pin1 → G1 BM18 | **CAD_ONLY** — lane AC-coupled qua C47 |
| IFPD_AUX_C | J1 pin15 ← D3 pin1 ← C43 pin2 → Q509 pin4 | **CAD_ONLY** — AUX qua IC đa chân Q509 |
| IFPD_AUX_R | Q7 pin3 ← C43 pin1 → Q509 pin1 | **CAD_ONLY** — AUX qua IC đa chân Q7/Q509 |
| DP_D_HPD_C | J1 pin18 ← R720 pin2 ← C1293 pin1 | **CAD_ONLY** — HPD |
| DP_D_HPD_R | R742 pin2 ← R720 pin1 ← C1296 pin1; R742 pin1 → Q521 pin1 | **CAD_ONLY** — HPD qua R742/Q521 (IC đa chân) |
| DP_PWR_CD | Tín hiệu tồn tại, đường đi chưa truy vết | **UNKNOWN** |

### DVI (J5)

| Tín hiệu | Đường đi (CAD) | Trạng thái |
|----------|---------------|------------|
| IFPA_L0 (lane 0+) | C1273 pin1 → G1 BG24 ← R7890 pin1 | **CAD_ONLY** — lane AC-coupled qua C1273 |
| IFPAB_TXD2_C (lane 0-) | J5 pin2 ← C1273 pin2 → R693 pin1 | **CAD_ONLY** |
| IFPA_HPD_C | J5 pin16 ← R101 pin2 ← C78 pin1 | **CAD_ONLY** — HPD |
| IFPA_HPD_R | R97 pin2 ← R101 pin1 ← C82 pin1 | **CAD_ONLY** — HPD qua R97/R101 |
| DDC_5V | Qua U502 (IC đa chân), chưa truy vết | **UNKNOWN** |

### HDMI (J10)
- J10 chỉ là **footprint**, chưa lắp connector thực (theo ảnh prior report).
- HDMI_C_HPD_C: J10 pin G19 ← C1305 pin1 (**CAD_ONLY**).
- HDMI_E_HPD_C: chưa truy vết (**UNKNOWN**).

## 3. Sideband (AUX/HPD/DDC/PWR) — chặn tại IC đa chân

| Tín hiệu | IC đa chân trên đường (refdes từ CAD) | Trạng thái |
|----------|--------------------------------------|------------|
| DP AUX | Q509, Q7 | **BLOCKED qua IC** — refdes/function chưa xác định từ CAD |
| DP HPD | Q521, R742, R720 | **BLOCKED qua IC Q521** |
| DVI HPD | R97, R101 (resistor, 2 chân — không chặn) | Không chặn qua IC, nhưng G1 pin cuối chưa truy vết |
| DVI DDC/I2C | U502 | **BLOCKED qua IC U502** |
| DP_PWR | U1 (theo prior report) | **UNKNOWN** |

Các IC đa chân (Q509, Q521, Q7, Q508, U502, U1, v.v.) có refdes trong CAD nhưng **không định danh chức năng/loại IC** trong file .cad. Cần ảnh silkscreen macro để xác định.

## 4. Tách thiết kế GeForce và lắp ráp CMP

- CAD là thiết kế **GeForce CG161P R2** (reference ASUS DUAL-RTX2060S-O8G-EVO-V2), **không phải BOM xác nhận trên bản CMP**.
- Đường net trong CAD là `CAD_ONLY`: có đường logic trên bản vẽ, **chưa chứng minh** đồng kim/vía/lãnh capacitor thực sự lắp trên card CMP.
- Ảnh prior report cho biết J1 DP và J5 DVI có connector vật lý, J10 HDMI chỉ footprint — nhưng đây là quan sát hình ảnh, chưa đo continuity từng đường.

## 5. Verdict theo cổng

- **DP (J1):** Chuỗi lane endpoint đầy đủ ở mức GenCAD (J1 → C47 → G1). Sideband AUX/HPD qua IC đa chân chưa xác định. **Không thể kết luận routing thực tốt chỉ từ CAD.** Đường là `CAD_ONLY`.
- **DVI (J5):** Chuỗi lane đầy đủ ở mức GenCAD (J5 → C1273 → G1). HPD qua resistor R97/R101. DDC qua U502 (IC). **CAD_ONLY**, chưa chứng minh tín hiệu thực.
- **HDMI (J10):** Chỉ footprint, chưa lắp connector → không dùng được nếu không lắp thêm.

## 6. Điều kiện cản trở (blocker) và bằng chứng bổ sung tối thiểu

| Điểm cản trở | Loại | Bằng chứng cần bổ sung |
|-------------|------|----------------------|
| Sideband DP AUX/HPD qua IC Q509/Q7/Q521 | CAD_ONLY + IC không xác định | Ảnh silkscreen macro xác định IC; đo continuity power-off |
| Sideband DVI DDC qua U502 | CAD_ONLY + IC không xác định | Xác định IC U502; đo continuity |
| Cứng capacitor AC-coupling (C47, C1273, C43, ...) | CAD_ONLY | Đo continuity/đo đợn power-off từng tụ |
| G1 strap pins (BM5/BK5/BJ5) | Tồn tại trong signal | Nối với T02/T03 (strap semantic) |

## 7. Tóm tắt (≤10 dòng)

1. GenCAD CG161P R2 parse trực tiếp: G1=GPU, J1=DP, J5=DVI, J10=HDMI (footprint).
2. DP lane IFPD_L0: J1 pin1 → C47 → G1 BM18 (AC-coupled) — CAD_ONLY.
3. DVI lane IFPA_L0: J5 pin2 → C1273 → G1 BG24 (AC-coupled) — CAD_ONLY.
4. Sideband AUX/HPD/DDC/PWR đi qua IC đa chân (Q509, Q521, Q7, U502, U1) — BLOCKED qua IC, refdes không xác định chức năng.
5. CAD là thiết kế GeForce, không phải BOM CMP — chưa chứng minh đồng kim/vía/lãnh trên card thật.
6. Ảnh prior: J1/J5 có connector vật lý, J10 HDMI không lắp.
7. Outputs: DISPLAY_ROUTE_MATRIX.csv, PCB_DISPLAY_REPORT.md, evidence.json.
8. Không có RECOVERY_VERIFIED cho DP/DVI; sideband blocker là UNKNOWN lớn nhất.

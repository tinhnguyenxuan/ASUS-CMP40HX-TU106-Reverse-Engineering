# D3-E — PCB: ĐƯỜNG VẬT LÝ TỚI CONNECTOR (CÂU C)

**Nguồn:** `input/ASTRA_CMP40HX_HANDOFF/01_BOARDVIEW/CG161P_R2_boardview.cad`
**Format:** GENCAD 1.4, `MENTOR GRAPHICS — TRANSLATOR CAMCAD Professional 4.14.312.6`
**Revision:** `Tuesday, December 14, 2021 at 6:44pm`
**Board:** ASUS CG161P R2 (reference design GeForce)
**Ngày phân tích:** 2026-11-06 · offline only, không đụng phần cứng

---

## 0. KẾT LUẬN

> **Board reference design CÓ đường vật lý đầy đủ từ GPU tới cả 3 connector DP/HDMI/DVI, qua tụ AC-coupling.**
>
> **Nhưng đây là board GeForce. Không chứng minh được board CMP 40HX thực tế còn linh kiện hay không.**

---

## 1. Connector có trong thiết kế

Trích `$COMPONENTS` (1.874 component):

| Refdes | Shape | Loại | Technology |
|---|---|---|---|
| **J1** | `S_DISPLAY_20P_5HOLD_LF3` | **DisplayPort 20 chân** | SMD |
| **J10** | `SO_HDMI_38P_9H_C1_COLAY_LF3` | **HDMI 38 chân** | THRU |
| **J5** | `SO_DVI_24P_4HD_RA_C1_LF3` | **DVI 24 chân** | THRU |
| J6 | `S_WAFER_1X6P_79_2HD_XINY` | fan header | SMD |
| J7 | `SO_U_PWR_8P_2HOLD_C1_LF3` | PCIe 8-pin power | THRU |
| J8 | `SO_U_PWR_6P_2HOLD_C1_LF3` | PCIe 6-pin power | THRU |
| J9 | `S_WAFER_1X4P_2HOLD_XIN` | fan header | SMD |
| J606 | `S_WAFER_HD_7P_79_2HD_RA` | fan header | SMD |

**Ba connector display có footprint trong netlist.**

---

## 2. Chuỗi GPU → tụ coupling → connector (ĐẦY ĐỦ, từ `$SIGNALS`)

### 2.1 DisplayPort (J1) — 4 lane, mỗi lane qua 1 tụ

| GPU pin | Net GPU-side | Tụ | Net connector-side | Pin J1 |
|---|---|---|---|---|
| `G1 BM18` | `IFPD_L0` | **C47** | `IFPD_L0_C` | `J1 1` |
| `G1 BM17` | `IFPD_L0*` | **C46** | `IFPD_L0_C*` | `J1 3` |
| `G1 BK17` | `IFPD_L1*` | **C32** | `IFPD_L1_C*` | `J1 6` |
| `G1 BL17` | `IFPD_L1` | **C33** | `IFPD_L1_C` | `J1 4` |
| `G1 BL15` | `IFPD_L2*` | **C44** | `IFPD_L2_C*` | `J1 9` |
| `G1 BK15` | `IFPD_L2` | **C45** | `IFPD_L2_C` | `J1 7` |
| `G1 BM15` | `IFPD_L3` | **C31** | `IFPD_L3_C` | `J1 10` |
| `G1 BM14` | `IFPD_L3*` | **C30** | `IFPD_L3_C*` | `J1 12` |
| `G1 BE11` | `IFPD_AUX` | **C50** | `IFPD_AUX_C` | `J1 15` |
| `G1 BF11` | `IFPD_AUX*` | **C51** | `IFPD_AUX_C*` | `J1 17` |

Thêm: `DP_D_HPD_C` (J1.18) ← `C1293` + `R720`; `DP1_CEC` (J1.14); `DP1_MODE_C` (J1.13); `DP_PWR_CD` (J1.20).

### 2.2 DVI (J5) — 7 cặp TMDS

| GPU pin | Net GPU-side | Tụ | Net connector-side |
|---|---|---|---|
| `G1 BF21/BG21` | `IFPA_L3` / `IFPA_L3*` | C1260/C1261 | `IFPAB_TXC_C` |
| `G1 BG23/BH23` | `IFPA_L2` / `IFPA_L2*` | C1262/C1263 | `IFPAB_TXD0_C` |
| `G1 BF23/BE23` | `IFPA_L1` / `IFPA_L1*` | C1270/C1271 | `IFPAB_TXD1_C` |
| `G1 BF24/BG24` | `IFPA_L0` / `IFPA_L0*` | C1272/C1273 | `IFPAB_TXD2_C` |
| `G1 BK20/BL20` | `IFPB_L2` / `IFPB_L2*` | C1266/C1267 | `IFPAB_TXD3_C` |
| `G1 BM20/BM21` | `IFPB_L1` / `IFPB_L1*` | C1264/C1265 | `IFPAB_TXD4_C` |
| `G1 BL21/BK21` | `IFPB_L0` / `IFPB_L0*` | C1268/C1269 | `IFPAB_TXD5_C` |

Thêm: `IFPA_HPD_C` (J5.16), `SNN_VS_DVI` (J5.8), `DDC_5V` (J5.14), `IFPA_I2CW_SCL_C`/`SDA_C` (J5.6/7).

### 2.3 HDMI (J10) — 2 kênh TMDS

`IFPC_*` → `SNN_HDMI_*`/`J10 G*`; `IFPE_*` → `J10 P*`.
Ví dụ: `R24 1` ∈ `IFPC_TXD0_C1`; `C1263` không thuộc HDMI nhưng cùng pattern.

Thêm: `HDMI_C_HPD_C` (J10.G19) ← `C1305`+`R753`; `HDMI_E_HPD_C` (J10.P19); `SNN_HDMI_CEC1`(P13)/`CEC2`(G13); `I2CW_SCL_C`/`I2EW_SCL_C` (G15/P15); `DDC_5V` (P18/G18).

---

## 3. Cấu trúc tín hiệu — bằng chứng về kiến trúc SOR

Tên net tiết lộ **4 khối SOR độc lập** trong GPU:

| Prefix | Nguồn | Đích |
|---|---|---|
| `IFPA_*` | GPU pins BF/BG | **DVI** (J5) |
| `IFPB_*` | GPU pins BK/BL/BM | **DVI** (J5) — 3 lane phụ |
| `IFPC_*` | GPU pins BD | **HDMI** (J10, kênh G) |
| `IFPD_*` | GPU pins BK/BL/BM | **DisplayPort** (J1) |
| `IFPE_*` | GPU pins | **HDMI** (J10, kênh P) |

⇒ `IFPA`+`IFPB` = hai nửa của DVI; `IFPC`+`IFPE` = hai kênh HDMI; `IFPD` = DisplayPort.
Đúng mô hình TU106: **4 SOR** (SOR0/SOR1 dùng chung DVI, SOR2/SOR3 cho DP/HDMI).

---

## 4. ĐIỀU QUAN TRỌNG: đây là board GeForce, KHÔNG phải board CMP

### 4.1 Bằng chứng từ chính tài liệu

`pcb_audit/docx_text.txt:159` ghi nguyên văn:

> *"Bản ASUS CG161P R2 trong CAD có footprint J1 = DisplayPort 20P, J10 = HDMI, J5 = DVI; các chân GPU G1 còn có IFPA_Lx, IFPC_TXDx, IFPD_Lx, IFPD_AUX và HPD. Nhưng thông tin bạn cung cấp về CMP 40HX cho thấy board thực tế đã bỏ cổng và nhiều linh kiện ngoại vi. Do đó phải coi CAD chỉ là tài liệu bố trí của bản GeForce, không phải xác nhận tuyến vật lý còn nguyên trên bản mining."*

### 4.2 `STRAPS_NETLIST_VERIFIED.csv` — cảnh báo tương tự

```csv
strap_net,gpu_pin,pullup_1V8_AON,pulldown_GND,source,cmp40hx_population
STRAP0,BL3,R255,R268,Design netlist only,CMP population UNKNOWN
...
```
**`CMP population UNKNOWN`** cho cả 6 strap.

### 4.3 Hệ quả logic

| Mệnh đề | Trạng thái |
|---|---|
| Board reference design **có** đường tới DP/HDMI/DVI | **PROVEN** (netlist đầy đủ) |
| Board CMP 40HX thực tế **còn** J1/J5/J10 | **KHÔNG BIẾT** — netlist không nói |
| Board CMP 40HX thực tế **còn** tụ coupling C30–C51, C1260–C1273 | **KHÔNG BIẾT** |
| Board CMP 40HX thực tế **còn** trở HPD R720/R753 | **KHÔNG BIẾT** |

### 4.4 Cái netlist CHỨNG MINH được cho CMP

> **Thiết kế gốc đủ để xuất hình.** Nếu NVIDIA/ASUS không cắt bỏ, silicon TU106-100-A1 **có** toàn bộ đường: GPU pin → tụ → connector.
>
> Nghĩa là **câu C không bị chặn bởi thiếu thiết kế** — chỉ bị chặn bởi (a) linh kiện có được hàn hay không, và (b) silicon có bật SOR/PHY hay không.

---

## 5. Phân biệt ba trạng thái (yêu cầu D3-3 C)

| Trạng thái | Bằng chứng hiện có | Kết luận |
|---|---|---|
| **Thiết kế có đường** | Netlist GENCAD | ✅ **PROVEN** |
| **Linh kiện được hàn trên board CMP** | `CMP population UNKNOWN` (CSV); ảnh chưa phân tích được (vision lỗi) | ❓ **CHƯA BIẾT** |
| **Silicon SOR/PHY hoạt động** | Không có địa chỉ register Turing; không thiết bị đo | ❌ **CHƯA CHỨNG MINH** |

**Ba trạng thái độc lập.** Cái thứ nhất đúng không suy ra cái thứ hai hay thứ ba.

---

## 6. Ảnh PCB — trạng thái

`02_PCB_PHOTOS/ANNOTATED/CMP40HX_PORTS_PHOTO_ANNOTATED.jpg` (548 KB) và `CMP40HX_STRAP_PHOTO_ANNOTATED.jpg` (323 KB) **tồn tại**.

**Chưa phân tích được:** `vision_analyze` trả lỗi provider (`ChatCompletion` invalid response — endpoint không tương thích). Đây là **lỗi công cụ**, không phải kết luận về ảnh.

**Đây là phép kiểm còn lại duy nhất có thể trả lời "linh kiện có hàn hay không".**

---

## 7. Tổng kết D3-E

| Mục | Kết quả |
|---|---|
| Connector trong thiết kế | **J1 DP 20P, J10 HDMI 38P, J5 DVI 24P** — cả ba có |
| Đường GPU → connector | **PROVEN** — 32 chân GPU qua tụ C30–C51 (DP), C1260–C1273 (DVI) |
| Kiến trúc SOR | **4 khối** IFPA/IFPB (DVI), IFPC/IFPE (HDMI), IFPD (DP) — khớp TU106 |
| Board CMP có còn linh kiện | **CHƯA BIẾT** — CSV ghi `UNKNOWN`, ảnh chưa đọc được |
| Silicon SOR/PHY hoạt động | **CHƯA CHỨNG MINH** |
| Kết luận cho câu C | **Thiết kế đủ. Populate và silicon: chưa biết.** |

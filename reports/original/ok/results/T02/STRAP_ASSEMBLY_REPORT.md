# T02 — Kiểm chứng lắp đặt strap (CG161P R2 / CMP 40HX)

Ngày: 2026-11-05. Làm lại từ đầu, tự chạy tuần tự, không subagent. Không SSH, không can thiệp card.

## Input đã đọc trực tiếp
- `01_BOARDVIEW/CG161P_R2_boardview.cad` (SHA-256 `7338ccead9423c8ddd61f5c1e4f0147d95b3c6da5af3e9bae0a20fbcfab6264d`, đối chiếu CHECKSUMS)
- `01_BOARDVIEW/STRAPS_NETLIST_VERIFIED.csv`
- `06_PRIOR_REPORTS/CMP40HX_PHOTO_VS_CG161P_PHASE_REPORT.md`
- Ảnh: `02_PCB_PHOTOS/HIRES_ROI/` (strap_top_highres.jpg, strap_bottom_highres.jpg, strap_crop_original.jpg, strap_all_highres.jpg), `02_PCB_PHOTOS/PHONE_PREVIEWS/`

## Phương pháp
1. Trích netlist STRAP0-5 từ CAD trực tiếp (không lấy CSV làm đáp án).
2. Phân loại 12 footprint POPULATED / DNP / UNCERTAIN.
3. Không suy trị số trở từ kích thước/màu; không chuyển có/không linh kiện thành mức latch H/L nếu thiếu ngưỡng.
4. Chuyển yêu cầu giải nghĩa strap→PCI class sang T03.

## 1. Netlist strap từ CAD (xem trực tiếp, 6/6)

| Strap | Net | GPU pin | Pull-up (→1V8_AON) | Pull-down (→GND) |
|-------|-----|---------|-------------------|------------------|
| STRAP0 | STRAP0 | BL3 | R255 | R268 |
| STRAP1 | STRAP1 | BL4 | R257 | R269 |
| STRAP2 | STRAP2 | BM4 | R256 | R263 |
| STRAP3 | STRAP3 | BM5 | R258 | R261 |
| STRAP4 | STRAP4 | BK5 | R249 | R264 |
| STRAP5 | STRAP5 | BJ5 | R250 | R265 |

Mỗi net là cấu trúc 2 điện trở nối tiếp qua node STRAP (G1 pin ← R_pullup pin2, R_pulldown pin1 → GND). Xác minh trực tiếp từ `$SIGNALS` STRAP0-5 (absolute lines 38063-38098).

## 2. Dân số 12 footprint (từ ảnh prior report + CAD)

| Strap | Pull-up | Trạng thái | Pull-down | Trạng thái | Nguồn |
|-------|---------|-----------|-----------|-----------|-------|
| STRAP0 | R255 | UNCERTAIN | R268 | UNCERTAIN | CAD chỉ; ảnh chưa assess |
| STRAP1 | R257 | UNCERTAIN | R269 | UNCERTAIN | CAD chỉ; ảnh chưa assess |
| STRAP2 | R256 | UNCERTAIN | R263 | UNCERTAIN | CAD chỉ; ảnh chưa assess |
| STRAP3 | R258 | DNP (không lắp) | R261 | POPULATED (có SMD) | Prior photo report, ảnh 1793813621675/1673, mốc Y1/G1 |
| STRAP4 | R249 | DNP (không lắp) | R264 | POPULATED (có SMD) | Prior photo report, ảnh 1793813621675/1673, mốc Y1/G1 |
| STRAP5 | R250 | DNP (không lắp) | R265 | POPULATED (có SMD) | Prior photo report, ảnh 1793813621675/1673, mốc Y1/G1 |

## 3. Kết luận

- **Netlist strap:** 6/6 khớp giữa CAD và CSV (VERIFIED). Mapping STRAP3=BM5, STRAP4=BK5, STRAP5=BJ5 xác minh trực tiếp từ CAD.
- **STRAP3/4/5:** pull-up **không lắp**, pull-down **có SMD** ⇒ xu hướng LOW. STRAP5:3 ≈ `000` (**INFERRED** từ dân số; không phải phép đo logic H/L, không phải giá trị PSTRAPS latch).
- **STRAP0/1/2:** UNKNOWN — chưa có assess ảnh; cần macro ảnh hoặc đo đồng hồ khi ngắt nguồn.
- **Cảnh báo:** Không suy STRAP3→VGA hoặc STRAP3→PCI class chỉ từ ảnh. STRAP5:3 có thể là field đa bit tuỳ SKU. Không hàn/lắp/đổi strap.

## 4. Điều kiện cản trở

| Điểm | Trạng thái | Bằng chứng cần bổ sung |
|------|-----------|----------------------|
| STRAP0/1/2 population | UNKNOWN | Macro ảnh strap vùng trên; đo continuity power-off |
| Mức latch hiệu dụng STRAP3/4/5 | UNKNOWN | Đọc PSTRAPS read-only với offset TU106 đã xác minh |
| Trị số điện trởstrap | UNKNOWN | Đo ohm khi ngắt nguồn (không làm trong R0) |

## 5. Tóm tắt (≤10 dòng)

1. Netlist strap 6/6 xác minh trực tiếp từ CAD (VERIFIED): STRAP0-5 ↔ G1 BL3/BL4/BM4/BM5/BK5/BJ5.
2. Mỗi strap có pull-up 1V8_AON + pull-down GND.
3. STRAP3/4/5: pull-up DNP, pull-down populated → xu hướng LOW (INFERRED từ ảnh prior, không đo logic).
4. STRAP0/1/2: UNKNOWN (chưa assess ảnh).
5. STRAP5:3 ≈ 000 theo dân số; không phải mức latch đo được.
6. Không kết luận STRAP3→PCI class từ ảnh.
7. Outputs: STRAP_12_FOOTPRINTS.csv, STRAP_ASSEMBLY_REPORT.md, evidence.json.

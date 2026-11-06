# T00 — INPUT_GAPS (redo từ đầu, chỉ từ nguồn chính trong package)

Ngày: 2026-11-05. Phạm vi: chỉ đọc artifact trong `input/ASTRA_CMP40HX_HANDOFF`, không SSH, không can thiệp card.

## Kiểm toàn vẹn package (lần làm lại)

`sha256sum -c ASTRA_CMP40HX_HANDOFF/CHECKSUMS.sha256` từ thư mục `input/` → **88/88 OK, 0 FAILED** (xem lại trực tiếp terminal). Checksum chỉ chứng minh toàn vẹn nội bộ package, **KHÔNG** chứng minh nguồn gốc / provenanance.

## Cấu trúc package (tái kiểm trực tiếp)

- `00_READ_FIRST/` — README, ASTRA_MASTER_PROMPT, DISPLAY_ENABLE_DECISION_TREE, EVIDENCE_CONTRADICTIONS, REFERENCES_AND_PROVENANCE, SESSION_SUMMARY
- `01_BOARDVIEW/` — CG161P_R2_boardview.cad, STRAPS_NETLIST_VERIFIED.csv, CMP40HX_Strap_Report.docx, CG161P_R2_STRAP_FOOTPRINTS_PHONE.png
- `02_PCB_PHOTOS/` — PHONE_PREVIEWS, ANNOTATED, HIRES_ROI (strap_top_highres.jpg, strap_bottom_highres.jpg)
- `03_VBIOS/` — CMP40HX_ORIGINAL_1MB.bin, cmp40hx_t4_derivative.bin
- `04_PHASE15_EXTRACTS/` — FUSE (fuse2.json, fuse_bitfields.csv, fuse_map.json, P0_FUSE.md, fuse_dump2.py, fuse_read.py), PCIE (pcie_map.json), PHASE15, TOOLS, TOPOLOGY, VBIOS
- `05_PHASE21_EXTRACTS/` — TARGET_LIVE_FINDINGS.md, FIRMWARE_PROVENANCE_REPORT.md, VBIOS_DISPLAY_ANALYSIS.md, GSP_CAPABILITY_GATES.md, GSP_DISPLAY_CONFIG_DATAFLOW.md, GSP_DISPLAY_OBJECT_FIELDS.md, evidence/
- `06_PRIOR_REPORTS/` — BAO_CAO_DAY_DU.md, BAO_CAO_TONG_HOP_PHASE15_20.md, CMP40HX_PCB_PHASE_CROSSCHECK.md, CMP40HX_PHOTO_VS_CG161P_PHASE_REPORT.md, CODEX_CMP40HX_HANDOFF.md

## GAP (thiếu dữ liệu, ghi rõ không bịa)

| GAP | Mục tiêu bị ảnh hưởng | Chi tiết |
|-----|----------------------|----------|
| GAP-1 | T04, T07 | Không có binary GSP đúng phiên bản runtime `615.71.09` trong package. Static analysis chỉ có `615.78.08`. Không được ánh xạ địa chỉ từ 615.78.08 sang 615.71.09. |
| GAP-2 | T05 | Không có ROM GeForce TU106 độc lập có provenance (RTX 2060 SUPER / RTX 2070) để đối chiếu DCB với CMP ROM. Chỉ có hai ROM CMP/derivative. |
| GAP-3 | T02, T03 | Ảnh strap HIRES_ROI thiếu độ phân giải để xác nhận chắc chắn điện trở 0402 lắp hay bỏ trống. Không có phép đo điện trở / continuity khi ngắt điện. |
| GAP-4 | T00, T04, T07 | Không có capture live mới có timestamp: `lspci -Dnn`, `setpci 08.L` (chỉ đọc), `nvidia-smi -q`, GPU UUID. Cần user phê duyệt (ngoài phạm vi offline). |
| GAP-5 | T04 | Provenance v15 nguyên bản (archive `cmp40hx_research_v15_final.tar.gz`) không có trong package; không tái tạo chuỗi provenance đầy đủ của fuse2.json. |
| GAP-6 | T04, T07 | Lệch phiên bản source tĩnh (615.78.08) vs runtime (615.71.09). Mọi claim DECODED từ source cần gắn nhãn "static 615.78.08". |
| GAP-7 | T01 | CAD là thiết kế GeForce CG161P R2, không phải BOM xác nhận trên bản CMP. Chưa đối chiếu từng tụ AC-coupling / sideband IC trên card thật. |

## Phân bổ tác dụng GAP

| Task | Bị ảnh hưởng |
|------|--------------|
| T04 | GAP-1, GAP-5, GAP-6 |
| T05 | GAP-2 |
| T06 | GAP-1 (phiên bản firmware ảnh hưởng 바닥 mask) |
| T07 | GAP-1 → NEEDS_INPUT |
| T01 | GAP-7 |
| T02, T03 | GAP-3 |
| T08, T09 | GAP-4 (triad chưa chốt) |

## Tóm tắt (≤10 dòng)

1. Package toàn vẹn 88/88 OK; chỉ chứng minh nội bộ, không phải nguồn gốc.
2. Đã đọc trực tiếp 6 file READ_FIRST và raw artifacts chính (fuse2.json, pcie_map.json, STRAPS CSV, TARGET_LIVE_FINDINGS).
3. Claim register T00 ghi 14 mệnh đề từ nguồn chính, không dẫn lại kết luận cũ.
4. GAP-1 (thiếu GSP 615.71.09) và GAP-2 (thiếu ROM GeForce đối chiếu) là blocker lớn nhất.
5. GAP-4 (capture live có timestamp) cần user phê duyệt trước khi thực hiện.
6. T00 hoàn tất; chưa tự chạy T01-T09.

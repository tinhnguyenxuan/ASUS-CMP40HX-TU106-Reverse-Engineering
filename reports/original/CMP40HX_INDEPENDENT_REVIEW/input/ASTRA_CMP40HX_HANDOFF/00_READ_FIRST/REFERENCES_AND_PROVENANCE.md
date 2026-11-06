# Nguồn trong gói và tài liệu tham khảo

## Primary user-supplied
- `01_BOARDVIEW/CG161P_R2_boardview.cad` — GenCAD 1.4, SHA256 `7338ccead9423c8ddd61f5c1e4f0147d95b3c6da5af3e9bae0a20fbcfab6264d`.
- `01_BOARDVIEW/Original_Boardview.rar` — RAR gốc do người dùng gửi.
- `02_PCB_PHOTOS/PHONE_PREVIEWS/*` — 18 ảnh CMP chính chủ, resize và bỏ metadata camera; **xem ảnh gốc nếu cần xác nhận chi tiết 0402**.
- `02_PCB_PHOTOS/ANNOTATED/*` — đánh dấu từ lượt phân tích trước, có thể định vị sai ở mức pad, dùng tham khảo.
- `03_VBIOS/CMP40HX_ORIGINAL_1MB.bin` — SHA256 `dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec`.
- `04_PHASE15_EXTRACTS/FUSE/fuse2.json` — dump cũ, raw `regs["3076"]=1` thuộc address `0x21C04`. Tất cả dữ liệu nguồn trong archive full có thể nằm ở v15.tar.gz.
- `05_PHASE21_EXTRACTS/*` — các file lọc từ `baocao.zip` của Codex, gồm đường driver/GSP, DCB và live findings.

## Secondary reports / prior AI analysis
- `01_BOARDVIEW/CMP40HX_Strap_Report.docx` — báo cáo CG161P boardview do người dùng cung cấp, CAD là GeForce RTX2060 SUPER V2, không phải BOM CMP.
- `06_PRIOR_REPORTS/BAO_CAO_DAY_DU.md` — báo cáo cũ có suy luận cứng về 128 cores và fuse=0; **không coi kết luận là đã được chứng minh**.
- `06_PRIOR_REPORTS/BAO_CAO_TONG_HOP_PHASE15_20.md` — tóm tắt và các kết luận bị bác bỏ.
- `06_PRIOR_REPORTS/CMP40HX_PCB_PHASE_CROSSCHECK.md`, `CMP40HX_PHOTO_VS_CG161P_PHASE_REPORT.md` — đối chiếu trước, nên kiểm tra lại bằng primary.

## External references to verify independently
- NVIDIA Turing architecture whitepaper: https://www.nvidia.com/content/dam/en-zz/Solutions/design-visualization/technologies/turing-architecture/NVIDIA-Turing-Architecture-Whitepaper.pdf
- EnvyTools PSTRAPS: https://github.com/envytools/envytools/blob/master/docs/hw/io/pstraps.rst
- NVIDIA open-gpu-kernel-modules: https://github.com/NVIDIA/open-gpu-kernel-modules
- Nouveau/Envytools source: https://github.com/envytools/envytools
- Cyridd CMP unlocker research: https://github.com/Cyridd/cmpunlocker
- TU106 board-level N18E examples referenced by original report: https://cdn.badcaps-static.com/pdfs/8a704080c1ebbb3be4c276aa77f62c93.pdf

Khẳng định trong secondary reports phải được xác minh bằng dữ liệu trong gói hoặc nguồn độc lập, không đơn thuần dẫn lại một AI.

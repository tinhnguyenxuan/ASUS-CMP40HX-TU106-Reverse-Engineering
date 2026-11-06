# PHASE16/TOPOLOGY_CONSUMER_SEARCH — Báo cáo tìm nguồn công khai tiêu thụ / định nghĩa bitfield cho các đọc topology TU106 lưu trữ

Mục tiêu: tìm trong nguồn công khai (NVIDIA open-gpu-kernel-modules tag 615.78.08) và trong nguồn đã lưu offline (/tmp/nvsrc, /tmp/envytools) các định nghĩa bitfield hoặc mã tiêu thụ ký hiệu cho năm đọc topology TU106 được trích trong báo lưu trữ BAO_CAO_CMP40HX_TU106.md:

- MMIO 0x00409604 (gpc_nr)
- MMIO 0x00502608 (tpc_nr)
- Biểu thức bước TPC_UNIT: 0x504000 + g*0x8000 + t*0x800
- Fuse base+0x650 (địa chỉ tuyệt đối 0x00021650)
- Fuse base+0xc1c (địa chỉ tuyệt đối 0x00021C1C)

Chế độ làm việc: chỉ đọc, không truy cập phần cứng, không đọc/ghi MMIO hoặc PCI-config, không thay đổi driver, không nạp/flash firmware, không khóa/chữ ký, không bypass, không brute force, không khai thác. Không tạo định nghĩa trường nào. Không coi header thế hệ khác là TU106 nếu không có chứng minh rõリア-theo-thế-hệ. Không giả định số TPC bằng nhau trên mỗi GPC.

## 1. Nguồn đã tra cứu (có URL/tag/hash xác định rõ)

| # | Nguồn | Đường dẫn / ref | Hash | Kết quả |
|---|-------|-----------------|------|---------|
| 1 | NVIDIA open-gpu-kernel-modules (github) | https://github.com/NVIDIA/open-gpu-kernel-modules.git, refs/tags/615.78.08 | tag object 4bfe30bb78e7364959e59c16cfefd88e8c14670e → commit 1a82fbfda8f321b056eb3568850f9316c5e465c5 (2026-10-07) | Không có hit nào cho 5 đọc trên (xem §2) |
| 2 | /tmp/nvsrc (bản lưu đã có) | /tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_fuse.h | f96f637c14732564911cd3211409a11b5dacd0ef27c5ad3df56e5d715d9fa30d | 2 thanh ghi không-topology; không có trường tại 0x650/0xc1c |
| 3 | /tmp/nvsrc (bản lưu đã có) | /tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_fault.h | 8410c458867a942f03358e94333ae274caa1a7adafca5bb4331f52500d855f50 | ID client sự cố (index), không phải số lượng engine |
| 4 | /tmp/envytools (rnndb) | /tmp/envytools/rnndb | — | Chỉ XML trước-Turing (g80/gf100); không có TU106; không có hit địa chỉ nào |
| 5 | Bản lưu làm việc | work_v15/MMIO/mmio.json (8782ce56...), fuse2.json (0e770041...), p5678.json (d004107a...) | xem findings.json | gpc_nr/tpc_nr/TPC_UNIT không có trong chụp 52 thanh ghi; nvidia-smi không có multiProcessorCount; giá trị fuse thô đã xác minh nhưng không có định nghĩa bitfield |

Lưu ý: bản sao /tmp/nvsrc của dev_fuse.h và dev_fault.h (tu102) bitwise giống hệt tệp tại tag 615.78.08 (cùng sha256) — nguồn đã lưu chính là phần của nguồn công khai này.

## 2. Kết quả tra cứu theo từng đọc

### 2.1 gpc_nr — MMIO 0x00409604
- Hit trong nguồn công khai: KHÔNG (không biểu tượng, không hằng địa chỉ) trên toàn cây checkout tag 615.78.08.
- Không có dev_top.h/dev_gr.h cho tu102/tu106 tại tag này.
- Giá trị lưu trữ 0x08040003 (low16 = 3) chỉ tồn tại trong văn bản BAO_CAO §3.1; thanh ghi không được chụp trong lưu ảnh MMIO (trang 1033 không chạm).
- Không có định nghĩa bitfield chung nào trong nguồn công khai gắn fuse+0xc1c = 0x38 (popcount 3) làm số GPC.
- **Phán định:** KHÔNG CÓ NGUỒNG CÔNG KHAI PHÙ HỢP — giá trị lưu trữ ≠ giá trị đã chụp/giai mã.

### 2.2 tpc_nr — MMIO 0x00502608
- Hit trong nguồn công khai: KHÔNG trên toàn cây checkout.
- Giá trị lưu trữ 0x00040005 (low16 = 5, TPC trong GPC0) chỉ trong văn bản BAO_CAO §3.1; thanh ghi không được chụp (trang 1282).
- bits 0-4 của fuse+0x650 = 0x4001F bằng 5, nhưng không có trường công khai nào đặt tên các bit này là TPC enable/count cho TU106.
- **Phán định:** KHÔNG CÁO NGUỒNG CÔNG KHAI PHÙ HỢP.

### 2.3 TPC_UNIT — 0x504000 + g*0x8000 + t*0x800
- Biểu thức bước chỉ tồn tại trong văn bản trích án BAO_CAO §3.2; không có header công khai nào định nghĩa TPC_UNIT base/stride.
- Không địa chỉ nào trong khoảng 0x00504000+ được chụp trong lưu ảnh MMIO.
- **Phán định:** KHÔNG CÓ NGUỒNG CÔNG KHAI PHÙ HỢP.

### 2.4 fuse base+0x650 (0x00021650)
- Giá trị thô 0x0004001F ĐÃ xác minh lại từ work_v15/RAW_DATA/fuse2.json regs["1616"].
- dev_fuse.h (tu102, tức cả /tmp/nvsrc và tag 615.78.08) chỉ định nghĩa 2 thanh ghi: NV_FUSE_OPT_NVDEC_DISABLE 0x00021378 (bits 2:0) và NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS 0x0002174C (bit 0). KHÔNG có trường tại 0x00021650.
- Không mã tiêu thụ fuse nào trong nguồn công khai đọc offset 0x650 để suy topology.
- **Phán định:** GIÁ TRỊ THÔ ĐÃ XÁC MINH, NGHĨA VỪA CHƯA BIẾT.

### 2.5 fuse base+0xc1c (0x00021C1C)
- Giá trị thô 0x00000038 ĐÃ xác minh lại từ fuse2.json regs["3100"].
- Không có trường công khai nào tại 0x00021C1C cho tu106.
- popcount(0x38) = 3 khớp gpc_nr lưu trữ nhưng là sự nhất quán giữa hai nguyên liệu thô, không phải giải mã bitfield (không có định nghĩa chung trong nguồn công khai).
- **Phán định:** GIÁ TRỊ THÔ ĐÃ XÁC MINH, NGHĨA VỪA CHƯA BIẾT.

## 3. Mã tiêu thụ liên kết (không phải MMIO — chỉ dùng làm bối cảnh, không phải giải mã)

Trong public source tag 615.78.08, duy nhất các chỗ lấy số GPC/TPC là giao diện điều khiển RM, đọc thông tin tĩnh từ firmware, KHÔNG đọc MMIO:

- src/nvidia/src/kernel/gpu/gr/kernel_graphics_manager.c:624/646/671 — đọc pGrInfo->infoList[NV2080_CTRL_GR_INFO_INDEX_LITTER_NUM_GPCS].data
- src/nvidia/src/kernel/gpu/gr/kernel_graphics.c:3646 (subdeviceCtrlCmdKGrGetNumTpcsForGpc_IMPL) — nvPopCount32(floorsweepingMasks.gpcMask) cho số GPC; mảng tpcCount[gpcId] theo từng GPC cho số TPC

Lưu ý quan trọng: nguồn công khai tự mô tả số TPC theo từng GPC (mảng index theo gpcId) — hỗ trợ quy tắc "không giả định số TPC bằng nhau trên mỗi GPC". Cả hai đều lấy từ thông tin tĩnh, không phải thanh ghi 0x00409604 / 0x00502608.

## 4. Điều khiển âm (negative control — BỊ LOẠI)

- src/common/inc/swref/published/blackwell/gb10b/dev_fuse.h: `NV_FUSE_STATUS_OPT_GPC 0x00820c1c` — hit duy nhất trên chuỗi "0xc1c". Đây là thanh ghi fuse STATUS của Blackwell GB10b, KHÔNG phải TU106, không ở fuse base 0x00021000, và nguồn không tuyên bố tương đương thế hệ. LOẠI — không dùng làm định nghĩa TU106.
- src/common/inc/swref/published/ampere/ga100/dev_top.h — dev_top.h chỉ có cho ampere/ga100 và blackwell/gb100, và chỉ chứa 7 #define về PTOP device info, KHÔNG có trường bitfield số GPC/TPC. Không thể thế thế cho TU106. dev_gr.h và dev_graph.h không tồn tại überhaupt tại tag này.

## 5. Kết luận

Tra cứu đã kết thúc trong giới hạn đã định (mã nguồn công khai tag 615.78.08, cây đã check out kín; /tmp/nvsrc; /tmp/envytools). KHÔNG TÌM THẤY định nghĩa bitfield công khai và KHÔNG TÌM THẤY mã tiêu thụ ký hiệu công khai cho bất kỳ đọc topology TU106 nào được trích lưu trữ: MMIO 0x00409604 (gpc_nr), MMIO 0x00502608 (tpc_nr), bước TPC_UNIT 0x504000+g*0x8000+t*0x800, fuse +0x650, fuse +0xc1c.

Các giá trị lưu trữ ("3 GPC, 5 TPC GPC0, 17 TPC, 34 SM, 64 ROP") vẫn là lời 주장 truy vấn lưu trữ (archived query claims) từ văn bản BAO_CAO; địa chỉ nguồn của chúng chưa bao giờ được chụp vào lưu ảnh đã lưu; chúng nhất quán với nhau và với popcount fuse (3 và 5) nhưng nhất quán ≠ giải mã. Những chỉ số topology này vẫn là UNKNOWN.

Điều duy nhất được CHỨNG THỰC là giá trị fuse thô: base+0x650 = 0x0004001F và base+0xc1c = 0x00000038 (xác minh từ fuse2.json đã lưu). Không có định nghĩa trường nào được tạo ra. Rằng rã còn thiếu: header bitfield fuse áp dụng TU106 hoặc header dev_top.h/dev_gr.h tu106 đặt tên các thanh ghi/offset này.

Các đầu ra đi kèm (thư mục này):
- extraction_commands.sh — lệnh trích xuất có thể tái lập
- findings.json — kết quả máy có nguồn gốc xác định
- REPORT.md — báo cáo này
- hashes.txt — băm các tệp đầu ra

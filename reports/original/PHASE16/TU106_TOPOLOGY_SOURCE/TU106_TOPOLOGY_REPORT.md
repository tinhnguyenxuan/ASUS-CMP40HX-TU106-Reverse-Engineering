# TU106 TOPOLOGY SOURCE — CMP 40HX (TU106-100-A1) GPC/TPC/SM/ROP

Mục tiêu: xác định, d'après bằng chứng offline đã lưu, cái gì có thể CHỨNG ĐƯỢC về topology GPC/TPC/SM/ROP của CMP 40HX (TU106). Không đục phần cứng, không ghi MMIO/PCI-config, không reload driver, không flash firmware. Chỉ dùng địa chỉ thực sự đã được dump.

## 1. Cách tái lập (reproducible)

```
cd /home/REDACTED_USER/codex-work
python3 PHASE16/TU106_TOPOLOGY_SOURCE/t16_topology_source.py
# -> PHASE16/TU106_TOPOLOGY_SOURCE/t16_topology_evidence.json
```

Script chỉ stdlib, chỉ đọc, băm toàn bộ输入, trích xuất fuse tại base+0x650 và base+0xc1c từ saved fuse2.json, kiểm tra MMIO snapshot (52 thanh ghi), kiểm tra nvidia-smi log đã lưu, kiểm tra header công khai /tmp/nvsrc/.../turing/tu102. Không đổi file cũ nào.

## 2. Nguyên liệu đã băm (sha256)

| file | vai trò | bytes | sha256 |
|------|---------|-------|--------|
| work_v15/RAW_DATA/fuse2.json | archived fuse array dump, base 0x21000 | 55233 | 0e770041019aa3e4ac25733429589867a03c5542e83bc89f6937878c6e5c4ecc |
| work_v15/RAW_DATA/p5678.json | saved NVML / nvidia-smi -q query archive | 17350 | d004107aae6356cb7849c2ac77f3504aaac38393214ad70419e523f7eefca165 |
| work_v15/TOPOLOGY/silicon_topology.json | saved NVML sm_count fragment | 4694 | 1364dbb89eb9054b8d875a114fe4a40ffc0769d6df83bc996e93bfba236d23ee |
| work_v15/MMIO/mmio.json | saved MMIO snapshot (52 thanh ghi) | 18248 | 8782ce5628383a19d73121396c4032f9f67f6275c0c897455ea1c5913c61e0b8 |
| work_v15/MMIO/registers_turing.json | saved turing register namespace | 14974 | a7e084bcb153e8413927843b77b3dab89fd113bff4c77b5a4de17480961b91a9 |
| PHASE16/ENGINE_INTERFACES/findings.json | archived coordinator findings (BAO_CAO claims) | 27911 | 832ab402f235dc6da098a1fc4fa4f8c6020973e2f894685aa42835f14826570b |
| /tmp/BAO_CAO_CMP40HX_TU106.md | archived primary technical report (nguồn của lời 주장 3/17/34) | 13636 | aa43bb2dd7fe83b9c2c889539a6e2cf9dba5f0832ce9d2abc94317f9daedb64e |
| /tmp/nvsrc/.../turing/tu102/dev_fuse.h | public Turing fuse definitions | 2150 | f96f637c14732564911cd3211409a11b5dacd0ef27c5ad3df56e5d715d9fa30d |
| /tmp/nvsrc/.../turing/tu102/dev_fault.h | public fault client IDs (chỉ số client, KHÔNG phải số engine) | — | — |

## 3. Giá trị fuse thô đã xác minh từ saved dump

| fuse offset | abs_addr | raw_value | popcount | nguồn |
|-------------|----------|-----------|----------|-------|
| base+0x650 | 0x021650 | 0x0004001F | 6 | fuse2.json "regs"["1616"] |
| base+0xc1c | 0x021C1C | 0x00000038 | 3 | fuse2.json "regs"["3100"] |

Hai giá trị này ĐÃ được đọc lại trực tiếp từ fuse2.json đã lưu. Chỉ là giá trị thô: dev_fuse.h (tu102, duy nhất áp dụng được cho TU106) KHÔNG có trường nào tại 0x650 hay 0xc1c, nên không thể giải mã thành mask/topology.

## 4. Phân loại bốn chỉ số topology

| chỉ số | Archived query claim (lời 주장 từ truy vấn đã lưu) | Register value (giá trị thanh ghi lưu trữ) | Actual decoded topology (giải mã thực từ bằng chứng đã lưu) | Đã chứng thực? |
|--------|---------------------------------------------------|-------------------------------------------|------------------------------------------------------------|----------------|
| GPC | 3 GPC — BAO_CAO §3.1: gpc_nr 0x00409604 = 0x08040003 (low16=3) | fuse+0xc1c = 0x38 (popcount 3), xác minh từ fuse2.json | UNKNOWN — không có bitfield định nghĩa 0x38 làm GPC mask; gpc_nr 0x00409604 (trang 1033) KHÔNG nằm trong saved MMIO snapshot | Không |
| TPC | 17 TPC (5+6+6 qua TPC_UNIT map probe); 5 TPC trong GPC0 — tpc_nr 0x00502608 = 0x00040005 | fuse+0x650 = 0x4001F (bits0-4 = 5), xác minh từ fuse2.json | UNKNOWN — bits0-4 của 0x4001F == 5 khớp giá trị tpc_nr lưu trữ nhưng không phải giải mã bitfield; 17 chia hết cho 3 sai, phân bố TPC trên 3 GPC không xác định được | Không |
| SM | 34 SM — BAO_CAO §3.3: 17 TPC × 2 == cudaGetDeviceProperties multiProcessorCount=34, CUDA cores=2176 | saved nvidia-smi log KHÔNG chứa multiProcessorCount/CUDA cores; silicon_topology.json sm_count = "NVIDIA CMP 40HX, 7.5" (mảnh vở, không phải 34) | UNKNOWN — 34 SM chỉ tồn tại trong lời 주장 BAO_CAO, không có trong log nvidia-smi đã lưu và không giải mã được từ thanh ghi nào đã dump | Không |
| ROP | 64 ROP — BAO_CAO §10: suy từ bảng so sánh SKU RTX 2070/TU106 full | không có thanh ghi ROP/L2/MC nào được dump trong snapshot 52 thanh ghi | UNKNOWN — 0% đo được trên card này; chỉ suy từ tài liệu SKU khác, không được dùng làm chứng thực TU106 của card này | Không |

Quy tắc áp dụng: không suy SKU/vai trò thiết bị từ device ID 10de:1f0b. Không coi thế hệ khác làm thay thế cho TU106.

## 5. Định nghĩa thanh ghi công khai đã kiểm tra (Turing/TU106)

- dev_fuse.h (tu102): chỉ định nghĩa 2 thanh ghi áp dụng được cho TU106 — NV_FUSE_OPT_NVDEC_DISABLE 0x21378 (bits2:0, đọc được 0) và NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS 0x2174C (bit0, đọc được 1). **Không có trường nào tại fuse+0x650 và fuse+0xc1c.**
- dev_fault.h (tu102): chỉ NV_PFAULT_CLIENT_GPC_TPCCS_* / GPC_T1_* — là ID client sự cố (index không gian), KHÔNG là số lượng engine.
- dev_top.h / dev_gr.h / dev_graph_h: **KHÔNG tồn tại** cho tu102/tu106 trong bộ ảnh /tmp/nvsrc. Chỉ có cho các thế hệ khác (ampere/ga100, blackwell/gb100, volta/gv100, pascal/gp100, rubin/gr100) — không được dùng-thế-thay cho TU106.
- TPC_UNIT = 0x504000 + g×0x8000 + t×0x800 (công thức stride từ BAO_CAO §3.2): chỉ có trong văn bản trích án, KHÔNG có trong header công khai đã lưu và KHÔNG có địa chỉ nào trong phạm vi này nằm trong saved MMIO snapshot.

## 6. Báo tuỳ chéo độc lập (raw datum vs raw datum)

1. fuse+0xc1c popcount(0x38)=3 vs gpc_nr存档 0x08040003 low16=3: giá trị 3 nhất quán, hai nguyên liệu thô độc lập, nhưng **không có định nghĩa bitfield chung** -> "nhất quán, chưa chứng thực". Tuỳ chéo này không nâng lần lượt lên thành giải mã.
2. fuse+0x650 bits0-4 = 5 vs tpc_nr存档 0x00040005 low16=5: tương tự, nhất quán chưa chứng thực.
3. 17 TPC vs 3 GPC: 17 % 3 != 0 -> phân bố TPC/GPC (5/6/6 được BAO_CAO tuyên bố) không thể kiểm chứng từ bằng chứng đã lưu; lời 주장 "GPC0 TPC5 trả poison" mâu thuẫn với giả định 3×6 đều đặn.
4. 17×2=34 SM vs multiProcessorCount=34: hai con số chỉ nằm trong văn bản BAO_CAO, none xuất hiện trong log nvidia-smi đã lưu và none trong thanh ghi đã dump -> hỗ trợ lẫn nhau trong văn bản trích án, không phải bằng chứng từ dữ liệu đã lưu.

## 7. Chưa giải quyết (unresolved) và capture cần thiết

| id | phần tử chưa giải quyết | lý do | capture còn thiếu |
|----|------------------------|-------|-------------------|
| U-TOP-GPC-DECODE | Số GPC và ý nghĩa fuse+0xc1c=0x38 | Không có dev_top.h/dev_gr.h cho TU106; dev_fuse.h không có trường tại 0xc1c; gpc_nr 0x00409604 không được dump | Đọc MMIO 0x00409604 + công khai header TU106 xác định bitfield gpc_nr/tpc_nr |
| U-TOP-TPC-DIST | Số TPC (17) và phân bố trên 3 GPC | tpc_nr 0x00502608 và bản đồ TPC_UNIT 0x504000+ không được dump; 17 không chia hết cho 3 | Đọc MMIO 0x00502608 và probe mỗi TPC unit 0x504000+g×0x8000+t×0x800 (+0x010/+0x100/+0x400) + định nghĩa header |
| U-TOP-SM-COUNT | Số SM (34), CUDA cores (2176) | log nvidia-smi đã lưu không có multiProcessorCount/CUDA cores; sm_count field là mảnh vở | Lưu toàn bộ log nvidia-smi -q / truy vấn NVML có multiProcessorCount và CUDA cores, hoặc dump thanh ghi số SM với định nghĩa áp dụng TU106 |
| U-TOP-ROP-COUNT | ROP (64), phân vùng L2, bộ điều khiển bộ nhớ | 0% đo được trên card này; không có thanh ghi L2/MC/ROP trong phạm vi 52 thanh ghi đã dump | Dump không gian MMIO L2/ROP/MC với định nghĩa áp dụng TU106, hoặc tài liệu cấu hình die TU106 chính thức |
| U-FUSE-0x650-0xC1C | Ý nghĩa fuse+0x650=0x4001F và 0xc1c=0x38 | Giá trị thô đã xác minh, nhưng không có định nghĩa bitfield công khai tại hai offset; suy popcount sang topology đã bị bác | Định nghĩa fuse bitfield áp dụng TU106 (hoặc mã RM tiêu thụ fuse) gắn tên hai offset này |

## 8. Phạm vi MMIO đã lưu (không phải quét đầy đủ)

- 52 thanh ghi đã dump, trang đã chạm: [0, 2, 3, 8, 16, 17, 20, 31, 132, 182] (theo nhãn "page" trong mmio.json).
- Mỗi trang trong tu06 chỉ lấy 4 u32 (16 byte) mẫu của 4 KiB -> **mẫu 16 byte/trang không phải quét MMIO đầy đủ**; chỉ các địa chỉ thực sự đã bị chạm mới được dùng làm input giải mã.
- gpc_nr (0x00409604), tpc_nr (0x00502608), TPC_UNIT (0x504000+) đều **không có** trong bộ 52 thanh ghi đã lưu.

## 9. Kết luận

Từ bằng chứng offline đã lưu, **không có chỉ số GPC/TPC/SM/ROP nào được giải mã thành topology**: snapshot MMIO không chứa thanh ghi topology, log nvidia-smi đã lưu không có multiProcessorCount, và bộ header công khai áp dụng TU106 (tu102, 37 tệp) không có dev_top.h/dev_gr.h và không có trường dev_fuse.h tại fuse+0x650/0xc1c.

Cái duy nhất **CHỨNG ĐƯỢC** là giá trị fuse thô: base+0x650 = 0x0004001F và base+0xc1c = 0x00000038 (xác minh lại từ fuse2.json đã lưu). Lời 주장 trích án "3 GPC, 17 TPC, 34 SM" là giá trị thanh ghi / truy vấn từ văn bản BAO_CAO, các địa chỉ nguồn của chúng chưa bao giờ được dump vào snapshot đã lưu; chúng nhất quán lẫn nhau và khớp popcount fuse, nhưng **nhất quán ≠ giải mã**. Mọi chỉ số topology vẫn là UNKNOWN với các capture còn thiếu như bảng mục 7.

Các đầu ra cũ (work_v15/PHASE16/*, PHASE16/ENGINE_INTERFACES/*) không bị sửa đổi.

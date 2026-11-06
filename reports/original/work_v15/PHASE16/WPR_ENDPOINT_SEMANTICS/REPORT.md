# WPR2 Endpoint Semantics — CMP 40HX (TU106) — Phase 16

## Tóm tắt
Numeric field extraction đã được thiết lập (E16-007, đã xác thực lại bởi verify_wpr.py):
- raw LO `NV_PFB_PRI_MMU_WPR2_ADDR_LO @ 0x1FA824 = 0x01F7E000`
- raw HI `NV_PFB_PRI_MMU_WPR2_ADDR_HI @ 0x1FA828 = 0x01FFEE00`
- trường `VAL[31:4]` theo đơn vị 4 KiB, `ALIGNMENT = 0xc`
- decode: `(raw & 0xFFFFFFF0) << 8` → base `0x1F7E00000`, HI decoded `0x1FFEE0000`
- kích thước: `0x080E0000` = 135,135,232 bytes = **128.875 MiB** (32,864 trang 4 KiB), nằm trong 8 GiB FB.
- Phép trừ raw `0x01FFEE00 - 0x01F7E000 = 0x80E00 (~0.50 MiB)` là **invalid** (đã retract trong SECURITY_ARCH_REVIEW).

Câu hỏi còn mở của review trước: **HI là inclusive end, exclusive end, last-page address, hay bound khác?** Review trước gán nhãn HI exclusive nhưng **không có bằng chứng consumer độc lập**. Bài này tra cứu nguồn off-line (/tmp/nvsrc + archived artifacts) để_answer và ghi lại mức độ tin cậy của mỗi bằng chứng.

## Nguồn đã tra cứu (offline, read-only)
- Cây nguồn đã lưu `/tmp/nvsrc` (thư mục common/, nvidia/, nvidia-modeset/), phiên bản tự khai báo **615.78.08** (`common/inc/nvUnixVersion.h`, NV_VERSION_STRING).
- Archived artifacts trong `work_v15/PHASE16/` (EVIDENCE_LEDGER.md E16-007, SECURITY_ARCH_REVIEW/, MEMORY_PCIE/).
- Không truy cập mạng; URL được trích dẫn trong E16-007 (`.../open-gpu-kernel-modules/580.95.05/.../tu102/dev_fb.h`) được coi là ngoại cảnh, **không verify được so với /tmp/nvsrc**, không dùng làm nguồn xuất bản chính xác.

## Bằng chứng tìm được (path / hash / line / kiến trúc)

| # | File | sha256 | Dòng | Kiến trúc | Nội dung liên quan | Mức độ |
|---|------|--------|------|-----------|-------------------|--------|
| 1 | `common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080fb.h` | `9e9783e9...88ce0` | 3065-3091 | RM ctrl ioctl interface: `NV2080_CTRL_CMD_FB_GET_WPR_REGION_INFO` (msg id 0x64) | Struct có `wpr2End`; comment dòng 3074-3079: `wpr1End`/`wpr2End` = "FB offset of the **end (exclusive)**" | Comment hợp đồng ABI, không phải bằng chứng consumer đọc registro |
| 2 | `nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta.h` | `f3b615a6...58fc5` | 32, 128, 42-55, 199 | GSP firmware WPR metadata (CPU-RM init, DMA đến FB, Booter khóa trong WPR2); Booter Turing→Ada | `gspFwWprEnd` là ranh giới trên của vùng WPR; vùng kế tiếp (PMU reservation) bắt đầu tại `gspFwWprEnd+frtsSize` (dòng 199) | Hỗ trợ exclusive-end (ranh giới, không phải trang cuối bao gồm) |
| 3 | `nvidia/interface/nvrm_registry.h` | `8de487f1...1556f` | 2792-2816 | RM registry regkeys | `RmGspWprEndMargin`: "increase the margin **after the end of WPR2**" | Margin đặt sau end ⇒ end được coi là ranh giới exclusive |
| 4 | `common/inc/swref/published/turing/tu102/dev_fb.h` | `8c824a87...2c6a9` | 39-44 | HW register header Turing (tu102; cùng khối PFB MMU WPR2 đã lưu cho TU106) | `WPR2_ADDR_LO 0x1FA824`, `WPR2_ADDR_HI 0x1FA828`, `_VAL 31:4`, `_ALIGNMENT 0xc` | Chỉ định nghĩa trường, **không có comment inclusivity** |
| 5 | `common/inc/swref/published/hopper/gh100/dev_fb.h` | `d1b0dfde...08f0eb` | 43-52 | HW header Hopper | `WPR2_ADDR_HI_VAL_INIT 0x0` (khi tắt, decoded HI = 0, nằm dưới base) | Thả thuận với exclusive-end, không phải bằng chứng |
| 6 | `common/inc/swref/published/blackwell/gb100/dev_hubmmu_base.h` | `2b2e4262...6b4b70` | 91-96 | HW header Blackwell HUBMMU | Cùng hình thức trường: `WPR2_ADDR_HI 0xa828`, VAL 31:4, alignment 0xc | Duy nhất qua thế hệ, không có ý nghĩa endpoint |
| 7 | `nvidia/arch/nvalloc/common/inc/nvrangetypes.h` | `84e8f17a...8fc5` | 63-76 | NvAlloc range types | Macro `NV_WITHIN_EXCLUSIVE_RANGE`, `NV_EMPTY_EXCLUSIVE_RANGE`... | Convention chung của codebase, không riêng WPR |

## Consumer code (đọc WPR2_ADDR_HI và phân nhánh theo inclusivity)
**Không tìm thấy** trong cây nguồn đã lưu:
- `grep WPR2_ADDR_HI/LO` → chỉ có header swref (turing, hopper, blackwell).
- `grep GetWprRegionInfo/wpr2End` → chỉ có `ctrl2080fb.h` và khai báo `subdeviceCtrlCmdFbGetWprRegionInfo_IMPL` trong `nvidia/generated/g_subdevice_nvoc.h`; **hàm body không có trong cây đã lưu**.
- Không có `.c/.cpp` nào trong `nvidia/` tiêu thụ registro này.

Kết quả: **bằng chứng consumer trực tiếp = CHƯA THIẾT LẬP**.

## Kết luận về HI
- Đọc tốt nhất (best-supported): **HI là exclusive upper bound** (ranh giới trên; byte tại HI KHÔNG thuộc WPR2). Cơ sở: comment hợp đồng ioctl (`wpr2End` = end exclusive), layout metadata GSP (`gspFwWprEnd` là ranh giới trên, vùng kế tiếp bắt đầu tại end), regkey margin đặt "after the end of WPR2".
- Mức tin cậy: **comment/contract cấp độ, không phải bằng chứng consumer**. Không có consumer code trong nguồn đã lưu để chứng minh độc lập.
- **Không hardcode exclusivity**: nếu yêu cầu bằng chứng consumer trực tiếp → đánh giá `UNKNOWN`. Các unknown còn giữ: consumer proof, WPR2 vs NVML Reserved overlap, áp dụng giá trị boot-stage `WPR2_lo 0x1FFFFE00` so với MMIO cuối, nguồn xuất bản chính xác (URL 580.95.05 chưa verify).

## Con đường分配 (alignment)
- WPR2 register căn 4 KiB (VAL[31:4] đơn vị 4 KiB; ALIGNMENT 0xc); base và decoded HI đều 4 KiB-aligned (nibble thấp = 0).
- Metadata GSP: `gspFwWprStart`/`gspFwWprEnd` căn 128K (không phải hw WPR2 reg).
- WPR2 chiếm 32,864 trang 4 KiB.

## WPR2 vs NVML Reserved 389 MiB overlap
- Không có bằng chứng trực tiếp: NVML Reserved là con số 389 MiB không có phạm vi địa chỉ trong artifact đã lưu.
- Quy tắc MEMORY_PCIE_REPORT.md §8: **không trừ mặc định WPR2 khỏi Reserved**; overlap = **UNKNOWN** (giữ nguyên).

## Unknowns được giữ
1. Consumer proof độc lập cho exclusivity của HI (không có consumer code trong nguồn đã lưu).
2. Nguồn xuất bản chính xác: /tmp/nvsrc tự khai báo 615.78.08; URL 580.95.05 trong E16-007 là ngoại cảnh, chưa verify.
3. Overlap WPR2 vs NVML Reserved 389 MiB.
4. Giá trị boot-stage `WPR2_lo = 0x1FFFFE00` vs giá trị MMIO cuối `0x01F7E000/0x01FFEE00`.

## Lưu ý bảo tồn
Không artifact gốc nào bị sửa. Tất cả đầu ra chỉ ghi vào `work_v15/PHASE16/WPR_ENDPOINT_SEMANTICS/` (REPORT.md, findings.json, SOURCE_SEARCH_LOG.md).

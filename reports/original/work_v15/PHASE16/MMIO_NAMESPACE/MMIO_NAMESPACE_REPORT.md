# MMIO_NAMESPACE_REPORT — CMP40HX/TU106 (TU10x family)

## 1. Mục tiêu và phạm vi

Kiểm toán lại 52 entry đã lưu trong `MMIO/mmio.json` (giá trị dump) đối với `MMIO/registers_turing.json` (danh sách từ nguồn header Turing) và các header tại `/tmp/nvsrc/common/inc/swref/published/turing/tu102/*.h`.

- Chỉ đọc file đã dump, **không đọc phần cứng**, không ghi/gủi BIOS, không gọi whole-GPU DONE.
- Output riêng: `PHASE16/MMIO_NAMESPACE/`. Artifact cũ ở `PHASE16/MMIO_SOURCE/` được **giữ nguyên không sửa** (xem mục Ghi chú thay thế).
- Không chạm checkpoint chung, binary/dump gốc.

## 2. Lỗi gốc (từ PHASE16/mmio_topology_coordinator_review.json)

CSV cũ dùng `NV_XVE_ID_VENDOR_NVIDIA = 0x10DE` (access `C---V`) như địa chỉ register, đọc trúng poison `0x5040badf` rồi gọi là `state=data`. Kết luận "52/52 matched source" **không hợp lệ**: input catalog lẫn giá trị enum/constant với địa chỉ register; sự khớp tên+địa chỉ với catalog lỗi không phải bằng chứng độc lập.

## 3. Phân loại macro từ header Turing

Mỗi `#define` được phân loại theo dạng giá trị, không coi mọi `#define` số hex là register:

| Loại macro | Dạng | Ví dụ |
|---|---|---|
| register/address | `0xADDR /* <access> */` | `NV_PFB_PRI_MMU_WPR2_ADDR_LO 0x001FA824 /* RW-4R */` |
| address range (block) | `0xHI:0xLO /* RW--D */` | `NV_PCFG 0x00088FFF:0x00088000 /* RW--D */` |
| field bitrange | `HI:LO /* ...F */` | `NV_XVE_ID_VENDOR 15:0 /* C--VF */` |
| enum/constant value | `0xVAL | <dec> /* ...V */` | `NV_XVE_ID_VENDOR_NVIDIA 0x000010DE /* C---V */` |
| indexed address expression | `(BASE+(i)*N)` | `NV_PFB_PRI_MMU_FAULT_BUFFER_GET(i) (0x00100E2C+(i)*20) /* RW-4A */` |

Quy tắc phân loại áp dụng: access kết thúc bằng `V` → constant value (không phải địa chỉ); access `C--4R` + tên `NV_CTRL_*` → control-space address; access null + `PCFG` → PCI config; access null + `BASE` → MMIO BAR0 base.

## 4. Tách namespace

| Namespace | Định nghĩa | Entry |
|---|---|---|
| MMIO_BAR0 | địa chỉ register trong cửa sổ BAR0 16 MiB, có access MMIO | 42 |
| MMIO_BAR0_BASE | địa chỉ base trong BAR0, access null (FBIF_BASE/GSP_BASE) | 3 |
| PCI_CONFIG | offset PCI config (`NV_PCFG_*_OFFSET`) | 1 |
| CONTROL_SPACE | địa chỉ control-interface NV_CTRL (access `C--4R`), không phải BAR0 MMIO | 3 |
| CONSTANT | giá trị enum/constant bị dùng nhầm làm địa chỉ register | 3 |

Tổng: 52 entry. Không còn entry "unknown" nào.

## 5. Kết quả kiểm toán 52 entry

### Confirmed MMIO_BAR0 register addresses (42)
Tất cả căn 4 byte, nằm trong BAR0, địa chỉ khớp source (header hash + dòng ghi kèm trong JSON), access dump khớp access source. Ví dụ: `NV_PFB_PRI_MMU_WPR2_ADDR_LO 0x1FA824`, `NV_PFB_PRI_MMU_L2TLB_ECC_UNCORRECTED_ERR_COUNT 0x100E78`, `NV_PLTCG_LTC0_LTS0_L2_CACHE_ECC_UNCORRECTED_ERR_COUNT 0x1404F8`, `NV_PSEC_FALCON_ENGINE 0x8403C0`, `NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE 0x30B0`, ... (xem đầy đủ trong `corrected_registers.csv` và `mmio_namespace_verified.json`).

### Constants mislabelled (3) — giá trị constant bị dùng làm địa chỉ register

| Tên | Giá trị (làm địa chỉ) | Access header | Vật chất thực sự | Trạng thái dump |
|---|---|---|---|---|
| `NV_XVE_ID_VENDOR_NVIDIA` | 0x10DE | `C---V` | vendor ID PCI | data (giá trị đọc được `0x5040BADF` = poison) |
| `NV_PBDMA_SIGNATURE_HW_VALID` | 0xFACE | `RW--V` | magic giá trị signature chờ đợi | data (giá trị đọc được `0x5040BADF` = poison) |
| `NV_PBDMA_ACQUIRE_TIMEOUT_MAN_MAX` | 0xFFFF | `RW--V` | hằng số tối đa | data |

### Misaligned addresses (3)
`0x10DE`, `0xFACE`, `0xFFFF` — không chia hết cho 4, xác nhận chúng không phải địa chỉ register MMIO thực (cùng 3 constant ở trên).

### Control-space addresses, không phải MMIO BAR0 (3)
`NV_CTRL_CPU_DOORBELL_VECTORID 0xB6687C`, `NV_CTRL_LEGACY_ENGINE_STALL_INTR_BASE_VECTORID 0xB66880`, `NV_CTRL_LEGACY_ENGINE_NONSTALL_INTR_BASE_VECTORID 0xB66884` (access `C--4R`, dev_ctrl.h). Đây là danh sách tên constant của control interface, không phải MMIO BAR0 register.

### PCI config (1)
`NV_PCFG_XVE_REGISTER_MAP_START_OFFSET 0x88000` (access null, dev_nv_pcfg_xve_regmap.h) — offset bản đồ register XVE trong PCI config, không phải MMIO BAR0.

### Unsupported expressions
Các macro dạng indexed expression tồn tại trong header (ví dụ `NV_PBUS_VBIOS_SCRATCH(i)`, `NV_PFB_PRI_MMU_FAULT_BUFFER_GET(i)`, `NV_PSEC_MAILBOX(i)`, `NV_PGSP_MAILBOX(i)`, `NV_PGSP_QUEUE_HEAD(i)`, …) nhưng **không entry nào trong 52 entry đã lưu dùng dạng indexed**, nên không có entry nào bị đánh dấu unsupported trong catalog flat. Chúng được loại khỏi xác thực địa chỉ bằng.

### Unknown
0 entry unknown. Số lượng GPC/TPC/SM/ROP vẫn UNKNOWN do không có header `dev_top.h`/`dev_graph.h`/`dev_gr.h` trong bản cục bộ — không đặt tên bằng popcount.

## 6. Bitfield extraction — chỉ trên giá trị register thực

- Trích bằng mask thật `(value >> lo) & ((1 << (hi-lo+1)) - 1)`, so sánh với giá trị bitfield đã lưu.
- Giá trị error-like/poison (`0xFFFFFFFF`, `0xBAD00100`, mẫu `0xBADFxxxx`, `0xBADE/xxxx`, `0xBADD/xxxx`) → **không có semantic field value đáng tin** (`bitfield_semantic = none_poison`).
  Entries bị ảnh hưởng: `NV_VIRTUAL_FUNCTION_PRIV_MMU_PAGE_FAULT_CTRL` (0x3070), `NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE` (0x30B0), `NV_VIRTUAL_FUNCTION_TIME_0/1`, `NV_VIRTUAL_FUNCTION_DOORBELL`, `NV_VIRTUAL_FUNCTION_ERR_CONT` (giá trị `0xBADF1100` / `0xBADF5040`).
- Hai entry có giá trị poison nhưng `state=data` lưu sai trạng thái: `NV_XVE_ID_VENDOR_NVIDIA` (0x10DE, đọc được `0x5040BADF`) và `NV_PBDMA_SIGNATURE_HW_VALID` (0xFACE, đọc được `0x5040BADF`).
- Giá trị enum không bao giờ được dùng làm bit offset; bitfield hi/lo lấy từ khai báo header.

## 7. Xác minh header hash/lines, source applicability

- 37 header tu102 đã được sha256 (toàn bộ trong `mmio_namespace_verified.json`, mục `header_hashes`).
- Mỗi entry trong JSON ghi `source_file`, `source_line`, `header_sha256`, `source_access`, `dump_access`, `access_match` (tất cả 52 entry: access dump khớp access source).
- Áp dụng nguồn: tu102 là định nghĩa cho TU10x/TU106; các họ header khác **không được dùng** làm định nghĩa TU106.

## 8. L2TLB ≠ L2 cache

| | Địa chỉ | Header | Ý nghĩa |
|---|---|---|---|
| L2TLB | `NV_PFB_PRI_MMU_L2TLB_ECC_UNCORRECTED_ERR_COUNT` 0x100E78 | dev_fb.h | ECC lỗi không sửa của MMU L2 TLB (TOTAL 15:0, UNIQUE 31:16) |
| L2 cache | `NV_PLTCG_LTC0_LTS0_L2_CACHE_ECC_UNCORRECTED_ERR_COUNT` 0x1404F8 | dev_ltc.h | ECC lỗi không sửa của LTC L2 cache |

Hai thanh ghi này **không được trộn lẫn**.

## 9. WPR2 decode (chỉ đọc dump, không phần cứng)

Theo `dev_fb.h`: VAL[31:4] << 12, 28 bit, ALIGNMENT = 12 (0xC), không dùng mask 20 bit.

| | Raw | Field (31:4) | Decoded address |
|---|---|---|---|
| `WPR2_ADDR_LO` 0x1FA824 | 0x01F7E000 (33021952) | 0x001F7E00 | 0x1F7E0000 |
| `WPR2_ADDR_HI` 0x1FA828 | 0x01FFEE00 (33549824) | 0x001FFEE0 | 0x1FFEE0000 |

Hiệu ran giới = 135135232 bytes = 128.875 MiB (khớp `data_audit.py`). Ran giới inclusive/exclusive = **UNKNOWN** (không có nguồn cục bộ định nghĩa ran giới cục bộ) — không gán vùng reserved từ phép trừ.

## 10. Giới hạn

- Chỉ phân tích file đã dump; không đọc phần cứng; không xác định được nguyên nhân vật lý của poison (bị xóa hardware, decode mapping, privilege filtering, hay gating).
- Sampling 16 từ/tọa độ trong các bản dump cũ giữ nguyên giới hạn mẫu (không giả có full 4 KiB).
- Không kết luận "toàn bộ GPU DONE".

## 11. Ghi chú thay thế artifact cũ (supersession)

Artifact cũ ở `PHASE16/MMIO_SOURCE/` (`mmio_topology_verify.py`, `_verified.json`, `register_fields.csv`, `page_inventory.csv`, `MMIO_TOPOLOGY_SOURCE_REPORT.md`, run log) được **giữ nguyên, không sửa**. Báo cáo và file trong `PHASE16/MMIO_NAMESPACE/` thay thế kết quả "52/52 matched source" của job `mmio_topology_v1` (đã kết thúc exit 0). Việc này không đụng checkpoint chung và không sửa binary/dump gốc.

## 12. File đầu ra

- `mmio_namespace_verify.py` — tool stdlib, chạy offline, exit 0
- `mmio_namespace_verify_run.log` — stdout + stderr + exit code của lần chạy thật
- `mmio_namespace_verified.json` — toàn bộ ánh xitched namespace, hash input/header, dòng nguồn, bitfield recompute
- `corrected_registers.csv` — 52 hàng, mỗi hàng có namespace/source_type/addr/line/hash/error_like/confirmed_mmio_bar0_address/bitfield_semantic
- `MMIO_NAMESPACE_REPORT.md` — báo cáo này

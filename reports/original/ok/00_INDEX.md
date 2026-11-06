# CMP 40HX — TOÀN BỘ NGHIÊN CỨU (phiên 2026-11-06)

**GPU:** NVIDIA CMP 40HX · TU106-100-A1 · `10DE:1F0B` · `0000:03:00.0`
**Driver/GSP:** 615.78.08 · **VBIOS:** 90.06.67.00.06 · `PMC_BOOT_0 = 0x166000A1`

## KẾT QUẢ CUỐI CÙNG

### Display — TẮT, nguyên nhân PROVEN
```
0x021C04 = 1
  → gpuFuseSupportsDisplay_GM107() = FALSE   (kern_gpu_gm107.c:67-72)
  → kern_disp.c:444  return NV_ERR_NOT_SUPPORTED
  → gpuRemoveMissingEngineClasses(ENG_KERNEL_DISPLAY)  (gpu.c:2237)
  → dmesg: "nvidia-drm: Cannot find any crtc or sizes"
```
Thêm hai tầng độc lập: VBIOS `NO_DISPLAY_SUBSYSTEM=1` + DCB `entry_count=0`;
`gpu.c` hard-code `case ENG_CLASS_DISP: return NV_FALSE`.

### TPC5 — tắt, KHÔNG có cờ defective, KHÔNG mở được
Ba nguồn độc lập cùng ra **17 TPC = 34 SM**:

| Nguồn | Đo |
|---|---|
| Fuse `STATUS_OPT_TPC_GPC0` `0x021C38` | `0x20` = bit 5 |
| RM `tpcMask[]` | `0x1F` / `0x3F` / `0x3F` |
| Hardware GR `GPC_UNIT(0,0x2608)` | `5` / `6` / `6` |

Hardware tự nhãn: poison `0xBADF1300` = `FECS_PRI_FLOORSWEEP`, không phải `ORPHAN`.
Phân loại: **`disabled-not-defective-marked`**.

### Khai thác live — 3 lỗ hổng, TPC5 vẫn không mở
| Lỗ hổng | Trạng thái |
|---|---|
| Module không chữ ký (`MODULE_SIG_FORCE` unset, lockdown `[none]`) | **LOADED** — ring0 |
| `/dev/mem` (`IO_STRICT_DEVMEM` unset) | root đọc/ghi physical |
| BAR0 `resource0` O_RDWR | OK, bỏ qua driver |

Thử thật: `0x021040=1` **STUCK** ✅ · `CTRL_OPT_TPC_GPC0 |= 0x20` **BOUNCE** ❌ ·
GR vẫn 5 TPC. ⇒ **latch ở hardware**, xác nhận độc lập trên TU106.
Reboot khôi phục hoàn toàn, card không hỏng.

## CẤU TRÚC

| Thư mục | Nội dung | md |
|---|---|---|
| `TPC5_LIVE/` | **Khai thác thực chiến — 3 lỗ hổng + TPC5 thử thật** | 1 |
| `TPC5_R1/` | Recovery R1 + sửa lỗi định danh register | 4 |
| `TPC5/` | Silicon health, 4 câu hỏi tách rời | 3 |
| `DISPLAY_D3/` | Object provenance, kernel path, PCB | 6 |
| `DISPLAY_D2/` | GSP display-state producer | 9 |
| `DISPLAY_D1/` | Fuse producer, VBIOS policy | 8 |
| `T00`–`T09`, `T1`–`T8` | Chuỗi tiền đề | 46 |
| `scripts/` | Script live + phân tích dùng trong phiên | — |

**84 báo cáo Markdown. Toàn bộ đọc read-only, trừ `TPC5_LIVE/` (có ghi register, đã khôi phục).**

## ĐỌC THEO CÂU HỎI

| Câu hỏi | File |
|---|---|
| Vì sao không có hình? | `results/DISPLAY_D1/D1_FINAL_VERDICT.md` |
| Gate nằm ở đâu? | `results/DISPLAY_D1/D1_FUSE_021C04_PRODUCER.md` |
| VBIOS khác GeForce? | `results/DISPLAY_D1/D1_VBIOS_DISPLAY_POLICY.md` |
| `+0x6EA` là gì? | `results/DISPLAY_D3/D3_GSP_6EA_SEMANTICS.md` |
| PCB có đường ra cổng? | `results/DISPLAY_D3/D3_E_PCB_PATH_EVIDENCE.md` |
| TPC5 mất vì sao? | `results/TPC5/TPC5_RECOVERABILITY_VERDICT.md` |
| Có cờ defective? | `results/TPC5/TPC5_DEFECT_REGISTER_EVIDENCE.md` |
| **Đã thử mở TPC5 thế nào?** | `results/TPC5_LIVE/EXPLOIT_LIVE_20261106.md` |
| Định danh register override? | `TPC5_OVERRIDE_REGISTER_IDENTITY.md` |

## BƯỚC TIẾP THEO (chưa làm)

| # | Việc | Chi phí |
|---|---|---|
| 1 | Đọc `0x021C38` trên **card CMP 40HX thứ hai** → phân hạng vs defective | 0, read-only |
| 2 | So RTX 2060 Super (TU106-410, cũng 34 SM) | 0, read-only |
| 3 | Đọc `CMP40HX_PORTS_PHOTO_ANNOTATED.jpg` → tầng populate PCB | 0 |

**#1 có sức phân biệt cao nhất.** Cùng `0x20` → phân hạng sản phẩm. Khác → defective ngẫu nhiên.

## GIỚI HẠN PHƯƠNG PHÁP

GSP-RM **stripped** (0 symbol) ⇒ mọi "hàm" suy từ prologue heuristic.
Không có CFG thật ⇒ `jalr` gián tiếp qua `*(reg+off)` tàng hình.
Không có địa chỉ `NV_PDISP_*`/`NV_SOR_*` cho Turing trong open source.
Không có đường host đọc bộ nhớ GSP.
**Turing không có header nào** cho `EN_SW_OVERRIDE`/`RECONFIG_OVERRIDE`.

Nguyên tắc đã giữ: "grep không thấy" **không** dùng để chứng minh "không tồn tại
đường gián tiếp". Kết luận phủ định chỉ dựa trên poison readback hoặc đọc thật.

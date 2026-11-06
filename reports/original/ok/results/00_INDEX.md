# CMP 40HX — BÁO CÁO NGHIÊN CỨU ĐỘC LẬP (INDEX)

**GPU:** NVIDIA CMP 40HX · TU106-100-A1 · `10DE:1F0B` · `0000:03:00.0`
**Driver:** 615.78.08 · **GSP-RM:** 615.78.08 · **VBIOS:** 90.06.67.00.06
**PMC_BOOT_0:** `0x166000A1`
**Đóng gói:** 2026-11-06

---

## TỔNG QUAN

122 file, 78 báo cáo Markdown, **10.829 dòng**. Toàn bộ phân tích offline +
đọc MMIO read-only. **0 lần ghi MMIO/BAR3/fuse, 0 patch driver/GSP/VBIOS, 0 reset GPU.**

Mọi kết luận đều truy được về: đường dẫn source + line/function, instruction bytes,
địa chỉ tuyệt đối, hoặc giá trị đọc trực tiếp từ phần cứng.

---

## BA KẾT LUẬN LỚN NHẤT

### 1. Display bị chặn bởi MỘT dòng code đọc MỘT fuse

```
BAR0 0x021C04 = 1
  → gpuFuseSupportsDisplay_GM107() = NV_FALSE        (kern_gpu_gm107.c:67-72)
  → kern_disp.c:444  return NV_ERR_NOT_SUPPORTED
  → gpuRemoveMissingEngineClasses(ENG_KERNEL_DISPLAY) (gpu.c:2237)
  → dmesg: "nvidia-drm: Cannot find any crtc or sizes"
```

Xác nhận thêm hai tầng độc lập: VBIOS `NO_DISPLAY_SUBSYSTEM=1` + DCB `entry_count=0`;
và `gpu.c` hard-code `case ENG_CLASS_DISP: return NV_FALSE`.

### 2. TPC5 bị tắt, KHÔNG có cờ defective, hardware tự nhãn FLOORSWEEP

Ba nguồn độc lập đều ra **17 TPC = 34 SM**:

| Nguồn | Đo |
|---|---|
| Fuse `STATUS_OPT_TPC_GPC0` `0x021C38` | `0x20` = bit 5 → tắt TPC5 |
| RM `tpcMask[]` | `0x1F` / `0x3F` / `0x3F` |
| Hardware GR `GPC_UNIT(g,0x2608)` | `5` / `6` / `6` |

**Phát hiện chính:** poison `0xBADF1300` tại TPC5 giải mã thành
`NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_PRI_FLOORSWEEP` (`gm107/dev_pri_ringstation_sys.h:36`),
trong khi GPC3/4/5 trả `0xBADF20xx` = `FECS_PRI_ORPHAN`.

⇒ Hardware phân biệt được **có mặt / floorswept / không tồn tại**. TPC5 thuộc nhóm
**floorswept, không phải orphan**.

### 3. `+0x6EA` trong GSP KHÔNG phải display gate (bác bỏ D1/D2)

- **21 writer** (11 `sb` + **10 `sh`**), không phải 11 — 10 site ghi 2 byte
  ⇒ là byte thấp của trường 16-bit, không phải field độc lập
- **495 reader** (`lbu`)
- **0/21 writer** dùng chuỗi object của handler (`0x160`→`0xE8`);
  **145/145 reader** thì dùng ⇒ hai tập rời nhau ⇒ **≥2 struct khác nhau**
- `RMDebugSetSMCMode` = **SMC/MIG mode** (compute), `ctrl2080internal.h:924-931` ghi
  nguyên văn *"Current MIG MODE"* — không phải display

---

## PHÂN LỚP BÁO CÁO

### Ấn bản mới nhất — nên đọc trước

| Thư mục | Nội dung | Dòng |
|---|---|---|
| **`TPC5_R1/`** | **Recovery phase R1 — gateway, slot +0x130, nguồn mask** | **428** |
| **`TPC5/`** | **Silicon health GPC0/TPC5 — 3 câu hỏi tách rời** | **720** |
| **`DISPLAY_D3/`** | Object provenance W5/W6, kernel internal path, PCB path | **1.369** |
| `DISPLAY_D2/` | GSP display-state producer, 11 write site, ABI control | 1.935 |
| `DISPLAY_D1/` | Fuse producer, GSP call graph, VBIOS policy, hypotheses | 2.083 |

### Chuỗi T (tiền đề, giữ nguyên để truy vết)

| Nhóm | Nội dung |
|---|---|
| `T00`–`T09` | Nền tảng: checksum, fuse/PCIe map, straps, SEC2, BIT/DCB parser, fuse base = 0 |
| `T5`–`T8` | Mask chain, GSP inventory, dispatch table 1182 entry, `physGpcMask` |

---

## FILE QUAN TRỌNG NHẤT THEO CÂU HỎI

| Câu hỏi | Đọc file |
|---|---|
| Vì sao không có hình? | `DISPLAY_D1/D1_FINAL_VERDICT.md` |
| Gate nằm ở đâu trong driver? | `DISPLAY_D1/D1_FUSE_021C04_PRODUCER.md` |
| VBIOS khác gì GeForce? | `DISPLAY_D1/D1_VBIOS_DISPLAY_POLICY.md` |
| `+0x6EA` là gì? | `DISPLAY_D3/D3_GSP_6EA_SEMANTICS.md` |
| Có gọi được control nội bộ không? | `DISPLAY_D3/D3_KERNEL_INTERNAL_QUERY_PATH.md` |
| PCB có đường ra cổng không? | `DISPLAY_D3/D3_E_PCB_PATH_EVIDENCE.md` |
| TPC5 mất vì sao? | `TPC5/TPC5_RECOVERABILITY_VERDICT.md` |
| Có đường bật TPC5 không? | `TPC5_R1/RECOVERY_GATE_VERDICT.md` |
| Slot +0x130 trỏ vào đâu? | `TPC5_R1/SLOT_0130_TARGET.md` |
| Bằng chứng defect register? | `TPC5/TPC5_DEFECT_REGISTER_EVIDENCE.md` |
| Fuse có đúng không? | `TPC5/TPC5_RAW_FUSE_COMPARISON.md` |

---

## BỐN TRẠNG THÁI — KHÔNG ĐƯỢC ĐÁNH ĐỒNG

| # | Trạng thái | Kết luận |
|---|---|---|
| ① | GPU render 3D | ✅ **CÓ** — 34 SM hoạt động, compute bình thường |
| ② | Driver nhận là display-class GPU | ❌ **KHÔNG** — `ENG_CLASS_DISP` bị loại |
| ③ | Display engine hoạt động | ❌ **KHÔNG** — preInit trả `NV_ERR_NOT_SUPPORTED` |
| ④ | DP/HDMI phát tín hiệu vật lý | ❓ **Thiết kế: CÓ đường** (netlist đầy đủ) · **Populate: CHƯA BIẾT** · **Silicon: CHƯA CHỨNG MINH** |

---

## PHÂN LOẠI TPC5 — BỐN CÂU TÁCH RỜI

| Câu | Trả lời | Mức |
|---|---|---|
| **Fuse tắt TPC5?** | **CÓ** | ✅ PROVEN — ba nguồn khớp |
| **Defective marked?** | **KHÔNG tìm thấy cờ** | ⚠️ `disabled-not-defective-marked` |
| **Silicon chạy được?** | **CHƯA BIẾT** | ❌ không kiểm được mà không bật |
| **Bật an toàn?** | **KHÔNG có cách đã chứng minh** | ❌ điều kiện cần thoả, điều kiện đủ chưa ai chứng minh |

**Fuse hiệu lực tắt = PROVEN. Raw OTP bất biến = CHƯA CHỨNG MINH.** Ba khả năng
chưa loại trừ: raw OTP / shadow register / devinit-SEC2 ghi.

---

## GIỚI HẠN PHƯƠNG PHÁP — NÊU THẲNG

Đây là giới hạn đã xác định chính xác, không phải thiếu sót:

- GSP-RM **stripped**: 0 symbol, 0 `.symtab` ⇒ mọi "hàm" suy từ prologue heuristic
  (**46.510** prologue thật)
- Không có CFG thật ⇒ `jalr` gián tiếp qua `*(reg+off)` là tàng hình
- Không có địa chỉ register `NV_PDISP_*`/`NV_SOR_*` cho Turing trong open source
  (`swref/published/turing/tu102/` chỉ 37 file, không có `dev_disp.h`)
- Không có đường host đọc bộ nhớ GSP
- Control `0x20800A4B` bị `RMCTRL_FLAGS_INTERNAL` chặn — **5 lớp**, `CAP_SYS_ADMIN`
  không đủ

**Nguyên tắc đã giữ:** "grep không thấy" **không** được dùng để chứng minh
"không tồn tại đường dữ liệu gián tiếp". Kết luận phủ định chỉ dựa trên
**poison readback** hoặc **đọc register thật**.

---

## CÁC GIAI ĐOẠN SAU

| # | Việc | Trả lời | Chi phí |
|---|---|---|---|
| 1 | Đọc `0x021C38` trên **card CMP 40HX thứ hai** | Phân hạng vs defective | thấp, read-only |
| 2 | So RTX 2060 Super (TU106-410, cũng 34 SM) | 34 SM có phải chuẩn SKU | thấp, read-only |
| 3 | Đọc ảnh `CMP40HX_PORTS_PHOTO_ANNOTATED.jpg` | Populate tầng PCB | 0 |

**Việc #1 là phép kiểm rẻ nhất có sức phân biệt cao nhất cho TPC5.**

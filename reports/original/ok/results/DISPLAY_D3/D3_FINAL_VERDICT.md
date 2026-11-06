# D3 — FINAL VERDICT

**GPU:** CMP 40HX, TU106-100-A1, `10DE:1F0B`, BDF `0000:03:00.0`
**Firmware:** GSP-RM 615.78.08 · ELF `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85`
**Source RM:** `615.78.08` @ `1a82fbfda8f321b056eb3568850f9316c5e465c5`
**Ngày:** 2026-11-06 · offline only · 0 ghi MMIO/BAR3/fuse, 0 patch, 0 flash

---

## 1. BA KẾT LUẬN CHÍNH CỦA D3

### ① `+0x6EA` KHÔNG phải display gate — và D1/D2 đã hiểu sai về nó

| Sự thật | Bằng chứng |
|---|---|
| Có **21 writer**, không phải 11 | 11 `sb` + **10 `sh`** tại 9+ hàm khác nhau |
| Có **495 reader** (`lbu`) | quét toàn ELF |
| **10 writer ghi 2 byte** (`sh`) | ⇒ không phải field độc lập 1 byte, mà là **byte thấp của trường 16-bit** tại `0x6EA–0x6EB` |
| **0/21 writer** dùng chuỗi object của handler (`0x160`→`0xE8`) | 8 site `sh` ghi cùng encoding `23 95 d5 6e` |
| **145/145 reader** trong hàm có chuỗi handler dùng đúng chuỗi đó | 1.252 hàm có chuỗi này |
| Hai tập **rời nhau hoàn toàn** | ⇒ offset `0x6EA` xuất hiện trong **≥2 struct khác nhau** |

⇒ **`0x6EA` là một offset, không phải một field. Ngữ nghĩa: UNKNOWN.**

### ② W5/W6 không vận hành trên object của handler

- `a0` của W5 (`0x5306D20`) **không bị ghi lại** trong 3096 B ⇒ cùng một giá trị tại `0x5306D30` và `0x5306DE4` (**PROVEN**)
- W5 **không chạm** `+0x6A8` — chỉ 7 hàm trong toàn ELF chạm cả `0x6A8` và `0x6EA`, **W5 không nằm trong số đó**
- Hàm HAL init (`0x458E1CC`, 124 B) **không ghi** `+0x88`, `+0x90`, hay `+0x6EA` — nó chỉ đọc `*(u32)(obj+0x6A8)` rồi nhảy nhánh
- **Sửa lỗi transcription D2:** HAL slot `obj+0x88` = **`0x5232DE0`**, không phải `0x5233DE0`

### ③ `RMDebugSetSMCMode` là **SMC/MIG (compute)**, không phải display

| Bằng chứng | Nội dung |
|---|---|
| `ctrl2080internal.h:924-931` | *"NV2080_CTRL_CMD_INTERNAL_GPU_GET_SMC_MODE … **Current MIG MODE** of the GPU"* |
| `ctrl2080gpu.h:169-172` | `SMC_MODE_UNSUPPORTED / ENABLED / DISABLED / ENABLE_PENDING` |
| `kernel_mig_manager.c:4000` | `pKernelMIGManager->bMIGEnabled = (params.smcMode == ENABLED)` — **consumer duy nhất** |
| Blob registry `0x41346C0-0x4134710` | `RmMigCcConfig`, `EnableDebuggerInterface`, `RMDebugSetSMCMode`, `RMDebugSMCDynamicTpcFs` — **toàn bộ là compute/MIG** |
| Trên target (D2-G) | Key **không tồn tại** ⇒ W4 **không kích hoạt** |

⇒ D2 gọi W4 là *"debug override cho display state"* — **SAI về ngữ nghĩa**. Nó là override cho **SMC/MIG mode**.

---

## 2. BA CÂU HỎI — KHÔNG ĐÁNH ĐỒNG

| # | Câu hỏi | Trạng thái | Cơ sở |
|---|---|---|---|
| **A** | Vì sao host RM từ chối display? | **PROVEN** | `0x021C04=1` → `gpuFuseSupportsDisplay_GM107=FALSE` → `kern_disp.c:444` `NV_ERR_NOT_SUPPORTED` → `gpuRemoveMissingEngineClasses` (`gpu.c:2237`) → dmesg `Cannot find any crtc or sizes` |
| **B** | GSP có nhận diện Display IP trên CMP 40HX? | **CHƯA ĐO — không đo được read-only** | Handler `0x04B9F5CC` chưa chạy. Control `0x20800A4B` = `RMCTRL_FLAGS_INTERNAL`, 5 lớp chặn |
| **C** | PDISP/SOR/PHY hoạt động trên silicon + PCB? | **TÁCH LÀM 3** | **Thiết kế: PROVEN** — netlist GENCAD có đường GPU→tụ→J1/J5/J10. **Populate: CHƯA BIẾT** — `CMP population UNKNOWN`. **Silicon: CHƯA CHỨNG MINH** |

**A KHÔNG suy ra B. A KHÔNG suy ra C. B KHÔNG suy ra C.**

### 2.1 Chi tiết câu C sau D3-E

| Lớp | Trạng thái | Cơ sở |
|---|---|---|
| **Thiết kế** (board reference CG161P R2) | ✅ **PROVEN** | `$COMPONENTS`: J1=`S_DISPLAY_20P`, J10=`SO_HDMI_38P`, J5=`SO_DVI_24P`. `$SIGNALS`: `G1 BM18 → IFPD_L0 → C47 → IFPD_L0_C → J1 1` (và 31 chuỗi tương tự) |
| **Populate** (board CMP thực tế) | ❓ **CHƯA BIẾT** | `STRAPS_NETLIST_VERIFIED.csv` ghi `CMP population UNKNOWN`; ảnh PCB chưa đọc được (vision lỗi provider) |
| **Silicon** (SOR/PHY bật) | ❌ **CHƯA CHỨNG MINH** | Không có địa chỉ register `NV_PDISP_*`/`NV_SOR_*` cho Turing; không thiết bị đo |

---

## 3. ĐƯỜNG NỘI BỘ — CÓ TỒN TẠI, KHÔNG CẦN BỎ QUYỀN

`kern_disp.c:435-465` là **caller duy nhất** của control `0x20800A4B` trong toàn bộ RM open:

```c
RM_API *pRmApi = GPU_GET_PHYSICAL_RMAPI(pGpu);
NvU32   hClient = pGpu->hInternalClient;      // client NV01_ROOT
NvU32   hSubdevice = pGpu->hInternalSubdevice;

if (!gpuFuseSupportsDisplay_HAL(pGpu))
   return NV_ERR_NOT_SUPPORTED;                // ★ GATE — dòng 444

status = pRmApi->Control(pRmApi, hClient, hSubdevice,
                         NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION,
                         &ctrlParams, sizeof(ctrlParams));
```

### 3.1 Tám tiền điều kiện — 7 ĐẠT, 1 TRƯỢT

| # | Tiền điều kiện | Trạng thái |
|---|---|---|
| 1 | GPU probe + `OBJGPU` tồn tại | ✅ |
| 2 | `bFullyConstructed = NV_TRUE` (`gpu.c:2202`) | ✅ |
| 3 | `pGpu->hInternalClient` cấp (`gpu.c:971`) | ✅ |
| 4 | `hInternalSubdevice` cấp | ✅ |
| 5 | `ENG_KERNEL_DISPLAY` trong init list | ✅ |
| 6 | `KernelDisplay` construct (`PDB_PROP_KDISP_IS_MISSING` chỉ cho VF) | ✅ |
| 7 | GSP sẵn sàng (`IS_FW_CLIENT`) | ✅ |
| **8** | **`gpuFuseSupportsDisplay_HAL(pGpu) == TRUE`** | ❌ **TRƯỢT** |

**Chuỗi đứt tại `kern_disp.c:444`, trước `pRmApi->Control(...)` ở dòng 447.**

### 3.2 Không có log để quan sát

Dòng 444 **không có `NV_PRINTF`**. `ResmanDebugLevel` trên target đã `0xFFFFFFFF` (max) nhưng không có gì để log. Khớp dmesg: `grep -iE "nvidia.*(disp|gsp|ipver)"` → 0 hit.

---

## 4. TÁC ĐỘNG LÊN CÁC KẾT LUẬN D1/D2

### 4.1 Điều D3 **BÁC BỎ**

| Kết luận cũ | Trạng thái mới | Cơ sở |
|---|---|---|
| "11 write site của `+0x6EA`" | **SAI — có 21** | 10 site `sh` bị bỏ sót |
| "`+0x6EA` là display gate / display state" | **SAI — ngữ nghĩa UNKNOWN** | 0/21 writer cùng object với handler |
| "W5/W6 decode `class` từ bảng phân loại của `obj+0x88`" | **SAI (D2 đã sửa)** | `obj+0x88` là con trỏ hàm; `class = 385` không khớp nhánh nào |
| "`obj+0x88` = `0x5233DE0`" | **SAI — là `0x5232DE0`** | tính lại từ raw bytes |
| "W4 là debug override cho display state" | **SAI — là SMC/MIG override** | `ctrl2080internal.h:924-931` ghi rõ "MIG MODE" |
| "`+0x6EA` do chipset HAL quyết định" | **KHÔNG CHỨNG MINH** | W5 không chạm `+0x6A8`; 0/21 writer trong chuỗi handler |

### 4.2 Điều D3 **CỦNG CỐ**

| Kết luận | Vẫn đúng |
|---|---|
| Gate fuse `0x021C04=1` → `kern_disp.c:444` là nguyên nhân gần | ✅ |
| Control `0x20800A4B` không gọi được từ userspace | ✅ (`RMCTRL_FLAGS_INTERNAL`) |
| `+0x6EA` không phải fuse, không phải VBIOS | ✅ (0 site đọc cửa sổ `0x21000`) |
| Control là read-only (1 store vào output) | ✅ |
| 8 site `sb zero` không mang thông tin vào | ✅ |
| W2 không thể tạo trạng thái | ✅ |
| W4 không kích hoạt trên target | ✅ (key không tồn tại) |

---

## 5. TRẠNG THÁI CHÍNH XÁC CỦA NGHIÊN CỨU

### 5.1 Đã chứng minh (PROVEN)

1. Gate display là `kern_disp.c:444`, đọc fuse `0x021C04=1` từ silicon.
2. Control `0x20800A4B` = `0x20800A4B | RMCTRL_FLAGS_INTERNAL`, chặn userspace.
3. Caller duy nhất của control là `kdispStatePreInitLocked_IMPL`, gọi sau gate fuse.
4. `+0x6EA` là byte thấp của trường 16-bit, 21 writer / 495 reader.
5. 0/21 writer dùng cùng chuỗi object với handler display.
6. `obj+0x88` của HAL branch = địa chỉ hàm `0x5232DE0`; `lhu 0x10` đọc byte lệnh.
7. `RMDebugSetSMCMode` = MIG mode, consumer duy nhất là `KernelMIGManager`.
8. W4 không kích hoạt trên target (key registry không tồn tại).

### 5.2 Chưa chứng minh được và **không thể** chứng minh bằng phương pháp hiện có

| # | Điều chưa biết | Vì sao không đo được |
|---|---|---|
| 1 | `ipVersion` thật trên CMP 40HX | Control bị `RMCTRL_FLAGS_INTERNAL`; gate fuse chặn trước |
| 2 | `+0x6EA` trên card này = 0 hay khác | Không có đường đọc; object chưa xác định |
| 3 | Ai gọi 6 hàm chứa writer | 0 call trực tiếp, 0 literal ptr; GSP stripped |
| 4 | `PDISP/SOR/PHY` có hoạt động | Không có địa chỉ register Turing; không thiết bị đo |
| 5 | PCB có linh kiện DP/HDMI | Ảnh có nhưng **chưa phân tích** |

### 5.3 Ranh giới của phương pháp — nêu thẳng

Đây **không phải thiếu sót**. Đây là giới hạn đã xác định chính xác:

- **Firmware stripped** (0 symbol, 0 `.symtab`) ⇒ mọi "hàm" là suy ra từ prologue heuristic (**46.510 prologue thật**, không phải 104.466 như D2 đếm sai lần đầu)
- **Không có CFG thật** ⇒ `jalr` gián tiếp qua `*(reg+off)` là tàng hình
- **Không có địa chỉ register display** cho Turing trong open source
- **Không có đường host đọc GSP memory**

---

## 6. KẾT LUẬN CUỐI

> **Display CMP 40HX bị chặn bởi một dòng code duy nhất đọc một fuse duy nhất.**
>
> `0x021C04 = 1` → `kern_disp.c:444` → `NV_ERR_NOT_SUPPORTED` → `KernelDisplay` bị huỷ → không CRTC → không tín hiệu.
>
> **`+0x6EA` không phải display gate.** Nó là một offset xuất hiện trong ≥2 struct khác nhau, 21 writer, 495 reader, ngữ nghĩa chưa xác định. D1/D2 đã dành lượng lớn công sức cho nó dựa trên giả định sai rằng nó là "display state".
>
> **Câu B (GSP có thấy Display IP?) và câu C (PHY/PCB hoạt động?) vẫn mở.**
> Câu B cần module kernel (rủi ro oops chưa loại trừ, ngoài phạm vi D3).
> Câu C cần ảnh PCB (miễn phí, **chưa làm**) và/hoặc thiết bị đo.

---

## 7. BƯỚC TIẾP THEO — XẾP THEO CHI PHÍ

| # | Việc | Trả lời | Chi phí | Trạng thái |
|---|---|---|---|---|
| **1** | Đọc `CMP40HX_PORTS_PHOTO_ANNOTATED.jpg` | C (PCB) | **0** | **CHƯA LÀM — nên làm ngay** |
| 2 | Tìm boardview trong `input/ASTRA_CMP40HX_HANDOFF/01_BOARDVIEW/` | C | 0 | chưa làm |
| 3 | Viết client NVML/thư viện khác thử đọc `ipVersion` gián tiếp | B | thấp | **đã chứng minh bất khả thi** (D2-H) |
| 4 | Module kernel chẩn đoán | B | **rủi ro oops** | cần quyết định riêng |
| 5 | Đo tín hiệu DP/HDMI bằng scope | C | thiết bị | không có |

**Việc #1 và #2 miễn phí và chưa làm. Đó là bước hợp lý tiếp theo trước khi cân nhắc #4.**

---

## 8. Artifact

| File | Nội dung |
|---|---|
| `D3_W5_W6_OBJECT_PROVENANCE.md` | CFG W5, nguồn `a0`, nguồn `a5`, layout, 21 writer, bác bỏ đồng nhất object |
| `D3_GSP_6EA_SEMANTICS.md` | Ngữ nghĩa `+0x6EA`, độ rộng truy cập, đối chiếu SMC/MIG |
| `D3_KERNEL_INTERNAL_QUERY_PATH.md` | `serverControl_ValidateCookie`, caller duy nhất, 8 tiền điều kiện, đánh giá chẩn đoán |
| `D3_DISPLAY_DIAGNOSTIC_FEASIBILITY.md` | Ba kênh chẩn đoán, ba câu hỏi tách biệt |
| `D3_FINAL_VERDICT.md` | File này |

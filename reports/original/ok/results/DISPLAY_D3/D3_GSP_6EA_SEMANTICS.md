# D3-B — NGỮ NGHĨA `+0x6EA` & ĐỐI CHIẾU SMC/MIG

**Firmware:** GSP-RM 615.78.08 · ELF `cd83bb04…3a2cfe85`
**Source RM:** `615.78.08` @ `1a82fbfd…`
**Ngày:** 2026-11-06 · offline only

---

## 0. KẾT LUẬN

> **`+0x6EA` KHÔNG phải display gate. Ngữ nghĩa: UNKNOWN.**
>
> `RMDebugSetSMCMode` là **SMC mode** — khái niệm **compute/MIG**, **không phải display**.
> D2 gọi nó là "debug override cho display state" — **SAI về ngữ nghĩa**. D3 sửa.

---

## 1. `0x6EA` là byte đầu của trường 16-bit, không phải field độc lập

### 1.1 Bằng chứng độ rộng truy cập

| Opcode | Số lượng | Nghĩa |
|---|---|---|
| `lbu ...,0x6ea(...)` | **495** | đọc 1 byte |
| `sb ...,0x6ea(...)` | **11** | ghi 1 byte |
| **`sh ...,0x6ea(...)`** | **10** | **ghi 2 byte** — `0x6EA` VÀ `0x6EB` |

10 site `sh`:

| Địa chỉ | Raw | Lệnh |
|---|---|---|
| `0x518BE8C` | `23 95 d5 6e` | `sh a3,0x6ea(a1)` |
| `0x518C52C` | `23 95 d5 6e` | `sh a3,0x6ea(a1)` |
| `0x518CC94` | `23 95 d5 6e` | `sh a3,0x6ea(a1)` |
| `0x518D36C` | `23 95 d5 6e` | `sh a3,0x6ea(a1)` |
| `0x518DA80` | `23 95 d5 6e` | `sh a3,0x6ea(a1)` |
| `0x518E4CC` | `23 95 d5 6e` | `sh a3,0x6ea(a1)` |
| `0x518ED24` | `23 95 d5 6e` | `sh a3,0x6ea(a1)` |
| `0x518F474` | `23 95 d5 6e` | `sh a3,0x6ea(a1)` |
| `0x5307034` | `23 15 05 6e` | `sh zero,0x6ea(a0)` |
| `0x5382BA0` | `23 95 07 6e` | `sh zero,0x6ea(a5)` |

**8 site đầu ghi CÙNG một giá trị `a3` bằng CÙNG một encoding** (`23 95 d5 6e`) trong **8 hàm khác nhau**.

### 1.2 Hệ quả

Nếu `0x6EA` là field độc lập 1 byte, không ai ghi 2 byte vào nó. Việc 10 site ghi `sh` chứng minh:

> **`0x6EA` là byte thấp của một trường 16-bit tại `0x6EA–0x6EB`.**

⇒ Gọi nó là "một cờ display" là **sai cấu trúc**.

---

## 2. Vùng flag liên tiếp — không phải field đơn

Object của W5 dùng **vùng liên tục** `0x6CD` → `0x785`:

```
0x6CD (sb)  0x6CE (sh)  0x6CF (sb)  0x6D1 (sb)  0x6DC (sh)
0x6DD  0x6DE  0x6DF  0x6E0  0x6E1  0x6E2(sh)  0x6E3
0x6E6  0x6E9  0x6EA(1B+2B)  0x6EB  0x6EC  0x6ED  0x6EE  0x6EF  0x6F0(sw)
0x6F1  0x6F2  0x6F3  0x6F4  0x6F5  0x6F6  0x6F7
0x712  0x71D  0x72C  0x731  0x732  0x734(sh)  0x735  0x736
0x738  0x73A  0x73C(sh)  0x73E  0x73F  0x740  0x741  0x742(sh)  0x745
0x74A  0x756  0x75C  0x763  0x76B  0x785
```

**Đây là một khối cấu hình/flag ~180 byte**, không phải vài cờ rời. `0x6EA` chỉ là **một byte trong khối đó**.

---

## 3. Đối chiếu `RMDebugSetSMCMode` — SMC = compute/MIG, KHÔNG phải display

### 3.1 Chuỗi và vị trí

```
0x041346D0: "EnableDebuggerInterface"
0x041346E8: "RMDebugSetSMCMode"
0x04134700: "RMDebugSMCDynamicTpcFs"
0x041346C0: "RmMigCcConfig"
```

Cùng blob registry key với `RmMigCcConfig` (MIG) và `RmDebugSMCDynamicTpcFs` (TPC floorsweeping động). **Toàn bộ nhóm là compute/MIG.**

### 3.2 Control tương ứng

`src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080internal.h:924-937`:

```c
/*
 * NV2080_CTRL_CMD_INTERNAL_GPU_GET_SMC_MODE
 *
 *     Current MIG MODE of the GPU. Values range NV2080_CTRL_GPU_INFO_GPU_SMC_MODE*
 */
#define NV2080_CTRL_CMD_INTERNAL_GPU_GET_SMC_MODE (0x20800a4c)
typedef struct NV2080_CTRL_INTERNAL_GPU_GET_SMC_MODE_PARAMS {
    NvU32 smcMode;
} NV2080_CTRL_INTERNAL_GPU_GET_SMC_MODE_PARAMS;
```

**Comment của NVIDIA ghi nguyên văn: "Current MIG MODE".**

Giá trị (`ctrl2080gpu.h:169-172`):
```c
#define NV2080_CTRL_GPU_INFO_GPU_SMC_MODE_UNSUPPORTED      (0x00000000U)
#define NV2080_CTRL_GPU_INFO_GPU_SMC_MODE_ENABLED          (0x00000001U)
#define NV2080_CTRL_GPU_INFO_GPU_SMC_MODE_DISABLED         (0x00000002U)
#define NV2080_CTRL_GPU_INFO_GPU_SMC_MODE_ENABLE_PENDING   (0x00000003U)
```

### 3.3 Consumer duy nhất trong RM: MIG manager

`src/nvidia/src/kernel/gpu/mig_mgr/kernel_mig_manager.c:3987-4000`:

```c
    NV_ASSERT_OR_RETURN(params.smcMode != NV2080_CTRL_GPU_INFO_GPU_SMC_MODE_UNSUPPORTED, ...);

    if ((params.smcMode == NV2080_CTRL_GPU_INFO_GPU_SMC_MODE_DISABLE_PENDING) ||
        (params.smcMode == NV2080_CTRL_GPU_INFO_GPU_SMC_MODE_ENABLE_PENDING))
    { ... }

    pKernelMIGManager->bMIGEnabled = (params.smcMode == NV2080_CTRL_GPU_INFO_GPU_SMC_MODE_ENABLED);
```

Và `subdevice_ctrl_gpu_kernel.c:256-288` — chỉ để **report** qua `NV2080_CTRL_GPU_INFO_INDEX_GPU_SMC_MODE` (index `0x2A`).

### 3.4 Kết luận đối chiếu

| Câu hỏi | Trả lời |
|---|---|
| `RMDebugSetSMCMode` là gì? | Registry debug key điều khiển **SMC mode** = **MIG mode** |
| SMC/MIG là compute hay display? | **COMPUTE** — chia GPU thành instance compute, không liên quan display pipeline |
| Consumer trong RM là ai? | **Chỉ `KernelMIGManager`** — `bMIGEnabled` |
| Có đường nào SMC → display? | **KHÔNG tìm thấy.** Không consumer nào của `smcMode` chạm display |
| D2 nói "W4 là debug override cho display state" | **SAI** — W4 clear một byte trong struct chưa xác định, dựa trên **SMC (compute) key** |

### 3.5 Mệnh đề đúng

> W4 (`0x4C95FDC`) clear `0x6EA` **khi** registry key `RMDebugSetSMCMode` tồn tại **và** bằng 0.
>
> Key này điều khiển **SMC/MIG mode** (compute), **không phải display**.
>
> ⇒ Nếu W4 chạy, nó **không** chứng minh bất cứ điều gì về display. Nó chỉ cho thấy `0x6EA` là byte trong một struct mà **SMC mode** cũng chạm tới.
>
> **Trên target key không tồn tại (D2-G) ⇒ W4 không chạy.**

---

## 4. Vì sao `0x6EA` không thể là display gate

Bốn điều kiện cần để gọi một field là "display gate", và trạng thái từng điều:

| # | Điều kiện | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1 | Có **consumer** đọc nó và quyết định display | **KHÔNG** | 495 `lbu` reader; không reader nào truy được tới display pipeline trong phân tích tĩnh |
| 2 | Consumer dùng **cùng object** với writer | **KHÔNG** | 0/21 writer, 145/145 reader dùng chuỗi `0x160→0xE8`. Hai tập rời nhau |
| 3 | Là **field độc lập** có ngữ nghĩa riêng | **KHÔNG** | 10 writer ghi 2 byte (`sh`) — nó là byte thấp của trường 16-bit |
| 4 | Có **writer trên đường thực thi đã chứng minh** | **KHÔNG** | 6 hàm chứa writer: 0 caller trực tiếp, 0 địa chỉ literal |

**Điều kiện 2 là nghiêm trọng nhất.** Handler `0x04B9F5CC` là consumer display **duy nhất** xác định được, và nó đọc `0x6EA` trên `*(*(pGpu+0x160)+0xE8)` — **không** phải `a0` của W5.

---

## 5. Chuỗi handler vs chuỗi writer — bằng chứng định lượng

### 5.1 Phép kiểm

Tìm mọi hàm có pattern: `ld X, 0x160(..)` **theo sau trong ≤5 lệnh** bởi `ld Y, 0xE8(X)`.

Kết quả: **1.252 hàm** dùng chuỗi object của handler.

Trong đó, **145 hàm** đọc `0x6EA`.

### 5.2 Đối chiếu 6 hàm chứa writer

| Hàm | Writer | Dùng chuỗi handler? |
|---|---|---|
| `0x4A127FC` | W1 | **KHÔNG** |
| `0x4B6F190` | W2 | **KHÔNG** |
| `0x4C89440` | W3 | **KHÔNG** |
| `0x4C95EFC` | W4 | **KHÔNG** |
| `0x5306D20` | W5/W6/W7/W8 + `sh` | **KHÔNG** |
| `0x5382B34` | W9/W10/W11 + `sh` | **KHÔNG** |
| `0x518BCC4`…`0x518F140` (8 hàm) | 8 × `sh` | **KHÔNG** |

**0 trên 21.**

### 5.3 Diễn giải

Hai tập **rời nhau hoàn toàn**:

- **Writers:** 21 site, 9+ hàm, **không** dùng `pGpu→0x160→0xE8`.
- **Readers:** 145 hàm, **tất cả** dùng `pGpu→0x160→0xE8`.

⇒ `0x6EA` xuất hiện trong **ít nhất hai struct khác nhau**, ở hai vùng nhớ khác nhau (một trong `pGpu`-derived static info, một trong object chưa rõ của W5).

---

## 6. Ba câu hỏi tách biệt (yêu cầu D3-3)

### A. Vì sao host RM từ chối display?

**ĐÃ BIẾT, PROVEN.**
```
0x021C04 = 0x00000001
   → gpuFuseSupportsDisplay_GM107() → NV_FALSE
   → kern_disp.c:444 → NV_ERR_NOT_SUPPORTED
   → KernelDisplay bị huỷ
   → nvidia-drm: "Cannot find any crtc or sizes"
```
Không liên quan `+0x6EA`. Không liên quan SMC. Không liên quan W4.

### B. GSP có nhận diện Display IP trên CMP 40HX không?

**CHƯA ĐO — và không đo được bằng read-only.**

Handler `0x04B9F5CC` chưa bao giờ chạy (host chặn trước khi gửi control `0x20800A4B`).
Control bị `RMCTRL_FLAGS_INTERNAL` chặn từ userspace (D2-H).
⇒ `ipVersion` thật: **UNKNOWN**.

### C. PDISP/SOR/PHY có thực sự hoạt động trên silicon và PCB không?

**CHƯA CHỨNG MINH.**

- Địa chỉ register `NV_PDISP_*` cho Turing **không có** trong open-gpu-kernel-modules
- PCB chưa kiểm (`CMP40HX_PORTS_PHOTO_ANNOTATED.jpg` chưa phân tích)
- Không có phép đo nào cho thấy PHY/SOR hoạt động hoặc hỏng

### 6.1 Không lấy A suy ra B hoặc C

| Suy luận sai | Vì sao sai |
|---|---|
| "A đúng ⇒ B đúng (GSP cũng không thấy display)" | A là gate host; B là gate GSP. Độc lập. Chưa đo B. |
| "A đúng ⇒ C đúng (hardware hỏng)" | A là fuse silicon; C là PHY/PCB. Fuse≠hỏng vật lý. |
| "B sai ⇒ C sai" | Không liên quan. |

**Ba mệnh đề độc lập, ba mức bằng chứng khác nhau.**

---

## 7. Trạng thái cuối của `+0x6EA` sau D3

| Thuộc tính | Giá trị | Mức bằng chứng |
|---|---|---|
| Vị trí | byte thấp của trường 16-bit tại `0x6EA–0x6EB` | **PROVEN** (10 `sh` writer) |
| Số writer | **21** (không phải 11) | **PROVEN** |
| Số reader | **495** `lbu` | **PROVEN** |
| Cùng object với handler | **KHÔNG** | **BÁC BỎ** (0/21 vs 145/145) |
| Là display gate | **KHÔNG ĐỦ ĐIỀU KIỆN** | 4/4 điều kiện trượt |
| Ngữ nghĩa | **UNKNOWN** | không có consumer display nào xác định được |
| Liên quan SMC/MIG | **CÓ THỂ** — W4 phụ thuộc key SMC | W4 không chạy trên target |

**Không được gọi `+0x6EA` là display gate trong bất kỳ kết luận nào tiếp theo.**

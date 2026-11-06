# D3-C — KERNEL INTERNAL CONTROL PATH

**Source RM:** `615.78.08` @ `1a82fbfda8f321b056eb3568850f9316c5e465c5`
**Ngày:** 2026-11-06 · đọc source, không chạy module, không patch

---

## 0. KẾT LUẬN

> **`serverControl_ValidateCookie` + `RMCTRL_FLAGS_INTERNAL` xác nhận đầy đủ: control `0x20800A4B` chỉ gọi được từ bên trong RM với `bInternal=TRUE`.**
>
> **Nhưng có một đường nội bộ hợp lệ — đúng đường RM đang dùng.** `kern_disp.c:435-465` gọi nó qua `pGpu->hInternalClient` / `hInternalSubdevice` với `GPU_GET_PHYSICAL_RMAPI(pGpu)`.
>
> **Đường đó không cần bỏ kiểm tra quyền.** Nó **đã** hợp lệ. Vấn đề không phải quyền — mà là **gate fuse chặn trước khi tới đó**.

---

## 1. Xác nhận `serverControl_ValidateCookie` (yêu cầu D3-2.1)

### 1.1 Vị trí và nội dung

`src/nvidia/src/kernel/rmapi/control.c:795-807`:

```c
        if (status != NV_OK)
        {
            NV_PRINTF(LEVEL_WARNING, "Control command 0x%x is not in allowlist\n", pRmCtrlParams->cmd);
            return status;
        }
    }

    if ((pRmCtrlExecuteCookie->ctrlFlags & RMCTRL_FLAGS_INTERNAL))
    {
        NvBool bInternalCall = pRmCtrlParams->bInternal;
        if (!bInternalCall)
            return NV_ERR_NOT_SUPPORTED;
    }
```

### 1.2 Định nghĩa cờ

`src/nvidia/inc/kernel/rmapi/control.h:236-243`:

```c
//
// If the INTERNAL flag is specified, the call will only be allowed
// to be issued from RM itself. Otherwise, NV_ERR_NOT_SUPPORTED is returned.
//
#define RMCTRL_FLAGS_INTERNAL                                 0x000000080
```

### 1.3 Giá trị flags của control

`src/nvidia/generated/g_subdevice_nvoc.c:6572-6584`:

```c
    {               /*  [166] */
        /*pFunc=*/      (void (*)(void)) &subdeviceCtrlCmdDisplayGetIpVersion__EXPORT,
        /*flags=*/      0xc0u,
        /*accessRight=*/0x0u,
        /*methodId=*/   0x20800a4bu,
        /*paramSize=*/  sizeof(NV2080_CTRL_INTERNAL_DISPLAY_GET_IP_VERSION_PARAMS),
```

`0xC0 = 0x40 (ROUTE_TO_PHYSICAL) | 0x80 (INTERNAL)`.

### 1.4 Nơi set `bInternal`

`control.c:385`:
```c
    bInternalRequest = pRmApi->bApiLockInternal || pRmApi->bGpuLockInternal;
```
`control.c:478`:
```c
    rmCtrlParams.bInternal = bInternalRequest;
```

**Hai cờ này chỉ TRUE khi gọi qua RMAPI interface lấy bằng `rmapiGetInterface(RMAPI_GPU_LOCK_INTERNAL)` hoặc `RMAPI_API_LOCK_INTERNAL`** — tức chỉ tồn tại trong tiến trình kernel.

⇒ **Xác nhận đầy đủ: userspace không gọi được.** (Khớp D2-H.)

---

## 2. Hàm host gọi `DISPLAY_GET_IP_VERSION` (yêu cầu D3-2.2)

### 2.1 Chỉ có MỘT caller trong toàn bộ RM open source

`grep -rn "NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION" src/nvidia/src/`:

| File | Dòng | Vai trò |
|---|---|---|
| `src/nvidia/src/kernel/gpu/disp/kern_disp.c` | 442 | khai báo params |
| `src/nvidia/src/kernel/gpu/disp/kern_disp.c` | 448 | **CALL SITE duy nhất** |
| `src/nvidia/src/kernel/gpu/arch/t23x/kern_gpu_t234d.c` | 139 | (chỉ trong danh sách, không gọi) |

### 2.2 Call site đầy đủ — `kern_disp.c:435-465`

```c
NV_STATUS
kdispStatePreInitLocked_IMPL(OBJGPU        *pGpu,
                             KernelDisplay *pKernelDisplay)
{
    NV_STATUS status;
    RM_API *pRmApi = GPU_GET_PHYSICAL_RMAPI(pGpu);       // ← interface nội bộ
    NvU32   hClient = pGpu->hInternalClient;              // ← client NV01_ROOT
    NvU32   hSubdevice = pGpu->hInternalSubdevice;
    NV2080_CTRL_INTERNAL_DISPLAY_GET_IP_VERSION_PARAMS ctrlParams;

    if (!gpuFuseSupportsDisplay_HAL(pGpu))
       return NV_ERR_NOT_SUPPORTED;                       // ★★★ GATE

    status = pRmApi->Control(pRmApi, hClient, hSubdevice,
                             NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION,
                             &ctrlParams, sizeof(ctrlParams));
    if (status != NV_OK)
    {
        NV_PRINTF(LEVEL_WARNING,
                  "Failed to read display IP version (FUSE disabled), status=0x%x\n",
                  status);
        return status;
    }

    // NOTE: KernelDisplay IpVersion _HAL functions can only be called after this point.
    status = gpuInitDispIpHal(pGpu, ctrlParams.ipVersion);

    kdispUpdatePdbAfterIpHalInit(pKernelDisplay);
    kdispAllocateCommonHandle(pGpu, pKernelDisplay);
    return status;
}
```

### 2.3 Ba đặc điểm của đường gọi nội bộ

1. **`GPU_GET_PHYSICAL_RMAPI(pGpu)`** — interface RM nội bộ, không phải user-facing
2. **`pGpu->hInternalClient`** — client `NV01_ROOT` tạo bởi `rmapiutilAllocClientAndDeviceHandles` (`rmapi_utils.c:60-66`)
3. **Không cần bỏ check** — `bInternal` sẽ TRUE vì interface này có lock internal

⇒ **Đây là đường gọi nội bộ hợp lệ, đã tồn tại, không cần sửa quyền truy cập.**

---

## 3. Tiền điều kiện để internal control thực thi (yêu cầu D3-2.3)

Xếp theo thứ tự thực thi, với trạng thái trên CMP 40HX:

| # | Tiền điều kiện | Cơ sở | Trạng thái CMP 40HX |
|---|---|---|---|
| 1 | **GPU được probe và `OBJGPU` tồn tại** | `gpu.c:2229` trong `gpuStatePreInit` | ✅ **ĐẠT** — `nvidia-smi` chạy, `nvidia-drm` nạp |
| 2 | **`bFullyConstructed = NV_TRUE`** | `gpu.c:2202` | ✅ **ĐẠT** — GPU construct xong |
| 3 | **`pGpu->hInternalClient` được cấp** | `gpu.c:971` `rmapiutilAllocClientAndDeviceHandles` | ✅ **ĐẠT** — log `GPU-0 allocated hInternalClient=0x...` (LEVEL_INFO, không in) |
| 4 | **`hInternalSubdevice` được cấp** | cùng | ✅ **ĐẠT** |
| 5 | **Engine descriptor `ENG_KERNEL_DISPLAY` có trong init list** | `gpuGetInitEngineDescriptors` | ✅ **ĐẠT** — `ENG_CLASS_KERNEL_DISPLAY → IS_FW_CLIENT = TRUE` (D1) |
| 6 | **`KernelDisplay` object được construct** | `PDB_PROP_KDISP_IS_MISSING` chỉ TRUE cho VF | ✅ **ĐẠT** (D1) |
| 7 | **GSP sẵn sàng** (`IS_FW_CLIENT`) | `nvidia-smi` báo GSP 615.78.08 | ✅ **ĐẠT** |
| 8 | **`gpuFuseSupportsDisplay_HAL(pGpu)` == TRUE** | `kern_disp.c:444` | ❌ **KHÔNG ĐẠT** — `0x021C04=1` ⇒ FALSE |

### 3.1 Nơi chuỗi đứt chính xác

`gpu.c:2229`:

```c
        rmStatus = gpuLoadFailurePathTest(pGpu, NV_REG_STR_GPU_LOAD_FAILURE_TEST_STAGE_PREINIT, curEngDescIdx, NV_FALSE);
        if (rmStatus == NV_OK)
        {
            engstateLogStateTransitionPre(pEngstate, ENGSTATE_STATE_PRE_INIT, &engTransitionData);
            rmStatus = engstateStatePreInit(pGpu, pEngstate);          // ← gọi pre-init
            engstateLogStateTransitionPost(pEngstate, ENGSTATE_STATE_PRE_INIT, &engTransitionData);
        }
        if (rmStatus == NV_ERR_NOT_SUPPORTED)
        {
            switch (curEngDescriptor)
            {
                case ENG_KERNEL_DISPLAY:
                    // On Displayless GPU's, Display Engine is not present. So, RM should not keep the display
                    // classes in GET_CLASSLIST. Hence removing the Display classes from the ClassDB
                    gpuRemoveMissingEngineClasses(pGpu, ENG_KERNEL_DISPLAY);
                    break;
```

⇒ **7/8 tiền điều kiện ĐẠT.** Chỉ tiền điều kiện #8 trượt, và nó là điều kiện **duy nhất** cần để control được gửi.

**Chuỗi đứt tại `kern_disp.c:444-445`, trước `pRmApi->Control(...)` ở dòng 447.**

---

## 4. Có đường nội bộ hợp lệ không cần bỏ quyền? (yêu cầu D3-2.4)

### 4.1 CÓ — và nó đã tồn tại

Đường đó là `kdispStatePreInitLocked_IMPL` → `pRmApi->Control(...)`.

**Nhưng nó nằm SAU gate fuse.** Muốn dùng nó để đo `ipVersion`, phải **vượt** `gpuFuseSupportsDisplay_HAL`, tức:

| Cách | Bản chất | Trong phạm vi D3? |
|---|---|---|
| Patch `kern_disp.c` bỏ dòng 444-445, rebuild module | **Sửa driver** | ❌ **BỊ CẤM** |
| Viết module kernel riêng gọi `pRmApi->Control` với `RMAPI_GPU_LOCK_INTERNAL` | Module mới | ❌ **BỊ CẤM** ("không sửa hoặc chạy module trên máy GPU") |
| Debug bằng `RmLogonRC` / registry để RM tự log | Không sửa code | ⚠️ Cần `RmLogonRC=1` + `ResmanDebugLevel` (đã = `0xFFFFFFFF` trên target) |
| Đọc GSP log buffer qua BAR0 | Đọc memory | ⚠️ Không có đường map từ host (D1) |

### 4.2 Kiểm tra nhanh: RM có log gì về gate này không?

`kern_disp.c:450-455` có `NV_PRINTF(LEVEL_WARNING, "Failed to read display IP version (FUSE disabled), status=0x%x\n", status)` — **nhưng chỉ trong nhánh `status != NV_OK` của lời gọi control**, tức **sau** gate fuse.

Dòng 444 `return NV_ERR_NOT_SUPPORTED` **không có log**.

⇒ **Không có log nào được phát ra.** Khớp dmesg quan sát được: `grep -iE "nvidia.*(disp|gsp|ipver)"` → 0 hit.

### 4.3 Registry để bật log — kiểm trên target

`/proc/driver/nvidia/params` (D2-G):
```
ResmanDebugLevel: 4294967295       ← đã max
RmLogonRC: 1                        ← đã bật
RMTraceLevel/…: (không có key)
```

`ResmanDebugLevel` đã **`0xFFFFFFFF`** = log mọi level. Nhưng **không có `NV_PRINTF` nào ở dòng 444** để log. ⇒ **Không có gì để bật.**

---

## 5. Đánh giá khả năng chẩn đoán chỉ đọc trong kernel (yêu cầu D3-2.5)

**Phân tích lý thuyết, KHÔNG triển khai, KHÔNG chạy.**

### 5.1 Kiến trúc giả định (nếu được phép)

```
Module kernel chẩn đoán (read-only)
    │
    ├─ lấy OBJGPU qua gpuGetByHandle / gpuGetGpuByDeviceId
    ├─ dùng pGpu->hInternalClient (đã cấp sẵn)
    ├─ pRmApi = rmapiGetInterface(RMAPI_GPU_LOCK_INTERNAL)
    └─ pRmApi->Control(pRmApi, hInternalClient, hInternalSubdevice,
                       0x20800A4B, &params, 4)
```

### 5.2 Đánh giá từng rủi ro

| Rủi ro | Đánh giá | Cơ sở |
|---|---|---|
| **Quyền** | **KHÔNG phải rủi ro** | `bInternal` sẽ TRUE qua interface lock-internal. Đây đúng đường RM dùng |
| **Tác dụng phụ** | **KHÔNG** | Handler có **1 store duy nhất** (`sw a5,0x0(s2)` vào output); callback `0x4C86300` **0 store** (D2-D) |
| **Deadlock** | **THẤP** | `RMAPI_GPU_LOCK_INTERNAL` lấy GPU lock; nếu gọi từ context đã giữ lock → deadlock. Cần gọi từ work-queue riêng |
| **Race với display init** | **THẤP** | Display init đã fail và không chạy lại (fuse gate). Không có consumer khác |
| **GSP state** | **THẤP** | Control chỉ đọc. Không đổi state GSP |
| **`params` chưa khởi tạo** | **TRUNG BÌNH** | Nếu handler không ghi (lỗi sớm), `params.ipVersion` là rác. Phải zero trước |
| **Handler trả lỗi** | **CAO, đã biết** | Nếu `*(base+0x1F60)==NULL` hoặc `0x6EA==0`, handler vẫn `return NV_OK` với `ipVersion=0`. Nhưng nếu `base` chưa init → crash. **Chưa xác định** |

### 5.3 Rủi ro lớn nhất: `base` có thể chưa tồn tại

Handler: `base = *(*(pGpu+0x160)+0xE8)`. Nếu display init **chưa từng chạy**, cấu trúc mà `+0xE8` trỏ tới có thể **chưa được cấp phát** ⇒ dereference NULL hoặc rác ⇒ **kernel oops**.

**Chưa xác định được tĩnh** vì firmware stripped, không có symbol để biết ai cấp `*(pGpu+0x160)`.

### 5.4 Kết luận mục 5

| Câu hỏi | Trả lời |
|---|---|
| Có thể làm về lý thuyết? | **CÓ**, đường hợp lệ tồn tại |
| Có an toàn chứng minh được? | **KHÔNG** — rủi ro dereference `base` chưa xác định |
| Có cần bỏ kiểm tra quyền? | **KHÔNG** |
| Có nằm trong phạm vi D3? | **KHÔNG** — D3 cấm sửa/chạy module |
| Giá trị thu được? | 1 số `ipVersion` (0–4) — trả lời câu hỏi B |

**Đánh giá:** đây là phép kiểm **khả thi về kỹ thuật nhưng không chứng minh được là an toàn bằng phân tích offline**. Cần quyết định riêng của người dùng, ngoài phạm vi D3.

---

## 6. Tổng kết D3-C

| Mục | Kết quả |
|---|---|
| `serverControl_ValidateCookie` + `RMCTRL_FLAGS_INTERNAL` | **XÁC NHẬN ĐẦY ĐỦ** — `control.c:795-807`, `control.h:236-243` |
| Hàm host gọi control | **`kdispStatePreInitLocked_IMPL`** — caller duy nhất, `kern_disp.c:435-465` |
| Tiền điều kiện | 8 điều, **7 ĐẠT**, 1 trượt (`gpuFuseSupportsDisplay_HAL`) |
| Đường nội bộ hợp lệ không cần bỏ quyền | **CÓ** — `pRmApi->Control` qua `hInternalClient`, đã tồn tại |
| Vì sao không chạy | Gate fuse ở dòng 444 **trước** lời gọi control |
| Chẩn đoán read-only trong kernel | **Khả thi kỹ thuật, KHÔNG chứng minh an toàn** — rủi ro `base` chưa cấp phát |
| Log để quan sát | **Không có** — dòng 444 không có `NV_PRINTF`; `ResmanDebugLevel` đã max |

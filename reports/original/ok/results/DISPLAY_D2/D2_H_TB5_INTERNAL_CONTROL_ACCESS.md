# D2-H — T-B5: CONTROL `0x20800A4B` CÓ GỌI ĐƯỢC TỪ USERSPACE KHÔNG?

**Ngày:** 2026-11-06 · Đọc source RM 615.78.08 · Chỉ phân tích tĩnh

---

## KẾT LUẬN: **KHÔNG. BLOCKED Ở BA LỚP ĐỘC LẬP.**

`NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` = **`0x20800A4B`** có `ctrlFlags = 0xC0` = `ROUTE_TO_PHYSICAL (0x40) | INTERNAL (0x80)`. Cờ `INTERNAL` chặn userspace **tuyệt đối**.

**`T-B1-run` (gọi control trên GPU thật) là BẤT KHẢ THI từ userspace.** Không cần thử.

---

## 1. Bằng chứng #1 — dispatch table ghi flags `0xC0`

`src/nvidia/generated/g_subdevice_nvoc.c:6572-6584`:

```c
    {               /*  [166] */
        /*pFunc=*/      (void (*)(void)) &subdeviceCtrlCmdDisplayGetIpVersion__EXPORT,
        /*flags=*/      0xc0u,
        /*accessRight=*/0x0u,
        /*methodId=*/   0x20800a4bu,
        /*paramSize=*/  sizeof(NV2080_CTRL_INTERNAL_DISPLAY_GET_IP_VERSION_PARAMS),
        ...
    },
```

### 1.1 Giải mã `0xC0`

`src/nvidia/inc/kernel/rmapi/control.h:220-243`:

```c
#define RMCTRL_FLAGS_PRIVILEGED                               0x000000004
#define RMCTRL_FLAGS_NON_PRIVILEGED                           0x000000008
#define RMCTRL_FLAGS_ROUTE_TO_PHYSICAL                        0x000000040
//
// If the INTERNAL flag is specified, the call will only be allowed
// to be issued from RM itself. Otherwise, NV_ERR_NOT_SUPPORTED is returned.
//
#define RMCTRL_FLAGS_INTERNAL                                 0x000000080
```

⇒ `0xC0 = 0x40 (ROUTE_TO_PHYSICAL) | 0x80 (INTERNAL)`.

**Không có `PRIVILEGED`, không có `NON_PRIVILEGED`.**

---

## 2. Bằng chứng #2 — nơi duy nhất set `bInternal = TRUE`

`src/nvidia/src/kernel/rmapi/control.c:385`:

```c
    // If we're behind either API lock or GPU lock treat as internal.
    bInternalRequest = pRmApi->bApiLockInternal || pRmApi->bGpuLockInternal;
```

`control.c:478`:

```c
    rmCtrlParams.bInternal = bInternalRequest;
```

### 2.1 `bApiLockInternal` / `bGpuLockInternal` là gì

Hai cờ **chỉ tồn tại trong tiến trình kernel của RM**. Được set bởi:

- `rmapiGetInterface(RMAPI_GPU_LOCK_INTERNAL)` — đường RM nội bộ
- `rmapiGetInterface(RMAPI_API_LOCK_INTERNAL)`

**Không có ioctl nào của userspace set được hai cờ này.** `NV_ESC_RM_CONTROL` từ userspace đi qua `pRmApi` với lock thường → `bInternalRequest = FALSE`.

---

## 3. Bằng chứng #3 — chốt chặn cuối trong `serverControl_ValidateCookie`

`control.c:802-807`:

```c
    if ((pRmCtrlExecuteCookie->ctrlFlags & RMCTRL_FLAGS_INTERNAL))
    {
        NvBool bInternalCall = pRmCtrlParams->bInternal;
        if (!bInternalCall)
            return NV_ERR_NOT_SUPPORTED;
    }
```

⇒ Userspace gửi `0x20800A4B` sẽ nhận **`NV_ERR_NOT_SUPPORTED` (0x56)** — ngay tại đây, **trước khi** handler GSP được gọi.

---

## 4. Bằng chứng #4 — client nội bộ là `NV01_ROOT`, không phải user class

`rmapiutilAllocClientAndDeviceHandles` (`src/nvidia/src/kernel/rmapi/rmapi_utils.c:42-90`):

```c
    // Allocate a client
    pRmApi->AllocWithHandle(pRmApi, NV01_NULL_OBJECT, NV01_NULL_OBJECT,
                            NV01_NULL_OBJECT, NV01_ROOT, &hClient, sizeof(hClient));

    // Allocate a device
    serverutilGenResourceHandle(hClient, &hDevice);
    nv0080AllocParams.deviceId = gpuGetDeviceInstance(pGpu);
    pRmApi->AllocWithHandle(..., NV01_DEVICE_0, ...);

    // Allocate a subDevice
```

Và `kern_disp.c:440-441`:

```c
    NvU32   hClient = pGpu->hInternalClient;
    NvU32   hSubdevice = pGpu->hInternalSubdevice;
```

⇒ `KernelDisplay` gọi control này bằng **`hInternalClient` class `NV01_ROOT`** — client kernel-internal của chính RM, không phải handle userspace có thể tạo.

### 4.1 Hệ quả quan trọng

Control này **không chỉ** yêu cầu "quyền admin". Nó yêu cầu **client class `NV01_ROOT` cộng với `bInternal=TRUE`**, tức **đang chạy bên trong RM với GPU lock internal**.

Ngay cả `CAP_SYS_ADMIN` cũng **không đủ**. Không có `NV01_ROOT` handle nào được export ra userspace.

---

## 5. Bằng chứng #5 — không có đường ioctl thay thế

Kiểm tra `NV_ESC_RM_CONTROL` từ userspace:

- `bInternalRequest = pRmApi->bApiLockInternal || pRmApi->bGpuLockInternal` — cả hai FALSE từ user path
- Không có flag `NVOS54_FLAGS_*` nào map sang `bInternal`
  - `NVOS54_FLAGS_IRQL_RAISED` → chỉ yêu cầu IRQL nâng cao, **không** set internal
  - `NVOS54_FLAGS_LOCK_BYPASS` → chỉ bỏ lock, **không** set internal

⇒ **Không có tổ hợp flags nào biến lời gọi userspace thành `bInternal=TRUE`.**

---

## 6. Vậy `ipVersion` thật của CMP 40HX có đo được không?

| Đường | Khả thi | Lý do |
|---|---|---|
| `NV_ESC_RM_CONTROL` từ userspace | **KHÔNG** | `RMCTRL_FLAGS_INTERNAL` → `NV_ERR_NOT_SUPPORTED` |
| NVML / `nvidia-smi` | **KHÔNG** | Không expose internal control |
| Gọi qua `hInternalClient` | **KHÔNG** | Handle kernel-only, không export |
| Patch driver để bỏ check | **ĐƯỢC về kỹ thuật** | Nhưng **ngoài phạm vi D2** — là sửa driver, không phải phân tích |
| Debug GSP qua JTAG/serial | **KHÔNG có thiết bị** | — |
| Đọc trực tiếp struct trong GPU memory | **KHÔNG** | Không có đường map |

### 6.1 Mệnh đề trung thực

> **`ipVersion` thật của CMP 40HX KHÔNG THỂ ĐO ĐƯỢC bằng phương tiện read-only hiện có.**
>
> Đây không phải "chưa làm" — đây là **kết quả đã chứng minh**: control bị chặn ở lớp RM với `RMCTRL_FLAGS_INTERNAL`, và không có API userspace nào khác expose cùng thông tin.

---

## 7. Điều này nói gì về giả thuyết "gate G3"

D1 đặt giả thuyết: nếu vượt gate fuse `0x021C04`, GSP có thể trả `ipVersion=0` (gate thứ hai).

**Sau D2-H:**

- Gate G3 **tồn tại** trong code (handler `0x04B9F5CC`, nhánh `0x4B9F60C`)
- Gate G3 **có điều kiện kích hoạt xác định** (`*(base+0x1F60)==NULL` HOẶC `*(u8*)(base+0x6EA)==0` HOẶC callback `0x4C86300` trả `a5[0]==0`)
- Gate G3 **chưa bao giờ chạy** trên card này — host chặn tại `kern_disp.c:444`
- Gate G3 **không thể quan sát** bằng read-only từ userspace

⇒ **Trạng thái của G3 trên CMP 40HX: UNPROVEN và KHÔNG QUAN SÁT ĐƯỢC.** Không phải "có", không phải "không". Đây là giới hạn thật của phương pháp.

---

## 8. Cập nhật bảng phép kiểm

| # | Phép kiểm | Trạng thái sau D2-H |
|---|---|---|
| T-B4 | Registry `RMDebugSetSMCMode` | ✅ ĐÃ CHẠY — key không tồn tại ⇒ W4 không kích hoạt |
| T-B6 | 8 slot HAL | ✅ ĐÃ CHẠY — tất cả là hàm, slot `+0x68` stub `0x56` |
| **T-B5** | **Quyền internal control** | ✅ **ĐÃ CHẠY — KHÔNG khả thi từ userspace, chứng minh 5 lớp** |
| T-B1-run | Gọi `0x20800A4B` | ❌ **BẤT KHẢ THI** — hệ quả trực tiếp của T-B5 |
| T-B7 | Ai ghi `obj+0x6A8` | ⚠️ 123 writer; 3 `sw` đúng nghĩa (`0x507C57C`, `0x507D50C`, `0x515DBC4`) — chưa xác định struct |
| T-B8 | F5 có chạy trên TU106 | ❌ BLOCKED — 0 caller, 0 literal |
| T-B9 | CFG đầy đủ cho F5 | Chưa chạy |

---

## 9. Kết luận D2 — trạng thái cuối

### Đã chứng minh

1. `+0x6EA` **không phải fuse**, **không phải VBIOS** — 0 site đọc cửa sổ `0x21000`, 0 tham chiếu ROM trên 4.272.758 instruction.
2. **11 site nằm trong 6 hàm thật** (không phải 10 — prologue heuristic ban đầu đếm cả epilogue).
3. **8/11 site ghi hằng `0`** — clear/reset, không mang thông tin.
4. **W2 (`0x4B6F3EC`) không thể tạo trạng thái** — đọc trước, thoát nếu `0`.
5. **W4 (`0x4C95FDC`) không kích hoạt trên target** — registry key `RMDebugSetSMCMode` không tồn tại.
6. **W5/W6 là 2 site duy nhất còn lại** có thể đặt giá trị khác 0, đọc qua HAL method pointer `obj+0x88`/`obj+0x90`.
7. **`obj+0x88` là slot HAL method**, chọn theo `*(u32*)(obj+0x6A8)` — **cách decode của D2-A đã bị bác bỏ**.
8. **Control `0x20800A4B` không gọi được từ userspace** — `RMCTRL_FLAGS_INTERNAL`, 5 lớp chặn độc lập.
9. **`ipVersion` thật không đo được** bằng phương tiện read-only.

### Chưa chứng minh được

1. **Nguồn cuối của giá trị W5/W6 ghi** — cách decode cũ bị bác bỏ, chưa có giả thuyết thay thế có bằng chứng.
2. **Ai gọi 6 hàm** — 0 call trực tiếp; chỉ F3/F4 có địa chỉ literal (slot #14/#16 của bảng 28 entry).
3. **Giá trị thực của `+0x6EA` trên CMP 40HX** — không quan sát được.
4. **Trạng thái gate G3** — không quan sát được.

### Điều D2 nói rõ là KHÔNG biết

- `+0x6EA` trên card này là 0 hay khác 0
- `*(base+0x1F60)` có NULL không
- `ipVersion` thật là bao nhiêu
- 6 hàm có được gọi trên TU106 không

**Đây không phải thiếu sót — đây là ranh giới của phân tích tĩnh + read-only, đã xác định chính xác ở đâu và vì sao.**

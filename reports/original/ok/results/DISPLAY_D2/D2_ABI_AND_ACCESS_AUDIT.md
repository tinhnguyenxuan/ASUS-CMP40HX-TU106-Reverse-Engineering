# D2-D — ABI VÀ ĐIỀU KIỆN TRUY CẬP CONTROL `0x20800A4B`

**Ngày:** 2026-11-06 · **Chưa gọi control này trên GPU thật** — đây là bản kiểm toán trước khi gọi

---

## 1. Định nghĩa control

| Trường | Giá trị | Nguồn |
|---|---|---|
| Tên | `NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` | `ctrl2080internal.h` |
| Command ID | **`0x20800A4B`** | message id `0x4B` |
| Params struct | `NV2080_CTRL_INTERNAL_DISPLAY_GET_IP_VERSION_PARAMS` | `{ NvU32 ipVersion; }` |
| Payload size | **`0x4`** byte | dispatch record `0x04061958` |
| Dispatch record | vaddr `0x04061958` (`.rm_rodata`) | 1182-entry table, base `0x0405FCB8` |
| Handler | **`0x04B9F5CC`** | record +16 |
| Flags | **`0x000000C0`** | record +24 |

### 1.1 So sánh flags với record đã biết

| Record | cmd | size | flags |
|---|---|---|---|
| A26 (T7) | `0x20800A26` | `0x2A60` | `0x00010080` |
| **A4B (D2)** | `0x20800A4B` | `0x4` | **`0x000000C0`** |

`0xC0` = bit 6 (`0x40`) + bit 7 (`0x80`). `0x80` = bit 7. Trong bảng `0x20800A26`, flags `0x00010080` có bit 7 + bit 16.

**Bit 7 xuất hiện ở cả hai** ⇒ có thể là bit "internal". **Bit 16 chỉ có ở A26** ⇒ A26 có thêm một thuộc tính A4B không có.

**Chưa xác định được ngữ nghĩa bit flags** — không có header công bố định nghĩa. **Không được suy đoán.**

---

## 2. ABI — ai gọi được

### 2.1 Đường truy cập

`NV2080_CTRL_CMD_INTERNAL_*` là **internal control**, không phải public API. Ba đường có thể gọi:

| Đường | Khả thi? | Điều kiện |
|---|---|---|
| **`NV2080_CTRL_CMD_INTERNAL_*` qua `rmapi` userspace** | **Cần xác minh** | Client phải cấp `NV2080_CTRL_INTERNAL_*` quyền; thường chỉ RM nội bộ |
| **`nvidia-smi` / NVML** | **KHÔNG** | NVML không expose internal control |
| **Ioctl `NV_ESC_RM_CONTROL`** trực tiếp | **Có thể** | Cần `NV_ESC_RM_ALLOC` object `NV01_DEVICE_0` + `NV20_SUBDEVICE_0` trước; cần `CAP_SYS_ADMIN` |

### 2.2 Kiểm tra quyền — CHƯA LÀM, cần làm trước khi gọi

Ba câu hỏi phải trả lời trước:

1. **Client nào được gửi internal control?** — RM phân loại client theo `clientId`; internal control chỉ chấp nhận từ **kernel client / RM-internal client**, không phải user client. **Cần xác minh trong `rmapi.c` / `nv_ioctl.c`.**
2. **Có bị chặn bởi `RmClientIsInternal()` hay kiểm tra privilege tương tự?** — **chưa kiểm.**
3. **Nếu gọi sai client class, kết quả là gì?** — dự kiến `NV_ERR_INVALID_CLIENT` / `NV_ERR_NOT_SUPPORTED`. **Không phải crash** — RM validate trước khi dispatch.

---

## 3. Tác dụng phụ — kiểm toán

### 3.1 Handler có ghi gì không?

Disassembly `0x04B9F5CC` (D1 §6.2, đầy đủ):

| Site | Instruction | Ghi vào đâu |
|---|---|---|
| `0x4B9F610` | `sw a5,0x0(s2)` | `*ipVersion` — **output param** |
| `0x4B9F658` | `j 0x4b9f610` | (nhảy, không ghi) |
| `0x4B9F66C` | `j 0x4b9f610` | (nhảy) |
| `0x4B9F674` | `j 0x4b9f610` | (nhảy) |
| `0x4B9F67C` | `j 0x4b9f610` | (nhảy) |

**Chỉ có MỘT store duy nhất: `sw a5,0x0(s2)` vào output parameter. Không có store nào khác.**

Đối chiếu: không có `sb`/`sh`/`sw`/`sd` nào khác trong toàn hàm 0x110 byte.

### 3.2 Có gọi gì gây tác dụng phụ không?

| Call | Đích | Đánh giá |
|---|---|---|
| `0x4B9F63C jalr` | `0x4C86300` | **Read-only**: `lbu` từ `*(params+0x2F0)[0..2]`, `lbu` từ `*(this+0x2208)+0x2160+0x18`. **Không store.** |
| callback `0x4B9F650` → nhánh | không gọi | — |

Kiểm tra `0x4C86300` toàn hàm (0x34 B) — chỉ có `lbu`, `ld`, `add`, `seqz`, `addi`, `beqz`, `bnez`, `ret`. **0 store.**

### 3.3 Kết luận tác dụng phụ

> **Gọi control `0x20800A4B` là READ-ONLY ở cả hai lớp (host dispatch + GSP handler).**
> Chỉ một store duy nhất vào output buffer do caller cấp.

**Rủi ro còn lại:** nếu client chưa alloc đúng object, ioctl trả lỗi — **không ghi hardware**.

---

## 4. Điều kiện truy cập control này trên CMP 40HX hiện tại

### 4.1 Đường host — **ĐÃ CHẶN TRƯỚC KHI GỬI**

```
kdispStatePreInitLocked_IMPL (kern_disp.c:444)
    if (!gpuFuseSupportsDisplay_HAL(pGpu)) return NV_ERR_NOT_SUPPORTED;
        → KernelDisplay bị huỷ
        → object display không được tạo
        → control 0x20800A4B KHÔNG BAO GIỜ được gửi
```

⇒ **Trên hệ thống hiện tại, không có client nào trong RM gửi control này.** Không có "gate phía GSP" nào đang hoạt động — vì chưa có ai đến được cửa.

### 4.2 Nếu user cố gửi trực tiếp

Cần vượt **ba** lớp:

| Lớp | Kiểm tra | Kết quả dự kiến |
|---|---|---|
| 1 | `NV_ESC_RM_ALLOC` object `NV20_SUBDEVICE_0` | Subdevice alloc được? — phụ thuộc `engstateIsPresent` |
| 2 | Client class có quyền gửi `NV2080_CTRL_CMD_INTERNAL_*` | **CHƯA XÁC ĐỊNH** — có thể `NV_ERR_INVALID_CLIENT` |
| 3 | GSP handler `0x04B9F5CC` chạy | Nếu tới được: trả `ipVersion` |

**Lớp 2 là điểm chưa biết quan trọng nhất.** Nếu internal control bị chặn ở lớp này, `T-B1` bất khả thi từ userspace.

---

## 5. Phân biệt: nhánh `ipVersion=0` tồn tại ≠ nhánh đó được chọn

Đây là yêu cầu cốt lõi của D2. Bảng phân biệt:

| Mệnh đề | Trạng thái | Cơ sở |
|---|---|---|
| Nhánh `ipVersion = 0` **tồn tại trong code** | **PROVEN** | `0x4B9F60C`–`0x4B9F610`: `li a5,0 ; sw a5,0(s2)` |
| Handler `0x04B9F5CC` **tồn tại và dispatch đúng** | **PROVEN** | record `0x04061958`, cmd `0x20800A4B`, handler khớp, `const = 0x040704C8` như mọi record |
| Nhánh đó **được chọn trên CMP 40HX** | **UNPROVEN — KHÔNG CÓ BẰNG CHỨNG** | Handler **chưa bao giờ được gọi**: host trả `NV_ERR_NOT_SUPPORTED` tại `kern_disp.c:444` trước khi gửi control |
| `ipVersion` thật của CMP 40HX | **CHƯA ĐO** | — |
| `*(base+0x1F60) == NULL` trên CMP 40HX | **CHƯA ĐO** | — |
| `*(u8*)(base+0x6EA) == 0` trên CMP 40HX | **CHƯA ĐO** | D2-A đã truy **nguồn** của byte này (chipset HAL + debug key), nhưng **chưa biết giá trị thực** |

### 5.1 Điều KHÔNG được nói

| Tuyên bố sai | Vì sao sai |
|---|---|
| "GSP đã trả `ipVersion = 0` cho CMP 40HX" | Handler chưa từng chạy. Không có dữ liệu. |
| "Vì `0x021C04 = 1` nên `0x6EA = 0`" | **Hai thứ độc lập.** D2 chứng minh `0x6EA` đến từ `this->f_0x88+0x10` và debug key, **không phải fuse**. |
| "Nhánh `ipVersion=0` là nguyên nhân display tắt" | Nguyên nhân đã chứng minh là `kern_disp.c:444`, **trước** khi control này tồn tại trong luồng. |
| "Nhánh `ipVersion=0` không bao giờ xảy ra" | Không chứng minh được. Nó có thể xảy ra nếu gate fuse được vượt. |

### 5.2 Điều ĐƯỢC nói có bằng chứng

> Nhánh `ipVersion = 0` **tồn tại**, **có thể được chọn** (3 điều kiện độc lập: `*(base+0x1F60)==0`, `*(u8*)(base+0x6EA)==0`, hoặc callback trả `a5[0]==0`), và **nếu gate host được vượt thì đây là gate thứ hai**.
>
> Trên CMP 40HX hiện tại **không có phép đo nào** cho biết nhánh nào được chọn — vì control chưa bao giờ đi qua.

---

## 6. Kế hoạch gọi an toàn (nếu được duyệt)

Không thực hiện trong D2. Nếu làm, theo thứ tự:

1. **Kiểm tĩnh trước:** `grep` trong `src/nvidia/` tìm kiểm tra quyền cho `NV2080_CTRL_CMD_INTERNAL_*` từ user client. Trả lời lớp 2 ở §4.2.
2. **Chỉ đọc:** mở `/dev/nvidiactl`, `NV_ESC_CHECK_VERSION`, `NV_ESC_RM_ALLOC` subdevice.
3. **Nếu subclass alloc được:** gửi `NV_ESC_RM_CONTROL` với `cmd = 0x20800A4B`, buffer 4 byte zeroed.
4. **Đọc kết quả** — nếu `NV_OK`, `ipVersion` có giá trị.
5. **Không ghi gì vào GPU.** Handler đã chứng minh read-only (§3).
6. **Có thể chạy lại nhiều lần** — idempotent, không thay đổi trạng thái.

**Điều kiện dừng:** nếu bước 1 cho thấy internal control bị chặn cho user client → `T-B1` = **BLOCKED**, ghi rõ.

---

## 7. Tổng kết D2-D

| Câu hỏi | Trả lời |
|---|---|
| ABI của `0x20800A4B` | `(NvHandle hClient, NvHandle hSubdevice, NV2080_CTRL_INTERNAL_DISPLAY_GET_IP_VERSION_PARAMS *p)`, params 4 byte, `{ NvU32 ipVersion }` |
| Payload size | `0x4` (khớp dispatch record) |
| Handler | `0x04B9F5CC`, flags `0x000000C0` |
| Tác dụng phụ | **KHÔNG** — 1 store duy nhất vào output, callback read-only |
| Ai gọi được | **CHƯA XÁC ĐỊNH** — internal control có thể chặn user client |
| Đang được gọi trên CMP 40HX? | **KHÔNG** — host chặn tại `kern_disp.c:444` |
| Nhánh `ipVersion=0` là nguyên nhân? | **KHÔNG phải nguyên nhân hiện tại**; là **gate tiềm năng** nếu vượt gate fuse |
| Đã gọi trên GPU thật? | **CHƯA — đúng yêu cầu** |

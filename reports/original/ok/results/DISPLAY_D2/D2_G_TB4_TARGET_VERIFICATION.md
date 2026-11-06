# D2-G — T-B4: KIỂM TRÊN MÁY ĐÍCH (SSH ĐÃ HOẠT ĐỘNG LẠI)

**Ngày:** 2026-11-06 · **Read-only** · Không ghi MMIO/BAR3/fuse, không flash, không sửa firmware

---

## 0. SSH đã vào được

```
REDACTED_USER@<REDACTED_LAB_IP>  →  hostname 2696
nvidia-smi: NVIDIA CMP 40HX, 615.78.08
```

---

## 1. KẾT QUẢ T-B4 — registry key `RMDebugSetSMCMode` KHÔNG tồn tại

### 1.1 `/proc/driver/nvidia/params`

```
ResmanDebugLevel: 4294967295
RmLogonRC: 1
...
RegistryDwords: ""
RegistryDwordsPerDevice: ""
RegistryBinaryFilePerDevice: ""
RmMsg: ""
...
```

**`RegistryDwords` = chuỗi RỖNG.** Không có key nào được set qua module param.

### 1.2 `/proc/driver/nvidia/registry`

```
Binary: ""
```
**11 byte — hoàn toàn rỗng.**

### 1.3 Grep key cụ thể

```
grep -i "rmdebug\|display\|smc" /proc/driver/nvidia/params   →  0 hit
```

**Không có `RMDebugSetSMCMode`, không có key display nào.**

---

## 2. HỆ QUẢ TRỰC TIẾP — W4 ĐANG CLEAR `+0x6EA`

Site #4 `0x4C95FDC` logic (D2-A):

```asm
4c95fb4: lui  a1,0x4134
4c95fbc: addi a1,a1,0x6e8        # key = "RMDebugSetSMCMode" @ 0x41346E8
4c95fb8: addi a2,s0,-0x9c        # &out
4c95fc0: mv   a0,s1              # this
4c95fc8: jalr 0x348(ra)          # → 0x45E130C = (this,key,&out)->status
4c95fd0: bnez a0, 0x4c95fe0      # lookup fail -> skip
4c95fd4: lw   a5,-0x9c(s0)       # a5 = out value
4c95fd8: bnez a5, 0x4c96578      # value != 0 -> skip clear
4c95fdc: sb   zero,0x6ea(s1)     # value == 0 -> CLEAR
```

Key **không tồn tại** ⇒ lookup **fail** ⇒ `bnez a0` **rẽ nhánh bỏ qua** ⇒ `sb zero` **KHÔNG chạy**.

⚠️ **ĐÍNH CHÍNH so với D2-C:** D2-C viết *"`RMDebugSetSMCMode == 0` ⇒ GSP clear `0x6EA`"* và ngầm hiểu "key không tồn tại ⇒ clear". **SAI.** Đọc kỹ:

- `jalr` trả `a0 = status`. Nếu key không có trong registry → helper trả **non-zero**.
- `bnez a0, 0x4c95fe0` → **nhảy qua** `sb zero`.
- Chỉ khi lookup **thành công** (`a0 == 0`) **và** giá trị đọc được `== 0` thì mới clear.

⇒ **Trên máy này, W4 KHÔNG clear `+0x6EA`.**

### 2.1 Mệnh đề đúng

> **W4 là đường clear CHỈ KHI registry key `RMDebugSetSMCMode` tồn tại và bằng 0.** Trên target hiện tại key **không tồn tại** ⇒ **W4 không kích hoạt**.

**Giá trị thực tế của `+0x6EA` trên card này vẫn CHƯA BIẾT** — không phải do W4, và không đo được (handler chưa chạy).

---

## 3. dmesg đầy đủ — xác nhận trạng thái

```
[    8.700121] NVRM: loading NVIDIA UNIX Open Kernel Module for x86_64  615.78.08
[    8.713475] nvidia-modeset: Loading ... 615.78.08
[    8.730304] [drm] [nvidia-drm] [GPU ID 0x00000300] Loading driver
[    8.733014] [drm] Initialized nvidia-drm 0.0.0 20160202 for 0000:03:00.0 on minor 1
[    8.733024] nvidia 0000:03:00.0: [drm] No compatible format found
[    8.733028] nvidia 0000:03:00.0: [drm] Cannot find any crtc or sizes
```

**Không có dòng nào** về display init, PDISP, IP version, hay `RMDebugSetSMCMode`.
`grep -iE "nvidia.*(disp|gsp|ipver)"` → **0 hit** ngoài hai dòng `[drm]` ở trên.

⇒ Xác nhận: **đường display không đi qua** bất kỳ log nào — dừng im lặng tại `kern_disp.c:444`.

---

## 4. Phát hiện phụ — BAR1/BAR3 bị dồn chỗ

```
[5.134240] nvidia 0000:03:00.0: BAR 1 [mem size 0x4000000000 64bit pref]: can't assign; no space
[5.134242] nvidia 0000:03:00.0: BAR 3 [mem size 0x02000000 64bit pref]: can't assign; no space
[5.134427] nvidia 0000:03:00.0: BAR 1 [mem 0x381000000000-0x381fffffffff 64bit pref]: assigned
[5.134438] nvidia 0000:03:00.0: BAR 3 [mem 0x380800000000-0x380801ffffff 64bit pref]: assigned
```

Kernel thử nhiều kích thước (256 GB, 32 GB, 128 GB, 512 GB) rồi cuối cùng gán BAR1 = **256 GB**. Đây là **hành vi bình thường của driver open trên CMP** (BAR1 bị khai báo lớn), **không phải nguyên nhân display**.

Ghi nhận vì nó giải thích tại sao BAR1 không dùng được cho việc đọc fuse (D1 đã sửa sang BAR0).

---

## 5. Trạng thái 6 phép kiểm sau D2

| # | Phép kiểm | Trạng thái | Kết quả |
|---|---|---|---|
| **T-B4** | Registry `RMDebugSetSMCMode` | ✅ **ĐÃ CHẠY** | **Key KHÔNG tồn tại ⇒ W4 không clear** |
| **T-B6** | 8 slot HAL `obj+0x60..0x98` | ✅ **ĐÃ CHẠY** | Tất cả là **hàm**; slot `+0x68` là stub trả `0x56` |
| **T-B7** | Ai ghi `obj+0x6A8` (arch ID) | ⚠️ **123 writer** | Phần lớn là `sd` (offset dùng cho struct khác); có **3 `sw` đúng nghĩa** tại `0x507C57C`, `0x507D50C`, `0x515DBC4` |
| **T-B8** | F5 có chạy trên TU106 không | ❌ **BLOCKED** | 0 caller trực tiếp, 0 literal — không xác định được tĩnh |
| **T-B9** | CFG đầy đủ cho F5 | Chưa chạy | Cần dựng CFG thật (không chỉ linear) |
| **T-B1-run** | Gọi control `0x20800A4B` | ❌ **CHƯA** | Quyền internal control cho user client chưa xác định |

### 5.1 Về T-B7 — 123 writer

`0x507C57C`: `sw a3,0x6a8(a4)` với `a3 = 0x1FF`, `a4 = s3 + 0x2000`.
`0x515DBC4`: `sw a2,0x6a8(a5)` rồi `0x6AC`, `0x6B0` — **cụm 3 field liên tiếp**.

⇒ `obj+0x6A8` có thể là **field 32-bit trong một struct khác**, không phải arch ID như `0x458E258` đọc. **Hai struct khác nhau dùng cùng offset.** Không kết luận được nếu không có CFG xác định `a5` trong `0x458E240` là object nào.

---

## 6. Điều thay đổi so với D2-C

| D2-C nói | Sự thật (D2-G) |
|---|---|
| "`RMDebugSetSMCMode == 0` ⇒ GSP clear `0x6EA`" | Chỉ đúng **khi key tồn tại**. Key **không tồn tại** trên target ⇒ **W4 không chạy** |
| W4 là "một con đường phần mềm thuần khiến GSP tắt display" | Đúng về **cơ chế**, nhưng **không kích hoạt** trên hệ thống này |

**W4 vẫn có giá trị phân tích:** nó chứng minh GSP **có** một nhánh tắt display do registry điều khiển, tồn tại **độc lập với fuse**. Nhưng nó **không** phải nguyên nhân hiện tại.

---

## 7. Kết luận D2 sau khi có T-B4

> **Trong 11 write site, sau khi loại trừ bằng bằng chứng:**
>
> - **8 site ghi hằng `0`** — clear/reset, không mang thông tin vào
> - **W2 (`0x4B6F3EC`) không thể tạo trạng thái** (đọc trước, thoát nếu 0)
> - **W4 (`0x4C95FDC`) không kích hoạt** trên target (key registry không tồn tại)
> - **W5/W6 (`0x5306DE4`, `0x530713C`)** — 2 site duy nhất còn lại có thể đặt giá trị khác 0. Nguồn: `lhu 0x10(fnptr_HAL)` qua `obj+0x88`/`obj+0x90` — **cơ chế chưa xác định**, và **cách decode của D2-A đã bị bác bỏ**
>
> **⇒ Giá trị thực của `+0x6EA` trên CMP 40HX: CHƯA XÁC ĐỊNH ĐƯỢC bằng phân tích tĩnh.**
>
> **Không có bằng chứng** `+0x6EA` phản ánh fuse, VBIOS, hay product policy.

---

## 8. Bước tiếp theo cần quyết định của người dùng

Hai đường, cả hai đều cần sự đồng ý:

| Đường | Việc phải làm | Rủi ro |
|---|---|---|
| **A. Đo `ipVersion` thật** | Viết client NV2080 userspace gửi `NV_ESC_RM_CONTROL` cmd `0x20800A4B`. Cần audit trước xem internal control có chặn user client không (đọc `src/nvidia/`). Handler đã chứng minh **read-only, 1 store** | Thấp — read-only, idempotent |
| **B. Đo `+0x6EA` trực tiếp** | Không có đường host đọc. Cần patch debug vào driver hoặc GSP — **ngoài phạm vi D2** | Cao — sửa driver/firmware |

**Đường A là bước hợp lý tiếp theo.** Cần anh xác nhận trước khi em viết client và chạy trên GPU thật.

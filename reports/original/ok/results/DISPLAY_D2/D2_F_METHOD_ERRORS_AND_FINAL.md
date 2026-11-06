# D2-F — SỬA LỖI PHƯƠNG PHÁP & KẾT LUẬN CUỐI

**Ngày:** 2026-11-06 · Ghi lại hai lỗi do chính D2 phát hiện và tự sửa

---

## SỬA LỖI #1 — Prologue heuristic đếm sai

### Vấn đề

`trace6ea.py` phát hiện "prologue" bằng bit pattern:

```python
w & 0x7F == 0x13 and rd == x2 and rs1 == x2      # addi sp, sp, N
```

Pattern này khớp **cả `addi sp, sp, +N`** (epilogue) lẫn **`addi sp, sp, -N`** (prologue).

### Bằng chứng lỗi

`0x53075F0` được ghi nhận là prologue của một hàm 184 B. Đọc thật:

```asm
0053075ec: ld   s0,0x8(sp)      # ← epilogue của hàm TRƯỚC
0053075f0: addi sp,sp,0x10      # +0x10  (DƯƠNG)
0053075f4: ret
0053075f8: li   t6,0x0          # ← code tiếp, không có prologue
0053075fc: li   t5,0x0
005307600: j    0x53070dc
```

`0x53075F0` là **epilogue nằm giữa hàm**, không phải đầu hàm.

### Hệ quả lên D2-A

| D2-A nói | Sự thật |
|---|---|
| 10 hàm chứa 11 write site | **6 hàm thật** (`F1`–`F6`) |
| `0x53075F0` = hàm 184 B | **epilogue** — thuộc `F5` |
| `0x53076A8` = hàm 656 B | **epilogue** — thuộc `F5` |
| `0x538307C` = hàm 892 B | **epilogue** — thuộc `F6` |
| `0x5382C14` = hàm 1128 B | **epilogue** — thuộc `F6` |

### Đếm lại chính xác (`addi sp, sp, -N` với immediate **âm**)

```
TRUE prologues: 46.510  (so với 104.466 khi đếm sai)
```

| Write site | Hàm thật | Kích thước |
|---|---|---|
| W1 `0x4A128D4` | `0x4A127FC` | 420 B |
| W2 `0x4B6F3EC` | `0x4B6F190` | 3.316 B |
| W3 `0x4C89784` | `0x4C89440` | 964 B |
| W4 `0x4C95FDC` | `0x4C95EFC` | 1.796 B |
| **W5 `0x5306DE4`** | **`0x5306D20`** | **3.096 B** |
| **W6 `0x530713C`** | **`0x5306D20`** | **3.096 B** |
| **W7 `0x5307604`** | **`0x5306D20`** | **3.096 B** |
| **W8 `0x53076C4`** | **`0x5306D20`** | **3.096 B** |
| **W9 `0x5382D2C`** | **`0x5382B34`** | **2.244 B** |
| **W10 `0x5382F08`** | **`0x5382B34`** | **2.244 B** |
| **W11 `0x538314C`** | **`0x5382B34`** | **2.244 B** |

⇒ **6 hàm, không phải 10.** W5–W8 cùng một hàm; W9–W11 cùng một hàm.

### Điều này thay đổi cách đọc kết luận

- W5/W6 ghi giá trị khác 0 và W7/W8 ghi 0 — **cùng một hàm, bốn nhánh**. Đây là **một cây quyết định duy nhất**, không phải bốn writer độc lập.
- W9/W10/W11 **cùng một hàm** — ba nhánh reset của cùng một routine.

---

## SỬA LỖI #2 — `obj+0x88` là con trỏ HÀM, không phải con trỏ DỮ LIỆU

D2-A kết luận site #5/#6 decode `class`/`index` từ `*(u16*)(this->f_0x88 + 0x10)` như một bảng phân loại.

D2-E chứng minh bảng HAL tại `0x458E240`/`0x458E348` ghi **địa chỉ hàm** `0x5232DE0` vào `obj+0x88`. T-B6 xác nhận cả 8 slot là HAL method, một slot là stub trả `0x56`.

⇒ `lhu 0x10(fnptr)` đọc **byte lệnh**, không đọc dữ liệu. **Giả thuyết D2-A bị bác bỏ.**

---

## KẾT LUẬN CUỐI D2 — những gì đứng vững

### Bảng 6 hàm, 11 site, phân loại

| Hàm | Site | Loại | Nguồn giá trị |
|---|---|---|---|
| **F1** `0x4A127FC` | W1 | clear có điều kiện | 3 điều kiện lỗi AND |
| **F2** `0x4B6F190` | W2 | re-write | `*(this+0x250)()` — **chỉ khi đã != 0** |
| **F3** `0x4C89440` | W3 | clear có điều kiện | hiện `!=0` AND field `!=1` |
| **F4** `0x4C95EFC` | W4 | **debug override** | **registry key `"RMDebugSetSMCMode"`** |
| **F5** `0x5306D20` | W5, W6, W7, W8 | **constructor 4 nhánh** | `lhu 0x10(fnptr_HAL)` — **cơ chế chưa xác định** |
| **F6** `0x5382B34` | W9, W10, W11 | reset/cleanup 3 nhánh | hằng `0x30C1`, `0x0FDF0FF00` |

### Mệnh đề được chứng minh

| # | Mệnh đề | Bằng chứng |
|---|---|---|
| 1 | `+0x6EA` **không phải fuse** | 0 site đọc cửa sổ `0x21000`; 0 literal `0x21C04`/`0x820C04` trên 4.272.758 instruction |
| 2 | `+0x6EA` **không phải VBIOS** | 0 site tham chiếu BIT/DCB/ROM |
| 3 | **8/11 site ghi hằng `0`** | disassembly đầy đủ |
| 4 | **W2 không thể tạo trạng thái** | `lbu 0x6ea(s1); beqz a5, skip` — đọc trước, thoát nếu 0 |
| 5 | **W4 phụ thuộc registry `RMDebugSetSMCMode`** | chuỗi `@0x41346E8` + helper `0x45E130C = (this,key,out)->status` |
| 6 | `obj+0x88`/`obj+0x90` do **bảng HAL dispatch** ghi theo `*(u32*)(obj+0x6A8)` | `0x458E240`, 8 slot, slot `+0x68` là stub `0x56` |
| 7 | **Không hàm nào trong 6 có caller trực tiếp** | 0/6 trên 111.131 call resolve được |
| 8 | **F3 và F4 nằm trong bảng 28 slot** `.rm_rodata:0x4035608` | slot #14 (`0x4035678`) và #16 (`0x4035688`) |

### Mệnh đề KHÔNG chứng minh được

| # | Điều chưa biết | Vì sao |
|---|---|---|
| 1 | Nguồn cuối của giá trị W5/W6 ghi | Cách decode D2-A bị bác bỏ; chưa có giả thuyết thay thế có bằng chứng |
| 2 | Ai gọi 6 hàm | 0 call trực tiếp, chỉ 2/6 có địa chỉ literal |
| 3 | `ipVersion` thật trên CMP 40HX | Control `0x20800A4B` chưa từng được gửi (host chặn tại `kern_disp.c:444`) |
| 4 | 6 hàm có chạy trên TU106 không | Không có caller ⇒ không xác định được |

### Điều KHÔNG được nói

| Sai | Đúng |
|---|---|
| "`0x6EA` lấy từ chipset HAL data" | W5/W6 đọc qua con trỏ **hàm** HAL; cơ chế chưa rõ |
| "`0x021C04=1` ⇒ `0x6EA=0`" | Hai thứ độc lập |
| "GSP đã trả `ipVersion=0` cho CMP" | Handler chưa từng chạy |
| "`0x6EA` do product policy" | Không có bằng chứng đọc SKU; W4 là **registry debug key**, không phải policy |

### Điều đáng chú ý nhất D2 tìm được

> **W4 (site `0x4C95FDC`) clear `0x6EA` khi registry key `"RMDebugSetSMCMode"` bằng 0.**
>
> Đây là **một con đường phần mềm thuần** khiến GSP tắt display state — **độc lập hoàn toàn với fuse `0x021C04`**. Nó chứng minh: ngay cả nếu fuse được vượt, vẫn còn ít nhất một cờ debug trong registry có thể tắt display.
>
> **Không xác nhận được key này có tồn tại trên máy đích** — SSH bị từ chối.

---

## Phép kiểm còn lại

| # | Phép kiểm | Trạng thái |
|---|---|---|
| **T-B4** | Đọc `/proc/driver/nvidia/params`, kiểm `RMDebugSetSMCMode` | **BLOCKED — SSH `REDACTED_USER@<REDACTED_LAB_IP>` từ chối mật khẩu** |
| **T-B7** | Trace `*(u32*)(obj+0x6A8)` → arch ID → nhánh HAL cho TU106 | Chưa chạy |
| **T-B8** | Xác định F5 có chạy trên object đã qua HAL không | Chưa chạy — không có caller |
| **T-B9** | Tái phân tích F5 bằng CFG đầy đủ (không chỉ linear) để xác định `lhu 0x10` thật sự đọc gì | Chưa chạy |

**T-B4 là phép kiểm duy nhất có thể chạy ngay** — chỉ cần SSH hoạt động trở lại.

# D2-E — T-B2: AI GHI `this+0x88` (nguồn cuối của `+0x6EA`)

**Firmware:** GSP-RM 615.78.08, inner ELF `cd83bb04…3a2cfe85`
**Ngày:** 2026-11-06 · offline only

---

## 0. Câu hỏi

Site #5/#6 (`0x5306D20`, `0x5307018`) đọc:

```asm
0x5306D30: ld   a4,0x88(a0)      # a4 = *(this + 0x88)
0x5306D34: ld   a3,0x90(a0)      # a3 = *(this + 0x90)
0x5306D3C: lhu  a4,0x10(a4)      # a4 = *(u16*)(a4 + 0x10)   ← NGUỒN của class/index
```

⇒ Cần tìm ai ghi `this+0x88`.

---

## 1. Kết quả: **TÌM ĐƯỢC** — bảng HAL dispatch

### 1.1 Hàm khởi tạo tại `0x458E240`

```asm
458e240: ld   a5,0x8(a0)          # a5 = *(a0 + 0x8)  = object
458e244: beqz a5, 0x458ecc4       # NULL -> thoát
458e248: addi sp,sp,-0x20 ; lưu s0,ra
458e258: lw   a4,0x6a8(a5)        # a4 = *(u32*)(obj + 0x6A8)   ← CHIP ARCH ID
458e25c: lui  a3,0x3000
458e264: bgeu a4,a3, 0x458e2b0    # switch trên a4
458e268: lui  a3,0x13010
458e26c: bltu a4,a3, 0x458e274
458e270: j    0x4592f28           # nhánh arch A
458e274: lui  a3,0x12010
458e278: bltu a4,a3, 0x458e280
458e27c: j    0x4592f0c           # nhánh arch B
458e280: lui  a3,0x3000
458e284: bgeu a4,a3, 0x458e28c
458e288: j    0x4591288           # nhánh arch C
458e28c: lui  a3,0x5226
458e290: addi a3,a3,-0x64         # a3 = 0x5225F9C
458e294: sd   a3,0xa0(a5)         # obj+0xA0 = 0x5225F9C
458e298: lui  a3,0x2f020
458e29c: bltu a4,a3, 0x458e4c8
458e2a0: lui  a3,0x522a
...
```

### 1.2 Nhánh chứa `+0x88` — `0x458E300..0x458E370`

```asm
458e300: addi a3,a3,-0x454
458e304: sd   a3,0x60(a5)        # obj+0x60 = 0x0522FBAC
458e308: lui  a3,0x23050
458e30c: bltu a4,a3, 0x458eccc
458e310: lui  a3,0x521b
458e314: addi a3,a3,-0x438
458e318: sd   a3,0x68(a5)        # obj+0x68 = 0x0521ABC8
458e31c: lui  a3,0x5237
458e320: addi a3,a3,-0xb8
458e324: sd   a3,0x70(a5)        # obj+0x70 = 0x05236F48
458e328: lui  a3,0x522e
458e32c: addi a3,a3,0x224
458e330: sd   a3,0x78(a5)        # obj+0x78 = 0x0522E224
458e334: lui  a3,0x5235
458e338: addi a3,a3,0x7d8
458e33c: sd   a3,0x80(a5)        # obj+0x80 = 0x052357D8
458e340: lui  a3,0x5233
458e344: addi a3,a3,-0x220
458e348: sd   a3,0x88(a5)        # obj+0x88 = 0x05232DE0   ★★ ĐÂY
458e34c: lui  a3,0x522b
458e350: addi a3,a3,0x18c
458e354: sd   a3,0x90(a5)        # obj+0x90 = 0x0522B18C   ★★ VÀ ĐÂY
458e358: lui  a3,0x522e
458e35c: addi a3,a3,0x404
458e360: sd   a3,0x98(a5)        # obj+0x98 = 0x0522E404
458e364: lui  a3,0x3000
458e368: bltu a4,a3, 0x458e370
458e36c: j    0x4593000
```

**Đây là bảng gán con trỏ hàm liên tiếp** `obj+0x60, +0x68, +0x70, +0x78, +0x80, +0x88, +0x90, +0x98` — mỗi slot 8 byte, mỗi slot một địa chỉ trong `.rm_text`.

### 1.3 Xác nhận cùng object

| Bằng chứng | Giá trị |
|---|---|
| Base register | `a5 = *(a0+0x8)` — object lấy từ `a0+8` |
| Offset dùng để chọn nhánh | `0x6A8` |
| Offset ghi `+0x88` | `0x88` |
| W5/W6 đọc | `0x88`, `0x90`, `0x6E9..0x6EF` trên cùng base `a0` |

⇒ **Cùng một object type.** `obj+0x88` là **slot 6** trong bảng HAL 8 slot.

---

## 2. Giá trị được ghi — **địa chỉ CODE**, không phải con trỏ dữ liệu

| Slot | Giá trị | Section |
|---|---|---|
| `obj+0x60` | `0x0522FBAC` | `.rm_text` |
| `obj+0x68` | `0x0521ABC8` | `.rm_text` |
| `obj+0x70` | `0x05236F48` | `.rm_text` |
| `obj+0x78` | `0x0522E224` | `.rm_text` |
| `obj+0x80` | `0x052357D8` | `.rm_text` |
| **`obj+0x88`** | **`0x05232DE0`** | **`.rm_text`** |
| **`obj+0x90`** | **`0x0522B18C`** | **`.rm_text`** |
| `obj+0x98` | `0x0522E404` | `.rm_text` |

**Tất cả 8 slot đều là địa chỉ hàm.** Đây là **HAL function table**, không phải dữ liệu.

---

## 3. Hệ quả: D2-A §2 cần đính chính

### 3.1 Điều D2-A nói

> Site #5/#6: `class = *(u16*)(this->f_0x88 + 0x10) >> 5`, `index = word & 0x1F`

### 3.2 Sự thật

`this->f_0x88` = **địa chỉ code** `0x5232DE0`. Đọc `*(u16*)(0x5232DE0 + 0x10)` = đọc **byte lệnh** tại `0x5232DF0`:

```
0x5232DF0: 13 05 00 00   =  li a0, 0x0    (instruction word)
```

`lhu` tại đó = `0x0513`. Rồi `class = 0x0513 >> 5 = 0x28 = 40`. Vô nghĩa như "class".

### 3.3 Cách đọc đúng

`obj+0x88` là **con trỏ hàm**, không phải con trỏ struct. Vậy `ld a4,0x88(a0)` nạp **địa chỉ hàm**, và `lhu a4,0x10(a4)` là **đọc instruction word trong code**.

**Hai khả năng, đều chưa loại trừ được:**

1. **Compiler/LTO đã sinh code sai-hoặc-fusion**: `lhu 0x10(a4)` thực chất là **tail-call thunk** bị objdump giải mã nhầm thành `lhu`. Kiểm tra: `0x5306D3C` raw = `03 57 07 01`. Opcode `0x03` = LOAD, `funct3=0x5` = LH (load halfword), unsigned variant là `funct3=0x5` với bit 14 set → `lhu`. **Decode đúng là `lhu`.**

2. **`obj+0x88` trong ngữ cảnh W5 là struct khác** — nhưng §1.3 đã chứng minh cùng object.

### 3.4 Kết luận trung thực

> **D2-A §2 SAI khi nói "site #5/#6 decode `*(u16*)(this->f_0x88 + 0x10)` như bảng phân loại".**
>
> `this->f_0x88` được ghi bằng **địa chỉ hàm** (`0x5232DE0`) bởi bảng HAL tại `0x458E348`. Đọc `u16` tại `code+0x10` là đọc byte lệnh, không phải dữ liệu.
>
> **Nguồn của `class`/`index` cho `+0x6EA` vẫn CHƯA XÁC ĐỊNH.** D2-A đưa ra một giả thuyết (chipset HAL data), D2-E **bác bỏ cách diễn giải cụ thể đó** nhưng **không thay thế bằng giả thuyết mới**.

---

## 4. Điều §1 vẫn chứng minh được (không bị ảnh hưởng)

| Sự thật | Còn hiệu lực |
|---|---|
| `obj+0x88` được ghi bởi **bảng HAL dispatch** tại `0x458E240` | **CÓ** |
| Bảng chọn nhánh theo `*(u32*)(obj+0x6A8)` = **chip arch ID** | **CÓ** |
| 8 slot `+0x60..+0x98` là **con trỏ hàm** | **CÓ** |
| Việc chọn nhánh phụ thuộc **chip architecture** | **CÓ** |

⇒ **Phát hiện có giá trị thực:** `+0x6EA` phụ thuộc vào **một bảng HAL được chọn theo chip arch ID tại `obj+0x6A8`**. Đây là **con đường gián tiếp từ chip identity → display state**, khác với fuse.

Nhưng **chuỗi cụ thể từ `obj+0x88` tới `+0x6EA` chưa đúng** — cần đọc lại chỗ site #5/#6 dùng `a4`.

---

## 5. Đọc lại site #5/#6 — dùng `a4` thế nào

Toàn bộ site #5 (`0x5306D20`) sau khi có `a4`:

```asm
5306d30: ld   a4,0x88(a0)     # a4 = fnptr
5306d34: ld   a3,0x90(a0)     # a3 = fnptr
5306d3c: lhu  a4,0x10(a4)     # ??? 
5306d40: lhu  a1,0x10(a3)     # ???
5306d44: srli a2,a4,0x5       # a2 = a4>>5
5306d48: beq  a2,0x2, 0x53070ac
...
5306d68: andi a5,a4,0x1f      # index = a4 & 0x1F
5306d6c: lui  t1,0x60000
5306d70: srl  t1,t1,a5
5306d7c: andi t3,t1,0x1
5306dd4: mv   t3,a5
5306de0: beqz a3, 0x5307604   # ← nếu a3==0 ...
5306de4: sb   a2,0x6ea(a0)    # *0x6EA = a2 = a4>>5
```

**Chú ý `beqz a3`:** `a3` là **con trỏ hàm** (`fnptr_0x90`). Nó **không bao giờ NULL** sau bảng HAL.

⇒ Nhánh `sb zero` (#7 `0x5307604`) **không đạt được** trên object đã qua bảng HAL.

**Điều này có nghĩa:** `*0x6EA = a4>>5` là **con số suy ra từ byte lệnh**, và `beqz a3` gần như luôn false ⇒ nhánh ghi `0` bị bỏ qua.

---

## 6. Đánh giá lại toàn bộ 11 site sau phát hiện này

| # | Giá trị | Nguồn thật | Đánh giá lại |
|---|---|---|---|
| 5 | `a4>>5` | `lhu` từ **code address + 0x10** | **KHÔNG phải class** — byte lệnh. Ý nghĩa thật: **chưa xác định** |
| 6 | `1` | bit từ cùng giá trị | **KHÔNG phải bit-field** — cùng vấn đề |
| 7,8 | `0` | else-branch | Nhánh #7 gần như **không đạt được** (`beqz a3` false) |
| 1,3,4 | `0` | điều kiện lỗi / registry | **Còn hiệu lực** |
| 2 | `fnptr_0x250()` | gọi hàm thật | **Còn hiệu lực** — nhưng chỉ chạy khi đang != 0 |
| 9,10,11 | `0` | reset trong `this+0x8000` | **Còn hiệu lực** |

---

## 7. Trạng thái cuối của câu hỏi "nguồn `+0x6EA`"

| Ứng viên | Trạng thái sau D2-E |
|---|---|
| **Fuse** | **BÁC BỎ** (không đổi) — 0 site đọc cửa sổ `0x21000` |
| **VBIOS** | **BÁC BỎ** (không đổi) — 0 site tham chiếu ROM |
| **Chipset HAL** | **ĐƯỢC ỦNG HỘ** — nhưng **qua `obj+0x6A8` (arch ID) chọn bảng HAL**, không qua `*(u16*)(fnptr+0x10)` như D2-A nói |
| **devinit** | **CHƯA LOẠI TRỪ** |
| **Product policy** | **CHƯA LOẠI TRỪ** — không đọc SKU trực tiếp |
| **Registry debug key** | **ĐÃ CHỨNG MINH cho site #4** (không đổi) |

### Mệnh đề đúng

> `+0x6EA` được ghi bởi **11 site**. **8 site ghi hằng `0`.** **1 site (#2) không thể tạo trạng thái** (chỉ chạy khi đã `!=0`). **2 site (#5, #6) ghi giá trị suy ra từ một trường đọc qua con trỏ hàm `obj+0x88`/`obj+0x90`** — và trường đó **được chọn bởi bảng HAL theo chip arch ID tại `obj+0x6A8`**.
>
> **`+0x6EA` KHÔNG phải fuse. KHÔNG phải VBIOS.** Nó **phụ thuộc chip architecture** qua bảng HAL, **và** có một debug override từ registry `RMDebugSetSMCMode`.
>
> **Cơ chế chính xác từ `obj+0x88` tới giá trị `+0x6EA` CHƯA XÁC ĐỊNH** — D2-A đưa giả thuyết "bảng phân loại instance", D2-E **bác bỏ** vì `obj+0x88` là con trỏ hàm, không phải con trỏ dữ liệu.

---

## 8. Phép kiểm tiếp theo

### 8.1 T-B6 ĐÃ CHẠY — kết quả

Disassemble 8 slot `obj+0x60..+0x98`:

| Slot | Địa chỉ | Chữ ký quan sát |
|---|---|---|
| `+0x60` | `0x0522FBAC` | **giữa hàm** (không prologue tại đó — slot không align đầu hàm) |
| `+0x68` | `0x0521ABC8` | `addi sp,-0x10`, **`li a0,0x56` rồi `ret`** = **stub `NV_ERR_NOT_SUPPORTED`** |
| `+0x70` | `0x05236F48` | `addi sp,-0xA0`, lưu 12 thanh ghi — hàm lớn |
| `+0x78` | `0x0522E224` | `li a2,0x88 ; li a3,0x40 ; ld s6,0x6b0(a1)` |
| `+0x80` | `0x052357D8` | `li a3,0x4 ; li a2,0xB2 ; jalr` |
| **`+0x88`** | **`0x05232DE0`** | `addi sp,-0x60`, lưu 10 thanh ghi, **`beqz a4`**, **`lw a5,0x14(a4)`** |
| **`+0x90`** | **`0x0522B18C`** | `li a2,0x6F ; li a3,0x238 ; ld s2,0x6b0(a1)` |
| `+0x98` | `0x0522E404` | `li a2,0x8B ; li a3,0xC ; ld s5,0x6b0(a1)` |

**Kết quả quyết định:**

1. Cả 8 slot là **hàm**, không phải dữ liệu. Xác nhận §2.
2. Slot `+0x68` là **stub trả `0x56`** (`NV_ERR_NOT_SUPPORTED`) — tức bảng HAL này **có nhánh "không hỗ trợ"** cho từng method.
3. Slot `+0x88` (`0x05232DE0`) **nhận `a4` là con trỏ params** và đọc `0x14(a4)`. Đây là **hàm xử lý**, không phải struct phân loại.
4. Nhiều slot đọc `0x6B0(a1)` — **`a1` là object thứ hai**, khác `this`.

### 8.2 Kết luận T-B6

> **`obj+0x88` là slot HAL method, không phải con trỏ bảng phân loại.**
> Site #5/#6 đọc `lhu 0x10(fnptr)` — **byte lệnh trong code**, không phải dữ liệu phân loại.
>
> ⇒ **Giả thuyết của D2-A về nguồn `class`/`index` bị bác bỏ hoàn toàn.**
> **Cơ chế thật từ `obj+0x88` tới `+0x6EA` vẫn CHƯA XÁC ĐỊNH.**

### 8.3 Phép kiểm còn lại

| # | Phép kiểm | Trả lời | Trạng thái |
|---|---|---|---|
| **T-B7** | Trace `*(u32*)(obj+0x6A8)` — arch ID nào ứng TU106 | Nhánh HAL nào chọn trên CMP 40HX | Chưa chạy |
| **T-B8** | Xác định `0x5306D20` có thực sự được gọi trên object đã qua HAL không (nếu slot `+0x68` là stub `0x56`, có thể cả nhóm không chạy) | Site #5/#6 có chạy | Chưa chạy |
| **T-B4** | Đọc `/proc/driver/nvidia/params` | Site #4 có đang clear không | **BLOCKED — SSH từ chối** |

**T-B8 là phép kiểm đáng giá nhất:** nếu slot `+0x68` trả `NV_ERR_NOT_SUPPORTED` trong nhánh này, toàn bộ nhóm có thể là code chết trên TU106.

# D2-A — 11 WRITE SITES: DISASSEMBLY + DATAFLOW + CLASSIFICATION

**Firmware:** GSP-RM 615.78.08, inner ELF `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85` (22.901.568 B)
**Tool:** `/usr/lib/llvm-18/bin/llvm-objdump -d --triple=riscv64` → 4.272.758 instructions
**Section:** `.section_task_rm_elf_text_instance`, vaddr `0x4588000`, size `0x1039000`
**Ngày:** 2026-11-06 · offline only

> Đính chính so với D1: D1 ghi "11 `sb 0x6ea`" — **đúng**. Nhưng D1 chưa phân loại site nào ghi giá trị gì, chưa tìm caller, chưa xác định writer khởi tạo. D2 làm phần đó.

---

## 0. Phương pháp

Firmware **stripped, 0 symbol, 7 section marker**. Không có ranh giới hàm trong ELF. Dựng ranh giới bằng prologue scan:

- Mọi hàm biên dịch trong blob này bắt đầu bằng `addi sp, sp, -N` (`rd=x2, rs1=x2, opcode=0x13`).
- Quét toàn bộ 8-hex-byte instruction word → **104.466 prologue**.
- "Function" của một địa chỉ = prologue gần nhất trước nó; "function end" = prologue kế tiếp.

Kiểm chứng gián tiếp: 11 site rơi vào 10 hàm có kích thước 184–1312 B, mỗi hàm có prologue + epilogue hợp lệ. Nếu heuristic sai, ranh giới sẽ cắt giữa lệnh — không xảy ra.

**Giới hạn đã biết:** `.section_task_rm_elf_text_instance` chứa dữ liệu xen kẽ (objdump giải mã vùng cuối `0x55C0000+` thành RVC rác). Mọi phân tích dưới đây chỉ dùng instruction 4-byte, địa chỉ chia hết 4.

---

## 1. Bảng 11 write site

| # | Địa chỉ | Raw | Instruction | Hàm chứa | Size |
|---|---|---|---|---|---|
| 1 | `0x4A128D4` | `23 85 04 6e` | `sb zero, 0x6ea(s1)` | `0x4A127FC` | 244 B |
| 2 | `0x4B6F3EC` | `23 85 a4 6e` | `sb a0, 0x6ea(s1)` | `0x4B6F190` | 1288 B |
| 3 | `0x4C89784` | `23 85 09 6e` | `sb zero, 0x6ea(s3)` | `0x4C896CC` | 312 B |
| 4 | `0x4C95FDC` | `23 85 04 6e` | `sb zero, 0x6ea(s1)` | `0x4C95EFC` | 1312 B |
| 5 | `0x5306DE4` | `23 05 c5 6e` | `sb a2, 0x6ea(a0)` | `0x5306D20` | 760 B |
| 6 | `0x530713C` | `23 05 55 6e` | `sb t0, 0x6ea(a0)` | `0x5307018` | 984 B |
| 7 | `0x5307604` | `23 05 05 6e` | `sb zero, 0x6ea(a0)` | `0x53075F0` | 184 B |
| 8 | `0x53076C4` | `23 05 05 6e` | `sb zero, 0x6ea(a0)` | `0x53076A8` | 656 B |
| 9 | `0x5382D2C` | `23 85 07 6e` | `sb zero, 0x6ea(a5)` | `0x5382C14` | 1128 B |
| 10 | `0x5382F08` | `23 85 05 6e` | `sb zero, 0x6ea(a1)` | `0x5382C14` | 1128 B |
| 11 | `0x538314C` | `23 85 05 6e` | `sb zero, 0x6ea(a1)` | `0x538307C` | 892 B |

**Chỉ 3 site ghi giá trị khác hằng 0:** #2 (`a0`), #5 (`a2`), #6 (`t0`).
**8 site còn lại viết hằng `zero`** — tức "tắt display", không phải "đặt trạng thái".

---

## 2. Dataflow từng site

### Site #1 — `0x4A128D4` `sb zero, 0x6ea(s1)` — CLEAR CÓ ĐIỀU KIỆN

Base: `0x4A12820 mv s1, a0` ⇒ **`s1 = this`** (tham số 1).

```
4a12884: lui a5,0x2
4a12888: add a5,s1,a5
4a1288c: ld  a5,-0x188(a5)      # a5 = *(this + 0x1E78)
4a12890: lbu a5,0x219(a5)       # a5 = *(u8*)(that + 0x219)
4a12894: beqz a5, 0x4a128d8     # nếu 0 -> BỎ QUA, không ghi
4a12898: lbu a5,0x6d7(s1)       # a5 = *(u8*)(this+0x6D7)
4a1289c: beqz a5, 0x4a128d8     # nếu 0 -> BỎ QUA
4a1289c: ld  a5,0x738(s2)       # s2 = a1 = params; con trỏ hàm tại +0x738
4a128a8: jalr a5                # gọi, trả a0
4a128ac: andi a5,a0,0x7
4a128b0: sext.w a0,a0
4a128b4: beqz a5, 0x4a128d8     # nếu (kết quả & 7)==0 -> BỎ QUA
4a128b8..4a128d0:                # log: a0=2, a1=status, a2=0x59710090
4a128d4: sb zero,0x6ea(s1)      # CHỈ ghi khi cả 3 điều kiện đúng
```

**Điều kiện ghi (AND 3 vế):**
1. `*(u8*)(*(this+0x1E78) + 0x219) != 0`
2. `*(u8*)(this+0x6D7) != 0`
3. `(callback_at_params_0x738(this, params) & 7) != 0`

⇒ **Đây là đường thông báo lỗi/fatal**, không phải constructor. Ghi `0` = tắt display sau khi phát hiện lỗi. Không phải nguồn khởi tạo.

---

### Site #2 — `0x4B6F3EC` `sb a0, 0x6ea(s1)` — WRITER CHÍNH, có READBACK

Base: `0x4B6F1E0 mv s1, a0` ⇒ **`s1 = this`**.

```
4b6f3d8: lbu a5,0x6ea(s1)        # ĐỌC giá trị hiện tại
4b6f3dc: beqz a5, 0x4b6f3f0     # nếu ĐANG 0 -> bỏ qua (không bao giờ set từ 0)
4b6f3e0: ld  a5,0x250(s1)       # con trỏ hàm tại this+0x250
4b6f3e4: mv  a0,s1
4b6f3e8: jalr a5                # a0 = kết quả
4b6f3ec: sb  a0,0x6ea(s1)       # GHI LẠI kết quả đó
4b6f3f0: ...                    # tiếp tục init
```

**Đây là site duy nhất mang tính chất "cập nhật trạng thái từ hardware".** Nhưng đọc kỹ:

- Điều kiện tiên quyết: `*(u8*)(this+0x6EA) != 0`. **Nếu đang là 0 thì không vào nhánh này.**
- Nghĩa là site này **không thể** biến 0 thành khác 0. Nó chỉ **ghi đè giá trị khác 0 đã có sẵn** bằng kết quả callback `*(this+0x250)`.

⇒ Site #2 là **consumer + re-writer**, không phải producer. **Không khởi tạo được trạng thái ban đầu.**

**Ngữ cảnh hàm `0x4B6F190`:** prologue lưu 13 thanh ghi (s0–s11), gọi `auipc/jalr` tới `0x4ED7F4C`… rồi `0x4EDB8B8`, kiểm tra `*(u8*)(this+0x5DC-0x8C=0x550)`… đây là **hàm init lớn**, không phải leaf.

---

### Site #3 — `0x4C89784` `sb zero, 0x6ea(s3)` — CLEAR CÓ ĐIỀU KIỆN (2 vế)

Base: `0x4C89768 li s3, 0x51` — **không phải base pointer**; nhánh này là code lỗi (đặt mã lỗi `0x51`), dùng `s3` từ nhánh khác cùng hàm.

```
4c89770: lbu a5,0x6ea(s3)        # đọc hiện tại
4c89774: lw  a4,-0x5c(s0)        # một field khác
4c89778: beqz a5, 0x4c89564      # nếu đang 0 -> thoát
4c8977c: li  a5,0x1
4c89780: beq a4,a5, 0x4c89564    # nếu field == 1 -> thoát
4c89784: sb  zero,0x6ea(s3)      # CHỈ ghi khi: hiện!=0 AND field!=1
```

⇒ **Clear có điều kiện**, thêm một trường hợp: tắt display khi một field khác không bằng 1.
Không phải constructor.

---

### Site #4 — `0x4C95FDC` `sb zero, 0x6ea(s1)` — CLEAR SAU KHI ĐỌC VERSION

Base: `0x4C95FB0 ld s1, -0xa8(s0)` ⇒ `s1 = this` (lưu từ `0x4C95F50 sd a0,-0xa8(s0)`).

```
4c95fb4: lui  a1,0x4134
4c95fbc: addi a1,a1,0x6e8        # a1 = 0x41346E8  ← địa chỉ rodata
4c95fb8: addi a2,s0,-0x9c
4c95fc0: mv   a0,s1
4c95fc8: jalr 0x348(ra)          # gọi hàm đọc, out = *(u32*)(s0-0x9c)
4c95fd0: bnez a0, 0x4c95fe0      # nếu lỗi -> bỏ qua
4c95fd4: lw   a5,-0x9c(s0)       # a5 = giá trị đọc được
4c95fd8: bnez a5, 0x4c96578      # nếu != 0 -> đi nhánh khác (không clear)
4c95fdc: sb   zero,0x6ea(s1)     # CHỈ clear khi giá trị đọc == 0
```

**Phát hiện quan trọng:** site này **clear `0x6EA` khi một giá trị đọc từ `0x41346E8` bằng 0**.

`0x41346E8` nằm trong `.section_task_rm_elf_data_instance` (vaddr `0x4201000`–`0x4588000`) — vùng **data**, không phải rodata. `0x41346E8` < `0x4201000` ⇒ thuộc `.section_task_rm_elf_rodata_instance`. Đây là một **bảng hằng** — cần đọc giá trị để biết nó so cái gì. Xem D2-C.

⇒ Site #4 là **tắt display dựa trên kết quả đọc hằng số**, sau khi đã `0x4C95EFC` khởi tạo một loạt field. Không phải nguồn ban đầu.

---

### Site #5 — `0x5306DE4` `sb a2, 0x6ea(a0)` — WRITER TỪ `lhu 0x10(fnptr)`

> ⚠️ **ĐÍNH CHÍNH (D2-E/T-B6):** phần diễn giải dưới đây — "class = word>>5, index = word&0x1F, decode bảng phân loại" — **ĐÃ BỊ BÁC BỎ**. `obj+0x88` được bảng HAL tại `0x458E348` ghi bằng **địa chỉ hàm** `0x5232DE0` (trong `.rm_text`), nên `lhu 0x10(a4)` đọc **byte lệnh**, không đọc dữ liệu. T-B6 xác nhận cả 8 slot `obj+0x60..+0x98` là HAL method. **Giữ nguyên phần disassembly (đúng); bỏ phần diễn giải.**

Base: `a0` = `this` (không đổi trong hàm).

```asm
5306d20: addi sp,sp,-0x10                # hàm nhỏ, 760 B
5306d30: ld   a4,0x88(a0)                # a4 = this->f_0x88
5306d34: ld   a3,0x90(a0)                # a3 = this->f_0x90
5306d3c: lhu  a4,0x10(a4)                # a4 = *(u16*)(f_0x88 + 0x10)   ← NGUỒN
5306d40: lhu  a1,0x10(a3)                # a1 = *(u16*)(f_0x90 + 0x10)
5306d44: srli a2,a4,0x5                  # a2 = a4 >> 5                   ← class
5306d48: beq  a2,0x2, 0x53070ac          # nếu class==2 -> nhánh khác
5306d60: li   a5,0x1
5306d64: bne  a2,a5, 0x5307020           # nếu class!=1 -> nhánh khác
5306d68: andi a5,a4,0x1f                 # a5 = a4 & 0x1F  = index
5306d6c: lui  t1,0x60000
5306d70: srl  t1,t1,a5                   # t1 = 0x60000000 >> index
5306d7c: andi t3,t1,0x1                  # t3 = bit[index]
...
5306dcc: sb   a6,0x6e6(a0)               # store liên quan
5306de0: beqz a3, 0x5307604              # nếu a3==0 -> sb zero
5306de4: sb   a2,0x6ea(a0)               # *0x6EA = class = (a4>>5)
```

**Đây là writer khởi tạo thật, hai site #5 và #6 cùng một hàm.**

Nguồn: `*(u16*)(this->f_0x88 + 0x10)`, decode:
- `class = word >> 5`
- `index = word & 0x1F`
- bit = `(0x60000000 >> index) & 1`

Với `class == 1`: `0x6EA = 1` (site #6 ghi `t0 = 1`).
Với `class != 1`: `0x6EA = 0` (site #7 `sb zero`).

⇒ **`0x6EA` = phân loại display sub-variant, lấy từ `*(u16*)(this->f_0x88 + 0x10)`.**

**Không phải fuse. Không phải VBIOS. Không phải product policy.** Là **chipset HAL data** — một cấu trúc do HAL/engine enumeration dựng, đọc từ `this+0x88` và `this+0x90`.

---

### Site #6 — `0x530713C` `sb t0, 0x6ea(a0)` — CÙNG CƠ CHẾ, giá trị = 1

```asm
53070ac: andi a6,a4,0x1f                 # a6 = index  (a4 = *(u16*)(f_0x88+0x10))
53070b0: li   a3,0xc0
53070b8: srl  a3,a3,a6                   # a3 = 0xC0 >> index
53070c4: andi a3,a3,0x1
53070d0: beqz a3, 0x53075f8              # nếu bit==0 -> clear path
53070d4: li   t6,0x1
53070d8: li   t5,0x1
53070ec: li   t0,0x1                      # t0 = 1
5307130: andi a5,t1,0x1
5307138: beqz a5, 0x53076c4              # nếu t1 bit==0 -> sb zero
530713c: sb   t0,0x6ea(a0)               # *0x6EA = 1
```

Nguồn: `bit_index = (0xC0 >> (a4 & 0x1F)) & 1` với `a4 = *(u16*)(this->f_0x88 + 0x10)`.

**Hai nhánh của cùng một hàm `0x5306D20` (class==1) và `0x5307018` (class==2)** ghi 1 hoặc 0 tuỳ bit trong cùng một word 16-bit.

---

### Site #7 — `0x5307604` `sb zero, 0x6ea(a0)` — NHÁNH NGƯỢC CỦA #5

```asm
5306de0: beqz a3, 0x5307604     # từ site #5
5307604: sb zero,0x6ea(a0)      # class != 1 -> 0
5307608: beqz a7, 0x5306dec
```

⇒ Đây là **else-branch** của site #5. Cùng nguồn, cùng thời điểm.

### Site #8 — `0x53076C4` `sb zero, 0x6ea(a0)` — NHÁNH NGƯỢC CỦA #6

```asm
5307138: beqz a5, 0x53076c4     # từ site #6
53076c4: sb zero,0x6ea(a0)
53076c8: beqz a3, 0x5307144
```

⇒ **else-branch** của site #6.

---

### Sites #9 #10 — `0x5382D2C` / `0x5382F08` — CÙNG HÀM `0x5382C14`, HAI NHÁNH

Base: `0x5382D18 add a5,a0,a5` với `0x5382D14 lui a5,0x8` ⇒ `a5 = this + 0x8000`.
`0x5382EFC add a1,a0,a1` với `0x5382EF4 lui a1,0x8` ⇒ `a1 = this + 0x8000`.
**Cùng object: `this + 0x8000 + 0x6EA`.**

```asm
5382c14: (prologue, 1128 B)
5382cfc: lui  a4,0x3
5382d00: addi t1,a4,0xc1        # t1 = 0x30C1
5382d08: srl  t1,t1,t3          # shift theo t3 = field index
5382d14: lui  a5,0x8
5382d18: add  a5,a0,a5          # a5 = this+0x8000
5382d28: sb   t4,0x6e9(a5)      # t4 = 0
5382d2c: sb   zero,0x6ea(a5)    # CLEAR
5382d30: sb   t1,0x6eb(a5)
...
5382eec: lui  a2,0xfdf1
5382ef0: slli a2,a2,0x4         # a2 = 0x0FDF10000 → 64-bit
5382ef8: addi a2,a2,-0x100      # a2 = 0x0FDF0FF00
5382efc: add  a1,a0,a1          # a1 = this+0x8000
5382f08: sb   zero,0x6ea(a1)    # CLEAR (nhánh khác)
```

**Nguồn: `t3` = index từ `a3`, dùng `srl` để chọn bit trong hằng `0x30C1` và `0x0FDF0FF00`.**

Đây là **cùng một mẫu**: giá trị `0x6EA` được **clear** và các field lân cận (`0x6E9`, `0x6EB`, `0x6EC`, `0x6EE`, `0x6EF`) được set theo bit trong hằng số.

⇒ **Không phải writer khởi tạo.** Đây là **reset/cleanup path** của một subsystem.

### Site #11 — `0x538314C` — NHÁNH THỨ BA CÙNG PATTERN

```asm
538307c: (prologue)
538312c: lui  a2,0xfdf1
5383130: slli a2,a2,0x4
5383138: addi a2,a2,-0x100
538313c: add  a1,a0,a1          # this+0x8000
5383144: li   t3,0x1
5383148: sb   t3,0x6e9(a1)      # = 1  (khác site #9/#10 ghi 0)
538314c: sb   zero,0x6ea(a1)    # CLEAR
```

⇒ Cùng cơ chế, khác giá trị `0x6E9`.

---

## 3. Phân loại 11 site

| Loại | Sites | Số | Vai trò |
|---|---|---|---|
| **A. Constructor / khởi tạo thật** | #5, #6 | 2 | Ghi `class` từ `*(u16*)(this->f_0x88+0x10)` — **nguồn gốc giá trị** |
| **A'. Else-branch của constructor** | #7, #8 | 2 | Ghi 0 khi class != 1/2 — cùng nguồn, cùng thời điểm |
| **B. Reset / cleanup path** | #9, #10, #11 | 3 | Clear field cùng loạt trong `this+0x8000` |
| **C. Clear có điều kiện (lỗi)** | #1, #3 | 2 | Chỉ ghi khi phát hiện điều kiện bất thường |
| **D. Clear sau khi đọc hằng rodata** | #4 | 1 | So giá trị đọc từ `0x41346E8` |
| **E. Re-write có readback** | #2 | 1 | Chỉ chạy khi đang != 0 — **không tạo được trạng thái** |

**Tổng kết định lượng:**
- **2 site** mang giá trị **khác 0** vào `0x6EA`: #5 (`= class`, có thể 1), #6 (`= 1`).
- **8 site** ghi hằng `0`.
- **1 site** (#2) chỉ ghi đè giá trị đã khác 0.
- **0 site** đọc fuse.
- **0 site** đọc VBIOS.
- **0 site** đọc product-policy/registry/SKU.

---

## 4. Nguồn giá trị `+0x6EA` — trả lời trực tiếp

| Ứng viên | Kết luận | Bằng chứng |
|---|---|---|
| **Fuse** | **BÁC BỎ** | Không site nào đọc cửa sổ `0x21000`, không literal `0x21C04`/`0x820C04`, không `lui 0x21`+`lw 0xC04` (D1 đã chứng minh, D2 xác nhận lại trên 4,27M lệnh) |
| **VBIOS** | **BÁC BỎ** | Không site nào tham chiếu BIT/DCB/ROM; writer duy nhất đọc `this->f_0x88` và `this->f_0x90` — object runtime |
| **Chipset HAL** | **ĐƯỢC ỦNG HỘ MỘT PHẦN** | `obj+0x88`/`obj+0x90` **được chọn bởi bảng HAL dispatch** tại `0x458E240` theo `*(u32*)(obj+0x6A8)` = chip arch ID. Nhưng **cách decode `lhu 0x10(fnptr)` của D2-A đã bị bác bỏ** (fnptr là code, không phải data) — cơ chế thật chưa xác định. Xem `D2_TB2_WHO_WRITES_THIS_0x88.md` |
| **devinit** | **CHƯA LOẠI TRỪ** | `this->f_0x88` có thể do devinit/GSP bootstrap điền. D2 không truy ngược được ai ghi `this+0x88` (xem D2-B) |
| **Product policy** | **CHƯA LOẠI TRỪ** | Không tìm được đọc SKU/CMP/token trong 4,27M lệnh. Nhưng policy có thể đã ảnh hưởng **gián tiếp** qua `this->f_0x88` |

**Mệnh đề trung thực:** `0x6EA` là **phân loại display sub-variant** lấy từ một trường 16-bit trong object runtime. **Nguồn cuối của trường đó chưa xác định** — không phải fuse, không phải VBIOS trực tiếp, có thể là chipset HAL hoặc devinit. **Không được nói nó là fuse. Không được nói nó là hằng số.**

---

## 5. Artifact

- `writers_sites.json` — ranh giới hàm + raw bytes 11 site
- `writers_dataflow.json` — chain base-reg và value-reg mỗi site
- `callers6ea.json` — kết quả tìm caller (rỗng — xem D2-B)

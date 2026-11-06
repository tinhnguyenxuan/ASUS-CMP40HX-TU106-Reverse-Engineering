# D2-B — CALLER ANALYSIS & CALLBACK TABLE

**Firmware:** GSP-RM 615.78.08, inner ELF `cd83bb04…3a2cfe85`
**Ngày:** 2026-11-06 · offline only

---

## 0. Kết quả tìm caller trực tiếp: **0**

Quét toàn bộ 4.272.758 instruction, lọc `jalr`/`jal` 4-byte căn lề, resolve target từ comment của objdump:

```
calls from valid 4B insns:                     111.131
calls whose target is not a valid 4B insn:         270   (decode rác — loại)
calls with valid target:                       110.861
```

Đối chiếu 10 hàm chứa write site:

| Hàm | Caller trực tiếp |
|---|---|
| `0x4A127FC` (W1) | **0** |
| `0x4B6F190` (W2) | **0** |
| `0x4C896CC` (W3) | **0** |
| `0x4C95EFC` (W4) | **0** |
| `0x5306D20` (W5) | **0** |
| `0x5307018` (W6) | **0** |
| `0x53075F0` (W7) | **0** |
| `0x53076A8` (W8) | **0** |
| `0x5382C14` (W9) | **0** |
| `0x538307C` (W10) | **0** |

**KHÔNG có một lời gọi trực tiếp nào tới 10 hàm này trong toàn bộ GSP-RM 615.78.08.**

---

## 1. Kiểm tra giả thuyết "gọi gián tiếp qua con trỏ"

Nếu hàm được gọi qua con trỏ, địa chỉ của nó phải xuất hiện dạng literal 8-byte ở đâu đó. Quét toàn bộ file ELF:

| Hàm | u64 hits | u32 hits |
|---|---|---|
| `0x4A127FC` | 0 | 0 |
| `0x4B6F190` | 0 | 0 |
| `0x4C896CC` | 0 | 0 |
| **`0x4C95EFC`** | **1** | **1** |
| `0x5306D20` | 0 | 0 |
| `0x5307018` | 0 | 0 |
| `0x53075F0` | 0 | 0 |
| `0x53076A8` | 0 | 0 |
| `0x5382C14` | 0 | 0 |
| `0x538307C` | 0 | 0 |

⇒ **Chỉ W4 (`0x4C95EFC`) xuất hiện dưới dạng con trỏ trong dữ liệu.** 9 hàm còn lại **không có địa chỉ literal, không có call site trực tiếp, không có entry trong bảng con trỏ**.

---

## 2. W4 nằm trong bảng con trỏ hàm 28 entry

Vu64 hit: file offset `0x35688` → vaddr **`0x4035688`**, thuộc `.section_task_rm_elf_rodata_instance` (VMA `0x401d000`, file `0x1d000`, size `0x1e4000`).

Xác định ranh giới "run" của các qword trỏ vào code:

```
run start vaddr 0x4035608   end vaddr 0x40356e0   entries = 28
W4 (0x4C95EFC) là entry #16
```

Toàn bộ 28 entry, tất cả trỏ vào `.rm_text` hợp lệ:

```
[ 0] 0x04035608 = 0x000000000531AF1C    [14] 0x04035678 = 0x0000000004C89440
[ 1] 0x04035610 = 0x00000000051CE3C4    [15] 0x04035680 = 0x0000000004C7EF60
[ 2] 0x04035618 = 0x000000000531AF40    [16] 0x04035688 = 0x0000000004C95EFC  <<< W4
[ 3] 0x04035620 = 0x00000000051CE3DC    [17] 0x04035690 = 0x0000000004C7F024
[ 4] 0x04035628 = 0x000000000531AF64    [18] 0x04035698 = 0x0000000004C7DEC0
[ 5] 0x04035630 = 0x00000000051CE414    [19] 0x040356A0 = 0x000000000531AFD0
[ 6] 0x04035638 = 0x00000000051CE44C    [20] 0x040356A8 = 0x000000000531AFF4
[ 7] 0x04035640 = 0x00000000051CE468    [21] 0x040356B0 = 0x000000000531B018
[ 8] 0x04035648 = 0x000000000531AF88    [22] 0x040356B8 = 0x000000000531B03C
[ 9] 0x04035650 = 0x00000000051CE4BC    [23] 0x040356C0 = 0x000000000531B060
[10] 0x04035658 = 0x000000000531AFAC    [24] 0x040356C8 = 0x000000000531B084
[11] 0x04035660 = 0x00000000051CE4D8    [25] 0x040356D0 = 0x000000000531B0A8
[12] 0x04035668 = 0x00000000051CE4F4    [26] 0x040356D8 = 0x000000000531B0CC
[13] 0x04035670 = 0x00000000051CE50C    [27] 0x040356E0 = 0x000000000531B0F0
```

**Đây là bảng callback/vtable 28 slot.** Các địa chỉ `0x531AFxx`, `0x51CE3xx` lặp lại theo nhóm ⇒ bảng được tổ chức theo **cặp (entry, thunk)**, mẫu điển hình của NVOC HAL table.

### 2.1 Bối cảnh ngay trước bảng

```
0x040355E8 = 0x0000000000000008      ← hằng 8
0x040355F0 = 0x00000000040700A0      ← con trỏ rodata
0x040355F8 = 0x00000000052646D0      ← con trỏ code
0x04035600 = 0x0000000000000010      ← hằng 0x10 = 16
0x04035608 = 0x000000000531AF1C      ← BẮT ĐẦU BẢNG 28 ENTRY
```

`8`, `0x10`, `0x040700A0` trước bảng là **metadata mô tả bảng** (kích thước slot / số entry / pointer tới const table). Trùng khớp mẫu dispatch table ở T7 (`const = 0x040704C8`).

### 2.2 Không ai tham chiếu bảng này bằng địa chỉ tuyệt đối

| Địa chỉ | u32 hits | u64 hits |
|---|---|---|
| `0x4035640` | 0 | 0 |
| `0x4035648` | 0 | 0 |
| `0x4035680` | 0 | 0 |
| `0x4035688` (W4 slot) | 0 | 0 |
| `0x4035690` | 0 | 0 |

Và không có cặp `lui`+`addi` nào tính ra `0x4035688` (kiểm bằng cách tính giá trị thật, không phải khớp chuỗi — script đầu tiên của tôi khớp giả 200+ lần, đã sửa).

**Diễn giải:** bảng được truy cập qua **base + index** với base là một offset cố định trong một struct lớn hơn, hoặc qua macro `offsetof`. Địa chỉ tuyệt đối không bao giờ xuất hiện dạng literal.

---

## 3. Ba entry lân cận — chữ ký giống nhau?

| Slot | Địa chỉ | Prologue | Đặc điểm |
|---|---|---|---|
| **#15** | `0x4C7EF60` | `addi sp,sp,-0x20`, lưu s0/s1/s2/ra | Gọi `*(this+0x110)(a1)` rồi early-return nếu lỗi. **Wrapper mỏng.** |
| **#16** | `0x4C95EFC` | `addi sp,sp,-0xE0`, lưu **13 thanh ghi** s0–s11 | **Hàm init lớn** (1312 B). Đọc hằng `0x41346E8`, clear `0x6EA` nếu giá trị == 0. |
| **#17** | `0x4C7F024` | `addi sp,sp,-0x50`, lưu s0–s7 | Đọc `this+0x1FF58`, gọi `*(that+0x178)`, đọc `a1+0x2C0`. **Iterator/walker.** |

⇒ Bảng **không phải** một vtable đồng nhất kiểu C++ (mỗi slot cùng signature). Đây là **bảng callback hỗn hợp** — mỗi slot một chữ ký khác nhau, đúng kiểu NVOC/engine-interface table nơi slot index là hợp đồng, không phải kiểu hàm.

---

## 4. Vì sao 9 hàm còn lại không có caller

Ba khả năng, xếp theo mức bằng chứng:

### (a) Bị **dead-code / strip bởi LTO** — HỖ TRỢ MẠNH

9/10 hàm không có call site trực tiếp, không có địa chỉ literal, không nằm trong bảng. Trong một firmware 22,9 MB đã biên dịch + strip, khả năng cao các nhánh này bị loại trong build TU106 hoặc chỉ tồn tại cho chip khác nhưng linker không xoá.

### (b) Gọi qua **con trỏ tính toán** (base+index từ struct khác) — CHƯA KIỂM CHỨNG

Không loại trừ được. Nhưng không có bằng chứng: nếu vậy phải có một struct chứa địa chỉ các hàm này — **không có literal nào**.

### (c) **Nằm ngoài đường thực thi trên TU106** — HỖ TRỢ

Chữ ký cho thấy các hàm này thuộc đường display init/cleanup. Nếu GSP không bao giờ khởi tạo display object trên CMP 40HX (vì host không gửi control), thì các nhánh này **có thể tồn tại nhưng không được gọi** ngay cả trong GSP.

**Nhưng đây là suy luận, không phải bằng chứng.** Không được dùng làm kết luận.

---

## 5. Chuỗi bị đứt — ghi chính xác

```
CALLER  ──────────────────────────► ĐỨT
   │  (0 lời gọi trực tiếp, 0 địa chỉ literal cho 9/10 hàm)
   ▼
HÀM CHỨA WRITE SITE (10 hàm, xác định được)
   │  dataflow đầy đủ (D2-A)
   ▼
VALUE: *(u16*)(this->f_0x88 + 0x10)   ← nguồn giá trị 0x6EA
   │  ──────────────────────────► ĐỨT (ai ghi this->f_0x88 = CHƯA XÁC ĐỊNH)
   ▼
0x6EA
```

**Hai chỗ đứt, không phải một:**

1. **Không xác định được ai gọi 10 hàm chứa write site.** Không có call site, không có bảng entry cho 9/10.
2. **Không xác định được ai ghi `this->f_0x88`** — trường 16-bit nguồn của `class` và `index`.

Chỗ đứt #2 quan trọng hơn cho câu hỏi gốc: **nếu `this->f_0x88` là object do HAL dựng từ đặc điểm silicon, thì `0x6EA` phản ánh silicon. Nếu do policy dựng, nó phản ánh policy.** D2 **chưa phân biệt được**.

---

## 6. Giới hạn của phân tích này — nêu thẳng

| Giới hạn | Ảnh hưởng |
|---|---|
| Firmware stripped, 0 symbol, 0 `.symtab` | Không có tên hàm; mọi "hàm" là suy ra từ prologue |
| Prologue heuristic `addi sp,sp,-N` | 104.466 prologue trên 4,27M lệnh — hợp lý nhưng chưa đối chứng ground truth |
| `jalr` có thể dùng thanh ghi khác `ra` | 270 call bị loại vì target không hợp lệ; có thể mất vài call thật |
| Không có CFG thật (chỉ linear disassembly) | JALR gián tiếp qua `*(reg+off)` là **tàng hình** — đây chính là loại call mà bảng callback dùng |
| GSP khác bản trên card? | Đã xác minh SHA-256 khớp `modinfo` + `nvidia-smi` |

**Kết luận đúng phạm vi:** "0 caller trực tiếp" là **sự thật đo được trên 4.271.758 instruction**. Nó **không** chứng minh hàm không bao giờ được gọi — chỉ chứng minh **không gọi trực tiếp và không có địa chỉ literal**.

---

## 7. Phép kiểm tiếp theo để đóng chỗ đứt

| # | Phép kiểm | Trả lời |
|---|---|---|
| **T-B1** | Tìm base của bảng 28 entry: quét `lui`+`addi`/`auipc` tạo ra địa chỉ trong `0x40356xx` ± 0x1000, thử cả **base + index** với index từ struct | Ai đọc bảng, và index nào ứng với display |
| **T-B2** | Truy ngược `this+0x88`: quét mọi `sd ...,0x88(reg)` trong `.rm_text`, xem writer có đọc fuse/VBIOS/policy không | Nguồn cuối của `0x6EA` |
| **T-B3** | Đọc hằng `0x41346E8` trong `.rm_rodata` (dùng bởi site #4) | So sánh với cái gì |

`T-B3` là phép kiểm **rẻ nhất và chắc chắn chạy được** — thuần đọc dữ liệu tĩnh, không cần CFG. D2-C làm ngay.

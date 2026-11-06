# D2-C — CALLBACK THẬT & NGUỒN `+0x6EA`: ĐỌC HẰNG SỐ

**Firmware:** GSP-RM 615.78.08, inner ELF `cd83bb04…3a2cfe85`
**Ngày:** 2026-11-06 · offline only

---

## 1. Phát hiện: site #4 đọc **registry key debug**, không đọc silicon

### 1.1 Đường dẫn đầy đủ

```
0x4C95FB0: ld   s1, -0xa8(s0)      # s1 = this
0x4C95FB4: lui  a1, 0x4134
0x4C95FBC: addi a1, a1, 0x6e8      # a1 = 0x41346E8   ← ĐỐI SỐ 2
0x4C95FB8: addi a2, s0, -0x9c      # a2 = &out (u32)
0x4C95FC0: mv   a0, s1             # a0 = this
0x4C95FC4: auipc ra, 0xff94b
0x4C95FC8: jalr 0x348(ra)          # → 0x45E130C
```

### 1.2 Chuỗi tại `0x41346E8`

```
0x041346D0: "EnableDebuggerInterface\0"
0x041346E8: "RMDebugSetSMCMode\0"           ← ĐÂY
0x04134700: "RMDebugSMCDynamicTpcFs\0"
0x041346C0: "RmMigCcConfig\0"
```

`.section_task_rm_elf_rodata_instance`, ngay sau một loạt **tên registry key quen thuộc**. Đối chứng: D1 đã tìm thấy `"RmDisableDisplay"` trong cùng loại blob.

### 1.3 Hàm được gọi `0x45E130C` — chữ ký helper đọc registry

```asm
45e130c: addi sp,sp,-0x30 ; lưu s0-s4,ra
45e1330: beqz a1, 0x45e13a4     # a1 == NULL -> log lỗi + return 0x1F
45e1338: beqz a2, 0x45e1400     # a2 == NULL -> log lỗi + return 0x1F
45e133c: mv   s1,a1             # s1 = key name
45e1340: mv   s3,a0             # s3 = this
45e1344: auipc ra,0xf0b
45e1348: jalr 0x73c(ra)         # -> 0x5382D2C region: lookup/enumerate
45e1350: bnez a0, 0x45e1374     # tìm thấy -> đi tiếp
... (không tìm thấy -> epilogue, return 0)
45e139c: auipc t1,0xfffeb
45e13a0: jr   -0x224(t1)        # tail-call: đọc giá trị, ghi vào *a2
45e13a4: lui  a1,0x58e8 ; addi a1,a1,-0x7f0   # chuỗi lỗi
45e13ac: li   a0,0x1
45e13b0: auipc ra,0xfdf ; jalr 0x128(ra)      # -> 0x5382D2C: ĐÂY LÀ LOG
```

**Đọc được:**
- `(this, keyname, void *out) -> NV_STATUS`, return `0x1F` (`NV_ERR_INVALID_ARGUMENT`) nếu `keyname==NULL || out==NULL`.
- Tra key; nếu có → đọc giá trị qua tail-call; nếu không → return 0 và `*out` giữ nguyên.
- Hàm log dùng chung `0x5382D2C`. Nơi này **nằm ngay trong vùng 0x5382xxx** — cùng vùng với write site #9/#10/#11.

### 1.4 Hệ quả cho câu hỏi `+0x6EA`

Site #4 (`0x4C95FDC sb zero,0x6ea`):

```asm
4c95fd0: bnez a0, 0x4c95fe0     # đọc lỗi -> bỏ qua
4c95fd4: lw   a5,-0x9c(s0)      # a5 = giá trị đọc từ registry
4c95fd8: bnez a5, 0x4c96578     # nếu != 0 -> nhánh khác
4c95fdc: sb   zero,0x6ea(s1)    # nếu == 0 -> clear display state
```

⇒ **`RMDebugSetSMCMode` == 0 ⇒ GSP clear `0x6EA`.**

Đây là **debug override**: nếu registry key này không được set (mặc định trên mọi hệ thống không bật debug), GSP **tắt display state**.

**Không phải fuse. Không phải VBIOS. Không phải chipset HAL. Là registry debug key.**

---

## 2. Nhánh 3 điều kiện trước đó — ai chặn site #4

Site #4 có 3 cửa thoát phía trước:

```asm
4c95f74: lbu a5,0x6c8(s1)          # this+0x6C8
4c95f78: bnez a5,0x4c95fb0         # !=0 -> NHẢY TỚI site #4

4c95f7c: lui a5,0x5
4c95f80: add a5,s1,a5
4c95f84: lbu a5,-0x92(a5)          # *(u8*)(this+0x4F6E)
4c95f8c: bnez a5,0x4c95fb0         # !=0 -> tới site #4

4c95f90: ld   a5,0x310(s6)
4c95f94: lbu  a5,0x21(a5)          # *(u8*)(*(a1+0x310) + 0x21)
4c95f98: bnez a5,0x4c95fb0         # !=0 -> tới site #4

4c95f9c: ld   a5,0x2b0(s6)
4c95fa4: jalr a5                    # callback tại a1+0x2B0
```

**Nếu cả 3 field đều 0**, hàm gọi `*(a1+0x2B0)` trước rồi mới tới site #4. Đây là **chuỗi quyết định** đầy đủ: 3 cờ + 1 callback + registry key.

`a1` (s6) là **tham số 2** của hàm — một object/cấu hình khác `this`.

---

## 3. Callback lấy Display IP version — đối chiếu TU106

Handler `0x04B9F5CC` (D1) gọi qua `*(base+0x1F50)`:

```asm
4b9f634: ld   a1,-0xb0(s1)          # s1 = base+0x2000  => a1 = *(base+0x1F50)
4b9f638: auipc ra,0xe7
4b9f63c: jalr -0x338(ra)             # → target
```

Resolve: `0x4B9F638 + 0xE7000 - 0x338` = **`0x4C86300`** (objdump in kèm `<...+0x6fe300>`, và `0x4588000+0x6FE300 = 0x4C86300` — khớp cả hai cách).

Disassembly `0x4C86300` (toàn hàm, 0x34 B):

```asm
4c86300: addi sp,sp,-0x10 ; sd s0,0x8(sp) ; addi s0,sp,0x10
4c8630c: ld   a5,0x2f0(a1)        # a5 = *(params + 0x2F0)
4c86314: lbu  a0,0x0(a5)          # a0 = a5[0]
4c86318: beqz a0, 0x4c86328       # nếu 0 -> return 0
4c8631c: lbu  a3,0x1(a5)          # a3 = a5[1]
4c86320: bnez a3, 0x4c86334       # nếu !=0 -> nhánh sâu
4c86324: lbu  a0,0x2(a5)          # a0 = a5[2]
4c86328: ... ret                   # return a0
4c86334: lui  a3,0x2
4c86338: add  a5,a4,a3            # a5 = this + 0x2000
4c8633c: ld   a5,0x208(a5)        # a5 = *(this+0x2208)
4c86340: add  a5,a5,a3
4c86344: ld   a5,0x160(a5)        # *(that + 0x160+0x2000)
4c86348: beqz a5, 0x4c86398
4c8634c: lbu  a5,0x18(a5)         # byte tại +0x18
4c86350: addi a5,a5,-0x1
4c86354: seqz a5,a5               # (byte == 1)
```

⇒ **Callback thật là `0x4C86300`** — một hàm **tra bảng byte** tại `*(params+0x2F0)`, trả `a5[0]`, `a5[2]`, hoặc kết quả nhánh sâu. **Không đọc fuse, không đọc VBIOS, không đọc register.** Đây là **bảng mô tả display config trong bộ nhớ**.

Điều quan trọng: `a5[0] == 0` ⇒ trả `0` ⇒ `ipVersion = 0`. Nghĩa là **chỉ cần byte đầu của bảng tại `*(params+0x2F0)` bằng 0 là display coi như không có**.

### 3.1 Ba lớp của đường lấy ipVersion

```
host RM  ──(control 0x20800A4B)──►  GSP handler 0x04B9F5CC
                                        │
                                        ├─ s3 = *(base+0x1F60)
                                        ├─ flag = *(u8*)(base+0x6EA)   ← D2-A đã truy nguồn
                                        └─ ipVersion = *(base+0x1F50)(...)   ← callback slot
```

**Đây là 3 nguồn độc lập, không phải 1.** Ngay cả nếu `0x6EA != 0`, `*(base+0x1F60)` vẫn có thể NULL ⇒ vẫn trả 0.

### 3.2 Đối chiếu chip TU106

GSP firmware `gsp_tu10x.bin` là **build dành riêng cho TU10x** (tên file do driver chọn theo chip). Trong ELF có **3 vùng text riêng biệt**:

| Section | VMA | Size | Vai trò |
|---|---|---|---|
| `.ga100_text` | `0x4005000` | `0x1414` | patch code cho GA100 |
| `.tu10x_text` | `0x4007000` | `0x1414` | **patch code cho TU10x** |
| `.tu10x_resident_text` | `0x400E000` | `0x3000` | resident init cho TU10x |
| `.ga100_resident_text` | `0x400A000` | `0x3000` | resident init cho GA100 |

⇒ Firmware **có nhánh code riêng cho TU10x**. Đây là bằng chứng firmware biết chip. Nhưng câu hỏi "callback nào được chọn trên TU106" **vẫn chưa trả lời được** vì:

- `*(base+0x1F50)` được nạp **runtime** từ một struct, không phải hằng biên dịch.
- Không có literal trong ELF trỏ tới một callback cụ thể cho slot này.
- `.tu10x_text` chỉ 5.140 B — quá nhỏ để chứa toàn bộ display HAL; các hàm display dùng chung nằm ở `.rm_text`.

**Kết luận trung thực:** firmware có nhánh TU10x, nhưng **callback cụ thể cho slot `+0x1F50` chưa xác định được bằng phân tích tĩnh** (nạp động).

---

## 4. Trả lời trực tiếp: `+0x6EA` đến từ đâu

| Nguồn | Kết luận | Bằng chứng |
|---|---|---|
| **Fuse** | **BÁC BỎ** | 0 site đọc cửa sổ `0x21000`; 0 literal `0x21C04`/`0x820C04`; không `lui 0x21`+`lw 0xC04` trên 4,27M lệnh |
| **VBIOS** | **BÁC BỎ** | 0 site tham chiếu BIT/DCB/ROM/nvkm bios |
| **Chipset HAL** | **ĐƯỢC ỦNG HỘ (writer khởi tạo)** | Site #5/#6: `class = *(u16*)(this->f_0x88+0x10) >> 5`, `index = word & 0x1F` — decode bảng instance |
| **devinit** | **CHƯA LOẠI TRỪ** | `this->f_0x88` có thể do devinit điền; **chưa truy được writer** |
| **Product policy** | **CHƯA LOẠI TRỪ, nhưng KHÔNG trực tiếp** | Không đọc SKU/CMP; nhưng `this->f_0x88` có thể phản ánh policy |
| **Registry debug key** | **ĐÃ CHỨNG MINH cho site #4** | `"RMDebugSetSMCMode"` tại `0x41346E8`; helper `0x45E130C` = `(this,key,out)->status` |

### 4.1 Bảng phân loại cuối cùng cho giá trị `+0x6EA`

| Writer | Giá trị ghi | Nguồn | Phân loại |
|---|---|---|---|
| #5 `0x5306DE4` | `a2 = class` | `*(u16*)(this->f_0x88+0x10)>>5` | **Khởi tạo — chipset HAL data** |
| #6 `0x530713C` | `t0 = 1` | bit trong cùng word, `0xC0>>index` | **Khởi tạo — chipset HAL data** |
| #7 `0x5307604` | `0` | else-branch của #5 | else của khởi tạo |
| #8 `0x53076C4` | `0` | else-branch của #6 | else của khởi tạo |
| #9 `0x5382D2C` | `0` | hằng `0x30C1>>idx`, `0x0FDF0FF00>>idx` | **Reset/cleanup** |
| #10 `0x5382F08` | `0` | cùng bộ hằng | **Reset/cleanup** |
| #11 `0x538314C` | `0` | cùng bộ hằng | **Reset/cleanup** |
| #1 `0x4A128D4` | `0` | 3 điều kiện lỗi | **Clear khi lỗi** |
| #3 `0x4C89784` | `0` | hiện!=0 AND field!=1 | **Clear có điều kiện** |
| #4 `0x4C95FDC` | `0` | **`"RMDebugSetSMCMode"` == 0** | **Debug override** |
| #2 `0x4B6F3EC` | `a0` = `*(this+0x250)()` | chỉ khi đang != 0 | **Re-write, không tạo trạng thái** |

**Chỉ 2 site tạo giá trị khác 0.** Cả hai lấy từ `*(u16*)(this->f_0x88 + 0x10)`.

---

## 5. Điều này đóng được gì và KHÔNG đóng được gì

### Đóng được

1. `+0x6EA` **không phải** cờ fuse đọc trực tiếp. 0 site đọc fuse.
2. `+0x6EA` **không phải** dữ liệu VBIOS. 0 site tham chiếu ROM.
3. **8/11 site** chỉ ghi hằng `0` — không mang thông tin vào.
4. **Site #2 không thể biến 0 thành khác 0** (đọc trước, thoát nếu 0) — nên không thể là producer của trạng thái ban đầu.
5. **Site #4 phụ thuộc registry debug key `RMDebugSetSMCMode`** — đây là **đường phần mềm**, chứng minh có ít nhất một con đường khiến GSP tự tắt display mà không liên quan silicon.

### Chưa đóng được

1. **Ai gọi 10 hàm chứa write site?** 0 caller trực tiếp, 0 địa chỉ literal cho 9/10.
2. **Ai ghi `this->f_0x88`?** — nguồn cuối của `class`/`index`. Chưa truy.
3. **Callback nào thực sự nạp vào `*(base+0x1F50)`?** — nạp động.
4. **`ipVersion` thật của CMP 40HX là bao nhiêu?** — chưa đo.

### Mệnh đề trung thực

> `+0x6EA` là **phân loại display sub-variant** lấy từ một trường 16-bit trong object runtime (`this->f_0x88 + 0x10`), **cộng** với ít nhất **một debug override đọc từ registry**. Nó **không phải fuse**, **không phải VBIOS**. Nguồn cuối của trường 16-bit đó **chưa xác định** — có thể chipset HAL, có thể devinit, có thể bị policy ảnh hưởng gián tiếp.

**Không được kết luận** `0x6EA = 0` trên CMP 40HX chỉ vì `0x021C04 = 1`. Hai thứ **độc lập** — đây chính là điểm D1 chưa tách được và D2 tách ra được.

---

## 6. Phép kiểm còn lại (rẻ nhất trước)

| # | Phép kiểm | Trả lời | Chi phí |
|---|---|---|---|
| **T-B2** | Quét `sd reg,0x88(reg2)` trong `.rm_text`, tìm writer của `this->f_0x88` | Nguồn cuối của `class` | Trung bình |
| **T-B1** | Tìm base bảng 28 entry qua `lui+addi` tính đúng (không khớp chuỗi) | Ai đọc bảng, slot nào là display | Trung bình |
| **T-B4** | Kiểm registry key `RMDebugSetSMCMode` có tồn tại trên target không (`/proc/driver/nvidia/params`) | Site #4 có đang clear không | **Rất rẻ — read-only** |
| **T-B1-run** | Gọi control `0x20800A4B` khi audited (xem D2-D) | `ipVersion` thật | Cần audit ABI trước |

`T-B4` là phép kiểm **miễn phí**: chỉ đọc file trong `/proc`. Nếu key không tồn tại, site #4 **đang clear** `0x6EA` trên máy này — một phát hiện có ý nghĩa trực tiếp.

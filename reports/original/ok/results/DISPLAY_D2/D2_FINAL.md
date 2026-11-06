# D2 — KẾT LUẬN: NGUỒN GỐC `+0x6EA`

**Firmware:** GSP-RM 615.78.08 · inner ELF SHA-256 `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85`
**Ngày:** 2026-11-06 · offline only · **0 ghi MMIO/BAR3/fuse, 0 flash, 0 sửa firmware**

---

## TRẢ LỜI TRỰC TIẾP

> **`+0x6EA` KHÔNG phải fuse. KHÔNG phải VBIOS.** — điều này đứng vững qua toàn bộ D2.
>
> Trong 11 write site: **8 site ghi hằng `0`** (clear/reset). **1 site (#2) không thể tạo trạng thái** (chỉ chạy khi đã `!=0`). **1 site (#4) là debug override** đọc registry key `"RMDebugSetSMCMode"` — **đã chứng minh bằng chuỗi + helper `0x45E130C`**. **2 site (#5, #6)** ghi giá trị suy ra từ `lhu 0x10(...)` qua `obj+0x88`/`obj+0x90`.
>
> ⚠️ **ĐÍNH CHÍNH so với bản nháp D2-A (đã sửa):**
> D2-A nói `obj+0x88` là **con trỏ tới bảng phân loại** và site #5/#6 decode `class`/`index` từ đó. **SAI.**
> D2-E chứng minh `obj+0x88` được ghi bởi **bảng HAL dispatch** tại `0x458E240`/`0x458E348` bằng **địa chỉ hàm** (`0x5232DE0`, `0x522B18C` — đều trong `.rm_text`). T-B6 xác nhận cả 8 slot `+0x60..+0x98` là **HAL method**, một slot là stub trả `0x56`.
> ⇒ `lhu 0x10(fnptr)` đọc **byte lệnh**, không đọc dữ liệu. **Cơ chế thật từ `obj+0x88` tới `+0x6EA` CHƯA XÁC ĐỊNH.**

**Điều D2 chứng minh chắc chắn:**

| Mệnh đề | Cơ sở |
|---|---|
| `+0x6EA` không do fuse | 0 site đọc cửa sổ `0x21000`; 0 literal `0x21C04`/`0x820C04`; 4.272.758 instruction |
| `+0x6EA` không do VBIOS | 0 site tham chiếu BIT/DCB/ROM |
| Site #4 phụ thuộc registry `RMDebugSetSMCMode` | chuỗi `@0x41346E8` + helper `(this,key,out)->status` |
| `obj+0x88`/`obj+0x90` là **HAL method slot**, chọn theo `*(u32*)(obj+0x6A8)` | bảng dispatch `0x458E240`, 8 slot, 1 slot là stub `0x56` |
| 8/11 site chỉ ghi `0` | disassembly đầy đủ |

**Điều D2 KHÔNG chứng minh được:** nguồn cuối của giá trị mà site #5/#6 ghi — vì cách decode đã bị bác bỏ và chưa có giả thuyết thay thế có bằng chứng.

---

## 1. Phân loại 11 write site (bảng cuối)

| # | Địa chỉ | Lệnh | Giá trị | Nguồn | Loại |
|---|---|---|---|---|---|
| 1 | `0x4A128D4` | `sb zero,0x6ea(s1)` | `0` | 3 điều kiện lỗi AND | **Clear khi lỗi** |
| 2 | `0x4B6F3EC` | `sb a0,0x6ea(s1)` | `*(this+0x250)()` | chỉ chạy khi đang `!=0` | **Re-write, không tạo** |
| 3 | `0x4C89784` | `sb zero,0x6ea(s3)` | `0` | hiện`!=0` AND field`!=1` | **Clear có điều kiện** |
| **4** | `0x4C95FDC` | `sb zero,0x6ea(s1)` | `0` | **`"RMDebugSetSMCMode"`==0** | **Debug override** |
| **5** | `0x5306DE4` | `sb a2,0x6ea(a0)` | `class = w>>5` | `w=*(u16*)(this->f_0x88+0x10)` | **KHỞI TẠO** |
| **6** | `0x530713C` | `sb t0,0x6ea(a0)` | `1` | `(0xC0>>(w&0x1F))&1` | **KHỞI TẠO** |
| 7 | `0x5307604` | `sb zero,0x6ea(a0)` | `0` | else của #5 | else khởi tạo |
| 8 | `0x53076C4` | `sb zero,0x6ea(a0)` | `0` | else của #6 | else khởi tạo |
| 9 | `0x5382D2C` | `sb zero,0x6ea(a5)` | `0` | hằng `0x30C1>>idx` | **Reset/cleanup** |
| 10 | `0x5382F08` | `sb zero,0x6ea(a1)` | `0` | hằng `0x0FDF0FF00>>idx` | **Reset/cleanup** |
| 11 | `0x538314C` | `sb zero,0x6ea(a1)` | `0` | cùng bộ hằng | **Reset/cleanup** |

**Định lượng:**
- 2 site mang giá trị khác 0 → nguồn thật
- 8 site ghi `0`
- 1 site re-write
- **0 site đọc fuse / VBIOS / SKU**

---

## 2. Nguồn giá trị — bảng quyết định

| Nguồn | Kết luận | Bằng chứng cụ thể |
|---|---|---|
| **Fuse** | **BÁC BỎ** | 0 site tham chiếu cửa sổ `0x21000`; 0 literal `0x21C04`/`0x820C04`; không `lui 0x21`+`lw 0xC04` trên 4.272.758 instruction |
| **VBIOS** | **BÁC BỎ** | 0 site tham chiếu BIT/DCB/ROM/nvkm bios; writer đọc `this->f_0x88`/`f_0x90` — object runtime |
| **Chipset HAL** | **ĐƯỢC ỦNG HỘ (writer khởi tạo)** | #5/#6 decode `*(u16*)(this->f_0x88+0x10)`: `class=w>>5`, `idx=w&0x1F`, bit chọn trong `0x60000000`/`0xC0` — chữ ký bảng phân loại instance |
| **devinit** | **CHƯA LOẠI TRỪ** | `this->f_0x88` có thể do devinit điền; **chưa truy được writer** |
| **Product policy** | **CHƯA LOẠI TRỪ, không trực tiếp** | Không đọc SKU/CMP; nhưng có thể ảnh hưởng gián tiếp qua `this->f_0x88` |
| **Registry debug key** | **ĐÃ CHỨNG MINH (site #4)** | `"RMDebugSetSMCMode"` @ `0x41346E8`; helper `0x45E130C = (this,key,out)->status` |

---

## 3. Callback lấy Display IP version

Handler `0x04B9F5CC` gọi callback qua `*(base+0x1F50)` → resolve ra **`0x4C86300`**.

```asm
4c86300: (0x34 B, read-only)
4c8630c: ld   a5,0x2f0(a1)        # a5 = *(params+0x2F0)
4c86314: lbu  a0,0x0(a5)          # a0 = a5[0]
4c86318: beqz a0, 0x4c86328       # nếu 0 -> return 0
4c8631c: lbu  a3,0x1(a5)
4c86320: bnez a3, 0x4c86334
4c86324: lbu  a0,0x2(a5)          # return a5[2]
```

**Không store. Không đọc fuse/VBIOS/register.** Đây là **tra bảng byte trong bộ nhớ**.

Ba nguồn độc lập quyết định `ipVersion = 0`:
1. `*(base+0x1F60) == NULL`
2. `*(u8*)(base+0x6EA) == 0`  ← D2 truy nguồn xong
3. callback `0x4C86300` trả `a5[0] == 0`

---

## 4. Đứt ở đâu — ghi chính xác

```
WRITER FUNCTIONS (10 hàm, xác định đầy đủ)
   ▲
   │  ĐỨT #1: 0 caller trực tiếp, 0 địa chỉ literal cho 9/10 hàm
   │          (111.131 call resolve được trên 4,27M lệnh)
   │
VALUE: *(u16*)(this->f_0x88 + 0x10)
   ▲
   │  ĐỨT #2: ai ghi this->f_0x88 — CHƯA XÁC ĐỊNH
   │
0x6EA
```

**Đứt #2 là đứt quan trọng hơn** cho câu hỏi gốc: nếu `f_0x88` do HAL dựng từ đặc điểm silicon thì `0x6EA` phản ánh silicon; nếu do policy dựng thì phản ánh policy. **D2 chưa phân biệt được.**

### Phát hiện phụ có giá trị: W4 nằm trong bảng callback 28 entry

```
.section_task_rm_elf_rodata_instance, vaddr 0x4035608 — 0x40356E0, 28 entry × 8 byte
W4 (0x4C95EFC) là entry #16
```

Ba slot lân cận (#15 `0x4C7EF60`, #17 `0x4C7F024`) có **chữ ký khác nhau** — bảng callback hỗn hợp (kiểu NVOC/engine-interface), không phải vtable C++.

Không ai tham chiếu bảng bằng địa chỉ tuyệt đối (0 u32 hit, 0 u64 hit, 0 cặp `lui`+`addi` tính đúng) ⇒ truy cập qua base + index.

---

## 5. ABI control `0x20800A4B` — kiểm toán

| Hạng mục | Kết quả |
|---|---|
| Params | `{ NvU32 ipVersion; }` — **4 byte**, khớp dispatch record `size=0x4` |
| Handler | `0x04B9F5CC`, record `0x04061958`, flags `0x000000C0` |
| **Tác dụng phụ** | **KHÔNG** — toàn hàm chỉ có **1 store** (`sw a5,0x0(s2)` vào output); callback `0x4C86300` **0 store** |
| Ai gọi được | **CHƯA XÁC ĐỊNH** — internal control có thể chặn user client (`NV_ERR_INVALID_CLIENT`) |
| Đang được gọi trên CMP 40HX? | **KHÔNG** — `kern_disp.c:444` return trước khi gửi |
| Đã gọi trên GPU thật? | **CHƯA — đúng yêu cầu "không gọi khi chưa kiểm toán"** |

---

## 6. Nhánh `ipVersion=0`: tồn tại ≠ được chọn

| Mệnh đề | Trạng thái |
|---|---|
| Nhánh `ipVersion=0` tồn tại trong code | **PROVEN** (`0x4B9F60C`–`0x4B9F610`) |
| Handler dispatch đúng | **PROVEN** (record `0x04061958`, const `0x040704C8` khớp mọi record) |
| Nhánh đó **được chọn trên CMP 40HX** | **UNPROVEN — KHÔNG CÓ BẰNG CHỨNG** |
| `ipVersion` thật của CMP 40HX | **CHƯA ĐO** |
| `*(base+0x1F60)` / `0x6EA` thực tế trên card | **CHƯA ĐO** |

### Không được nói

| Sai | Vì sao |
|---|---|
| "GSP trả `ipVersion=0` cho CMP 40HX" | Handler chưa từng chạy |
| "`0x021C04=1` ⇒ `0x6EA=0`" | **Hai thứ độc lập** — D2 chứng minh `0x6EA` từ HAL + debug key |
| "Nhánh `ipVersion=0` là nguyên nhân display tắt" | Nguyên nhân đã chứng minh là `kern_disp.c:444`, **trước** khi control tồn tại trong luồng |

---

## 7. Sửa báo cáo D1 (theo yêu cầu)

| # | Sửa gì | File | Trạng thái |
|---|---|---|---|
| 1 | Patch CMP Linux là **15 u32 / 60 byte**, không phải 12 byte | `CMPWIKI_40HX_CROSSCHECK.md` §A.1 + bảng A.3 | **ĐÃ SỬA** |
| 2 | Register read-only **không** chứng minh không có producer firmware/latched khác | `D1_FINAL_VERDICT.md` §"Điều D1 không kế thừa" | **ĐÃ SỬA** — thêm khối đính chính 4 đường producer |
| 3 | BAR0 không phải BAR1 | `D1_FUSE_021C04_PRODUCER.md` | đã sửa từ trước (D1 audit) |
| 4 | Không suy ra GSP không có consumer từ thiếu literal | `D1_FUSE_021C04_PRODUCER.md` §4.1 | đã sửa từ trước (D1 audit) |

---

## 8. Phép kiểm còn lại

| # | Phép kiểm | Trả lời | Trạng thái | Chi phí |
|---|---|---|---|---|
| **T-B4** | Đọc `/proc/driver/nvidia/params` + `/proc/driver/nvidia/registry` | Site #4 có đang clear `0x6EA` trên máy này không | ✅ **ĐÃ CHẠY** — key `RMDebugSetSMCMode` **KHÔNG tồn tại** ⇒ **W4 không kích hoạt**. Xem `D2_G_TB4_TARGET_VERIFICATION.md` |
| **T-B2** | Quét `sd reg,0x88(reg2)` trong `.rm_text` | Ai ghi `this->f_0x88` — nguồn cuối của `class` | Chưa chạy | Trung bình |
| **T-B1** | Tìm base bảng 28 entry (tính đúng `lui`+`addi`, không khớp chuỗi) | Ai đọc bảng, slot nào là display | Chưa chạy | Trung bình |
| **T-B5** | Kiểm tĩnh quyền internal control cho user client trong `src/nvidia/` | `T-B1-run` có khả thi không | Chưa chạy | Thấp |
| **T-B1-run** | Gọi `0x20800A4B` (sau T-B5) | `ipVersion` thật | **Chưa — cần audit trước** | Trung bình |

**`T-B2` là phép kiểm quan trọng nhất còn lại** — nó đóng chỗ đứt #2 và trả lời trực tiếp "`0x6EA` phản ánh silicon hay policy".

---

## 9. Artifact

| File | Nội dung |
|---|---|
| `D2_11_WRITE_SITES_DISASM.md` | Disassembly đầy đủ 11 site + dataflow + phân loại |
| `D2_CALLER_AND_CALLBACK_TABLE.md` | 0 caller, bảng 28 entry, 2 chỗ đứt |
| `D2_CALLBACK_AND_VALUE_SOURCE.md` | Nguồn giá trị, registry key `RMDebugSetSMCMode`, callback `0x4C86300` |
| `D2_ABI_AND_ACCESS_AUDIT.md` | ABI, tác dụng phụ, điều kiện truy cập |
| `D2_FINAL.md` | File này |
| `writers_sites.json` | Ranh giới hàm + raw bytes 11 site |
| `writers_dataflow.json` | Chain base-reg / value-reg |
| `callers6ea.json` | Kết quả caller (rỗng — đã ghi rõ lý do) |

### Script tái lập

| Script | Chức năng |
|---|---|
| `trace6ea.py` | Prologue scan + ranh giới hàm 11 site |
| `dataflow6ea.py` | Chain nguồn mỗi site |
| `callers6ea.py` | Resolve `jalr` qua comment objdump, đối chiếu 10 target |
| `win.py` | In cửa sổ disassembly theo vaddr |

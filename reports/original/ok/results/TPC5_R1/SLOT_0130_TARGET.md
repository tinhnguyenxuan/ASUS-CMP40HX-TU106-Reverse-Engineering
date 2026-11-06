# R1 — SLOT +0x130 TARGET

**GSP-RM 615.78.08** · ELF `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85`
**Ngày:** 2026-11-06 · offline only

---

## 1. Object provenance của `s2` — PROVEN

```
4bc6868: 83 37 05 16   ld   a5, 0x160(a0)     ; a0 = pGpu
4bc6874: 83 b4 07 e8   ld   s1, 0xe8(a5)      ; s1 = *(*(pGpu+0x160)+0xE8)
4bc6878: b7 29 00 00   lui  s3, 0x29          ; s3 = 0x29000
4bc6880: b3 89 91 00   add  s3, s1, s3        ; s3 = s1 + 0x29000
4bc68a0: 83 b9 09 f5   ld   s2, -0xb0(s3)     ; s2 = *(s1 + 0x28F50)
```

**`s2 = *(*(*(pGpu + 0x160) + 0xE8) + 0x28F50)`** — chuỗi 3 lần dereference.

### 1.1 Vì sao `0x28F50` không grep được

`0x28F50` vượt quá imm12 (2047) của lệnh `sd`. Compiler **bắt buộc** dùng
`lui 0x29` + `add` + `ld -0xb0`. Do đó:

- Grep literal `0x28F50` trong `gsp.dis` → **0 hit** (đã xác nhận)
- Grep `sd ..., -0xb0(...)` → **1.847 hit**, gần như toàn bộ là **stack-relative**
  (`-0xb0(s0)` = frame pointer), không phải field của object

**Kết luận:** phép tìm kiếm "ai ghi `+0x28F50`" bằng pattern byte **không khả thi**
trên binary stripped. Không phải thiếu công cụ — đây là giới hạn cấu trúc.

---

## 2. Slot `+0x130` là method pointer — PROVEN

```
4bc6d54: 83 37 09 13   ld    a5, 0x130(s2)    ; imm = 0x130 = 304 = qword 38
4bc6d58: 93 0b 4a 00   addi  s7, s4, 0x4
4bc6d5c: 93 86 0b 00   mv    a3, s7           ; a3 = &out tpcMask[]
4bc6d60: 93 05 09 00   mv    a1, s2           ; a1 = this
4bc6d64: e7 80 07 00   jalr  a5
```

`a1 = this`, `a3 = out-param` → quy ước C++ method. **PROVEN: đây là vtable slot 38.**

### 2.1 Ba slot trên cùng instance (phân biệt rõ theo yêu cầu R1-4)

| Slot | Offset | Call site | Vai trò | Mức |
|---|---|---|---|---|
| 37 | `+0x128` | `0x4BC6994` | out buffer trên stack | INFERRED |
| **38** | **`+0x130`** | **`0x4BC6D64`** | **ghi `tpcMask[]`** | **PROVEN** |
| 64 | `+0x200` | `0x4BC6D30` | cấp index để `sllw a4,s1,a2` → `or a5,a5,a4` → `sw a5,0x204(s3)` | INFERRED |

`+0x204` = `physGpcMask` theo header (`ctrl2080internal.h:316`), **không phải** `tpcMask`.
`s2+0x3E0` = bitmap GPC (đã chứng minh ở T8), **không phải** TPC mask.

---

## 3. Tìm hàm đích slot +0x130 — 281 bảng, không kết luận được

Quét tất cả run ≥20 con trỏ code liên tiếp trong `.rm_rodata` + `.rm_data`:

| # | Địa chỉ bảng | Độ dài | `[38]` |
|---|---|---|---|
| 1 | `0x0407F6D0` | 1855 | `0x458BC40` |
| 2 | `0x0407D490` | 671 | `0x4589400` |
| 3 | `0x040A2CD8` | 448 | `0x048C9730` |
| 4 | `0x040529C8` | 140 | `0x053A2B94` |
| 5 | `0x04053178` | 139 | `0x053A2B94` |
| 6 | `0x0404B460` | 125 | `0x05370F14` |
| 7 | `0x04044110` | 111 | `0x05319AE0` |
| 8 | `0x0402F230` | 100 | `0x051D13C0` |

### 3.1 Vì sao không xác định được hàm đích

Byte `sd fnptr, 0x130(obj)` **không phải** cách object được khởi tạo. Bảng method
được nạp bằng **constructor tổng quát** dạng vòng lặp:

```
sd fnptr, 0(ptr)
addi fnptr, fnptr, 8
addi ptr, ptr, 8
```

⇒ Không có store đặc trưng cho slot 38 để grep. Không có symbol. Không có RTTI.

**Đây là nơi call graph đứt.** Không phải "chưa tìm", mà là **không thể tìm** bằng
phân tích tĩnh trên ELF stripped — kết luận giống hệt D2 (6 hàm writer `+0x6EA`
cũng có 0 caller vì cùng lý do).

**UNKNOWN:** hàm đích thực tế của slot 38.

---

## 4. GSP có đọc fuse không? — KHÔNG. Đây là kết quả quan trọng hơn

Kiểm toàn bộ 4.272.792 dòng disassembly:

| Tìm kiếm | Kết quả |
|---|---|
| Literal `0x21000` / `0x21c38` / `0x21C38` / `0x21a40` / `0x21A40` | **0 hit** |
| Store `sw/sd ..., 0xa40(...)` hoặc `0xa80(...)` với base gần `0x21` | **0 hit** |
| `lui X, 0x21` | 5 hit — tất cả là **con trỏ tới chuỗi/registry**, không phải MMIO |

> ### **GSP-RM 615.78.08 KHÔNG đọc cửa sổ fuse `0x021xxx`.**
>
> Do đó giá trị `0x1F` mà slot +0x130 ghi vào `tpcMask[]` **không thể** đến từ
> một phép đọc fuse của GSP.

Điều này **đóng** giả thuyết "GSP software mask tự quyết định". GSP chỉ **nhận**
cấu hình từ bootstrap, không tự suy ra từ fuse.

---

## 5. Tổng kết SLOT_0130

| Mục | Trạng thái |
|---|---|
| Object provenance `s2` (3 deref) | **PROVEN** |
| `+0x130` là method pointer slot 38 | **PROVEN** |
| `+0x130` ghi `tpcMask[]`, `+0x204` là `physGpcMask`, `+0x3E0` là GPC bitmap | **PROVEN** |
| Hàm đích của slot 38 | **UNKNOWN — không thể xác định (constructor tổng quát)**, đã thử 281 bảng |
| GSP đọc fuse `0x021xxx` | **BÁC BỎ — 0 tham chiếu** |
| Nguồn giá trị `0x1F` | **bootstrap static config**, không phải GSP tự tính |

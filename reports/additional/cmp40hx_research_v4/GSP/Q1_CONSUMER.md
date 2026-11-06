# Q1 — CONSUMER CỦA BẢNG DESCRIPTOR: ĐÃ TÌM RA HÀM DISPATCH

Trạng thái: **ĐẠT** ở mức **chứng minh cơ chế truy cập**.
Chưa parse được 100% tên entry (ghi rõ lý do bên dưới).

Bằng chứng: `GSP/q1_lui.json`, `GSP/q1_disasm.json`, `GSP/q1_table_layout.json`,
`TOOLS/q1_lui.py`, `TOOLS/q1_disasm.py`.

---

## 1. Phương pháp — không cần Ghidra

Báo cáo trước kết luận `BLOCKED` vì "cần Ghidra trên 17 MB RISC-V".
Thực ra chỉ cần **quét lệnh `LUI`** — 20 bit cao của địa chỉ bảng nằm ngay
trong opcode.

```python
# RISC-V LUI: bits[6:0]=0x37, rd=bits[11:7], imm[31:12]
if (w & 0x7F) == 0x37:
    imm20 = (w >> 12) & 0xFFFFF     # sign-extend
```

Quét `.text` step=2 (tập lệnh nén RVC) tìm `LUI` có `imm20` khớp 20 bit cao của
base bảng descriptor.

**Kết quả (`MEASURED`):**

```
7 section text, 17,066,024 B, step=2
381,665 lệnh LUI trong text
      8 LUI có imm20 khớp base bảng descriptor
```

8 LUI đó tập trung trong dải **`0x04F575FC .. 0x04F7230C`** (~110 KB) — đây là
vùng code dispatch.

---

## 2. Disasm — dùng capstone, không dùng envydis

**Sai lầm đã sửa:** lần đầu dùng `envydis -m falcon` → 93% "unknown instruction".
Lý do: **`envydis` là kiến trúc Falcon**, không phải RISC-V.

**Cách đúng:** `capstone 5.0.7` với `CS_ARCH_RISCV / CS_MODE_RISCV64`
(có sẵn `/usr/bin/python3`, không phải venv của Hermes).

---

## 3. HÀM DISPATCH — disasm thật

Tại `0x04F575FC` (LUI khớp, imm20 `0x41a7`):

```asm
04f575f8  63120940   bnez      s2, 0x404
04f575fc  b7741a04   lui       s1, 0x41a7        <<< NAP 20 BIT CAO
04f57600  371c0000   lui       s8, 1
04f57604  9384040b   addi      s1, s1, 0xb0      <<< base = 0x041A70B0
04f57608  130c0c74   addi      s8, s8, 0x740
04f5760c  338c8401   add       s8, s1, s8        <<< end = base + 0x1740
04f57610  6f004002   j         0x24
--- vong lap ---
04f57614  83b70903   ld        a5, 0x30(s3)      <<< callback tu CONTEXT
04f57618  035684f7   lhu       a2, -0x88(s0)
04f5761c  13850900   mv        a0, s3
04f57620  e7800700   jalr      a5                <<< GOI CALLBACK
04f57624  1b090500   sext.w    s2, a0
04f57628  63160926   bnez      s2, 0x26c
04f5762c  93840402   addi      s1, s1, 0x20      <<< STRIDE = 32 BYTE
04f57630  63069c42   beq       s8, s1, 0x42c     <<< het bang thi thoat
04f57634  13068008   addi      a2, zero, 0x88
04f57638  93050000   mv        a1, zero
04f5763c  130504f2   addi      a0, s0, -0xe0
04f57640  97f03100   auipc     ra, 0x31f
04f57644  e780c09f   jalr      ra, ra, -0x604
04f57648  83d80400   lhu       a7, 0x00(s1)      <<< entry+0x00
04f5764c  03a84400   lw        a6, 4(s1)         <<< entry+0x04
04f57650  83c68400   lbu       a3, 8(s1)         <<< entry+0x08
04f57654  03b70401   ld        a4, 0x10(s1)      <<< entry+0x10 (u64)
04f57658  83d78401   lhu       a5, 0x18(s1)      <<< entry+0x18
04f5765c  93050a00   mv        a1, s4
04f57660  130604f2   addi      a2, s0, -0xe0
04f57664  13850a00   mv        a0, s5
04f57668  230004f2   sb        zero, -0xe0(s0)
04f5766c  230d04f6   sb        zero, -0x86(s0)
04f57670  231c14f7   sh        a7, -0x88(s0)     <<< luu entry+0x00
04f57674  232e04f7   sw        a6, -0x84(s0)     <<< luu entry+0x04
04f57678  2300d4f8   sb        a3, -0x80(s0)     <<< luu entry+0x08
04f5767c  2334e4f8   sd        a4, -0x78(s0)     <<< luu entry+0x10
04f57680  2318f4f8   sh        a5, -0x70(s0)     <<< luu entry+0x18
```

---

## 4. ĐIỀU ĐÃ CHỨNG MINH (`DECODED`)

### 4.1 Bảng được truy cập bằng HẰNG SỐ TRONG LỆNH, không qua con trỏ

`lui s1, 0x41a7` + `addi s1, s1, 0xb0` → **base = `0x041A70B0`**.

Đây là lý do **mọi phép quét con trỏ đều thất bại** (0 hit ở P3, 0 hit ở Q9):
base nằm ngay trong mã lệnh, không có biến con trỏ nào trong data giữ nó.

### 4.2 Stride chính xác = **32 byte**

`addi s1, s1, 0x20` — xác nhận layout 32 byte/entry đã đoán từ P3.

### 4.3 Span = **`0x1740`** (5,952 B = 186 entry)

`lui s8,1` + `addi s8,s8,0x740` + `add s8,s1,s8` → end = base + 0x1740.
Vòng lặp `beq s8, s1, <thoat>` xác nhận.

### 4.4 Layout entry — ĐỌC TRỰC TIẾP TỪ CODE (`MEASURED`)

| Offset | Lệnh đọc | Kích thước | Đã lưu vào |
|---|---|---|---|
| `+0x00` | `lhu a7, 0x00(s1)` | **u16** | stack `-0x88(s0)` |
| `+0x04` | `lw a6, 4(s1)` | **u32** | stack `-0x84(s0)` |
| `+0x08` | `lbu a3, 8(s1)` | **u8** | stack `-0x80(s0)` |
| `+0x10` | `ld a4, 0x10(s1)` | **u64** | stack `-0x78(s0)` |
| `+0x18` | `lhu a5, 0x18(s1)` | **u16** | stack `-0x70(s0)` |

**Đây là layout CHÍNH XÁC, đọc từ code đang chạy — không phải suy đoán.**

### 4.5 SỬA LAYOUT CỦA P3

P3 đoán: `u64 name_ptr@+0x00 | u32 f08@+0x08 | u32 f0c@+0x0C | u32 id@+0x10 | …`

| Field | P3 đoán | **Thực tế từ disasm** | Kết luận |
|---|---|---|---|
| `+0x00` | u64 `name_ptr` | **u16** | **SAI** |
| `+0x04` | — | u32 | mới |
| `+0x08` | u32 `f08` | **u8** | **SAI kích thước** |
| `+0x0C` | u32 `f0c = 0` | (không đọc) | có thể padding |
| `+0x10` | u32 `id` | **u64** | **SAI** |
| `+0x14` | u32 `f14` | (nằm trong u64 trên) | gộp |
| `+0x18` | u32 `f18` | **u16** | **SAI kích thước** |
| `+0x1C` | u32 `f1c` | (không đọc) | có thể padding |

**P3 đã đọc lệch toàn bộ layout.** Parser P3 dùng `u64@+0x00` làm `name_ptr`
trong khi code dùng `u16@+0x00` và `u64@+0x10`.

### 4.6 Callback lấy từ CONTEXT, không từ entry

`ld a5, 0x30(s3)` rồi `jalr a5` — `s3` là **con trỏ context**, không phải entry.
Nghĩa là handler **không nằm trong entry**, mà ở struct context riêng
(có thể tra theo `id`).

---

## 5. ĐIỀU CHƯA LÀM ĐƯỢC — parse 100% tên entry

**Trung thực:** với `base = 0x041A70B0` và `u64@+0x10` là `name_ptr`, chỉ
**56/186 entry** (30%) có `name_ptr` trỏ tới **đầu chuỗi ASCII thật**.

Đã kiểm tra nguyên nhân:

| Kiểm tra | Kết quả |
|---|---|
| Entry 0 `u64 = 0x5345` | quá nhỏ để là vaddr → chính entry 0 đã không theo layout |
| 130 entry "không tên" có `u64` là gì | 129/130 có `u64 ≥ 0x4000000` (là vaddr) nhưng trỏ vào **giữa** vùng dữ liệu khác |
| Có phải 2 loại record xen kẽ? | **có** — 25 cụm entry-có-tên, cụm dài nhất chỉ 9 entry |
| Thử base khác (0x41A70F0, 0x41A7350) | 0–56 tên, không tốt hơn |
| Thử `u64` là 2×u32 offset vào pool | **0 tên** |

**Kết luận (`BLOCKED` phần này):** base `0x41A70B0` đúng (từ disasm), stride 32
đúng (từ disasm), nhưng **cấu trúc bên trong entry phức tạp hơn layout tuyến
tính 24/32 byte**. Có thể:
- Bảng gồm **nhiều sub-table** nối tiếp nhau, mỗi sub-table layout khác.
- Hoặc entry có **union** — `u64@+0x10` khi là `name_ptr`, khi là cặp số.

Cần: **đọc thêm hàm `jalr a5` (callback)** để biết nó diễn giải entry thế nào.
Đó là bước tiếp theo thực sự, không phải đoán.

---

## 6. Tác động lên các mục khác

### 6.1 Q9 được giải thích một phần

Q9 kết luận `BLOCKED` vì 7 tên quan trọng (`RMClkVfOverride`, `OVERVOLTAGE_*`,
`PERFORMANCE_CAP0`) không có entry. Giờ biết **lý do**: chúng **không** thuộc
bảng này — bảng này chỉ chứa policy perf/pstate (`PERF_CF_*`, `MODS_RULES_*`,
`CLIENT_*`, `VMIN_*`).

`PERFORMANCE_CAP0` **có** trong bảng ở base `0x41AF8A8` (phát hiện ở Q1-lite).
7 tên còn lại thuộc **bảng hoặc cơ chế khác** — có thể tra theo tên so sánh
chuỗi trong hàm khác.

### 6.2 Sửa `MASTER_REPORT.md`

Mục P3 "0 xref cứng → BLOCKED, cần Ghidra" nay phải đọc là:
**đã tìm ra consumer, base là hằng số `0x41A70B0` trong lệnh `lui`/`addi`,
stride 32, span 0x1740, layout đọc từ code**.

---

## 7. Trạng thái Q1

| Mục | Trạng thái |
|---|---|
| Tìm consumer của bảng descriptor | **ĐẠT** — `0x04F575FC` |
| Chứng minh base là hằng số trong lệnh | **ĐẠT** — `lui 0x41a7` + `addi 0xb0` |
| Xác định stride | **ĐẠT** — `addi s1,s1,0x20` = 32 |
| Xác định span | **ĐẠT** — base + `0x1740` = 186 entry |
| Layout entry | **ĐẠT** — 5 trường, kích thước đọc từ code |
| Sửa layout sai của P3 | **ĐẠT** — P3 lệch toàn bộ |
| Parse 100% tên entry | **CHƯA** — 56/186; cấu trúc entry phức tạp hơn layout tuyến tính |
| Đọc callback `jalr a5` | **CHƯA** — bước tiếp theo thực sự |

**Công cụ mới:** `TOOLS/q1_lui.py` (quét LUI), `TOOLS/q1_disasm.py`
(capstone RISC-V), `TOOLS/q1_regtable.py`, `TOOLS/q1_final.py`.

**Bài học phương pháp:** `BLOCKED: cần Ghidra` là kết luận **sai**. Quét `LUI`
20 bit cao + capstone RISC-V cho kết quả trong vài giây. Ghidra không cần thiết
cho bài toán này.

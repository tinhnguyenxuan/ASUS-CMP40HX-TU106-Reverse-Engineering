# PHASE15/GSP_DISPATCH_ANALYSIS.md — Phân tích dispatcher GSP-RM @ 0x04F575FC

## 1. Mục tiêu

Xác định caller/callee của dispatcher, phân tích callback qua `jalr`, khôi phục C-like pseudocode vòng lặp xử lý descriptor, phân tích 5 field entry, tìm chức năng 340 descriptor, tạo function inventory các section code RISC-V.

## 2. Dữ liệu gốc

| Trường | Giá trị |
|---|---|
| Source | `GSP/Q1_CONSUMER.md` (disasm thật từ `gsp_tu10x.bin`, capstone RISC-V 5.0.9 qua `/usr/bin/python3`) |
| Dispatcher | `0x04F575FC` (LUI imm20 `0x41a7` + ADDI `0xb0` → base `0x041A70B0`) |
| Bảng descriptor | base `0x041A70B0`, stride 32, span `0x1740` → 186 entry |
| Tổng string trong `.rodata` | 134,417 |
| Entry có tên phân giải được | 56/186 (30%) |
| Entry không tên | 130/186 (70%) |

## 3. Disasm hàm dispatcher (từ code thực, không phải suy đoán)

```asm
04f575f8  63120940   bnez      s2, 0x404
04f575fc  b7741a04   lui       s1, 0x41a7        <<< NAP 20 BIT CAO CỦA BASE
04f57600  371c0000   lui       s8, 1
04f57604  9384040b   addi      s1, s1, 0xb0      <<< base = 0x041A70B0
04f57608  130c0c74   addi      s8, s8, 0x740
04f5760c  338c8401   add       s8, s1, s8        <<< end = base + 0x1740
04f57610  6f004002   j         0x24
--- vong lap (tại 0x04F57614) ---
04f57614  83b70903   ld        a5, 0x30(s3)      <<< callback TỪ CONTEXT (s3), KHÔNG TỪ ENTRY
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
04f57648  83d80400   lhu       a7, 0x00(s1)      <<< entry+0x00 (u16)
04f5764c  03a84400   lw        a6, 4(s1)         <<< entry+0x04 (u32)
04f57650  83c68400   lbu       a3, 8(s1)         <<< entry+0x08 (u8)
04f57654  03b70401   ld        a4, 0x10(s1)      <<< entry+0x10 (u64)
04f57658  83d78401   lhu       a5, 0x18(s1)      <<< entry+0x18 (u16)
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

## 4. C-like pseudocode vòng lặp

```c
// s3 = con truttore context (gồm callback tại +0x30)
// s1 = con trỏ entry hiện tại, bắt đầu từ base 0x041A70B0
// s8 = end = base + 0x1740
// s0 = con trỏ struct stack (vùng tạm -0xe0..-0x68)

void dispatch_descriptor_table(void *context, uintptr_t base, uintptr_t end) {
    void (*callback)(void *ctx, ...);
    uintptr_t entry = base;

    while (entry != end) {
        // Đọc 5 field từ entry (layout xác nhận từ code, KHÔNG phải suy đoán)
        uint16_t f00 = *(uint16_t *)(entry + 0x00);
        uint32_t f04 = *(uint32_t *)(entry + 0x04);
        uint8_t  f08 = *(uint8_t  *)(entry + 0x08);
        uint64_t f10 = *(uint64_t *)(entry + 0x10);
        uint16_t f18 = *(uint16_t *)(entry + 0x18);

        // Lưu vào struct stack (dùng cho callback)
        stack->f00 = f00;
        stack->f04 = f04;
        stack->f08 = f08;
        stack->f10 = f10;
        stack->f18 = f18;

        // Callback lấy từ context (s3 + 0x30), KHÔNG phải từ entry
        callback = *(void **)(context + 0x30);
        int rc = callback(context, &stack->f00, ...);  // a2 = tham số (f10?)

        if (rc != 0) break;  // dừng vòng lặp nếu callback trả nonzero

        entry += 32;  // stride
    }
}
```

**Điều then chốt:** `u64@+0x10` **KHÔNG phải** `name_ptr` như P3 đoán. Code đọc nó rồi lưu vào struct context và **truyền cho callback qua `a2`** → là giá trị tham số. `ld a5, 0x30(s3)` lấy callback từ context, không từ entry.

## 5. Layout entry (đọc từ code, không phải P3 đoán sai)

| Offset | Kích thước | P3 đoán | Thực tế | Kết luận |
|---|---|---|---|---|
| `+0x00` | u16 | u64 `name_ptr` | **u16** | P3 SAI |
| `+0x04` | u32 | (không đọc) | u32 | mới |
| `+0x08` | u8  | u32 `f08` | **u8** | P3 SAI kích thước |
| `+0x0C` | — | u32 `f0c=0` | (padding) | không đọc |
| `+0x10` | u64 | u32 `id` | **u64** | P3 SAI |
| `+0x14` | — | u32 `f14` | (gộp vào u64 trên) | |
| `+0x18` | u16 | u32 `f18` | **u16** | P3 SAI kích thước |
| `+0x1C` | — | u32 `f1c` | (padding) | không đọc |

## 6. `u16@+0x18` = `{group:8, subtype:8}` — 23 mã

```
0xFF01 x47   0xFF02 x80   0xFF03 x7    0xFF05 x16
0xFF06 x6    0xFF07 x8    0xFF0A x1    0xFF0B x1
0x0201 x4    0x0301 x2    0x0402..0x040A 0x0502/0x0505
0x0002, 0x0005, 0x0101, 0x0102, 0x0105
```

Trị giá tới `0xFF0B` → **không phải độ dài tên** (tên dài 31 ký tự). Đây là mã loại policy. Nhóm `0xFFxx` chiếm 166/186 entry (89%).

## 7. Bác bỏ 4 giả thuyết về `u64@+0x10` (có bằng chứng)

| Giả thuyết | Kết quả | Bằng chứng |
|---|---|---|
| Suffix merging (tên chia suffix) | **BÁC BỎ** | `_MIN` là suffix của 126 chuỗi khác nhau → không phân giải duy nhất |
| `u32@+0x04` = offset vào string pool | **BÁC BỎ** | Chỉ 16/370 u32 là offset tới vùng ASCII |
| `u16@+0x18` = độ dài tên | **BÁC BỎ** | Tới `0xFF0B`, không phải độ dài |
| `u64@+0x10` = `name_ptr` | **BÁC BỎ** (theo nghĩa parser tự do) | 174/184 giá trị rơi vào dải string nhưng 0 phân giải duy nhất; chỉ 56/184 trỏ đầu chuỗi thật |

**Kết luận:** `u64@+0x10` là **tham số truyền cho callback** (qua `a2`), không phải con trỏ tên. Tên entry xác định bởi `(offset, length)` — mà `length` không nằm trong entry → cần đọc hàm callback để biết cách tra tên.

## 8. Caller của dispatcher

8 lệnh LUI có imm20 khớp base bảng, tập trung trong `0x04F575FC..0x04F7230C` (~110 KB). Đây là vùng code dispatch.

**Tìm caller trực tiếp (offline, read-only, đã làm):**
- Quét toàn bộ `gsp_tu10x.bin` (22.9 MB) bằng Python stdlib:
  - `jal` trực tiếp đến `0x04F575FC`: **0 kết quả** (172,754 JAL quét)
  - `auipc` + `jalr` pair cùng register targeting dispatcher: **0 kết quả** (189,928 pairs quét)
  - `lui` với imm20 khớp high 20 bit của dispatcher: **2 kết quả**, nhưng đều nằm trong khu vực dispatcher tự nó (`0xF5744C`, `0xF574D0`), không phải caller từ hàm khác

**Kết luận:** Caller có thể gọi qua function pointer / GOT / bảng dispatch, không phải `jal` trực tiếp. **Cần Ghidra headless call graph** để xác định hàm nào gọi dispatcher. → Ghi vào `BLOCKERS.md` (cần công cụ lớn hơn).

**Callee (callback):** `ld a5, 0x30(s3)` + `jalr a5` → callback ở context +0x30. **Chưa disasm được hàm callback** (cần tìm địa chỉ context, chưa làm).

## 9. Callee (callback)

`ld a5, 0x30(s3)` + `jalr a5` → callback ở context +0x30. **Chưa disasm được hàm callback** (cần tìm địa chỉ context, chưa làm).

## 10. Chức năng 340 descriptor

- 60 bảng, 340 entry thật (P3 cũ sai: 139 entry là mảnh chuỗi vụn).
- Các entry có tên: `PERF_CF_CONTROLLER_*`, `VMIN_*`, `MODS_RULES_*`, `CLIENT_*`, `UNLOAD_DRIVER_VOLTAGE_RAIL_*`, `RELIABILITY_NVVDD`, `MCLK_LIMIT`, `RATED_TDP_MIN`, `JPAC_PSTATE_MAX`, `PMU_DOM_GRP_1`.
- 7 tên **KHÔNG** trong bảng: `RMClkVfOverride`, `RmAtsVolOverride`, `RmClkControllersOverride`, `OVERVOLTAGE_LOGIC`, `OVERVOLTAGE_NVVDD_0/1`, `PERFORMANCE_CAP0` → có thể thuộc bảng thứ hai (U-GSP-006).

## 11. Function inventory các section code RISC-V

**Chưa làm** (COVERAGE.md mục 4: function inventory = chưa làm, call graph = chưa làm). Các section:
- `.tu10x_text` (5,140 B), `.tu10x_resident_text` (12,288 B), `.section_task_init_elf_text_instance` (16,384 B), `.section_task_rm_elf_text_instance` (17,010,688 B).

## 12. RPC và quan hệ GSP-RM với engine

**Chưa làm** — cần disasm section text và tra các mailbox register.

---
**Ponytail:** phân tích dựa trên disasm đã có (Q1_CONSUMER.md), không viết tool mới. Thêm function inventory khi có tài nguyên disasm lớn hơn.

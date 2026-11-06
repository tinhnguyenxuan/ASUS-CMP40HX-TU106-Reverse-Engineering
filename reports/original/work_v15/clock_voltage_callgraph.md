# CALL GRAPH — clock / voltage / power (GSP-RM)

Trạng thái: **một phần**. Ghi rõ chỗ nào có bằng chứng, chỗ nào chưa.

---

## 1. Vị trí code

`gsp_tu10x.bin` — ELF64 RISC-V lồng 2 lớp:

```
lop ngoai : ELF64 REL, machine 0xF3, 10 section
lop trong : @file 0x40, ELF64 EXEC, 37 section, 11 PT_LOAD, entry 0x4009000
load base : 0x4000000
quy doi   : vaddr = file_offset + 0x4000000   (sh_offset TUYET DOI tu dau file)
```

| Section | vaddr | file off | Size |
|---|---|---|---|
| `.tu10x_text` | `0x04007000` | `0x00007040` | 5,140 |
| `.tu10x_resident_text` | `0x0400E000` | `0x0000E040` | 12,288 |
| `.section_task_init_elf_text_instance` | `0x04018000` | `0x00018040` | 16,384 |
| **`.section_task_rm_elf_rodata_instance`** | `0x0401D000` | `0x0001D040` | **1,982,464** |
| `.section_task_rm_elf_data_instance` | `0x04201000` | `0x00201040` | 3,698,688 |
| **`.section_task_rm_elf_text_instance`** | `0x04588000` | `0x00588040` | **17,010,688** |

---

## 2. Bảng descriptor registry — CẤU TRÚC ĐÃ XÁC ĐỊNH

Vị trí: `0x1a7280 .. 0x1a8840` trong `.rodata`. **8 bảng con, 139 entry, 32 byte/entry.**

```
struct regkey_descriptor {
    u64 name_ptr;    // vaddr cua chuoi ten
    u32 f08;         // 12 gia tri: 0xff01, 0xff02, 0xff0a, ...
    u32 f0c;         // LUON = 0 (139/139)
    u32 id;          // ma key tang dan, 20..287
    u32 f14;         // 139 gia tri khac nhau
    u32 f18;         // 11 gia tri: 273, 274, 277, 278, ... (nghi ma module)
    u32 f1c;         // ~0 (138/139), 1 entry = 0x04F69E8C
}
```

**8 bảng con:**

```
0x1a7280..0x1a73e0  11 entry
0x1a7440..0x1a7620  15 entry
0x1a7640..0x1a7900  22 entry
0x1a7b00..0x1a7e60  27 entry
0x1a7f00..0x1a8060  11 entry
0x1a8080..0x1a8200  12 entry
0x1a8300..0x1a8580  20 entry
0x1a85a0..0x1a8840  21 entry
```

---

## 3. Các node clock/voltage/power đã xác định

### 3.1 Controller trần (PERF_CF)

| Key | Chuỗi @file | Descriptor | id | f08 | f14 | f18 |
|---|---|---|---|---|---|---|
| `PERF_CF_CONTROLLER_DRAM_MAX` | `0x1a6130` | `0x1a7280` | 20 | `0xff02` | 42 | 273 |
| **`PERF_CF_CONTROLLER_GPC_MAX`** | `0x1a6150` | **`0x1a72a0`** | **21** | `0xff0a` | **88** | 273 |
| `PERF_CF_CONTROLLER_NVD_MAX` | — | `0x1a72e0` | 23 | `0xff01` | 1 | 274 |

Đây là **bộ điều khiển trần GPC / DRAM / NVD** — ứng viên mạnh nhất cho H4.
`id = 21` là chỗ để đặt giá trị nếu muốn thử.

### 3.2 Overvoltage

| Key | @file |
|---|---|
| `OVERVOLTAGE_LOGIC` | `0x001a6ba0` |
| `OVERVOLTAGE_NVVDD_0` | `0x001a9798` |
| `OVERVOLTAGE_NVVDD_1` | `0x001a97b0` |

**Chưa có descriptor entry** trong 139 entry đã parse. Có thể thuộc bảng
descriptor khác ngoài vùng `0x1a7280..0x1a8840`, hoặc là chuỗi dùng nội bộ
(không expose thành registry key).

### 3.3 Override (không có descriptor)

| Key | @file | Ghi chú |
|---|---|---|
| `RMClkVfOverride` | `0x00092de8` | rơi vào `.tu10x_text`/`.resident_text` |
| `RmAtsVolOverride` | `0x000a7a90` | |
| `RmClkControllersOverride` | `0x00092fd8` | |
| `RmClockForceUprocVfeVfGen` | `0x00092d10` | |
| `RMEnableOverclockingAllPstates` | `0x001a5ba0` | |
| `RMForceLockedClocksMode` | `0x001a5c60` | |
| `RMHwSpeedoOverride` | `0x001b4af8` | bảng chuỗi liền nhau |
| `RMHwSpeedoCheckIgnore` | `0x001b4b40` | |
| `RmPmgrIddqOverride` | `0x001b4b58` | |
| `RmPmgrIddqNvvddOverride` | `0x001b4b88` | |
| `RmPmgrIddqCheckIgnore` | `0x001b4bb8` | |
| `RmSramVminCheckIgnore` | `0x001b4bd0` | |
| `RmPmgrIsenseVcmOffsetOverride` | `0x001b4be8` | **mới phát hiện** |
| `RmPmgrIsenseDiffGainOverride` | `0x001b4c08` | **mới phát hiện** |
| `RmPmgrIsenseDiffOffsetOverride` | `0x001b4c28` | **mới phát hiện** |
| `RmPmgrSpeedoCoefficient` | `0x001b8f70` | |
| `RmPmgrSpeedoOffset` | `0x001b8f88` | |
| `RmVoltThresholdCtrlCtrl` | `0x001b9730` | |
| `RMSec2UseDebugFuseOnlyBinary` | `0x001bbdc8` | |

---

## 4. XREF — KẾT QUẢ ÂM TÍNH, PHƯƠNG PHÁP ĐÃ ĐÚNG

Quét 3 kiểu trên **toàn bộ 22,901,632 byte**:

| Kiểu | Cách làm | Kết quả |
|---|---|---|
| Code ref | `auipc rd,imm20` + (`addi`/`ld`/`lw` cùng `rd`), cửa sổ `o+2..o+24`, **step = 2** (RVC) | **0** |
| u32 pointer | tìm `pack('<I', vaddr)` | **0** (trừ entry descriptor của chính nó) |
| u64 pointer | tìm `pack('<Q', vaddr)` | **0** |
| Relative 32-bit | `va - vị_trí_bảng` | **0** (trừ 1 hit trùng ngẫu nhiên) |
| Ngược về base bảng descriptor | `pack('<Q', 0x41a7280)` và `+0x10` | **0** |

**Diễn giải:** registry dispatch là **data-driven theo tên**. Không có
tham chiếu cứng từ code tới chuỗi. Đây **không phải lỗi script** — đã sửa
đúng công thức vaddr (`sh_offset` tuyệt đối) và đã dùng step=2 cho RVC.

**Hệ quả:** không thể suy ra kiểu giá trị mong đợi (boolean 0/1 hay số) từ
phân tích tĩnh từ vị trí chuỗi. Cần tìm **hàm đọc bảng descriptor** — hàm này
duyệt 139 entry, so sánh tên, rồi dispatch theo `f08`/`f18`. Tìm nó bằng cách:
xref tới **base bảng descriptor** (đã thử, 0 hit) hoặc tìm hằng số `139`/`0x8B`
trong code cùng pattern so sánh chuỗi.

---

## 5. Call graph — phần ĐÃ BIẾT (đường VBIOS → GSP)

```
[VBIOS, SPI flash]
  NPDS 0xE0 #2 @0x054000
    └── VFE @0x5649C
          slot[0] REL 1068.75 mV ─┐
          slot[1] ALT 1093.75 mV ─┤
          slot[3] OV  1125.00 mV ─┼── selector @0x2D384 = {0,1,3,0,2,4}
          slot[2] VMIN  693.50 mV ┘
                                   │
[host RM: nvidia.ko 615.78.08]     │
  kgspExtractVbiosFromRom_TU102 ◄──┘   doc ROM qua SPI/eFuse
  _kgspVbiosOverridePrepare         thay image tu RAM (duong da dung)
  kernel_gsp.c:4914                 PACKED_REGISTRY_TABLE
                                   │
[GSP-RM: RISC-V 22.9 MB]           │
  bang descriptor @0x1a7280 (139 entry)
    ├── PERF_CF_CONTROLLER_GPC_MAX (id 21)   ← DIEM DUT
    ├── PERF_CF_CONTROLLER_DRAM_MAX (id 20)
    ├── PERF_CF_CONTROLLER_NVD_MAX (id 23)
    └── OVERVOLTAGE_LOGIC / NVVDD_0 / NVVDD_1
                                   │
[PMU]  ← CHUA CO BANG CHUNG
[SEC2] ← CHUA CO BANG CHUNG
```

**Điểm đứt:** chưa nối được `PERF_CF_CONTROLLER_GPC_MAX` (id 21) với
giá trị cụ thể nào, và chưa tìm được hàm đọc VFE slot trong 17 MB code.

---

## 6. Phân biệt host RM / GSP-RM / PMU / SEC2

| Thành phần | Đã xác định được | Chưa xác định |
|---|---|---|
| **host RM** | đọc VBIOS (`kgspExtractVbiosFromRom_TU102`), override qua RAM (`_kgspVbiosOverridePrepare`), đóng gói registry (`kernel_gsp.c:4914`), ghi WPR metadata | — |
| **GSP-RM** | ELF RISC-V, 37 section, 139 descriptor, tên policy clock/volt/power | hàm đọc VFE; giá trị policy 21 |
| **PMU** | không có | tất cả |
| **SEC2** | chỉ tên trong log (`SEC2ExploitDmem`, `SEC2UseDebugFuseOnlyBinary`) | chức năng power/clock |

---

## 7. Việc cần làm để hoàn thành call graph

1. **Ghidra** load `gsp_tu10x.bin` base `0x4000000`, chỉ analyze
   `.section_task_rm_elf_text_instance` (17 MB — chọn "Aggressive Instruction
   Finder" tắt để tránh treo). Tìm hàm duyệt 139 entry: pattern là vòng lặp
   stride **32** trên vùng `0x41a7280..0x41a8840`.
2. **Tìm so sánh chuỗi** trong hàm đó → sẽ thấy `strcmp`-tương đương.
3. Từ đó suy ra `f08` (kiểu) và `f18` (module) nghĩa gì → biết
   `PERF_CF_CONTROLLER_GPC_MAX` cần boolean hay số.

Ước lượng: Ghidra trên 17 MB RISC-V là việc nặng, nên chạy nền.

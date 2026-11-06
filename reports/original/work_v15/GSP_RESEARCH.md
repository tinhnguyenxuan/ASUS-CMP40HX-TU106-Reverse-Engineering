# GSP_RESEARCH — Nhiệm vụ B

Tóm tắt. Chi tiết đầy đủ: `clock_voltage_callgraph.md`, `EVIDENCE_LEDGER.md` E08.
Dữ liệu thô: `outputs/gsp_strings.json`, `outputs/gsp_xrefs.json`.

---

## B1 — ELF sections, symbols, relocation, container

`gsp_tu10x.bin` = **ELF64 lồng 2 lớp**, không phải blob mờ:

```
lop ngoai : ELF64 REL, e_machine 0xF3 (RISC-V), 10 section
            .fwimage       @0x40         21,935,048 B
            .fwversion     @0x15D3E2C            10 B
            .fwsignature1  @0x15D3E36         4,096 B
            .fwsignature2  @0x15D4E36         4,096 B
            .fwsignature3  @0x15D5E36         4,096 B
            .symtab / .strtab

lop trong : @file offset 0x40, ELF64 EXEC, RISC-V
            entry 0x4009000, 37 section, 11 PT_LOAD
            load base 0x4000000
```

Section lớn:

| Section | vaddr | file off | Size |
|---|---|---|---|
| `.section_task_rm_elf_rodata_instance` | `0x0401D000` | `0x0001D040` | 1,982,464 |
| `.section_task_rm_elf_data_instance` | `0x04201000` | `0x00201040` | 3,698,688 |
| `.section_task_rm_elf_text_instance` | `0x04588000` | `0x00588040` | 17,010,688 |
| `.section_task_init_dmem_64kb_instance` | `0x055C1000` | `0x015C1040` | 65,536 |

**Quy tắc quy đổi (đã sửa):** `vaddr = file_offset + 0x4000000`.
Lý do: `sh_offset` trong section header là **tuyệt đối từ đầu file**.
Công thức cũ `0x4000000 + (file_off - 0x40)` lệch `0x40` — đủ để mọi so khớp
thất bại.

**Relocation:** không có `.rela.*` → file đã link tĩnh. Không có bảng
relocation nào để đọc con trỏ gián tiếp.

---

## B2 — Call graph clock/voltage/power

**Đã xác định cấu trúc:** bảng descriptor registry @ `0x1a7280..0x1a8840`,
**8 bảng con, 139 entry, 32 byte/entry**:

```
struct { u64 name_ptr; u32 f08; u32 f0c(=0); u32 id; u32 f14; u32 f18; u32 f1c; }
```

Node clock/voltage/power đã tìm được:

| Key | id | f08 | f14 | f18 |
|---|---|---|---|---|
| `PERF_CF_CONTROLLER_DRAM_MAX` | 20 | `0xff02` | 42 | 273 |
| **`PERF_CF_CONTROLLER_GPC_MAX`** | **21** | `0xff0a` | **88** | 273 |
| `PERF_CF_CONTROLLER_NVD_MAX` | 23 | `0xff01` | 1 | 274 |

**Chưa xác định:** hàm tiêu thụ giá trị. Call graph đầy đủ cần Ghidra trên
17 MB RISC-V — xem `clock_voltage_callgraph.md` mục 7.

---

## B3 — Truy vết chuỗi

**8/8 chuỗi trong đề bài đều tồn tại:**

| Chuỗi | @file | Có descriptor? |
|---|---|---|
| `RMClkVfOverride` | `0x00092de8` | không |
| `RmAtsVolOverride` | `0x000a7a90` | không |
| `RmClkControllersOverride` | `0x00092fd8` | không |
| `OVERVOLTAGE_LOGIC` | `0x001a6ba0` | không |
| `OVERVOLTAGE_NVVDD_0` | `0x001a9798` | không |
| `OVERVOLTAGE_NVVDD_1` | `0x001a97b0` | không |
| `PERFORMANCE_CAP0` | `0x001a6100` | không |
| `PERF_CF_CONTROLLER_GPC_MAX` | `0x001a6150` | **CÓ** (`0x1a72a0`, id 21) |

Mật độ string theo chủ đề: **PWR 116, PERF 104, CLK 50, VF 36, PSTATE 32,
VOLT 31, BOOST 25, THERM 18, SPEEDO 8, IDDQ 6, OCP 6, OVERCLOCK 4, TGP 3.**

---

## B4 — Parser / điều kiện / điểm tiêu thụ

**Đây là mục đề bài yêu cầu nghiêm ngặt nhất: "không kết luận có tác dụng chỉ
vì tìm thấy string".**

Kết quả quét **3 phương pháp** trên **toàn bộ 22,901,632 byte**:

| Phương pháp | Chi tiết | Kết quả |
|---|---|---|
| `auipc`+`addi`/`ld`/`lw` | cửa sổ `o+2..o+24`, **step=2** (RVC 16-bit), kiểm `rs1 == rd` | **0 ref** |
| u32 absolute pointer | `pack('<I', vaddr)` | **0** (trừ entry descriptor tự trỏ) |
| u64 absolute pointer | `pack('<Q', vaddr)` | **0** |
| Relative offset 32-bit | `va - vị_trí_bảng` | **0** (1 hit ngẫu nhiên) |
| Ngược về base descriptor | `pack('<Q', 0x41a7280)`, `+0x10` | **0** |

**Kết luận B4 (có bằng chứng):**
- **19/20 key: KHÔNG có parser tĩnh nào tham chiếu.** Registry key được tra
  **theo tên lúc runtime** qua bảng descriptor data-driven.
- **Điều kiện áp dụng + điểm tiêu thụ: CHƯA XÁC ĐỊNH được.**
- Do đó **không thể kết luận key nào có tác dụng** — kể cả
  `PERF_CF_CONTROLLER_GPC_MAX` (có descriptor nhưng chưa biết giá trị).

Đây là **điểm thiếu bằng chứng được ghi nhận rõ**, không phải kết luận vội.

---

## B5 — Đường dữ liệu VBIOS → bộ điều khiển điện áp

**Đã xác định (có bằng chứng):**
- Đầu vào: VFE @ `0x5649C`, slot[0] REL / slot[1] ALT (hằng số µV),
  selector @ `0x2D384`.
- Trung gian: `kgspExtractVbiosFromRom_TU102` đọc ROM qua SPI/eFuse;
  `_kgspVbiosOverridePrepare` thay image từ RAM; `kernel_gsp.c:4914` đóng gói
  `PACKED_REGISTRY_TABLE`.
- Đầu ra tiềm năng: bảng descriptor 139 entry trong GSP-RM.

**Chưa nối được:** hàm nào trong 17 MB code GSP-RM đọc slot VFE và biến nó
thành yêu cầu điện áp. Không có xref cứng để bám vào.

**Trạng thái: ĐẠT MỘT PHẦN — hai đầu đã biết, giữa còn đứt.**

---

## B6 — Phân biệt host RM / GSP-RM / PMU / SEC2

| Thành phần | Bằng chứng trong phiên này |
|---|---|
| **host RM** | `kgspExtractVbiosFromRom_TU102`, `_kgspVbiosOverridePrepare`, `kernel_gsp.c:4914`, ghi WPR metadata `0xffe40000` |
| **GSP-RM** | ELF RISC-V 22.9 MB, 139 descriptor, `PERF_CF_CONTROLLER_*`, 116 string PWR |
| **PMU** | **KHÔNG CÓ BẰNG CHỨNG** trong phiên này |
| **SEC2** | chỉ thấy tên trong log (`SEC2ExploitDmem`) và string (`RMSec2UseDebugFuseOnlyBinary`) |

---

## B7 — Có giới hạn SKU / clock cap / voltage cap riêng cho CMP 40HX?

**Voltage cap: CÓ — xác định chính xác.**

```
REL  = 1068.75 mV   (slot[0], @0x56699)
ALT  = 1093.75 mV   (slot[1], @0x566B1)
OV   = 1125.00 mV   (slot[3], @0x566E1)
BOOT =  800.00 mV
VMIN =  693.50 mV   (bounds 400..993.75 mV)
```

Xác nhận bởi: IEEE-754 decode + `nvbios` ground truth + cấu trúc slot +
ảnh vendor Galax HOF XOC.

**Clock cap: KHÔNG tìm thấy.**

Quét **mọi offset (chẵn và lẻ)** trong 40 bảng `PERF_PTRS` cho `u16`/`u32`
tần số: **không có `1890` (0x0762) hay `1905` (0x0771)` ở bất kỳ đâu**.

Các giá trị tìm được và ý nghĩa:

| Giá trị | Hex | Xuất hiện | Nghi là |
|---|---|---|---|
| 7000 | `0x1B58` | 9 lần (PERF 2,17,20,22,32,34,47) | **memory clock GDDR6 P0** |
| 5000 | `0x1388` | 4 lần (PERF 20,22,35) | memory clock P2/P5 |
| 3300 | `0x0CE4` | 2 lần (PERF 17,35) | memory clock P8 |
| 1942 | `0x0796` | PERF[16] | **ứng viên sát trần nhất** |
| 1697 | `0x06A1` | 3 lần (PERF 17,33) | GPC clock |
| 1638 | `0x0666` | PERF[42] | GPC clock |
| 860 | `0x035C` | PERF[16] | video clock |
| 620 | `0x026C` | PERF[17] header | video clock |
| 405 | `0x0195` | PERF[0] | video/idle clock |

**SKU cap trong GSP-RM: CHƯA XÁC ĐỊNH.** `PERF_CF_CONTROLLER_GPC_MAX` (id 21)
là ứng viên mạnh nhất nhưng chưa có giá trị.

---

## B8 — Điểm thiếu bằng chứng (ghi rõ theo yêu cầu)

| # | Thiếu | Vì sao không lấy được | Cần gì |
|---|---|---|---|
| 1 | Hàm đọc VFE trong GSP-RM | 0 xref cứng trên 22.9 MB; cần Ghidra 17 MB RISC-V | Ghidra + thời gian |
| 2 | Kiểu giá trị của `PERF_CF_CONTROLLER_GPC_MAX` | như trên | như trên |
| 3 | Chức năng PMU | không có symbol/string riêng | Ghidra trên ucodes |
| 4 | Chức năng SEC2 | chỉ có tên | như trên |
| 5 | Nghĩa `f08` / `f18` trong descriptor | chưa tìm được consumer | Ghidra |

Không có mục nào trong bảng này được thay bằng suy đoán trong báo cáo.

---

## B9 — Công cụ đã viết

| Script | Chức năng |
|---|---|
| `scripts/gsp_scan.py` | parse ELF 2 lớp, 37 section, PT_LOAD; tìm 20 chuỗi; mật độ theo chủ đề; XREF 3 kiểu step=2 |
| `scripts/gsp_descriptors.py` | tìm + parse 8 bảng descriptor (139 entry × 32 B); phân bố field; xuất JSON |

Cả hai dùng **Python stdlib thuần** (struct, json), không dependency ngoài.

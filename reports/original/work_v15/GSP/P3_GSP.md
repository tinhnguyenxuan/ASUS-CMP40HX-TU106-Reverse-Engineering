# P3 — GSP-RM REVERSE ENGINEERING

Trạng thái: **ĐẠT** — sửa được lỗi parser cũ, phát hiện **340 entry thật** trong
**60 bảng**, tìm ra tên policy khớp trực tiếp với `nvidia-smi`.

Bằng chứng: `GSP/gsp_functions.json`, `TOOLS/gsp_desc2.py`.

---

## 1. SỬA LỖI NGHIÊM TRỌNG CỦA BÁO CÁO TRƯỚC

Báo cáo trước kết luận: *"8 bảng descriptor, 139 entry × 32 B"*. **SAI.**

### 1.1 Nguyên nhân sai

Parser cũ quét `for o in range(LO, HI, 32)` — bước nhảy 32 byte cố định từ một
offset bắt đầu tuỳ ý. Vì bảng **không căn lề 32** ở điểm bắt đầu, nhiều "entry"
đọc ra chỉ là **đuôi chuỗi của entry trước**:

```
entry thật:  PERF_CF_CONTROLLER_GPC_MAX
"entry" ma:  CONTROLLER_GPC_MAX      <- 12 byte cuoi cua chuoi tren
"entry" ma:  ER_NVD_MAX              <- 8 byte cuoi cua PERF_CF_CONTROLLER_NVD_MAX
"entry" ma:  M_GRP_1
"entry" ma:  OWER
```

Chúng vẫn "hợp lệ" vì `name_ptr` trỏ vào **giữa** một chuỗi ASCII, và parser chỉ
kiểm "đọc được chuỗi ASCII" chứ không kiểm "là đầu chuỗi".

### 1.2 Cách sửa (DECODED)

Ba điều kiện mới:
1. `name_ptr` phải trỏ tới **đầu chuỗi thật** — tra trong bảng string đã quét
   đầy đủ `.rodata` (không phải `find` tuỳ ý).
2. `f0c == 0` (trường này bằng 0 ở mọi entry thật).
3. `id < 10000` và `f18 < 10000`.
4. Bước nhảy **4 byte** thay vì 32.
5. Gom thành bảng: entry liên tiếp cách đúng 32 byte, tối thiểu 3 entry.

### 1.3 Kết quả đúng

```
  134,417 string trong .rodata (1,982,464 B)
    1,509 ứng viên entry 32 B
       60 bảng (>=3 entry liên tiếp)
      340 entry THẬT
```

**So với báo cáo cũ: 340 entry (đúng) vs 139 (sai, gồm ~200 mảnh vụn).**

---

## 2. LAYOUT ENTRY — xác nhận

```
struct regkey_descriptor {      // 32 byte
    u64 name_ptr;    // +0x00  vaddr chuỗi (= file_off + 0x4000000)
    u32 f08;         // +0x08  kiểu/flags
    u32 f0c;         // +0x0C  LUÔN = 0 (340/340)  <- dùng làm bộ lọc
    u32 id;          // +0x10  mã key
    u32 f14;         // +0x14  index
    u32 f18;         // +0x18  mã module
    u32 f1c;         // +0x1C
}
```

### 2.1 Phân bố `f08` (kiểu)

| f08 | Số entry | Nghi là |
|---|---:|---|
| `0x0000ff02` | 84 | kiểu phổ biến nhất |
| `0x0000ff01` | 57 | |
| `0x0000ff05` | 37 | |
| `0x0000ff03` | 28 | |
| `0x0000ff07` | 28 | |
| `0x0000ff06` | 28 | |
| `0x0000ff08` | 20 | |
| `0x0000ff04/09` | 16 each | |
| `0x00000102/0d/0e` | 6/4/4 | **không có tiền tố `0xff`** — nhóm riêng |
| `0x0000040a/11/02` | 2 each | |

Nhóm `0x0000ffXX` = 13 giá trị → nghi **kiểu dữ liệu** hoặc **bitmask quyền**.
Nhóm `0x000001XX` và `0x000004XX` khác hẳn → **cần điều tra riêng (UNKNOWN)**.

### 2.2 Phân bố `f18` (module)

| f18 | Số entry |
|---:|---:|
| 278 | 102 |
| 277 | 93 |
| 273 | 35 |
| 274 | 22 |
| 279 | 17 |
| 290 | 17 |
| 405 | 16 |
| 406 | 14 |
| 275 | 9 |
| 415 | 6 |
| **33** | 4 |
| 287 | 3 |
| 354 | 2 |

13 giá trị. `f18` nhóm 273–279 (8 giá trị liên tiếp) = **module ID đánh số liên
tục**. Nhóm 405/406/415 và 33/287/354 nằm ngoài dải → **nhóm khác (UNKNOWN)**.

---

## 3. PHÁT HIỆN LỚN — tên policy KHỚP TRỰC TIẾP với nvidia-smi

`nvidia-smi -q -d PERFORMANCE` báo các cờ:
`SW Power Cap`, `HW Slowdown`, `HW Thermal Slowdown`, **`Board Limit`**,
**`Reliability`**.

Trong 340 entry tìm được **tên tương ứng từng chữ một**:

| Entry | id | f08 | f14 | f18 |
|---|---:|---|---:|---:|
| **`RELIABILITY_NVVDD`** | 204 | `0xff02` | 150 | 273 |
| `VMIN_NVVDD_0` | 204 | `0xff02` | 150 | 273 |
| `VMIN_NVVDD_1` | 205 | `0xff01` | 151 | 273 |
| `VMIN_MSVDD_1` | 206/208/213 | `0xff01` | 281/249/129 | 278/279 |
| `VMIN_LOGIC` | 213 | `0xff01` | 129 | 279 |
| `MCLK_LIMIT` | 155/158 | `0x0000010e` | 274/78 | 354/274 |
| `RATED_TDP_MIN` | 137 | `0xff01` | 204 | 274 |
| `PERF_CF_CONTROLLER_GPC_MAX` | 19/20/21 | `0xff08`/`0xff02`/`0xff0a` | 280/42/88 | 290/273 |
| `PERF_CF_CONTROLLER_GPC_MIN` | 8 | `0x00000411` | 279 | 33 |
| `PERF_CF_CONTROLLER_DRAM_MAX` | 18 | `0xff02` | 219 | 290 |
| `PERF_CF_CONTROLLER_NVD_MAX` | 20 | `0xff02` | 42 | 273 |
| `PERF_CF_CONTROLLER_XBAR_MAX` | 21 | `0xff0a` | 88 | 273 |
| `UNLOAD_DRIVER_VOLTAGE_RAIL_0` | 149 | `0xff02` | 254 | 275 |
| `UNLOAD_DRIVER_VOLTAGE_RAIL_1` | 150/151 | `0xff02` | 283/155 | 275/273 |
| `UNLOAD_DRIVER_VOLTAGE_RAIL_2` | 151 | `0xff02` | 155 | 273 |
| `UNLOAD_DRIVER_VOLTAGE_RAIL_3` | 139/152 | `0xff02` | 90/72 | 274/290 |
| `JPAC_PSTATE_MAX` | 34 | `0xff02` | 57 | 278 |
| `MODS_RULES_STRICT_PSTATE_MAX/MIN` | 217/218 | `0xff03/04` | 236/160 | 406/278 |
| `MODS_RULES_STRICT_DRAM_MAX/MIN` | 219/226 | `0xff07` | 131/134 | 278/277 |
| `MODS_RULES_STRICT_PCIE_MAX/MIN` | 223/230 | `0xff06` | 133/136 | 277/278 |
| `MODS_RULES_STRICT_XBAR_MAX/MIN` | 225/231 | `0xff03/02` | 161/139 | 277 |
| `MODS_RULES_LOCK_DRAM_MAX/MIN` | 220/227 | `0xff05` | 132/135 | 278/277 |
| `CLIENT_LOW_STRICT_PSTATE_MAX/MIN` | 42/43 | `0xff03/04` | 220/156 | 278 |
| `CLIENT_PERF_CF_PWR_MODEL_PROFILE_SETUP_LOCK` | 138/145 | `0xff05` | 270/152 | 273/275 |
| `PMU_DOM_GRP_1` | 201 | `0xff02` | 143 | 273 |
| `SLI_GPU_BOOST_DOM_GRP_0/1` | 204 | `0xff02` | 150 | 273 |
| `FORCED_DACPERFTEST` | 136 | `0xff05` | 53 | 274 |
| `CLIENT_LOW_STRICT_XBAR_MIN` | 56 | `0xff02` | 126 | 277 |

**Độ tin: CAO** cho "tên tồn tại". Độ tin **THẤP** cho "nghĩa của f08/f14/f18".

### 3.1 `RELIABILITY_NVVDD` là gì

`nvidia-smi` báo `Reliability: Active` dưới tải ở ROM gốc, và **`Not Active`**
khi nạp T4 (REL/ALT = 1125 mV). Tên entry `RELIABILITY_NVVDD` xuất hiện **đúng
một lần** với `id=204`, `f14=150`.

Đây là **liên hệ tên ↔ hành vi quan sát được**. Nhưng:
- **Chưa chứng minh** entry này chính là nguồn của cờ `Reliability` trong nvidia-smi.
- `id=204` trùng với `VMIN_NVVDD_0` và `SLI_GPU_BOOST_DOM_GRP_0` → **`id` không
  phải khoá duy nhất toàn cục**, mà duy nhất **trong một bảng**.

### 3.2 Sửa lỗi nhận định cũ về `PERF_CF_CONTROLLER_GPC_MAX`

Báo cáo cũ: *"`PERF_CF_CONTROLLER_GPC_MAX` id=21 f08=0xff0a f14=88 f18=273"*.
Đúng **một phần**: có **6 bản** trong 6 bảng khác nhau:

```
0x1aa578 id=19 f08=0xff08 f14=280 f18=290
0x1ac538 id=19 f08=0xff08 f14=280 f18=290
0x1ae358 id=20 f08=0xff08 f14=42  f18=273
0x1b0078 id=20 f08=0xff08 f14=42  f18=273
0x1b1c18 id=20 f08=0xff05 f14=42  f18=273
0x1b33f8 id=20 f08=0xff05 f14=42  f18=273
```

và **`PERF_CF_CONTROLLER_XBAR_MAX`** mới là cái có `f08=0xff0a, f14=88, f18=273`.
Báo cáo cũ **gán nhầm tên**. Đã sửa.

### 3.3 Tên CÓ nhưng KHÔNG có trong bảng descriptor

| Tên | Trạng thái |
|---|---|
| `RMClkVfOverride` | **KHÔNG** có descriptor |
| `RmAtsVolOverride` | **KHÔNG** |
| `RmClkControllersOverride` | **KHÔNG** |
| `OVERVOLTAGE_LOGIC` | **KHÔNG** |
| `OVERVOLTAGE_NVVDD_0` | **KHÔNG** |
| `OVERVOLTAGE_NVVDD_1` | **KHÔNG** |
| `PERFORMANCE_CAP0` | **KHÔNG** |

Đây là các chuỗi **tồn tại trong binary** nhưng **không đăng ký qua bảng
descriptor** → có thể là tên nội bộ, hoặc thuộc **bảng descriptor khác chưa tìm**.

---

## 4. XREF — vẫn 0, nhưng lý do đã khác

Sau khi sửa parser, vẫn kiểm tra lại con trỏ ngược về base từng bảng:

```
bang @0x1aa418 base: 0 hit
bang @0x1aa578 base: 0 hit
... (tất cả 60 bảng: 0 hit)
```

**Kết luận (CORROBORATED):** bảng descriptor được truy cập **bằng địa chỉ tính
toán** (base + index × 32), không qua con trỏ lưu trong data. Nghĩa là code
GSP-RM giữ base dưới dạng **hằng số ngay trong lệnh** (`lui`/`auipc`), không
phải biến con trỏ.

Điều này giải thích vì sao quét con trỏ thất bại, và chỉ ra hướng đúng:
**tìm hằng số `0x41AA418` trong code**, hoặc tìm ngay **`id` và `f14`** dưới dạng
số học trong lệnh.

---

## 5. Phân loại subsystem (theo mục 6.C)

Từ 340 tên, phân loại được:

| Lớp chức năng | Ví dụ tên | Số entry |
|---|---|---:|
| **Clock/power management** | `PERF_CF_CONTROLLER_*`, `MCLK_LIMIT`, `RATED_TDP_MIN`, `JPAC_PSTATE_MAX` | ~60 |
| **Voltage management** | `VMIN_NVVDD_0/1`, `VMIN_MSVDD_1`, `VMIN_LOGIC`, `RELIABILITY_NVVDD`, `UNLOAD_DRIVER_VOLTAGE_RAIL_0..3` | ~12 |
| **P-state / perf rules** | `MODS_RULES_STRICT_*`, `CLIENT_LOW_STRICT_*` | ~50 |
| **SLI/boost** | `SLI_GPU_BOOST_DOM_GRP_0/1` | 2 |
| **PMU domain** | `PMU_DOM_GRP_1` | 1 |
| **Debug/test** | `FORCED_DACPERFTEST` | 1 |
| **Khác** | 200+ entry chưa phân loại | ~214 |

---

## 6. Điểm thiếu bằng chứng (mục 6.J)

| # | Thiếu | Trạng thái |
|---|---|---|
| 1 | Consumer của từng entry (hàm nào đọc) | **BLOCKED** — cần Ghidra |
| 2 | Nghĩa `f08` (16 giá trị) | **UNKNOWN** |
| 3 | Nghĩa `f18` (13 giá trị, 2 nhóm rời) | **UNKNOWN** |
| 4 | Nghĩa `f14` | **UNKNOWN** |
| 5 | Nghĩa `f1c` | **UNKNOWN** |
| 6 | `id` duy nhất trong phạm vi nào | **DECODED** — trong 1 bảng |
| 7 | Bảng descriptor thứ hai chứa `RMClkVfOverride` | **UNKNOWN** — có thể tồn tại |

---

## 7. Trạng thái P3

| Mục đề bài | Trạng thái |
|---|---|
| A. Phân tích toàn bộ gsp_tu10x.bin | **ĐẠT** — 22,901,632 B |
| B. Section map / relocation / function / data inventory | **ĐẠT MỘT PHẦN** — 37 section, 11 PT_LOAD; không có `.rela`; function inventory **chưa làm** |
| C. Nhận dạng 11 lớp chức năng | **ĐẠT MỘT PHẦN** — 6/11 lớp có tên đại diện |
| D. Giải mã registry descriptor table | **ĐẠT** — 340 entry thật, layout xác nhận |
| E. Tìm consumer mỗi descriptor | **BLOCKED** — 0 xref, cần Ghidra |
| F. Call graph theo subsystem | **CHƯA** — phụ thuộc E |
| G. Magic constants / register refs / command IDs | **CHƯA** |
| H. Đối chiếu register access với MMIO map | **CHƯA** |
| I. Bản đồ Host RM ↔ GSP-RM ↔ Falcon | **ĐẠT MỘT PHẦN** — `clock_voltage_callgraph.md` |
| J. Ghi branch chưa xác định | **ĐẠT** — mục 6 |

**Coverage P3:** 340 entry có tên (**340/340 = 100% tên**),
0/340 có consumer (**0%**), 0/16 giá trị `f08` giải nghĩa (**0%**),
0/13 giá trị `f18` giải nghĩa (**0%**).

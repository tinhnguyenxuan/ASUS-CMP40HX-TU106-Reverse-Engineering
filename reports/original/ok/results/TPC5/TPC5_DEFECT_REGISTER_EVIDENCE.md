# TPC5 — BẰNG CHỨNG REGISTER DEFECT & 5 ỨNG VIÊN

**GPU:** TU106-100-A1 · `10DE:1F0B` · `0000:03:00.0`
**Ngày:** 2026-11-06 · **chỉ đọc**, không ghi register nào

---

## 0. KẾT LUẬN

> **KHÔNG có register nào trên TU106 được chứng minh là "OPT_TPC_DEFECTIVE".**
>
> Cả 5 ứng viên (`0x020040`, `0x020084`, `0x020350`, `0x0205C4`, `0x0203A0`) đều **không phải** register defect. Ba trong số đó trả **poison** ở địa chỉ tuyệt đối.
>
> **Nhưng tìm được thứ có giá trị hơn: mã poison `0xBADF13xx` giải mã thành `FECS_PRI_FLOORSWEEP`.** Cơ chế TPC5 bị tắt để lại **dấu vết phần cứng đọc được**.

---

## 1. Kiểm tra 5 ứng viên — đọc trực tiếp BAR0

### 1.1 Ứng viên ở địa chỉ tuyệt đối (giả thuyết "dùng trực tiếp")

| Địa chỉ | Giá trị đọc được | Phân loại |
|---|---|---|
| `0x020040` | `0x00000000` | **LIVE** — nhưng là register khác (xem §1.3) |
| `0x020084` | `0x001168CF` | **LIVE** — nhưng là register khác (xem §1.3) |
| `0x020350` | `0xBADF5040` | **POISON — không có register** |
| `0x0203A0` | `0xFFFFFFFF` | **ALL-ONES — không có register** |
| `0x0205C4` | `0xBADF5108` | **POISON — không có register** |

**3/5 không tồn tại. 2/5 tồn tại nhưng thuộc khối khác, không phải fuse.**

### 1.2 Ứng viên dưới giả thuyết "dịch sang fuse base" (`0x21000 + offset Ampere`)

Giả thuyết: Ampere fuse base `0x820000`, nên `0x820040 → 0x21000+0x40 = 0x21040`.

| Ampere | → TU106 | Giá trị | Phân loại |
|---|---|---|---|
| `0x820040` `EN_SW_OVERRIDE` | `0x021040` | `0x00000000` | **LIVE** (không phải defect) |
| `0x820084` `DIS_SW_OVERRIDE` | `0x021084` | `0xBADF5040` | **POISON — không tồn tại** |
| `0x820350` | `0x021350` | `0x00000000` | **LIVE** (không phải defect) |
| `0x8203A0` `OPT_GPC_DEFECTIVE` | `0x0213A0` | `0xBADF5040` | **POISON — không tồn tại** |
| `0x8205C4` `OPT_TPC_DEFECTIVE` | `0x0215C4` | `0x00000000` | **LIVE** (không phải defect) |

### 1.3 Ứng viên dưới giả thuyết "cộng 0x21000"

`0x020040 → 0x023040`, `0x020084 → 0x023084`, … → **cả 5 đều trả `0xBADF1100` = POISON**.

---

## 2. `0x020xxx` là khối gì? — nhận dạng của `0x020040` / `0x020084`

Hai địa chỉ này **LIVE** nhưng nội dung chứng minh chúng **không phải fuse**:

| Địa chỉ | Giá trị | Suy luận |
|---|---|---|
| `0x0200A8` | `0xC10910DE` | chứa `0x10DE` (vendor NVIDIA) ở low16 |
| `0x0207F8` | `0x000010DE` | `10DE` lần nữa |
| `0x020040` | `0x20000000` | bit 29 đơn lẻ, không phải bitmask TPC |
| `0x020084` | `0x001168CF` | giá trị đặc trưng cấu hình, không phải bitmask |
| `0x020350` | `0xBADF5040` | poison ngay giữa vùng |

⇒ `0x020000` không phải cửa sổ fuse. Không có dấu hiệu bitmask 6-bit TPC. **Bác bỏ.**

### 2.1 Kiểm tra header — không ứng viên nào có định nghĩa

| Tìm kiếm | Kết quả |
|---|---|
| `0x020040` / `0x020084` / `0x020350` / `0x0205C4` / `0x0203A0` trong `swref/published/turing/` | **0 file** |
| 5 địa chỉ trong **toàn bộ** `swref/published/` (mọi chip) | **0 file** |
| `0x8205C4` / `0x8203A0` / `0x820040` / `0x820084` trong toàn bộ `swref/` | **0 file** |

**Lưu ý phương pháp:** đây **không** phải bằng chứng "không tồn tại". Nó chỉ cho thấy header open-source **không phủ** các register này. Kết luận "không tồn tại" ở §1 dựa trên **poison readback**, không dựa trên grep.

### 2.2 `tu102/dev_fuse.h` chỉ có 2 register

```c
#define NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS        0x0002174C /* RW-4R */
#define NV_FUSE_OPT_NVDEC_DISABLE               0x00021378 /* RW-4R */
```

Header published của Turing **không** có `STATUS_OPT_GPC`, `STATUS_OPT_TPC_GPC*`, `STATUS_OPT_FBP`, hay bất kỳ defect register nào. Kể cả `ga100/dev_fuse.h` (141 dòng) cũng **không** có `0x8205C4`/`0x8203A0`.

⇒ Tên "`OPT_TPC_DEFECTIVE`" cho `0x8205C4` là **kiến thức từ ngoài repo** (cộng đồng Ampere), không có trong source NVIDIA mở. Không được dùng làm định nghĩa TU106.

---

## 3. ĐỐI CHIẾU CÓ KIỂM CHỨNG — TU104 `issue #187`

Nguồn: `https://github.com/physicsdolphin/nv-uefi-unlocker/issues/187`
GPU: EVGA RTX 2060 KO, **TU104 A1**, `10de:1e89`, driver **nouveau**, SystemRescue 13.02, đọc BAR0 `O_RDONLY`/`PROT_READ`.

### 3.1 Dữ liệu TU104 #187 (bản gốc)

```
STATUS_OPT_GPC     0x021c1c = 0x00000008   -> chỉ GPC3 fused off
STATUS_OPT_TPC_GPC0 0x021c38 = 0x00000031
STATUS_OPT_TPC_GPC1 0x021c3c = 0x00000031
STATUS_OPT_TPC_GPC2 0x021c40 = 0x00000031
STATUS_OPT_TPC_GPC3 0x021c44 = 0x0000003f   (GPC tắt toàn bộ)
STATUS_OPT_TPC_GPC4 0x021c48 = 0x00000031
STATUS_OPT_TPC_GPC5 0x021c4c = 0x00000031
CTRL_OPT_TPC_GPC0..5                   = 0x00000000
[GR] GPC_UNIT(g,0x2608) g=0..4 = 3,3,3,3,3 -> 15 TPC = 30 SM
```

### 3.2 So sánh trực tiếp TU104 ↔ TU106 (CMP 40HX)

| Register | TU104 | TU106 (CMP 40HX) | Diễn giải |
|---|---|---|---|
| `STATUS_OPT_GPC` `0x21C1C` | `0x08` | `0x38` | TU104: 1 GPC tắt (GPC3). TU106: 3 GPC tắt (3,4,5) |
| `TPC_GPC0` `0x21C38` | `0x31` = `0b110001` | `0x20` = `0b100000` | **TU104 tắt TPC0 VÀ TPC4,5**; TU106 chỉ tắt **TPC5** |
| `TPC_GPC1` `0x21C3C` | `0x31` | `0x00` | TU104 tắt TPC0,4,5; TU106 **không tắt gì** |
| `TPC_GPC2` `0x21C40` | `0x31` | `0x00` | như trên |
| `TPC_GPC3` `0x21C44` | `0x3F` | `0x3F` | cả hai: GPC không tồn tại → tắt toàn bộ |
| `TPC_GPC4` `0x21C48` | `0x31` | `0x3F` | TU104 GPC4 **tồn tại**; TU106 không có GPC4 |
| `TPC_GPC5` `0x21C4C` | `0x31` | `0x3F` | như trên |
| `CTRL_OPT_TPC_*` | `0x00` ×6 | `0x00` ×6 | **cả hai: override không bật** |

### 3.3 Điều #187 xác lập được (áp dụng cho TU106)

1. **`STATUS_OPT_TPC_GPC` rộng 6 bit trên Turing.** TU102 = 6 TPC/GPC, TU104 = 4 TPC/GPC. Trên TU104, **bit 4 và 5 luôn set** vì TPC đó không tồn tại. Bits 3:0 là bit có nghĩa.
   → Áp dụng TU106: **bit 0..5 đều có nghĩa** (TU106 có 6 TPC/GPC).
2. **Layout `0x021xxx` của Turing đã được xác nhận độc lập**: status `0x21c38+4g`, ctrl `0x21838+4g`, gpc `0x21c1c`. GR và fuse **đồng ý** với nhau.
3. **`CTRL_OPT_TPC_GPC = 0` nghĩa là override không bật.** Không có Software Override đang hoạt động.
4. **Suy đoán dịch Ampere `0x820040/0x820084` sang `0x021040/0x021084` là SAI.** `0x021084` trả `0xBADF5040`.
5. **Fuse không cho biết GPC/TPC đó có defective hay không.** #187 ghi rõ: *"The fuses do not show if GPC3 is defective."*

### 3.4 Điểm #187 để NGỎ — và D3 trả lời được một phần

> *"If you know the Turing addresses for EN/DIS_SW_OVERRIDE and for the OPT_GPC_DEFECTIVE / TPC defect banks (`0x8205c4` / `0x8203a0` on Ampere), tell me. I will read them."*

**Câu trả lời từ phép đọc CMP 40HX hôm nay:**

| Ampere | Dịch sang TU106 | Kết quả | Kết luận |
|---|---|---|---|
| `0x8203a0` | `0x0213a0` | `0xBADF5040` | **không tồn tại trên Turing** |
| `0x8205c4` | `0x0215c4` | `0x00000000` | tồn tại nhưng **= 0**, không mang thông tin defect |
| `0x820040` | `0x021040` | `0x00000000` | tồn tại, **= 0** |
| `0x820084` | `0x021084` | `0xBADF5040` | **không tồn tại** |

⇒ **Bank defect của Ampere KHÔNG có tương đương Turing ở các địa chỉ này.** Đây là dữ liệu thực nghiệm trả lời trực tiếp câu hỏi mở của #187.

---

## 4. PHÁT HIỆN CHÍNH — poison không phải rác, nó là mã lỗi

Đây là kết quả có giá trị nhất của nhiệm vụ này.

### 4.1 Quan sát

Khi đọc `TPC_UNIT` cho 6 TPC của GPC0 (công thức nouveau `0x504000 + tpc*0x800`):

```
GPC0 TPC0  base=0x504000  +000=0xBADF5040  +004=0x00000000  +010=0x00000000  +200=0x000900F0
GPC0 TPC1  base=0x504800  +000=0xBADF5040  +004=0x00000000  +010=0x00000000  +200=0x000900F0
GPC0 TPC2  base=0x505000  +000=0xBADF5040  +004=0x00000000  +010=0x00000000  +200=0x000900F0
GPC0 TPC3  base=0x505800  +000=0xBADF5040  +004=0x00000000  +010=0x00000000  +200=0x000900F0
GPC0 TPC4  base=0x506000  +000=0xBADF5040  +004=0x00000000  +010=0x00000000  +200=0x000900F0
GPC0 TPC5  base=0x506800  +000=0xBADF1300  +004=0xBADF1300  +010=0xBADF1300  +200=0xBADF1300
                                                                  ^^^^^^^^^^^^
```

**TPC0–TPC4 trả `0xBADF5040` ở +000 nhưng `0x00000000` ở +004/+010 và LIVE ở +200.
TPC5 trả `0xBADF1300` ở MỌI offset.**

### 4.2 Giải mã mã poison

Header `maxwell/gm107/dev_pri_ringstation_sys.h:34-41`:

```c
#define NV_PPRIV_SYS_PRI_ERROR_CODE                                    31:8  /* --XVF */
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_PRI_TIMEOUT               0xBADF10
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_PRI_DECODE                0xBADF11
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_PRI_RESET                 0xBADF12
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_PRI_FLOORSWEEP            0xBADF13   <<<<<
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_PRI_STUCK_ACK             0xBADF14
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_PRI_0_EXPECTED_ACK        0xBADF15
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_PRI_FENCE_ERROR           0xBADF16
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_PRI_SUBID_ERROR           0xBADF17
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_PRI_ORPHAN                0xBADF20
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_DEAD_RING                 0xBADF30
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_TRAP                      0xBADF40
#define NV_PPRIV_SYS_PRI_ERROR_CODE_FECS_PRI_CLIENT_ERR            0xBADF50
```

### 4.3 Bảng giải mã toàn bộ poison gặp phải

| Poison | Byte [31:8] | Mã lỗi | Nghĩa |
|---|---|---|---|
| `0xBADF5040` | `0xBADF50` | **`FECS_PRI_CLIENT_ERR`** | TPC có mặt nhưng offset này không được map |
| **`0xBADF1300`** | **`0xBADF13`** | **`FECS_PRI_FLOORSWEEP`** | **TPC bị floorsweep** |
| `0xBADF1100` | `0xBADF11` | `FECS_PRI_DECODE` | địa chỉ không decode được |
| `0xBADF2023/24/25` | `0xBADF20` | `FECS_PRI_ORPHAN` | GPC không tồn tại (3/4/5) |

### 4.4 Ý nghĩa then chốt

> **Hardware không trả "không có TPC5". Nó trả "TPC5 bị FLOORSWEEP".**
>
> Đây là **phân biệt cơ học** giữa "không tồn tại" và "bị tắt", do chính GPU phát ra, không phải suy luận của ta:
>
> - `FECS_PRI_ORPHAN` → GPC3/4/5 **không tồn tại** (địa chỉ mồ côi)
> - `FECS_PRI_FLOORSWEEP` → **TPC5 tồn tại nhưng bị floorsweep**
> - `FECS_PRI_CLIENT_ERR` → TPC0–4 có mặt, chỉ offset +000 không map

Đây là **bằng chứng mạnh nhất** trong toàn bộ nghiên cứu TPC5: GPU tự phân loại TPC5 là *floorswept*, không phải *absent*.

### 4.5 Giới hạn của bằng chứng này — nói thẳng

| Điều chứng minh được | Điều KHÔNG chứng minh được |
|---|---|
| TPC5 **tồn tại** trong thiết kế hardware (không phải orphan) | TPC5 có **transistor thực** hay đã bị cắt bằng mask |
| Hardware gắn nhãn nó là **floorsweep** | TPC5 có **chức năng tốt** hay defective |
| Phân biệt được với GPC3/4/5 (`ORPHAN`) | Có thể bật TPC5 mà không hỏng gì |

**`FECS_PRI_FLOORSWEEP` là mã trạng thái, không phải kết quả kiểm định chất lượng.**
Nó nói "đơn vị này bị loại khỏi cấu hình", không nói "đơn vị này hỏng" hay "đơn vị này tốt".

---

## 5. Có register `OPT_TPC_DEFECTIVE` trên TU106 không?

### 5.1 Bằng chứng phủ định có kiểm soát

| Phương pháp | Kết quả | Sức mạnh |
|---|---|---|
| Readback poison tại `0x0213A0`, `0x021084` | không tồn tại | **mạnh** — hardware trả lời |
| `tu102/dev_fuse.h` | chỉ 2 register, không có defect | trung bình — header published không đầy đủ |
| `ga100/dev_fuse.h` | 141 dòng, không có `0x8205C4`/`0x8203A0` | trung bình |
| Grep toàn `swref/` | 0 hit cho cả Ampere lẫn Turing | **yếu** — không chứng minh phủ định |

### 5.2 Kết luận đúng mức

> **Không tìm được register defect nào trên TU106.** Không khẳng định "TU106 không có cơ chế defect" — chỉ khẳng định **không có trong 5 ứng viên đã kiểm, không có trong header open-source, và các địa chỉ Ampere tương ứng đều poison/zero.**
>
> **Đường dữ liệu gián tiếp chưa loại trừ:** defect flag có thể nằm trong vùng fuse khác chưa được đặt tên, trong OTP riêng, hoặc trong dữ liệu do SEC2/devinit xử lý mà host không thấy.

### 5.3 Điều #187 cũng nói vậy — và nó là quan sát độc lập

> *"The fuses do not show if GPC3 is defective."*

Trên TU104, tác giả cũng không tìm được defect flag. Với CMP 40HX: **cùng kết luận, cùng lý do**.

---

## 6. Tổng kết

| Mục | Kết quả |
|---|---|
| 5 ứng viên có phải register defect? | **KHÔNG** — 3 poison, 2 thuộc khối khác |
| Có register `OPT_TPC_DEFECTIVE` trên TU106? | **Không tìm thấy** — không khẳng định không tồn tại |
| Đối chiếu TU104 #187 | **Khớp layout**, cùng kết luận về defect flag |
| Trả lời câu hỏi mở của #187 | **CÓ** — bank defect Ampere không có tương đương Turing ở các địa chỉ đó |
| **Phát hiện chính** | **`0xBADF1300` = `FECS_PRI_FLOORSWEEP`** — hardware tự gắn nhãn TPC5 là floorswept, không phải orphan |

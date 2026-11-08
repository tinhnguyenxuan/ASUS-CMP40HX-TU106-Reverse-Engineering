# VFE / VOLTAGE DEEP REVERSE — Phase 5B

> **Publication edition (V5):** This is a curated ROM/source-analysis extract from the supplied `vbiosrel6(2).zip`. Host telemetry, game tests, benchmark steps and Windows/Linux collectors are intentionally omitted. It is historical research, **not** new hardware verification. See [integrated report](../../../docs/TU106_VBIOS_PHASE4_6.md).


**Phạm vi:** bảng VFE v0x30 (P2 slot 8, envytools gọi là "VOLT MAPPING"), phần mở rộng
20 byte của POWER BUDGET, khối `rel`/`viol`, và VFE liên quan gì tới clock/voltage limit.

**Môi trường:** ROM tĩnh. Không có GPU. Các giá trị *đọc được*; ngữ nghĩa số học phần lớn
**UNKNOWN** vì không có consumer công khai.

---

## 0. KẾT QUẢ

| # | Nội dung | Mức |
|---|---|---|
| 1 | VFE **không phải** bảng voltage-rail. Nó là **bảng phương trình** (Variable/Equation). Header + entry khớp `vbios_vfe_3x_*` của nvgpu. | PROVEN |
| 2 | Extent chỉ đóng khi tính **cả 3 khối**: `9 + 20*25 + 150*24 + 55*24 + 15 = 5444` = đúng span slot 8 ở cả 3 ROM. | PROVEN |
| 3 | Mọi `type` byte trong var ∈ 0..7 và equ ∈ 0..6 — đúng enum NVIDIA. Stride sai sẽ phá ngay. | PROVEN |
| 4 | 55 bản ghi rppm 24 B + 15 B tail: **cấu trúc suy ra, ngữ nghĩa UNKNOWN**. | UNKNOWN |
| 5 | 20 byte mở rộng của POWER BUDGET entry: **UNKNOWN**, không có schema. | UNKNOWN |
| 6 | `rel` (15×14) và `viol` (13×13): kích thước **PROVEN** (header khai báo + extent đóng), nội dung **UNKNOWN**. | PROVEN size / UNKNOWN content |
| 7 | Không có trường nào trong VFE/Power Budget **chứng minh** được là "giới hạn xung" hay "điều kiện throttle". | UNKNOWN |

---

## 1. VFE LÀ GÌ — SỬA LẠI GIẢ ĐỊNH CỦA v3

v3 gọi slot 8 là "VOLT MAPPING" và cố parse nó bằng `vbios_voltage_rail_table_1x`. Sai.
Header thật: `30 09 19 14 18 96 c8 0f 28`:

| off | giá trị | nghĩa (nvgpu) |
|---|---|---|
| +0 | `0x30` | `version` — khớp `VBIOS_VFE_3X_HEADER_SIZE_09`... thực ra là version 3x |
| +1 | `9` | `header_size` |
| +2 | `0x19` = 25 | `vfe_var_entry_size` |
| +3 | `0x14` = 20 | `vfe_var_entry_count` |
| +4 | `0x18` = 24 | `vfe_equ_entry_size` |
| +5 | `0x96` = 150 | `vfe_equ_entry_count` |
| +6 | `0xc8` = 200 | `polling_periodms` |
| +7 | `0x0f` = 15 | `vfe_var_rppm_entry_count` |
| +8 | `0x28` = 40 | `vfe_equ_rppm_entry_count` |

Đây **chính xác** là `struct vbios_vfe_3x_header_struct` (nvgpu `bios.h:341`).
⇒ Slot 8 = **Voltage/Frequency Equation table**, không phải bảng rail.

### 1.1 Var entry (25 B)

```c
struct vbios_vfe_3x_var_entry_struct {
    u8 type;
    u32 out_range_min, out_range_max;
    u32 param0, param1, param2, param3;
};
```
`type` enum: 0 DISABLED · 1 SINGLE_FREQUENCY · 2 SINGLE_VOLTAGE · 3 SINGLE_SENSED_TEMP ·
4 SINGLE_SENSED_FUSE · 5 DERIVED_PRODUCT · 6 DERIVED_SUM · 7 SINGLE_CALLER_SPECIFIED.

Đọc được trên CMP (20 entry): `4,4,4,4,4,4,4,4,5,6,3,4,3,2,5,5,...`
⇒ chủ yếu `SINGLE_SENSED_FUSE` (4) và `DERIVED_PRODUCT` (5): các biến đầu vào lấy từ **fuse**
và từ **tích của biến khác**. Đây là mô tả toán học của V/F curve, **không phải** một dãy
điện áp.

### 1.2 Equ entry (24 B)

```c
struct vbios_vfe_3x_equ_entry_struct {
    u8 type; u8 var_idx; u8 equ_idx_next;
    u32 out_range_min, out_range_max;
    u32 param0, param1, param2;
    u8 param3;
};
```
`type`: 0 DISABLED · 1 QUADRATIC · 2 MINMAX · 3 COMPARE · 4 QUADRATIC_FXP · 5 MINMAX_FXP ·
6 EQUATION_SCALAR.
`param3 & 0xF` = `PAR3_OUTPUT_TYPE`: 0 UNITLESS · 1 **FREQ_MHZ** · 2 **VOLT_UV** ·
3 VF_GAIN · 4 VOLT_DELTA_UV · 6 WORK_TYPE · 7 UTIL_RATIO · 9 **POWER_MW** ·
0xA PWR_OVER_UTIL_SLOPE · 0xC **THRESHOLD**.

Phân bố type trên CMP (150 entry): `1`×89 (QUADRATIC), `0`×29, `3`×25 (COMPARE), `2`×6,
`4`×1. `var_idx` ∈ {5,7,9..18, 0xFF}.

**Đây là chỗ có ý nghĩa nhất:** `COMPARE` (3) + output type `THRESHOLD` (0xC) nghĩa là bảng
này **có** logic điều kiện — nó có thể mô tả "nếu nhiệt > X thì trần xung = Y". Nhưng:
- Không có consumer công khai để xác nhận cách PMU/GSP đánh giá nó.
- `out_range_min/max` là **IEEE754 float32**, không phải số nguyên. Bằng chứng: đọc thô cho
  `0x42240000` = **41.0**, `0x42700000` = **60.0**, `0x00000000` = 0.0,
  `0x7F7FFFFF` = ±**3.4028e38** (= FLT_MAX, dùng làm "không giới hạn"), `0xC2D20000` = -105.0.
  Một chuỗi toàn giá trị hợp lý như vậy không thể là ngẫu nhiên ⇒ **PROVEN** là float32.

⇒ **PROVEN**: có bảng phương trình, có entry COMPARE/THRESHOLD, có output type FREQ/VOLT/POWER.
⇒ **UNKNOWN**: giá trị nào đang được PMU dùng, ngưỡng cụ thể là gì, và có áp cho CMP khác
GeForce hay không.

### 1.3 Rppm (55 × 24 + 15)

`var_rppm_cnt = 15`, `equ_rppm_cnt = 40` → 55. Vùng còn lại 1335 B = 55×24 + 15.
Kiểm tra chu kỳ trên 1335 B: period 24 cho **1235/1296** byte trùng (95%), cao hơn hẳn
period 16/20/25/32/33. ⇒ 24 B là stride đúng.

Tail 15 byte toàn `00` ở cả 3 ROM. Không đủ để gọi là index table.
**UNKNOWN** — không có struct nào trong nvgpu cho khối rppm.

---

## 2. POWER BUDGET — 20 BYTE MỞ RỘNG VÀ rel/viol

### 2.1 Cái đã biết (từ Phase 4)

```
44 + 20*66 + 15*14 + 13*13 = 1743  (đóng chính xác, cả 3 ROM)
```
Header nvgpu 37 B, ROM 44 B ⇒ **+7 byte**; entry nvgpu 46 B, ROM 66 B ⇒ **+20 byte**.

### 2.2 20 byte mở rộng của entry — UNKNOWN

Entry 66 B, các trường nvgpu chiếm 0..45. Phần 46..65 (20 byte) **không có tên**.
Quan sát: phần lớn là `00`, có vài entry chứa giá trị nhỏ. Không đủ để đoán.
⇒ **UNKNOWN**. Cần: GSP-RM disassembly hoặc một ROM family khác có cùng độ rộng.

### 2.3 rel (15 × 14 B) và viol (13 × 13 B)

Header khai báo `table_rel_entry_size=14`, `num_table_rel_entries=15`,
`table_viol_entry_size=13`, `num_table_viol_entries=13`. Extent đóng ⇒ **kích thước PROVEN**.

Nội dung: `rel` nhiều khả năng là quan hệ giữa các entry (ratios/dependencies), `viol` là
bảng vi phạm (violation) — nhưng **không có field name nào**. Ghi **UNKNOWN**.

### 2.4 `param0..3`, `filter_param`, `ratio_min/max`, `sample_mult`

nvgpu đặt tên nhưng không mô tả. Đọc được: `param0 = 0x00000010` ở nhiều entry.
Đây là nơi **có thể** chứa hysteresis/filter của bộ điều khiển công suất, nhưng chưa
chứng minh. **UNKNOWN**.

---

## 3. VFE CÓ LIÊN QUAN GÌ TỚI CLOCK/VOLTAGE LIMIT

Chuỗi suy luận được phép:

```
VFE equ entry (type=COMPARE, param3&0xF=THRESHOLD)
        ↓  (PMU/GSP đánh giá)
   đầu ra (FREQ_MHZ / VOLT_UV / POWER_MW)
        ↓
   trần xung / trần áp / trần công suất lúc chạy
```

Ba mắt đầu **có** trong ROM. Mắt "PMU/GSP đánh giá thế nào" **không** có trong nguồn mở.

Điều **không** được nói:
- Không nói "VFE giới hạn xung CMP" — chưa so được entry nào active.
- Không nói "CMP có VFE khác GeForce" — **chưa so**. Đây là việc rẻ nhất còn lại: diff 150
  equ entry giữa 3 ROM.

**So sánh nhanh đã làm:** cả 3 ROM có cùng header (`20/25/150/24`), cùng phân bố type byte
đầu, cùng 1335 B rppm. Chưa diff từng entry — nếu diff ra 0 khác biệt thì VFE **không** phải
nguyên nhân SKU; nếu có khác biệt thì đó là ứng viên.

```bash
# việc tiếp theo, 2 phút:
python3 - <<'EOF'
import sys; sys.path.insert(0,"scripts")
from tu106_vbios import load
R={n:load(f"./roms/{f}",n) for n,f in
   (("CMP","TU106.rom"),("2060S","219827.rom"))}
a,b=R["CMP"].vfe_3x(),R["2060S"].vfe_3x()
for kind in ("vars","equs","rppm"):
    d=[i for i,(x,y) in enumerate(zip(a[kind],b[kind]))
       if x["off"]!=0 and (y.get("raw") or b"")!=x.get("raw",b"") ]
    print(kind,"entries differing:",len(d))
EOF
```

**Đã chạy trong Phase 5:** xem §4.

---

## 4. SO VFE GIỮA 3 ROM — KẾT QUẢ (sửa lại: KHÔNG giống 2070)

So theo **giá trị trường** (bỏ `off`), không theo offset file:

| khối | CMP vs 2060S | CMP vs 2070 |
|---|---|---|
| header (9 B) | giống | giống |
| 20 var entry | **giống hệt** (0/20 khác) | **3 khác** (var 3, 6, 7) |
| 150 equ entry | **giống hệt** (0/150 khác) | **25 khác** |
| rppm + tail | giống hệt | giống hệt |
| toàn bảng (byte) | **5444/5444 giống** | **5240/5444 giống** (204 B khác) |

⇒ **CMP giống byte-for-byte với RTX 2060 SUPER. CMP KHÁC RTX 2070.**

Khác biệt CMP↔2070 đọc được ngay bằng float32:

| entry | CMP / 2060S | 2070 | nhận xét |
|---|---|---|---|
| var 6 (type 4 = SENSED_FUSE) | `[41.0, 41.0]` | `[60.0, 60.0]` | hai ngưỡng số, chênh 19 |
| var 7 | `[1981, 2336]` | `[1981, 2336]` | **giống** |
| var 3 | `[−FLT_MAX, +FLT_MAX]` | như trên | "không giới hạn" |
| equ 5 | `[−75000, 0]` | `[0, 0]` | 2070 bỏ một dải âm |
| equ 2 | float nhỏ ~1.7e-38 | ~1.79e-38 | denormal, khác 1 bit |

**Đọc được (HYPOTHESIS về nghĩa):** `41.0` / `60.0` ở một biến `SENSED_FUSE` gần như chắc là
**ngưỡng nhiệt °C** (41 °C là mốc fan/clock thấp điển hình; 60 °C là mốc cao hơn). 2070 đặt
ngưỡng cao hơn vì card đó chạy 1408/1620 MHz và tản nhiệt khác.
Nhưng: **chưa có consumer** để xác nhận đơn vị ⇒ **HYPOTHESIS**, không phải kết luận.



Mức: **PROVEN** (so byte), kết luận "VFE không phân biệt CMP với 2060S" = **STRONGLY SUPPORTED**.

---

## 5. CÒN LẠI GÌ ĐỂ GIẢI MÃ

| # | câu hỏi | cần gì |
|---|---|---|
| 1 | `out_range_min/max` là float hay fixed-point, scale bao nhiêu | consumer RM/GSP, hoặc so với một V/F point đã biết từ `nvidia-smi -q -d SUPPORTED_CLOCKS` |
| 2 | 20 B mở rộng của PB entry | GSP-RM, hoặc ROM family khác cùng width |
| 3 | nội dung rel / viol | GSP-RM |
| 4 | 15 B tail của rppm | một chip khác có rppm |
| 5 | bit 3 của LOW POWER GR | xem `LOW_POWER_GR_RESEARCH.md` |
| 6 | entry nào của VFE đang active | telemetry runtime (nhiệt, công suất, xung) + đối chiếu |

Không đặt tên cho bất kỳ byte nào ở trên. Chưa có schema thì để UNKNOWN.

---

## 6. KẾT LUẬN

1. **VFE = bảng phương trình V/F**, không phải bảng rail. Giải mã được **cấu trúc đầy đủ**
   (header 9, var 25×20, equ 24×150, rppm 55×24+15) với extent đóng tuyệt đối 5444 B.
2. **VFE của CMP giống byte-for-byte với RTX 2060 SUPER**, khác 2070 ở 204 byte (float32
   coefficient). ⇒ VFE **không** phân biệt CMP với 2060S.
3. `out_range_min/max` là **float32** (bằng chứng: 41.0, 60.0, 0.0, ±FLT_MAX, −105.0).
3. **POWER BUDGET** có 20 B mở rộng + khối rel/viol: kích thước biết, nội dung **UNKNOWN**.
4. CMP khác 2070 ở một ngưỡng `41.0` vs `60.0` — **HYPOTHESIS** là ngưỡng nhiệt °C, chưa có
   consumer xác nhận.
5. Không có trường nào trong hai bảng này **chứng minh** là cơ chế throttle. Muốn biết phải
   đo (M15/M16) và/hoặc disassemble GSP-RM.

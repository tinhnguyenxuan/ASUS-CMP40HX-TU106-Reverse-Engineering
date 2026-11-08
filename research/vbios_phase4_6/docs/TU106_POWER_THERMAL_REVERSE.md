# TU106 POWER / THERMAL REVERSE — Phase 4D

> **Publication edition (V5):** This is a curated ROM/source-analysis extract from the supplied `vbiosrel6(2).zip`. Host telemetry, game tests, benchmark steps and Windows/Linux collectors are intentionally omitted. It is historical research, **not** new hardware verification. See [integrated report](../../../docs/TU106_VBIOS_PHASE4_6.md).


**Bản:** Phase 4. Giải mã thêm 3 bảng trong v3 (POWER BUDGET, POWER TOPOLOGY, THERMAL POLICY)
và đóng lại phần lớn nhóm UNKNOWN về power.
**Môi trường:** ROM tĩnh. Không có GPU để đối chiếu `nvidia-smi` ⇒ mọi giá trị là *cấu
hình trong ROM*, không phải *trạng thái đang chạy*.

---

## 0. PHÁT HIỆN CHÍNH

> **POWER BUDGET đã giải mã được, và nó bác bỏ giả thuyết "CMP bị giới hạn công suất".**
>
> | | CMP 40HX | RTX 2060S | RTX 2070 |
> |---|---|---|---|
> | `limit_min` | **110 W** | 125 W | 125 W |
> | `limit_rated` (mặc định) | **184 W** | **184 W** | 185 W |
> | `limit_max` (trần cho phép) | **220 W** | **220 W** | 222 W |
>
> Mặc định **bằng nhau**, trần **bằng nhau**. CMP chỉ cho phép đặt **thấp hơn** (110 W so
> với 125 W) — tức một lựa chọn *hạ*, không phải một trần *hạ*.
>
> ⇒ Nếu card CMP thực tế chạy dưới 184 W thì đó là **quyết định runtime** (driver/BIOS
> policy/board), không phải giới hạn trong bảng power budget.

---

## 1. CÁCH TÌM RA SCHEMA (để tái lập)

v3 kết luận POWER BUDGET là UNKNOWN vì "envytools v0x30 không đóng extent". Nguyên nhân:
envytools mô tả **bản gốc** của bảng; TU106 dùng bản mở rộng. Cái làm nó đóng được là
**header tự khai báo kích thước của cả bốn khối con**.

`nvgpu include/nvgpu/bios.h`:

```c
#define VBIOS_POWER_POLICY_3X_HEADER_SIZE_25   0x25U     /* 37 */
struct pwr_policy_3x_header_struct {
    u8 version, header_size, table_entry_size, num_table_entries;
    u16 base_sample_period, min_client_sample_period;
    u8 table_rel_entry_size, num_table_rel_entries;
    u8 tgp_policy_idx, rtp_policy_idx, mxm_policy_idx, dnotifier_policy_idx;
    u32 d2_limit, d3_limit, d4_limit, d5_limit;
    u8 low_sampling_mult, pwr_tgt_policy_idx, pwr_tgt_floor_policy_idx,
       sm_bus_policy_idx, table_viol_entry_size, num_table_viol_entries;
};
#define VBIOS_POWER_POLICY_3X_ENTRY_SIZE_2E    0x2EU      /* 46 */
struct pwr_policy_3x_entry_struct {
    u8 flags0, ch_idx;
    u32 limit_min, limit_rated, limit_max;
    u32 param0, param1, param2, param3, limit_batt;
    u8 flags1, past_length, next_length;
    u16 ratio_min, ratio_max;
    u8 sample_mult; u32 filter_param;
};
```

ROM slot 11 (CMP @ `0x57e92`):

```
30 2c 42 14 | 14 00 14 00 0e 0f 02 ff ff ff 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 32 0f ff ff | 0d 0d | ff 00 ff ff ...
```

| off | nvgpu field | ROM | ghi chú |
|---|---|---|---|
| +0 | version | `0x30` | khớp `VBIOS_POWER_POLICY_VERSION_3X` |
| +1 | header_size | `0x2c` = 44 | nvgpu 37 ⇒ **+7 byte mở rộng** |
| +2 | table_entry_size | `0x42` = 66 | nvgpu 46 ⇒ **+20 byte mở rộng** |
| +3 | num_table_entries | `0x14` = 20 | |
| +4 | base_sample_period | 20 ms | |
| +6 | min_client_sample_period | 20 ms | |
| +8 | table_rel_entry_size | 14 | |
| +9 | num_table_rel_entries | 15 | |
| +10..13 | tgp/rtp/mxm/dnotifier idx | `02 ff ff ff` | chỉ TGP được đặt |
| +14..29 | d2..d5_limit | 0,0,0,0 | |
| +30 | low_sampling_mult | `0x32` = 50 | |
| +31 | pwr_tgt_policy_idx | `0x0f` = 15 | |
| +32 | pwr_tgt_floor_policy_idx | `0xff` | |
| +33 | sm_bus_policy_idx | `0xff` | |
| +34 | table_viol_entry_size | **13** | |
| +35 | num_table_viol_entries | **13** | |

**Extent đóng chính xác:**

```
44 + 20*66 + 15*14 + 13*13 = 44 + 1320 + 210 + 169 = 1743
0x57e92 + 1743 = 0x58561 = slot kế tiếp theo địa chỉ
```

Cả 3 ROM: `1743` khớp tuyệt đối. Đây là **PROVEN** cho cấu trúc.

---

## 2. POWER BUDGET — 20 ENTRY

Entry 66 byte; các trường nvgpu ở đầu entry:

| off | field |
|---|---|
| +0 | `flags0` (`class_id = [3:0]`, `limit_unit = [4]`) |
| +1 | `ch_idx` |
| +2 | `limit_min` (u32) |
| +6 | `limit_rated` (u32) |
| +10 | `limit_max` (u32) |
| +14..+29 | `param0..3` |
| +30 | `limit_batt` |
| +34 | `flags1` |
| +38 | `flags1`?? — parser đọc `u8(e+38)`; phần còn lại của 66−46=20 byte mở rộng **UNKNOWN** |

Giá trị có ý nghĩa (CMP):

| entry | class | unit | min | rated | max | diễn giải |
|---|---|---|---|---|---|---|
| 0 | 0xa | 0 | 20000 | 5001000 | 5001000 | sai đơn vị — **UNKNOWN** |
| 1 | 0x4 | 0 | 1 | 1001000 | 1001000 | **UNKNOWN** |
| **2** | **1** | 0 | **110000** | **184000** | **220000** | **GPU power limit, mW** |
| 3 | 4 | 0 | 1000 | 64000 | 76000 | rail phụ |
| 4 | 4 | 0 | 1000 | 147000 | 172000 | rail phụ |
| 5 | 0 | 0 | 1000 | 162000 | 175000 | rail phụ |
| 7 | 5 | 1 | 1000 | 11000 | 13100 | nvgpu: class 5 = `HW_THRESHOLD` ⇒ **ngưỡng**, không phải watt |
| 8 | 5 | 1 | 1000 | 17000 | 25400 | ngưỡng |
| 12 | 5 | 1 | 100000 | 208000 | 208000 | ngưỡng |
| 13 | 0xa | 1 | 1000 | 162000 | 162000 | **UNKNOWN** |

**Vì sao entry 2 là GPU limit và đơn vị là mW:**
1. `class_id = 1` — không phải class 5 (`HW_THRESHOLD`) đã biết, nên là một loại limit thật.
2. Ba giá trị liên hệ đúng thứ tự min < rated < max.
3. `184000` và `220000` rơi đúng vào dải công suất của một card TU106 8-pin.
4. Nếu là %, giá trị 184000 vô nghĩa; nếu là µW, 0,184 W vô nghĩa. **mW** là đơn vị duy
   nhất cho ra số hợp lý.

Mức: cấu trúc **PROVEN**; đơn vị + ánh xạ entry→GPU limit **STRONGLY SUPPORTED**.

### 2.1 So ba ROM

| | CMP | 2060S | 2070 |
|---|---|---|---|
| `limit_min` | **110000** | 125000 | 125000 |
| `limit_rated` | 184000 | 184000 | **185000** |
| `limit_max` | 220000 | 220000 | **222000** |

Khác biệt duy nhất giữa CMP và 2060S: **`limit_min` thấp hơn 15 W**. Đây là *nới* dải,
không phải *siết*.

> **Đối chiếu với spec công bố** (175 W cho cả 2060S và 2070): ROM ghi 184/185 W.
> Hai con số không mâu thuẫn — "TDP" marketing và "rated power limit" trong VBIOS là hai
> khái niệm khác nhau. **Không** dùng ROM để bác bỏ spec, và **không** dùng spec để bác bỏ ROM.

## 3. POWER TOPOLOGY — GIẢI MÃ HOÀN TOÀN, VÀ GIỐNG HỆT NHAU

`nvgpu`:
```c
struct pwr_topology_2x_header { u8 version, header_size, table_entry_size,
        num_table_entries, rel_entry_size, num_rel_entries; };      /* 6 B */
struct pwr_topology_2x_entry { u8 flags0, pwr_rail; u32 param0,
        curr_corr_slope, curr_corr_offset, param1, param2; };       /* 22 B */
```
ROM slot 15: `ver=0x20, hlen=6, esz=22, cnt=20, rel=27 x 15`

```
6 + 20*22 + 15*27 = 6 + 440 + 405 = 851    (đóng chính xác, cả 3 ROM)
```

⇒ Header + entry khớp **100%** với struct nvgpu; khối `rel` (15 × 27 B) do header khai báo
nhưng nvgpu không mô tả nội dung. **PROVEN** cho cấu trúc, **UNKNOWN** cho `rel`.

20 entry: `class_id` ∈ {0, 2, 5}, `pwr_rail` ∈ {`0xdf`,`0xe2`,`0xe9`,`0xff`,`0xfa`,...},
`curr_corr_slope = 0x1000`, `curr_corr_offset = 0`, `param0 = 0x00b71b00`.

**Toàn bộ 851 byte giống nhau giữa CMP / 2060S / 2070.** ⇒ Cảm biến công suất, rail và
hệ số hiệu chỉnh dòng **không** phải nguồn gốc khác biệt hiệu năng.

Lưu ý về `class_id`: nvgpu chỉ đặt tên `CLASS_SENSOR = 1`, mà giá trị 1 **không xuất hiện**
trong bảng này ⇒ enum của nvgpu không phủ bảng của TU106. Không suy nghĩa từ tên.

---

## 4. THERMAL POLICY — CẤU TRÚC RÕ, NGHĨA CHƯA

Slot 20: `ver=0x10, hlen=10, esz=40, cnt=4` → `10 + 4*40 = 170` (đóng chính xác).
Không có struct nào trong nvgpu cho hình dạng này ⇒ field **UNKNOWN**.

Header 10 byte, phần sau `hlen` khác nhau:

| | +4 | +5 | +6 | +7 | +8 | +9 |
|---|---|---|---|---|---|---|
| CMP | **`0xFF`** | ff | ff | `C0` | `01` | `00` |
| 2060S | **`0x02`** | ff | ff | `C0` | `01` | `00` |
| 2070 | `0x02` | ff | ff | **`0x00`** | **`0x02`** | `00` |

CMP khác 2060S ở **đúng một byte**. Nếu `0x02` là index hợp lệ và `0xFF` là "không có"
(quy ước rất phổ biến trong VBIOS NVIDIA), thì CMP **tắt** một policy mà GeForce bật, trỏ
tới index 2. Đó là **HYPOTHESIS** — chưa có tên trường.

Entry 2 cũng khác: byte 0 = `0x00` (CMP) vs `0x01` (GeForce); 2070 có `0x20 0a` ở +2..+3
so với `0x60 0a` của hai card kia.

Bảng entry (CMP entry 0, 40 B):
```
01 00 20 0b 20 0b 20 0b c8 00 13 40 ff ff ff 7f 20 00 00 00 e0 ff a0 ff 88 13 ...
```
Các cặp `20 0b` = 0x0b20 = 2848, lặp 3 lần; `c8 00` = 200. Không đủ để đặt tên.
**UNKNOWN.**

---

## 5. LOW POWER GR — CẤU TRÚC RÕ, MASK CHƯA

Slot 32: `ver=0x10, hlen=10, esz=5, cnt=5` → 35 (đóng chính xác).

nvgpu: `nvgpu_bios_lpwr_gr_table_1x_header` = 7 B, entry = `u32 feature_mask` (4 B).
TU106: header 10 B, entry 5 B ⇒ **rộng hơn** ở cả hai. Chỉ bit 0 (`GR`) và bit 4 (`RPPG`)
được nvgpu đặt tên.

| entry | CMP | GeForce |
|---|---|---|
| 0 | `e7 ff ff ff 01` | `ef ff ff ff 01` |
| 1 | `e7 ff ff ff 01` | `e7 ff ff ff 01` |
| 2 | `e6 ff ff ff 00` | `e6 ff ff ff 00` |
| 3 | `e6 ff ff ff 00` | `e6 ff ff ff 00` |
| 4 | `e5 ff ff ff 00` | `e5 ff ff ff 00` |

Khác biệt duy nhất: **entry 0, bit 3** (u32 LE `0xffffffe7` vs `0xffffffef`, XOR `0x8`). tức CMP **tắt**
một feature bit mà GeForce bật. Bit 27 chưa có tên. Byte thứ 5 (0/1) chưa rõ.

Đây là dữ kiện đáng chú ý: một bit trong bảng "LOW POWER GR" (low power cho graphics) khác
nhau. **HYPOTHESIS**: có thể là một power feature (RPPG-related, hoặc clock gating) mà CMP
không dùng. Không đủ để gọi là "tắt boost".

---

## 6. POWER BASE CLOCK — ENTRY 3..16 VẪN UNKNOWN

v3 đã decode entry 0/1/2 (base/boost) với extent đóng (`19 + 17*41 = 716`). Entry 3..16
dùng cùng stride nhưng cho giá trị vô lý (`133412`).

Quan sát mới của Phase 4: **header `+9..+0x12`** khác nhau:

| | +9..+0x12 |
|---|---|
| CMP | `ff ff ff ff ff ff ff ff ff ff` (10 × ff) |
| 2060S/2070 | `03 09 ff ff ff ff ff ff ff ff` |

⇒ Hai byte đầu là một bảng con / index, không phải phần của entry. Nếu `03` và `09` là
index, chúng trỏ tới bảng khác. **UNKNOWN**, nhưng đây là manh mối rẻ tiền để thử tiếp.

---

## 7. VOLTAGE — VFE, KHÔNG PHẢI VF CURVE ĐƠN GIẢN

Slot 8 "VOLT MAPPING" ở CMP: `ver=0x30, hlen=9, esz=25, cnt=20` — **khớp
`vbios_vfe_3x_header_struct`** (9 B) và `VBIOS_VFE_3X_VAR_ENTRY_SIZE_19` (0x19 = 25 B).
Nhưng `9 + 20*25 = 509` ≠ span 5444.

⇒ Bảng VFE có cấu trúc nhiều khối (var + equ + rppm), giống POWER BUDGET. Header khai báo:

```c
struct vbios_vfe_3x_header_struct {
    u8 version, header_size, vfe_var_entry_size, vfe_var_entry_count,
       vfe_equ_entry_size, vfe_equ_entry_count, polling_periodms,
       vfe_var_rppm_entry_count, vfe_equ_rppm_entry_count;
};
```
Đọc từ ROM: `30 09 19 14 18 96 c8 0f 28` → var 25 × 20, equ `0x18`=24 × `0x96`=150,
polling `0xc8`=200, rppm `0x0f`=15, `0x28`=40.

Thử: `9 + 20*25 + 150*24 + 15*x + 40*y = 5444`? `9+500+3600 = 4109`; còn 1335.
1335 = 15*89 = 15*89. Hoặc 1335/40 = 33.4. Chưa đóng ⇒ **cần** thêm một khối.

⇒ Voltage/VF curve **chưa** giải mã được ở Phase 4. Ghi UNKNOWN, không đoán.

---

## 8. BẢNG: FIELD NÀO QUY ĐỊNH CÁI GÌ (mức bằng chứng)

| thứ cần biết | field | nguồn | mức |
|---|---|---|---|
| Power mặc định | `POWER BUDGET e2.limit_rated` | ROM + nvgpu | STRONGLY SUPPORTED |
| Power tối thiểu đặt được | `e2.limit_min` | idem | STRONGLY SUPPORTED |
| Power tối đa đặt được | `e2.limit_max` | idem | STRONGLY SUPPORTED |
| Trần xung | `PERFORMANCE v0x60` GPC `max` = 2100 MHz | nvgpu | PROVEN (giá trị) |
| Trần xung thật (boost) | `POWER BASE CLOCK e2` = 1648 MHz | envytools | STRONGLY SUPPORTED |
| Ngưỡng nhiệt | **chưa tìm được** | — | UNKNOWN |
| Giới hạn điện áp | VFE (chưa decode) | — | UNKNOWN |
| Hysteresis power | `pwr_policy` `param0..3`, `filter_param` | nvgpu có tên, ROM không xác nhận | UNKNOWN |
| Chuyển P-state | `PERFORMANCE` entry list + `initial_pstate` | nvgpu | PROVEN (cấu trúc) |
| Feature low-power bị tắt trên CMP | `LOW POWER GR e0` bit 3 (u32 LE) | ROM | HYPOTHESIS |

**Giới hạn thiết kế ≠ trạng thái hoạt động.** Bảng trên là *thiết kế*. Trạng thái phải đo:
M15 (power limit runtime), M16 (clock behaviour).

---

## 9. KẾT LUẬN

1. **Power không phải nguyên nhân.** Mặc định 184 W bằng 2060S, trần 220 W bằng nhau.
   Đây là kết quả **từ ROM**, không phải suy đoán, và nó **bác bỏ** giả thuyết "CMP bị bóp
   công suất trong VBIOS".
2. **POWER TOPOLOGY giống 100%** ⇒ cảm biến/rail/hiệu chỉnh dòng không khác.
3. **Ba khác biệt thật trong nhóm power**: `limit_min` 110 vs 125 W; THERMAL POLICY header
   `+4` `0xFF` vs `0x02`; LOW POWER GR entry 0 bit 3. Cả ba đều là **CMP tắt/nới**, không
   phải siết.
4. **Vẫn UNKNOWN**: nghĩa các byte THERMAL POLICY, bit 3 của LOW POWER GR, VFE/voltage
   curve, entry 3..16 của POWER BASE CLOCK, và `param0..3`/`filter_param` của power policy.
5. **Chưa đo gì.** M15/M16 trong `data/PHASE4_RUNTIME_MEASUREMENT_PLAN.csv` sẽ trả lời
   liệu card có chạy đúng 184 W và giữ được boost hay không.

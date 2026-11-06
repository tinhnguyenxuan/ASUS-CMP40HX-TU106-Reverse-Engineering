# VBIOS_ANALYSIS — Nhiệm vụ A

Tóm tắt. Chi tiết + bằng chứng: `EVIDENCE_LEDGER.md` E01–E06, `MASTER_REPORT.md` mục 1.

## Định danh
```
CMP40HX_ORIGINAL_1MB.bin  1,048,576 B  sha256 dc5395dd...d009dec
cmp40hx_t4.bin              495,616 B  sha256 aa0ebd6d...40cfdb
19 byte khac biet
```

## Bản đồ container (mỗi image: sum(bytes) % 256 == 0)
```
bank1                0x000000..0x0A1600   660,992 B
  legacy x86 #1      0x028600..0x037A00    62,464 B
  EFI #1             0x037A00..0x048A00    69,632 B
  NPDS 0xE0 #1       0x048A00..0x054000    46,592 B
  NPDS 0xE0 #2       0x054000..0x076800   141,312 B   <- chua VFE
  NPDS 0x70 digest   0x076800..0x078400     7,168 B
  padding FF         0x078400..0x079000     3,072 B
  NVGIf #2           0x079000..0x0A1600   165,376 B   <- bien payload
bank2                0x0A1600..0x100000   387,584 B
```

## Vùng 0x56690–0x566FF — A3
VFE table, header `30 09 19 14 18`:
- base slot `0x56699`, stride **24**, count **150**
- var base `0x564A5`, stride **25**, count **20**
- selector `0x2D384` = `00 01 03 00 02 04`

## Record chứa 6 float32 — A4
| Offset | Slot | Field | Ý nghĩa | Đơn vị |
|---|---|---|---|---|
| `0x5669C` | slot[0] | `+0x03` lo | NVVDD REL clamp dưới | µV f32 |
| `0x566A0` | slot[0] | `+0x07` hi | NVVDD REL clamp trên | µV f32 |
| `0x566A4` | slot[0] | `+0x0B` c0 | NVVDD REL hằng số | µV f32 |
| `0x566B4` | slot[1] | `+0x03` lo | NVVDD ALT clamp dưới | µV f32 |
| `0x566B8` | slot[1] | `+0x07` hi | NVVDD ALT clamp trên | µV f32 |
| `0x566BC` | slot[1] | `+0x0B` c0 | NVVDD ALT hằng số | µV f32 |

Phương trình: `y = c0 + c1·x + c2·x²`, type=1 (constant) → `y = c0`, kẹp `[lo,hi]`.
`var_idx = 10` cho cả 2 slot.

## Chứng minh là điện áp — A5
4 nguồn độc lập: IEEE-754 (`1068750.0` / `1125000.0` µV) · `nvbios` 0.1.32
(`stored_units: uV`, `equation_type: 1`, `equation_offset: 353945`) · cấu trúc
slot (`lo==hi==c0`, `c1==c2==0`) · ảnh vendor Galax HOF XOC dùng đúng
`REL = ALT = OV = 1125 mV`.

## Checksum — A6
Byte `0x767FF` = byte cuối image `NPDS 0xE0 #2` (`0x054000..0x076800`).
**Thuật toán: 8-bit additive, `sum(image) mod 256 == 0`.**
Sửa: `new_ck = (old_ck - Σ(T4-ROM)) mod 256` = `(0x33 - (-690)) mod 256` = **`0xE5`**.
Không phải chữ ký, không có thành phần mật mã.

## Payload 495,616 B — A7
`payload = rom[0 : 0x79000]`. Biên = magic **`NVGIf`** tại `0x79000`
(trùng magic `0x0`; toàn bank1 chỉ có 2 lần `NVGI`).

## Phần bị cắt — A8
`0x79000..0xA1600` = **165,376 B dữ liệu THẬT** (nonzero 70–93%), gồm
`NVGIf #2` + phần sau bank1. Cộng `bank2` 387,584 B.
Vùng `0x78400..0x79000` (3,072 B) mới là padding `0xFF`.
**Chưa xác định** `NVGIf #2` là gì (header `0x80240366` chưa decode).

## Parser + test — A9, A10
```
scripts/vbios_parser.py  -> outputs/vbios_map.json
scripts/verify_diff.py   -> outputs/vbios_diff.json
scripts/test_parser.py   -> 7/7 PASS
```

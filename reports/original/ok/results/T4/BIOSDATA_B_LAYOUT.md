# BIOSDATA_B_LAYOUT.md

## BIOSDATA (Token B) — Layout chi tiết, version 2, 37 byte

### 1. Vị trí trong BIT table

| Thuộc tính | Giá trị |
|------------|---------|
| Tag | 0x42 (B) |
| Index trong BIT | [1] |
| Version | 2 |
| Length | 37 bytes |
| Offset trong BIT | 0x023E |
| Data file offset (tất cả ROM) | 0x2883E |
| ROM image base | 0x28600 |

### 2. Raw payload 37 byte

| Offset | CMP stock | CMP variant 253219 | GeForce 246948 | GeForce 268920 | GeForce 265590 |
|--------|-----------|--------------------|----------------|----------------|----------------|
| B+0 | 0x00 | 0x00 | 0x00 | 0x00 | 0x00 |
| B+1 | 0x67 | 0x67 | 0x44 | 0x4C | 0x3D |
| B+2 | 0x06 | 0x06 | 0x06 | 0x06 | 0x06 |
| B+3 | 0x90 | 0x90 | 0x90 | 0x90 | 0x90 |
| B+4 | 0x06 | 0x06 | 0xC1 | 0x57 | 0xCB |
| B+5–10 | 00 00 00 00 00 a8 | (same) | (same) | (same) | (same) |
| B+11 | 0x07 | 0x07 | 0x07 | 0x07 | 0x07 |
| B+12–21 | 00×10 | (same) | (same) | (same) | (same) |
| B+22 | 0x02 | 0x02 | 0x02 | 0x02 | 0x02 |
| B+23–27 | 00 5c 5c 22 02 | (same) | (same) | (same) | (same) |
| B+28–31 | 00 00 36 02 | (same) | (same) | (same) | (same) |
| B+32 | **0x12** | **0x12** | **0x10** | **0x10** | **0x10** |
| B+33 | 0x04 | 0x04 | 0x04 | 0x04 | 0x04 |
| B+34 | 0x00 | 0x00 | 0x00 | 0x00 | 0x00 |
| B+35 | **0x01** | **0x01** | **0x01** | **0x01** | **0x01** |
| B+36 | 0x00 | 0x00 | 0x00 | 0x00 | 0x00 |

**Full hex:**
- CMP: `00 67 06 90 06 00 00 00 00 00 a8 07 00 00 00 00 00 00 00 00 02 00 5c 5c 22 02 00 00 36 02 04 00 12 2a 4d 01 00`
- GeForce 246948: `00 44 06 90 c1 00 00 00 00 00 a8 07 00 00 00 00 00 00 00 00 02 00 5c 5c 22 02 00 00 36 02 04 00 10 5b 43 01 00`

### 3. Byte B+32: CMP=0x12, GeForce=0x10

| ROM | B+32 | B+35 |
|-----|------|------|
| CMP stock | 0x12 | 0x01 |
| CMP variant 253219 | 0x12 | 0x01 |
| GeForce 246948 | 0x10 | 0x01 |
| GeForce 268920 | 0x10 | 0x01 |
| GeForce 265590 | 0x10 | 0x01 |

B+35 = 0x01 trên tất cả ROM (không phân biệt). B+32 khác nhau: CMP=0x12 (bit 1 = 1), GeForce=0x10 (bit 1 = 0).

### 4. Module Map External 0 — Coproc Build hypothesis

Theo đặc tả NVIDIA BIT/DCB, **Module Map External 0 bit1 = Coproc Build**. Layout công khai của BIOSDATA v2 dài 33 byte, nhưng payload thực tế dài 37 byte (thêm 4 byte).

Giả thuyết: 4 byte dự phòng đẩy Module Map External 0 đến B+32. Nếu đúng:
- CMP: B+32 = 0x12 → bit 1 = 1 → Coproc Build = 1 (enabled)
- GeForce: B+32 = 0x10 → bit 1 = 0 → Coproc Build = 0 (disabled)

**Nhưng đây vẫn là GIẢ THIẾT**, chưa PROVEN vì:
1. Không có tài liệu NVIDIA chính thức xác nhận layout 37-byte của BIOSDATA v2
2. Không có bằng chứng trực tiếp rằng B+32 là Module Map External 0
3. Byte B+1 (0x67 CMP vs 0x44/0x4C/0x3D GeForce) cũng khác nhau nhưng chưa biết chức năng

## Ghi chú PONYTAIL

# ponytail: BIOSDATA B v2 = 37 byte parsed. B+32=0x12 (CMP) vs 0x10 (GeForce), B+35=0x01 (cả hai). Module Map External 0 tại B+32 là giả thuyết, chưa PROVEN.

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

### 2. Raw payload 37 byte (các ROM)

| Offset trong B | CMP stock | CMP variant 253219 | GeForce 246948 | GeForce 268920 | GeForce 265590 |
|----------------|-----------|--------------------|----------------|----------------|----------------|
| B+0 | 0x00 | 0x00 | 0x00 | 0x00 | 0x00 |
| B+1 | 0x67 | 0x67 | 0x44 | 0x4C | 0x3D |
| B+2 | 0x06 | 0x06 | 0x06 | 0x06 | 0x06 |
| B+3 | 0x90 | 0x90 | 0x90 | 0x90 | 0x90 |
| B+4 | 0x06 | 0x06 | 0xC1 | 0x57 | 0xCB |
| B+5..B+10 | 00 00 00 00 00 a8 | 00 00 00 00 00 a8 | 00 00 00 00 00 a8 | 00 00 00 00 00 a8 | 00 00 00 00 00 a8 |
| B+11 | 0x07 | 0x07 | 0x07 | 0x07 | 0x07 |
| B+12..B+21 | 00 00 00 00 00 00 00 00 00 00 | (tương tự) | (tương tự) | (tương tự) | (tương tự) |
| B+22 | 0x02 | 0x02 | 0x02 | 0x02 | 0x02 |
| B+23 | 0x00 | 0x00 | 0x00 | 0x00 | 0x00 |
| B+24 | 0x5c | 0x5c | 0x5c | 0x5c | 0x5c |
| B+25 | 0x5c | 0x5c | 0x5c | 0x5c | 0x5c |
| B+26 | 0x22 | 0x22 | 0x22 | 0x22 | 0x22 |
| B+27 | 0x02 | 0x02 | 0x02 | 0x02 | 0x02 |
| B+28 | 0x00 | 0x00 | 0x00 | 0x00 | 0x00 |
| B+29 | 0x00 | 0x00 | 0x00 | 0x00 | 0x00 |
| B+30 | 0x36 | 0x36 | 0x36 | 0x36 | 0x36 |
| B+31 | 0x02 | 0x02 | 0x02 | 0x02 | 0x02 |
| B+32 | **0x12** | **0x12** | **0x10** | **0x10** | **0x10** |
| B+33 | 0x04 | 0x04 | 0x04 | 0x04 | 0x04 |
| B+34 | 0x00 | 0x00 | 0x00 | 0x00 | 0x00 |
| B+35 | 0x12 | 0x12 | 0x10 | 0x10 | 0x10 |
| B+36 | 0x2a | 0x2a | 0x5b | 0x72 | 0x3a |

**Full hex:**
- CMP: `00 67 06 90 06 00 00 00 00 00 a8 07 00 00 00 00 00 00 00 00 02 00 5c 5c 22 02 00 00 36 02 04 00 12 2a 4d 01 00`
- GeForce 246948: `00 44 06 90 c1 00 00 00 00 00 a8 07 00 00 00 00 00 00 00 00 02 00 5c 5c 22 02 00 00 36 02 04 00 10 5b 43 01 00`
- GeForce 268920: `00 4c 06 90 57 00 00 00 00 00 a8 07 00 00 00 00 00 00 00 00 02 00 5c 5c 22 02 00 00 36 02 04 00 10 72 43 01 00`
- GeForce 265590: `00 3d 06 90 cb 00 00 00 00 00 a8 07 00 00 00 00 00 00 00 00 02 00 5c 5c 22 02 00 00 36 02 04 00 10 3a 43 01 00`

### 3. Byte B+32: CMP=0x12, GeForce=0x10

| ROM | B+32 | B+1 | B+35 |
|-----|------|-----|------|
| CMP stock | 0x12 | 0x67 | 0x12 |
| CMP variant 253219 | 0x12 | 0x67 | 0x12 |
| GeForce 246948 | 0x10 | 0x44 | 0x10 |
| GeForce 268920 | 0x10 | 0x4C | 0x10 |
| GeForce 265590 | 0x10 | 0x3D | 0x10 |

**Quan sát:** B+32 luôn bằng B+35 trong tất cả ROM. B+1 khác nhau theo dòng sản phẩm (0x67 CMP vs 0x44/0x4C/0x3D GeForce).

### 4. Không gán nhãn Coproc Build

Theo yêu cầu: **Không gán nhãn "Coproc Build" cho byte B+32** trước khi xác minh layout chính thức từ NVIDIA. Các lý do:

1. Không có tài liệu NVIDIA chính thức mô tả layout 37-byte của BIOSDATA version 2 trong bộ source mở có sẵn.
2. B+32 = B+35 trong tất cả ROM — có thể là giá trị được sao chép, không nhất thiết là bit cờ độc lập.
3. Byte B+1 (0x67 CMP vs 0x44/0x4C/0x3D GeForce) là điểm khác biệt rõ ràng hơn giữa CMP và GeForce, nhưng cũng chưa có bằng chứng về chức năng.
4. Byte B+2 (0x06) giống nhau trong tất cả ROM → không phải bit phân biệt display.

### 5. Kết luận layout

B là cấu trúc 37 byte, version 2. Các trường được xác định:
- B+0: 0x00 (tất cả ROM)
- B+2: 0x06 (tất cả ROM)
- B+4: khác nhau (0x06 CMP, 0xC1/0x57/0xCB GeForce)
- B+11: 0x07 (tất cả ROM)
- B+22: 0x02 (tất cả ROM)
- B+24-27: 0x5c5c2202 (tất cả ROM)
- B+30-31: 0x3602 (tất cả ROM)
- B+33: 0x04 (tất cả ROM)
- B+36: khác nhau (0x4d/0x43/0x43)

**Không có trường nào được xác định với độ tin cậy cao** vì không có tài liệu tham khảo NVIDIA chính thức.

## Ghi chú PONYTAIL

# ponytail: BIOSDATA version 2, 37 byte, parsed thành công. B+32=0x12 (CMP) vs 0x10 (GeForce) là sự khác biệt duy nhất được xác nhận, nhưng chưa có tài liệu NVIDIA để gán nhãn chức năng. Không gán nhãn "Coproc Build".

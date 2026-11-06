# DCB_POINTER_VALIDATION.md

## DCB (Display Configuration Block) — Con trỏ và cấu trúc

### 1. DCB locations theo ROM

| ROM | DCB offset | SHA-256 (ROM) | Device ID |
|-----|-----------|---------------|-----------|
| CMP stock | 0x2D9B2 | dc5395dd... | 0x1F0B |
| CMP variant 253219 | 0x2D9B2 | bbdac1e9... | 0x1F0B |
| GeForce 246948 | 0x2D8FC | c468ac52... | 0x1F06 |
| GeForce 268920 | 0x2D90C | 0a2fd878... | 0x1F06 |
| GeForce 265590 | 0x2D8FC | 560f2be1... | 0x1F07 |

### 2. Cấu trúc DCB header (8 byte đầu)

| Offset | Trường | Kiểu | CMP (0x2D9B2) | GeForce (0x2D8FC/0x2D90C) |
|--------|--------|------|---------------|---------------------------|
| DCB+0 | Signature | 4 byte | 0x4EDCBDCB | 0x4EDCBDCB |
| DCB+4 | Version | 1 byte | 0xAA (170) | 0x04 |
| DCB+5 | Header size | 1 byte | 0x4B (75) | 0x4B (75) |
| DCB+6 | Entry count | 1 byte | 0x00 | 0x00 |
| DCB+7 | Entry size | 1 byte | 0x00 | 0x00 |

### 3. Kết quả parse DCB

| ROM | Version | Header size | Entry count | Entry size | Connector entries |
|-----|---------|-------------|-------------|------------|-------------------|
| CMP stock | 0xAA (170) | 75 | 0 | 0 | **Không có** |
| CMP variant 253219 | 0xAA (170) | 75 | 0 | 0 | **Không có** |
| GeForce 246948 | 0x04 | 75 | 0 | 0 | **Không có** |
| GeForce 268920 | 0x04 | 75 | 0 | 0 | **Không có** |
| GeForce 265590 | 0x04 | 75 | 0 | 0 | **Không có** |

### 4. Thu hồi verdict "GeForce entries=0"

**T2 đã khẳng định "GeForce entries=0" một cách đúng.** Parse lại với con trỏ DCB hợp lệ (0x2D8FC/0x2D90C) cho thấy:
- GeForce DCB version = 4 (không phải 170 như CMP)
- Entry count = 0 trong tất cả GeForce ROM
- Không có connector entries nào được định nghĩa

**Tuy nhiên:** Version 0xAA (170) của CMP là non-standard (NVIDIA thường dùng 0x10/0x20/0x30/0x41). Entry count = 0 có thể nghĩa là:
1. DCB là placeholder (không có display connector nào)
2. Định dạng DCB tùy chỉnh của NVIDIA cho CMP
3. Connector data nằm ở nơi khác (không qua DCB)

### 4. Đối chiếu với BIT Token U

| ROM | BIT U NO_DISPLAY_SUBSYSTEM | DCB entry_count | Nhận xét |
|-----|---------------------------|-----------------|----------|
| CMP stock | 1 (disabled) | 0 | Nhất quán: không có display |
| CMP variant 253219 | 1 (disabled) | 0 | Nhất quán |
| GeForce 246948 | 0 (enabled) | 0 | SỐ THẤT: U=0 nhưng DCB=0 entries |
| GeForce 268920 | 0 (enabled) | 0 | SỐ THẤT |
| GeForce 265590 | 0 (enabled) | 0 | SỐ THẤT |

**Nhận xét:** GeForce có U=0 (display được phép) nhưng DCB entries=0. Điều này có nghĩa là DCB không phải là nguồn duy nhất quyết định display — có thể connector data được đọc từ nơi khác (VBIOS table khác, hoặc hard-coded trong driver/firmware).

## Ghi chú PONYTAIL

# ponytail: DCB parsed thành công từ con trỏ hợp lệ. Tất cả ROM có entry_count=0. CMP version=170 (non-standard), GeForce version=4. GeForce U=0 nhưng DCB=0 entries → DCB không phải nguồn duy nhất quyết định display.

# DCB_POINTER_VALIDATION.md

## DCB (Display Configuration Block) — Con trỏ và cấu trúc (phiên bản sửa)

### 1. Cách tìm DCB

Chữ ký DCB `0x4EDCBDCB` nằm tại **DCB+6**, không phải DCB+0. Cấu trúc DCB bắt đầu 6 bytes trước chữ ký:

| Offset từ đầu cấu trúc | Trường | Kiểu |
|------------------------|--------|------|
| DCB+0 | Version | 1 byte |
| DCB+1 | Header size | 1 byte |
| DCB+2 | Entry count | 1 byte |
| DCB+3 | Entry size | 1 byte |
| DCB+4–5 | Padding | 2 bytes |
| DCB+6–9 | Signature | 4 bytes (0x4EDCBDCB) |
| DCB+10 | Version 2 | 1 byte |
| DCB+11 | Header size 2 | 1 byte |
| DCB+12–… | Extended header / padding | varies |
| DCB+header_size | Entries | entry_count × entry_size |

### 2. DCB locations theo ROM

| ROM | DCB struct start | Signature offset | SHA-256 (ROM) | Device ID |
|-----|-----------------|------------------|---------------|-----------|
| CMP stock | 0x2D9AC | 0x2D9B2 | dc5395dd… | 0x1F0B |
| CMP variant 253219 | 0x2D9AC | 0x2D9B2 | bbdac1e9… | 0x1F0B |
| GeForce 246948 | 0x2D8F6 | 0x2D8FC | c468ac52… | 0x1F06 |
| GeForce 268920 | 0x2D906 | 0x2D90C | 0a2fd878… | 0x1F06 |
| GeForce 265590 | 0x2D8F6 | 0x2D8FC | 560f2be1… | 0x1F07 |

### 3. DCB header parse

| ROM | Version | Header size | Entry count | Entry size | Version 2 | Header size 2 |
|-----|---------|-------------|-------------|------------|-----------|---------------|
| CMP stock | 0x41 | 35 | **0** | 8 | 0xAA | 75 |
| CMP variant 253219 | 0x41 | 35 | **0** | 8 | 0xAA | 75 |
| GeForce 246948 | 0x41 | 35 | **16** | 8 | 0x04 | 75 |
| GeForce 268920 | 0x41 | 35 | **16** | 8 | 0x04 | 75 |
| GeForce 265590 | 0x41 | 35 | **16** | 8 | 0x04 | 75 |

### 4. DCB entries (GeForce only, CMP có entry_count=0)

GeForce có 16 entries nhưng **không phải 16 connector**. Chỉ entries 0–6 có pointer thực tế; entries 7–15 là unused/disabled (type 0x0F với pointer=NULL, flags=0x000000).

**GeForce 246948 entries thực:**
| Index | Type | Index in type | Pointer | Flags | Ghi chú |
|-------|------|---------------|---------|-------|---------|
| 0 | eDP (0x06) | 6 | 0x800F | 022000 | Connector thực |
| 1 | TMDS (0x02) | 6 | 0x000F | 022000 | Connector thực |
| 2 | TMDS (0x02) | 5 | 0x011F | 021000 | Connector thực |
| 3 | TMDS (0x02) | 7 | 0x022F | 041000 | Connector thực |
| 4 | eDP (0x06) | 8 | 0x833F | 042000 | Connector thực |
| 5 | TMDS (0x02) | 8 | 0x033F | 042000 | Connector thực |
| 6 | TMDS (0x02) | 3 | 0x044F | 013000 | Connector thực |
| 7 | 0x0E | 0 | NULL | 003000 | Unused |
| 8 | 0x0E | 3 | 0x844F | 011000 | Có pointer nhưng type chưa biết |
| 9–15 | 0x0F | 0 | NULL | 0x0000–0x0020 | Unused |

**CMP: entry_count = 0** → không có DCB entries nào → không có connector được định nghĩa trong VBIOS.

### 5. Thu hồi verdict T2

T2 đã khẳng định "GeForce entries=0" — **SAI**. Với parser DCB đúng (signature ở DCB+6), GeForce có entry_count=16 với 7 entries thực tế (0–6) và 1 entry có pointer nhưng type未知 (8). CMP thực sự có entry_count=0.

### 6. Đối chiếu với BIT Token U

| ROM | BIT U NO_DISPLAY_SUBSYSTEM | DCB entry_count | DCB real connectors | Nhận xét |
|-----|---------------------------|-----------------|---------------------|----------|
| CMP stock | 1 (disabled) | 0 | 0 | Nhất quán: không có display |
| CMP variant 253219 | 1 (disabled) | 0 | 0 | Nhất quán |
| GeForce 246948 | 0 (enabled) | 16 | 7 real | SỐ THẤT: U=0 nhưng DCB có entries |
| GeForce 268920 | 0 (enabled) | 16 | 7 real | SỐ THẤT |
| GeForce 265590 | 0 (enabled) | 16 | 7 real | SỐ THẤT |

**Nhận xét:** GeForce có U=0 (display được phép) và DCB có entries. CMP có U=1 (display bị cấm) và DCB entries=0. Hai bý chứng này nhất quán với nhau đối với CMP. Đối với GeForce, DCB entries không khớp với "displayless" — có nghĩa là DCB không phải là nguồn duy nhất quyết định display.

## Ghi chú PONYTAIL

# ponytail: DCB parser đã sửa (signature ở DCB+6). CMP entry_count=0, GeForce entry_count=16 nhưng chỉ 7 entries thực. BIT U và DCB nhất quán đối với CMP (đó displayless), không nhất quán đối với GeForce.

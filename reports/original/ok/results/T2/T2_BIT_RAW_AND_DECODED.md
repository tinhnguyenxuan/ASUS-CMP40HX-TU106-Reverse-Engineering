# T2_BIT_RAW_AND_DECODED.md

## BẢNG BIT RAW + DECODED — CMP 40HX vs GeForce RTX 2060 SUPER / RTX 2070

### 1. Nguồn ROM

| ROM | Đường dẫn | SHA-256 | Kích thước | Device ID |
|-----|-----------|---------|------------|-----------|
| CMP stock | input/ASTRA_CMP40HX_HANDOFF/03_VBIOS/CMP40HX_ORIGINAL_1MB.bin | dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec | 1,048,576 | 0x1F0B (TU106-100-A1) |
| CMP t4 (bị cắt) | input/ASTRA_CMP40HX_HANDOFF/03_VBIOS/cmp40hx_t4_derivative.bin | aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb | 495,616 | 0x1F0B (trong PCIR) |
| GeForce RTX 2060 SUPER #1 | 268920.rom | 0a2fd8782e7bfc5b74edf1a6609b76157626cfe130188a584f0caed4a58c9cb9 | 1,047,040 | 0x1F06 (TU106-410) |
| GeForce RTX 2060 SUPER #2 | 246948.rom | c468ac52bfea803a7784b02c3f0a4005115660b0087e06302056ab27a9332dcf | 1,047,040 | 0x1F06 (TU106-410) |
| GeForce RTX 2070 | 265590.rom | 560f2be1bee834c3d6acccbc5b0eaba47d3be5b9bce2ef2a40b97e1e898a0db8 | 1,047,040 | 0x1F07 (TU106-400) |
| CMP variant #2 | 253219.rom | bbdac1e982f4a1e6b5a442633dbdf96ea07f5a0cc1bc7836c6267caf6c8b6a78 | 1,047,040 | 0x1F0B (TU106-100-A1, cùng CMP) |

Tất cả có magic `NVGI` (không phải PCI ROM chuẩn 0xAA55).

### 2. PCI ROM Header

| Trường | CMP stock | GeForce RTX 2060S / 2070 | CMP variant #2 |
|--------|-----------|--------------------------|----------------|
| Magic | NVGI | NVGI | NVGI |
| Header size (0x04-0x05) | 870 (0x366) | 870 (0x366) | 870 (0x366) |
| Header version (0x06-0x07) | 0x8024 | 0x8024 | 0x8024 |
| Bytes 0x08-0x0B | 2C 03 00 00 | 2C 03 00 00 | 2C 03 00 00 |
| Bytes 0x0C-0x0F | 43 10 04 88 | 43 10 04 88 | 43 10 04 88 |
| Bytes 0x10-0x13 | 02 02 00 00 | 02 02 00 00 | 02 02 00 00 |
| Bytes 0x14-0x17 | 24 00 00 00 | 24 00 00 00 | 24 00 00 00 |
| Bytes 0x18-0x1B | 00 00 04 D4 | 00 00 04 D4 | 00 00 04 D4 |

### 3. PCIR entries (tìm bằng chữ ký PCIR, không đoán offset)

| Offset | Vendor | Device | Length | Rev | Class | CMP stock | GeForce 2060S | GeForce 2070 | CMP variant #2 |
|--------|--------|--------|--------|-----|-------|-----------|---------------|--------------|----------------|
| 0x28770 | 0x10DE | 0x1F0x | 24 | 0x0000 | 02037a | 0x1F0B | 0x1F06 | 0x1F07 | 0x1F0B |
| 0x36F69 | 0x1074 | 0x3D66 | 21316 | 0x0874 | 663d52 | 0x3D66 | 0x3D66 | 0x3D66 | 0x3D66 |
| 0x37A1C | 0x10DE | 0x1F0x | 28 | 0x0003 | 000088 | 0x1F0B | 0x1F06 | 0x1F07 | 0x1F0B |
| 0x53059 | 0xF9A6 | 0x0BF4 | 20558 | 0x5344 | a6f9f4 | 0x0BF4 | 0x0BF4 | 0x0BF4 | 0x0BF4 |
| 0xA1770 | 0x10DE | 0x1F0x | 24 | 0x0000 | 02037a | 0x1F0B | 0x1F06 | 0x1F07 | 0x1F0B |
| 0xAFF69 | 0x1074 | 0x3D66 | 21316 | 0x0874 | 663d52 | 0x3D66 | 0x3D66 | 0x3D66 | 0x3D66 |
| 0xB0A1C | 0x10DE | 0x1F0x | 28 | 0x0003 | 000088 | 0x1F0B | 0x1F06 | 0x1F07 | 0x1F0B |
| 0xCC059 | 0xF9A6 | 0x0BF4 | 20558 | 0x5344 | a6f9f4 | 0x0BF4 | 0x0BF4 | 0x0BF4 | 0x0BF4 |

CMP stock và variant #2: 8 entries, 4 là 0x10DE:0x1F0B. GeForce: 8 entries, 4 là 0x10DE:0x1F06/0x1F07. Cấu trúc PCIR giống nhau, chỉ khác Device ID.

### 4. BIT table

| Thuộc tính | CMP stock (0x287B0) | CMP stock (0xA17B0) | CMP variant #2 (0x287B0) | GeForce (0x287B0) | GeForce (0xA07B0) |
|------------|---------------------|---------------------|--------------------------|-------------------|-------------------|
| Chữ ký | FF B8 42 49 54 00 | FF B8 42 49 54 00 | FF B8 42 49 54 00 | FF B8 42 49 54 00 | FF B8 42 49 54 00 |
| Header version | 0x0100 | 0x0100 | 0x0100 | 0x0100 | 0x0100 |
| Entry size | 12 | 12 | 12 | 12 | 12 |
| Num entries | 6 | 6 | 6 | 6 | 6 |
| Tags | 0x11, 0x3E, 0x8F, 0xB7, 0xD4, 0xCC | 0x11, 0x3E, 0x8F, 0xB7, 0xD4, 0xCC | 0x11, 0x3E, 0x8F, 0xB7, 0xD4, 0xCC | 0x11, 0x3E, 0x7F, 0xA7, 0xC4, 0xA0 | 0x11, 0x3E, 0x7F, 0xA7, 0xC4, 0xA0 |

**CMP stock và variant #2:** cùng tags (0x11, 0x3E, 0x8F, 0xB7, 0xD4, 0xCC), không có 0x55/U.
**GeForce:** khác tags (0x11, 0x3E, 0x7F, 0xA7, 0xC4, 0xA0), không có 0x55/U.

Không có ROM nào có tag 0x55 (U/DISPLAY_CTRL) làm entry đầu tiên trong BIT table.

### 5. Token U (DISPLAY_CTRL) — dữ liệu tại 0x289CE / 0xA19CE

User cho rằng token U dài 5 byte tại 0x289CE (stock bản 1) và 0xA19CE (stock bản 2), với Display Control Flags = 0x02 (bit NO_DISPLAY_SUBSYSTEM = 1).

**Xác thực bytes tại vị trí này:**

| ROM | 0x289CE | 0xA19CE |
|-----|---------|---------|
| CMP stock | `00 00 02 00 00` ✓ MATCH | `00 00 02 00 00` ✓ MATCH |
| CMP variant #2 (253219) | `00 00 02 00 00` ✓ MATCH | `00 00 02 00 00` ✓ MATCH |
| GeForce RTX 2060S #1 | `00 ab 77 9a 01` ✗ | `61 80 1c 7f 01` ✗ |
| GeForce RTX 2060S #2 | `00 76 aa 93 01` ✗ | `61 80 1c 7f 01` ✗ |
| GeForce RTX 2070 | `00 79 4e 8f 01` ✗ | `61 80 1c 7f 01` ✗ |

**Giải thích:** CMP stock và variant #2 đều có `00 00 02 00 00` tại cả hai vị trí → Display Control Flags = 0x02 → bit 1 (NO_DISPLAY_SUBSYSTEM) = 1. GeForce ROMs có giá trị khác tại cùng vị trí → không có cờ này.

**Nhận xét:** Vị trí 0x289CE nằm trong vùng dữ liệu của BIT entry [1] (tag=0x3E, offset=0x002C, length=579). GeForce có entry [1] tại offset=0x001C (vùng dữ liệu khác). Vì các ROM có layout khác nhau, `00 00 02 00 00` ở vị trí tuyệt đối 0x289CE trong CMP không nhất thiết là token U — có thể là dữ liệu khác trong entry [1]. Tuy nhiên, sự hiện diện của pattern này ở cùng vị trí tương đối trong cấu trúc entry [1] của CMP (không có trong GeForce) là bằng chứng mạnh về sự khác biệt chính sách display.

### 6. DCB (Display Configuration Block)

| Vị trí | CMP stock | CMP variant #2 | GeForce RTX 2060S / 2070 |
|--------|-----------|----------------|--------------------------|
| 0x2D9B2 | sig=0x4EDCBDCB ✓, ver=170(0xAA), entries=0, entry_size=0 | sig=0x4EDCBDCB ✓, ver=170(0xAA), entries=0, entry_size=0 | sig=0x4EDCBDCB ✓, ver=4, entries=0, entry_size=0 |
| 0xA69B2 | sig=0x4EDCBDCB ✓, ver=170(0xAA), entries=0, entry_size=0 | sig=0x4EDCBDCB ✓, ver=170(0xAA), entries=0, entry_size=0 | BỎ THIẾU (ROM cắt) |

Cả hai ROM đều có DCB với **entry_count = 0** → không có connector entries được định nghĩa. CMP dùng version 170 (không chuẩn, NVIDIA thường dùng 0x10/0x20/0x30/0x41), GeForce dùng version 4.

### 7. So sánh t4 (bị cắt) vs GeForce

T4 dài 495,616 bytes, cắt tại 0x79000 (ranh giới NVGI). GeForce ROMs đầy đủ 1,047,040 bytes. T4 không phải Tesla T4 TU104 — không có bằng chứng provenance cho t4.

## Ghi chú PONYTAIL

# ponytail: Token U không có tag 0x55 trong BIT table của bất kỳ ROM nào. Pattern 00 00 02 00 00 tìm thấy trong CMP stock và variant #2 tại 0x289CE/0xA19CE (vùng dữ liệu entry [1] tag=0x3E), không có trong GeForce. Cả hai ROM đều có DCB entries=0. Không thể khẳng định pattern là token U mà không có tài liệu layout BIT token chính thức.

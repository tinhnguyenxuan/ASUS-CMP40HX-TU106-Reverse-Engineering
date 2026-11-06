# T2_EVIDENCE_LEDGER.md

## EVIDENCE LEDGER — T2 INDEPENDENT TU106 DISPLAY POLICY INVESTIGATION

### 1. File ROM được phân tích

| # | File | SHA-256 | Kích thước | Device ID | Nguồn |
|---|------|---------|------------|-----------|-------|
| 1 | CMP40HX_ORIGINAL_1MB.bin | dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec | 1,048,576 | 0x1F0B | ASTRA_CMP40HX_HANDOFF |
| 2 | cmp40hx_t4_derivative.bin | aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb | 495,616 | 0x1F0B (PCIR) | ASTRA_CMP40HX_HANDOFF (bị cắt) |
| 3 | 268920.rom | 0a2fd8782e7bfc5b74edf1a6609b76157626cfe130188a584f0caed4a58c9cb9 | 1,047,040 | 0x1F06 | User-supplied (GeForce RTX 2060 SUPER) |
| 4 | 246948.rom | c468ac52bfea803a7784b02c3f0a4005115660b0087e06302056ab27a9332dcf | 1,047,040 | 0x1F06 | User-supplied (GeForce RTX 2060 SUPER) |
| 5 | 265590.rom | 560f2be1bee834c3d6acccbc5b0eaba47d3be5b9bce2ef2a40b97e1e898a0db8 | 1,047,040 | 0x1F07 | User-supplied (GeForce RTX 2070) |
| 6 | 253219.rom | bbdac1e982f4a1e6b5a442633dbdf96ea07f5a0cc1bc7836c6267caf6c8b6a78 | 1,047,040 | 0x1F0B | User-supplied (CMP 40HX variant, cùng Device ID với CMP stock) |

### 2. BIT table comparison

| ROM | BIT locations | Tags | Token U (0x55) | DCB version | DCB entries |
|-----|--------------|------|----------------|-------------|-------------|
| CMP stock | 0x287B0, 0xA17B0 | 0x11, 0x3E, 0x8F, 0xB7, 0xD4, 0xCC | Không có tag | 170 (0xAA) | 0 |
| CMP variant #2 (253219) | 0x287B0, 0xA17B0 | 0x11, 0x3E, 0x8F, 0xB7, 0xD4, 0xCC | Không có tag | 170 (0xAA) | 0 |
| GeForce 2060S #1 | 0x287B0, 0xA07B0 | 0x11, 0x3E, 0x7F, 0xA7, 0xC4, 0xA0 | Không có tag | 4 | 0 |
| GeForce 2060S #2 | 0x287B0, 0xA07B0 | 0x11, 0x3E, 0x7F, 0xA7, 0xC4, 0xA0 | Không có tag | 4 | 0 |
| GeForce 2070 | 0x287B0, 0xA07B0 | 0x11, 0x3E, 0x7F, 0xA7, 0xC4, 0xA0 | Không có tag | 4 | 0 |

### 3. Token U data comparison (0x289CE / 0xA19CE)

| ROM | 0x289CE | 0xA19CE | NO_DISPLAY_SUBSYSTEM |
|-----|---------|---------|----------------------|
| CMP stock | 00 00 02 00 00 | 00 00 02 00 00 | Flags=0x02, bit1=1 ✓ |
| CMP variant #2 (253219) | 00 00 02 00 00 | 00 00 02 00 00 | Flags=0x02, bit1=1 ✓ |
| GeForce 2060S #1 | 00 ab 77 9a 01 | 61 80 1c 7f 01 | Không có |
| GeForce 2060S #2 | 00 76 aa 93 01 | 61 80 1c 7f 01 | Không có |
| GeForce 2070 | 00 79 4e 8f 01 | 61 80 1c 7f 01 | Không có |

### 4. Driver/GSP call graph evidence

| Evidence | File | Dòng | Nội dung |
|----------|------|------|----------|
| TU106 uses GM107 fuse display HAL | g_gpu_nvoc.c | 2097-2100 | ChipHal TU102|TU104|TU106|TU116|TU117 → gpuFuseSupportsDisplay_GM107 |
| Fuse read implementation | kern_gpu_gm107.c | 64-72 | Reads NV_FUSE_STATUS_OPT_DISPLAY (0x21C04), tests DATA==ENABLE |
| Display init gate | kern_disp.c | 444 | `if (!gpuFuseSupportsDisplay_HAL(pGpu)) return NV_ERR_NOT_SUPPORTED;` |
| GSP VGA workspace gate | kernel_gsp_tu102.c | 1361 | `if (gpuFuseSupportsDisplay_HAL(pGpu) && ...)` |
| KernelDisplay NULL check | disp_objs.c | 95 | `if (pKernelDisplay == NULL) return NV_ERR_NOT_SUPPORTED;` |
| GridDisplayless mutual exclusion | gpu.c | 1945 | Classes DISPLAY_COMMON and NVA083_GRID_DISPLAYLESS mutually exclusive |
| TU106 has both children | kern_gpu_tu102.c | 195-208 | Both KernelDisplay and OBJGRIDDISPLAYLESS present |

### 5. Fuse definition gap

| Fuse | Định nghĩa trong tu102/dev_fuse.h? | Định nghĩa trong gm107/dev_fuse.h? | Live read trên TU106 |
|------|-------------------------------------|-------------------------------------|----------------------|
| 0x21C04 (OPT_DISPLAY) | KHÔNG | CÓ (0x00021C04) | 0x00000001 |
| 0x2174C (SECURE_GSP_DEBUG_DIS) | CÓ | Không | 0x00000001 |
| 0x21378 (NVDEC_DISABLE) | CÓ | Không | 0x00000000 |
| 0x0524 | KHÔNG | KHÔNG | 0x00000000 |

### 6. Test đã thực hiện (read-only, không flash/ghi MMIO)

| Test | Kết quả |
|------|---------|
| Parse BIT table từ 6 ROM | Thành công, 6 entries mỗi BIT |
| Parse DCB từ 6 ROM | Thành công, entries=0 cả hai |
| So sánh bytes 0x289CE/0xA19CE | CMP stock + variant #2 có pattern, GeForce không |
| Tra cứu driver source 615.78.08 | Tìm được 2 consumer của gpuFuseSupportsDisplay_HAL |
| Tra cứu fuse definitions | 0x21C04 không có trong tu102/dev_fuse.h |
| dmesg firmware log | SEC2 được nhắc đến, GSP UNTOUCHED |
| cmpunlocker compute unlock | Hoạt động (SS0/SS1), không ảnh hưởng display/fuse |

### 7. Không được phép (theo ràng buộc)

- ❌ Flash VBIOS
- ❌ Ghi MMIO
- ❌ Chỉnh strap
- ❌ Ghi fuse/OTP/RIR
- ❌ Reset GPU
- ❌ Reverse Falcon SEC2 (trừ khi có liên hệ trực tiếp với đường quyết định display)

## Ghi chú PONYTAIL

# ponytail: Tất cả bằng chứng được thu thập read-only. 5 file đã ghi vào results/T2/. Không có hành vi ghi nào được thực hiện.

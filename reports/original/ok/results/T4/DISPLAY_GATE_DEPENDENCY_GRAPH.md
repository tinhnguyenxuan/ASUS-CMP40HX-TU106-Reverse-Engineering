# DISPLAY_GATE_DEPENDENCY_GRAPH.md

## Đồ thị phụ thuộc gate display — Driver/GSP 615.78.08

### 1. Consumer của gpuFuseSupportsDisplay_HAL

| # | File | Dòng | Mã | Hiệu ứng |
|---|------|------|-----|----------|
| 1 | src/nvidia/src/kernel/gpu/disp/kern_disp.c | 444 | `if (!gpuFuseSupportsDisplay_HAL(pGpu)) return NV_ERR_NOT_SUPPORTED;` | Chặn khởi tạo display nếu fuse DATA ≠ ENABLE |
| 2 | src/nvidia/src/kernel/gpu/gsp/arch/turing/kernel_gsp_tu102.c | 651 | `if (gpuFuseSupportsDisplay_HAL(pGpu) && kdispGetVgaWorkspaceBase(...))` | Chỉ tính VGA workspace layout khi fuse enable |

### 2. Consumer của KernelDisplay presence

| # | File | Dòng | Mã | Hiệu ứng |
|---|------|------|-----|----------|
| 3 | src/nvidia/src/kernel/gpu/disp/disp_objs.c | 95 | `if (pKernelDisplay == NULL) return NV_ERR_NOT_SUPPORTED;` | Chặn display API nếu KernelDisplay không tồn tại |
| 4 | src/nvidia/src/kernel/gpu/gpu.c | 1945 | `Classes DISPLAY_COMMON and NVA083_GRID_DISPLAYLESS mutually exclusive` | KernelDisplay và GridDisplayless loại trừ nhau |

### 3. Consumer của BIT Token U (0x55)

| # | File | Dòng | Mã | Hiệu ứng |
|---|------|------|-----|----------|
| — | — | — | **Không tìm thấy** | Không có mã driver/GSP trong source 615.78.08 đọc trực tiếp BIT token U từ VBIOS |

### 4. Consumer của BIOSDATA B (0x42)

| # | File | Dòng | Mã | Hiệu ứng |
|---|------|------|-----|----------|
| — | — | — | **Không tìm thấy** | Không có mã driver/GSP trong source 615.78.08 đọc trực tiếp BIOSDATA B từ VBIOS |

### 5. Đồ thị phụ thuộc

```
┌─────────────────────────────────────────────────────────────────┐
│  GATE 1: Fuse 0x21C04 (gpuFuseSupportsDisplay_HAL)              │
│  ├─ Loại: Độc lập (đọc trực tiếp thanh ghi fuse qua MMIO)       │
│  ├─ Consumer: kern_disp.c:444, kernel_gsp_tu102.c:651           │
│  ├─ Nếu DATA ≠ ENABLE(0): display init bị chặn                  │
│  └─ Live read: 0x00000001 → GATE FALSE                          │
├─────────────────────────────────────────────────────────────────┤
│  GATE 2: KernelDisplay != NULL                                   │
│  ├─ Loại: Phụ thuộc GATE 1                                       │
│  ├─ Consumer: disp_objs.c:95                                     │
│  ├─ Nếu GATE 1 FALSE → display không init → KernelDisplay NULL   │
│  └─ Live state: Display Attached = No, Display Active = Disabled │
├─────────────────────────────────────────────────────────────────┤
│  GATE 3: BIT Token U (NO_DISPLAY_SUBSYSTEM)                      │
│  ├─ Loại: UNKNOWN (không có consumer kernel)                     │
│  ├─ Nguồn: VBIOS data, có thể được đọc bởi userspace driver      │
│  └─ Giá trị: CMP=1 (disabled), GeForce=0 (enabled)               │
├─────────────────────────────────────────────────────────────────┤
│  GATE 4: BIOSDATA B (Coproc Build hypothesis at B+32)            │
│  ├─ Loại: UNKNOWN (giả thuyết, chưa PROVEN)                      │
│  ├─ Nguồn: VBIOS data                                            │
│  └─ Giá trị: CMP=0x12 (bit1=1), GeForce=0x10 (bit1=0)           │
└─────────────────────────────────────────────────────────────────┘
```

### 6. Direct host consumer vs firmware consumer

| Consumer | Loại | File | Dòng | Sử dụng fuse 0x21C04? |
|----------|------|------|------|----------------------|
| kern_disp.c display init | Direct host | kern_disp.c | 444 | Có (qua gpuFuseSupportsDisplay_HAL) |
| kernel_gsp_tu102.c VGA workspace | Firmware-adjacent | kernel_gsp_tu102.c | 651 | Có (qua gpuFuseSupportsDisplay_HAL) |
| GSP firmware | Firmware | gsp_tu10x.bin | — | Không rõ (GSP UNTOUCHED per dmesg) |
| BIT Token U consumer | Unknown | — | — | Không tìm thấy trong kernel source |

### 7. Nguồn giá trị ban đầu của 0x21C04

| Nguồn | Bý chứng | Kết luận |
|-------|----------|----------|
| Raw OTP | Không có mã nạp OTP vào thanh ghi | UNKNOWN |
| Shadow/latch | Không có mã ghi vào 0x21C04 | UNKNOWN |
| Firmware (SEC2/GSP) | GSP UNTOUCHED per dmesg | UNKNOWN |
| VBIOS configuration | Không có mã driver đọc VBIOS fuse | UNKNOWN |

### 8. Dữ liệu chưa biết (UNKNOWN)

1. **BIT Token U consumer:** Không có mã kernel đọc token U từ VBIOS. Có thể được đọc bởi userspace NVIDIA driver (không có trong kernel module source).
2. **BIOSDATA B consumer:** Không có mã kernel đọc BIOSDATA B từ VBIOS.
3. **Fuse 0x21C04 nguồn:** OTP vs shadow vs firmware chưa xác định.
4. **GSP RmDisableDisplay:** Không tìm thấy trong kernel source. Có thể nằm trong GSP firmware (không có source).
5. **Module Map External 0 tại B+32:** Giả thuyết, chưa có tài liệu NVIDIA xác nhận.

## Ghi chú PONYTAIL

# ponytail: 4 gate xác định. GATE 1 (fuse 0x21C04) độc lập và FALSE. GATE 2 phụ thuộc GATE 1. GATE 3 (BIT U) và GATE 4 (BIOSDATA B) không có consumer kernel. Nguồn 0x21C04 là UNKNOWN.

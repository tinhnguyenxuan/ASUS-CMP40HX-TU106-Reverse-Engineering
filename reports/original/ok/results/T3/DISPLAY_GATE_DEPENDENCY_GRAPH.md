# DISPLAY_GATE_DEPENDENCY_GRAPH.md

## Đồ thị phụ thuộc gate display — Driver/GSP 615.78.08

### 1. Consumer của gpuFuseSupportsDisplay_HAL

| # | File | Dòng | Mã | Hiệu ứng |
|---|------|------|-----|----------|
| 1 | src/nvidia/src/kernel/gpu/disp/kern_disp.c | 444 | `if (!gpuFuseSupportsDisplay_HAL(pGpu)) return NV_ERR_NOT_SUPPORTED;` | Chặn khởi tạo display nếu fuse DATA ≠ ENABLE |
| 2 | src/nvidia/src/kernel/gpu/gsp/arch/turing/kernel_gsp_tu102.c | 1361 | `if (gpuFuseSupportsDisplay_HAL(pGpu) && kdispGetVgaWorkspaceBase(...))` | Chỉ tính VGA workspace layout khi fuse enable |

### 2. Consumer của KernelDisplay presence

| # | File | Dòng | Mã | Hiệu ứng |
|---|------|------|-----|----------|
| 3 | src/nvidia/src/kernel/gpu/disp/disp_objs.c | 95 | `if (pKernelDisplay == NULL) return NV_ERR_NOT_SUPPORTED;` | Chặn display API nếu KernelDisplay không tồn tại |
| 4 | src/nvidia/src/kernel/gpu/gpu.c | 1945 | `Classes DISPLAY_COMMON and NVA083_GRID_DISPLAYLESS mutually exclusive` | KernelDisplay và GridDisplayless loại trừ nhau |

### 3. Consumer của BIT Token U (0x55)

| # | File | Dòng | Mã | Hiệu ứng |
|---|------|------|-----|----------|
| — | — | — | **Không tìm thấy** | Không có mã driver/GSP trong source 615.78.08 đọc trực tiếp BIT token U từ VBIOS |

### 4. Phân loại gate

```
┌─────────────────────────────────────────────────────────────┐
│  GATE 1: Fuse 0x21C04 (gpuFuseSupportsDisplay_HAL)          │
│  ├─ Độc lập: đọc trực tiếp thanh registros fuse              │
│  ├─ Consumer: kern_disp.c:444, kernel_gsp_tu102.c:1361       │
│  ├─ Nếu DATA ≠ ENABLE(0): display init bị chặn               │
│  └─ Live read: 0x00000001 → GATE FALSE                       │
├─────────────────────────────────────────────────────────────┤
│  GATE 2: KernelDisplay != NULL                                │
│  ├─ Phụ thuộc GATE 1 (nếu GATE 1 FALSE, KernelDisplay          │
│  │   có thể không được init)                                  │
│  ├─ Consumer: disp_objs.c:95                                 │
│  ├─ Nếu NULL: display API trả về NOT_SUPPORTED               │
│  └─ Live state: Display Attached = No, Display Active = Disabled│
├─────────────────────────────────────────────────────────────┤
│  GATE 3: BIT Token U (NO_DISPLAY_SUBSYSTEM)                   │
│  ├─ **Không có consumer** trong kernel source 615.78.08       │
│  ├─ Có trong VBIOS (CMP: 1, GeForce: 0)                       │
│  ├─ Có thể được đọc bởi userspace (nvidia-settings, X driver) │
│  └─ Trạng thái kernel: UNKNOWN                                │
└─────────────────────────────────────────────────────────────┘
```

### 5. Gate độc lập vs phụ thuộc nhau

| Gate | Độc lập? | Phụ thuộc vào gate nào? | Bý chứng |
|------|----------|------------------------|----------|
| GATE 1 (Fuse 0x21C04) | Có | Không | Kern_disp.c:444 đọc trực tiếp fuse |
| GATE 2 (KernelDisplay) | Không | GATE 1 | Nếu fuse disable, display không init → KernelDisplay có thể NULL |
| GATE 3 (BIT Token U) | UNKNOWN | UNKNOWN | Không tìm thấy consumer trong kernel source |

### 6. Dữ liệu chưa biết (UNKNOWN)

1. **BIT Token U consumer:** Không có mã kernel đọc token U từ VBIOS. Có thể được đọc bởi userspace NVIDIA driver (không có trong kernel module source).
2. **Fuse 0x21C04 nguồn:** OTP vs shadow vs firmware chưa xác định (xem DISPLAY_FUSE_PROVENANCE.md).
3. **GSP RmDisableDisplay:** Không tìm thấy mã trong kernel source 615.78.08. Có thể nằm trong GSP firmware (không có source).
4. **DCB consumer:** Không có mã kernel parse DCB từ VBIOS image.

## Ghi chú PONYTAIL

# ponytail: 3 gate xác định. GATE 1 (fuse 0x21C04) độc lập và FALSE. GATE 2 (KernelDisplay) phụ thuộc GATE 1. GATE 3 (BIT U) không có consumer kernel. Tất cả kết luận dựa trên source 615.78.08 đọc được.

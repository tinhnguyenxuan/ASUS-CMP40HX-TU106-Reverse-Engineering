# P8 — TRUST BOUNDARIES

Prompt mục 11 yêu cầu phân tích riêng. Nội dung dựa trên dữ liệu **đo được** từ
`SECURITY/p8_wpr.json` và `SECURITY/security_registers.json`.

---

## 1. Các tầng thực thi trên GPU

```
┌─────────────────────────────────────────────────────────────┐
│ HOST (Linux kernel, Secure Boot TẮT)                        │
│   driver nvidia.ko — KHÔNG có chữ ký hợp lệ                  │
├─────────────────────────────────────────────────────────────┤
│ GSP-RM (RISC-V, trong WPR2)                                 │
│   22.9 MB, entry 0x4009000, base 0x4000000                   │
├─────────────────────────────────────────────────────────────┤
│ FWSEC (Falcon secure) — boot stage 1                        │
├─────────────────────────────────────────────────────────────┤
│ SEC2 (Falcon) — chạy exploit sequence, sau đó DMEM = 0       │
├─────────────────────────────────────────────────────────────┤
│ NVUCODES (11 blob, 6 plaintext + 4 mã hoá + 1 hỗn hợp)        │
├─────────────────────────────────────────────────────────────┤
│ VBIOS shadow (BAR0 0x300000, 1 MB)                          │
├─────────────────────────────────────────────────────────────┤
│ SILICON (TU106, 17 TPC, 34 SM, 2176 CUDA)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Điểm tiếp giáp và trạng thái bảo vệ

### 2.1 HOST ↔ DRIVER

| Thuộc tính | Giá trị | Trạng thái |
|---|---|---|
| Secure Boot | **TẮT** | driver nạp được dù không có chữ ký |
| Module verification | `signature and/or required key missing` | kernel **taint** |
| CA đáng tin | Canonical Ltd. Secure Boot Signing (Ubuntu Core 2019) | driver không nằm trong danh sách |

**Nhận xét:** toàn bộ vùng nhở giữa driver Linux và GPU **không được xác thực ở
tầng host**. Đây là điểm tiếp giáp **yếu nhất** trong kiến trúc — driver có toàn
quyền ghi BAR0/BAR1.

### 2.2 DRIVER ↔ GSP-RM

| Cơ chế | Trạng thái |
|---|---|
| `NVreg_RegistryDwords` → `PACKED_REGISTRY_TABLE` → GSP-RM | **ĐANG DÙNG** (`kernel_gsp.c:4914`) |
| `vbiosOverrideArgs` | **API chính thức** (`gsp_init_args.h:104-108`) |
| WPR metadata nạp 2 lần | **ĐÃ ĐO** |

**Nhận xét:** driver truyền tham số xuống GSP-RM bằng **API chính thức** của
NVIDIA, không phải ghi trực tiếp register. Điều này nghĩa là phần lớn "mở khoá"
xảy ra **bên trong GSP-RM**, không phải ở driver.

### 2.3 GSP-RM ↔ FWSEC

```
kgspBootstrap_TU102: POST_FWSEC_PRE_GSP_ENTRY WPR=01ffee00:01ffe000
                     FECS=ffffff8f RESET=000000ff
kgspBootstrap_TU102: REFWSEC_STOCK_WPR_PASS WPR=01ffee00:01ffe000
```

**Nhận xét:** WPR được hạ từ `0x01FFEE00:0x01FFE000` xuống khi vào GSP, rồi
**phục hồi lại đúng giá trị đó** sau khi GSP chạy. Đây là chuỗi **relock** —
FWSEC giao quyền cho GSP rồi lấy lại.

### 2.4 GSP-RM ↔ SILICON

| Điểm kiểm soát | Giá trị đo được |
|---|---|
| `FECS_PLM` | `0xFFFFFF8F` |
| `RESET_PLM` | `0x000000FF` |
| `SS0` / `SS1` | `0x88888888` / `0x00000008` |
| `ACR_TOKEN` | `0xC2` |
| `CPUCTL` | `0x00000010` |

**Nhận xét:** `PLM` là **mask 32 bit**, trong đó 8 bit thấp là privilege level
thực. `0x8F` = `10001111` → bit 0,1,2,3,7 bật. Nếu bit 7 = "secure" và bit 0..3 =
các level, thì state = level 3 + secure bật.

**Giới hạn:** `PLM_FECS`/`PLM_RESET` register **poison** trong BAR0 — không đọc
được. Chỉ có giá trị từ boot log.

---

## 3. Vùng nhớ được bảo vệ

| Vùng | Nguồn | Phạm vi | Kích thước |
|---|---|---|---|
| WPR2 | MMIO + dmesg | `0x01F7E000` – `0x01FFEE00` | **480.0 MB** |
| SEC2 DMEM | dmesg | `[0x00000000, 0x00010000)` | 64 KB |

**Sửa lại (U-SEC-001 RESOLVED):** chỉ có **một** vùng WPR. Source driver chỉ định
nghĩa `NV_PFB_PRI_MMU_WPR2_ADDR_LO=0x1FA824` và `..._HI=0x1FA828`. Bản trước của
file này liệt kê 4 vùng WPR0/WPR1/WPR2/WPR2-alt — sai, vì các offset
`0x1FA800..0x1FA82C` không có tên register trong source.

### 3.1 WPR2 là gì?

`WPR2` rộng **480.0 MB** (`0x01F7E000..0x01FFEE00`) — đó là nơi chứa
GSP-RM image và metadata boot. Đúng như prompt mục 9 đã dự đoán: WPR2 nằm trong
VRAM, không đọc được từ host.

### 3.2 SEC2 DMEM — cơ chế tự dọn

```
s_clearCmp40Sec2ExploitDmem: FULL_DMEM_ZERO_PASS [0x00000000,0x00010000)
```

Sau khi SEC2 xong việc, toàn bộ 64 KB DMEM bị **zero hoá**. Đây là biện pháp
**chống phân tích sau thực thi** — dữ liệu còn lại trong DMEM không còn.

---

## 4. Ranh giới DMA

| Thuộc tính | Giá trị |
|---|---|
| IOMMU group | **31** (riêng) |
| DMA mask | **47 bit** (`0x7FFFFFFFFFFF`) |
| BAR0 | 16 MB @ `0xFA000000` |
| BAR1 | 64 GiB @ `0x381000000000` |
| BAR3 | 32 MB @ `0x380800000000` |
| BAR5 | 128 B I/O @ `0xE000` |

**Nhận xét quan trọng:**
- **BAR1 64 GiB** nghĩa là driver có thể map toàn bộ VRAM vào địa chỉ hệ thống.
- **IOMMU group 31** — card nằm một mình trong nhóm IOMMU, **không** DMA được
  sang thiết bị khác. Đây là **ranh giới bảo vệ chủ động**.
- **DMA mask 47 bit** → phạm vi DMA 128 TB.

---

## 5. Confidential Computing — TẮT

```
Conf Compute Protected Memory Usage: Total 0 MiB, Used 0 MiB, Free 0 MiB
GPU Virtualization Mode: None
```

Không có vùng CC nào được cấp phát. Không có cô lập giữa các tenant (không có
multi-tenant).

---

## 6. Ma trận trust boundary

| Ranh giới | Ai kiểm soát | Xác thực? | Đọc được? |
|---|---|---|---|
| Host ↔ driver | kernel | **KHÔNG** (taint) | có |
| Driver ↔ GSP-RM | NVIDIA API | **CÓ** (chính thức) | có |
| GSP-RM ↔ FWSEC | PLM | **CÓ** (`0xFFFFFF8F`) | chỉ log |
| GSP-RM ↔ SEC2 | PLM + token | **CÓ** (`0xC2`) | chỉ log |
| GSP-RM ↔ silicon | PLM + WPR | **CÓ** | phần |
| Silicon ↔ VRAM | WPR | **CÓ** | **KHÔNG** |
| DMA ↔ hệ thống | IOMMU | **CÓ** (group 31) | có |

---

## 7. Kết luận trust boundaries

| Phát hiện | Trạng thái |
|---|---|
| Kiến trúc 5 tầng (host → GSP → FWSEC → SEC2 → silicon) | **ĐÃ XÁC NHẬN** |
| Ranh giới yếu nhất | **Host ↔ driver** (không chữ ký) |
| Ranh giới mạnh nhất | **Silicon ↔ VRAM** (WPR, không đọc được) |
| DMA được cô lập | **IOMMU group 31** |
| Confidential Computing | **TẮT** |
| Chống phân tích sau thực thi | **SEC2 DMEM zero 64 KB** |

**Điểm đáng lưu ý cho nghiên cứu tiếp:** toàn bộ "mở khoá" mà driver thực hiện
xảy ra **bên trong GSP-RM** qua API chính thức. Driver chỉ truyền tham số. Nếu
muốn đi sâu hơn vào khai thác, cần phân tích **GSP-RM firmware** (RISC-V) chứ
không phải driver Linux hay VBIOS.

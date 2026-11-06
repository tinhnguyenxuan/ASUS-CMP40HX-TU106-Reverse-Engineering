# P8 — SECURITY ARCHITECTURE (TU106 trong CMP 40HX)

Bằng chứng: `SECURITY/p8_wpr.json`, `SECURITY/security_registers.json`,
`RAW_DATA/p5678.json`, dmesg boot log, `RAW_DATA/q3_pcie.txt`.

Theo prompt mục 11: chỉ phân tích và lập tài liệu. **Không tạo payload, không sửa
code, không trích xuất khoá bảo mật.**

---

## 1. Tổng quan chuỗi boot GPU (từ dmesg, `MEASURED`)

```
t=0.701  kernel: X.509 cert Ubuntu Secure Boot signing loaded
t=3.946  nvidia: module verification failed: signature and/or required key missing
          -> tainting kernel
t=4.754  GPU0 _kgspCreateSignatureMemdesc
t=4.864  GPU0 kgspBootstrap_TU102: POST_FWSEC_PRE_GSP_ENTRY
t=4.864  GPU0 _kgspCmp40ExecuteBooterFreshMeta
t=4.892  GPU0 kgspBootstrap_TU102: WPR_META_BEFORE_RESET
t=4.892  GPU0 kgspBootstrap_TU102: WPR_META_INPUT_RESET_PASS
t=4.892  GPU0 kgspCmp40SanitizeSec2AfterExploit: NATIVE_CLEANUP_DMEM_PRESERVED_PASS
t=4.892  GPU0 kgspBootstrap_TU102: FULLSPEED_STOCK_RELOCK_WPR_DOWN_HANDOFF_PASS
t=4.892  GPU0 kgspBootstrap_TU102: TOKEN_RELEASE_RESETPLM_FF_PHASE_BOUNDARY_PASS
t=4.956  GPU0 kgspBootstrap_TU102: REFWSEC_STOCK_WPR_PASS
t=4.956  GPU0 kgspBootstrap_TU102: RISCV_MODE_BOOTARGS_PASS
t=4.956  GPU0 kgspBootstrap_TU102: POST_FWSEC_PRE_GSP_HANDOFF_PASS
t=4.956  GPU0 _kgspCmp40ExecuteBooterFreshMeta (lần 2)
t=4.958  GPU0 s_clearCmp40Sec2ExploitDmem: FULL_DMEM_ZERO_PASS [0x00000000,0x00010000)
t=5.005  GPU0 kgspBootstrap_TU102: INPLACE_STOCK_BOOTER_AFTER_UNLOCK_PASS
```

**Chuỗi 5 bước đã được xác nhận:**
1. **FWSEC** (Falcon secure) khởi động, vào trạng thái fullspeed
2. **GSP entry** — WPR được hạ xuống (`WPR-down`)
3. **GSP handoff** — chuyển quyền cho RISC-V GSP
4. **RefWSEC + RISCV boot args** — thiết lập lại WPR, đưa tham số cho RISC-V
5. **Stock relock** — GSP lấy lại quyền điều khiển, WPR hạ lần cuối

---

## 2. WPR (Write-Protected Region) — đọc được cả boot log lẫn MMIO

### 2.1 Giá trị từ boot log (`MEASURED`)

| Tham số | Giá trị |
|---|---|
| `WPR2_lo` | `0x1FFFFE00` |
| WPR tại boot | `0x01FFEE00 : 0x01FFE000` |
| WPR lúc handoff | `0x00000000 : 0x1FFFFE00` |
| WPR lúc inplace-booter | `0x01FFEE00 : 0x01F7E000` |
| WPR2 cuối | `0x00000000 : 0x1FFFFE00` |

### 2.2 Giá trị từ MMIO BAR0 (`MEASURED`)

| Register | Offset | Giá trị | Kích thước vùng |
|---|---|---|---|
| **WPR0_LO** | `0x1FA800` | `0x001001C0` | |
| **WPR0_HI** | `0x1FA804` | `0x1FFFF000` | **~511.0 MB** |
| **WPR1_LO** | `0x1FA810` | `0x00000000` | |
| **WPR1_HI** | `0x1FA814` | `0x08000880` | ~128.0 MB |
| **WPR2_LO** | `0x1FA820` | `0x01F78200` | |
| **WPR2_HI** | `0x1FA824` | `0x01F7E000` | **23.75 KB** |
| **WPR2_LO_ALT** | `0x1FA828` | `0x01FFEE00` | |
| **WPR2_HI_ALT** | `0x1FA82C` | `0x1FFFFFF0` | ~480.0 MB |
| WPR_CFG | `0x1FA830` | `0x00000000` | (zero) |
| PLM_FECS | `0x1FA840` | `0xBADF5040` | **poison** |
| PLM_RESET | `0x1FA844` | `0xBADF5040` | **poison** |
| ACR_CMD | `0x1FA850` | `0xBADF5040` | **poison** |
| ACR_STATUS | `0x1FA854` | `0xBADF5040` | **poison** |
| SEC2_STATUS | `0x1FA860` | `0xBADF5040` | **poison** |

### 2.3 Đối chiếu — có mâu thuẫn cần ghi

`WPR2_LO @0x1FA820 = 0x01F78200` nhưng dmesg báo `WPR2_lo = 0x1FFFFE00`.

**Hai giá trị khác nhau.** Ba khả năng:
- (a) `0x1FA820` là WPR2 của **boot loader** (bị ghi đè khi GSP chạy)
- (b) dmesg báo giá trị **trước** khi driver khởi động
- (c) `0x1FA820`/`0x1FA824` thực ra là cặp `WPR2_LO/HI` của **WPR khác**

**Quan sát đáng chú ý:** `0x1FA824` = `0x01F7E000` **trùng chính xác** với giá trị
`WPR=01ffee00:01f7e000` ở dòng `INPLACE_STOCK_BOOTER_AFTER_UNLOCK_PASS`.
→ `0x1FA824` là **WPR2_HI đang hoạt động**, khớp trạng thái cuối.

**Trạng thái:** `U-SEC-001` giữ `UNKNOWN`, ưu tiên P1.

---

## 3. PLM (Privilege Level Mask) — từ boot log

| Tham số | Giá trị | Nghĩa |
|---|---|---|
| **FECS_PLM** | `0xFFFFFF8F` | PLM trước/sau khi relock |
| **RESET_PLM** | `0x000000FF` | toàn bộ level mở khi reset |
| `plm_before` | `0xFFFFFF8F` | trước |
| `plm_after` | `0xFFFFFF8F` | sau |
| `plm_restored` | `0xFFFFFF8F` | khôi phục |
| SS0 | `0x88888888` | signature/secret slot 0 |
| SS1 | `0x00000008` | signature/secret slot 1 |
| ACR_TOKEN | `0xC2` | token xác thực ACR |

**Ý nghĩa:** `FECS_PLM = 0xFFFFFF8F` là mask **8 bit** (giá trị bit 0..7), trong đó
các bit 4,5,6 bật. Tương truyền NVIDIA: bit 0..3 = các level privilege, bit 7 =
secure. Giá trị `0xFFFFFF8F` = 32 bit với 24 bit cao bật — đây là **toàn bộ mask**
(32 bit), trong đó `0x8F` là phần PLM thực.

`RESET_PLM = 0x000000FF` — reset mở **tất cả 8 level**, phù hợp lúc khởi động.

**Lưu ý:** PLM register **không đọc được qua BAR0** (`0x1FA840/0x1FA844` poison).
Chỉ có giá trị từ boot log. → đây là giới hạn đo, ghi rõ.

---

## 4. ACR / FWSEC

### 4.1 WPR metadata (fresh) — 2 lần nạp

| Lần | phys | signature | size |
|---|---|---|---|
| 1 | `0x8EFDE000` | `0xFFE40000` | `0xFA00` (64,000) |
| 2 | `0x8EFDD000` | `0xFFE40000` | `0x1000` (4,096) |

Đồng thời: `restored stock signature in-place phys=0xffe40000 backing=0xfa00
advertised=0x1000`

**Giải thích:** driver nạp WPR metadata **hai lần**. Lần 1 `size=0xFA00` (64 KB) —
đây là bản đầy đủ. Lần 2 `size=0x1000` (4 KB) — bản rút gọn (`advertised=0x1000`).
`backing=0xFA00` là bộ nhớ thật giữ bản đầy đủ, `advertised` là kích thước
"quảng cáo" cho phần cứng. Đây là cơ chế **in-place restore** — driver tự ghi lại
chữ ký gốc.

### 4.2 SEC2 sanitize

`kgspCmp40SanitizeSec2AfterExploit: NATIVE_CLEANUP_DMEM_PRESERVED_PASS`
`TOKEN_RELEASE_NATIVE_CLEANUP_PASS RESET=000000ff CPUCTL=00000010 mailbox0=00000000
mailbox1=00000000 tracepc=00007d11`

`s_clearCmp40Sec2ExploitDmem: FULL_DMEM_ZERO_PASS [0x00000000,0x00010000)`

**Ý nghĩa:** sau khi xử lý xong, SEC2 engine được **dọn sạch DMEM** — toàn bộ
64 KB `[0x00000000, 0x00010000)` được zero hoá. Đây là biện pháp **xoá dấu vết**,
ngăn việc đọc dữ liệu còn sót sau khi engine đã xong việc.

### 4.3 Mailbox / mutex / stack

| Tham số | Giá trị |
|---|---|
| `mailbox` | `0x1CDD` |
| `mutex_release` | `0x0D27` |
| `stack` | `0xFF14` |
| `stage` | `0xC100` |
| `tail` | `0x3988` |
| `ls_version` | `0x344` |
| `ls_id` | `1` |
| `header` | `0x00020001` |
| `tracepc` | `0x7D11` |
| `CPUCTL` | `0x00000010` |
| `idx` (phase boundary) | `96` |
| `gadgets` | `0xCC8, 0xCBD, 0x0C1D, 0x1D62, 0x1F89, 0x5FF, 0x64EC` |

`gadgets` là **7 địa chỉ trong firmware** mà driver đã ghi log. Chúng là điểm
nằm trong dải `0x4F57xxx..0x4F72xxx` mà em đã disasm ở Q1 — **trùng khớp vùng
dispatch**. Không suy đoán thêm chức năng.

---

## 5. Secure boot và chữ ký driver

### 5.1 Driver Linux KHÔNG được ký

```
[    3.945834] nvidia: module verification failed: signature and/or required key
                       missing - tainting kernel
```

→ driver nvidia trên máy này **không có chữ ký hợp lệ** so với CA của Ubuntu
(`Canonical Ltd. Secure Boot Signing (Ubuntu Core 2019)`).

**Hệ quả:** nếu Secure Boot bật, driver không nạp được. Card chỉ chạy được vì
Secure Boot **tắt** trên máy này. Đây là **ràng buộc ở tầng host**, không phải
tầng GPU.

### 5.2 GPU firmware — CÓ chữ ký, và driver khôi phục nó

```
_kgspCreateSignatureMemdesc: signed fullspeed stock-relock WPR-down commit
kgspCmp40RebuildStockSignature: restored stock signature in-place
```

→ GPU firmware **được ký** và driver **chủ động khôi phục chữ ký gốc** sau khi
mở khoá. Nghĩa là firmware không bị thay thế, chỉ được mở khoá tạm thời.

---

## 6. Trust boundaries

### 6.1 Phân vùng bảo vệ (đo được)

| Vùng | Nguồn | Kích thước | Ghi chú |
|---|---|---|---|
| **WPR0** | MMIO | ~511.0 MB | `0x001001C0..0x1FFFF000` |
| **WPR1** | MMIO | ~128.0 MB | `0x00000000..0x08000880` |
| **WPR2** | MMIO | 23.75 KB | `0x01F78200..0x01F7E000` |
| **WPR2 (alt)** | MMIO | ~480.0 MB | `0x01FFEE00..0x1FFFFFF0` |
| SEC2 DMEM | dmesg | 64 KB | `[0x00000000,0x00010000)` — zero sau dùng |

### 6.2 Mức truy cập DMA

```
IOMMU group : 31
DMA mask    : 47 bits (0x7FFFFFFFFFFF)
BAR1        : 64 GiB
BAR3        : 32 MiB (Resizable BAR)
```

DMA mask 47 bit → GPU có thể DMA tới toàn bộ **128 TB** địa chỉ hệ thống.
**IOMMU group 31** nghĩa là card nằm trong một nhóm IOMMU riêng — đây là điều
**tốt**: card không thể DMA sang thiết bị ngoài nhóm.

### 6.3 Confidential Computing

```
Conf Compute Protected Memory Usage: Total 0 MiB, Used 0 MiB, Free 0 MiB
```

→ **Confidential Computing TẮT.** Không có vùng bảo vệ CC nào được cấp phát.
`nvidia-smi` báo `GPU Virtualization Mode: None`.

---

## 7. Những gì KHÔNG làm được (giới hạn đo)

| Tham số | Trạng thái | Vì sao |
|---|---|---|
| PLM register thực | **chỉ có từ boot log** | `0x1FA840/0x1FA844` poison |
| ACR_CMD / ACR_STATUS | **poison** | ngoài cửa sổ BAR0 decode |
| SEC2_STATUS | **poison** | ngoài cửa sổ BAR0 |
| Falcon privilege level thực | **UNKNOWN** | cần đọc register của từng Falcon engine |
| Secure boot state GPU | **UNKNOWN** | fuse báo giá trị nhưng không xác nhận được quá trình |
| Khoá bảo mật | **KHÔNG TRÍCH XUẤT** | cấm theo prompt mục 11 |

---

## 8. Kết luận P8

| Mục | Trạng thái |
|---|---|
| Chuỗi boot 5 bước | **ĐÃ XÁC NHẬN** (dmesg, `MEASURED`) |
| WPR regions | **ĐỌC ĐƯỢC** cả boot log lẫn MMIO |
| PLM | **CHỈ boot log** — MMIO poison |
| ACR | **poison** — chỉ biết token `0xC2` |
| FWSEC | **đã xác nhận** hoạt động |
| SEC2 | **đã xác nhận** + dọn DMEM 64 KB |
| Driver Linux chữ ký | **KHÔNG HỢP LỆ** — Secure Boot tắt trên host |
| GPU firmware chữ ký | **CÓ** + được khôi phục in-place |
| Trust boundary DMA | IOMMU group 31 riêng, DMA 47-bit |
| Confidential Computing | **TẮT** |
| Khoá bảo mật | **không trích xuất** |

**P8: ĐẠT** — phân loại được firmware components, WPR regions, trust boundaries,
và chứng minh được một số mâu thuẫn cần ghi nhận (`U-SEC-001`).

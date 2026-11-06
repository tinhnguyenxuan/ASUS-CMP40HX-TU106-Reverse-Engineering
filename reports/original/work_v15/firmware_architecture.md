# FIRMWARE ARCHITECTURE — CMP 40HX / TU106

Nguồn: `ucodes_tu10x.bin` (8,837,632 B) và `gsp_tu10x.bin` (22,901,632 B),
driver 615.78.08. Dữ liệu đầy đủ: `outputs/firmware_container_map.json`.

Quy tắc C3: **không khẳng định AES chỉ từ entropy cao.**

---

## 1. NVUCODES container — C1

```
+0x00  "NVUCODES"                      magic ASCII
+0x08  u32 ver        = 1
+0x0C  u32 header_size= 0x1F0 = 496
+0x10  u64 hash       = 0x8D1990AB6B98AE2B
```

**Entry directory** @ `0x1F0`, stride **32 byte**, marker `04 00 00 00`
ngay trước trường `offset` u32:

```
@0x00208  off=0x00002F00    @0x00328  off=0x00098F00
@0x00220  off=0x00020F00    @0x00340  off=0x000B7C00
@0x00238  off=0x0003EF00    @0x00358  off=0x000D6700
@0x00250  off=0x0005CF00    @0x00370  off=0x000F5400
@0x00268  off=0x0007AF00    @0x00388  off=0x00113F00
                            @0x003A0  off=0x00134300
```

11 blob, offset **tăng đơn điệu**, khoảng cách đều `0x1E000` (blob cuối `0x20400`).
Blob cuối kết thúc `0x134300 + 7,575,296 = 0x86DA00` = **đúng kích thước file** →
không có dữ liệu ngoài directory.

---

## 2. Phân loại 11 blob — C2

| # | Offset | Size | Entropy | Nonzero | Phân loại | head 16 |
|---:|---|---:|---:|---:|---|---|
| 0 | `0x00002F00` | 122,880 | 3.481 | 37% | plaintext | `3a 7e a9 5c b0 28 ...` |
| 1 | `0x00020F00` | 122,880 | **7.998** | 99% | entropy cao | — |
| 2 | `0x0003EF00` | 122,880 | **7.998** | 99% | entropy cao | — |
| 3 | `0x0005CF00` | 122,880 | **7.998** | 99% | entropy cao | — |
| 4 | `0x0007AF00` | 122,880 | **7.998** | 99% | entropy cao | — |
| 5 | `0x00098F00` | 126,208 | 4.915 | 57% | plaintext | — |
| 6 | `0x000B7C00` | 125,696 | 4.898 | 57% | plaintext | — |
| 7 | `0x000D6700` | 126,208 | 4.916 | 57% | plaintext | — |
| 8 | `0x000F5400` | 125,696 | 4.898 | 57% | plaintext | — |
| 9 | `0x00113F00` | 132,096 | 4.953 | 57% | plaintext | — |
| 10 | `0x00134300` | 7,575,296 | 7.261 | 83% | hỗn hợp | — |

**Tổng: 6 plaintext + 4 entropy cao + 1 hỗn hợp.**

### 2.1 Vì sao 4 blob giống nhau là đáng chú ý

Cả 4 blob entropy cao đều **chính xác 122,880 B = 0x1E000**, entropy **7.998**,
nonzero **99%**. Kích thước giống hệt nhau gợi ý **cùng một loại firmware**,
mỗi engine một blob (FECS, GPCCS, SEC2, PMU là 4 engine có microcode riêng
trên Turing).

### 2.2 Vì sao KHÔNG kết luận là AES

Entropy 7.998/8.0 chỉ nói **phân bố byte gần đều**. Điều này đúng cho:
- dữ liệu mã hoá (AES-CBC/CTR, ChaCha20…)
- dữ liệu nén tốt (LZMA, deflate mức cao, zstd --ultra)
- dữ liệu đã nén **rồi** mã hoá

Không có bằng chứng nào phân biệt ba khả năng này từ dữ liệu hiện có:
- Không có magic/header trong 16 byte đầu.
- Không tìm thấy IV/salt 16 byte lặp lại ở cùng offset giữa các blob.
- Không có khoá nào trong driver source công khai (615.78.08) để giải mã
  microcode engine — driver chỉ `request_firmware` rồi đẩy nguyên blob xuống GPU.

**Kết luận C3: chỉ ghi nhận "entropy cao, chưa phân loại".**

### 2.3 Phép thử phân biệt (chưa chạy)

1. **Nén lại:** `zlib.compress(blob)` / `lzma.compress(blob)`. Nếu tỉ lệ nén
   > 1.02 → dữ liệu **không mã hoá** (nén được dữ liệu có cấu trúc). Nếu ≈ 1.00
   → đã mã hoá hoặc đã nén.
2. **XOR cặp blob:** nếu hai blob là cùng plaintext khác key (kiểu stream
   cipher), `blob1 XOR blob2` sẽ lộ cấu trúc (nhiều byte 0 hoặc pattern).
3. **Tìm 16 byte trùng:** nếu 4 blob có 16 byte giống nhau ở cùng offset → IV
   cố định hoặc salt.

---

## 3. Bản đồ nạp / xác thực / khởi tạo — C4

Từ log driver thực tế trong phiên (dmesg trên target), chuỗi khởi tạo:

```
[4.955] _kgspCmp40ExecuteBooterFreshMeta:
        fresh WPR metadata phys=0x8efdd000 signature=0xffe40000 size=0x1000
[4.958] s_clearCmp40Sec2ExploitDmem:
        FULL_DMEM_ZERO_PASS [0x00000000,0x00010000)
[5.005] kgspBootstrap_TU102:
        STOCK_BOOTER_RESET_FF_ACCEPTED
[5.005] INPLACE_STOCK_BOOTER_AFTER_UNLOCK_PASS
        WPR=01ffee00:01f7e000  SS0=0x88888888 SS1=0x00000008
        FECS_PLM=0xffffff8f  RESET_PLM=0x000000ff
[5.602] CMP40_GSP_READY_V551: feature=0x000000f3 ss0=0x88888888
        readout=0x00000000 ss1=0x00000008
[5.602] CMP40_PCIE_GEN2_V2: LNKCFG=0x80085800 PL_RATE=0x00140036 CYA0=0x068731b3
[5.682] CMP40_PCIE_GEN2_V2: CYA=068731b3(DIS_G2=0) CFG=80085800
[7.812] CMP40_PCIE_GEN2_V2: RETRAIN_FAIL status=1101
```

**Diễn giải thứ tự (chỉ phần đọc được từ log):**
1. Host RM ghi WPR metadata mới (`0xffe40000`).
2. Xoá DMEM 64 KB của SEC2 trước khi boot.
3. Booter chạy, reset được chấp nhận (`RESET_FF_ACCEPTED`).
4. WPR2 đặt tại `0x01ffee00..0x01f7e000`.
5. GSP báo ready, `feature = 0xf3`.
6. Thương lượng PCIe (bị ép Gen2 — `DIS_G2=0` nhưng `RETRAIN_FAIL`).

**Ghi chú:** đây là log của **bản cmpunlocker đã vá**, không phải đường boot
nguyên bản. Dùng để hiểu **thứ tự**, không dùng để suy ra hành vi stock.

---

## 4. Thành phần tham gia power/clock policy — C5

| Thành phần | Bằng chứng trong phiên này | Vai trò power/clock |
|---|---|---|
| **GSP-RM** | ELF RISC-V 22.9 MB, 17 MB code, 139 descriptor regkey | **CÓ** — `PERF_CF_CONTROLLER_GPC_MAX` (id 21), `_DRAM_MAX` (20), `_NVD_MAX` (23); 116 string PWR, 50 CLK, 31 VOLT, 32 PSTATE |
| **VBIOS VFE** | 150 slot × 24 B, 20 var × 25 B @ `0x5649C` | **CÓ** — REL/ALT/OV/VMIN/BOOT đều là slot VFE |
| SEC2 | log boot có nhắc (`SEC2ExploitDmem`) | **CHƯA XÁC ĐỊNH** |
| PMU | không có log/string riêng | **CHƯA XÁC ĐỊNH** |
| FECS | `FECS_PLM=0xffffff8f` trong log boot | **CHƯA XÁC ĐỊNH** (chỉ thấy trong thanh ghi) |
| GPCCS | không thấy | **CHƯA XÁC ĐỊNH** |

**Không có bằng chứng nào cho phép quy kết trần 1905 MHz cho SEC2/PMU/FECS/GPCCS.**
Đây là điểm thiếu #7 trong `MASTER_REPORT.md`.

---

## 5. Giao tiếp ở mức kiến trúc — C6

Đường đã xác định (không sửa đổi chuỗi boot, không triển khai bypass mới):

```
VBIOS (SPI flash, 1 MiB)
  └─ NPDS type-0xE0 #2 @0x054000
       └─ VFE table @0x5649C   (150 slot × 24 B, 20 var × 25 B)
            ├─ slot[0] = NVVDD REL  (hằng 1068.75 mV)
            ├─ slot[1] = NVVDD ALT  (hằng 1093.75 mV)
            ├─ slot[3] = NVVDD OV   (hằng 1125 mV)
            ├─ selector @0x2D384    (0,1,3,0,2,4)
            └─ slot[2..149]         (84 slot có hệ số góc)

host RM (nvidia.ko, 615.78.08)
  ├─ kgspExtractVbiosFromRom_TU102   đọc VBIOS qua SPI/eFuse
  ├─ _kgspVbiosOverridePrepare       thay image từ RAM (đường đã dùng cho T4)
  └─ kernel_gsp.c:4914               đóng gói PACKED_REGISTRY_TABLE

GSP-RM (RISC-V, 22.9 MB)
  ├─ 8 bảng descriptor @0x1a7280  (139 entry × 32 B)
  ├─ PERF_CF_CONTROLLER_GPC_MAX    (id 21, module 273)
  ├─ OFFER_VOLTAGE / NVVDD_0 / NVVDD_1
  └─ OVERCLOCKING (4 string), TGP (3 string)

PMU / SEC2 / FECS / GPCCS  ← CHƯA XÁC ĐỊNH
```

**Điểm đứt:** chưa tìm được hàm trong 17 MB code GSP-RM đọc slot VFE và
chuyển thành yêu cầu điện áp. Lý do: không có XREF cứng tới chuỗi key
(đã kiểm 3 kiểu trên toàn file — xem `EVIDENCE_LEDGER.md` E08).

---

## 6. Tóm tắt C1–C6

| Mục | Trạng thái |
|---|---|
| C1 header + entry directory | **ĐẠT** — 11 blob, stride 32, offset/size/entropy đầy đủ |
| C2 phân biệt nén/mã hoá/không xác định | **ĐẠT MỘT PHẦN** — phân loại được plaintext vs entropy cao; chưa phân biệt AES vs nén |
| C3 không khẳng định AES từ entropy | **TUÂN THỦ** |
| C4 bản đồ loading/auth/init | **ĐẠT MỘT PHẦN** — từ log thực, nhưng là log bản đã vá |
| C5 thành phần power/clock | **ĐẠT MỘT PHẦN** — GSP-RM + VBIOS có bằng chứng; SEC2/PMU/FECS/GPCCS không |
| C6 kiến trúc giao tiếp | **ĐẠT** — đường đi từ VBIOS tới GSP-RM, có điểm đứt ghi rõ |

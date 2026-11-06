# DISCOVERY LOG — CMP 40HX / TU106

Mỗi mục: hành động → kết quả thô → kết luận → phân loại.
Nhật ký này ghi **cả phát hiện sai và sửa lại**, không chỉ thành công.

Phân loại: `MEASURED` · `DECODED` · `CORROBORATED` · `INFERRED` · `UNKNOWN` ·
`CONTRADICTED` · `BLOCKED`

---

## Vòng 1 — Khôi phục và kiểm kê

**Hành động:** đọc `CHECKPOINT.json`, kiểm tra `cmp40hx_research/` và
`~/cmpunlock/vbiosovr/src` trên target.

**Kết quả:** checkpoint phiên trước có 22 mục `DONE`. Driver source 211 MB,
**2,133 header**.

**Kết luận:** trạng thái khôi phục được, không cần làm lại P2/P3 cũ ở mức cấu trúc.

`MEASURED`

---

## Vòng 2 — P0: trích register từ source

**Hành động:** `TOOLS/extract_regs.py` quét 2,133 header.

**Kết quả (lần 1):** 13,428 register, 7,890 bitfield. Nhưng `NV_FUSE*` có **100**
register, nhiều cái địa chỉ `0x0`/`0x1` — vô lý.

**Phát hiện lỗi:** regex nhận nhầm **value definition** (`#define ..._DATA_NO 0x00000000`)
là register.

**Sửa:** yêu cầu `0x1000 ≤ addr ≤ 0x100000000` → còn **938 register**.

`DECODED` (sửa lỗi)

---

## Vòng 3 — P0: aperture fuse

**Hành động:** đọc 64 register `NV_FUSE*` qua `mmap` read-only tại `0x00820000`.

**Kết quả:**
```
0x00820000 -> 0x166000a1   (= NV_PMC_BOOT_0, KHONG phai fuse)
0x00820378 -> 0xbadf5040   poison
... 53/64 poison
```

**Kiểm chứng đối chứng:** đọc cùng offset qua `0x00021000`:
```
0x00021378 -> 0x00000000   NVDEC_DISABLE = 0
0x0002174c -> 0x00000001   SECURE_GSP_DEBUG_DIS = 1
```

**Nguyên nhân:** `NV_FUSE0_PRI_BASE = 0x820000` chỉ có trong
`blackwell/gb100/hwproject.h`, không áp dụng TU106.

**Kết luận:** `0x00021000` là cửa sổ thật. **Bác bỏ** kết luận phiên trước.

`MEASURED` + `CONTRADICTED`

---

## Vòng 4 — P0: span thật của khối fuse

**Hành động:** `TOOLS/fuse_dump2.py`, dump theo trang 4 KB, dừng khi gặp trang
toàn poison.

**Kết quả:**
```
trang 0x00000: 300 co du lieu, 239 poison
trang 0x01000:  52 co du lieu, 939 poison
trang 0x02000:   0 co du lieu, 1024 poison   <-- DUNG
tong 3072 word: 352 co du lieu, 2202 poison, 518 zero
```

**Kết luận:** span thật `0x1DFF` (7,680 B), không phải `0x1800`.
**352 word có dữ liệu**. Poison gồm **3 mã**, không phải 1.

`MEASURED`

---

## Vòng 5 — P0: cấu trúc nội dung fuse

**Hành động:** phân tích 352 word theo vùng offset.

**Kết quả:**
- `0x0110..0x0198`: **152 word toàn `0x00000001`**
- `0x00D4..0x00F4`: **11 word `0xFFFFFFFC`/`0xFFFFFF8F`**
- `0x0718..0x0734`: **8 word entropy cao liên tục** (32 B)
- `0x04D8 = 0x1F0B`, `0x056C = 0x1F4B`, `0x0650 = 0x0004001F`

**Kết luận:** 3 loại nội dung rõ rệt. Đối chiếu `0x04D8`/`0x056C`/`0x0650` khớp
dữ liệu đo độc lập → `CORROBORATED`.

**Không kết luận** 152 word là "physical OTP" — giữ `INFERRED` vì cả 2 giả thuyết
(OTP cell / mảng enable flag) cùng khớp.

`MEASURED` + `CORROBORATED` + `INFERRED`

---

## Vòng 6 — P1: MMIO map

**Hành động:** `TOOLS/mmio_scan.py` đọc 52 register turing.

**Kết quả:**
```
data 33 · zero 13 · poison 6
NV_PMC_BOOT_0 = 0x166000a1
NV_PFB_PRI_MMU_WPR2_ADDR_LO = 0x01f7e000
NV_PFB_PRI_MMU_WPR2_ADDR_HI = 0x01ffee00
NV_PCFG_XVE_REGISTER_MAP_START_OFFSET = 0x1f0b10de
```

**Đối chứng chéo:** dmesg boot ghi `WPR=01ffee00:01f7e000` → **khớp 100%**.
Hai nguồn độc lập (MMIO + log).

`MEASURED` + `CORROBORATED`

---

## Vòng 7 — P2: cấu trúc ROM

**Hành động:** so sánh `rom[0:0x79000]` với `rom[0x79000:0xF2000]`.

**Kết quả:**
```
byte khac: 1,212 / 495,616 = 0.245%
cum khac DUY NHAT: 0x3000..0x34BF
sau 0xF2000: 57,344 B (NMX container)
```

**Kết luận:** ROM 1 MiB = **2 bản sao của image 495,616 B** + NMX 57,344 B.
**Bác bỏ** "bank1 660,992 B + bank2 387,584 B" của phiên trước.

`MEASURED` + `CONTRADICTED`

---

## Vòng 8 — P2: key block

**Hành động:** parse `0x3000..0x34BF` = 1,216 B.

**Kết quả:** **38 record × 32 byte chính xác**.

```
+0x00 2 sig  0x6700 (37) / 0x6701 (1)
+0x02 2 ver  0x0200/0x0300/0x0400/0x0600
+0x04 4 f4   luon boi so 0x20 (38/38)
+0x08 4 f8   0x1669xxxx..0x1687dxxx
+0x0C 4 flags lo ∈ {FF,FC,F8,F0,F3}  hi ∈ {00,79}
+0x10 16 hash
```

Bản 2 tại cùng vùng: **toàn `0xFF`**.

**Giả thuyết bị bác bỏ:**
- `f4` = unix timestamp → chỉ 9/38 trong dải hợp lý
- `hash` = SHA-256/SHA-1/MD5 của ROM → **0/912** phép thử

**Kết luận:** layout giải được, **nghĩa 3/6 field chưa biết**.

`DECODED` (layout) + `UNKNOWN` (nghĩa)

---

## Vòng 9 — P3: sửa lỗi parser descriptor

**Hành động:** parse lại bảng descriptor GSP-RM.

**Phát hiện lỗi:** bảng thật gồm các tên như
```
PERF_CF_CONTROLLER_GPC_MAX
CONTROLLER_GPC_MAX      <- chi la duoi chuoi cua ten tren
ER_NVD_MAX              <- 8 byte cuoi cua PERF_CF_CONTROLLER_NVD_MAX
OWER
M_GRP_1
```
Parser cũ quét bước 32 byte từ offset tuỳ ý nên nhận cả **đuôi chuỗi**.

**Sửa:** `name_ptr` phải trỏ **đầu chuỗi thật** trong bảng 134,417 string của
`.rodata`; `f0c == 0`; bước nhảy 4; gom bảng ≥3 entry.

**Kết quả:**
```
134,417 string · 1,509 ứng viên · 60 bảng · 340 entry THẬT
```

**Bác bỏ** "8 bảng, 139 entry" của phiên trước.

`DECODED` + `CONTRADICTED`

---

## Vòng 10 — P3: tên policy khớp nvidia-smi

**Hành động:** lọc 340 tên theo `NVVDD|VMIN|VOLT|PWR|CLK|PERF_CF|TDP|PSTATE`.

**Kết quả (100 entry):**
```
RELIABILITY_NVVDD          id=204 f08=0xff02 f14=150 f18=273
VMIN_NVVDD_0/1             id=204/205
VMIN_MSVDD_1               id=206/208/213
VMIN_LOGIC                 id=213
MCLK_LIMIT                 id=155/158  f08=0x0000010e
RATED_TDP_MIN              id=137
UNLOAD_DRIVER_VOLTAGE_RAIL_0..3   id=139/149/150/151/152
PERF_CF_CONTROLLER_GPC_MAX (6 ban)
MODS_RULES_STRICT_PSTATE/DRAM/PCIE/XBAR_MAX/MIN
CLIENT_LOW_STRICT_PSTATE_MAX/MIN
JPAC_PSTATE_MAX · PMU_DOM_GRP_1
```

`nvidia-smi -q -d PERFORMANCE` báo cờ **`Reliability`** — GSP có
**`RELIABILITY_NVVDD`**. T4 làm cờ đó chuyển `Not Active`.

**Kết luận:** liên hệ tên ↔ hành vi là `INFERRED`, **chưa chứng minh nhân quả**
(vì `id=204` trùng 3 entry khác nhau).

**Sửa thêm:** gán `id=21 f08=0xff0a f14=88` cho `GPC_MAX` trong báo cáo cũ là
**sai** — giá trị đó thuộc `XBAR_MAX`.

`DECODED` + `CONTRADICTED`

---

## Vòng 11 — P3: xref sau khi sửa

**Hành động:** kiểm con trỏ ngược về base cả 60 bảng.

**Kết quả:** **0 hit** ở tất cả.

**Kết luận:** code giữ base dưới dạng **hằng số trong lệnh** (`lui`/`auipc`),
không qua biến con trỏ → giải thích vì sao quét con trỏ thất bại.
Hướng đúng: tìm hằng số `0x41AA418`.

`CORROBORATED`

---

## Vòng 12 — P4: XOR cặp blob firmware

**Hành động:** `TOOLS/fw_entropy.py`, XOR mọi cặp blob cùng kích thước.

**Kết quả:**
```
blob[0]^blob[1..4]: entropy 7.997-7.998, nonzero 99.4%
blob[5]^blob[7]:    entropy 3.8064, nonzero 41.1%
blob[6]^blob[8]:    entropy 0.0033, nonzero  0.0%   <-- GAN NHU BANG 0
```

Kiểm chứng trực tiếp: `blob[6]` vs `blob[8]` khác **đúng 24 byte** tại
`0x6F3E`, `0x7200..0x7213`, `0xB659`, `0xB7B8..0xB7CB`.

**Kết luận:** `blob[6]` ≡ `blob[8]` → 6 plaintext nhưng chỉ **~5 nội dung**.
4 blob mã hoá là **4 nội dung khác nhau** (XOR ra entropy cực đại).

`MEASURED` + `DECODED`

---

## Vòng 13 — P4: nén lại 4 blob entropy cao

**Hành động:** thử `zlib -9` và `lzma preset 9` trên 4 blob.

**Kết quả:**
```
size 122,880 · entropy 7.998 · distinct 256/256 · max_freq ~0.006
zlib ratio 1.001 · lzma ratio 0.999  -> khong giam byte nao
```

**Kết luận:** đã ở dạng không nén được nữa — đúng cho **cả** mã hoá **và** nén
tối đa. **KHÔNG kết luận AES** (mục C3 / 7.I).

`DECODED` + `UNKNOWN`

---

## Vòng 14 — P4: disasm blob[0]

**Hành động:** `envydis -m falcon` trên `blob[0]` (122,880 B), 4 offset khởi đầu.

**Kết quả:**
```
3 lenh dau decode duoc: mov $r0 0xffc0 / mov $sp $r0 / clear b32 $r10 / lcall 0xfe10 / exit
toan bo: 93.1% "unknown instruction" o CA 4 offset (4/8/0x10/0x20)
0 lcall · 4 exit · entropy 3.481 · nonzero 37%
```

**Kết luận:** **không phải code Falcon**. 3 lệnh đầu chỉ là trùng hợp byte pattern.
Entropy 3.481 quá thấp cho code. → `INFERRED`: data segment.

`MEASURED` + `INFERRED` + `BLOCKED`

---

## Vòng 15 — P5/P6/P7/P8: đo read-only

**Hành động:** `TOOLS/phase5678.py` trên target.

**Kết quả đáng chú ý:**
```
P7: Region 0 = 16 MB, Region 1 = 64 GB (!), Region 3 = 32 MB
    LnkCap 5GT/s · LnkCtl2 target 5GT/s · LnkSta RUNTIME 2.5GT/s (downgraded)

P6: Total 8192 MiB · Reserved 389 MiB · Free 7804 MiB
    BAR1 Total 65536 MiB

P8: WPR2 = 01f7e000..01ffee00 (khop MMIO 100%)
    module verification failed - tainting kernel
```

**Kết luận:**
- **P6 giải xong:** 389 MiB là **Reserved**, `nvidia-smi` nói thẳng. WPR2 chỉ
  0.5 MiB → **388.5 MiB là carveout khác** (UNKNOWN).
- **P7:** card **có Gen2**, đích đặt Gen2, **runtime Gen1** — 3 tầng khác nhau.
- **P8:** WPR2 khớp 2 nguồn độc lập.

`MEASURED` + `CORROBORATED`

---

## Vòng 16 — Ráp và self-check

**Hành động:** `TOOLS/build_db.py` + `TOOLS/verify_all.py`.

**Kết quả:** 35 unknown (32 open, 3 resolved), coverage 9 subsystem,
**39/39 assert PASS**.

**Kết luận phiên:** 8 kết luận cũ bị bác bỏ, 6 mục BLOCKED có lý do,
0 thao tác ngoài read-only.

`MEASURED`

---

## Tổng kết phân loại

| Phân loại | Số phát hiện |
|---|---:|
| `MEASURED` | 11 |
| `DECODED` | 6 |
| `CORROBORATED` | 4 |
| `INFERRED` | 3 |
| `CONTRADICTED` (bác bỏ) | 8 |
| `UNKNOWN` (ghi nhận) | 35 |
| `BLOCKED` (có lý do) | 6 |

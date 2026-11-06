# P4 — FALCON / FIRMWARE REVERSE ENGINEERING

Trạng thái: **ĐẠT MỘT PHẦN** — 3 phát hiện mới, 2 mục BLOCKED có lý do.
Bằng chứng: `FIRMWARE/firmware_inventory.json`, `TOOLS/fw_entropy.py`.

---

## 1. Container NVUCODES — xác nhận layout

```
+0x00  "NVUCODES"
+0x08  u32 ver = 1
+0x0C  u32 header_size = 0x1F0 = 496
+0x10  u64 = 0x8D1990AB6B98AE2B
```

Entry table @ `0x1F0`, **stride 32**, marker `04 00 00 00` + offset u32.
File 8,837,632 B, **11 blob**, offset tăng đơn điệu, khoảng cách đều `0x1E000`.
Blob cuối kết thúc `0x86DA00` = **đúng kích thước file** → không dữ liệu ngoài.

---

## 2. PHÁT HIỆN #1 — `blob[6]` và `blob[8]` LÀ CÙNG MỘT FIRMWARE

Đây là phát hiện quan trọng nhất của P4.

Phép thử XOR cặp blob cùng kích thước:

```
blob[5] ^ blob[7] (126,208 B): entropy 3.8064, nonzero 41.1%
blob[6] ^ blob[8] (125,696 B): entropy 0.0033, nonzero  0.0%   <-- GAN NHU BANG 0
```

Kiểm chứng trực tiếp:

```
blob[6] vs blob[8]: 125,696 vs 125,696 B, 24 byte khac
  4 cum khac: 0x6F3E (1 B), 0x7200..0x7213 (20 B),
              0xB659 (1 B), 0xB7B8..0xB7CB (20 B)
```

**Kết luận (MEASURED):** hai blob **trùng nhau 99.98%**, khác đúng **24 byte**
ở 2 cặp vị trí (1 byte + 20 byte) lặp lại 2 lần.

Cùng so sánh `blob[5]` vs `blob[7]`: **51,879 byte khác** (41%) → hai firmware khác nhau.

**Hệ quả:** trong 11 blob, **6 plaintext không phải 6 firmware độc lập**. Có
**cặp trùng**. Đếm lại: tối đa **5 firmware plaintext khác nhau**, không phải 6.

**Chưa xác định:** 24 byte khác nhau là gì — version stamp? patch? checksum?
**UNKNOWN `U-FW-012`.**

---

## 3. PHÁT HIỆN #2 — 4 blob entropy cao KHÔNG nén được

Theo mục 7.I ("không giả định entropy cao = AES") và C3, đã chạy 2 phép thử
phân biệt:

| # | Size | entropy | distinct byte | max_freq | zlib ratio | lzma ratio | Kết luận |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 122,880 | 7.998 | **256/256** | 0.00606 | **1.001** | **0.999** | không nén được |
| 2 | 122,880 | 7.998 | 256/256 | 0.00582 | 1.001 | 0.999 | không nén được |
| 3 | 122,880 | 7.998 | 256/256 | 0.00596 | 1.001 | 0.999 | không nén được |
| 4 | 122,880 | 7.998 | 256/256 | 0.00632 | 1.001 | 0.999 | không nén được |

**Đọc kết quả:**
- `distinct_byte = 256/256` → **cả 256 giá trị byte đều xuất hiện**.
- `max_freq ≈ 0.006` ≈ `1/256 = 0.0039` × 1.5 → **phân bố gần đều**.
- `zlib_ratio 1.001` / `lzma_ratio 0.999` → **nén KHÔNG giảm được byte nào**.

**Kết luận (DECODED):** 4 blob **đã ở dạng không nén được nữa**. Điều này đúng
cho **cả** dữ liệu mã hoá **và** dữ liệu đã nén mức tối đa.

### 3.1 Những gì KHÔNG kết luận được (tuân thủ C3 / 7.I)

- **KHÔNG** kết luận "là AES".
- **KHÔNG** kết luận "là LZMA/zstd".
- **KHÔNG** có magic, header, IV, salt nào tìm thấy trong 16 byte đầu.

### 3.2 Phép thử XOR cặp blob mã hoá

```
blob[0] ^ blob[1..4]: entropy 7.997-7.998, nonzero 99.4%
blob[1] ^ blob[2..4]: entropy 7.997-7.998, nonzero 99.4%
```
Tất cả cặp đều ra entropy cực đại → **không phải cùng plaintext khác khoá
stream cipher**. Nếu là stream cipher cùng plaintext, XOR sẽ ra cấu trúc.

**Hệ quả (DECODED):** 4 blob là **4 nội dung khác nhau**, không phải 1 nội dung
mã hoá 4 lần.

---

## 4. PHÁT HIỆN #3 — `blob[0]` KHÔNG phải code Falcon thuần

`blob[0]` @ `0x002F00`, 122,880 B, entropy **3.481**, nonzero 37%,
`text_like` 8.4%.

```
head 64 B: d0 c0 ff 00 00 fe 04 00 bd a4 7e 10 fe 00 f8 02
           8b 00 00 00 0c 38 f4 30 c8 f9 22 fe 40 01 90 00
```

### 4.1 Thu decode Falcon (envydis)

Ba lệnh đầu decode **có nghĩa**:

```
00000000: d0 c0 ff 00 00     mov $r0 0xffc0
00000005: fe 04 00           mov $sp $r0
00000008: bd a4              clear b32 $r10
0000000a: 7e 10 fe 00        lcall 0xfe10
0000000e: f8 02              exit
```

Nhưng khi disasm toàn bộ 122,880 B:

```
93.1% dong la "unknown instruction"
0 lcall
4 exit
```

Thử 4 offset khởi đầu khác nhau (`0x04`, `0x08`, `0x10`, `0x20`):
**93.1% unknown ở cả 4**.

### 4.2 Kết luận

`blob[0]` **không phải firmware Falcon thuần code**. Bằng chứng:
- Entropy 3.481 quá thấp so với code Falcon (~5–6).
- `nonzero` chỉ 37% → 63% byte là 0.
- 93.1% lệnh không decode được từ **mọi** offset thử.
- Không có magic `fuc`/`NVFU`/header chuẩn.

**Giả thuyết (INFERRED):** `blob[0]` là **bảng dữ liệu / tham số** (data segment),
không phải text segment. 3 lệnh đầu decode được chỉ là **trùng hợp byte pattern**.

**Đúng bài học từ phiên trước:** tỉ lệ decode KHÔNG đủ tin. Ở đây tỉ lệ decode
thấp (7%) và bản thân nó đã là bằng chứng **phủ định**.

---

## 5. Bảng phân loại 11 blob

| # | Offset | Size | Entropy | Nội dung xác định được |
|---:|---|---:|---:|---|
| 0 | `0x002F00` | 122,880 | 3.481 | **dữ liệu, không phải code** (INFERRED) |
| 1 | `0x020F00` | 122,880 | 7.998 | không nén được, khác nội dung với 2/3/4 |
| 2 | `0x03EF00` | 122,880 | 7.998 | như trên |
| 3 | `0x05CF00` | 122,880 | 7.998 | như trên |
| 4 | `0x07AF00` | 122,880 | 7.998 | như trên |
| 5 | `0x098F00` | 126,208 | 4.915 | plaintext, **khác blob[7] 41%** |
| 6 | `0x0B7C00` | 125,696 | 4.898 | plaintext, **≡ blob[8] (24 B khác)** |
| 7 | `0x0D6700` | 126,208 | 4.916 | plaintext, **khác blob[5] 41%** |
| 8 | `0x0F5400` | 125,696 | 4.898 | plaintext, **≡ blob[6]** |
| 9 | `0x113F00` | 132,096 | 4.953 | plaintext |
| 10 | `0x134300` | 7,575,296 | 7.261 | hỗn hợp, lớn nhất |

**Đếm lại đúng:**
- 11 blob tổng
- **4 blob không nén được** (1–4), 4 nội dung khác nhau
- **6 blob plaintext** nhưng chỉ **~5 nội dung** (6 ≡ 8)
- 1 blob hỗn hợp (10)
- 1 blob dữ liệu (0)

---

## 6. Mục BLOCKED (theo mục 7.H — lập bảng phần không đọc được)

| # | Phần | Lý do BLOCKED |
|---|---|---|
| 1 | Nghĩa 4 blob entropy cao | Không nén được, không magic, không IV. **Không thể phân biệt AES vs nén** từ dữ liệu hiện có. Cần: khoá giải mã (không có trong driver công khai), hoặc mẫu plaintext đã biết |
| 2 | Disasm `blob[0]` thành code | 93.1% unknown từ 4 offset khác nhau. **Không phải code Falcon.** Cần: xác định đây là bảng gì trước |
| 3 | 24 byte khác giữa blob[6] và blob[8] | Chưa biết là version / patch / checksum |
| 4 | Entry directory chỉ có offset+size | Không có trường engine / load address → không map blob → engine nào |
| 5 | SEC2 / PMU / FECS / GPCCS riêng biệt | Không có trường nào trong container định danh engine |

**Không brute-force khoá, không trích xuất bí mật, không triển khai bypass**
(theo mục 7.J).

---

## 7. Trạng thái P4

| Mục đề bài | Trạng thái |
|---|---|
| A. Giải mã container header + entry directory | **ĐẠT** — 11 blob, offset/size/entropy đầy đủ |
| B. Architecture / metadata / version / load address | **ĐẠT MỘT PHẦN** — container OK; **load address KHÔNG có** |
| C. Tìm phần disassemble được | **ĐẠT** — thử 4 offset, 93% unknown, kết luận không phải code |
| D. Phân biệt nén / mã hoá / chữ ký / không xác định | **ĐẠT MỘT PHẦN** — chứng minh **không nén được**; chưa phân biệt AES vs nén |
| E. Startup / message queue / mailbox / interrupt | **KHÔNG LÀM** — phụ thuộc B |
| F. Đối chiếu firmware metadata với VBIOS + driver | **ĐẠT MỘT PHẦN** — kích thước khớp, không có version field |
| G. Firmware dependency graph | **KHÔNG LÀM** — không có trường engine |
| H. Bảng phần không đọc được + lý do | **ĐẠT** — mục 6 |
| I. Không giả định entropy cao = AES | **TUÂN THỦ** |
| J. Không brute-force / trích xuất bí mật | **TUÂN THỦ** |

**Coverage P4:** 11/11 blob phân loại (**100%**), 2/11 blob xác định bản chất
nội dung (**18%**), 0/11 blob disasm được thành code (**0%**).

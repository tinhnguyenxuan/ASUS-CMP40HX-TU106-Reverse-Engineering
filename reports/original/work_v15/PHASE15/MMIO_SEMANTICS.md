# PHASE15/MMIO_SEMANTICS.md — Nghĩa các mã trả về MMIO và cấu trúc BAR0

## 1. Mục tiêu

Phân tích các mã trả về khi đọc MMIO/BAR0 không decode, phân biệt các loại poison, và vẽ bản đồ cấu trúc BAR0 theo block. Không coi zero/poison là bằng chứng tuyệt đối về vắng mặt block (theo yêu cầu P4).

## 2. Dữ liệu gốc

| Trường | Giá trị |
|---|---|
| Source | `MMIO/P1_MMIO.md`, `MMIO/mmio.json`, `MMIO/registers_turing.json`, `TOPOLOGY/aperture_map.json`, `TOPOLOGY/p9_*.json` |
| Register turing trích từ source | 52 (từ 2,133 header driver 615.78.08, lọc kiến trúc) |
| Register đã đọc được | 33 (63.5%) |
| Register zero | 13 (25.0%) |
| Register poison | 6 (11.5%) |
| Trang 64 KB đã chạm | 10 / 256 (3.9%) |

## 3. Các mã trả về MMIO (DECODED)

| Mã | Số lượng | Vị trí | Ý nghĩa |
|---|---|---|---|
| `0xBADF5040` | nhiều | BAR0 (vùng ngoài decode) | **Lỗi truy cập / ngoài cửa sổ decode** — taxonomy nv-uefi-unlocker: privilege violation (PLM chặn) |
| `0xBADF1300` | 1+ | FUSE aperture | Poison fuse (không phải ngoài khối) |
| `0xBADF1301` | 1+ | Display MMIO (DISP/SOR/DAC) | Poison display |
| `0xBADF1100` | 1+ | FUSE offset ≥ `0x3814` | Poison ngoài phạm vi fuse |
| `0xBADF510C` | 7 | FUSE (vùng có dữ liệu, `0x0178`...) | **Ô fuse bị khóa** (giữa vùng có dữ liệu) |
| `0xBAD00100` | 25 trang | BAR0 `0x010000..0x01FFFF` + `0x058000..0x060FFF` | **Mã mới** — khác `0xBADFxxxx` (nửa thấp không phải mã lỗi) |
| `0xFFFFFFFF` | 72 trang | BAR0 `0x0A0000..0x0BFFFF` + `0x3D8000..0x3FFFFF` | Bus float / uninitialized |

**Phân biệt quan trọng:**
- `0xBADFxxxx`: mã lỗi cụ thể ở nửa thấp (5040 = privilege, 1300/1301 = block, 1100 = out of range, 510C = fuse khóa).
- `0xBAD00100`: **KHÔNG** thuộc họ `0xBADFxxxx` → mã trả về khác, chưa biết nghĩa chính xác → `U-MMIO-012`.
- `0xFFFFFFFF`: giá trị bus float kinh điển PCIe, nhưng ở đây nằm trong BAR0 GPU → **GPU tự trả về**, không phải bus ngoài → chưa xác nhận ai trả về.

## 4. Bản đồ cấu trúc BAR0 (áp sau P9 reclassify)

| Vùng | Trang | Nội dung | Phân loại |
|---|---|---|---|
| `0x00000..0x00FFF` | 4 | Register PMC/PBUS/PCFG... | DATA (register đọc được) |
| `0x010000..0x01FFFF` | 16 | `0xBAD00100` lặp, 16 trang giống hệt nhau | POISON mã mới |
| `0x058000..0x060FFF` | 9 | `0xBAD00100` lặp | POISON mã mới |
| `0x0A0000..0x0BFFFF` | 32 | `0xFFFFFFFF` lặp | UNINIT / bus float |
| `0x300000..0x3D7FFF` | 141 | Nhiều giá trị, entropy cao | DATA thật = VBIOS shadow |
| `0x3D8000..0x3FFFFF` | 40 | `0xFFFFFFFF` lặp | UNINIT / bus float |

**Số liệu sửa (P9):** POISON 3,278 (81.0%), DATA 141 (3.5%), ZERO 355 (8.8%), UNINIT_FF 72 (1.8%), MIXED 201 (4.9%). Tổng 4,047 trang. 49 trang nhỏ chưa phân loại.

**TU-07 (PHÁT HIỆN LỚN NHẤT):** `BAR0 0x300000` = VBIOS shadow đang chạy, khớp `rom_file[0x28600:]` **100%** (chỉ 14 byte khác = serial + part number). Serial thật: `CMP40HX-8G#REDACTED`.

## 5. Quy tắc an toàn (tuân thủ)

- Không coi zero/poison là bằng chứng tuyệt đối về vắng mặt block (mục 8.F).
- Không quét địa chỉ chưa biết nếu không xác minh an toàn.
- Chỉ đọc register đã tài liệu hoá (`mmap PROT_READ`).
- Không write probing, không quét dải chưa xác nhận.

---
**Ponytail:** phân tích dựa trên dữ liệu đã có (aperture_map.json, p9_*.json). Không viết tool mới.

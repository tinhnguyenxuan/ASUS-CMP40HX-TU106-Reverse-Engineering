# BAO CAO PHASE 15 — UNKNOWN RESOLUTION (CMP 40HX / TU106-100-A1)

**Session:** 2026-11-06 v16 · **Card:** `10DE:1F0B`, subsystem `8804:1043`, VBIOS `90.06.67.00.06`, BDF `0000:03:00.0`
**Ràng buộc:** toàn bộ phân tích offline, read-only. Không ghi MMIO/OTP/fuse, không flash VBIOS, không reload driver, không reboot, không sweep VF offset, không brute-force khoá.

---

## 1. TONG QUAT

| Muc | So luong | Trang thai |
|---|---:|---|
| Unknown tong (UNKNOWN_DATABASE.json) | 45 | 35 open, 10 resolved |
| Da giai trong P15 | 0 | Toan con unknown con lai duoc danh gia BLOCKED co ly do |
| File ra mat P15 | 10 | Xem muc 6 |
| Script moi | 3 | fuse_deep.py, gsp_find_caller.py/2, gsp_second_table.py |
| Assert self-check | verify_all.py | 162/162 PASS (giu nguyen tu v14, P15 khong them assert moi) |

---

## 2. P0 — FUSE / OTP (da giai duoc phep o du lieu co san)

### 2.1 Du lieu co ban
- Aperture thuc: `0x00021000`, span `0x1DFF` (7,680 B = 3,072 word). `0x00820000` la GB100, **khong ap TU106**.
- 352 word DATA / 518 ZERO / 2,202 POISON. 126 distinct gia tri.
- Ma poison: `0xBADF5040`, `0xBADF1300`, `0xBADF1100`.

### 2.2 Register da co ten (8/352 word = 2.3%)

| Offset | Dia tri | Gia tri | Ten | Nghia | Confidence |
|---|---|---|---|---|---|
| +0x0000 | 0x021000 | 0xC0040000 | Strap mirror / NV_PMC_BOOT_0 proxy | Khong giong exact NV_PMC_BOOT_0 (0x166000A1) | TRUNG BINH |
| +0x0378 | 0x021378 | 0x00000000 | NV_FUSE_OPT_NVDEC_DISABLE | NVDEC bat | CAO |
| +0x04D8 | 0x0214D8 | 0x00001F0B | SKU device ID | Khop PCI 10DE:1F0B | CAO |
| +0x056C | 0x02156C | 0x00001F4B | Chip family | Khop TU106 | CAO |
| +0x0650 | 0x021650 | 0x0004001F | TPC/SM config | Can bitfield | TRUNG BINH |
| +0x074C | 0x02174C | 0x00000001 | NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS | GSP debug TAT | CAO |
| +0x0C04 | 0x021C04 | 0x00000001 | NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE | Fuse bao display bat | CAO |
| +0x0C1C | 0x021C1C | 0x00000038 | GPC config | 3 bit -> 3 GPC | TRUNG BINH |

### 2.3 U-FUSE-001: 152 word = 1 — KHONG phai OTP bit cell
- Phan tan 70 range ro rang, co gaps (vi 0x011C=0 giua cac word=1).
- Tat chi co bit 0 set (0x00000001).
- Ket luan: **INFERRED enable flag / version field / counter**, khong phai OTP bit cell vat ly.
- Dieu kien mo lai: dump fuse TU106/TU104 chip khac de doi chieu pattern.

### 2.4 U-FUSE-002: fuse +0x0718 (32 byte entropy cao)
- 8 word: `57C095DC 839CF28E BF493942 51C51E03 64375730 CA078F03 E13B9D22 1E38C5B9`.
- CRC32(raw32) = `0x719E0687`, Adler32 = `0xF9630E16`. Khong khop gia tri known nao.
- Da exhaustive SHA-256/HMAC tren ROM+GSP+uCodes+chinh khoi fuse: **0 khop** (455,689 + 12,883 phep thu).
- 4 giai thuat moi: public key hash / nonce booter / chip trim / version stamp. Confidence: UNKNOWN.

### 2.5 Phan biet OTP vat ly vs shadow
- Chua coi la OTP vat ly khi co cross-check nguon doc lap (PDI khop `nvidia-smi -q`).
- `fuse+0x0000` != `NV_PMC_BOOT_0` => INFERRED strap mirror, khong phai OTP truc tiep.

---

## 3. P1 — GSP-RM (da tim caller = 0 ket qua)

### 3.1 Dispatcher (tu Q1, da xac nhan)
- Ham dispatch @`0x04F575FC`, base `0x041A70B0`, stride 32, span `0x1740` = 186 entry.
- Layout entry (doc tu code, P3 sai toan bo): `u16@0, u32@4, u8@8, u64@0x10, u16@0x18`.
- `u64@+0x10` la tham so callback (qua `a2`), KHONG phai name_ptr. Callback tu context `+0x30`, khong tu entry.
- 4 giai thuat ve `u64@+0x10` deu bi bac bo co bang chung.

### 3.2 Tim caller (offline, read-only, da lam)
- Quet toan bo `gsp_tu10x.bin` (22.9 MB):
  - `jal` truc tiep den `0x04F575FC`: **0 ket qua** (172,754 JAL).
  - `auipc`+`jalr` pair cung register targeting dispatcher: **0 ket qua** (189,928 pairs).
  - `lui` khop high 20 bit: 2 ket qua, nhung o trong khuong dispatch chinh, khong la caller tu ham khac.
- Ket luan: caller goi qua function pointer / GOT / bang dispatch. **Can Ghidra headless call graph**. (U-GSP-008, BLOCKED)

### 3.3 Callee (callback)
- `ld a5, 0x30(s3)` + `jalr a5` => callback tai context +0x30. Chua disasm duoc ham callback (can tim dia chi context).

---

## 4. P2 — VBIOS (layout da giai, 5 field van Unknown)

### 4.1 Key block: 38 record x 32 byte tai `0x003000..0x0034BF`
Layout: `sig@0, ver@2, f4@4, f8@8, flags@0xC, hash@0x10`.
- Image #1: 38 record co du lieu. Image #2: toan `0xFF` o vung nay (chua ky).

### 4.2 Field Unknown (5/6)
| Field | Offset | Gia tri mau | Trang thai |
|---|---|---|---|
| sig | +0x00 | 0x6700 x37, 0x6701 x1 | UNKNOWN |
| ver | +0x02 | 0x0200/0x0300/0x0400/0x0600 | INFERRED (version ID) |
| f4 | +0x04 | Boi so 0x20 (38/38), khong phai timestamp | INFERRED (checksum?) |
| f8 | +0x08 | 0x166xxxx, tang dan theo ver | INFERRED (build ID?) |
| flags | +0x0C | byte thap 0xF0-0xFF, byte cao 0x00/0x79 | UNKNOWN |
| hash | +0x10 | 16 byte entropy cao, khong khop SHA-256/MD5/SHA-1 (0/912) | UNKNOWN |

### 4.3 NPDS-0x70: 12 digest
- Tai `0x076800..0x078400`, 12 x 32 byte. 0 / 1,365,939 phep thu khop. UNKNOWN.

---

## 5. P3 — Firmware (11 blob da phan loai)

| # | Offset | Kich thuoc | Entropy | Nhiem nguyen |
|---|---|---|---|---|
| 0 | 0x002F00 | 122,880 | 3.481 | Du lieu, khong phai code Falcon (INFERRED) |
| 1-4 | 0x020F00..0x07AF00 | 122,880 | 7.998 | Khong nen duoc, 4 noi dung khac nhau |
| 5 | 0x098F00 | 126,208 | 4.915 | Plaintext, khac blob[7] 41% |
| 6 | 0x0B7C00 | 125,696 | 4.898 | Plaintext, **=== blob[8] (24 B khac)** |
| 7 | 0x0D6700 | 126,208 | 4.916 | Plaintext, khac blob[5] 41% |
| 8 | 0x0F5400 | 125,696 | 4.898 | Plaintext, === blob[6] |
| 9 | 0x113F00 | 132,096 | 4.953 | Plaintext |
| 10 | 0x134300 | 7,575,296 | 7.261 | Hop nhap, lon nhat |

- blob[6] ≡ blob[8]: 24 byte khac = build timestamp ASCII (`Dec 31 2024` vs `Jan 2 2025`).
- 4 blob entropy cao: **khong nen duoc** (zlib 1.001, lzma 0.999). **Khong ket luan AES** (nguyen tac C3).
- blob[0]: 93.1% lenh unknown tu 4 offset => khong phai code Falcon (INFERRED data segment).
- Can khoa giai ma de mo (BLOCKED, U-FW-001..004).

---

## 6. P4 — MMIO / Topology (poison codes da catalog)

| Ma | So luong | Vi tri | Nghia |
|---|---|---|---|
| 0xBADF5040 | nhieu | BAR0 ngoai cua so decode | Privilege violation (PLM chan) |
| 0xBADF1300/1301 | 1+ | FUSE / Display | Poison block |
| 0xBADF1100 | 1+ | FUSE offset >= 0x3814 | Out of range |
| 0xBADF510C | 7 | FUSE (vung co du lieu) | O fuse bi khoa |
| 0xBAD00100 | 25 trang | BAR0 `0x010000..0x01FFFF`, `0x058000..0x060FFF` | **Ma moi**, khac ho 0xBADFxxxx |
| 0xFFFFFFFF | 72 trang | BAR0 `0x0A0000..0x0BFFFF`, `0x3D8000..0x3FFFFF` | Bus float / uninitialized |

- TU-07: `BAR0 0x300000` = VBIOS shadow dang chay, khop `rom[0x28600:]` 100% (chi 14 byte khac). Serial that: `CMP40HX-8G#REDACTED`.

---

## 7. BLOCKED (13 item, co ly do bu)

| ID | Nhom | Ly do | Dieu kien mo lai |
|---|---|---|---|
| U-FUSE-001 | FUSE | Can dump chip khac de doi chieu 152 word=1 | Dump fuse TU106/TU104 khac |
| U-FUSE-002 | FUSE | Exhaustive hash 0 khop, khong co khoa/HMAC | ROM TU106 khac hoac source booter |
| U-FUSE-003/004 | FUSE | Khong co bitfield strap tu source | dev_fuse.h TU106 hoac Nouveau doc |
| U-GSP-004 | GSP | id khong duy tin cuc (trung VMIN_NVVDD_0) | Disasm ham consume policy |
| U-GSP-006 | GSP | 7 ten khong co entry, 0 ptr tro toi | Quet .rodata tim bang entry thu 2 (da lam, 0 ket qua) |
| U-GSP-007 | GSP | Can doc ham callback jalr a5 | Disasm ham callback (context +0x30) |
| U-GSP-008 | GSP | Caller dispatch: 0 JAL, 0 AUIPC+JALR | Ghidra headless call graph |
| U-FW-001..004 | Firmware | 4 blob ma hoa, khong co khoa | Khoa giai ma hoac plaintext-known |
| U-FW-012/013 | Firmware | 24 byte khac / blob[0] khong phai code | Source firmware hoac xac dinh bang cua |
| U-VBIOS-001/003 | VBIOS | 5 field key block + 12 digest Unknown | ROM TU106 khac hoac ham bam tu source |
| U-MMIO-012 | MMIO | 2 ma tra ve moi chua biet nghia | Tai lieu ma tra ve hoac disasm handler MMIO |
| U-BAR3-001/002 | MMIO | BAR3 chua gi / thieu 0x1F0B | Doi chieu source GMMU hoac traces driver |
| U-MEM-001 | Memory | 388.5 MiB carveout, WPR2 chi 0.5 MiB | Doc them register PFB carveout |
| U-SEC-002 | Security | PLM/ACR poison chi co tu boot log | Disasm boot code hoac tai lieu PLM/ACR |

---

## 8. FILE RA MAT (PHASE15/)

| File | Vai tro |
|---|---|
| `FUSE_SEMANTICS.md` | Giai nghia fuse/OTP chi tiet |
| `GSP_DISPATCH_ANALYSIS.md` | Phan tai dispatcher @0x04F575FC |
| `FIRMWARE_RESEARCH.md` | Nghien cuu 11 blob firmware |
| `VBIOS_UNKNOWN_FIELDS.md` | 5 field chua biet trong key block |
| `MMIO_SEMANTICS.md` | Ma tra ve MMIO va cau truc BAR0 |
| `NEW_DISCOVERIES.md` | 10 tim kiem moi (D-P15-001..010) |
| `EVIDENCE_LEDGER.md` | 15 by chung (E15-01..E15-15) |
| `BLOCKERS.md` | 13 item BLOCKED co ly do bu |
| `UPDATED_COVERAGE.md` | Coverage theo don vi he thong (khong giong ty le chung) |
| `CHECKPOINT.json` | v16, unknowns 45/35/10 |

### Script moi
- `fuse_deep.py` + `fuse_deep.json`: bit pattern, gia tri recurring, CRC32/Adler32 cua +0x0718.
- `gsp_find_caller.py/2.py` + `gsp_dispatcher_caller.json`: tim caller dispatcher (0 ket qua).
- `gsp_second_table.py` + `gsp_second_table.json`: tim bang descriptor thu 2 (0 ket qua).

---

## 8. KET LUAN

Phase 15 da giai duoc phep o du lieu co san:
- FUSE: 8/352 word co ten, 152 word=1 duoc phan biet la enable flag (khong phai OTP cell), fuse +0x0718 xac nhan khong phai hash PDI.
- GSP-RM: da xac nhan layout entry va dispatcher, nhung **khong tim duoc caller** (0 JAL/AUIPC+JALR) => can Ghidra.
- Firmware: 11 blob phan loai xong, khong ket luan AES (tuân nguyen tac C3).
- VBIOS/MMIO: layout key block va poison codes da catalog.

**Con lai 35 unknown**, toan bo duoc danh gia **BLOCKED co ly do bu** (can du lieu ngoai hoac cong cu lon hon). Khong tu khong dinh "du an hoan thanh".

**Ponytail:** bao cao tuc tac, khong them file bo sung neu khong can. Them giai thich chi khi co du lieu moi.

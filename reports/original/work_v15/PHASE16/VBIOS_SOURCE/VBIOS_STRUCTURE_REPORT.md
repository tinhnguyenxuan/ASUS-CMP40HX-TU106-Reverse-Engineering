# BAO CAO KIEM CHIEU CAU TRUC VBIOS CMP40HX/TU106 (PHASE16)

Nguon: `PHASE16/VBIOS_SOURCE/vbios_structure_verify.py` (chi stdlib, chi doc input, khong sua ROM, khong flash, khong truy cap GPU).
Ket qua chi tiet: `vbios_structure_verified.json`. Nhat chay: `vbios_structure_verify_run.log` (exitcode 0).

## 1. Input hashes (REDACTED_USER tu file thuc, khong hardcode)

| File | Kich thuoc | SHA-256 |
|---|---:|---|
| `outputs/CMP40HX_ORIGINAL_1MB.bin` | 1,048,576 B | dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec |
| `outputs/cmp40hx_t4.bin` | 495,616 B (0x79000) | aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb |
| `RAW_DATA/vbios_shadow.bin` | 1,048,576 B | 2715c0b106931b540b5ef6660201919e9297f3f5cdc61432d9a16352c55b717a |

## 2. Chu ki container va ran gioi image (phan biet hit vs ran gioi co chuong trinh)

Quet 10 chu ki: `NVGIf`, `55AA`, `PCIR`, `NPDS`, `NPDE`, `NVGI`, `RIBILU`, `PPID`, `GXIP`, `JFFS`.
Tong so hit chu ki: **64**. Chua co nao trong 64 hit duoc doan la ma hoa/chuc nang.

### 2.1 Chap nhan ran gioi image (co header + do dai + chain chuong trinh): 4

| # | Chu ki | Offset | By dau | Chung minh (header/do dai/chain) |
|---|---|---|---|---|
| 1 | `NVGIf` | 0x000000 | `4e 56 47 49 66 03 24 80` | Magic `NVGIf` + header3 `032480` giong nhau o 2 vi tri + ma `NVGIf` ke tiep khoang cach REPEAT_SPAN (0x79000) chieu toi 0x79000, noi dung 2 ban gan nhu giong het (1,212/495,616 byte khac, cuc 0x3000..0x34bf). |
| 2 | `NVGIf` | 0x079000 | `4e 56 47 49 66 03 24 80` | Cung header3, ma `NVGIf` ke tiep chieu lui toi 0x0. Hai bo dem NVGIf lap lai theo span 0x79000. |
| 3 | `55AA` | 0x028600 | `55 aa ...` | `55AA` + con tro tai +0x18 = 0x0170 tro den `PCIR` tai 0x028770 (vendor 0x10DE, device 0x1F0B). Chuoi 55AA -> con tro -> PCIR duoc chuong trinh. |
| 4 | `55AA` | 0x0a1600 | `55 aa ...` | `55AA` + con tro tai +0x18 tro den `PCIR` tai 0x0a1770. **Luyet quan trong: 0x0a1600 = 0x079000 + 0x028600, la sao chep cua header legacy o bank1 trong bank2, KHONG phai bat dau cua mot bank/doc lieu moi.** |

### 2.2 Tu chap nhan (chi hit chu ki byte, chua co header/do dai/chain): 60

Bo loai bo het 60 hit con lai (PCIR x8, NPDS x11, NPDE x13, 55AA x20 con lai, NVGI x2, RIBILU/PPID/GXIP/JFFS x5) vi chu ki duy nhat la mau byte, chua co truong do dai va chuoi lien ket chay het. Duoc liet ke day du trong `vbios_structure_verified.json` (`rejected_candidates`).

### 2.3 Sua loi ke thua tu `images()` cu

`images()` cu trong `scripts/vbios_parser.py` dat `bank1` ket thuc 0x0a1600 (660,992 B) va coi bank1/bank2 giong nhau 100%. **Bac bo:**
- Ran gioi thuc cua 2 bank la **REPEAT_SPAN = 0x79000 (495,616 B)**, duoc thuc te do `bank1[0:0x79000] ~= bank2[0x79000:0xF2000]` (1,212 byte khac, cuc duy nhat 0x3000..0x34bf).
- `0x0a1600` khong phai ket thuc bank1; no chi la vi tri header legacy copy o bank2 (0x79000 + 0x28600). Thang bao `bank1 end 0xA1600` mau thuan `repeat span 0x79000` duoc xoa bo.
- Vung sau 0xF2000 (0xF2000..0x100000, 57,344 B) la NMX container duoi (co `RIBILU`, `PPID`, `GXIP`, `JFFS`), KHONG phai toan 0xFF (51,523 byte 0xFF + 5,201 byte 0x00 + cac byte khac).

## 3. BIT table (17 token) — parse tu raw bytes, nguyen ban con tro

Vi tri: 0x0287B0 (trong legacy1). Header: 12 B, buoc 6 B, so token 17. Kich thuc 114 B, ket thuc 0x028822.
Cong thuc con tro (Turing, luu giong nguyen ban va danh dau dan su): `file_off = ROM_IMG(0x28600) + ptr + (EFI_SZ(0x11000) neu ptr >= LEGACY_SZ(0xF400) else 0)`; `ptr == 0` duoc anh xa ve co so hinh anh ROM (0x028600). Cong thuc nay DUOC KHIEN BAO la da ke thua tu Turing, KHONG phai trinh trinh chung minh chung.

| Idx | Token | Ver | Len | Raw ptr | Mapped offset | Null | In bounds |
|---:|---|---:|---:|---:|---|---:|---:|
| 0 | 0x32 (2) | 1 | 4 | 562 | 0x028832 | 0 | co |
| 1 | 0x42 (B) | 2 | 37 | 574 | 0x02883e | 0 | co |
| 2 | 0x43 (C) | 2 | 44 | 611 | 0x028863 | 0 | co |
| 3 | 0x44 (D) | 1 | 4 | 655 | 0x02888f | 0 | co |
| 4 | 0x49 (I) | 1 | 36 | 659 | 0x028893 | 0 | co |
| 5 | 0x4d (M) | 2 | 29 | 695 | 0x0288b7 | 0 | co |
| 6 | 0x4e (N) | 0 | 0 | 0 | 0x028600 | 1 (ptr==0) | co |
| 7 | 0x50 (P) | 2 | 224 | 724 | 0x0288d4 | 0 | co |
| 8 | 0x53 (S) | 2 | 24 | 948 | 0x0289b4 | 0 | co |
| 9 | 0x54 (T) | 1 | 2 | 972 | 0x0289cc | 0 | co |
| 10 | 0x55 (U) | 1 | 5 | 974 | 0x0289ce | 0 | co |
| 11 | 0x56 (V) | 1 | 6 | 979 | 0x0289d3 | 0 | co |
| 12 | 0x78 (x) | 1 | 8 | 985 | 0x0289d9 | 0 | co |
| 13 | 0x64 (d) | 1 | 2 | 993 | 0x0289e1 | 0 | co |
| 14 | 0x70 (p) | 2 | 4 | 995 | 0x0289e3 | 0 | co |
| 15 | 0x75 (u) | 1 | 13 | 999 | 0x0289e7 | 0 | co |
| 16 | 0x69 (i) | 2 | 104 | 1012 | 0x0289f4 | 0 | co |

- Tong: **17 token**, 1 null pointer (token 0x4e, ptr=0), 0 token ngoai pham vi.
- Ung dung cua con tro: token 0x50 (P) tro toi 0x0288d4 chinh la vi tri PERF pointer slot (vong lap ky tu). Token 0x4e (N) ptr=0 tro ve 0x028600 (co so legacy image).
- Nghia cua tung ma token (0x32, 0x42, ...) chua duoc nguon dich -> **UNKNOWN** (liet ke tuy nhien, khong bo sot).

## 4. PERF con tro va bang (56 slot, 40 bang)

Vi tri PERF pointer slot: 0x0288D4, 56 slot x 4 B.
- 40 slot co con tro khac 0, 16 slot null.
- Tat ca 40 con tro duoc giai header (ver/hdr_size/esz/count, kich thuc = hdr + esz*count), tat ca trong pham vi ROM (in bounds), 0 truncation.
- **Tat ca 40 bang co header hop ly nhan `semantic_status = UNKNOWN`**: header shape khong xac dinh nghia bang. Khong ep mot dinh dang header chung cho tat ca bang roi goi la da giai ma.

Bang PERF (idx, raw ptr, offset, ver, hdr, esz, cnt, size, ket thuc):
02 0x01AB55 0x054155 v96 h10 e5  c7  sz45  end 0x054182
01 0x01B000 0x054600 v17 h26 e60 c33 sz2006 end 0x054dd6  <-- bang lon nhat
02 0x01BAC4 0x0550C4 v32 h6 e74 c12 sz894  end 0x055442
05 0x01F123 0x058723 v16 h4 e3  c18 sz58   end 0x05875d
08 0x01CE9C 0x05649C v48 h9 e25 c20 sz509  end 0x056699  <-- VFE bien (20 var x 25 B)
10 0x01E3E0 0x0579E0 v32 h8 e49 c7  sz351  end 0x057b3f
11 0x01E892 0x057E92 v48 h44 e66 c20 sz1364 end 0x0583e6
14 0x01AD26 0x054326 v32 h19 e1  c17 sz36   end 0x05434a
15 0x01E53F 0x057B3F v32 h6 e22 c20 sz446  end 0x057cfd
16 0x01EF61 0x058561 v16 h5 e25 c11 sz280  end 0x058679
17 0x01AFF2 0x0545F2 v16 h14 e70 c183 sz12824 end 0x05780a  <-- chua cac bang nho (xem overlap duoi)
18 0x01F15D 0x05875D v16 h9 e5  c32 sz169  end 0x058806
19 0x01F206 0x058806 v16 h4 e5  c2  sz14   end 0x058814
20 0x01F079 0x058679 v16 h10 e40 c4  sz170  end 0x058723
22 0x01F224 0x058824 v16 h6 e26 c2  sz58   end 0x05885e
23 0x01F25E 0x05885E v16 h6 e54 c2  sz114  end 0x0588d0
25 0x01F2D0 0x0588D0 v16 h4 e5  c2  sz14   end 0x0588de
26 0x004D7B 0x02D37B v16 h5 e14 c1  sz19   end 0x02d38e
27 0x004D17 0x02D317 v16 h4 e24 c4  sz100  end 0x02d37b
28 0x004D8E 0x02D38E v16 h5 e17 c1  sz22   end 0x02d3a4
29 0x01CC22 0x056222 v16 h6 e7  c5  sz41   end 0x05624b
30 0x01CC4B 0x05624B v16 h5 e12 c5  sz65   end 0x05628c
31 0x01CC8C 0x05628C v16 h4 e13 c5  sz69   end 0x0562d1
32 0x01CCD1 0x0562D1 v16 h10 e5  c5  sz35   end 0x0562f4
33 0x01CCF4 0x0562F4 v16 h7 e15 c5  sz82   end 0x056346
34 0x01CD46 0x056346 v16 h14 e5  c5  sz39   end 0x05636d
35 0x01CD6D 0x05636D v16 h58 e5  c5  sz83   end 0x0563c0
36 0x01CDDC 0x0563DC v48 h9 e4  c2  sz17   end 0x0563ed
37 0x01F214 0x058814 v16 h4 e2  c6  sz16   end 0x058824
38 0x01F2DE 0x0588DE v16 h6 e5  c2  sz16   end 0x0588ee
39 0x01CDED 0x0563ED v16 h6 e24 c5  sz126  end 0x05646b
40 0x01F2F8 0x0588F8 v16 h4 e19 c18 sz346  end 0x058a52
41 0x01F452 0x058A52 v16 h7 e5  c18 sz97   end 0x058ab3
42 0x01F4B3 0x058AB3 v16 h6 e24 c8  sz198  end 0x058b79
43 0x01F579 0x058B79 v16 h5 e10 c8  sz85   end 0x058bce
44 0x01F704 0x058D04 v16 h4 e6  c4  sz28   end 0x058d20
45 0x01F720 0x058D20 v16 h4 e29 c8  sz236  end 0x058e0c
46 0x01F5CE 0x058BCE v16 h4 e13 c2  sz30   end 0x058bec
47 0x01CE6B 0x05646B v16 h4 e9  c5  sz49   end 0x05649c
48 0x01CDC0 0x0563C0 v16 h8 e4  c5  sz28   end 0x0563dc

### 4.1 Overlap / truncation (thuc te, khong bo sot)

- Truncation: 0 bang (tat ca ket thuc <= 1 MB).
- Bang xoa BIT table: 0 (BIT o [0x0287B0, 0x028822], cac bang PERF o >= 0x02d317).
- **Bang-bang overlap: 14 cap**. Bang idx 17 (khoang [0x0545F2, 0x05780A]) chua/chong len cac bang idx 1, 29, 30, 31, 32, 33, 34, 35, 36, 39, 47, 48; bang idx 1 chong len bang idx 17. Nghia: con tro PERF nhieu chi tro vao vung noi cung cua mot cau truc lon (bang 17), khong phai 40 bang doc lap hoan toan. Duoc liet ke day du trong JSON (`table_table_overlaps`). Semantic cua bang 17 va cac bang con = UNKNOWN.

## 5. Block record NVGI/key (38 record x 32 B)

Vi tri bank1: 0x03000..0x034BF (1,216 B). Layout record (32 B): sig(2), ver(2), f4(4), f8(4), fc/flags(4), hash16(16).
- Bank1: 38/38 record co du lieu (khong nao toan 0xFF).
- Bank2 (0x079000+0x03000 = 0x07C000): 0/38 record co du lieu, toan bo `0xFF`.
- Sig: 0x6700 (37 record), 0x6701 (1 record, idx 0). Ver: 0x0200 (2), 0x0300 (16), 0x0400 (16), 0x0600 (4).
- `f4` luon la boi so cua 0x20 (38/38). `f8` co 10 gia tri nhom (`0x166xxxxx` / `0x1687xxxx`), tang theo `ver`. `fc` flags byte cao `0x00`/`0x79`, byte thap `0xF0-0xFF`.
- `f4` KHONG phai unix timestamp (chu 9/38 o trong 2000..2030, con lai vo ly 1972-2102). `f4` khong phai offset (max 0xF9FC88A0 > kich thuc file).
- 16-byte hash: **chua biet la ma gi**. Thu SHA-256/SHA-1/MD5/SHA-384 cua 6 vung ROM x 38 record = 0/912 khop (duoc kiem tra o `TOOLS/nvgi_block.py`).
- Tat ca 5 field con lai (`sig` nghia, `f4`, `f8`, `flags` nhom, `hash16`) = **UNKNOWN**. Gan trung hop voi fuse `0x00D4..0x00F4` chua duoc chuong trinh.

## 6. Hai vung lap lai (bank1 vs bank2) theo span thuc

- Span: **0x79000 (495,616 B)** (denominator), khong ke thua tu `images()` cu.
- Bank1: `rom[0x00000:0x79000]` (= payload T4). Bank2: `rom[0x79000:0xF2000]`.
- Byte khac: **1,212 / 495,616 = 0.245%**.
- Cuc khac: **duy nhat 1 cuc [0x3000, 0x34bf]** (1,216 B, 1,212 byte khac, 4 byte giong nhau trong cuc).
- Nghia: image #1 (bank1) co 38 record key tai 0x3000; image #2 (bank2) vung cung vi tri toan `0xFF` -> mot ban da khoi tao, mot ban chua, KHONG phai hai ban sao redundant giong nhau 100%.
- Sau 0xF2000 (0xF2000..0x100000): NMX container duoi, khong toan 0xFF.

## 7. Original vs T4 (shared-prefix difference)

- T4 = `rom[0:0x79000]` voi **19 byte thay doi** (denominator 495,616), 18 byte o `[0x5669C, 0x566BE]` + 1 byte checksum tai `0x767FF`.
- 18 byte thay doi o 6 truong float32 (cac copy cua nvvdd REL/ALT c0/c1/c2) nam o VFE slot base 0x56699 buoc 24.
- Byte `0x767FF` (cuoi NPDS_E0_2) duoc sua` de tong image chia het 256: `new = (old - sum(t4[i]-rom[i] for 18 byte thay doi)) mod 256`. ROM=0x33, T4=0xE5.
- Ngoai 19 byte nay, `rom[0:0x79000] == T4` hoan toan (khong co byte khac nao).
- **Ket luan: T4 khong match 100% voi prefix ROM; co 19 byte khac, da liet ke day du.**

## 8. Shadow (BAR0 0x300000) vs ROM container [0x28600:]

- Shadow bat dau bang `55AA` (legacy header thuc), PCIR tai shadow offset 0x170 (vendor 0x10DE, device 0x1F0B, classcode 0x030200) -> khop the TU106 CMP 40HX.
- Duch qua: **shadow[0:883,200] vs rom[0x28600:1,048,576]**, denominator **883,200 B**.
- **Byte khac: 14 / 883,200 (khong phai 100% match). Ty le khop 0.999984.**
- 14 byte khac (chi duoc lay tu shadow chay thuc, in ra day du):
  - `0x0D1A88`: shadow 0x04 vs rom 0x05 (rom off 0x0FA088)
  - `0x0D1A9A`: shadow 0x0D vs rom 0x0C (rom off 0x0FA09A)
  - `0x0D1C88`: shadow 0xE1 vs rom 0xD1 (rom off 0x0FA288)
  - `0x0D1CB0..0x0D1CB5`: shadow `02513` vs rom `304974` (PPID serial, rom off 0x0FA2B0..0x0FA2B5)
  - `0x0D5A1A`: shadow 0x11 vs rom 0x19 (rom off 0x0FE01A)
  - `0x0D5B30..0x0D5B35`: shadow `02513` vs rom `304974` (PPID ban sao, rom off 0x0FE130..0x0FE135)
- Serial card chay thuc (tu shadow): `CMP40HX-8G#REDACTED`. Serial ROM file: `CMP40HX-8G#REDACTED`. Serial xuat hien 2 lan (OEM section + ban sao).
- Byte `0x04` vs `0x05` tai +0xD1A88 va `0x11` vs `0x19` tai +0xD5A1A: chua biet nghia (co the image index/flags/checksum) -> UNKNOWN.
- **Ket luan: VBIOS shadow chay thuc giong ROM container tai offset 0x28600 ngoai 14 byte (serial + 3 byte khac). ROM file bat dau bang `NVGIf` (container), image legacy thuc nam o 0x28600.**

## 9. Phan biet DECODED / source-backed / UNKNOWN

| Thuoc REDACTED_USER | Trang thai | Can su |
|---|---|---|
| Cac ran gioi container (2 x NVGIf, 2 x 55AA legacy) | DECODED | header + do dai + chain chuong trinh tu raw bytes |
| BIT header (12/6/17) + 17 token + con tro nguyen ban | DECODED (cau truc) | parse tu raw; cong thuc anh xa da ke khai la Thuan (chua chung minh chung) |
| Cong thuc anh xa con tro BIT | Da ke khai (Thuan) | khong co tai lieu Thuan trong tay |
| 40 bang PERF header/extent | DECODED (cau truc) | parse tu raw header |
| Semantic tat ca 40 bang PERF | UNKNOWN | chua co nguon dich field |
| 38 record key block + layout | DECODED (cau truc) | parse tu raw 32 B |
| sig/f4/f8/flags/hash16 nghia | UNKNOWN | 0/912 bam khop; f4 khong phai timestamp/offset |
| 14 byte shadow khac (serial) | DECODED (gia tri) | doc tu shadow thuc |
| Nghia byte 0x04/0x05, 0x11/0x19 | UNKNOWN | chua co nguon dich |
| NMX container duoi (0xF2000..) | UNKNOWN (cau truc bo con) | co chuoi RIBILU/PPID/GXIP/JFFS, chua giao dich |

**Khong suy ket thuc hop/ma hoa tu entropy hoac checksum.** Tong byte chia het 256 (checksum 0) ve nhieu vung chi chung minh REDACTED_USER toan du lieu luu tru, khong chung minh xac thuc, ma hoa, hoac su dung thuc te. Toan bo ket luan xuat phat tu raw byte, khong query GPU, khong flash, khong doi fuse/MMIO/PCI config.

## 10. So dem thuc (REDACTED_USER lai tu output cua chay nay)

- Hinh anh: 1 ROM container (1 MiB) + 2 bo dem NVGIf (2 x 0x79000) + 1 NMX duoi (0xF2000..0x100000)
- Token BIT: 17 (1 null)
- Con tro PERF: 56 slot (40 non-null, 16 null); bang duoc giai: 40; header hop ly: 40; bang-bang overlap: 14 cap; truncation: 0
- Record key: 38 o bank1 (co du lieu), 0 o bank2 (toan 0xFF)
- Bank lan lai: 1,212/495,616 byte khac (denominator), cuc [0x3000, 0x34bf]
- Original/T4: 19/495,616 byte khac (denominator), [0x5669C..0x566BE] + 0x767FF
- Shadow vs ROM[0x28600:]: 14/883,200 byte khac (denominator), **khong phai 100%**
- Chu ki hit: 64; chap nhan ran gioi: 4; tu chap nhan: 60

## 11. Vung chua biet (UNKNOWN, khong bo sot)

1. NMX container duoi `0xF2000..0x100000` (cau truc bo con, serial PPID o day).
2. 16-byte hash cua 38 record key block (chua biet la ma gi).
3. Nghia cac field key block (`sig`, `f4`, `f8`, `flags`, `hash16`).
4. Semantic tat ca 40 bang PERF (bao cac bang 17 chua cac bang khac).
5. Nghia ma token BIT (0x32, 0x42, ...).
6. Cong thuc anh xa con tro BIT (da ke khai Thuan, chua co tai lieu).
7. Nghia byte shadow khac: `0x04/0x05` (+0xD1A88), `0x11/0x19` (+0xD5A1A).
8. PGRAPH aperture thuc (0x400000 tra poison) - duoc xoa khoi pham vi VBIOS nhan lai o phan khac.

## 12. Lenh sinh lai

```
python3 /home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_SOURCE/vbios_structure_verify.py
sha256sum /home/REDACTED_USER/codex-work/work_v15/outputs/CMP40HX_ORIGINAL_1MB.bin /home/REDACTED_USER/codex-work/work_v15/outputs/cmp40hx_t4.bin /home/REDACTED_USER/codex-work/work_v15/RAW_DATA/vbios_shadow.bin
python3 /home/REDACTED_USER/codex-work/work_v15/scripts/test_parser.py
python3 /home/REDACTED_USER/codex-work/work_v15/scripts/verify_diff.py /home/REDACTED_USER/codex-work/work_v15/outputs/CMP40HX_ORIGINAL_1MB.bin /home/REDACTED_USER/codex-work/work_v15/outputs/cmp40hx_t4.bin
```

## 13. Trang thai hoan toan

- Da chay script thuc, luu stdout/stderr/exitcode vao `vbios_structure_verify_run.log` (exitcode 0).
- `vbios_structure_verified.json` da luu truoc bao cao.
- Toan so dem trong bao cao REDACTED_USER tu output chay, khong hardcode.
- Khong tuning, khong sua ROM, khong danh dau toan bo GPU hoan toat. Full GPU reverse engineering **CHUA HOAN TAT**; 8 vung/field con lai danh da la UNKNOWN.

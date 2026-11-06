# RUN LOG — SECURITY_ARCH (Phase 16, CMP40HX/TU106)

Ngay chay: 2026-11-04. Môi trường: offline, read-only, không chạm phần cứng.

## Lệnh đã chạy

```
/usr/bin/python3 /home/REDACTED_USER/codex-work/work_v15/PHASE16/SECURITY_ARCH/verify.py
```

Thư mục làm việc: `/home/REDACTED_USER/codex-work/work_v15/PHASE16/SECURITY_ARCH/`

## Nguồn đầu vào (read-only)

- `/tmp/nvsrc` — xep lan NVIDIA open-gpu-kernel modules (15 file source duoc katalog)
- `work_v15/SECURITY/security_registers.json` — do MMIO + dmesg (17 register, 5 poison)
- `work_v15/PHASE16/fuse_audit.json` — dump fuse 3072 word, 352 DATA / 518 ZERO / 2202 POISON
- `work_v15/PHASE16/firmware_container_verified.json` + `FIRMWARE_CONTAINER_VERIFIED.md` — container ucodes_tu10x.bin (8,837,632 B, 38 payload)
- `work_v15/PHASE16/GSP_AUDIT.md` — GSP/RM audit (descriptor table, WPR, decoder)
- `work_v15/PHASE15/FUSE_SEMANTICS.md` + `BAO_CAO_PHASE15.md` — khuoc noc fuse/OTP truoc do (can kiem toan)

## Buoc thuc hien (verify.py)

1. Katalog 15 file source tu `/tmp/nvsrc`, REDACTED_USER SHA256 tung file → `source_provenance.json`
2. Trich xuat 2 dinh nghia fuse tu `dev_fuse.h` tu102 (dong 26, 31) → `source_facts.json`
3. Trich xuat thiet lap WPR meta (magic, verified, kich thuoc 256 byte) tu `gsp_fw_wpr_meta{,_v1}.h`
4. Trich xuat kenh SEC2 EMEM (channel 0, 1024 byte) tu `sec2_emem_channels.h`
5. Trich xuat doi so khoi dong GSP (`GSP_ARGUMENTS_CACHED`, `WPR_ALIGNMENT=128K`) tu `gsp_init_args.h`
6. Xac nhan booter co metadata chu ky (SIG_DBG/SIG_PROD) tu `cmp40_booter_load_610.h`
7. Doc do MMIO + dmesg tu `security_registers.json` → `measured_facts.json` (WPR2 LO/HI, PLM, ACR token, IOMMU, DMA, CC)
8. Xay dung `boot_chain.json` (12 buoc tu dmesg + vai tro firmware tu source)
9. Xay dung `privilege_boundaries.json` (7 ran gioi)
10. Kiem toan 23 khuoc noc truoc (FUSE/WPR/PLM/FW/SEC-SB/DMA/CC) → `audit_prior_claims.json` (3 SUPPORTED, 4 MEASURED, 13 REJECTED, 2 INFERRED, 1 UNKNOWN)
11. Giu nguyen 15 unknown → `unknowns.json`
11. Chay 19 assertion, tat ca PASS → `run_summary.json`, `assertions.log`
12. Xuat `REPORT.md` va `run_log.md`

## Ket qua chay

```
assertions_pass: true
assertions_total: 19
failures: []
audit_items: 23
  SUPPORTED: 3   (NVDEC_DISABLE, GSP_DEBUG_DIS, WPR2=0.50 MiB)
  MEASURED:  4   (PDI khop nvidia-smi, firmware ky/phuc hoi, SEC2 DMEM xoa, DMA/IOMMU)
  REJECTED:  13  (4 vung WPR, 0x1FA820=WPR2_LO, PLM tu BAR0, 11 blob, entropy=AES, driver ky, CC bat, 6 fuse ten chua co trong source, 152 word==1 la OTP cell)
  INFERRED:  2   (offset 0x0000 strap mirror, 0xBADF510C)
  UNKNOWN:   1   (fuse +0x0718 32 byte)
```

## Tap tin xuat ra (PHASE16/SECURITY_ARCH/)

| Tap tin | Kich thuoc | Vai tro |
|---|---|---|
| `verify.py` | 29,816 B | Script sinh toan bo by chung |
| `run_summary.json` | 333 B | Tom tgat chay |
| `assertions.log` | 2,182 B | Nhat ky assertion chi tiet |
| `source_provenance.json` | 2,991 B | 15 file source + SHA256 + dong |
| `source_facts.json` | 928 B | 31 su thiet lap tu source |
| `measured_facts.json` | 838 B | 16 su thiet lap tu do/dmesg |
| `fuse_source_mapping.json` | 477 B | Anh xa 2 fuse register tu source |
| `boot_chain.json` | 5,413 B | Chuoi boot 12 buoc + vai tro firmware |
| `privilege_boundaries.json` | 2,072 B | 7 ran gioi + WPR2 + SEC2 + CC + DMA |
| `audit_prior_claims.json` | 8,651 B | 23 khuoc noc kiem toan |
| `unknowns.json` | 1,848 B | 15 unknown + 4 yeu cau mo lai |
| `REPORT.md` | 13,120 B | Bao cao chinh |
| `run_log.md` | (nay) | Nhat ky chay |

## Xac nhan tai sao noi duoc

- Tat ca du lieu trong cac file JSON duoc sinh bang `verify.py` tu source `/tmp/nvsrc` + bao cao luu, khong do dan.
- 19 assertion tat ca PASS, bao gom: 2 fuse dinh nghia o dong chinh xac, WPR2 LO/HI khop MMIO va dmesg, kich thuoc WPR2 = 0x80E00 (0.50 MiB), container firmware = 38 payload/496 record, CC tat, IOMMU = 31, DMA = 47 bit, driver chua ky (taint).
- Khong co tac dong phan cứng, khong ghi MMIO/fuse/PCIe, khong flash ROM, khong trich xuat khoa, khong bruteforce.

## Buoc tiep theo (neu nguoi de yeu)

1. Dump fuse tu chip TU106/TU104 khac de do chieu pattern 152 word==1 (U-FUSE-001).
2. Tai lieu PLM/ACR hoac disasm ma boot de giai quyet PLM/ACR poison (U-SEC-002).
3. Bo nguon firmware hoac plaintext-biet de xac dinh ISA payload (U-FW-001..004).
4. ROM TU106 khac de xac nhan PDI/+0x0718 (U-FUSE-002).
5. Xac dinh nguoi goi dispatcher GSP (can tool call graph ngoai pham vi read-only file).

# BAO CAO SECURITY_ARCH — CMP40HX / TU106 (Phase 16)

Ngay thuc hien: 2026-11-04. Moi truong: chi doc file, khong chot GPU, khong ghi MMIO/fuse/PCIe, khong flash/nap ROM, khong reload driver, khong reboot, khong ep xuong/tang ap, khong thuc hien exploit/bat thoai/trich xuat khoa/bruteforce/nap ROM/ghi vet lam.

Nguon chinh: `/tmp/nvsrc` (xep lan NVIDIA open-gpu-kernel modules) + bao cao luu cu trong `work_v15/PHASE16/` va `work_v15/SECURITY/`. Tat du lieu duoc sinh lai boi `verify.py` (chay duy nhat, 19/19 assertion PASS).

---

## 1. Chuoi boot va vai tro firmware (BOOT CHAIN / FIRMWARE ROLES)

### 1.1 Vai tro duoc dinh nghia trong source (SOURCE DEFINED)

| Vai tro | Nguon duong dan | Dong | Vai tro trong chuoi |
|---|---|---|---|
| GSP-RM | `nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta.h` | struct GspFwWprMeta | FW resource manager RISC-V, chay trong WPR2. `gspFwOffset` / `gspFwHeapOffset` nam trong WPR2. |
| GSP-RM | `nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta_v1.h` | toan tap | Dung cho Booter (Turing den Ada). `magic=0xdc3aae21371a60b3`, `verified=0xa0a0a0a0a0a0a0a0`, kich thuoc dung la 256 byte. |
| Booter | `nvidia/src/kernel/gpu/gsp/cmp40_booter_load_610.h` | header | CMP40 Booter Load tu bo 610.57.04. Chua IMAGE/HEADER/SIG/PATCH/NUM_SIGS. Co metadata chu ky (SIG_DBG/SIG_PROD 16 byte). |
| SEC2 | `nvidia/arch/nvalloc/common/inc/sec2/sec2_emem_channels.h` | 34-39 | Kenh EMEM cua SEC2. `SEC2_EMEM_CHANNEL_RM = 0`, kich thuoc 1024 byte. NVDM qua MCTP qua EMEM giua phan quan ly SEC2 va CPU-RM/khac. |
| GSP init | `nvidia/inc/kernel/gpu/gsp/gsp_init_args.h` | 60-113 | `GSP_ARGUMENTS_CACHED` (magic `'G'<<24\|'S'<<16\|'P'<<8\|' '`, <=4KB). `vbiosOverrideArgs`, `bindataArgs`, `messageQueueInitArguments` (co cipher flag 0x01). `WPR_ALIGNMENT = RM_PAGE_SIZE_128K`. |
| Falcon | `nvidia/inc/kernel/gpu/falcon/falcon_common.h` | 33-44 | `FLCN_IMEM_ACCESS_ALIGNMENT=4`, `FLCN_DMEM_ACCESS_ALIGNMENT=4`, `FALCON_IMEM_BLKSIZE2=8`, `FALCON_DMEM_BLKSIZE2=8`. |
| PMU | `nvidia/inc/kernel/gpu/pmu/kern_pmu.h` | stub | Chua `g_kern_pmu_nvoc.h`; khong co gia tri register PMU duoc doc tren the nao nay. |
| SEC2 ctx | `nvidia/inc/kernel/gpu/sec2/sec2_context.h` / `kernel_sec2.h` | stub | Chua nvoc metadata; class TSEC cho gui kenh. |

### 1.2 Chuoi boot duoc do tu dmesg (MEASURED, khong duoc xac thuc tu register BAR0)

1. `t=4.754` `_kgspCreateSignatureMemdesc` — "signed fullspeed stock-relock WPR-down commit"
2. `t=4.864` `kgspBootstrap_TU102: POST_FWSEC_PRE_GSP_ENTRY` — WPR=01ffee00:01ffe000, FECS=ffffff8f, RESET=000000ff
3. `t=4.864` `_kgspCmp40ExecuteBooterFreshMeta` — fresh WPR metadata phys=0x8efde000, signature=0xffe40000, size=0xfa00
4. `t=4.892` `kgspBootstrap_TU102: WPR_META_BEFORE_RESET / INPUT_RESET_PASS` — bootCount=0, verified=0
5. `t=4.892` `kgspCmp40SanitizeSec2AfterExploit: NATIVE_CLEANUP_DMEM_PRESERVED_PASS`
6. `t=4.892` `kgspBootstrap_TU102: FULLSPEED_STOCK_RELOCK_WPR_DOWN_HANDOFF_PASS` — WPR xoa, giao nhiem vu cho GSP
7. `t=4.892` `kgspBootstrap_TU102: TOKEN_RELEASE_RESETPLM_FF_PHASE_BOUNDARY_PASS` — ran gioi han PLM
8. `t=4.956` `kgspBootstrap_TU102: REFWSEC_STOCK_WPR_PASS` — phuc hoi WPR
9. `t=4.956` `kgspBootstrap_TU102: RISCV_MODE_BOOTARGS_PASS` — tham so bo RISC-V
10. `t=4.956` `kgspBootstrap_TU102: POST_FWSEC_PRE_GSP_HANDOFF_PASS` — giao nhiem vu GSP cuoi cung
11. `t=4.958` `s_clearCmp40Sec2ExploitDmem: FULL_DMEM_ZERO_PASS [0x0,0x10000)` — xoa toan bo 64 KB DMEM cua SEC2
12. `t=5.005` `kgspBootstrap_TU102: INPLACE_STOCK_BOOTER_AFTER_UNLOCK_PASS` — stock relock

**Phan biet:** buoc 1-2 (FWSEC) chay truoc GSP. Buoc 6 (WPR-down) va buoc 8-9 (phuc hoi WPR + boot args RISC-V) xay ra khi GSP duoc khoi dong. Buoc 11-12 xoa SEC2 DMEM sau khi xong va relock. Chuoi 5 buoc duoc xac nhan trong bao cao cu (P8) va duoc luu lai o day voi muc `MEASURED`.

---

## 2. Ran gioi quyen (PRIVILEGE BOUNDARIES)

| Ran gioi | Nguon kiem soat | Xac thuc? | Doc duoc? | Ly do |
|---|---|---|---|---|
| Host <-> Driver | Kernel Linux | KHONG | co | Driver chua ky (taint); Secure Boot tat o host. |
| Driver <-> GSP-RM | API chinh thuc (GSP_ARGUMENTS_CACHED) | CO | co | ABI magics, <=4KB, truyen tham so xuong GSP. |
| GSP-RM <-> FWSEC | PLM | CO | chi log | FECS_PLM=0xFFFFFF8F tu dmesg. |
| GSP-RM <-> SEC2 | PLM + token | CO | chi log | ACR_TOKEN=0xC2 tu dmesg. |
| GSP-RM <-> Silicon | PLM + WPR | CO | phan | WPR2 khoa anh GSP trong FB. |
| Silicon <-> VRAM | WPR2 | CO | KHONG | WPR2 = 0x01F7E000..0x01FFEE00, 0.50 MiB, khong doc duoc tu host. |
| DMA <-> He thong | IOMMU | CO | co | Nhom IOMMU 31 (rieng), mask DMA 47 bit. |

**WPR2 (duoc doc ca 2 nguon):**
- MMIO `0x1FA824` (NV_PFB_PRI_MMU_WPR2_ADDR_LO) = `0x01F7E000`
- MMIO `0x1FA828` (NV_PFB_PRI_MMU_WPR2_ADDR_HI) = `0x01FFEE00`
- Kich thuoc = `0x01FFEE00 - 0x01F7E000` = `0x80E00` = **515.5 KiB ≈ 0.50 MiB**
- Khop dmesg `WPR=01ffee00:01f7e000` 100%.
- Khong phai 457 MiB (bao cao cu sai lan).

**PLM (chi tu dmesg, BAR0 bi poison):**
- FECS_PLM = `0xFFFFFF8F` (8 bit thap = cap quyen; bit 7 = an toan)
- RESET_PLM = `0x000000FF` (mo tat ca 8 cap khi reset)
- Register `0x1FA840` / `0x1FA844` doc duoc `0xBADF5040` (poison) → khong doc duoc tu BAR0.

**Confidential Computing: TAT.** Total/Used/Free = 0 MiB. GPU Virtualization Mode = None.

**DMA:** IOMMU nhom 31 (rieng the), mask 47 bit (128 TB), BAR1 64 GiB.

---

## 3. Chung tu boot an toan va WPR (SECURE BOOT / WPR EVIDENCE)

| Muc | Trang thai | Chung |
|---|---|---|
| Chuc ky driver Linux | BAC BO | dmesg: "module verification failed: signature and/or required key missing - tainting kernel". Secure Boot tat o host. Rang quyen o lop host, khong phai GPU. |
| Chuc ky firmware GPU | CO + phuc hoi in-place | dmesg: `_kgspCreateSignatureMemdesc` (signed), `kgspCmp40RebuildStockSignature` (restored stock signature in-place). Booter header co SIG_DBG/SIG_PROD (16 byte) tu bo 610.57.04. |
| WPR metadata nap 2 lan | DUOC DO | lan 1: phys=0x8efde000, sig=0xffe40000, size=0xfa00 (64 KB); lan 2: size=0x1000 (4 KB, advertised). backing=0xfa00. |
| SEC2 DMEM xoa | DUOC DO | `s_clearCmp40Sec2ExploitDmem: FULL_DMEM_ZERO_PASS [0x0,0x10000)` — xoa 64 KB sau su dung. |
| GSP debug fuse | TAT | `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS` (0x2174C, bit 0) = 1 → GSP debug bi tat. |

**WPR metadata (GspFwWprMetaV1, source):** toan cau 256 byte, `magic=0xdc3aae21371a60b3`, `verified=0xa0a0a0a0a0a0a0a0` (0 = chua xac thuc), mo ta layout FB (gspFwOffset, bootBinOffset, frtsOffset, gspFwWprStart/End, fbSize). Dung boi Booter de xac thuc va khoa trong WPR2.

---

## 4. Ket qua kiem toan cac khuoc noc truoc (AUDIT PRIOR CLAIMS)

Tong 23 khuoc noc duoc kiem toan chuong `source_facts.json` + `audit_prior_claims.json`:

- **SUPPORTED (3):** NVDEC_DISABLE tai 0x21378 (bit 2:0 = 0 → NVDEC bat); GSP_DEBUG_DIS tai 0x2174C (bit 0=1 → GSP debug tat); WPR2 = 0.50 MiB khop MMIO + dmesg.
- **MEASURED (4):** PDI `0x0000000000000000` khop nvidia-smi; firmware duoc ky + phuc hoi in-place; SEC2 DMEM xoa 64 KB; DMA/IOMMU group 31 + mask 47-bit.
- **REJECTED (13):** (a) 4 vung WPR (WPR0/WPR1/WPR2/WPR2-alt) — source chi dinh 1 cap WPR2; (b) 0x1FA820 la WPR2_LO — khong co register tai dia chi nay; (c) PLM doc duoc tu BAR0 0x1FA840/44 — ca 2 bi poison; (d) firmware 11 blob — byte parse thuc te la 38 payload (header 24 B, 496 record x 24 B); (e) entropy cao = AES — khong the phan biet ma hoa vs nen, khong co IV/magic/nguon; (f) driver co chu ky hop le — chua ky, taint; (g) Confidential Computing dang hoat dong — tat, 0 MiB; (h) fuse+0x04D8 la "SKU device ID" — khong dinh nghia trong source; (i) fuse+0x056C la "chip family" — khong dinh nghia; (j) fuse+0x0650 la "TPC/SM config" — khong dinh nghia; (k) fuse+0x0C04 la `NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE` — khong dinh nghia; (l) fuse+0x0C1C la "GPC config" — khong dinh nghia; (m) 152 word==1 la OTP bit cell vat ly — phan tan 70 khoang, bit 0 duy nhất, khong duoc.

**dev_fuse.h (Turing TU102, gTu106 gan nhat trong xep lan)** chi dinh nghia **2** register:
- `NV_FUSE_OPT_NVDEC_DISABLE` = 0x00021378, bits 2:0 (dong 31)
- `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS` = 0x0002174C, bit 0:0 (NO=0/YES=1) (dong 26-29)

Cac offset fuse khac (0x0000, 0x04D8, 0x056C, 0x0650, 0x0C04, 0x0C1C, v.v.) **khong co bitfield trong source** → ghi la INFERRED hoac REJECTED, khong duoc xac dinh danh.

---

## 5. Duoc giu nguyen (UNKNOWN) — khong do dan

| # | Noi dung | Ly do |
|---|---|---|
| U-1 | dev_fuse.h TU106 chua co trong xep lan; chi co TU102 (Turing) | 350/352 word fuse DATA khong co trang tri source |
| U-2 | Cau truc OTP vat ly / o luu fuse | Gia tri lua khong xac dinh duoc cong cu/co so OTP |
| U-3 | fuse +0x0718 (32 byte, entropy cao) | 4 giua (khoa cong khai, nonce booter, trim chip, ban stamp) tat ca UNKNOWN; khong brute-force |
| U-4 | 0xBADF510C (7 lan vung du lieu fuse) | Gia tri quan sat, khong co trang tri source |
| U-5 | Muc dich callback SEC2 (context +0x30, jalr a5) | Chua giai quyet dia chi callback |
| U-6 | Nguoi goi dispatcher GSP | 0 JAL / AUIPC+JALR truc tiep trong GSP ELF |
| U-7 | Gia tri register PMU tren the nao nay | Chua doc duoc gi |
| U-8 | ACR_CMD / ACR_STATUS / SEC2_STATUS BAR0 | Het ca bi poison (0xBADF5040) |
| U-9 | PLM register | Chi co tu dmesg, BAR0 poison |
| U-10 | Trang thai boot an toan GPU | Gia tri fuse quan sat nhung qua trinh chua xac thuc duoc |
| U-11 | ISA / dia chi tai / anh xa engine cua 38 payload firmware | Container da duoc parse (38 payload, khong overlap), y chua biet |
| U-12 | 388.5 MiB Reserved carveout (NVML) — WPR2 chi 0.50 MiB | Con lai chua giai |
| U-13 | UNK_0x1FA800/04/10/14/20/2C/30 | BAR0 register khong ten trong source |
| U-14 | fingerprint64 container firmware | Source no la hash ten file theo chi muc, da duoc xac thuc bang chu ky giong nhau trong gsp.bin, nhung khong phai chu ky payload |
| U-15 | 5/6 truong trong khoa VBIOS (sig/ver/f4/f8/flags/hash) | Chua biet |

**Yeu cau mo lai (neu can):** dump fuse tu chip TU106/TU104 khac de do chieu; tai lieu PLM/ACR hoac disasm ma bo; bo nguon firmware hoac plaintext-biet de xac dinh ISA payload; ROM TU106 khac de xac nhan PDI/+0x0718.

---

## 6. Thong tin nguon goc (SOURCE PROVENANCE)

15 file source duoc katalog voi SHA256 (xem `source_provenance.json`). File chinh:
- `common/inc/swref/published/turing/tu102/dev_fuse.h` — sha256 `f96f637c...` (2 fuse defs, dong 26 va 31)
- `nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta.h` — sha256 `f3b615a6...` (WPR meta, 256 byte, magic/verified)
- `nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta_v1.h` — sha256 `04e2da01...` (V1, Turing-Ada)
- `nvidia/arch/nvalloc/common/inc/sec2/sec2_emem_channels.h` — sha256 `2f900d61...` (kenh 0, 1024 byte)
- `nvidia/inc/kernel/gpu/gsp/gsp_init_args.h` — sha256 `b6996ab9...` (GSP_ARGUMENTS_CACHED)
- `nvidia/src/kernel/gpu/gsp/cmp40_booter_load_610.h` — sha256 `cb6bdec8...` (bo 610.57.04, co SIG metadata)
- `common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080acr.h` — sha256 `b2d1e136...` (stub FINN)
- `common/sdk/nvidia/inc/ctrl/ctrl208f/ctrl208fsec2.h` — sha256 `fd8332d2...` (SEC2 ECC stub)

**Ghi chu:** Xep lan `/tmp/nvsrc` chua co the xac nhan tag phat hanh chinh xac. URL goc tro toi `https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/main/...` (duong dan tuong ung, khong da cam bang byte hien tai cua main).

---

## 7. Pham vi va gioi han

- Khong lam: ep xuong/tang ap, voltage, power limit, benchmark.
- Khong lam: flash/nap ROM, ghi MMIO/fuse/PCIe, reload driver, reboot.
- Khong lam: exploit/bat thoai moi, trich xuat khoa, bruteforce, nap ROM.
- Khong da tam: entropy cao = ma hoa (nguyen tac C3).
- Tat du thao tac la offline, read-only, sinh lai duoc boi `verify.py`.

---

## 8. Tap tin da xuat (PHASE16/SECURITY_ARCH/)

| Tap tin | Vai tro |
|---|---|
| `verify.py` | Script sinh toan bo by chung, chay duy nhat, 19 assertion |
| `run_summary.json` | Tom tgat chay (23 khuoc noc, 19 assertion, tat ca PASS) |
| `assertions.log` | Nhat ky chi tiet tat ca assertion |
| `source_provenance.json` | 15 file source, duong dan, SHA256, so dong |
| `source_facts.json` | 31 su thiet lap tu source (fuse, WPR, SEC2, GSP, firmware) |
| `measured_facts.json` | 16 su thiet lap tu do/M MIO + dmesg |
| `fuse_source_mapping.json` | 2 fuse register tu source anh xa toi offset dump |
| `boot_chain.json` | Chuoi boot 12 buoc + vai tro firmware + WPR meta V1 |
| `privilege_boundaries.json` | 7 ran gioi, WPR2, SEC2 DMEM, CC, DMA |
| `audit_prior_claims.json` | 23 khuoc noc kiem toan (3 SUPPORTED, 4 MEASURED, 13 REJECTED, 2 INFERRED, 1 UNKNOWN) |
| `unknowns.json` | 15 unknown duoc giu nguyen + 4 yeu cau mo lai |

Duong dan tuyet doi: `/home/REDACTED_USER/codex-work/work_v15/PHASE16/SECURITY_ARCH/`

--- 

**Ket luan:** Kien truc bo an toan CMP40HX/TU106 duoc map duoc 2 register fuse co ten (source tu102), 1 vung WPR2 (0.50 MiB, khop MMIO+dmesg), chuoi boot 12 buoc tu dmesg, va 7 ran gioi. 13 khuoc noc truoc boi duoc bao loi/da chuan sua (4 vung WPR, 11 blob firmware, entropy=AES, PLM doc duoc tu BAR0, driver ky, v.v.). 15 unknown duoc giu nguyen, khong do dan.

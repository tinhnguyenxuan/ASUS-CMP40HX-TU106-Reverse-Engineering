# MEMORY_PCIE_REPORT — CMP40HX / TU106 (0000:03:00.0), Phase 16

## 1. Pham vi va quy che
- Chỉ chạy khi Codex dispatch; chỉ đọc file lưu và source headers NVIDIA (turing/tu102).
- KHONG doc /sys hoac /dev, KHONG probing/ghi GPU, KHONG sua clock/ROM/driver, KHONG doc VRAM/WPR khoi thiet lam, KHONG ghi BAR1_BLOCK.
- Tat du lieu tu archive cu: khong co moi do PCIe/runtime moi. Chua khan bao whole-GPU RE da HOAN TAT.
- Mua tac: MEASURED (bytes file thau), DECODED (quy rut tu bitfield/source), CORROBORATED (hai nguon thau), REJECTED, UNKNOWN.

## 2. PCIe config/capability (endpoint 0000:03:00.0)
config_space_64 raw (PCIE/pcie_map.json, offset bytes 0x00..0x3F): de100b1f07051000a100020300000000000000fa0c000000103800000c0000000838000001e000000000000043100488000000006000000000000000ff010000
- Vendor 0x10DE Device 0x1F0B Rev 0xA1 Class 030200 (3D controller) — MEASURED [config+0x00..+0x0B]
- Subsystem 0x1043:0x8804 (ASUS) — MEASURED [config+0x2C..+0x2F]
- First capability pointer = 0x60 at config+0x34 — MEASURED [config byte 0x34]
- Capability chain duoc liet ke bo lspci text (RAW_DATA/q3_pcie.txt): [60] PM v3 (line 47), [68] MSI 64-bit (line 48), [78] Express v2 Endpoint (line 49), ... [bb0] Physical Resizable BAR v1 (line 74). Cap treo ngoai 0x3F khong co trong config dump 64 byte -> chi duoc chung minh bo text, khong doc raw config.

### BAR decode (config bytes + resource range raw)
- BAR0: reg config+0x00 raw=0xFA00000032-bit -> mem/io-base 0x0000FA000000
- BAR1: reg config+0x01 raw=0x0000000C32-bit -> mem/io-base 0x000000000000
- BAR2: reg config+0x02 raw=0x0000381032-bit -> mem/io-base 0x000000003810
- BAR3: reg config+0x03 raw=0x0000000C32-bit -> mem/io-base 0x000000000000
- BAR4: reg config+0x04 raw=0x0000380832-bit -> mem/io-base 0x000000003800
- BAR5: reg config+0x05 raw=0x0000E00132-bit -> mem/io-base 0x00000000E000
resource_file ranges raw (PCIE/pcie_map.json):
  - 0x0000FA000000..0x0000FAFFFFFF size 16777216 (16.000 MiB) flags 0x00040200 — MEASURED raw range, chung minh khoi duoc giai ma
  - 0x381000000000..0x381FFFFFFFFF size 68719476736 (65536.000 MiB) flags 0x0014220C — MEASURED raw range, chung minh khoi duoc giai ma
  - 0x380800000000..0x380801FFFFFF size 33554432 (32.000 MiB) flags 0x0014220C — MEASURED raw range, chung minh khoi duoc giai ma
  - 0x00000000E000..0x00000000E07F size 128 (0.000 MiB) flags 0x00040101 — MEASURED raw range, chung minh khoi duoc giai ma

### ReBAR (Physical Resizable BAR [bb0]) — RAW_DATA/q3_pcie.txt lines 75-77
- BAR0: current 16MB / supported 16MB.
- BAR1: current 64GB / supported 64MB..256GB (64GB co trong danh sach duoc ho tro).
- BAR3: current 32MB / supported 32MB.
- Ket luat: ReBAR CAP da duoc khai bao ([bb0], line 74); BAR1 duoc cau hinh target 64GB. Nhung xau '64G' MOI KHONG DU chung minh day du khoi giai ma: span duoc chung minh bo resource range raw (BAR1: 381000000000..381fffffffff = 64 GiB; BAR3: 380800000000..380801FFFFFF = 32 MiB).

### Link: capability vs cau hinh target vs thuc te neu ngoai (khong do moi)
- Card (Endpoint, q3_pcie.txt line 27 LnkCap): 5GT/s x16; line 38 LnkCtl2 Target Link Speed: 5GT/s; line 40 LnkSta: 2.5GT/s (downgraded) x16.
- Root port 0000:00:02.0 (Express v2 Root Port, line 82): LnkCap 8GT/s x16 (line 108); LnkCtl2 target 5GT/s (line 124); LnkSta 2.5GT/s x16, DLActive+ (line 126).
- Ket luat: ca hai dau target 5 GT/s, runtime thuc te 2.5 GT/s -> link training chua dat target; KHONG duoc xac rang boi root port gioi han (PCIE/q3_link.json conclusion).

## 3. bar3_hot.bin: nguyen nguyen mapping
- Nguon tool TOOLS/p9_bar3dump.py: mo /sys/bus/pci/devices/0000:03:00.0/resource3, mmap [0x0:0x40000), ghi file byte 1:1.
- Mapping duoc xac dinh bo nguon tool: file_offset == BAR3_window_offset; dia chi thiet lap = 0x380800000000 + file_offset.
- BAR3 base duoc lay tu config: BAR3 reg config+0x1C = 0x0000000C (mem 64-bit prefetchable), BAR4 reg config+0x20 = 0x00003808 -> base 0x380800000000; size 32 MiB tu resource3 range 0x380800000000..0x380801FFFFFF.
- bar3_hot.bin: 262144 bytes (0x40000), SHA256 956c7b3ef2322c5ad5603f0cbc7f7defefa0bfb5678c276c0d91854099712d9c. Khung cua tool khop kich thuc file.
- Chua the lay lai tu thiet lam (offline, doc-only); mapping co so = config decode + nguon tool p9_bar3dump.py.
- Xac lap noi bo: p9_bar3_parsed.json (hot pages + nonzero u32) khop toan bo voi phep REDACTED_USER lai tu bar3_hot.bin: CO -> provenance luu truu duoc xac nhan noi bo.

## 4. BAR3 inventory (toan bo trang/entry raw, xuat ra bar3_entries.csv)
- Tong 64 trang (0x00000..0x3F000, 256 KiB); trang co du lieu: 48/64; tong byte co du lieu: 47069; u32 khong 0: 17774; u64 khong 0: 9245.
- Trang co du lieu: 0x00000(2), 0x08000(2), 0x10000(4), 0x11000(4), 0x12000(4), 0x14000(270), 0x15000(4), 0x16000(182), 0x17000(894), 0x18000(1022), 0x19000(1022), 0x1A000(1022), 0x1B000(1022), 0x1C000(1022), 0x1D000(1022), 0x1E000(1022), 0x1F000(1022), 0x20000(1022), 0x21000(1022), 0x22000(1022), 0x23000(1022), 0x24000(1022), 0x25000(1022), 0x26000(486), 0x27000(4), 0x28000(71), 0x29000(71), 0x2A000(79), 0x2B000(2479), 0x2C000(4), 0x2D000(4), 0x2E000(71), 0x30000(1501), 0x31000(1788), 0x32000(1788), 0x33000(1788), 0x34000(1788), 0x35000(1788), 0x36000(1788), 0x37000(1788), 0x38000(1788), 0x39000(1788), 0x3A000(1788), 0x3B000(1788), 0x3C000(1788), 0x3D000(1788), 0x3E000(1788), 0x3F000(1593)
- Cac u32 bat dau trang: 0x00000=0x00007FF0, 0x08000=0x00007FF0, 0x10000=0x1F4F4D02, 0x11000=0x1F4F4C02, 0x12040=0x1F4F4B02 — MEASURED [bar3_hot.bin+off].
- Vung 0x14000: u32 0x00000008 lap theo stride 0x10 — MEASURED (xem H2).
- Vung 0x17000: entry 16 byte {flags, 0x00060000, 8 byte zero}, flags tang 0x20000 — duoc bao bo p9_bar3dump.py; bar3_17000_stable o TOPOLOGY/p9_stability.json line 5.
- Duoi cuoi 0x3FE00..0x3FFF4: cac ban ghi {0x1FC..0001, 0x06000000, 0, 0} theo stride 0x10 — MEASURED (xem H3).

## 5. Kiem tra lai pattern ID 0x1f4f / 0x1f4e (khong duoc su dung de ket luat bang SKU)
- Quet tat ca u32 le 4 byte: co 50 lan xuat hien thoa hi16/lo16/full == 0x1F4F hoac 0x1F4E.
  - 0x10000: u32_le=0x1F4F4D02 u32_be=0x024D4F1F bytes=024d4f1f align4=True page_align=True hits=hi16==0x1F4F
  - 0x11000: u32_le=0x1F4F4C02 u32_be=0x024C4F1F bytes=024c4f1f align4=True page_align=True hits=hi16==0x1F4F
  - 0x12040: u32_le=0x1F4F4B02 u32_be=0x024B4F1F bytes=024b4f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x14FE0: u32_le=0x1F4F17F2 u32_be=0xF2174F1F bytes=f2174f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x14FE8: u32_le=0x1F4F1602 u32_be=0x02164F1F bytes=02164f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x14FF0: u32_le=0x1F4F17E2 u32_be=0xE2174F1F bytes=e2174f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x14FF8: u32_le=0x1F4F1502 u32_be=0x02154F1F bytes=02154f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x15000: u32_le=0x1F4F4802 u32_be=0x02484F1F bytes=02484f1f align4=True page_align=True hits=hi16==0x1F4F
  - 0x16000: u32_le=0x1F4EFB02 u32_be=0x02FB4E1F bytes=02fb4e1f align4=True page_align=True hits=hi16==0x1F4E
  - 0x16008: u32_le=0x1F4F4702 u32_be=0x02474F1F bytes=02474f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x16010: u32_le=0x1F4F4602 u32_be=0x02464F1F bytes=02464f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x16018: u32_le=0x1F4F4502 u32_be=0x02454F1F bytes=02454f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x16020: u32_le=0x1F4F4402 u32_be=0x02444F1F bytes=02444f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x16028: u32_le=0x1F4F4302 u32_be=0x02434F1F bytes=02434f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x16030: u32_le=0x1F4F4202 u32_be=0x02424F1F bytes=02424f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x16038: u32_le=0x1F4F4102 u32_be=0x02414F1F bytes=02414f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x16040: u32_le=0x1F4F4002 u32_be=0x02404F1F bytes=02404f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x16048: u32_le=0x1F4F1F02 u32_be=0x021F4F1F bytes=021f4f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x16050: u32_le=0x1F4F1E02 u32_be=0x021E4F1F bytes=021e4f1f align4=True page_align=False hits=hi16==0x1F4F
  - 0x16058: u32_le=0x1F4F1D02 u32_be=0x021D4F1F bytes=021d4f1f align4=True page_align=False hits=hi16==0x1F4F
- ID PCI tham gia so sanh: vendor 0x10DE device 0x1F0B sub 0x1043:0x8804. Khong gia tri nao trung.
- Ket luat: PATTERN 0x1f4f/0x1f4e KHONG DU DE GOI BANG BANG SKU table — khong trung ID, xuat hien bo trong trang, khong co cau truc bang, khong xac dinh endian/alignment co nghia. REJECTED.

## 6. GMMU/PDE/PTE va aperture tu source tu102/dev_mmu.h
- NV_MMU_PDE__SIZE = 8 byte. Word0 (bit [msb:lsb]): APERTURE_BIG [1:0] (0 invalid,1 video,2 sys coh,3 sys noncoh), SIZE [3:2] (0 full,1 half,2 quarter,3 eighth), ADDRESS_BIG_SYS [31:4] / ADDRESS_BIG_VID [28:4].
- NV_MMU_PTE__SIZE = 8 byte. Word0: VALID [0], PRIVILEGE [1], READ_ONLY [2], ENCRYPTED [3], ADDRESS_SYS [31:4] / ADDRESS_VID [28:4]; Word1: VOL [0], APERTURE [2:1] (0 vid mem,1 peer,2 sys coh,3 sys noncoh), LOCK [3], COMPTAGLINE [63:44], READ_DISABLE [30], WRITE_DISABLE [31], KIND [11:4] (0 PITCH,...7 INVALID).
- Source thu duoc boi regex tu dev_mmu.h; khong con thong tin driver map BAR3 vao aperture nao trong set header cua task.
- dev_vm.h: chi tim register khoi BAR VF (BAR1_BLOCK 0x0F40, BAR2_BLOCK 0x0F48) co TARGET [29:28] (0 vid,2 sys coh,3 sys noncoh) va MODE [31] (0 physical,1 virtual). Mapping driver BAR3 con UNKNOWN; khong doc BAR1_BLOCK theo yeu cau.

## 7. Kiem tra gia thuyet cau truc BAR3 (duoc chon mot gia thuyet de kiem tra xech)
- H1 u32 0x1f4f../0x1f4e.. o BAR3 la bang ma SKU / ID thiet lap PCI: REJECTED
  Co so: bar3_hot.bin u32 inventory; config_space_64 +0x00/+0x02/+0x2C/+0x2E
  - tat ca 50 lan xuat hien 0x1f4f/0x1f4e khong trung bat cu ID PCI nao (10de:1f0b, sub 1043:8804), khong co doi tuong alignment/endian bang bang, khong co cau truc bang
- H2 lap 0x00000008 tai 0x14000 la page directory / page table: REJECTED
  Co so: bar3_hot.bin +0x14000..
  - gia tri hang lan = 0x00000008 khong chua dia chi (khong co bit [31:4] hop le nhu dev_mmu.h PTE/PDE_ADDRESS)
  - khong co bit VALID (bit 0 cua word0 PTE/PDE) danh dau entry co hai
  - stride 0x10 voi 12 byte zero giua cac gia tri khong phai kich thuc 8 byte cua PDE/PTE (NV_MMU_PDE__SIZE=8, NV_MMU_PTE__SIZE=8)
  - khong giam duoc page directory chi tu bit lap luan (yeu cau cau truy van task)
- H3 vung cuoi 0x3FE00..0x3FFF4 cua BAR3 la mang PTE GMMU (dev_mmu.h, 8 byte/entry): REJECTED (mang PTE lien ke) / word0 tuong thich PTE ca le
  Co so: bar3_hot.bin +0x3FE00..+0x3FFF4; dev_mmu.h NV_MMU_PTE_*, NV_MMU_PTE__SIZE=8
  - co 31 ban ghi 16 byte tai 0x3FE00..0x3FFF4: word0 co VALID=1, dia chi [31:4] 16-byte aligned, aperture=video memory, KIND=PITCH; word1 lap lai 0x06000000 (VOL=0, LOCK=0)
  - dia chi tang 131072 (0x20000) muc giua cac ban ghi
  - TU CHAP: stride cua ban ghi la 0x10 byte, khac PTE__SIZE=8 byte tu dev_mmu.h; 8 byte cua moi ban ghi (w2,w3) luon zero -> khong phai mang PTE lien ke theo dinh nghia source
  - tat ca ban ghi nam trong mot trang (0x3F000); khong the kiem tra duong bien trang ngoai cua cua so 0x40000
Tat ca cac gia thuyet tren duoc ket qua REJECTED (hoac REJECTED nhu mang lien ke nhung ca le theo entry). KHONG gan page directory chi tu bit lap luan.

## 8. Thoa gia total/usable/reserved/free VRAM
- Tu smq (MEMORY/memory_registers.json): Total 8192 MiB, Reserved 389 MiB, Used 0 MiB, Free 7804 MiB.
- Total - Reserved - Used = 7803 MiB, khong bang Free 7804 MiB (delta 1 MiB, chua ro: lam tron hay overlap).
- NVML Reserved 389 MiB vs Total-Free-Used 388 MiB (delta 1 MiB). RESERVED KHONG BANG total-free.
- BAR1 memory (smi): Total 65536 MiB / Used 2 / Free 65534 — tuong ung voi config BAR1 64 GiB (CORROBORATED).

### WPR (corrected VAL[31:4] << 12 == (val & 0xFFFFFFF0) << 8, vi low nibble bang 0)
- Register runtime (SECURITY/security_registers.json): 0x1FA824 NV_PFB_PRI_MMU_WPR2_ADDR_LO = 0x01F7E000; 0x1FA828 WPR2_ADDR_HI = 0x01FFEE00.
- WPR2 corrected: base 0x1F7E00000, end 0x1FFEE0000, size 135135232 bytes (128.875 MiB), nam trong khoang 8 GiB FB.
- Gia tri luu va bo xung (dmesg_facts): WPR_at_boot lo 0x1FFE000; dmesg_facts.WPR2_lo 0x1FFFFE00; dmesg boot commit WPR2=0:0x1FFFFE00. Cac gia tri KHONG NHAU -> ung dung WPR2 nao ap dung hien tai chua ro.
- LUAT DU AP DUNG: KHONG tru WPR2 (128.875 MiB) mac dinh khoi NVML Reserved 389 MiB, vi chua biet overlap/cap phat. Muc tro giu giua WPR2 va Reserved = UNKNOWN.
- Giu nguyen EVIDENCE_LEDGER.md E16-007: cung base/end va khoang cach 128.875 MiB (CORROBORATED).

## 9. Ket luat
- PCIe/BAR3 interface duoc giai ma tu archive: cap the 10de:1f0b rev a1, BAR0 16MB @ fa000000, BAR1 64GB pref @ 0x381000000000, BAR3 32MB pref @ 0x380800000000 (map bar3_hot.bin), BAR5 I/O 0xe000/128B; ReBAR cap [bb0] ton tai, BAR1 target 64GB; link target 5GT/s nhung runtime 2.5GT/s x16 (downgraded).
- bar3_hot.bin co nguyen nguyen mapping va toan bo inventory xuat ra bar3_entries.csv; pattern 0x1f4f/0x1f4e KHONG duoc chap nhan lam bang SKU.
- GMMU PDE/PTE format duoc trích tu dev_mmu.h; ba gia thuyet cau truc BAR3 duoc kiem tra va BO LOC (H1/H2/H3).
- VRAM: Total 8192/Reserved 389/Used 0/Free 7804 MiB, hieu 1 MiB chua ro; WPR2 corrected [0x1F7E00000, 0x1FFEE0000] 128.875 MiB khong duoc tu do tru khoi Reserved.
- KHONG khan bao whole GPU DONE; khong co do thuc moi tren PCIe/runtime.

## Xuat: memory_pcie_verified.json, bar3_entries.csv, run.log, MEMORY_PCIE_REPORT.md (thu muc nay).

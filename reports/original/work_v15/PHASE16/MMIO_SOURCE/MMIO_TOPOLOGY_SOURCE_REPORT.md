# MMIO TOPOLOGY SOURCE REPORT — PHASE16/MMIO_SOURCE

GPU: CMP 40HX (TU106-100-A1), PCI 10DE:1F0B, subsystem 8804:1043, BDF 0000:03:00.0, BAR0 /sys/bus/pci/devices/0000:03:00.0/resource0
Che do: offline read-only khong GPU probes/writes/tuning/flash/reboot/driver reload/exploit/bypass. Dung /usr/bin/python3, chi stdlib.
Thu muc xuat: PHASE16/MMIO_SOURCE/ (khong sua checkpoint chung hay artifacts job khac).

## 1. Inputs da bam toan bo (sha256 trong mmio_topology_verified.json)

MMIO/mmio.json, MMIO/registers_turing.json, MMIO/registers_all.json, RAW_DATA/tu06.json,
TOPOLOGY/aperture_map.json, TOPOLOGY/p9_reclass.json, TOPOLOGY/p9_pattern.json,
TOPOLOGY/silicon_topology.json, SECURITY/security_registers.json, MEMORY/memory_registers.json.

Header duoc su dung (ma nguon): tat ca *.h trong /tmp/nvsrc/common/inc/swref/published/turing/tu102 (37 file, da bam).
Quy dinh ap dung: tu102 la dinh nghia cho TU10x/TU106 khi tram khop dia chi. Cac ho khac (trong registers_all.json, 2133 header, 938 thanh ghi) CHI duoc danh gia nhu tham chieu ap khong, KHONG duoc coi dinh nghia TU106.

## 2. Ket hop dia chi da dump voi nguon TU10x

- Da dump: 52 thanh ghi (MMIO/mmio.json, trang 0,2,3,8,16,17,20,31,132,182).
- Khop ten nguon tu102: 52/52. Dia chi khong biet: 0.
- Trich gia tri bitfield boi mask thuc: (value >> lo) & ((1 << (hi-lo+1)) - 1).
- Phan loai moi thanh ghi: source_match / zero / error_like (0xBADFxxxx, 0xBAD00100, 0xFFFFFFFF) / co bitfield duoc trich.
- Xuat: register_fields.csv (78 hang, 1 hang moi bitfield; thanh ghi khong bitfield van co hang). Moi hang co source_hash/source_line/raw/offset.

Khong thanh ghi nao trong dump o dia chi co nguon ho khac (registers_all) duoc dung de dinh nghia TU106.

## 3. WPR2 LO/HI @ 0x1FA824 / 0x1FA828 (dev_fb.h)

Theo tu102/dev_fb.h (dong 39-44): NV_PFB_PRI_MMU_WPR2_ADDR_LO 0x001FA824 VAL 31:4 ALIGNMENT 0x0c; NV_PFB_PRI_MMU_WPR2_ADDR_HI 0x001FA828 VAL 31:4 ALIGNMENT 0x0c.
Giai ma: field = (raw >> 4) & 0x0FFFFFFF (28 bit, KHONG mask 20 bit); decoded = field << 12.

| thanh ghi | raw | raw_hex | field (31:4) | field_hex | decoded | decoded_hex | source_line |
|---|---|---|---|---|---|---|---|
| WPR2_ADDR_LO | 33021952 | 0x01F7E000 | 2063872 | 0x001F7E00 | 8453619712 | 0x1F7E00000 | fb.h:40 |
| WPR2_ADDR_HI | 33549824 | 0x01FFEE00 | 2096864 | 0x001FFEE0 | 8588754944 | 0x1FFEE0000 | fb.h:43 |

Hieu chieu ran gioi: 135135232 byte = 128.875 MiB (chi la phep REDACTED_USER tren gia tri da decode).

Nguon su dung (consumer): boot log trong SECURITY/security_registers.json ghi WPR2 duoc lap trong boot (kgspExecuteBooterLoad_TU102 wpr2_lo=0x1ffffe00, WPR2=0:0x1ffffe00) — chi chung minh thanh ghi duoc su dung, KHONG xac dinh giai thich ran gioi (inclusive/exclusive). Bo nguon local khong co dinh nghia ran gioi nay => ran gioi semantics = UNKNOWN. KHONG su dung hieu chieu de phan bo reserved allocation.

## 4. Ket so trang tu RAW_DATA/tu06.json + bieu dien chinh sua

tu06: 4096 trang x 4KiB, moi trang chi co 4 u32 (16 byte) sample. KHONG ga din co full 4KiB.

Bo loc chinh sua (p9_reclass, theo distinct u32 cua vung DATA cu):
- DATA 287 -> POISON_MOI (0xBAD00100) 25, SINGLE_U32_KHAC (0xFFFFFFFF) 72 -> UNINIT_FF, DATA_THAT (VBIOS shadow 0x300000..0x3D7FFF) 141 -> DATA.

Ket qua chinh sua (giong aperture_map.json reclassified_v7.corrected_stats):
- POISON 3278, UNINIT_FF 72, DATA 141, ZERO 355, MIXED 201 => 4047 trang da phan loai.
- 49 trang CHUA duoc phan loai (4096 - 4047): trang co tu06=DATA nhung khong o trong vung nao cu p9_reclass (vung nho, <3 trang/vung, duoi nguong gom).

49 trang chi xac (page, offset, sample_class tu 4 u32 da dump):
7(0x007000 POISON_BAD00100_like), 140(0x08c000 MIXED_data_like), 282(0x11a000 MIXED_data_like), 499(0x1f3000 MIXED_data_like),
768(0x300000 MIXED_data_like), 769(0x301000 MIXED_data_like), 771(0x303000 MIXED_data_like), 774(0x306000 MIXED_data_like),
775(0x307000 MIXED_data_like), 776(0x308000 MIXED_data_like), 780(0x30c000 MIXED_data_like), 781(0x30d000 MIXED_data_like),
817(0x331000 MIXED_data_like), 818(0x332000 MIXED_data_like), 844(0x34c000 MIXED_data_like), 845(0x34d000 MIXED_data_like),
846(0x34e000 MIXED_data_like), 848(0x350000 MIXED_data_like), 849(0x351000 MIXED_data_like), 850(0x352000 MIXED_data_like),
852(0x354000 MIXED_data_like), 889(0x379000 MIXED_data_like), 890(0x37a000 MIXED_data_like), 892(0x37c000 MIXED_data_like),
895(0x37f000 MIXED_data_like), 896(0x380000 MIXED_data_like), 897(0x381000 MIXED_data_like), 901(0x385000 MIXED_data_like),
902(0x386000 MIXED_data_like), 938(0x3aa000 MIXED_data_like), 939(0x3ab000 MIXED_data_like), 965(0x3c5000 MIXED_data_like),
966(0x3c6000 MIXED_data_like), 967(0x3c7000 MIXED_data_like), 979(0x3d3000 UNINIT_FF_like), 980(0x3d4000 UNINIT_FF_like),
1040(0x410000 UNIFORM_data_like), 1041(0x411000 UNIFORM_data_like), 2304(0x900000 MIXED_data_like), 2308(0x904000 MIXED_data_like),
2312(0x908000 MIXED_data_like), 2316(0x90c000 MIXED_data_like), 2432(0x980000 MIXED_data_like), 2436(0x984000 MIXED_data_like),
2440(0x988000 MIXED_data_like), 2464(0x9a0000 MIXED_data_like), 2912(0xb60000 MIXED_data_like), 3008(0xbc0000 MIXED_data_like),
3009(0xbc1000 MIXED_data_like).

Phan biet mau trong sample: zero (tat ca 0), 0xFFFFFFFF (UNINIT_FF_like), 0xBADFxxxx (POISON_BADF_like), 0xBAD00100 (POISON_BAD00100_like), khac (MIXED/UNIFORM data_like). Phan biet nay chi ap dung voi 16 byte dau trang; noi dung con lai cua trang 4KiB chua biet.
KHONG su dung poison de luan ket vat ly engine mat hay dieu bo dia chi — poison chi la gia tri doc duoc ngoai cua so decode (xac dinh boi aperture_map conclusion).

Xuat: page_inventory.csv (4096 hang, moi hang co source_hash/source_line/raw/offset).

## 5. Topology TU10x (GPC/TPC/SM/ROP/L2)

Header da tra cuu trong bo nguon local: dev_top.h = KHONG CO, dev_graph.h = KHONG CO, dev_gr.h = KHONG CO.
Co: dev_fault.h (GPC/TPC fault CLIENT ID chi la khoang index client, KHONG la so luong engine), dev_ltc.h/dev_ltc_zb.h (L2 ECC error-count thanh ghi, KHONG so luong L2), dev_vm.h (L2 invalidate 0xF00/0xF04, khong co trong dump), dev_fb.h (L2TLB ECC), dev_fuse.h (fuse, khong la topology).

Ket luan: GPC/TPC/SM/ROP/L2 so luong = UNKNOWN. Bo du lieu neu decode chi khi co truong/thong tin nguon thuc; popcount=3 hoac 17 KHONG du de dat ten. Thong so sm_count="NVIDIA CMP 40HX, 7.5" tu silicon_topology.json la xuat nvml, KHONG la dinh nghia thanh ghi, khong duoc decode.

Kiem tra tiep theo (chi o duoi, khong thuc thu nghiem mot may):
- Lay dev_top.h/dev_gr.h tu bo nguon tu10x (tu102/tu104/tu106 neu co) de tim dinh nghia so luong GPC/TPC/SM/ROP.
- Doi chieu client ID lon nhat trong dev_fault.h (GPC_T1, TPCCS, GPC_PE) nhu gioi han thuan, ro rang la fault client khong la topology count.
- Doi chieu sm_count tu nvml voi bo nguon thanh ghi khi co.

## 6. Coverage thuc te

| muc tieu | tu yeu cau | thuc te |
|---|---|---|
| Thanh ghi da dump khop nguon TU10x | 52/52 | 52/52 |
| Trang da phan loai | 4047/4096 | 4047/4096 |
| Trang chua phan loai | 49/4096 | 49/4096 |
| GPC/TPC/SM/ROP decode duoc | yeu cau nguon thuc | 0/4 (UNKNOWN) |
| L2 thanh ghi co nguon | — | 4/4 da liệt kê (ECC/invalidate, khong phai count) |

## 7. Unknowns va gioi han

- GPC/TPC/SM/ROP/L2 so luong: UNKNOWN (bo header dev_top/dev_graph bi mat trong bo nguon local).
- WPR2 ran gioi inclusive/exclusive: UNKNOWN (khong co nguon local).
- Vi tri/pham vi WPR2 vat ly va overlap NVML Reserved: UNKNOWN (khong su dung phep tru).
- Noi dung 4KiB day du cua 49 trang chua phan loai: UNKNOWN (chi co 16 byte sample).
- registers_all.json (938 thanh ghi tu 2133 header ho khac) khong duoc dung de dinh nghia TU106.

## 8. Tap tin xuat (PHASE16/MMIO_SOURCE/)

- mmio_topology_verify.py — tool chinh (stdlib, chay duoc, exit 0).
- mmio_topology_verified.json — ket hop, hash inputs/header, WPR2, trang, topology, coverage.
- register_fields.csv — 78 hang, moi hang co source_hash/source_line/raw/offset.
- page_inventory.csv — 4096 hang, moi hang co source_hash/source_line/raw/offset.
- mmio_topology_verify_run.log — stdout+stderr+exit code cua lan chay thuc.

Ket thuc. Khong ket luan "toan bo GPU DONE".

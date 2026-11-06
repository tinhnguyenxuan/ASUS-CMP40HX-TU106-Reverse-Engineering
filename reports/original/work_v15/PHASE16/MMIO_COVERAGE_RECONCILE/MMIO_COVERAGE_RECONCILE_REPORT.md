# MMIO Namespace & BAR0 Sampling Coverage Reconcile

GPU: CMP 40HX (TU106-100-A1), PCI 10DE:1F0B, BDF 0000:03:00.0, BAR0 /resource0 (16 MiB, 4096 pages x 4 KiB)
Mode: offline read-only, stdlib only. No hardware access, no probes/writes, no driver/tool installation.
Original archives and prior worker outputs under work_v15/ were read only and are unmodified.

## 1. Raw input provenance

| file | bytes | sha256 | manifest (input_hashes.json) |
|------|-------|--------|------------------------------|
| MMIO/mmio.json | 18248 | 8782ce5628383a19d73121396c4032f9f67f6275c0c897455ea1c5913c61e0b8 | not_in_manifest |
| MMIO/registers_turing.json | 14974 | a7e084bcb153e8413927843b77b3dab89fd113bff4c77b5a4de17480961b91a9 | not_in_manifest |
| MMIO/registers_all.json | 514470 | 23d64737b22dea5e13c5070fabed61ec4262f55a8b6dc65347fa20b6eab0e410 | not_in_manifest |
| RAW_DATA/tu06.json | 772991 | a872f2ce4fb2bd1f069127d04bd937f28d324c0023841e49c97cd8490276d5ca | not_in_manifest |
| PHASE16/MMIO_SOURCE/page_inventory.csv | 1360200 | d533936694f5582288a50ca034edb06b5be9457f09c4d692d6b592a9310344c8 | not_in_manifest |
| PHASE16/MMIO_SOURCE/register_fields.csv | 20916 | dcd4a2a4395a51e474c6698575e1decb5781e7b001b0087269db4f7b8dcbc3f7 | not_in_manifest |
| PHASE16/MMIO_SOURCE/mmio_topology_verified.json | 10319 | 7214c8418215fb96c7a3c8499c32744fedc963d3cec43fbfb13adaaf82bb7c9e | not_in_manifest |
| PHASE16/MMIO_NAMESPACE/mmio_namespace_verified.json | 77750 | 0cf3344de2d8585e2aea7318b882e9e6c0c37ee396c97b16bef78681a6c6dfd9 | not_in_manifest |
| PHASE16/MMIO_NAMESPACE/corrected_registers.csv | 8558 | 5013ba75de6be96f79edf1c412b3966eb3e3cb2239fc3749ea9453ef1870e63a | not_in_manifest |
| PHASE16/mmio_namespace_coordinator_review.json | 4415 | b84d4a0ffaae5c5be8a64ccdb1c8e39de094aa16017cc43292513bdfd5c816f5 | not_in_manifest |
| PHASE16/mmio_topology_coordinator_review.json | 841 | 4d33083899c324d28d831dc38b730bc3c225df8f06f487e9316e754cd25fdff4 | not_in_manifest |
| PHASE16/mmio_audit.json | 1238 | abcca8580471ab0addb1a67b3558de00b4bbb9086a876ede0302df1724498b55 | not_in_manifest |

## 2. Header provenance (definition source: turing/tu102, applicable to TU10x/TU106)

- dev_ctrl.h: sha256=213bbf9cb40da4b78292cf9c63a3be307b53a19c9d80bc5194bc14bb29b6c0be
- dev_fuse.h: sha256=f96f637c14732564911cd3211409a11b5dacd0ef27c5ad3df56e5d715d9fa30d
- dev_bus.h: sha256=58d106d908a1b56a99b10075744067b15be95d0973ae4b4c9a50e914843cdd44
- dev_fb.h: sha256=8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9
- dev_gc6_island.h: sha256=2a2b677175b6cb8936f4c9d5deb8b677a19ba74ec274c43d140140e620186e2d
- dev_gsp.h: sha256=7736a1d52aaae1d7ba89f3d231d924f74cf612e404ccde4043326bf234180cb0
- dev_vm.h: sha256=8ea9a40bed9a857385f38f94d074081ac3d775676c6204ba72a2e883898faea6
- dev_gc6_island_addendum.h: sha256=192415f7fc931441531dda6705700480b6e0715ed25ab07ed86a04a0588183f5
- dev_esched_pbdma.h: sha256=e9b48a491a5d13b13f7e9de869f6b915359345df08d0f4f5c99d3e9322ffd5cb
- dev_nv_xve.h: sha256=4421613bea6c68c86555d40d5ff208af861bde4da48873218c3caffcdbb638ad
- dev_ltc.h: sha256=b22068694089ed6271d131e38574d1cea347ff751e790e3b1888c2d5cdb001ce

## 3. Namespace reconciliation (preserved: 42 registers, 3 bases, 3 constants, 3 control-space, 1 PCI config)

| category | count |
|----------|-------|
| confirmed MMIO_BAR0 registers | 42 |
| MMIO_BAR0 base (null access) | 3 |
| constants mislabeled as addresses | 3 |
| control-space addresses (NV_CTRL) | 3 |
| PCI config addresses | 1 |
| misaligned addresses | 3 |
| unknown | 0 |
| total | 52 |

- The 3 misaligned addresses are exactly the 3 constants (0xffff, 0xface, 0x10de); constants are values, not MMIO addresses.
- Control-space registers (0x00b6687c / 0x00b66880 / 0x00b66884) lie numerically inside the BAR0 window but are architecturally NV_CTRL control-space; per the prior review acceptance, control-space classification alone does not prove a location is physically outside BAR0.
- No MMIO_BAR0 register is misaligned; all 52 entries match their header address (52/52 address-level source match).

## 4. The 26 flags: semantic=true / source_match=false -> all corrected

Root cause: the prior worker's header parser executed `src_lo, src_hi = map(int, 'HI:LO'.split(':'))`, i.e. it read the
header bitrange as LO:HI and compared it against the dump's hi:lo. Every agreeing pair was reported `source_match=false`.
Reading the header in its documented HI:LO order makes all 26 flags `source_match=true`. No namespace, count, or classification changes.

| # | register | field | header (file:line, sha256) | header hi:lo | dump hi:lo | dump value | semantic | corrected source_match | TU106 |
|---|----------|-------|----------------------------|--------------|------------|------------|----------|------------------------|-------|
| 1 | NV_CTRL_CPU_DOORBELL_VECTORID | NV_CTRL_CPU_DOORBELL_VECTORID_VALUE | dev_ctrl.h:34, 213bbf9cb40da4b78292cf9c63a3be307b53a19c9d80bc5194bc14bb29b6c0be | 11:0 | 11:0 | 129 | true | true | yes |
| 2 | NV_CTRL_LEGACY_ENGINE_NONSTALL_INTR_BASE_VECTORID | NV_CTRL_LEGACY_ENGINE_NONSTALL_INTR_BASE_VECTORID_VECTOR | dev_ctrl.h:31, 213bbf9cb40da4b78292cf9c63a3be307b53a19c9d80bc5194bc14bb29b6c0be | 11:0 | 11:0 | 0 | true | true | yes |
| 3 | NV_CTRL_LEGACY_ENGINE_STALL_INTR_BASE_VECTORID | NV_CTRL_LEGACY_ENGINE_STALL_INTR_BASE_VECTORID_VECTOR | dev_ctrl.h:28, 213bbf9cb40da4b78292cf9c63a3be307b53a19c9d80bc5194bc14bb29b6c0be | 11:0 | 11:0 | 192 | true | true | yes |
| 4 | NV_FUSE_OPT_NVDEC_DISABLE | NV_FUSE_OPT_NVDEC_DISABLE_DATA | dev_fuse.h:32, f96f637c14732564911cd3211409a11b5dacd0ef27c5ad3df56e5d715d9fa30d | 2:0 | 2:0 | 0 | true | true | yes |
| 5 | NV_PBUS_BAR1_BLOCK | NV_PBUS_BAR1_BLOCK_PTR | dev_bus.h:41, 58d106d908a1b56a99b10075744067b15be95d0973ae4b4c9a50e914843cdd44 | 27:0 | 27:0 | 2063552 | true | true | yes |
| 6 | NV_PBUS_BAR1_BLOCK | NV_PBUS_BAR1_BLOCK_TARGET | dev_bus.h:43, 58d106d908a1b56a99b10075744067b15be95d0973ae4b4c9a50e914843cdd44 | 29:28 | 29:28 | 0 | true | true | yes |
| 7 | NV_PBUS_BAR2_BLOCK | NV_PBUS_BAR2_BLOCK_PTR | dev_bus.h:53, 58d106d908a1b56a99b10075744067b15be95d0973ae4b4c9a50e914843cdd44 | 27:0 | 27:0 | 2063553 | true | true | yes |
| 8 | NV_PBUS_BAR2_BLOCK | NV_PBUS_BAR2_BLOCK_TARGET | dev_bus.h:55, 58d106d908a1b56a99b10075744067b15be95d0973ae4b4c9a50e914843cdd44 | 29:28 | 29:28 | 0 | true | true | yes |
| 9 | NV_PFB_PRI_MMU_FILLUNIT_ECC_UNCORRECTED_ERR_COUNT | NV_PFB_PRI_MMU_FILLUNIT_ECC_UNCORRECTED_ERR_COUNT_TOTAL | dev_fb.h:98, 8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9 | 15:0 | 15:0 | 0 | true | true | yes |
| 10 | NV_PFB_PRI_MMU_FILLUNIT_ECC_UNCORRECTED_ERR_COUNT | NV_PFB_PRI_MMU_FILLUNIT_ECC_UNCORRECTED_ERR_COUNT_UNIQUE | dev_fb.h:100, 8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9 | 31:16 | 31:16 | 0 | true | true | yes |
| 11 | NV_PFB_PRI_MMU_HUBTLB_ECC_UNCORRECTED_ERR_COUNT | NV_PFB_PRI_MMU_HUBTLB_ECC_UNCORRECTED_ERR_COUNT_TOTAL | dev_fb.h:91, 8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9 | 15:0 | 15:0 | 0 | true | true | yes |
| 12 | NV_PFB_PRI_MMU_HUBTLB_ECC_UNCORRECTED_ERR_COUNT | NV_PFB_PRI_MMU_HUBTLB_ECC_UNCORRECTED_ERR_COUNT_UNIQUE | dev_fb.h:93, 8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9 | 31:16 | 31:16 | 0 | true | true | yes |
| 13 | NV_PFB_PRI_MMU_L2TLB_ECC_UNCORRECTED_ERR_COUNT | NV_PFB_PRI_MMU_L2TLB_ECC_UNCORRECTED_ERR_COUNT_TOTAL | dev_fb.h:84, 8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9 | 15:0 | 15:0 | 0 | true | true | yes |
| 14 | NV_PFB_PRI_MMU_L2TLB_ECC_UNCORRECTED_ERR_COUNT | NV_PFB_PRI_MMU_L2TLB_ECC_UNCORRECTED_ERR_COUNT_UNIQUE | dev_fb.h:86, 8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9 | 31:16 | 31:16 | 0 | true | true | yes |
| 15 | NV_PFB_PRI_MMU_PAGE_FAULT_CTRL | NV_PFB_PRI_MMU_PAGE_FAULT_CTRL_PRF_FILTER | dev_fb.h:35, 8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9 | 1:0 | 1:0 | 0 | true | true | yes |
| 16 | NV_PFB_PRI_MMU_WPR2_ADDR_HI | NV_PFB_PRI_MMU_WPR2_ADDR_HI_VAL | dev_fb.h:43, 8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9 | 31:4 | 31:4 | 2096864 | true | true | yes |
| 17 | NV_PFB_PRI_MMU_WPR2_ADDR_LO | NV_PFB_PRI_MMU_WPR2_ADDR_LO_VAL | dev_fb.h:40, 8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9 | 31:4 | 31:4 | 2063872 | true | true | yes |
| 18 | NV_PGC6_AON_SECURE_SCRATCH_GROUP_05_PRIV_LEVEL_MASK | NV_PGC6_AON_SECURE_SCRATCH_GROUP_05_PRIV_LEVEL_MASK_READ_PROTECTION | dev_gc6_island.h:29, 2a2b677175b6cb8936f4c9d5deb8b677a19ba74ec274c43d140140e620186e2d | 3:0 | 3:0 | 15 | true | true | yes |
| 19 | NV_PGSP_FALCON_MAILBOX0 | NV_PGSP_FALCON_MAILBOX0_DATA | dev_gsp.h:28, 7736a1d52aaae1d7ba89f3d231d924f74cf612e404ccde4043326bf234180cb0 | 31:0 | 31:0 | 0 | true | true | yes |
| 20 | NV_PGSP_FALCON_MAILBOX1 | NV_PGSP_FALCON_MAILBOX1_DATA | dev_gsp.h:30, 7736a1d52aaae1d7ba89f3d231d924f74cf612e404ccde4043326bf234180cb0 | 31:0 | 31:0 | 0 | true | true | yes |
| 21 | NV_VIRTUAL_FUNCTION_PRIV_ACCESS_COUNTER_CONFIG | NV_VIRTUAL_FUNCTION_PRIV_ACCESS_COUNTER_CONFIG_THRESHOLD | dev_vm.h:190, 8ea9a40bed9a857385f38f94d074081ac3d775676c6204ba72a2e883898faea6 | 15:0 | 15:0 | 18948 | true | true | yes |
| 22 | NV_VIRTUAL_FUNCTION_PRIV_ACCESS_COUNTER_CONFIG | NV_VIRTUAL_FUNCTION_PRIV_ACCESS_COUNTER_CONFIG_MIMC_GRANULARITY | dev_vm.h:192, 8ea9a40bed9a857385f38f94d074081ac3d775676c6204ba72a2e883898faea6 | 17:16 | 17:16 | 3 | true | true | yes |
| 23 | NV_VIRTUAL_FUNCTION_PRIV_ACCESS_COUNTER_CONFIG | NV_VIRTUAL_FUNCTION_PRIV_ACCESS_COUNTER_CONFIG_MOMC_GRANULARITY | dev_vm.h:198, 8ea9a40bed9a857385f38f94d074081ac3d775676c6204ba72a2e883898faea6 | 19:18 | 19:18 | 3 | true | true | yes |
| 24 | NV_VIRTUAL_FUNCTION_PRIV_CPU_INTR_LEAF_TRIGGER | NV_VIRTUAL_FUNCTION_PRIV_CPU_INTR_LEAF_TRIGGER_VECTOR | dev_vm.h:67, 8ea9a40bed9a857385f38f94d074081ac3d775676c6204ba72a2e883898faea6 | 11:0 | 11:0 | 143 | true | true | yes |
| 25 | NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE_PDB | NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE_PDB_ADDR | dev_vm.h:125, 8ea9a40bed9a857385f38f94d074081ac3d775676c6204ba72a2e883898faea6 | 31:4 | 31:4 | 21102848 | true | true | yes |
| 26 | NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE_UPPER_PDB | NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE_UPPER_PDB_ADDR | dev_vm.h:129, 8ea9a40bed9a857385f38f94d074081ac3d775676c6204ba72a2e883898faea6 | 19:0 | 19:0 | 77825 | true | true | yes |

All 26: header bitrange == dump bitrange; recomputed field value == dumped field value; semantic=true (register value not error-like/poison).

Related same-root-cause cases (semantic=false, excluded from the flagged list because register values are poison/error-like):

- NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE / NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE_REPLAY: header dev_vm.h:141 5:3, dump 5:3, value 0x0, register value 0xbadf5040 -> corrected source_match=true; no semantic field value trusted (error-like register).
- NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE / NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE_ACK: header dev_vm.h:151 8:7, dump 8:7, value 0x0, register value 0xbadf5040 -> corrected source_match=true; no semantic field value trusted (error-like register).
- NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE / NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE_CANCEL_CLIENT_ID: header dev_vm.h:155 14:9, dump 14:9, value 0x28, register value 0xbadf5040 -> corrected source_match=true; no semantic field value trusted (error-like register).
- NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE / NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE_CANCEL_GPC_ID: header dev_vm.h:156 19:15, dump 19:15, value 0x1e, register value 0xbadf5040 -> corrected source_match=true; no semantic field value trusted (error-like register).
- NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE / NV_VIRTUAL_FUNCTION_PRIV_MMU_INVALIDATE_CACHE_LEVEL: header dev_vm.h:169 26:24, dump 26:24, value 0x2, register value 0xbadf5040 -> corrected source_match=true; no semantic field value trusted (error-like register).
- NV_VIRTUAL_FUNCTION_TIME_0 / NV_VIRTUAL_FUNCTION_TIME_0_NSEC: header dev_vm.h:225 31:5, dump 31:5, value 0x5d6f888, register value 0xbadf1100 -> corrected source_match=true; no semantic field value trusted (error-like register).
- NV_VIRTUAL_FUNCTION_TIME_1 / NV_VIRTUAL_FUNCTION_TIME_1_NSEC: header dev_vm.h:227 28:0, dump 28:0, value 0x1adf1100, register value 0xbadf1100 -> corrected source_match=true; no semantic field value trusted (error-like register).

Side note: `NV_PGC6_BSI_SECURE_SCRATCH_14_BOOT_STAGE_3_HANDOFF` was listed as an 'unsupported source range expression';
bsi field dev_gc6_island_addendum.h:33 '26:26' is a plain single-bit field, not an unsupported range expression; dump bitfield 26:06 value=1 matches header.

## 5. Sampling coverage (exact bytes, no whole-page claims)

- BAR0: 4096 pages x 4096 bytes = 16777216 bytes (16 MiB).
- Sample: 4 u32 per page = 16 bytes observed per page.
- Observed bytes total: 65536 / 16777216 = 0.3906250000% of BAR0.
- Unobserved: 16711680 bytes = 99.6093750000% (4080 bytes per page).
- Each page is known only at its 4 sampled u32. Classifications are sample-level; no page or block is labeled physically absent, unmapped, poison, or zero from the sample.

## 6. The 49 unclassified pages (individual accounting)

- All 49 pages have a tu06 record and 4 sampled values: missing records = 0.
- 'Unmapped' is not determinable from a 16-byte sample; no page is labeled unmapped or physically absent.
- Pages were left unclassified because they are DATA-state small regions below the p9_reclass grouping threshold.

Buckets (sample-level only): {'poison (sample-level)': 1, 'data-like (sample-level)': 46, 'uninit_all_ones (sample-level)': 2}

| page | offset | sample class | sample values (4 u32) | bucket |
|------|--------|--------------|-----------------------|--------|
| 7 | 0x007000 | POISON_BAD00100_like | 0xbad00100,0xbad00100,0xbad00100,0xbad00100 | poison (sample-level) |
| 140 | 0x08c000 | MIXED_data_like | 0x00000002,0x00000004,0x000001cc,0x000001f4 | data-like (sample-level) |
| 282 | 0x11a000 | MIXED_data_like | 0xc0100080,0x00073000,0x00008000,0x00001000 | data-like (sample-level) |
| 499 | 0x1f3000 | MIXED_data_like | 0x02024001,0x00001000,0x02000000,0x00200000 | data-like (sample-level) |
| 768 | 0x300000 | MIXED_data_like | 0xeb7aaa55,0x30000002,0x14b60f2e,0xc683048b | data-like (sample-level) |
| 769 | 0x301000 | MIXED_data_like | 0x56464604,0x65082cf2,0x01f48003,0xc426105f | data-like (sample-level) |
| 771 | 0x303000 | MIXED_data_like | 0x56c35eff,0x04c48a02,0xc1480074,0x59e859f4 | data-like (sample-level) |
| 774 | 0x306000 | MIXED_data_like | 0x72000000,0xff0fff60,0x00809096,0x8b2666fc | data-like (sample-level) |
| 775 | 0x307000 | MIXED_data_like | 0x3d66001f,0x00ff0000,0x0c800400,0xc0406e00 | data-like (sample-level) |
| 776 | 0x308000 | MIXED_data_like | 0xfc001371,0x0013714c,0x00000006,0xb4b4b4e4 | data-like (sample-level) |
| 780 | 0x30c000 | MIXED_data_like | 0xaaaaaaaa,0xff000001,0x7472cab3,0x8f3b7572 | data-like (sample-level) |
| 781 | 0x30d000 | MIXED_data_like | 0x07070707,0x1c191919,0xa4000000,0x0000011d | data-like (sample-level) |
| 817 | 0x331000 | MIXED_data_like | 0xcea7ad5d,0x5ab0894d,0xbf93abfc,0xaa06c8d3 | data-like (sample-level) |
| 818 | 0x332000 | MIXED_data_like | 0x5806265f,0x46a66937,0xd40b874e,0xe350e869 | data-like (sample-level) |
| 844 | 0x34c000 | MIXED_data_like | 0xf4d9ff00,0xc0d90026,0x09039a98,0xf4002555 | data-like (sample-level) |
| 845 | 0x34d000 | MIXED_data_like | 0x103329a0,0xc7feffff,0x9ffd8000,0xfbe9a004 | data-like (sample-level) |
| 846 | 0x34e000 | MIXED_data_like | 0x00001b5a,0x7556a662,0xb0c7da04,0x6f651795 | data-like (sample-level) |
| 848 | 0x350000 | MIXED_data_like | 0xffffffff,0xffffffff,0xffffffff,0x01844d01 | data-like (sample-level) |
| 849 | 0x351000 | MIXED_data_like | 0x16b72561,0x9388795c,0x3d76d72d,0xc0ef0471 | data-like (sample-level) |
| 850 | 0x352000 | MIXED_data_like | 0x00001288,0x07fb449c,0x3fcf963f,0x32e078b2 | data-like (sample-level) |
| 852 | 0x354000 | MIXED_data_like | 0xffffffff,0xffffffff,0xffffffff,0x0188d7f9 | data-like (sample-level) |
| 889 | 0x379000 | MIXED_data_like | 0xeb7aaa55,0x30000002,0x14b60f2e,0xc683048b | data-like (sample-level) |
| 890 | 0x37a000 | MIXED_data_like | 0x56464604,0x65082cf2,0x01f48003,0xc426105f | data-like (sample-level) |
| 892 | 0x37c000 | MIXED_data_like | 0x56c35eff,0x04c48a02,0xc1480074,0x59e859f4 | data-like (sample-level) |
| 895 | 0x37f000 | MIXED_data_like | 0x72000000,0xff0fff60,0x00809096,0x8b2666fc | data-like (sample-level) |
| 896 | 0x380000 | MIXED_data_like | 0x3d66001f,0x00ff0000,0x0c800400,0xc0406e00 | data-like (sample-level) |
| 897 | 0x381000 | MIXED_data_like | 0xfc001371,0x0013714c,0x00000006,0xb4b4b4e4 | data-like (sample-level) |
| 901 | 0x385000 | MIXED_data_like | 0xaaaaaaaa,0xff000001,0x7472cab3,0x8f3b7572 | data-like (sample-level) |
| 902 | 0x386000 | MIXED_data_like | 0x07070707,0x1c191919,0xa4000000,0x0000011d | data-like (sample-level) |
| 938 | 0x3aa000 | MIXED_data_like | 0xcea7ad5d,0x5ab0894d,0xbf93abfc,0xaa06c8d3 | data-like (sample-level) |
| 939 | 0x3ab000 | MIXED_data_like | 0x5806265f,0x46a66937,0xd40b874e,0xe350e869 | data-like (sample-level) |
| 965 | 0x3c5000 | MIXED_data_like | 0xf4d9ff00,0xc0d90026,0x09039a98,0xf4002555 | data-like (sample-level) |
| 966 | 0x3c6000 | MIXED_data_like | 0x103329a0,0xc7feffff,0x9ffd8000,0xfbe9a004 | data-like (sample-level) |
| 967 | 0x3c7000 | MIXED_data_like | 0x00001b5a,0x7556a662,0xb0c7da04,0x6f651795 | data-like (sample-level) |
| 979 | 0x3d3000 | UNINIT_FF_like | 0xffffffff,0xffffffff,0xffffffff,0xffffffff | uninit_all_ones (sample-level) |
| 980 | 0x3d4000 | UNINIT_FF_like | 0xffffffff,0xffffffff,0xffffffff,0xffffffff | uninit_all_ones (sample-level) |
| 1040 | 0x410000 | UNIFORM_data_like | 0x32080a00,0x32080a00,0x32080a00,0x32080a00 | data-like (sample-level) |
| 1041 | 0x411000 | UNIFORM_data_like | 0x32080a00,0x32080a00,0x32080a00,0x32080a00 | data-like (sample-level) |
| 2304 | 0x900000 | MIXED_data_like | 0x00000043,0x00001707,0x00000004,0x120a130f | data-like (sample-level) |
| 2308 | 0x904000 | MIXED_data_like | 0x00000043,0x00001707,0x00000004,0x0c2d262a | data-like (sample-level) |
| 2312 | 0x908000 | MIXED_data_like | 0x00000043,0x00001707,0x00000004,0x2d2e0111 | data-like (sample-level) |
| 2316 | 0x90c000 | MIXED_data_like | 0x00000043,0x00001707,0x00000004,0x182c2711 | data-like (sample-level) |
| 2432 | 0x980000 | MIXED_data_like | 0x00000043,0x00001707,0x00000004,0x120a130f | data-like (sample-level) |
| 2436 | 0x984000 | MIXED_data_like | 0x00000043,0x00001707,0x00000004,0x120a130f | data-like (sample-level) |
| 2440 | 0x988000 | MIXED_data_like | 0x00000043,0x00001707,0x00000004,0x120a130f | data-like (sample-level) |
| 2464 | 0x9a0000 | MIXED_data_like | 0x00000043,0x00001707,0x00000004,0x120a130f | data-like (sample-level) |
| 2912 | 0xb60000 | MIXED_data_like | 0x75b15eab,0xdf4bfb06,0x5d8c7f08,0xa5abcf8b | data-like (sample-level) |
| 3008 | 0xbc0000 | MIXED_data_like | 0x46840574,0x5ffb8cb0,0xf84a19b0,0xd587cfe8 | data-like (sample-level) |
| 3009 | 0xbc1000 | MIXED_data_like | 0x58e56b40,0x42031158,0x9d92b50c,0xe788475c | data-like (sample-level) |

## 7. Classification counts reconciliation

Raw tu06 state counts: POISON=3253, DATA=287, ZERO=355, MIXED=201 (sum 4096).
p9_reclass zone moves (DATA -> corrected): {'POISON': 25, 'UNINIT_FF': 72, 'DATA': 141}.

| class | count |
|-------|-------|
| POISON | 3278 |
| UNINIT_FF | 72 |
| DATA | 141 |
| ZERO | 355 |
| MIXED | 201 |
| UNCLASSIFIED | 49 |
| total | 4096 |

- Classified pages: 4047; unclassified: 49. Displays must show UNCLASSIFIED=49 explicitly; 4047 classified is not full BAR0 coverage.
- Raw DATA=287 = corrected DATA=141 + UNINIT_FF=72 + UNCLASSIFIED=49; 25 DATA pages moved to POISON by p9_reclass POISON_MOI zones (3253 -> 3278).
- Poison share: 3278/4047 = 0.8099827032 of classified pages; 3278/4096 = 0.8002929688 of all 4096 pages.

## 8. WPR2: architectural definition / captured value / semantic interpretation

### NV_PFB_PRI_MMU_WPR2_ADDR_LO
- Address: 2074660 (0x1FA824).
- Architectural definition: dev_fb.h:40 `31:4` (VAL[31:4], 28-bit field); alignment dev_fb.h:41 (shift 12).
- Header sha256: 8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9.
- Captured value: raw 33021952 (0x1f7e000), state data, error_like False.
- Semantic interpretation: field 2063872 (0x1f7e00) << 12 = decoded 8453619712 (0x1f7e00000).
- Bound semantics: decoded bound from header formula only; inclusive/exclusive bound semantics not established locally.
### NV_PFB_PRI_MMU_WPR2_ADDR_HI
- Address: 2074664 (0x1FA828).
- Architectural definition: dev_fb.h:43 `31:4` (VAL[31:4], 28-bit field); alignment dev_fb.h:44 (shift 12).
- Header sha256: 8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9.
- Captured value: raw 33549824 (0x1ffee00), state data, error_like False.
- Semantic interpretation: field 2096864 (0x1ffee0) << 12 = decoded 8588754944 (0x1ffee0000).
- Bound semantics: decoded bound from header formula only; inclusive/exclusive bound semantics not established locally.

Bound difference: 135135232 bytes = 128.875 MiB (LO -> HI). Inclusive/exclusive not established locally; Linux Nova treating HI as exclusive is external context, not local evidence. No reserved allocation subtracted locally.

## 9. Topology semantics (unchanged unknowns)

- L2 TLB (dev_fb.h:82, 0x100E78) and L2 cache (dev_ltc.h:27, 0x1404F8) are kept separate; never conflated.
- GPC/TPC/SM/ROP counts: UNKNOWN. dev_top.h/dev_graph.h are absent from the local header snapshot; dev_fault.h holds fault client IDs, not engine counts; NVML sm_count is a log value, not a register definition.

## 10. Conclusion

- Namespace preserved: 42 MMIO_BAR0 registers, 3 BAR0 bases, 3 constants, 3 control-space, 1 PCI config (52 total).
- All 26 semantic=true/source_match=false flags corrected to source_match=true (parser transpose artifact), each with exact header file:line/sha256; TU106 applicable; no classification change.
- Exact observed coverage: 65536/16777216 bytes (0.3906250000%), sample-level only.
- 49 unclassified pages accounted individually: 0 missing records, 0 determinable unmapped, none labeled physically absent.
- whole_gpu_complete: false.

## 11. Outputs

- mmio_coverage_reconcile.py  (this script)
- mmio_coverage_reconcile.json  (machine-readable result)
- MMIO_COVERAGE_RECONCILE_REPORT.md (this report)
- mmio_coverage_reconcile_run.log (run log)

All outputs under: /home/REDACTED_USER/codex-work/work_v15/PHASE16/MMIO_COVERAGE_RECONCILE

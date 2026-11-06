PHASE16 — OFFICIAL PUBLIC SOURCE CONSUMER EVIDENCE (NVIDIA/open-gpu-kernel-modules 615.78.08)
============================================================================================

1. IDENTITY / SCOPE
-------------------
Repository : NVIDIA/open-gpu-kernel-modules
Release    : 615.78.08
Tag/commit : ca2d03e6fafd4d4b56b383497d931c25b283bfcf
Immutable base : https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/ca2d03e6fafd4d4b56b383497d931c25b283bfcf/<path>
Commit page  : https://github.com/NVIDIA/open-gpu-kernel-modules/commit/ca2d03e6fafd4d4b56b383497d931c25b283bfcf

Identity caveat (stated explicitly): matching public headers to tag 615.78.08 does NOT
establish whole-binary identity. This report only documents what public text source
contains; it does not assert that these sources build the local binary, nor does it
infer missing generated descriptor instances or firmware-slot roles. No source/config
mutation, hardware access, key/signature handling, bypass, or binary loading performed.

2. SAVED PUBLIC TEXT SOURCE (under /home/REDACTED_USER/codex-work/work_v15/PHASE16/OFFICIAL_CONSUMER_SOURCE/)
-----------------------------------------------------------------------------------------------------
saved-as                      sha256                                                     source path in repo
bin_data.c                    080ad8e8d357bb379e2aec1da54766a18624bb31c40e189bc19554c65e4d1b55  src/nvidia/src/kernel/core/bin_data.c
bin_data_pvt.h                0a46eff1c9db21f4b19d23d42c75d411685755f98f08b76247ace36a4fe1691a  src/nvidia/src/kernel/core/bin_data_pvt.h
ctrl2080fb.h                  9e9783e9c6b57078226dce4c181a1a3136d73cea2593fec70a122033d8788ce0  src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080fb.h
dev_fb_gh100.h                d1b0dfdeb0345ac0f8e7ae01af863e56587f43e35c9da732898f02c67b08f0eb  src/common/inc/swref/published/hopper/gh100/dev_fb.h
dev_fb_tu102.h                8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9  src/common/inc/swref/published/turing/tu102/dev_fb.h
dev_hubmmu_base_gb100.h       2b2e42622f32331573ba0da0d3c445c1cabb8dbf6ce3ccbc7b506b6db62f4b70  src/common/inc/swref/published/blackwell/gb100/dev_hubmmu_base.h
gsp_fw_heap.h                 7afe46bda5d760e585bc5fb3e5494c501f415c99b705a441e991cccb2d201e8d  src/nvidia/inc/kernel/gpu/gsp/gsp_fw_heap.h
gsp_fw_wpr_meta.h             f3b615a6d87b557ddab986b6ba6a5209901f09edcf0e5b9c983e0d8112538fc5  src/nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta.h
gsp_fw_wpr_meta_v1.h          04e2da01f1c1cedc6b740b1bab881f868419d93fb4701fbe1885bed09063f2b3  src/nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta_v1.h
kernel_gsp.c                  ed6d7020a8a1772bc44608178aa13a77a72b8bf0eabe3293c12bc9d2b122c6c9  src/nvidia/src/kernel/gpu/gsp/kernel_gsp.c
kernel_gsp_gh100.c            5ee22f09c650ab70764be05828cc58e1237436bada08c91898aeadc011d37ea2  src/nvidia/src/kernel/gpu/gsp/arch/hopper/kernel_gsp_gh100.c

3. TARGET 1 — WPR2_ADDR_HI/LO consumers
----------------------------------------
Register definitions (public headers only; NO consumer code found in public .c):
  dev_fb_gh100.h (hopper GH100):
    L43 #define NV_PFB_PRI_MMU_WPR2_ADDR_LO  0x001FA824 /* RW-4R */
    L45 #define NV_PFB_PRI_MMU_WPR2_ADDR_LO_VAL  31:4
    L48 #define NV_PFB_PRI_MMU_WPR2_ADDR_HI  0x001FA828 /* RW-4R */
    L50 #define NV_PFB_PRI_MMU_WPR2_ADDR_HI_VAL  31:4
  dev_fb_tu102.h (turing TU102): same offsets 0x001FA824 / 0x001FA828, VAL 31:4 (L39-L44)
  dev_hubmmu_base_gb100.h (blackwell GB100):
    L91 #define NV_HUBMMU_PRI_MMU_WPR2_ADDR_LO  0xa824
    L94 #define NV_HUBMMU_PRI_MMU_WPR2_ADDR_HI  0xa828, VAL 31:4 (L95)

Consumer search result: EXHAUSTIVE grep of every fetched public .c (subdevice.c, all
subdevice_ctrl_*.c, kernel_gsp.c, all gsp arch .c, kern_gpu_arch_*.c, device.c,
device_ctrl.c, bin_data.c) for WPR2_ADDR / WPR2_ADDR_LO / WPR2_ADDR_HI = NOTHING.
Conclusion: no public CPU-side consumer of the WPR2_ADDR_HI/LO registers exists in tag
615.78.08 source. WPR2 programming is delegated: kgspPopulateWprMeta_GH100
(kernel_gsp_gh100.c L386-L387) states "The actual offsets get filled in by ACR ucode
when it sets up WPR2." The register-level WPR2 writes live in closed bootloader/ACR/GSP
firmware, not public source. Reported as explicitly unavailable at consumer level.

4. TARGET 2 — subdeviceCtrlCmdFbGetWprRegionInfo_IMPL body
-----------------------------------------------------------
Command + params (public): NV2080_CTRL_CMD_FB_GET_WPR_REGION_INFO = 0x20801364U
  ctrl2080fb.h L3083
  Params struct NV2080_CTRL_FB_GET_WPR_REGION_INFO_PARAMS L3087-L3093:
    L3088 NvU64 wpr1Start
    L3089 NvU64 wpr1End
    L3090 NvU64 wpr2Start
    L3091 NvU64 wpr2End
    L3092 NvU64 fbRegionOfWpr2Start
  Comments L3072-L3081 explicitly mark wpr1End / wpr2End as "FB offset of the end
  (exclusive) of WPR1/WPR2".

Implementation body: NOT FOUND in public source.
  Declaration exists in nvoc generated header (subdeviceCtrlCmdFbGetWprRegionInfo_IMPL,
  g_subdevice_nvoc.h — seen in local /tmp/nvsrc headers; local headers match tag but do
  not establish binary identity).
  Searched and NOT present in any public .c of tag ca2d03e: subdevice.c (full read,
  resource management only, no FB/WPR), all src/nvidia/src/kernel/gpu/subdevice/subdevice_ctrl_*.c,
  kernel_gsp.c (full grep), gsp arch .c, kern_gpu_arch_*.c, device.c, device_ctrl.c.
Conclusion: subdeviceCtrlCmdFbGetWprRegionInfo_IMPL body is NOT in public CPU-side
source of tag 615.78.08. The command/params are public; the handler body is closed
(GSP-firmware-backed or proprietary RM). Reported as explicitly unavailable.

5. TARGET 3 — GSP WPR allocation / start / end setup (public source)
---------------------------------------------------------------------
Flow (kernel_gsp.c _kgspBootGspRm, L5428-L5508):
  L5439-L5441 kgspIsWpr2Up_HAL guard — fail if WPR2 already up.
  L5454 kgspPopulateWprMeta_HAL(pGpu, pKernelGsp, pGspFw) — populates GspFwWprMeta.
  L5463 kgspPrepareForBootstrap_HAL; L5483 kgspBootstrap_HAL.

kgspPopulateWprMeta_GH100 (kernel_gsp_gh100.c L366-L471) — Hopper+ WPR meta population:
  L388 pWprMeta->vgaWorkspaceSize = 128*1024
  L389 pWprMeta->pmuReservedSize = kpmuReservedMemorySizeGet(...)
  L392-L394 sizeOfBootloader = gspRmBootUcodeSize; sysmem addr from memdesc
  L397-L399 sizeOfRadix3Elf = imageSize; sysmem addr of radix3 ELF
  L402-L404 bootloader code/data/manifest offsets from RISC-V ucode desc
  L413 pWprMeta->nonWprHeapSize = kgspGetNonWprHeapSize(...)
  L426 pWprMeta->gspFwHeapSize = kgspGetFwHeapSize(pGpu, pKernelGsp, 0, 0)  (min size; 0 allows extension)
  L429 pWprMeta->frtsSize = kgspGetFrtsSize_HAL(...)
  L456-L457 revision = GSP_FW_WPR_META_REVISION (1); magic = GSP_FW_WPR_META_MAGIC
  L459 pagingConfig; L461-L468 PPCIE flag
  Comment L385-L387: "We send these to FSP as the size to reserve above FRTS. The
  actual offsets get filled in by ACR ucode when it sets up WPR2."

GspFwWprMeta struct (gsp_fw_wpr_meta.h L60-L210), exactly 256 bytes (L208):
  L107 gspFwRsvdStart ; L109 nonWprHeapOffset ; L110 nonWprHeapSize
  L112 gspFwWprStart  ; L115 gspFwHeapOffset ; L116 gspFwHeapSize
  L119 gspFwOffset    ; L122 bootBinOffset ; L125 frtsOffset ; L126 frtsSize
  L128 gspFwWprEnd    ; L131 fbSize ; L136 vgaWorkspaceOffset ; L137 vgaWorkspaceSize
  L203 pmuReservedSize ; L206 verified (0xa0a0a0a0a0a0a0a0 = verified)
  L212 GSP_FW_WPR_META_VERIFIED ; L213 _REVISION 1 ; L214 _MAGIC 0xdc3aae21371a60b3
  GspFwWprMetaV1 (gsp_fw_wpr_meta_v1.h) same 256-byte layout for Turing-Ada.

Alignment semantics (comments L38-L58 of gsp_fw_wpr_meta.h):
  gspFwWprStart 128K aligned; gspFwWprEnd 128K aligned; fbSize 1M aligned.
  WPR2 sits at end of FB; meta DMA'd "at the end of what will be WPR2".

Heap sizing constants (gsp_fw_heap.h): per-GB 96<<10 (L51), client alloc (48<<10)*2048 (L71),
base RM sizes TU10X 8<<20 / GH100 18<<20 / GR10X 32<<20 (L41-L43).
kernel_gsp.c heap: L7304 NV_ALIGN_UP(...PER_GB*memSizeGB, 1<<20); L7307 +CLIENT_ALLOC_SIZE;
L7312 NV_MAX(minGspFwHeapSizeMB<<20); L7315 NV_MIN(maxGspFwHeapSizeMB<<20);
L7423 heapSizeMBOverride<<20.

GSP WPR end margin / raw->end conversion: kgspGetWprEndMargin_GH100 (kernel_gsp_gh100.c L1311-L1353)
  L1322 wprEndMargin = DRF_VAL(_REG,_RM_GSP_WPR_END_MARGIN,_MB,wprEndMarginOverride) << 20;
  i.e. regkey raw value in MB converted to bytes by << 20 (multiply by 1 MiB).
  If 0, estimate from kpmuReservedMemorySizeGet + kgspGetFrtsSize_HAL + gspRmBootUcodeSize +
  sizeOfRadix3Elf + kgspGetFwHeapSize + kgspGetNonWprHeapSize (L1331-L1336).
  margin applied after end of WPR2 (recovery margin flag, L1345-L1348).

srRegionsInfo population (Hopper+, kernel_gsp_gh100.c L1362-L1383):
  L1373 nonWprHeapSize = pWprMeta->nonWprHeapSize ; L1374 vgaWorkspaceSize ; L1375 frtsSize
  L1378-L1382: if PDB_PROP_GPU_FW_WPR_OFFSET_SET_BY_ACR, nonWprHeapOffset/frtsOffset come
  from pGSCI->fwWprLayoutOffset (set by ACR), NOT computed in public source.

6. TARGET 4 — BINDATA_STORAGE_PVT / NVUCODES file loading + index lookup
-------------------------------------------------------------------------
Struct (bin_data_pvt.h L60-L67):
  L62 NvU32 actualSize        // size of (uncompressed) pData
  L63 NvU32 compressedSize    // size of (compressed) pData array
  L64 const void * pData      // pointer to raw binary (compressed or not)
  L65 NvU32 flags
  L66 NvU32 relOffset         // Offset of bin within bindata file
  Flags (L55-L59): COMPRESSED 0x01, REFERENCED 0x02, EXTERNAL 0x04, EXTERNAL_VMWARE 0x08, HEAP_ALLOCATED 0x10
  BINDATA_IS_MUTABLE = RMCFG_FEATURE_PLATFORM_GSP (L75); .bindata section when mutable.

NVUCODES container header (bin_data_pvt.h L84-L114, BINDATA_UCODES_BIN_HEADER):
  L88 magic = 0x5345444F4355564E ('NVUCODES')
  L97 version = 1
  L103 numEntries — "Number of possible bindata files ... each file has a unique index ... embedded inside gsp.bin"
  L105-L113 fingerprint — NvU64 hash of filenames in index-order; embedded in gsp.bin; pairs ucodes.bin with gsp.bin.

Public read / index-lookup paths (bin_data.c):
  bindataWriteToBuffer (L63-L106): reads pBinStoragePvt->pData (via _bindataGetBindataPtr L47-L50);
    if COMPRESSED -> utilGzGetData(pData, bufferSize, 0, bufferSize, pBuffer) — read offset passed is 0, NOT relOffset (L87-L91);
    else portMemCopy(pBuffer, bufferSize, pData, bufferSize) (L102).
  bindataGetBufferSize (L108-L123): returns ((BINDATA_STORAGE_PVT*)pBinStorage)->actualSize (L122).
  bindataArchiveGetStorage (L135-L159): index lookup by NAME — iterates pBinArchive->entries[i],
    matches bindataLabel == entries[i].bindataLabel (BINDATA_LABEL enum), returns entries[i].pBinStorage (L155).
    No per-entry name string in the public struct; lookup is by BINDATA_LABEL enum value.
  bindataGetNextUnreferencedStorage (L252-L274): walks g_bindata_pvt[*pIdx]; comment L260
    "Valid index for g_bindata_pvt starts from 1"; returns pData and compressedSize (L266-L267).
  bindataDestroyStorage (L276-L291): zeroes g_bindata_pvt[idx] (pData=NULL, actualSize=0, compressedSize=0, L287-L289).

relOffset / actualSize read-path determination:
  actualSize IS read (bindataGetBufferSize -> L122) and reported as uncompressed size.
  relOffset is present in the struct (documented "Offset of bin within bindata file") but is NOT read
  by any public bindata consumer in bin_data.c (only written to 0 in bindataDestroyStorage L289).
  Reads use the pData pointer directly; compressed reads start at offset 0. relOffset consumer
  is therefore absent from public source — recorded as explicitly unavailable at read-path level.
  Source index naming: not present as a name field; index lookup is by BINDATA_LABEL enum
  (bindataArchiveGetStorage) and by ordinal position in g_bindata_pvt[] (index starts at 1).

7. CONVERSION / SEMANTICS SUMMARY
---------------------------------
 raw-HI -> API-end: kgspGetWprEndMargin_GH100 converts regkey raw (MB) to bytes via << 20
   (kernel_gsp_gh100.c L1322). Heap sizes likewise use << 20 (kernel_gsp.c L7312/L7315/L7423).
   No explicit "+page adjustment" found in public WPR end computation; alignment is 128K for
   gspFwWprStart/gspFwWprEnd and 1M for fbSize (gsp_fw_wpr_meta.h comments L38-L58).
 inclusive/exclusive: END is EXCLUSIVE. ctrl2080fb.h L3072-L3081 documents wpr1End/wpr2End as
   "FB offset of the end (exclusive) of WPR1/WPR2".
 container external relOffset/actualSize: actualSize read at bin_data.c L122; relOffset NOT read
   by public path (struct field only). Index naming: BINDATA_LABEL enum / g_bindata_pvt ordinal
   (from 1); no source name string in public struct.

8. EXPLICIT UNAVAILABILITY (do not infer)
-----------------------------------------
 a) subdeviceCtrlCmdFbGetWprRegionInfo_IMPL body — absent from all public .c of tag ca2d03e
    (command + params struct ARE public: ctrl2080fb.h L3083-L3093).
 b) WPR2_ADDR_HI/LO register consumers — register macros public (dev_fb.h gh100/tu102,
    dev_hubmmu_base.h gb100); no public .c reads/writes them; WPR2 offsets filled by ACR ucode.
 c) Actual gspFwWprStart/gspFwWprEnd offset computation — filled by ACR ucode at boot
    (kernel_gsp_gh100.c L386-L387); public source only supplies sizes.
 d) relOffset read-path consumer and per-entry source name string — absent from public bindata.c.
 e) Generated descriptor instances / firmware-slot roles — NOT inferred (out of scope per instructions).

All saved files are verbatim public text from tag ca2d03e6fafd4d4b56b383497d931c25b283bfcf.
SHA256 values computed over the saved byte content; immutable URLs above allow re-verification.

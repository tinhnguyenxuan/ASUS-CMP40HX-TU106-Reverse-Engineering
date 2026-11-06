# PHASE16/TOPOLOGY_CONSUMER_SEARCH — extraction commands (reproducible, offline read-only where possible)
# Official public source fetched once from NVIDIA GitHub (tag 615.78.08, commit 1a82fbf...), then ALL
# searching is local grep over the checked-out tree plus the already-saved /tmp/nvsrc and /tmp/envytools.
# No hardware access, no MMIO/PCI reads/writes, no driver changes, no firmware loading.

# --- 1. Fetch official public source (NVIDIA open-gpu-kernel-modules, tag 615.78.08) ---
git clone --filter=blob:none --no-checkout --single-branch --branch 615.78.08 https://github.com/NVIDIA/open-gpu-kernel-modules.git /tmp/ogkm-6157808
cd /tmp/ogkm-6157808
git sparse-checkout init --cone
git sparse-checkout set kernel-open/common/inc kernel-open/nvidia src/common/inc/swref/published/turing/tu102 src/nvidia/src/kernel/gpu/gr src/nvidia/inc src/nvidia/src/kernel
git checkout 615.78.08
# provenance records
git ls-remote https://github.com/NVIDIA/open-gpu-kernel-modules.git refs/tags/615.78.08
git rev-parse 615.78.08 615.78.08^{commit}
git log -1 --format='%H %ci %s' 615.78.08

# --- 2. Search terms for the five cited TU106 topology readings ---
#   MMIO 0x00409604 (gpc_nr), MMIO 0x00502608 (tpc_nr)
#   TPC_UNIT stride expression 0x504000 + g*0x8000 + t*0x800
#   fuse base+0x650 (abs 0x00021650) and base+0xc1c (abs 0x00021C1c), fuse base 0x00021000

# --- 3. Local greps over checked-out official tree (tags 615.78.08) ---
cd /tmp/ogkm-6157808
grep -rniE 'gpc_nr|tpc_nr|gpcnr|tpcnr|0x409604|0x502608|0x504000|TPC_UNIT' src/ kernel-open/ \
  | tee /tmp/ogkm-6157808-results/symbol_addrs.txt   # -> NO HITS
grep -rniE '0x650|0xc1c|0xC1C' src/ kernel-open/ \
  | grep -viE 'clc1c0|minion_production|soeuc|nv-tegra|tegra' \
  | tee /tmp/ogkm-6157808-results/fuse_offsets.txt    # -> only blackwell/gb10b NV_FUSE_STATUS_OPT_GPC 0x00820c1c (excluded: not TU106)

# --- 4. Header inventory at this tag ---
find /tmp/ogkm-6157808/src/common/inc/swref/published/turing/tu102 -maxdepth 1 -type f -name 'dev_*.h' -printf '%f\n' | sort   # tu102: NO dev_top.h/dev_gr.h/dev_graph.h
find /tmp/ogkm-6157808/src/common/inc/swref/published -name 'dev_top.h' | sort                                              # dev_top.h: ampere/ga100, blackwell/gb100 only
find /tmp/ogkm-6157808/src/common/inc/swref/published -name 'dev_gr.h' | sort                                               # -> NONE at this tag
find /tmp/ogkm-6157808/src/common/inc/swref/published -name 'dev_graph.h' | sort                                            # -> NONE at this tag

# --- 5. Cross-check saved offline copies against official tree (byte-identity) ---
sha256sum /tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_fuse.h \
          /tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_fault.h \
          /tmp/ogkm-6157808/src/common/inc/swref/published/turing/tu102/dev_fuse.h \
          /tmp/ogkm-6157808/src/common/inc/swref/published/turing/tu102/dev_fault.h

# --- 6. Offline saved source trees already present ---
grep -rniE 'gpc_nr|tpc_nr|0x409604|0x502608|0x504000|TPC_UNIT' /tmp/nvsrc /tmp/envytools  # -> NO HITS
ls /tmp/envytools/rnndb/graph/                                                         # -> pre-Turing only (g80/gf100)

# --- 7. Related (non-MMIO) topology consumers found in public source (context only, not a decode) ---
grep -n 'NV2080_CTRL_GR_INFO_INDEX_LITTER_NUM_GPCS\|NV2080_CTRL_GR_GET_NUM_TPCS_FOR_GPC\|tpcCount\|gpcMask\|floorsweepingMasks' \
  /tmp/ogkm-6157808/src/nvidia/src/kernel/gpu/gr/kernel_graphics_manager.c \
  /tmp/ogkm-6157808/src/nvidia/src/kernel/gpu/gr/kernel_graphics.c
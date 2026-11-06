# Capability gates — partial source/dataflow evidence

Version pin for the browsed official sources: open-gpu-kernel-modules tag 615.78.08. The local /tmp/nvsrc tree is a partial header tree and contains a third-party Booter header; it is not a pristine complete stock source checkout. Its version header alone does not validate all its contents.

| Gate | Input and decision | Scope and limitation |
|---|---|---|
| kdispConstructEngine_IMPL | KDISP_IS_MISSING property causes NV_ERR_NOT_SUPPORTED | Host display construction; origin of property and target value unknown |
| kdispStatePreInitLocked_IMPL | False gpuFuseSupportsDisplay_HAL result returns unsupported before physical-RM display-IP control | Host policy path; HAL name alone does not prove direct OTP access on TU106 |
| Same preinit | Physical RM control INTERNAL_DISPLAY_GET_IP_VERSION; failing status returned; success feeds gpuInitDispIpHal | Must identify physical RM backend for actual GSP/client configuration and capture status; cannot assume every error is fused silicon |
| gpuGetChildrenPresent_TU106 | Static list includes KernelDisplay | Software architecture list only; does not prove enabled hardware on every SKU |
| CMP classification | Local gsp_static_config.h contains bIsCmpSku; generated GPU header declares FWCLIENT and GV100 methods | Interface and dispatch declarations only; classification producer, transport and consumers not traced yet |
| Secure GSP debug | kgspIsDebugModeEnabled_TU102 reads SECURE_GSP_DEBUG_DIS and tests DATA_NO | Concrete source consumer of debug-disable field; not a CUDA or display enable gate |

Official source anchors:

- https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/disp/kern_disp.c (construction and preinit)
- https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/arch/turing/kern_gpu_tu102.c (TU106 child list)
- https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/arch/turing/kernel_gsp_tu102.c (debug consumer)

No original GSP-RM function address, argument provenance or branch for CMP display capability has been recovered here. GSP strings such as RmDisableSec2/RmActivateHulk in earlier reports are not host-callable interfaces or proof of reachable functionality. SEC2 security setup, FECS/GPCCS execution configuration, host RM gates and userspace developer-tool policy remain distinct.

## TU106 display fuse dispatch resolved

Official 615.78.08 generated `g_gpu_nvoc.c` explicitly selects `gpuFuseSupportsDisplay_GM107` for TU106. The GM107 function tests STATUS_OPT_DISPLAY.DATA against ENABLE; it does not use the function name to choose a chip at runtime. This is the missing cross-generation applicability evidence.

The saved header defines register 0x21c04, field bit0, ENABLE=0. Archived fuse2.json contains value 1. Therefore the source predicate is false for that archived read. `tools/check_display_gate.py` reproduces this evaluation and records input hashes. Exact official tag header bytes still need acquisition; the locally saved header is the current numeric-definition evidence.

This supports a display capability gate driven by a fuse-status register, upstream of display IP discovery. It does not prove that physical OTP is programmed, that the register cannot be shadowed, that the current card state matches the old read, or that display silicon/PHY is absent. Do not classify SILICON_DISABLED on this evidence.

Dispatch source: https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/generated/g_gpu_nvoc.c . Helper source: https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/arch/maxwell/kern_gpu_gm107.c . Browsed 2026-11-04. CMP query dispatch in the same generated source selects FWCLIENT except the VF false stub; producer and downstream consumers remain unresolved.

## Matched project firmware identity

The saved project GSP independently declares fwversion 615.78.08 (FIRMWARE_PROVENANCE_REPORT.md). Display/profiler/SEC2 configuration names exist. The `RmDisableDisplay` consumers, typed read path, NVKV ingestion and host producer are now traced in the follow-up reports below; other names and branches remain incomplete. This supersedes any assumption that the local project GSP is the 570.144 image analyzed in the Phase19/20 summary; the latter is a separate hashed binary.

## Display name references now recovered

GSP_DISPLAY_CONFIG_DATAFLOW.md records two local RmDisableDisplay callers at VA 0x04840368 and 0x04b300c0, both using helper 0x045e130c. Word-value comparisons with 1 and a conditional object-field store are grounded in raw instructions. Follow-up reports resolve the helper's primary typed lookup, generic setters and host ingestion. Caller object identity, fallback semantics and effective target values remain unknown.

## Configuration value path

GSP_CONFIG_VALUE_SOURCES.md grounds the RmDisableDisplay name-read interpretation in typed name lookup, numeric status correspondence and output writes. This is a software configuration mechanism, not a read of the display fuse itself. Root initialization and fallback source remain unresolved, so this still does not establish target policy or a display unlock.

Follow-up: GSP_SYSTEM_INFO_INGESTION.md and GSP_NVKV_CALLBACK.md identify CPU-to-GSP system-info ingestion and callback reachability. HOST_REGISTRY_PRODUCER.md connects the official host global/per-device registry packer to `GSP_INIT` command 0x10001. This is separate from the still-unresolved read-wrapper fallback transport and does not establish effective display/profiler values.

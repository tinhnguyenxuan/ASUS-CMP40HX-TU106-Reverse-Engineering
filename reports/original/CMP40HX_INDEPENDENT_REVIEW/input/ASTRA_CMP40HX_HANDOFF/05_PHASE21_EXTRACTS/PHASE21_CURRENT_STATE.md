# Phase 21 current state

## Live-target update (supersedes historical rows below)

Authenticated target capture is available and B-RUNTIME-TARGET is CLOSED.
Four other blockers remain OPEN. CUDA is PARTIAL_CURRENT: device query and
4096-element kernel correctness passed; Tensor/library/profiling remain untested.
Driver/GSP is 615.71.09, distinct from the statically analyzed 615.78.08.
EGL/Vulkan diagnosis found DRM EACCES and a Vulkan NVIDIA ICD initialization
error. See TARGET_LIVE_FINDINGS.md and evidence/target_live_20261104/.

Generated UTC: 2026-11-04T14:10:43.092506+00:00

Checkpoint: status=IN_PROGRESS, complete=false

## Requirement status

| ID | Status | Evidence boundary |
|---|---|---|
| cuda_capability | MISSING_CURRENT | Local sandbox lacks GPU/toolchain; target runtime tests not run |
| compute_restriction | PROVEN_STATIC | Static selector evidence exists; exact runtime consumer mapping remains open |
| display | PROVEN_STATIC | Static policy/fuse dataflow recovered; current physical capability missing |
| headless_graphics | MISSING_CURRENT | No fresh target correctness capture |
| fuse | HISTORICAL_ONLY | Saved raw subset and archived predicate; current origin unresolved |
| cross_sku_vbios | UNKNOWN | Local original/derivative comparison only |
| gsp_gates | PROVEN_STATIC | Static dataflow verified; effective target values/runtime reachability open |
| feasibility | UNKNOWN | Rows retain unresolved runtime/hardware inputs |
| safety_repro | PROVEN_STATIC | Read-only checklist and package collector/verifier exist |
| deliverables | PROVEN_STATIC | Artifact suite and full integrity sweep pass |

## Open blockers

| ID | Closure evidence | Current boundary |
|---|---|---|
| B-RUNTIME-TARGET | timestamped target package from BDF 0000:03:00.0 verified by verify_target_package.py | Fresh local v5 package verified, but 14/14 target reads failed; no 10de:1f0b or NVIDIA runtime in sandbox |
| B-EFFECTIVE-REGISTRY | target package containing readable registry/NVKV source with command and timestamp | Static ingestion path recovered; live values absent |
| B-FUNCTIONAL-DISPLAY | fresh display/KMS plus EGL/OpenGL/Vulkan/CUDA results tied to target UUID | Historical Display Attached=No and empty BAR probe only; no fresh functional tests |
| B-REFERENCE-ROM | externally sourced ROM with chain-of-custody and exact SKU/revision metadata | 16 unique local ROM contents lack authenticated provenance; DCB tables identical |
| B-PCB-ROUTING | authenticated PCB photos plus schematic/boardview or documented continuity | Only supplied identifiers, static DCB and secondary prose; no authenticated board material |

## Current conclusion

Static firmware, provenance, Hermes-cache, and artifact-linkage audits are consistent. The fresh local v5 package is schema-verified but contains zero successful target reads, so it does not establish current GPU state. Effective registry values, functional display behavior, independent ROM provenance, and authenticated PCB routing remain unverified.

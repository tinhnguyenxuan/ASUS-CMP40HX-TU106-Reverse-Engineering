# CUDA capability audit — reconciled 2026-11-06

The retained target captures establish bounded CUDA operation on BDF 0000:03:00.0, UUID GPU-REDACTED, reported driver/GSP 615.71.09. These are timestamped captures, not tests freshly executed by this reconciliation. Local socket creation remains denied. The earlier NOT_RUN conclusion described the sandbox and incorrectly omitted retained target evidence; it is superseded.

| Capability | Captured evidence | Boundary |
|---|---|---|
| CUDA kernel/VRAM/synchronization | 2026-11-04: 4096-element FP32 kernel, zero mismatches | This bounded path works; no stock/throughput assertion |
| Tensor WMMA | 2026-11-04: 16x16 half-input/float-output, 256 outputs match | Working Tensor path, not performance or all MMA modes |
| cuBLAS | 2026-11-04: SGEMM, 256 outputs match | cuBLASLt and other operations remain unverified |
| CUPTI discovery | Library loads; GetVersion returns success/version18 | Device support, counter collection and authorization unverified |
| RM issue-rate GET | 2026-11-05: 0x2080123c returns success, 8 pairs | Cached speed-select API; not physical OTP or a benchmark |
| DP4A, graphs, CUDA/GL interop | No reviewed correctness capture | UNKNOWN |

`CUDA_RUNTIME_RESULTS.json` now carries per-test timestamps, original output and input hashes. Reproduce the offline reconciliation with `tools/reconcile_runtime_evidence.py`. The script executes no captured command or device operation.

The raw issue-rate response is decoded independently as 2044 bytes: a dword count followed by up to255 pairs of dwords. Pairs are (0,6),(2,6),(3,0),(4,6),(5,6),(6,6),(7,6),(8,6). Record names and limits are in evidence/reconciled_20261106/issue_rate_decoded.json. Code6 is preserved without an inferred divisor. An omitted DP entry does not establish missing DP hardware. Failed reconfiguration GETs return 0x56 with unchanged buffers; neither failure nor the sentinel value proves disabled silicon.

Public ABI: NVIDIA tag615.71.09 ctrl2080gr.h, https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gr.h . The ABI describes instruction speed-select reporting; it does not grant a direct OTP read or demonstrate restoration. Static GSP615.78.08 addresses must not be reused in615.71.09.

Profiling follow-up: PROFILING_CAPABILITY_BOUNDARIES.md distinguishes the official CMP exclusion/device-support reason from counter privileges and library discovery. A native version-aware device-support probe is prepared but uncompiled/unexecuted; actual target API denial and counter collection remain unverified.

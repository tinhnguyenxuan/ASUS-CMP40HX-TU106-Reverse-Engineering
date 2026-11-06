# Issue-rate encoding boundary — 2026-11-06

The retained615.71.09 capture uses GET_SM_ISSUE_RATE_MODIFIER_V2 (0x2080123c), returning count8 and index/value pairs preserved in evidence/reconciled_20261106/issue_rate_decoded.json. This is API/cached information; it is not a direct FECS selector or physical OTP read.

An offline comparison to the saved ctrl2080gr.h shows an important boundary:

| Captured V2 field | Value | Numeric correspondence in legacy20801230 definitions |
|---|---:|---|
| FMLA16 | 6 | No matching legacy enum; listed reduced-rate definitions stop at5 |
| FMLA32 | 6 | No matching legacy enum; listed reduced-rate definitions stop at5 |
| FFMA | 0 | Legacy label FULL_SPEED |
| IMLA0–4 | 6 | Legacy label REDUCED_SPEED_1_64 |

Reproduce with tools/audit_issue_rate_encodings.py. The exact local header hash and all comparisons are retained in evidence/issue_rate_enum_boundary.json. The comparison script does not establish byte identity to the target615.71.09 release or translate between the two API implementations.

Therefore the API values must not all be labeled 1/64 using a generic 2^code rule. Even legacy enum correspondence is not a measurement of achieved instruction throughput or the current override state. FMLA6 requires its own exact consumer/encoding evidence. Likewise FFMA0 is not proof that every FP32 workload executes at a nominal full rate.

Next useful evidence: the matched615.71.09 V2 host/static-info producer and firmware getter, any conversion relative to legacy query20801230, then controlled existing workload results. Do not write selectors, change clocks or reload/reset the driver to fill this gap automatically.

Official public ABI reference: https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gr.h . Read with the matched implementation; an enum's name alone is not silicon semantics.

## Matched615.71.09 host consumer recovered

Official kernel_graphics.c provides a concrete cache boundary. At lines1286–1303, the initialization branch obtains INTERNAL_STATIC_KGR_GET_SM_ISSUE_RATE_MODIFIER_V2 and copies the selected GR result into staticInfo. An alternative VSI branch copies V2 data at lines888–896.

The public V2 handler at lines3079–3144 selects a GR context, requires the cached V2 pointer and validates requested indices. A zero input count copies all cached indices; findSmIssueRateModifier copies each stored data field directly to the response. There is no rate-to-divisor conversion or hardware read in this shown response path. The legacy handler separately reads its own cached fields.

Thus the captured numbers are established as cached report values, not instantaneous FECS override readbacks. The upstream internal producer, conversion between legacy/V2 caches and effective instruction throughput remain unproved. Source parameter names mentioning fuse do not prove physical OTP access.

Source: https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/nvidia/src/kernel/gpu/gr/kernel_graphics.c#L3079 (official tag, reviewed2026-11-06). This source tracing executed no RM call or hardware operation.

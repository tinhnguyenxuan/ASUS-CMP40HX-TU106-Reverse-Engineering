# Retained evidence reconciliation — 2026-11-06

Current filesystem contains target captures and independent review artifacts that supersede older sandbox-only notes. No fresh SSH session succeeded in this reconciliation: local socket creation still returns EPERM. The cache path for original Phase19/20 scripts seen in a prior turn is no longer present. No unsafe historical script was executed.

Offline checks confirm retained 2026-11-04 FP32, WMMA and cuBLAS correctness, CUPTI library discovery and BDF-bound headless shader pixel correctness. Their observation dates remain attached; they are not a statement about the target at the present instant or an unmodified stock baseline.

Newly reconciled 2026-11-05 18:18:44Z raw RM capture contains one successful 0x2080123c response and six rejected TPC-reconfiguration queries with unchanged buffers. The decoder preserves the 8 returned index/value pairs and retains snapshots/hashes of the raw response, identity and probe source in evidence/reconciled_20261106. It never invokes the probe or its ioctl operations.

The companion identity capture reports the same BDF/UUID, VBIOS90.06.67.00.06, driver and GSP615.71.09. An installed firmware-file hash is not a resident-image readback. The newer independent report traces additional GSP topology handlers, but it remains necessary to independently verify the firmware bytes/dispatch mappings before adopting exact addresses as Phase21 conclusions.

CUDA_RUNTIME_RESULTS.json, CUDA_CAPABILITY_AUDIT.md and HEADLESS_GRAPHICS_REPORT.md now reflect this evidence. No throughput divisor, stock throttle, physical OTP, recoverable missing TPC, display-engine restoration or successful Vulkan render is inferred. Physical display and effective configuration remain unresolved.

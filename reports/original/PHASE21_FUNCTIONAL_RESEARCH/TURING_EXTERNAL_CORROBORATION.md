# External Turing corroboration — source review only, 2026-11-06

## Actual Turing access sites versus inherited header

The [Turing source at revision1d379b7](https://github.com/nlzy/turing-unlock/blob/1d379b7/kernel/turing_unlock/unlock.c) uses local Turing register definitions at FECS offsets0x409650,0x409664,0x40966c and readout0x409668. Its post-operation validation inspects the two override values and the readout separately. This independently agrees with the register cluster named by the retained CMP40HX patch, but does not recover individual instruction-class bit assignments or the original stock writer.

The accompanying [gfw_eval.h](https://github.com/nlzy/turing-unlock/blob/main/kernel/turing_unlock/gfw_eval.h) still declares feature-register constants at0x823804/1c/20. The reviewed unlock.c access sites use the local Turing definitions instead. Therefore an included header's constants cannot alone identify the active architecture/addressing path. No equivalence between the two register blocks is inferred.

The source implements state-changing privileged boot/security handling. It was read through public source pages only; nothing was installed, compiled or executed. Its existence is not authorization to invoke it under the current read-only restrictions.

## TU106 report with explicit scope

A [report by the RTX2070 operator](https://github.com/nlzy/turing-unlock/issues/4) identifies TU106, device10de:1f07, subsystem3842:2171, VBIOS90.06.18.40.09 and36SM, with driver/GSP610.43.02 and separately pinned610.43.03 boot assets. The author reports improved FP16-to-FP32 throughput after the procedure.

This is a same-chip-family functional report, stronger comparison context than Ampere-only claims. It is nevertheless GeForce equipment with different device/subsystem/firmware and SM configuration from the target CMP40HX. The benchmark, power state, procedure, and target applicability have not been independently reproduced here. No throughput factor, stock policy, missing-TPC health, display restoration or successful CMP unlock follows from it.

Public reports should guide exact-version source comparison and correctness-first measurements, not substitute for evidence on the requested board.

## Reference ROM search result

The search did not yield an acquired/authenticated TU106 reference ROM. TechPowerUp vgabios access was blocked by robots policy in the web tool; the earlier two named GeForce files remain HTML. No bypass or repeat against the blocked source was attempted. B-REFERENCE-ROM remains OPEN, and no cross-SKU byte comparison is claimed.

# Display architecture — partial findings

Target identity is supplied metadata: TU106-100-A1, CG161P REV 2.00, subsystem 8804:1043, VBIOS 90.06.67.00.06. Live identity has not been queried in this session.

A physical output needs a usable display controller/head/plane, output resource, clock/reset domains, PHY, package pins and routed PCB components, plus firmware and KMS configuration. Offscreen rendering alone proves none of these scanout stages.

Direct ROM evidence: DCB 4.1 at 0x2d9ac has no display path entries; connector table at 0x2dbc5 has no connectors. Communications table v4.1 has 15 records, with low-field DPAUX indices 0–6 in entries 3–9; 32 GPIO records have no HPD tags recognized by the saved envytools definitions. Reproduce with tools/offline_display.py then tools/decode_board_tables.py. Raw rows, offsets and input hashes are saved in evidence/board_tables.json.

These are board-description facts, not hardware discovery. No positive or negative silicon-level conclusion is established for PDISP, heads, window/plane engines, SOR, DP PHY, HDMI/TMDS PHY, AUX, HPD circuitry or display clocks/resets. Each remains UNKNOWN on this specific chip.

The NVIDIA DCB specification describes external board routing rather than chip capabilities: https://nvidia.github.io/open-gpu-doc/DCB/DCB-4.x-Specification.html . Version 4.1 also changes DFP assignment interpretation to pad macros; do not reuse pre-4.1 SOR assumptions.

GSP/RM discovery branches, DRM CRTC/connector queries and live error paths remain unmeasured. Current lack of access is not a driver rejection. No unknown MMIO addresses were probed.

Follow-up: official TU106 dispatch does select the GM107 display-fuse helper. Archived 0x21c04 bit0=1 evaluates as unsupported against saved ENABLE=0 definition. See evidence/display_gate.json and GSP_CAPABILITY_GATES.md. This locates a source-level gate, not the physical origin of its input or the current runtime outcome.

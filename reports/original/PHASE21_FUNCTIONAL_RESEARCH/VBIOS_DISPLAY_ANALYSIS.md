# VBIOS display analysis — partial, independently decoded

Run `python3 PHASE21_FUNCTIONAL_RESEARCH/tools/offline_display.py` from workspace root. Inputs and full SHA256 are in evidence/dcb.json. Original ROM hash matches handoff.

Legacy image begins at 0x28600; pointer at 0x28636 is 0x53ac, hence DCB absolute offset 0x2d9ac. Version 0x41, header size 35, entry count ZERO, entry size 8; signature 0x4edcbdcb verified. Original and locally supplied T4 derivative have identical DCB headers and table prefixes. T4 derivative is not an independent reference GPU ROM.

Connector pointer is non-null (relative 0x55c5, absolute 0x2dbc5), with prefix 40 05 00 04 00: no connector entries. Communications and GPIO tables remain present; their existence does not establish routed display outputs. Input, cinema, spread-spectrum, HDTV and switched-output pointers are null. Detailed GPIO/DDC/AUX interpretation and devinit scripts remain pending.

[NVIDIA DCB specification](https://nvidia.github.io/open-gpu-doc/DCB/DCB-4.x-Specification.html) defines these as board connection descriptions, not silicon capability declarations. Thus zero entries establishes missing declared output routes, not fused-off PDISP. Local independent layout check: /tmp/envytools/nvbios/dcb.c, v0x40/0x41 branch.

No trusted GeForce TU106 reference ROM has yet been compared. No ROM was loaded or flashed.

## Communications and GPIO follow-up

`tools/decode_board_tables.py` extracts bounded records using saved envytools layouts and preserves the source files with SHA256. Both ROMs have 15 communications records, 32 GPIO records and 32 I2C-device records. CCB 4.1 low fields declare DPAUX 0–6 in entries 3–9. No GPIO entry has a recognized HPD tag (07,08,51,52,5e,5f,60). This is a table-level negative result only. Raw fields remain available for independent decoding; unused records and reserved bytes are not interpreted as functioning engines or connectors.

Correction: the saved envytools parser uses the old access-method byte even for v4.1. It must not be used to conclude no AUX. The official v4.1 format uses 5-bit I2C and DPAUX fields instead; tools/decode_board_tables.py now decodes those fields. High bits are nonzero in several entries and remain explicitly undecoded rather than forced to the older published reserved-zero interpretation. The declared indices are not proof of physical routes or working AUX engines.

## Init-related FECS evidence

BIT I +6 points to condition table 0x2cc9c. Record 50 at 0x2cef4 tests FECS readout 0x409660 bit16 for 1. This is a condition record rather than a selector write or a display capability proof. Two candidate CONDITION-50 byte matches remain unverified instruction boundaries. Full details and source/hash provenance: COMPUTE_SELECTOR_EVIDENCE.md and evidence/vbios_fecs_condition.json.

Follow-up: VBIOS_INIT_FECS_PATH.md establishes a static path from the actual BIT I entry to condition50 at relative 0xca6e (absolute0x3506e), with guarded command streams and separate neighboring FECS writes at 0x409658/65c. Earlier statements that both CONDITION-50 byte matches lacked boundaries are superseded for this one site. Runtime guard results and exact field meanings remain unknown.

## Display programming and DP INFO roots

The original and local derivative have BIT Uv1 first-u16 pointer NULL (raw0000020000), BIT dv1 DP INFO pointer NULL (raw0000), while BIT Dfirst pointer0x517d remains non-null. See VBIOS_DISPLAY_ROOTS.md for precise offsets, bounded decoding and independent Nouveau consumer corroboration. Null roots do not prove hardware absence or exclude proprietary fallback. Newly supplied GeForce .rom files are HTML and rejected as reference firmware.

## Retained timing records and TMDS root

VBIOS_RETAINED_TIMINGS.md records ten plausible18-byte timing interpretations at the non-null first BIT Dpointer0x517d. The second Dpointer (legacy FP-mode consumer) is NULL; BIT T TMDS INFO pointer is NULL. Timing data presence is not mode exposure or scanout evidence; no all-display-data-erased claim is justified.

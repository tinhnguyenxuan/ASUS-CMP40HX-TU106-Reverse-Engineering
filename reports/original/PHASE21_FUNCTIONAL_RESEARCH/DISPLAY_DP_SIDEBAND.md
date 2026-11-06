# DisplayPort sideband — CAD/ROM correlation, 2026-11-06

This audit separates actual net membership from hypothesized device behavior. Reproduce tools/audit_pcb_netlist.py then tools/audit_dp_sideband.py. The original CAD and ROM hashes, source lines and checked pins are saved in evidence/dp_sideband_audit.json. No hardware operation was performed.

## Direct design membership

| Segment | Raw CAD membership | What remains unknown |
|---|---|---|
| GPU-side AUX positive | G1.BE11 and Q7.4 share IFPD_AUX | Transfer through Q7 and actual device population |
| GPU-side AUX negative | G1.BF11 and Q7.1 share IFPD_AUX* | Same |
| Other Q7 terminals | Q7.3 on IFPD_AUX_R; Q7.6 on IFPD_AUX_R* | Do not connect pins3/4 or1/6 without a part/pin model |
| AUX component/control area | Q7.2/5 on DP_AUX_PROT; Q509.2/5 on DP1_MODE | Net labels do not define electrical control function or polarity |
| Q509 | pin1 on IFPD_AUX_R, pin4 on IFPD_AUX_C, pins3/6 on IFPD_AUX_BYP | No internal continuity or bypass function assumed |
| HPD connector-side network | R720.2 on DP_D_HPD_C; R720.1 and R742.2 on DP_D_HPD_R | Actual resistor values, population and electrical signal unknown |
| HPD at Q521 | R742.1 and Q521.1 share DP_D_HPD_R_Q; Q521.3 and G1.BH1 share GPIO17_IFPD_HPD; Q521.2 is GND | Transistor/part type, logic inversion and operating levels unknown |

CAD footprints identify Q7/Q509 as SC70_6 and Q521 as SOT23; a footprint is not a verified semiconductor part number. It does not justify a proposed short, strap resistor change or functional equivalence between terminals. The extracted DEVICES identifiers are generic names, not authenticated electrical models.

These segments show a described AUX/HPD network and package-ball memberships in the supplied design. They improve the prior evidence limited to connector-side nodes; they do not prove the exact tested CMP PCB has that copper, populated parts or enabled silicon. Surface photos alone cannot close these electrical questions.

## ROM GPIO candidate correlation

The original ROM GPIOv4.1 table contains one record whose line field is17: absolute offset0x2d216, raw11 ff 00 44 ef 00. Under the saved parser layout, line=17 and tag=0xff (unused). This is consistent with the earlier observation that the ROM declares no recognized HPD tag.

The CAD net is named GPIO17_IFPD_HPD. That name makes ROM line17 worth investigating, but there is no independent package/manual proof here that the two numbering systems identify the same hardware GPIO. Hence this is CANDIDATE_CORRELATION, not a proved firmware disable path. No value was written and no replacement tag is recommended from this evidence.

## Restoration boundary

A functioning DisplayPort link needs lane routing, AUX communication, HPD signaling, sideband device behavior, power/clock/reset and a display controller/PHY permitted by firmware/driver. Existing headless rendering correctness does not exercise this chain. Empty DCB/connector declarations, missing DP INFO root, display capability gates and unknown sideband device state can coexist; none is isolated as the sole blocker.

Next discriminators are exact component identification/board correspondence, independently verified GPIO/package mapping and read-only documented capability responses. Without those inputs, neither BOARD_UNROUTED nor software-only restoration is justified. No live probing, continuity measurement, component removal or unknown-engine enablement occurred.

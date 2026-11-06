# PCB evidence — design and image audit, 2026-11-06

The filesystem now contains supplied GenCAD and photographs. Earlier claims that no board material existed are superseded. The CAD is design data associated by the handoff with ASUS CG161P R2; it has not been authenticated as the exact copper/BOM of the electrically tested CMP sample or linked to its GPU UUID.

## Independently rederived design evidence

Source: CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF/01_BOARDVIEW/CG161P_R2_boardview.cad, SHA256 7338ccead9423c8ddd61f5c1e4f0147d95b3c6da5af3e9bae0a20fbcfab6264d. Header declares GenCAD1.4, drawing Board_0_0, revision date2021-12-14, USER1000 units and six routing layers. These are file metadata, not chip/PCB authenticity proof.

`tools/audit_pcb_netlist.py` reparses raw SIGNAL/NODE and COMPONENT sections, checks unique pin-to-net membership and preserves source line numbers. It does not import conclusions from the prior CSV (whose rows have inconsistent column counts). Output: evidence/pcb_design_rederived.json.

| Design item | Direct evidence | Limit |
|---|---|---|
| G1 | BGA_2228_P070_375X375 footprint | Package ball naming from CAD, not independent pinout authentication |
| J1 | S_DISPLAY_20P footprint; eight lane conductors connect via two-terminal capacitors to G1 lane nets | Design connectivity, not verified copper/population/DP function |
| J5 | SO_DVI_24P footprint; fourteen conductors connect via capacitors to G1 lane nets | Do not infer support for every DVI mode from lane count |
| J10 | SO_HDMI_38P_9H_C1_COLAY footprint with P/G pin namespaces | Co-layout design, not installed connector or working HDMI |

Example raw route: J1.1 -> IFPD_L0_C -> C47.2 / C47.1 -> IFPD_L0 -> G1.BM18. Complementary conductor J1.3 uses C46 to G1.BM17. Other J1 routes terminate at G1 BL17/BK17, BK15/BL15 and BM15/BM14. These are separate signal nets bridged by intended capacitors; the report does not assert DC conduction through a capacitor.

Nine AUX/HPD/DDC-labelled connector-side nets are preserved with raw nodes. The parser intentionally invents no internal path through Q/U/D multipin parts. Its bounded HDMI passive-chain search found no complete lane path under its restricted traversal rules; this is NOT proof of an unrouted HDMI design. Full sideband device identities, switching/level conversion, ESD and power sequencing still require corroboration.

## Photographs inspected directly

Supplied annotated CMP40HX_PORTS_PHOTO_ANNOTATED.jpg shows connector bodies at J1 and J5 and an unpopulated J10 footprint. These observations are visible independently of the annotation text. Surface traces and nearby populated passives can be seen, but no continuity, hidden-layer routing, device electrical role or active signal can be established from this image. Original capture date and linkage of the pictured board to target UUID are unknown.

The inspected raw phone image1793813621628.jpg is a close-up of an IC/passives area and does not establish full board revision, output routing or target identity. No chip-part inference from an uncertain marking is used. Both inspected files have hashes recorded in pcb_design_rederived.json.

## Restoration implications

- A blanket statement that the pictured board lacks all output connectors is contradicted by the photograph. Connector presence does not establish working scanout.
- A blanket BOARD_UNROUTED classification is unsupported: the supplied design describes several output lane paths. Exact correspondence to the CMP board remains unresolved.
- J10 connector absence is visible in one photograph; it does not establish that adding a connector would restore HDMI. Firmware routing, sidebands, display capability gates and PHY state remain separate requirements.
- Package-pin membership in a reference CAD does not prove display silicon survives/enables on this specific TU106 die.

No soldering, continuity measurement, strap change, MMIO access or mode setting was performed. Before proposing any PCB modification, establish exact board correspondence and the missing electrical chain; before calling restoration successful, prove physical scanout to a real sink separately from already verified headless rendering.

## Sideband follow-up

DISPLAY_DP_SIDEBAND.md now follows raw GPU-side AUX nets to G1.BE11/BF11 and HPD-labelled net to G1.BH1, preserving unresolved Q7/Q509/Q521 internal behavior. ROM GPIOline17 has unused tag0xff; correspondence to the CAD GPIO17 net is only a candidate. This is design/configuration evidence, not working sideband or an approved modification plan.

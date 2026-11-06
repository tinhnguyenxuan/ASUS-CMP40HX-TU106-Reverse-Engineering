# Display restriction matrix — ongoing

| Layer/component | Direct evidence | Conclusion | Missing verification |
|---|---|---|---|
| PDISP, heads, planes | No validated live discovery | UNKNOWN | Matched TU106 engine-discovery source and target response |
| SOR, DP/HDMI PHY | No physical or runtime capture | UNKNOWN | Package/PCB routing and recognized capability queries |
| AUX configuration | CCB 4.1 low-field DPAUX indices 0–6, entries 3–9 | Declared controller indices, functionality UNKNOWN | Reserved/extended fields, firmware consumers and physical AUX routing |
| HPD configuration | No recognized HPD GPIO tags | No HPD GPIO mapping declared under saved parser | RM handling and board routing |
| Clock/reset | No decoded capture | UNKNOWN | Documented source/firmware initialization path |
| Fuse-status gate | Saved +0xc04 = 1; official TU106 dispatch selects GM107 helper, ENABLE=0 in saved header | Archived support predicate false; physical fuse storage UNKNOWN | Fresh status, exact tag header, physical vs shadow provenance |
| VBIOS paths | DCB count=0 | No declared output paths | Driver fallback/internal-table behavior |
| VBIOS connectors | Pointer non-null, count=0 | Empty connector table, not null pointer | Reference ROM and driver behavior |
| GSP/RM | No decision/dataflow trace | UNKNOWN | Exact firmware version and capability-return branches |
| DRM/KMS | No target enumeration | UNKNOWN | BDF-bound connector/CRTC query |
| PCB/package | Supplied GenCAD lane paths independently rederived; image shows J1/J5 populated and J10 absent | Exact target correspondence and electrical function UNKNOWN; BOARD_UNROUTED not proven | Authenticate board/CAD identity, sidebands and actual signal path |

No row establishes SILICON_DISABLED or a successful display restoration.

Additional VBIOS gate evidence: BIT U display-programming root and BIT dDP INFO root are NULL; BIT Dretains non-null data. These are independently decoded table fields, not silicon-disable evidence. See VBIOS_DISPLAY_ROOTS.md.

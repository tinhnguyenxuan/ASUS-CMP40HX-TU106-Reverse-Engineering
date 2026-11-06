# VBIOS display roots — bounded decode, 2026-11-06

Original ROM and local T4 derivative share these fields. Each file is independently hashed and the BIT header/signature/checksum and entry extents validated by tools/audit_vbios_display_roots.py. This decoder executes no firmware, init commands or device operations.

| Root | Entry/version | Data offset in original ROM | Raw data | Result |
|---|---|---|---|---|
| BIT U | v1, length5 | 0x289ce | 00 00 02 00 00 | u16 display-programming table pointer at+0 is NULL |
| BIT d | v1, length2 | 0x289e1 | 00 00 | DP INFO table pointer at+0 is NULL |
| BIT D | v1, length4 | 0x2888f | 7d 51 00 00 | Non-null first DFP/panel-related pointer0x517d; full semantics unresolved |

The U token itself exists and is not all zero: remaining bytes02 00 00 are retained as unknown fields. Missing root table, missing BIT entry, all-zero data and empty table are distinct conditions.

Independent Nouveau nvbios_disp_table logic looks up BIT U version1, reads its first u16 and returns no table if it is zero. This corroborates the saved envytools display-script discovery path. Source: [Nouveau display-table consumer](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/nouveau/nvkm/subdev/bios/disp.c). The upstream reference is mutable; the local envytools source copies and hashes used for numeric decoding are preserved in evidence/vbios_display_roots.json.

This establishes no discoverable programming-table root through that interface. It does not exclude scripts elsewhere, a driver-generated sequence or proprietary firmware fallback. General BIT I init scripts still exist and touch the graphics/FECS cluster. Neither null U/d roots nor zero-entry DCB proves that heads/SOR/PHY are physically absent.

The non-null BIT D pointer is not converted to a claim of panel support or working outputs. Next: decode the DFP/panel data under its actual version, then compare authenticated TU106 reference firmware. Software recovery feasibility still depends on display capability gates and physical board correspondence.

## Reference-file rejection

Both supplied files03_VBIOS/geforce/rtx2060super.rom and rtx2070.rom begin with an HTML doctype and document header. They are HTML, not usable ROM binaries. Names and intended download URLs do not establish an independent cross-SKU firmware reference. Their exact bytes/hashes are retained in evidence/vbios_display_roots.json; no parsing result or claimed GeForce field comparison is produced from them.

Follow-up: the retained first Dpointer admits ten consecutive plausible18-byte timing interpretations; its first byte must not be mistaken for a version. Second Dpointer and T TMDS INFO pointer are NULL. Detailed scope and decoded values: VBIOS_RETAINED_TIMINGS.md.

# Retained display timing data — bounded interpretation, 2026-11-06

BIT D v1 has two16-bit pointers. The first points to legacy-relative0x517d (absolute original ROM0x2d77d), while the second is NULL. The saved original and local T4 derivative contain identical bytes in the inspected window. BIT T v1 TMDS INFO pointer is also NULL, independently read at original offset0x289cc.

The first-pointer data admits a consistent18-byte detailed-timing-descriptor interpretation. Ten consecutive records have positive clocks, plausible active/blank dimensions and sync intervals contained in their blanking periods:

| Record | Active dimensions | Pixel clock kHz | Raster rate Hz |
|---|---|---:|---:|
| 0 | 720x400 | 28320 | 70.082 |
| 1 | 640x480 | 25180 | 59.952 |
| 2 | 800x600 | 40000 | 60.317 |
| 3 | 800x600 | 50000 | 72.010 |
| 4 | 800x600 | 49500 | 74.642 |
| 5 | 1024x768 | 65000 | 60.004 |
| 6 | 1024x768 | 75000 | 70.069 |
| 7 | 1024x768 | 78750 | 75.029 |
| 8 | 1280x1024 | 135000 | 75.025 |
| 9 | 1280x1024 | 108000 | 60.020 |

Reproduce with tools/decode_retained_display_timings.py. Raw records, clock/dimension/sync/flag values and full input hashes are in evidence/retained_display_timings.json. Reported rates are arithmetic clock/total-pixels results, not measurements or promises that a monitor accepts those timings.

Layout reference: [Linux detailed timing structures](https://github.com/torvalds/linux/blob/master/include/drm/drm_edid.h). The legacy [Nouveau BIT display parser](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/nouveau/nouveau_bios.c) distinguishes the first timing-like pointer from the second FP mode pointer. That source distinction does not establish how the current proprietary TU106 firmware consumes these bytes.

## Interpretation limits

The ten-record window is an analyst-selected bounded observation. No encoded table count, terminator or full-table extent has been proven. The following18 bytes fail this interpretation's plausibility checks; that supports stopping the decoding window but does not establish their true purpose. The first byte0x10 is the low byte of a plausible pixel clock under this interpretation and must not automatically be labeled a table-version header.

These are timing-like records within ROM, not a complete EDID block or an EDID read from an attached sink. No checksum authentication, output association, mode-list exposure, script reachability or live scanout follows. In particular the NULL second D pointer must not be confused with the retained first-pointer data.

The result refutes an overbroad description that all display-related data was erased. It is compatible with the separate findings of zero DCB output entries, NULL U programming root, NULL d DP INFO root and NULL T TMDS INFO root. None alone proves absent display silicon or software-restorable physical outputs.

# Reproducibility and audit guidance

## Hardware identity and tool versions

The original research reports identify the CMP 40HX TU106-100-A1 (`10DE:1F0B`), often PCI BDF `0000:03:00.0`, VBIOS `90.06.67.00.06`, Linux Ubuntu 24.04.5 with kernel 6.8.0-147-generic for live tests. Driver/GSP **615.71.09 and 615.78.08 both appear** in different captures. Record exact version, timestamp, GPU identity and boot state for every comparison.

## Evidence without risky writes

For evaluating claims, begin with existing [raw topology JSON](../evidence/original/PHASE_TU106_FLOORSWEEP_INDEPENDENT/LIVE_TPC_TOPOLOGY.json), [raw RM query](../evidence/original/PHASE_TU106_FLOORSWEEP_INDEPENDENT/LIVE_RM_QUERY_V2.json), [fuse report](../reports/original/ok/results/TPC5/TPC5_RAW_FUSE_COMPARISON.md) and [live BAR0 result](../reports/original/ok/results/TPC5_LIVE/EXPLOIT_LIVE_20261106.md). Confirm hashes and direct measurement provenance. These files are archived observations, **not instructions to repeat dangerous experiments**.

The tests of `0x021040`, `0x021838` and `0x0210D4..0x0210F4` involve physical hardware writes and can cause a crash, data corruption or permanent damage. There is no guarantee of safety on a different card, driver or boot state. **Do not automatically replay live-write scripts**.

## Original scripts

`/scripts/original/` contains preserved project programs. Publication redaction may replace hostnames, device UUIDs or absolute paths. Scripts have not been tested or sandboxed in this distribution. In particular, no shell, Python, CUDA or kernel experiment from the supplied ZIP was executed by the packager. Read each file before use and reconstruct original setup only from trusted, properly licensed sources.

## Manifests and hashing

Every source entry is accounted for in `manifests/SOURCE_INVENTORY.csv` (relative original path, size, raw SHA-256, destination in complete archive, public status, redactions). The public repo's `manifests/PUBLIC_SHA256SUMS.txt` covers all actually shipped selected files. Duplicate source names refer to the canonical surviving content entry; no file should be inferred absent without checking the inventory.

To verify the published files after unzip:

```bash
python3 tools/verify_checksums.py
```

No dependency install required. To compare to the **complete private archive**, verify the `SOURCE_INVENTORY.csv` hashes against the corresponding `preserved/...` paths. Never upload this private archive unreviewed.

# Tested paths that did not achieve an unlock

| Route | Actual reported observation | What **cannot** be concluded |
|---|---|---|
| Rewrite/report spoof `tpcMask[]` | Changes to reporting alone did not activate hardware TPC topology | That the kernel or firmware has no other init-time options |
| Candidate `0x021040` + `0x021838` BAR0 writes | `0x021040` read back as 1; `0x021838` bit5 immediately 0; `0x021C38`/GR stayed unchanged | Register identity, irreversible OTP, a universal prohibition on any override |
| Scan for TU106 defect registers by Ampere offsets | Candidate reads returned zero/poison/other values | The chip has no defects, or no defect indicator exists elsewhere |
| Treat `0x021A40` all-zero bank as RECONFIG_OVERRIDE | Aperture observed, semantics not proven | A valid Turing override bank |
| Derive TPC producer solely from GSP literal grep | No direct address literal matches | GSP never accesses fuse or derived effective mask |
| Phase 15–18 BAR3 redirection | Phase 19 measurements rejected the claimed arbitrary GPU PA primitive | Arbitrary GPU physical access via another mechanism |
| Display recovery by software mask/BIOS parsing | Native display output still not demonstrated | Physical DP/DVI hardware works or is irreversibly absent |

**NOT TESTED as a proven safe recovery:** RIR burn, OTP changes, bootloader patching, SEC2/Booter modification, flashing custom VBIOS to physical ROM. These are not recommended as follow-up without separate hardware proof and reliable recovery tooling.

See [full correction history](CRITICAL_CORRECTIONS.md) and [live experiment](../reports/original/ok/results/TPC5_LIVE/EXPLOIT_LIVE_20261106.md).

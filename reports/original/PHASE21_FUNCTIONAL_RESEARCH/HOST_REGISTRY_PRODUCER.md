# Host registry producer and GSP_INIT transport

## Result

The host-to-GSP path for registry values is now connected end to end for the saved 615.78.08 source and firmware:

`host registry database` → `osPackageRegistry()` → `PACKED_REGISTRY_TABLE` → `_kgspEncodePackedRegistryKeys()` → system-info NVKV stream → `GMCAPI_CMD_GSP_INIT (0x00010001)` → firmware NVKV decoder → typed configuration list → `RmDisableDisplay` readers.

This proves that a host registry entry can reach the same GSP list read by the two recovered `RmDisableDisplay` consumers. It does not prove that the target supplied that key or that changing it restores display hardware.

## Saved official source identity

The source input is `work_v15/PHASE16/OFFICIAL_CONSUMER_SOURCE/kernel_gsp.c`, SHA256 `ed6d7020a8a1772bc44608178aa13a77a72b8bf0eabe3293c12bc9d2b122c6c9`. The existing Phase 16 manifest identifies NVIDIA release 615.78.08 and immutable commit `ca2d03e6fafd4d4b56b383497d931c25b283bfcf`. The source hash was independently checked against that manifest. This source-to-release evidence does not by itself prove that every byte of the saved firmware was built from that public source revision; the firmware has separate version/hash evidence.

The official source performs the following sequence:

1. `_kgspPrepareRegistry()` calls `osPackageRegistry()` first to obtain the size, allocates the table, and calls it again to populate `pKernelGsp->pRegTable`.
2. `_kgspEncodePackedRegistryKeys()` walks all `numEntries`. For each supported entry it emits `REGKEY_NAME`, followed by `REGKEY_VALUE_U32`, `REGKEY_VALUE_BINARY`, or `REGKEY_VALUE_STRING` according to the packed entry type.
3. `_kgspEncodeSystemInfo()` appends those registry pairs to the same NVKV stream as PCI, platform, feature, and driver information.
4. `kgspSendInitRpcs_IMPL()` passes the encoded stream to `gmcapiCommand(..., GMCAPI_CMD_GSP_INIT, ...)`.

The official GMCAPI table defines `GSP_INIT` as category 1, ID 1, yielding command `0x00010001`. This resolves the previously unnamed command observed by the firmware packet consumer. In the firmware, the bounded path at 0x054fa2e4 masks the command to 24 bits, compares it with 0x10001, and passes the payload at packet+0x28 to the NVKV wrapper. `GSP_NVKV_CALLBACK.md` and `GSP_SYSTEM_INFO_INGESTION.md` provide the raw firmware-side proof.

## What the archived target configuration shows

An automated search covered textual files with extensions `.conf`, `.json`, `.log`, `.md`, `.out`, `.sh`, and `.txt` under `cmp40hx_transfer/` and `work_v15/RAW_DATA/`. It found two `RegistryDwords`-related lines and zero `RmDisableDisplay` lines. The concrete archived module option is:

`RmLinuxVbiosOverride=2;RmLinuxVbiosOverrideSize=495616`

Therefore, the available archived text does not support a claim that `RmDisableDisplay` was explicitly supplied through the global module option. This is stronger than the previous unknown only for those archived inputs. It does not cover the live `/proc/driver/nvidia/params`, per-device registry inputs, internal host-RM entries, a changed configuration after capture, or data omitted from the handoff.

The implementation of `osPackageRegistry()` is not included in the selected saved official-source subset, but it is present as `RmPackageRegistry()` in the [official 615.78.08 registry source](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/arch/nvalloc/unix/src/registry.c). It counts and copies the global registry first and the local per-device registry second. DWORDs are stored inline; binary and string entries use offsets into the packed data blob. Therefore the verified encoder forwards both registries' supported entries rather than selecting a special whitelist.

The [official 615.78.08 OS registry source](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/kernel-open/nvidia/os-registry.c) shows that `NVreg_RegistryDwords` is parsed into global entries during registry initialization, while `NVreg_RegistryDwordsPerDevice` writes DWORD entries for a BDF-matched GPU. Other driver initialization paths can also write global registry entries. The exact live packed table is consequently the authoritative evidence for effective input, rather than the module option string alone.

Ordering also matters. `RmPackageRegistry()` serializes global entries before local entries. The recovered GSP type-1 setter updates an existing same-name/type node rather than inserting a duplicate. For a duplicate DWORD key, the later per-device entry therefore replaces the earlier global value in the GSP list. This precedence is supported by the combined host and firmware dataflow; it has not been exercised on the target.

## Reproduction and limits

Run:

```bash
python3 PHASE21_FUNCTIONAL_RESEARCH/tools/verify_host_registry_producer.py
```

The verifier checks the saved source/manifest hashes, ten source-path invariants, the GMCAPI command mapping, and the bounded archived-text search. Machine-readable output is `evidence/host_registry_producer.json`.

No module parameter was changed, no driver was reloaded, and no GPU operation occurred. A live read-only capture of `/proc/driver/nvidia/params`, the actual packaged registry or equivalent GSP trace is still required to establish the effective `RmDisableDisplay` value. Even a proven value of zero would establish software policy only; display fuse state, heads/SOR/PHY discovery, VBIOS routing, and PCB connectivity remain independent requirements.

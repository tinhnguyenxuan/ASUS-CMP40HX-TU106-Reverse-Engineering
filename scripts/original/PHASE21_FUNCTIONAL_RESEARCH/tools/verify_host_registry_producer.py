"""Verify the saved 615.78.08 host-RM registry-to-GSP producer path.

This is a source and archived-text audit. It does not contact or configure a GPU.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
PHASE = ROOT / "PHASE21_FUNCTIONAL_RESEARCH"
SOURCE = ROOT / "work_v15/PHASE16/OFFICIAL_CONSUMER_SOURCE/kernel_gsp.c"
PROVENANCE = ROOT / "work_v15/PHASE16/PHASE16_EVIDENCE.json"
GMC_TABLE = Path("/tmp/nvsrc/nvidia/interface/gmcapi/gmcapi_table.h")

EXPECTED_SOURCE_SHA256 = "ed6d7020a8a1772bc44608178aa13a77a72b8bf0eabe3293c12bc9d2b122c6c9"
EXPECTED_COMMIT = "ca2d03e6fafd4d4b56b383497d931c25b283bfcf"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def function_window(text, name, next_name):
    start = text.index(name)
    end = text.index(next_name, start)
    return text[start:end]


source_hash = sha256(SOURCE)
assert source_hash == EXPECTED_SOURCE_SHA256
provenance = json.loads(PROVENANCE.read_text())
assert provenance["release"] == "615.78.08"
assert provenance["tag"] == EXPECTED_COMMIT
entry = next(item for item in provenance["files"] if item["saved_as"] == "kernel_gsp.c")
assert entry["sha256"] == source_hash

text = SOURCE.read_text()
encode_registry = function_window(text, "_kgspEncodePackedRegistryKeys", "_kgspEncodeSystemInfo")
encode_system = function_window(text, "_kgspEncodeSystemInfo\n(", "_kgspPrepareSystemInfo")
prepare_registry = function_window(text, "_kgspPrepareRegistry\n(", "kgspSendInitRpcs_IMPL")
send_init = function_window(text, "kgspSendInitRpcs_IMPL\n(", "_kgspVbiosVersionToStr") if False else text[
    text.index("kgspSendInitRpcs_IMPL\n("):text.index("done:\n", text.index("kgspSendInitRpcs_IMPL\n("))
]

required = {
    "walk_all_packed_entries": "for (i = 0; i < pRegTable->numEntries; i++)" in encode_registry,
    "encode_name": "NVKV_SET_STRING8_LEN(pKVContext, 0, REGKEY_NAME" in encode_registry,
    "encode_u32": "NVKV_SET_SEQ32_1U(pKVContext, 0, REGKEY_VALUE_U32" in encode_registry,
    "encode_binary": "NVKV_SET_ARRAY8(pKVContext, 0, REGKEY_VALUE_BINARY" in encode_registry,
    "encode_string": "NVKV_SET_STRING8_LEN(pKVContext, 0, REGKEY_VALUE_STRING" in encode_registry,
    "append_registry_to_system_info": "_kgspEncodePackedRegistryKeys(pKernelGsp, &pKVContext)" in encode_system,
    "package_size_query": "osPackageRegistry(pGpu, NULL, &pKernelGsp->regTableSize)" in prepare_registry,
    "package_table": "osPackageRegistry(pGpu, pKernelGsp->pRegTable, &pKernelGsp->regTableSize)" in prepare_registry,
    "send_gsp_init": "gmcapiCommand(pGpu, GMCAPI_CMD_GSP_INIT" in send_init,
    "send_encoded_system_info": "pKernelGsp->pEncodedSystemInfo" in send_init,
}
assert all(required.values()), required

gmc = GMC_TABLE.read_text()
gsp_init = re.search(
    r"GMCAPI_PHYSICAL\(\s*/\* numeric_id\s*= \*/ GMCAPI_ID\(GSP_MGMT, 0x0001\),"
    r"\s*/\* symbolic_id\s*= \*/ GSP_INIT,",
    gmc,
    re.S,
)
assert gsp_init

# Search only archived textual configuration/report inputs, not firmware strings or
# Phase-21 analysis generated from those strings.
roots = [ROOT / "cmp40hx_transfer", ROOT / "work_v15/RAW_DATA"]
suffixes = {".conf", ".log", ".txt", ".md", ".json", ".sh", ".out"}
archive_hits = []
for directory in roots:
    if not directory.exists():
        continue
    for path in directory.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        try:
            body = path.read_text(errors="strict")
        except (UnicodeError, OSError):
            continue
        for line_no, line in enumerate(body.splitlines(), 1):
            if "RegistryDwords" in line or "RmDisableDisplay" in line:
                archive_hits.append({
                    "path": str(path.relative_to(ROOT)),
                    "line": line_no,
                    "contains_registry_dwords": "RegistryDwords" in line,
                    "contains_rm_disable_display": "RmDisableDisplay" in line,
                    "text_sha256": hashlib.sha256(line.encode()).hexdigest(),
                })

assert not any(hit["contains_rm_disable_display"] for hit in archive_hits)

result = {
    "source": {
        "path": str(SOURCE.relative_to(ROOT)),
        "sha256": source_hash,
        "release": provenance["release"],
        "commit": provenance["tag"],
        "immutable_url": provenance["immutable_base"] + entry["repo_path"],
    },
    "gmcapi_table": {
        "path": str(GMC_TABLE),
        "sha256": sha256(GMC_TABLE),
        "verified_mapping": "GMCAPI_ID(GSP_MGMT=1, 0x0001) => command 0x00010001, GSP_INIT",
    },
    "checks": required,
    "archived_text_search": {
        "roots": [str(path.relative_to(ROOT)) for path in roots],
        "suffixes": sorted(suffixes),
        "hits": archive_hits,
        "rm_disable_display_hits": 0,
        "scope": "Archived textual inputs only; not current target state, binary files, archives, or generated Phase-21 analysis.",
    },
    "conclusion": (
        "615.78.08 host RM packages registry entries, encodes each typed entry after its name into "
        "the system-info NVKV stream, and sends that stream as GMCAPI GSP_INIT (0x10001). "
        "The archived textual configuration searched contains no RmDisableDisplay entry."
    ),
    "online_exact_tag_corroboration": {
        "registry_source": "https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/arch/nvalloc/unix/src/registry.c",
        "observed": "RmPackageRegistry counts and copies global registry first, then local per-device registry.",
        "os_registry_source": "https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/kernel-open/nvidia/os-registry.c",
        "observed_inputs": "NVreg_RegistryDwords global parsing and BDF-matched NVreg_RegistryDwordsPerDevice DWORD writes.",
        "provenance_limit": "Browsed exact-tag source; these two files are not in the selected locally hashed Phase 16 source subset.",
    },
    "limits": [
        "osPackageRegistry implementation is not present in the saved selected public source set; exact-tag online source was inspected separately.",
        "Absence from archived text does not prove absence from current module parameters, per-device registry, or other runtime inputs.",
        "No effective GSP key value or display restoration is established.",
    ],
}

output = PHASE / "evidence/host_registry_producer.json"
output.write_text(json.dumps(result, indent=2) + "\n")
print(f"{sum(required.values())} source-path checks PASS; command 0x10001 mapped; "
      f"{len(archive_hits)} archived RegistryDwords-related text hits; 0 RmDisableDisplay hits")

# Phase 21 target capture checklist

This is a read-only collection plan for the target BDF. It does not write GPU registers, reset devices, reload drivers, patch firmware, or change registry settings.

## 1. Identity and driver state

Run `python3 tools/collect_readonly.py` and preserve the JSON with UTC timestamp. Also preserve:

- `uname -a`
- `/sys/bus/pci/devices/0000:03:00.0/{vendor,device,subsystem_vendor,subsystem_device,revision,class}`
- `/proc/driver/nvidia/version`
- `nvidia-smi -q`
- `nvidia-smi -q -d DISPLAY,COMPUTE,PERFORMANCE`

These close identity/current-driver provenance only.

## 2. Effective configuration

Preserve read-only outputs for the exact driver interface available on the target:

- `/proc/driver/nvidia/params`
- `/proc/driver/nvidia/gpus/0000:03:00.0/information`
- `/proc/driver/nvidia/gpus/0000:03:00.0/registry`
- module command-line and service configuration sources, if readable

Record whether `RmDisableDisplay`, `RMRunFub`, `RMFubUseCaseMask`, profiler keys, and display-related keys are present. Absence in one interface is not proof of a default value.

## 3. Display capability and KMS state

Read only:

- `/sys/class/drm/*/status`, `enabled`, `modes`, `uevent`
- `/sys/kernel/debug/dri/*/` only when already mounted and readable
- `nvidia-smi --query-gpu=display_active,display_mode --format=csv`
- `dmesg`/journal lines limited to the target driver load and display initialization window

Preserve command, timestamp, BDF and return code. Do not infer physical heads/SOR/PHY from missing connector files alone.

## 4. Safe graphics correctness

On the target, run existing user-space tests only; do not install or modify drivers:

- `eglinfo` or equivalent EGL device query
- minimal OpenGL renderer/version query
- Vulkan `vulkaninfo --summary` if already installed
- CUDA device query and a small memory-copy/kernel correctness test
- KMS enumeration through existing tools, without modeset changes

Capture stdout/stderr, versions, exit codes and GPU UUID. A renderer string alone does not prove scanout.

## 5. Firmware/fuse correlation

If the target already exposes read-only interfaces, capture the exact raw values and source path for:

- host display status register corresponding to GM107 `0x21c04`
- effective GSP/RM registry/NVKV values
- display-IP capability response/status

Do not use `/dev/mem`, BAR writes, reset, or privileged probing to create new evidence.

## 6. Acceptance rules

A fresh target package must include command transcripts, UTC timestamps, BDF/UUID, input hashes and exit codes. Only then can it update the current-state rows in `REQUIREMENTS_AUDIT.md`. Historical files and static firmware remain separate evidence layers.

## Packaged collector

`tools/collect_target_package.py -o <directory>` emits `target_package.json` and `SHA256SUMS`. It records each read/command, UTC start time, return code or missing-tool status, stdout/stderr, and a package hash. Running it in the current sandbox is only a schema smoke test; the resulting local package is not target evidence.

`tools/verify_target_package.py <dir>/target_package.json` validates the package schema, read-only marker, BDF, per-record timestamps/status, and SHA256SUMS. A schema defect found during local smoke testing (missing timestamps on failed reads) was corrected in the collector before the final smoke test.

## Prepared missing CUDA correctness modes

ADDITIONAL_CUDA_PROBES.md describes the fp16/dp4a/graph source and runner. This closes the missing source-preparation step only: current local capture reports TOOLCHAIN_MISSING and no GPU execution. Use an explicitly new output directory on the authorized target, retain UUID/BDF/driver metadata and inspect compilation/output before treating any API feature as working. No runtime classification is updated merely because source exists.

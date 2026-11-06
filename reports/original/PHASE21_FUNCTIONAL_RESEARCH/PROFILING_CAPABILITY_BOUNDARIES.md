# Profiling capability boundaries — 2026-11-06

## Evidence on the target

Retained CUPTI capture proves library loading and version metadata only. The separate host-parameter capture reports RmProfilingAdminOnly=1 at its observation time. Neither capture calls a device-support API, enables counters, measures counter accuracy or proves a CMP-specific rejection. No current permission was changed or elevated.

## Documented CMP exclusion versus counter privilege

[NVIDIA CUPTI12.9.1 release notes](https://docs.nvidia.com/cupti/12.9.1/release-notes/release-notes.html) state CMP is unsupported and identify CUPTI_ERROR_CMP_DEVICE_NOT_SUPPORTED. This is documented product/tool policy, not proof that CUDA or Tensor execution is absent. Actual installed-version behavior and the API where this target rejects remain unmeasured.

The [device-support structure documentation](https://docs.nvidia.com/cupti/13.1.0/api/structCUpti__Profiler__DeviceSupported__Params.html) separates an overall support result from architecture, vGPU, confidential-compute, CMP and other factors. A successful API return must not be conflated with the overall supported flag. Fields and supported API modes vary by installed header/library version.

[NVIDIA counter-permission guidance](https://developer.nvidia.com/nvidia-development-tools-solutions-err-nvgpuctrperm-cupti) separately identifies CUPTI_ERROR_INSUFFICIENT_PRIVILEGES. Thus a captured permission failure would not by itself prove the CMP-specific tool policy is the only restriction. Conversely removing a permission restriction would not prove CMP support. No privilege change is proposed here.

## Prepared query probe — not executed

`tools/cupti_device_support.cpp` selects the CMP40HX by PCI BDF, prints UUID, CUDA-header version and CUPTI API version, initializes the profiling interface, queries device support and deinitializes. It enables no counters or callbacks and explicitly creates no CUDA context. It reports API status separately from isSupported, and prints optional reason fields only when present in the compile-time structure.

Native compilation uses the installed CUpti_Profiler_DeviceSupported_Params_STRUCT_SIZE macro, avoiding a ctypes layout guessed from another release. Runtime library/header mismatch can still cause an error; capture it as an API/ABI problem, not a GPU support verdict. The api field, when present, is reported with its zero-initialized value; identify that value against the actual installed header before interpreting the scope of the support answer.

For a target with matching headers/libraries already installed (paths may differ):

```
c++ -std=c++14 cupti_device_support.cpp -I/usr/local/cuda/include -I/usr/local/cuda/extras/CUPTI/include -L/usr/local/cuda/lib64 -L/usr/local/cuda/extras/CUPTI/lib64 -lcuda -lcupti -o /tmp/phase21-cupti-support
```

Capture source/binary hashes, build transcript, ldd resolution and UTC, then run under a bounded process timeout with existing user permissions. Verify BDF/UUID before adopting the result. Do not install libraries, use stub libcuda at runtime or run elevated to force a positive result.

Current sandbox lacks CUDA/CUPTI headers/toolchain, so this source is NOT_COMPILED_NOT_RUN as recorded in evidence/cupti_support_probe_preparation.json. No new target-support classification follows. The earlier glm_work notes used an incorrect result-string prototype; the native source uses the documented CUptiResult return and const-char-double-pointer output instead.

## Result interpretation

| Observation | Valid conclusion |
|---|---|
| cuptiGetVersion succeeds | Metadata discovery only |
| DeviceSupported API succeeds and overall is unsupported | Query worked; inspect individual reason fields |
| cmp reason explicitly unsupported | CMP policy identified for the queried library/API mode |
| Insufficient-privileges error | Permission failure at that API; other gates untested |
| Header/lib version or parameter error | Environment/ABI unresolved |
| Overall supported | Support query passes; actual counter collection still untested |

The original goal still requires identifying the exact target failure/success API and measuring counter operation safely. This preparation and published policy narrow the next question; they do not satisfy that runtime requirement.

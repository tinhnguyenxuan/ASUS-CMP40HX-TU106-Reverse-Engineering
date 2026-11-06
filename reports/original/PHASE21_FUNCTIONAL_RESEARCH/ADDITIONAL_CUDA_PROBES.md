# Additional CUDA correctness probes — prepared, not GPU-validated

Source: tools/cuda_additional_correctness.cu. Capture runner: tools/run_cuda_additional.py. Each mode is independently selectable and has one32-thread block; graph mode executes two dependent kernel nodes once. Device allocation payload is at most512 bytes, excluding CUDA context/driver allocations.

| Mode | Test | Independent expected result |
|---|---|---|
| fp16 | Load32 float2 values from VRAM, convert to half2, explicit hfma2 then read back both lanes | For lanes i/i+1, results2i+1 and2(i+1)+1, all exactly half-representable |
| dp4a | Load signed char4 vectors from VRAM; DP4A with per-thread accumulator | (-1,2,-3,4) dot (5,-6,7,-8) +i = i-70 |
| graph | Explicit dependency fill->transform, graph instantiate/launch and stream synchronize | First3i+1; then2x+5 gives6i+7 |

Runtime operands come from GPU memory for arithmetic probes rather than constant-only dot/FMA expressions. Actual instruction lowering still needs inspection of a real compiled artifact; no SASS/PTX verification is claimed. Graph output is zeroed before launch so a skipped node does not silently preserve expected results.

The binary checks CMP40HX/sm_75 and selects by BDF. The runner also checks the printed UUID against the expected target UUID, preserves original source bytes and hashes binary/outputs. Every CUDA API result, launch status, synchronization and cleanup status affects success. A failure is retained with API/code rather than classified as hardware absence. Each process has15-second CPU timeout; timed-out execution aborts remaining launches. A process timeout is not a guarantee of GPU preemption/reset.

On a target with existing toolkit supporting sm_75 and runtime headers>=11.4:

```
python3 PHASE21_FUNCTIONAL_RESEARCH/tools/run_cuda_additional.py --out /tmp/phase21-extra-cuda-NEW --bdf 0000:03:00.0
```

The directory must not already exist. No installation, sudo, clock/voltage adjustment, configuration change, MMIO access or GPU reset occurs. Compile timeout45 seconds; no test measures or claims throughput. Record host driver/GSP/ROM identity alongside results before merging into runtime conclusions.

## Validation boundary

Current sandbox has no nvcc. The runner's local v2 output is evidence/additional_cuda_local_20261106_v2/results.json with status NOT_RUN / TOOLCHAIN_MISSING; it is not a target failure. Source is reviewable but has not been compiled or executed on GPU. CPU reference checks verified exact half representability and signed dot/graph expected values only. FP16/DP4A/graph classifications remain UNKNOWN until a matched target run passes.

Primary API references: [NVIDIA integer intrinsics](https://docs.nvidia.com/cuda/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__INT.html), [NVIDIA graph management](https://docs.nvidia.com/cuda/cuda-runtime-api/cuda_runtime_api/group__CUDART__GRAPH.html). Version-specific compile compatibility remains subject to target toolkit validation.

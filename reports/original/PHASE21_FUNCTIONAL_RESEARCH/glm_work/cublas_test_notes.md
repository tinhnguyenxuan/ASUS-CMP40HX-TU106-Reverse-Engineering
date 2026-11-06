# cuBLAS correctness test notes

## File
`glm_work/cublas_correctness.cu`

## What it tests
cuBLAS `cublasSgemm` computes a single 16x16x16 SGEMM (float) on the device at
PCI BDF `0000:03:00.0`, selected with `cudaDeviceGetByPCIBusId`. Layout is
column-major: `alpha=1`, `beta=0`, `lda=M`, `ldb=K`, `ldc=M`. Device output is
compared against a column-major CPU reference over all 256 output elements;
mismatches print index, device value, reference value, and diff. Non-finite
device outputs are counted as mismatches (`isfinite`).

## Coverage
- Device selection: `cudaDeviceGetByPCIBusId(&device, "0000:03:00.0")` then
  `cudaSetDevice`; aborts if no device matches.
- cuBLAS: `cublasCreate`, `cublasSgemm` (CUBLAS_OP_N x2, column-major strides),
  `cublasDestroy` — every call wrapped in `CUBLAS_CALL`, aborts with status on
  failure.
- CUDA: `cudaMalloc` x3, `cudaMemcpy` H2D x2 + D2H x1, `cudaGetLastError`,
  `cudaFree` x3 — every call wrapped in `CUDA_CALL`, aborts with error string
  on failure.
- Inputs: deterministic small integers (A: 1..9, B: 1..6), non-constant,
  exactly representable in float; CPU reference uses float accumulation.
- Output bytes: all three allocations use `sizeof(float)` (float matrices,
  not half).
- No timing, no clocks/reset/config/MMIO changes, no benchmark code, no
  credentials.

## Compile
```
nvcc -arch=sm_75 cublas_correctness.cu -o cublas_correctness -lcublas
```

## Corrections vs. earlier WMMA test
- Device selection passes the PCI BDF string directly to
  `cudaDeviceGetByPCIBusId` instead of reading `cudaDeviceProp.pciBusID`
  (an integer, not a string) and comparing it to a string.
- Allocations use `sizeof(float)` because inputs and output are float; the
  earlier version mixed `half` inputs with a `float` output and sized buffers
  with `sizeof(half)`.

## Status
Not executed (no GPU operations permitted in this session). Review and run on
a host with a CUDA-capable sm_75+ device at PCI BDF 0000:03:00.0.

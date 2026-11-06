# Tensor correctness test notes

## File
`glm_work/tensor_correctness.cu`

## What it tests
One warp (32 threads, `<<<1, 32>>>`) computes a single 16x16x16 WMMA matrix
multiply on an sm_75 (Turing) device: half inputs (`__half`), float accumulator
(`float`), row-major layout. Device result is compared against a CPU reference
over all 256 output elements; mismatches are printed with index, device value,
reference value, and diff. The selected device's PCI BDF is reported.

## Coverage
- CUDA API: `cudaGetDeviceCount`, `cudaGetDeviceProperties`, `cudaSetDevice`,
  `cudaMalloc` x3, `cudaMemcpy` H2D x2 + D2H x1, kernel launch + `cudaGetLastError`,
  `cudaDeviceSynchronize`, `cudaFree` x3 — every call is wrapped in `CUDA_CALL`
  and aborts with the error string on failure.
- Device selection: iterates devices and matches `prop.pciBusID` against
  `0000:03:00.0`; errors out if no match.
- WMMA path: `fill_fragment` (zero acc), `load_matrix_sync` x2, `mma_sync`,
  `store_matrix_sync` with row-major strides of 16.
- Inputs: deterministic small integers (A: 1..9, B: 1..6), non-constant,
  exactly representable in half; CPU reference uses float accumulation.
- No timing, no clocks/reset/config changes, no benchmark code.

## Compile
```
nvcc -arch=sm_75 tensor_correctness.cu -o tensor_correctness
```

## Status
Not executed (no GPU operations permitted in this session). Review and run on
a host with a CUDA-capable sm_75+ device at PCI BDF 0000:03:00.0.

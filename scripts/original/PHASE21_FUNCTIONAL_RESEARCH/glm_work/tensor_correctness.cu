#include <cuda_fp16.h>
#include <mma.h>
#include <cuda_runtime.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

#define WMMA_M 16
#define WMMA_N 16
#define WMMA_K 16
#define TARGET_PCI_BDF "0000:03:00.0"
#define K_DIM 16
#define K_ELEMS (K_DIM * K_DIM) /* 256 */

#define CUDA_CALL(x)                                                          \
    do {                                                                      \
        cudaError_t __err = (x);                                              \
        if (__err != cudaSuccess) {                                           \
            fprintf(stderr, "CUDA call failed: %s -> %s (line %d)\n", #x,   \
                    cudaGetErrorString(__err), __LINE__);                     \
            exit(1);                                                          \
        }                                                                     \
    } while (0)

/* One warp (32 threads) computes one 16x16x16 half GEMM into float acc. */
__global__ void wmma_gemm_16x16x16(const half* A, const half* B, float* C) {
    nvcuda::wmma::fragment<nvcuda::wmma::matrix_a, WMMA_M, WMMA_N, WMMA_K,
                           half, nvcuda::wmma::row_major> a_frag;
    nvcuda::wmma::fragment<nvcuda::wmma::matrix_b, WMMA_M, WMMA_N, WMMA_K,
                           half, nvcuda::wmma::row_major> b_frag;
    nvcuda::wmma::fragment<nvcuda::wmma::accumulator, WMMA_M, WMMA_N, WMMA_K,
                           float> c_frag;

    nvcuda::wmma::fill_fragment(c_frag, 0.0f);

    nvcuda::wmma::load_matrix_sync(a_frag, A, WMMA_K); /* lda = 16 */
    nvcuda::wmma::load_matrix_sync(b_frag, B, WMMA_K); /* ldb = 16 */
    nvcuda::wmma::mma_sync(c_frag, a_frag, b_frag, c_frag);
    nvcuda::wmma::store_matrix_sync(C, c_frag, WMMA_N, /* ldc = 16 */
                                    nvcuda::wmma::mem_row_major);
}

static int select_device_by_pci_bus_id(const char* pci_bus_id) {
    int device_count = 0;
    CUDA_CALL(cudaGetDeviceCount(&device_count));
    if (device_count == 0) {
        fprintf(stderr, "No CUDA devices found\n");
        exit(1);
    }
    for (int i = 0; i < device_count; ++i) {
        cudaDeviceProp prop;
        CUDA_CALL(cudaGetDeviceProperties(&prop, i));
        char bus_id[32];
        CUDA_CALL(cudaDeviceGetPCIBusId(bus_id, sizeof(bus_id), i));
        if (strcmp(bus_id, pci_bus_id) == 0) {
            CUDA_CALL(cudaSetDevice(i));
            fprintf(stdout, "Selected device %d: %s (PCI BDF %s)\n", i,
                    prop.name, bus_id);
            return i;
        }
    }
    fprintf(stderr, "No CUDA device with PCI BDF %s\n", pci_bus_id);
    exit(1);
}

int main(void) {
    const int device = select_device_by_pci_bus_id(TARGET_PCI_BDF);

    const size_t mat_bytes = K_ELEMS * sizeof(half);

    /* Deterministic, non-constant small integer inputs (exact in half). */
    half h_A[K_ELEMS];
    half h_B[K_ELEMS];
    float h_C[K_ELEMS];
    float h_ref[K_ELEMS];

    for (int i = 0; i < K_ELEMS; ++i) {
        h_A[i] = __float2half(1.0f + (float)((i * 7) % 9));  /* 1..9 */
        h_B[i] = __float2half(1.0f + (float)((i * 5) % 6));  /* 1..6 */
        h_C[i] = 0.0f;
    }

    /* CPU reference: C = A * B, row-major 16x16, float accumulator. */
    for (int r = 0; r < K_DIM; ++r) {
        for (int c = 0; c < K_DIM; ++c) {
            float acc = 0.0f;
            for (int k = 0; k < K_DIM; ++k) {
                acc += __half2float(h_A[r * K_DIM + k]) *
                       __half2float(h_B[k * K_DIM + c]);
            }
            h_ref[r * K_DIM + c] = acc;
        }
    }

    half *d_A = NULL, *d_B = NULL;
    float *d_C = NULL;
    CUDA_CALL(cudaMalloc(&d_A, mat_bytes));
    CUDA_CALL(cudaMalloc(&d_B, mat_bytes));
    CUDA_CALL(cudaMalloc(&d_C, K_ELEMS * sizeof(float)));

    CUDA_CALL(cudaMemcpy(d_A, h_A, mat_bytes, cudaMemcpyHostToDevice));
    CUDA_CALL(cudaMemcpy(d_B, h_B, mat_bytes, cudaMemcpyHostToDevice));

    dim3 block(32); /* one warp */
    dim3 grid(1);
    wmma_gemm_16x16x16<<<grid, block>>>(d_A, d_B, d_C);
    CUDA_CALL(cudaGetLastError());      /* check kernel launch */
    CUDA_CALL(cudaDeviceSynchronize()); /* check kernel execution */

    CUDA_CALL(cudaMemcpy(h_C, d_C, sizeof(h_C), cudaMemcpyDeviceToHost));

    /* Compare all 256 elements. */
    int mismatch_count = 0;
    for (int i = 0; i < K_ELEMS; ++i) {
        float diff = fabsf(h_C[i] - h_ref[i]);
        if (!isfinite(h_C[i]) || diff > 1e-3f) {
            if (mismatch_count < 10) {
                int r = i / K_DIM, c = i % K_DIM;
                fprintf(stderr, "MISMATCH C[%d][%d]: device=%f ref=%f diff=%f\n",
                        r, c, h_C[i], h_ref[i], diff);
            }
            ++mismatch_count;
        }
    }

    cudaDeviceProp prop;
    CUDA_CALL(cudaGetDeviceProperties(&prop, device));

    fprintf(stdout, "Device BDF: %s\n", TARGET_PCI_BDF);
    if (mismatch_count == 0) {
        fprintf(stdout, "PASS: all 256 elements match CPU reference\n");
    } else {
        fprintf(stdout, "FAIL: %d of 256 elements mismatch\n", mismatch_count);
    }

    CUDA_CALL(cudaFree(d_A));
    CUDA_CALL(cudaFree(d_B));
    CUDA_CALL(cudaFree(d_C));

    return mismatch_count == 0 ? 0 : 1;
}

#include <cublas_v2.h>
#include <cuda_runtime.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

#define TARGET_PCI_BDF "0000:03:00.0"
#define M_DIM 16
#define N_DIM 16
#define K_DIM 16
#define C_ELEMS (M_DIM * N_DIM) /* 256 outputs */

#define CUDA_CALL(x)                                                          \
    do {                                                                      \
        cudaError_t __err = (x);                                              \
        if (__err != cudaSuccess) {                                           \
            fprintf(stderr, "CUDA call failed: %s -> %s (line %d)\\n", #x,    \
                    cudaGetErrorString(__err), __LINE__);                     \
            exit(1);                                                          \
        }                                                                     \
    } while (0)

#define CUBLAS_CALL(x)                                                        \
    do {                                                                      \
        cublasStatus_t __st = (x);                                            \
        if (__st != CUBLAS_STATUS_SUCCESS) {                                  \
            fprintf(stderr, "cuBLAS call failed: %s -> status %d (line %d)\\n", \
                    #x, (int)__st, __LINE__);                                 \
            exit(1);                                                          \
        }                                                                     \
    } while (0)

static int select_device_by_pci_bus_id(const char* pci_bus_id) {
    int device = -1;
    CUDA_CALL(cudaDeviceGetByPCIBusId(&device, pci_bus_id));
    CUDA_CALL(cudaSetDevice(device));
    fprintf(stdout, "Selected device %d (PCI BDF %s)\\n", device, pci_bus_id);
    return device;
}

int main(void) {
    const int M = M_DIM, N = N_DIM, K = K_DIM;
    const int lda = M, ldb = K, ldc = M;
    const float alpha = 1.0f, beta = 0.0f;

    /* Float bytes for float matrices (not half input bytes). */
    const size_t a_bytes = M * K * sizeof(float);
    const size_t b_bytes = K * N * sizeof(float);
    const size_t c_bytes = M * N * sizeof(float);

    /* Deterministic, non-constant small integer inputs (exact in float). */
    float h_A[M * K];
    float h_B[K * N];
    float h_C[M * N];
    float h_ref[M * N];

    for (int i = 0; i < M * K; ++i) {
        h_A[i] = (float)(1 + (i * 7) % 9);  /* 1..9 */
    }
    for (int i = 0; i < K * N; ++i) {
        h_B[i] = (float)(1 + (i * 5) % 6);  /* 1..6 */
    }
    for (int i = 0; i < M * N; ++i) {
        h_C[i] = 0.0f;
        h_ref[i] = 0.0f;
    }

    /* CPU reference: C = A * B, column-major 16x16x16, float accumulator.
       C[row + col*M] = sum_k A[row + k*M] * B[k + col*K] */
    for (int col = 0; col < N; ++col) {
        for (int row = 0; row < M; ++row) {
            float acc = 0.0f;
            for (int k = 0; k < K; ++k) {
                acc += h_A[row + k * M] * h_B[k + col * K];
            }
            h_ref[row + col * M] = acc;
        }
    }

    const int device = select_device_by_pci_bus_id(TARGET_PCI_BDF);

    float *d_A = NULL, *d_B = NULL, *d_C = NULL;
    CUDA_CALL(cudaMalloc(&d_A, a_bytes));
    CUDA_CALL(cudaMalloc(&d_B, b_bytes));
    CUDA_CALL(cudaMalloc(&d_C, c_bytes));

    CUDA_CALL(cudaMemcpy(d_A, h_A, a_bytes, cudaMemcpyHostToDevice));
    CUDA_CALL(cudaMemcpy(d_B, h_B, b_bytes, cudaMemcpyHostToDevice));

    cublasHandle_t handle = NULL;
    CUBLAS_CALL(cublasCreate(&handle));
    CUBLAS_CALL(cublasSgemm(handle, CUBLAS_OP_N, CUBLAS_OP_N,
                            M, N, K,
                            &alpha, d_A, lda, d_B, ldb, &beta, d_C, ldc));

    CUDA_CALL(cudaMemcpy(h_C, d_C, c_bytes, cudaMemcpyDeviceToHost));
    CUDA_CALL(cudaGetLastError());

    /* Check all 256 results, including isfinite. */
    int mismatch_count = 0;
    for (int i = 0; i < M * N; ++i) {
        if (!isfinite(h_C[i]) || fabsf(h_C[i] - h_ref[i]) > 1e-3f) {
            if (mismatch_count < 10) {
                int r = i % M, c = i / M;
                fprintf(stderr, "MISMATCH C[%d][%d]: device=%g ref=%g diff=%g\\n",
                        r, c, h_C[i], h_ref[i], fabsf(h_C[i] - h_ref[i]));
            }
            ++mismatch_count;
        }
    }

    fprintf(stdout, "Device BDF: %s\\n", TARGET_PCI_BDF);
    if (mismatch_count == 0) {
        fprintf(stdout, "PASS: all 256 results match CPU reference\\n");
    } else {
        fprintf(stdout, "FAIL: %d of 256 results mismatch\\n", mismatch_count);
    }

    CUDA_CALL(cudaFree(d_A));
    CUDA_CALL(cudaFree(d_B));
    CUDA_CALL(cudaFree(d_C));
    CUBLAS_CALL(cublasDestroy(handle));

    return mismatch_count == 0 ? 0 : 1;
}

#include <cuda_runtime.h>
#include <cstdio>
#include <cstring>

__global__ void calculate(float *output) {
    int index = blockIdx.x * blockDim.x + threadIdx.x;
    if (index < 4096) output[index] = float(index) * 2.0f + 1.0f;
}

int main() {
    int device = -1;
    cudaError_t status = cudaDeviceGetByPCIBusId(&device, "0000:03:00.0");
    if (status != cudaSuccess) { std::printf("BDF lookup: %s\n", cudaGetErrorString(status)); return 1; }
    status = cudaSetDevice(device);
    if (status != cudaSuccess) { std::printf("set device: %s\n", cudaGetErrorString(status)); return 1; }
    float *output = nullptr;
    status = cudaMalloc(&output, 4096 * sizeof(float));
    if (status != cudaSuccess) { std::printf("allocation: %s\n", cudaGetErrorString(status)); return 1; }
    calculate<<<16, 256>>>(output);
    status = cudaGetLastError();
    if (status != cudaSuccess) { std::printf("launch: %s\n", cudaGetErrorString(status)); return 1; }
    status = cudaDeviceSynchronize();
    if (status != cudaSuccess) { std::printf("synchronize: %s\n", cudaGetErrorString(status)); return 1; }
    float actual[4096];
    status = cudaMemcpy(actual, output, sizeof(actual), cudaMemcpyDeviceToHost);
    if (status != cudaSuccess) { std::printf("readback: %s\n", cudaGetErrorString(status)); return 1; }
    int mismatches = 0;
    for (int index = 0; index < 4096; ++index)
        if (actual[index] != float(index) * 2.0f + 1.0f) ++mismatches;
    cudaFree(output);
    std::printf("BDF=0000:03:00.0 elements=4096 mismatches=%d result=%s\n", mismatches, mismatches ? "FAIL" : "PASS");
    return mismatches ? 1 : 0;
}

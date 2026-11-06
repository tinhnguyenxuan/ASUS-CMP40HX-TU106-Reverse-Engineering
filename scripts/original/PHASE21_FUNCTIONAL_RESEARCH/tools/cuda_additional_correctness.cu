// Bounded correctness only. Requires CUDA toolkit supporting sm_75 and graph flags.
// No clock/voltage/configuration changes, MMIO, reset, or privileged operations.
#include <cuda_runtime.h>
#include <cuda_fp16.h>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#if CUDART_VERSION < 11040
#error "Requires CUDA runtime headers 11.4 or newer for graph flags"
#endif
static_assert(sizeof(int)==4,"DP4A reference requires 32-bit int");

constexpr int N = 32;
static void ck(cudaError_t e, const char* api) {
    if (e != cudaSuccess) {
        std::fprintf(stderr, "CUDA_ERROR api=%s code=%d name=%s message=%s\n",
                     api, int(e), cudaGetErrorName(e), cudaGetErrorString(e));
        throw std::runtime_error(api);
    }
}
#define CK(x) ck((x), #x)
struct Resources {
    void *a=nullptr, *b=nullptr, *out=nullptr;
    cudaStream_t stream=nullptr;
    cudaGraph_t graph=nullptr;
    cudaGraphExec_t executable=nullptr;
    bool cleanup() {
        bool ok=true;
        auto release=[&](cudaError_t e, const char* api) {
            if(e!=cudaSuccess) { std::fprintf(stderr,"CLEANUP_ERROR api=%s code=%d\n",api,int(e));ok=false; }
        };
        // After a failed CUDA call, do not reset/reload the device to recover.
        if(executable) release(cudaGraphExecDestroy(executable),"cudaGraphExecDestroy");
        if(graph) release(cudaGraphDestroy(graph),"cudaGraphDestroy");
        if(stream) release(cudaStreamDestroy(stream),"cudaStreamDestroy");
        if(out) release(cudaFree(out),"cudaFree(out)");
        if(b) release(cudaFree(b),"cudaFree(b)");
        if(a) release(cudaFree(a),"cudaFree(a)");
        return ok;
    }
};
__global__ void half_math(const float2* input, float2* output) {
    int i=threadIdx.x;
    if(i<N) {
        float2 x=input[i];
        __half2 v=__floats2half2_rn(x.x,x.y);
        __half2 r=__hfma2(v,__floats2half2_rn(2.f,2.f),__floats2half2_rn(1.f,1.f));
        output[i]=__half22float2(r);
    }
}
__global__ void dot4(const char4* a,const char4* b,int* output) {
    int i=threadIdx.x;
    if(i<N) output[i]=__dp4a(a[i],b[i],i);
}
__global__ void graph_fill(int* output) {
    int i=threadIdx.x;if(i<N) output[i]=3*i+1;
}
__global__ void graph_transform(int* output) {
    int i=threadIdx.x;if(i<N) output[i]=2*output[i]+5;
}
int main(int argc,char** argv) {
    if(argc<2 || argc>3 || (std::strcmp(argv[1],"fp16") && std::strcmp(argv[1],"dp4a") && std::strcmp(argv[1],"graph"))) {
        std::fprintf(stderr,"Usage: %s fp16|dp4a|graph [PCI-BDF]\n",argv[0]);return 2;
    }
    const char* bdf=argc==3?argv[2]:"0000:03:00.0";
    Resources r;bool ok=false;int mismatches=0;
    try {
        int device=-1;CK(cudaDeviceGetByPCIBusId(&device,bdf));
        cudaDeviceProp prop{};CK(cudaGetDeviceProperties(&prop,device));
        char actual[32]{};CK(cudaDeviceGetPCIBusId(actual,sizeof(actual),device));
        if(prop.major!=7 || prop.minor!=5 || !std::strstr(prop.name,"CMP 40HX"))
            throw std::runtime_error("Refusing unexpected GPU identity/capability");
        CK(cudaSetDevice(device));
        cudaUUID_t uuid{};CK(cudaDeviceGetUuid(&uuid,device));
        std::printf("IDENTITY bdf=%s name=%s cc=%d.%d uuid=GPU-",actual,prop.name,prop.major,prop.minor);
        for(int i=0;i<16;++i) { if(i==4||i==6||i==8||i==10) std::printf("-");std::printf("%02x",(unsigned char)uuid.bytes[i]); }
        std::printf("\n");
        CK(cudaStreamCreateWithFlags(&r.stream,cudaStreamNonBlocking));
        if(!std::strcmp(argv[1],"fp16")) {
            float2 input[N],output[N];
            for(int i=0;i<N;++i) input[i]=make_float2(float(i),float(i+1));
            CK(cudaMalloc(&r.a,sizeof(input)));CK(cudaMalloc(&r.out,sizeof(output)));
            CK(cudaMemcpy(r.a,input,sizeof(input),cudaMemcpyHostToDevice));
            CK(cudaMemset(r.out,0xff,sizeof(output)));
            half_math<<<1,N,0,r.stream>>>((float2*)r.a,(float2*)r.out);
            CK(cudaGetLastError());CK(cudaStreamSynchronize(r.stream));
            CK(cudaMemcpy(output,r.out,sizeof(output),cudaMemcpyDeviceToHost));
            for(int i=0;i<N;++i) if(output[i].x!=2*i+1 || output[i].y!=2*(i+1)+1) ++mismatches;
        } else if(!std::strcmp(argv[1],"dp4a")) {
            char4 a[N],b[N];int output[N];
            for(int i=0;i<N;++i) { a[i]=make_char4(-1,2,-3,4);b[i]=make_char4(5,-6,7,-8); }
            CK(cudaMalloc(&r.a,sizeof(a)));CK(cudaMalloc(&r.b,sizeof(b)));CK(cudaMalloc(&r.out,sizeof(output)));
            CK(cudaMemcpy(r.a,a,sizeof(a),cudaMemcpyHostToDevice));CK(cudaMemcpy(r.b,b,sizeof(b),cudaMemcpyHostToDevice));
            CK(cudaMemset(r.out,0x7f,sizeof(output)));
            dot4<<<1,N,0,r.stream>>>((char4*)r.a,(char4*)r.b,(int*)r.out);
            CK(cudaGetLastError());CK(cudaStreamSynchronize(r.stream));
            CK(cudaMemcpy(output,r.out,sizeof(output),cudaMemcpyDeviceToHost));
            for(int i=0;i<N;++i) if(output[i]!=i-70) ++mismatches;
        } else {
            int output[N];CK(cudaMalloc(&r.out,sizeof(output)));CK(cudaMemset(r.out,0,sizeof(output)));
            CK(cudaGraphCreate(&r.graph,0));
            cudaGraphNode_t first=nullptr,second=nullptr;
            void* args[]={&r.out};
            cudaKernelNodeParams params{};params.gridDim=dim3(1);params.blockDim=dim3(N);params.kernelParams=args;
            params.func=(void*)graph_fill;CK(cudaGraphAddKernelNode(&first,r.graph,nullptr,0,&params));
            params.func=(void*)graph_transform;CK(cudaGraphAddKernelNode(&second,r.graph,&first,1,&params));
            CK(cudaGraphInstantiateWithFlags(&r.executable,r.graph,0));
            CK(cudaGraphLaunch(r.executable,r.stream));CK(cudaStreamSynchronize(r.stream));
            CK(cudaMemcpy(output,r.out,sizeof(output),cudaMemcpyDeviceToHost));
            for(int i=0;i<N;++i) if(output[i]!=6*i+7) ++mismatches;
        }
        ok=mismatches==0;
    } catch(const std::exception& e) { std::fprintf(stderr,"TEST_ERROR %s\n",e.what()); }
    bool clean=r.cleanup();
    std::printf("RESULT test=%s elements=%d mismatches=%d status=%s cleanup=%s\n",argv[1],N,mismatches,ok?"PASS":"FAIL",clean?"PASS":"FAIL");
    return ok&&clean?0:1;
}

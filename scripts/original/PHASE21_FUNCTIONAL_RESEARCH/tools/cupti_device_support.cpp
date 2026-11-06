// Device support discovery only. No counters, callbacks, context creation,
// permissions/config changes, MMIO, reset or firmware invocation.
#include <cuda.h>
#include <cupti.h>
#include <cupti_profiler_target.h>
#include <cstdio>
#include <cstring>
#if CUDA_VERSION < 11050
#error "Requires CUDA/CUPTI headers providing device support query (11.5+)"
#endif
static bool driver(CUresult r,const char* api) {
    const char* name=nullptr; const char* msg=nullptr;
    if(r!=CUDA_SUCCESS) { cuGetErrorName(r,&name);cuGetErrorString(r,&msg);
        std::printf("DRIVER_ERROR api=%s code=%d name=%s message=%s\n",api,int(r),name?name:"?",msg?msg:"?");return false; }
    return true;
}
static bool cupti(CUptiResult r,const char* api) {
    const char* msg=nullptr;
    CUptiResult text_status=cuptiGetResultString(r,&msg);
    std::printf("CUPTI_CALL api=%s code=%d message=%s result_string_status=%d\n",api,int(r),text_status==CUPTI_SUCCESS&&msg?msg:"?",int(text_status));
    return r==CUPTI_SUCCESS;
}
// Fields added in newer header versions are reported as absent, not fabricated
// by ctypes offsets or a struct size copied from a different CUDA release.
#define FIELD(name) \
 template<class T> auto field_##name(const T& p,int)->decltype((void)p.name) { std::printf("FIELD " #name "=%d\n",int(p.name)); } \
 template<class T> void field_##name(const T&,long) { std::printf("FIELD " #name "=ABSENT_IN_COMPILE_HEADER\n"); }
FIELD(architecture) FIELD(sli) FIELD(vGpu) FIELD(confidentialCompute)
FIELD(cmp) FIELD(wsl) FIELD(api) FIELD(sku)
int main(int argc,char** argv) {
    if(argc>2) { std::fprintf(stderr,"Usage: %s [PCI-BDF]\n",argv[0]);return 2; }
    const char* bdf=argc==2?argv[1]:"0000:03:00.0";
    if(!driver(cuInit(0),"cuInit")) return 1;
    CUdevice dev; if(!driver(cuDeviceGetByPCIBusId(&dev,bdf),"cuDeviceGetByPCIBusId")) return 1;
    char name[128]{}; if(!driver(cuDeviceGetName(name,sizeof(name),dev),"cuDeviceGetName")) return 1;
    if(!std::strstr(name,"CMP 40HX")) { std::printf("IDENTITY_MISMATCH name=%s\n",name);return 1; }
    char actual[32]{}; if(!driver(cuDeviceGetPCIBusId(actual,sizeof(actual),dev),"cuDeviceGetPCIBusId")) return 1;
    CUuuid uuid{}; if(!driver(cuDeviceGetUuid(&uuid,dev),"cuDeviceGetUuid")) return 1;
    unsigned version=0; if(!cupti(cuptiGetVersion(&version),"cuptiGetVersion")) return 1;
    std::printf("IDENTITY bdf=%s name=%s uuid=GPU-",actual,name);
    for(int i=0;i<16;++i) {if(i==4||i==6||i==8||i==10) std::printf("-");std::printf("%02x",(unsigned char)uuid.bytes[i]);}
    std::printf("\nHEADERS cuda=%d params_size=%zu cupti_api_version=%u\n",CUDA_VERSION,size_t(CUpti_Profiler_DeviceSupported_Params_STRUCT_SIZE),version);
    CUpti_Profiler_Initialize_Params init{};init.structSize=CUpti_Profiler_Initialize_Params_STRUCT_SIZE;
    if(!cupti(cuptiProfilerInitialize(&init),"cuptiProfilerInitialize")) return 1;
    CUpti_Profiler_DeviceSupported_Params params{};
    params.structSize=CUpti_Profiler_DeviceSupported_Params_STRUCT_SIZE;params.cuDevice=dev;
    bool query_ok=cupti(cuptiProfilerDeviceSupported(&params),"cuptiProfilerDeviceSupported");
    if(query_ok) {
        std::printf("SUPPORT overall=%d equals_supported_enum=%d\n",int(params.isSupported),int(params.isSupported==CUPTI_PROFILER_CONFIGURATION_SUPPORTED));
        field_architecture(params,0);field_sli(params,0);field_vGpu(params,0);
        field_confidentialCompute(params,0);field_cmp(params,0);field_wsl(params,0);
        field_api(params,0);field_sku(params,0);
    } else std::printf("SUPPORT UNKNOWN_API_QUERY_FAILED\n");
    CUpti_Profiler_DeInitialize_Params deinit{};deinit.structSize=CUpti_Profiler_DeInitialize_Params_STRUCT_SIZE;
    bool clean=cupti(cuptiProfilerDeInitialize(&deinit),"cuptiProfilerDeInitialize");
    std::printf("PROBE_COMPLETED query_ok=%d cleanup_ok=%d counters_enabled=0\n",int(query_ok),int(clean));
    // Completed support query can report unsupported. That is not a counter PASS.
    return query_ok&&clean?0:1;
}

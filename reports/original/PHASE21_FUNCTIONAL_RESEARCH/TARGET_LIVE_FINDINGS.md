# Target live findings — 2026-11-04

Post-compute status sample for the same UUID/BDF reports P8, graphics 300 MHz,
memory 405 MHz, 12.46 W, 35 C and GPU utilization 0%. This is a single runtime
observation after the tests; it neither proves stock configuration nor long-term
stability. Source: evidence/target_live_20261104/post_compute_status.json.

## Headless clear/readback verified

The subsequent shader test compiled and linked vertex/fragment shaders, drew a
full-screen triangle into the matched CMP40HX pbuffer and read back all 16
expected green pixels. NVIDIA renderer and CUDA BDF mapping were verified; EGL
and GL error lists were clean. This is bounded shader/raster correctness, not
physical scanout or Vulkan evidence. Source: egl_shader_result.json in the live
folder. The generated probe required fixes for missing glUseProgram and GLint.

The corrected EGL probe matched the EGL device to CUDA BDF 0000:03:00.0 via
EGL_NV_device_cuda, created a 4x4 pbuffer/context, and read all 16 pixels back
as exact RGBA red. GL vendor NVIDIA Corporation, renderer NVIDIA CMP 40HX/PCIe/SSE2,
version OpenGL ES 3.2 NVIDIA 615.71.09. All recorded EGL/GL errors were clean.
This proves this bounded clear/readback operation on the target, not shader
execution, general rendering correctness, Vulkan support, or physical scanout.
Source: evidence/target_live_20261104/egl_render_final.json with source hash.
Generated constants EGL_NONE and EGL_HEIGHT required correction after prior
probe failures; those failures must not be interpreted as hardware evidence.

## Compute correctness update

CUPTI basic discovery succeeded: libcupti.so loaded and cuptiGetVersion returned
18 / CUPTI_SUCCESS. The generated ctypes result-string ABI was corrected to
return CUptiResult and accept const char ** before execution. No counters or
callbacks were enabled, so profiling correctness and counter permissions remain
unverified. Evidence: evidence/target_live_20261104/cupti_query.json.

cuBLAS SGEMM 16x16x16 also passed: all 256 outputs matched the column-major CPU
reference on BDF 0000:03:00.0. The generated source was reviewed after GLM
completed its edits. Evidence: evidence/target_live_20261104/cublas_correctness.json,
including source SHA256 and captured return code/stdout/stderr. This does not
establish performance or correctness of all cuBLAS operations.

The reviewed GLM-authored WMMA sm_75 test selected CMP40HX at 0000:03:00.0,
computed one 16x16x16 half-input / float-accumulator multiplication, and matched
all 256 output elements against the CPU reference. No performance measurement
or stock-state assertion follows. Initial generated code required fixes to BDF
selection, accumulator declaration, float output allocation/readback and NaN
checking before compilation. Source: glm_work/tensor_correctness.cu; evidence:
evidence/target_live_20261104/tensor_correctness.json. Earlier statements that
Tensor correctness was entirely untested are superseded for this bounded test.

Authenticated read-only capture: `evidence/target_live_20261104/target_package.json`.
Package verifier PASS. GPU UUID matches the retained CMP40HX identity at BDF
0000:03:00.0. Current driver and GSP are 615.71.09; static analysis of 615.78.08
does not establish the same implementation on this running firmware.

At 14:44:35Z, sysfs maps CMP40HX to DRM card1 and renderD129. The inventory
contains no connectors under card1. A connected DP-1 belongs to card0 at BDF
0000:04:00.0, a different device. It must not be cited as CMP40HX display output.
DRM node presence establishes enumeration only, not rendering correctness.

nvcc is installed. eglinfo, glxinfo, vulkaninfo and deviceQuery were not found
in PATH. Their absence does not establish lack of API support. A bounded CUDA
correctness test and direct EGL/Vulkan queries remain outstanding.

Source inventory: `evidence/target_live_20261104/drm_tool_inventory.json`.

CUDA Driver API query at 14:45:08Z: cuInit and cuDeviceGetCount returned success.
The single enumerated CUDA device matches BDF 0000:03:00.0 and reports compute
capability 7.5 and 34 multiprocessors. Every queried attribute returned success.
This establishes current CUDA initialization/enumeration and reported attributes;
kernel execution correctness and throughput remain untested.
Source: `evidence/target_live_20261104/cuda_driver_query.json`.

CUDA correctness test completed successfully: 4096 values matched the CPU
expectation exactly on BDF 0000:03:00.0. Source: target_live_20261104/cuda_correctness.json.

EGL device enumeration maps device 0 to card1/renderD129, but initialization
failed. Mesa software EGL initialized successfully. The GLVND vendor directory
contains only 50_mesa.json even though libEGL_nvidia.so.0 is installed. User REDACTED_USER
is not in video/render groups; device nodes are mode 0660 with those groups.
ACLs and actual open errors have not yet been tested, so group membership alone
does not prove access denial. These are userspace diagnostic leads, not proof
of absent display silicon. Source: egl_userspace_inventory.json in the live folder.

At 14:47:44Z, actual O_RDONLY opens of both card1 and renderD129 failed with
EACCES for the SSH user. This confirms an access restriction, beyond inference
from group membership. nvidia_drm is loaded and its modeset parameter is Y.
The standard Vulkan ICD directory contains nvidia_icd.json pointing to
libGLX_nvidia.so.0. Manifest presence does not prove Vulkan enumeration or
rendering. No permissions, group membership, modules or configuration changed.
Source: drm_access_vulkan_inventory.json in the live folder.

At 14:48:18Z, Vulkan instance creation and physical device enumeration succeeded
but returned only the llvmpipe CPU device (vendor 0x10005, device type CPU).
No NVIDIA physical device was exposed to this unprivileged process. This is a
software fallback observation under the recorded permissions/loader setup;
it does not establish physical Vulkan incapability. Source: vulkan_device_query.json.

NVIDIA-only Vulkan selection returned -9 and loader reported failure obtaining
vkCreateInstance through vk_icdGetInstanceProcAddr. A subsequent nm -D check
finds vkCreateInstance, vkGetInstanceProcAddr and vk_icdGetInstanceProcAddr all
exported in libGLX_nvidia.so.0. Therefore absent ELF exports alone do not explain
the runtime proc-address failure. Target per-GPU registry output is Binary: "";
this does not expose effective values of the investigated configuration keys.
Sources: vulkan_nvidia_only.json and nvidia_vk_symbols_registry.json.

Direct ctypes calls to the exported NVIDIA vk_icdGetInstanceProcAddr(NULL, name)
returned NULL for vkCreateInstance, vkEnumerateInstanceExtensionProperties and
vkGetInstanceProcAddr in this user environment. Thus the loader diagnostic is
reproducible below the Vulkan loader, despite the symbols existing in the ELF.
The cause and relationship to permissions remain unresolved. Evidence:
evidence/target_live_20261104/vulkan_direct_icd_dispatch.json.

Follow-up called vk_icdNegotiateLoaderICDInterfaceVersion first with version 7.
It returned -3 (initialization failure); subsequent queries still returned NULL.
The initial unnegotiated probe alone should not be treated as a complete ICD
handshake. The failed negotiation is a stronger bounded observation, not proof
of the cause. Evidence: vulkan_negotiated_dispatch.json.

The captured host module parameters include RmProfilingAdminOnly: 1 and empty
RegistryDwords / RegistryDwordsPerDevice strings. This identifies an existing
host profiling permission policy, not a measured CUPTI failure or a SKU
restriction. Empty registry strings do not prove firmware defaults or effective
RmDisableDisplay values. Source: profiling_policy_extract.json.

With a temporary GLVND manifest selecting libEGL_nvidia.so.0 for only the query
process, NVIDIA EGL enumerated one device and initialized EGL 1.5 successfully
(EGL_SUCCESS). The temporary manifest was removed on process exit; system vendor
configuration and device permissions were unchanged. This establishes NVIDIA
EGL initialization via explicit vendor selection despite the failed default
query. Rendering correctness and explicit EGL-device-to-BDF mapping remain to
be captured; initialization alone does not prove scanout. Source: egl_nvidia_only.json.

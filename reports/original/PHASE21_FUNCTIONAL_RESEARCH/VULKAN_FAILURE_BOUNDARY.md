# Vulkan failure boundary — independent audit, 2026-11-06

The retained target captures do not demonstrate a successful NVIDIA Vulkan device or render. They do establish a loader/ICD discovery failure before such a test. This is the observed failure boundary, not proof that the root cause resides exclusively in the loader.

## Checks performed offline

`tools/audit_vulkan_capture.py` parses the captured command AST without executing its Python, loading libraries or connecting to the target. Its ctypes Info fields match the reviewed VkInstanceCreateInfo LP64 order, offsets0/8/16/24/32/40/48/56 and size64. The captured command sets sType1, zero-initializes remaining fields and declares vkCreateInstance arguments. No structure-layout defect was found for that LP64 call. This does not validate uncaptured direct-dispatch call signatures or recreate the target environment.

The NVIDIA-only capture returns -9, corresponding to VK_ERROR_INCOMPATIBLE_DRIVER. Loader stderr reports failure obtaining vkCreateInstance through the NVIDIA ICD entrypoint and then no usable drivers. Default enumeration succeeds only for llvmpipe CPU rendering; it is not NVIDIA functionality evidence.

The ELF symbol capture contains definitions for vkCreateInstance, vkGetInstanceProcAddr and vk_icdGetInstanceProcAddr, while direct-probe output reports NULL proc addresses and unsuccessful interface negotiation. Those direct captures do not retain their exact commands/source, so pointer-return declarations, signature and call ordering cannot be fully audited. Their outputs are corroborating observations, not a complete ABI proof.

References for the ABI and loader interface: [Khronos Vulkan headers](https://github.com/KhronosGroup/Vulkan-Headers/blob/main/include/vulkan/vulkan_core.h), [Khronos driver interface](https://github.com/KhronosGroup/Vulkan-Loader/blob/main/docs/LoaderDriverInterface.md). Mutable upstream references were reviewed2026-11-06; the audited capture bytes are hashed in evidence/vulkan_capture_audit.json.

## Corrections to older diagnosis

| Earlier claim | Supported conclusion |
|---|---|
| Missing ICD exports eliminated | These three symbols are present in the inspected library; other initialization dependencies remain open |
| Missing/wrong library dependencies eliminated by ldd | Captured linked dependencies resolved; runtime dlopen, ABI/version or initialization failure is not excluded |
| Hardware Vulkan incapability eliminated by CUDA/GLES success | CUDA/GLES capability is demonstrated separately; Vulkan support remains UNKNOWN |
| DRM EACCES caused the Vulkan failure | Access denial is measured, but causality has not been isolated |
| libGLX filename means an X server is necessarily required | Filename/linked X11 libraries alone do not establish that requirement for this Vulkan operation |

No unsupported hardware feature, intentional CMP policy, broken silicon or restoration success follows from this failure. No permissions, groups, installed libraries, drivers or device state were changed.

## Next discriminating checks

If target access becomes available, retain full source and explicit pointer/result signatures for direct-ICD probes; compare with a minimal native-C instance/enumeration program under the existing user permissions and process-only ICD selection. Record library-open failures and exact loaded versions before attributing rejection to a SKU gate. Do not alter groups, run privileged tests or configure an X server merely to turn this negative observation into a success. A subsequent successful instance still needs target-identity selection and numerical/pixel correctness to prove rendering.

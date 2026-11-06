# Headless graphics — retained correctness evidence reconciled 2026-11-06

The 2026-11-04 EGL shader capture proves bounded headless rendering on the CMP40HX: EGL_NV_device_cuda maps the selected EGL device to CUDA BDF0000:03:00.0; GL renderer is NVIDIA CMP40HX/PCIe/SSE2, OpenGL ES3.2 NVIDIA615.71.09. Vertex and fragment shaders compiled, program linked and a triangle produced all16 expected green pixels in a4x4 pbuffer. Red clear before the draw makes a silent draw failure distinguishable. Recorded EGL/GL errors are clean.

Evidence: evidence/target_live_20261104/egl_shader_result.json. The offline reconciler checks the BDF mapping, actual pixel array and error flags rather than relying only on the saved pass label. It records the file hash in CUDA_RUNTIME_RESULTS.json. No new target execution occurred during reconciliation.

This proves the tested OpenGL ES shader/raster operation independently of physical display scanout. It does not prove full desktop OpenGL coverage, CUDA/OpenGL interop, Vulkan correctness or working HDMI/DisplayPort. The earlier claim that no EGL/OpenGL test ran in this phase is superseded.

Captured sysfs maps CMP40HX to card1/renderD129 with no connectors. Another GPU owns the connected DP-1; it is not CMP display output. Vulkan captures record an NVIDIA ICD initialization error and a DRM access failure in their tested environment. Those failures require separate diagnosis and are not evidence of silicon absence.

Next: review Vulkan loader/ICD ABI and process permissions without changing system configuration; test CUDA/GL interoperability independently if target access becomes available; obtain read-only KMS CRTC/capability evidence and physical board routing. No mode setting or scanout claim is justified by the current pbuffer test.

Vulkan diagnostic follow-up: VULKAN_FAILURE_BOUNDARY.md independently checks the captured instance-create struct ABI and narrows earlier GLM exclusion claims. No NVIDIA Vulkan render is proved; missing exports, runtime dependencies, permissions and hardware capability are distinct questions.

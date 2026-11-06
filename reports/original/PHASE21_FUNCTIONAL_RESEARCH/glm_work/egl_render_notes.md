# Ghi notes: egl_render_probe.py (PHASE21 / glm_work)

## Mục đích
Probe correctness EGL + OpenGL ES 2 headless (không hiển thị) qua Python stdlib ctypes, chỉ đọc, xuất JSON ra stdout. Tác giả tại đây, chưa chạy trên mục tiêu (không SSH, không thực thi trên target).

## File
- `glm_work/egl_render_probe.py` — schema `phase21-egl-render-v1`, trường `utc` (ISO 8601 UTC) và `command` mỗi lần chạy, `--self-check` không cần GPU.

## Luồng gọi
1. Ghi manifest GLVND tạm `{file_format_version:1.0.0, ICD:{library_path:libEGL_nvidia.so.0}}` vào NamedTemporaryFile (tự dọn dẹp), gán `__EGL_VENDOR_LIBRARY_FILENAMES`, rồi `CDLL("libEGL.so.1")` — chỉ Prozess này, không sửa hệ thống (phương pháp đã chứng minh trong `evidence/target_live_20261104/egl_nvidia_only.json`: init EGL 1.5 thành công).
2. Enumerate thiết bị qua `eglQueryDevicesEXT`; đối mỗi thiết bị gọi `eglQueryDeviceStringEXT` (`EGL_DRM_DEVICE_FILE_EXT` và `EGL_RENDER_DEVICE`) và chỉ CHỌN thiết bị cuyo chuỗi khớp `/dev/dri/card1` hoặc `/dev/dri/renderD129` (BDF 03:00.0, theo `TARGET_LIVE_FINDINGS.md` + `egl_device_query.json`). KHÔNG dùng ordinal chưa xác thực (`device[0]` không được nếu chưa khớp); nếu không tìm thấy → báo fail, không render trên thiết bị khác.
3. `eglGetPlatformDisplayEXT(EGL_PLATFORM_DEVICE_EXT, thiết bị)` → `eglInitialize` → `eglBindAPI(EGL_OPENGL_ES_API)`.
4. `eglChooseConfig` PBUFFER + ES2 + RGBA8 (red/green/blue/alpha = 8), kiểm tra lại thuộc tính config đã chọn qua `eglGetConfigAttrib`.
5. Tạo pbuffer 4x4 + context ES2 (`EGL_CONTEXT_CLIENT_VERSION = 2`), make current.
6. `glClearColor` đỏ `(1,0,0,1)`, `glClear`, `glReadPixels` 16 pixel RGBA unsigned byte, mỗi pixel phải đúng `(255,0,0,255)`.
7. `glGetString(GL_VENDOR/RENDERER/VERSION)`; kiểm tra lỗi EGL (`eglGetError`) và GL (`glGetError`) sau mỗi bước quan trọng, ghi mã lỗi vào báo cáo.
8. Dọn dẹp: release make-current → destroy context → destroy surface → terminate display trên đường hoàn tất (cũng xử lý handle đã tạo khi thất bại), rồi đóng manifest tạm (NamedTemporaryFile auto cleanup).

## Tiêu chí pass
`pass = true` chỉ khi: thiết bị khớp card1/renderD129, renderer chứa "NVIDIA", 16/16 pixel đúng (255,0,0,255), không có lỗi EGL/GL sau các bước chủ yếu.

## Ràng buộc
- Không sudo, không thay group/config, không chạm MMIO/GPU register, không reset/reload driver, không ghi node DRM, không đọc bí mật. Chỉ đệm manifest temp và biến env của quá trình này.
- Tất cả hàm EGL/GL được gọi qua ctypes với `argtypes`/`restype` rõ ràng; entry point mở rộng và GL lấy qua `eglGetProcAddress`.

## Giới hạn (quan trọng)
Chỉ chứng minh đường ống clear → readback trên thiết bị đã khớp. KHÔNG chứng minh shader, vẽ (draw), hay scanout. Xem `TARGET_LIVE_FINDINGS.md` và `evidence/target_live_20261104/egl_nvidia_only.json` cho bằng chứng hiện tại.

## Chạy local
`python3 glm_work/egl_render_probe.py --self-check` — không cần GPU, không chạm mục tiêu.

# Review: nguyên nhân thất bại EGL/Vulkan trên target (2026-11-04)

Nguồn bằng chứng: `evidence/target_live_20261104/` (capture read-only, không sửa hệ thống, không sudo, không MMIO/reset).

## 1. Bằng chứng đã thu

- CUDA Driver API: `cuInit=0`, `cuDeviceGetCount=1`, thiết bị duy nhất khớp BDF `0000:03:00.0` (CMP 40HX / TU106), compute 7.5, 34 multiprocessors, mọi thuộc tính truy vấn thành công. Nguồn: `cuda_driver_query.json`.
- CUDA correctness: kernel 4096 phần tử trên BDF `0000:03:00.0`, `mismatches=0`, `result=PASS`. Nguồn: `cuda_correctness.json`.
- DRM/KMD: kernel liệt kê `card1` và `renderD129` dưới BDF `0000:03:00.0`; `nvidia_drm` loaded, tham số `modeset=Y`. Nguồn: `drm_tool_inventory.json`, `drm_access_vulkan_inventory.json`.
- EGL thiết bị: `card1` (CMP40HX) và `card0` (R5 430) đều `eglInitialize` thất bại, `egl_version=[0,0]`; thiết bị phần mềm (llvmpipe) init thành công EGL 1.5. Nguồn: `egl_device_query.json`.
- Userspace `tinh` (uid=1000) không trong nhóm `video`/`render`; mở `O_RDONLY` `/dev/dri/card1` (0660 root:video) và `/dev/dri/renderD129` (0660 root:render) đều bị `EACCES`. Nguồn: `egl_userspace_inventory.json`, `drm_access_vulkan_inventory.json`.
- Vulkan ICD: `/usr/share/vulkan/icd.d/nvidia_icd.json` trỏ `library_path=libGLX_nvidia.so.0`; với `VK_ICD_FILENAMES=nvidia_icd.json`, `vkCreateInstance=-9`, loader báo `"Could not get 'vkCreateInstance' via 'vk_icdGetInstanceProcAddr' for ICD libGLX_nvidia.so.0"` và `"Found no drivers!"`. Nguồn: `vulkan_nvidia_only.json`.
- Vulkan mặc định (không ép ICD): instance tạo thành công nhưng chỉ liệt kê `llvmpipe` (vendor 0x10005, loại CPU), không có thiết bị NVIDIA vật lý. Nguồn: `vulkan_device_query.json`.
- EGL loader/glvnd: `/usr/share/glvnd/egl_vendor.d` chỉ chứa `50_mesa.json` (`libEGL_mesa.so.0`); không có manifest NVIDIA (`10_nvidia.json`), mặc dù `libEGL_nvidia.so.0` và `libGLX_nvidia.so.0` đã cài qua `ldconfig`. Nguồn: `egl_userspace_inventory.json`.
- `eglinfo`/`glxinfo`/`vulkaninfo`/`deviceQuery` không có trong PATH. Nguồn: `drm_tool_inventory.json`.

## 2. Đã chứng minh (khẳng định được từ bằng chứng)

1. Phần cứng CMP40HX **không** bị tắt: CUDA driver khởi tạo và kernel chạy đúng trên `card1`.
2. DRM/KMD không ẩn thiết bị: `card1`/`renderD129` được liệt kê, `nvidia_drm` chạy, `modeset=Y`.
3. EGL phần mềm (llvmpipe) hoạt động → stack EGL cơ bản không hỏng toàn bộ.
4. Quyền truy cập DRM node của `tinh` thực sự bị từ chối (`EACCES`), không chỉ là suy luận từ nhóm.

## 3. Nguyên nhân gợi ý, theo thứ tự ưu tiên (loader → ICD → permissions)

**H1 — EGL loader / nhà cung cấp glvnd (đánh giá cao nhất).**
Chỉ có `50_mesa.json` trong `egl_vendor.d`, nên `libEGL` của glvnd chọn Mesa, không phải NVIDIA. `libEGL_nvidia.so.0` có sẵn nhưng không được đăng ký làm nhà cung cấp EGL. `eglInitialize` thất bại đồng thời trên `card1` và `card0` (R5 430, có DP-1 kết nối) → thất bại không gắn liền với phần cứng CMP40HX.

**H2 — ICD Vulkan / liên kết thư viện.**
`nvidia_icd.json` trỏ `libGLX_nvidia.so.0` (thư viện GLX/NVIDIA, không phải `libvulkan_nvidia.so` thông thường). Ép loader dùng ICD này → `vkCreateInstance=-9` vì loader không lấy được `vkCreateInstance` qua `vk_icdGetInstanceProcAddr`. Có nghĩa là `libGLX_nvidia.so.0` thiếu thư viện con, sai ABI, hoặc ICD bị từ chối khởi tạo (ví dụ không mở được render node do quyền). Cần `ldd` để tách biệt.

**H3 — Quyền DRM node.**
`card1`/`renderD129` mode `0660` root:`video`/`render`; `tinh` không thành viên; mở thực tế bị `EACCES`. Đủ để làm Vulkan ICD và EGL trên render node thất bại, nhưng **chưa được tách** khỏi H1/H2 (ví dụ `eglInitialize` có thể thất bại trước khi attempt mở node, hoặc do vendor manifest thiếu).

## 4. Chưa chứng minh (suy luận còn mở — diagnose_userspace.py sẽ kiểm tra)

- `ldd` trên `libGLX_nvidia.so.0` / `libEGL_nvidia.so.0` chưa chạy → thư viện con thiếu/sai phiên bản chưa được loại trừ.
- Chưa tách được xem `EACCES` là nguyên nhân đơn độc hay đồng nguyên nhân với loader/ICD.
- Chưa tách được xem Vulkan ICD thất bại do quyền hay do liên kết ICD.
- "Không có connector dưới `card1`" **không** bằng chứng CMP40HX không có đầu ra vật lý (theo `TARGET_CAPTURE_CHECKLIST.md`: thiếu file connector không kết luận mất scanout); headless render không cần connector.
- GSP/RM (`RmDisableDisplay`…) có đang tắt display path hay không — giá trị registry/NVKV live chưa thu được.
- Tensor core, interop CUDA-GL/Vulkan, quét đồ họa/scanout thực tế chưa kiểm tra. CUDA correctness chỉ chứng minh compute, không chứng minh Tensor hay đồ họa.

## 5. Kết luận

Thất bại EGL/Vulkan nằm ở **userspace** (loader/ICD/permissions), chưa phải phần cứng bị disable. Ưu tiên chạy `diagnose_userspace.py` trên target trước khi kết luận về phần cứng hoặc GSP/RM gate.
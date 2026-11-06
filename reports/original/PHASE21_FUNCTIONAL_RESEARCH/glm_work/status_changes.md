# Đề xuất cập nhật blocker/matrix (dựa trên capture target_live_20261104 + CUDA PASS)

## By chứng mới thay đổi trạng thái

- **cuda_capability**: có bằng chứng current-target thực sự.
  - `cuda_driver_query.json`: `cuInit=0`, `cuDeviceGetCount=1`, thiết bị duy nhất khớp BDF `0000:03:00.0` (CMP 40HX), compute 7.5, 34 multiprocessors, mọi thuộc tính trả thành công.
  - `cuda_correctness.json`: kernel 4096 phần tử trên BDF `0000:03:00.0`, `mismatches=0`, `result=PASS`.
  - Còn mở: throughput, Tensor core, interop CUDA-GL/Vulkan. CUDA correctness chỉ chứng minh compute, không chứng minh Tensor hay đồ họa.
- **headless_graphics**: vẫn chưa chứng minh. EGL `eglInitialize` thất bại trên cả `card1` (CMP40HX) và `card0` (R5 430, có DP-1 kết nối); Vulkan mặc định chỉ liệt kê llvmpipe (CPU); ép ICD NVIDIA → `vkCreateInstance=-9`. Nguyên nhân gợi ý là userspace (loader/ICD/permissions), **chưa tách biệt**, chưa phải chứng minh phần cứng bị disable (CUDA PASS + DRM liệt kê card1). Không được đánh `PROVEN_STATIC`, không được đóng `B-FUNCTIONAL-DISPLAY` bằng bằng chứng tĩnh/lịch sử.
- Quyền DRM node của `tinh` thực sự bị `EACCES` (mở `card1`/`renderD129`), không chỉ suy luận từ nhóm.

## requirement_matrix.json — đề xuất đổi status

| id | status cũ | status mới | lý do |
|---|---|---|---|
| `cuda_capability` | `MISSING_CURRENT` | `PROVEN_CURRENT` | capture target có `cuInit`/`cuDeviceGetCount` thành công và kernel correctness PASS gắn BDF `0000:03:00.0` (nguồn: `cuda_driver_query.json`, `cuda_correctness.json`) |
| `headless_graphics` | `MISSING_CURRENT` | `MISSING_CURRENT` (giữ) | chưa có functional EGL/OpenGL/Vulkan/KMS trên target; lỗi userspace chưa tách nguyên nhân |
| `compute_restriction` | `PROVEN_STATIC` | giữ | bằng chứng tĩnh; runtime consumer mapping còn mở |
| `display` | `PROVEN_STATIC` | giữ | bằng chứng tĩnh; current physical capability còn mở |
| `gsp_gates` | `PROVEN_STATIC` | giữ | bằng chứng tĩnh; giá trị live registry/NVKV còn mở |
| `fuse` | `HISTORICAL_ONLY` | giữ | |
| `cross_sku_vbios` | `UNKNOWN` | giữ | |
| `feasibility` | `UNKNOWN` | giữ | |

Lưu ý: sự hiện diện của artifact tĩnh không đủ để đổi `MISSING_CURRENT/HISTORICAL_ONLY/UNKNOWN` (theo completion_rule của ma trận).

## blocker_register.json — đề xuất đổi status

| id | status cũ | status mới | lý do |
|---|---|---|---|
| `B-RUNTIME-TARGET` | `OPEN` | `CLOSED` | fresh target package từ BDF `0000:03:00.0` đã `verify_target_package.py` PASS, có timestamp và GPU UUID (TARGET_LIVE_FINDINGS: "Package verifier PASS"). Đây không phải sandbox v5 không đọc được target. Không ép giữ OPEN khi evidence thật đã đáp ứng. |
| `B-EFFECTIVE-REGISTRY` | `OPEN` | `OPEN` (giữ) | giá trị live `RmDisableDisplay`/`RMRunFub`/`RMFubUseCaseMask`/NVKV vẫn thiếu; chỉ có static ingestion path. |
| `B-FUNCTIONAL-DISPLAY` | `OPEN` | `OPEN` (giữ) | chưa có fresh functional EGL/OpenGL/Vulkan/KMS gắn UUID target; EGL/Vulkan thất bại ở userspace, nguyên nhân chưa tách (loader vs ICD vs permissions). |
| `B-REFERENCE-ROM` | `OPEN` | `OPEN` (giữ) | |
| `B-PCB-ROUTING` | `OPEN` | `OPEN` (giữ) | |

Nguyên tắc: không ép tất cả blocker thành `OPEN` nếu evidence thật đã đáp ứng (`B-RUNTIME-TARGET` đóng); đồng thời không mở wide các blocker khác chỉ vì lỗi userspace chưa tách biệt.

## Yêu cầu vẫn chưa xác minh (giữ nguyên, không force)

- **Tensor core**: CUDA correctness chạy kernel tính toán thường, không chứng minh Tensor.
- **Đồ họa / scanout**: EGL/OpenGL/Vulkan/KMS correctness chưa chứng minh trên target; thiếu connector dưới `card1` không bằng chứng mất đầu ra vật lý (theo checklist).
- **PCB CG161P REV2**: chỉ có supplied identifiers, static DCB và secondary prose; chưa có authenticated PCB photos / schematic / boardview hoặc documented continuity.

## Bước kế điểm

Chạy `glm_work/diagnose_userspace.py` trên target (chỉ đọc, mỗi subprocess có timeout, JSON ghi stdout) để tách H1 loader/glvnd, H2 liên kết ICD (`ldd libGLX_nvidia.so.0`), H3 quyền DRM node trước khi cập nhật `B-FUNCTIONAL-DISPLAY` hoặc kết luận phần cứng/GSP-RM.
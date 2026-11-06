# Ghi notes: cupti_query.py (PHASE21 / glm_work)

## Mục đích
Probe chỉ đọc (read-only) để phát hiện libcupti trên hệ thống mục tiêu và gọi hai API cơ bản đã dokument của CUPTI qua Python stdlib ctypes. Xuất JSON ra stdout. Cha sẽ chạy file này trên mục tiêu sau; tại đây chỉ tác giả, không thực thi GPU, không SSH.

## File
- `glm_work/cupti_query.py` — stdout JSON, schema `phase21-cupti-query-v1`, có `utc` (ISO 8601 UTC) và `command` cho mỗi lần chạy.

## API CUPTI gọi (chỉ hai API cơ bản)
- `cuptiGetVersion(unsigned int *version)` → `CUptiResult`
- `cuptiGetResultString(CUptiResult result, const char **text)` → `CUptiResult` (prototype corrected; native support probe uses this ABI)

ABI qua ctypes mặc định Linux x86-64 (restype `c_int`; argtypes con trỏ `c_uint` / `c_int`). Không gọi bộ đếm profiling, không đăng ký callback.

## Đường dẫn quét (giới hạn, cố định)
Thư mục: `/usr/local/cuda/lib64`, `/usr/local/cuda/lib64/stubs`, `/usr/lib/x86_64-linux-gnu`, `/usr/lib`, `/opt/cuda/lib64`, bổ sung `$CUDA_HOME`/`$CUDA_PATH/lib64` nếu biến env tồn tại (đây là đường dẫn, không phải bí mật). Mỗi thư mục dùng glob bị giới hạn (`MAX_GLOB_MATCHES=8`). JSON báo cáo: `searched_dirs`, `paths_tried`, `lib_load` (lỗi tải mỗi đường dẫn), `selected`.

## Ràng buộc quan trọng
- Truy vấn phiên bản chỉ chứng minh thư viện tải được và xuất metadata phiên bản — **KHÔNG** chứng minh quyền truy cập bộ đếm hay độ chính xác của profiling.
- `RmProfilingAdminOnly=1` không được đọc, không được sửa, giữ nguyên.
- Không sudo, không thay quyền/cấu hình, không đọc bí mật (secret), không chạm MMIO/GPU.

## Khi mở rộng
Cần tra bộ đếm profiling → thêm `cuptiSubscribe` / các API counter — chỉ khi cha yêu cầu, đây chỉ là giai đoạn khám phá.

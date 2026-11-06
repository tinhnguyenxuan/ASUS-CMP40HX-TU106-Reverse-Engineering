# Báo cáo tạm dừng — Phase 21

## Trạng thái

Nghiên cứu chưa hoàn tất. Đã kết nối target CMP 40HX BDF `0000:03:00.0`,
UUID `GPU-REDACTED`. Driver/GSP hiện tại là
`615.71.09`; phần reverse-engineering cũ dùng `615.78.08`. Không áp địa chỉ
hoặc kết luận tĩnh của bản cũ sang bản đang chạy khi chưa đối chiếu.

## Kết quả đã kiểm chứng

- CUDA khởi tạo, báo compute capability 7.5, 34 SM.
- Kernel cơ bản: 4.096 kết quả khớp CPU.
- WMMA 16×16×16: 256 kết quả khớp CPU.
- cuBLAS SGEMM 16×16: 256 kết quả khớp CPU.
- CUPTI nạp được và báo version 18; chưa kiểm thử counter/profiling.
- EGL NVIDIA khởi tạo với manifest tạm theo tiến trình; pbuffer clear/readback
  và phép vẽ shader tam giác đều PASS trên renderer CMP 40HX, đã ánh xạ BDF
  bằng `EGL_NV_device_cuda`. Không chứng minh scanout vật lý.
- Vulkan mặc định chỉ liệt kê llvmpipe; ICD NVIDIA không khởi tạo được trong
  môi trường user hiện tại. DRM card1/renderD129 trả EACCES. Nguyên nhân chính
  xác của lỗi Vulkan chưa xác định.
- Snapshot sau thử nghiệm: P8, 300 MHz, 12,46 W, 35°C, 0% GPU. Một snapshot
  không chứng minh stock hay ổn định dài hạn.

## GSP 615.71.09

File firmware cài trên target được sao về workspace, SHA-256
`78e0a2c8e4bd8a2faa1ff36137209669cdf60bd698b8f723dcf52869df82b909`.
Section `.fwversion` ghi `615.71.09`; hash file cài không chứng minh trực tiếp
byte đang nạp. Hai đoạn giống byte bản cũ đã được ánh xạ vào code section:

- `0x04b2fcb0`: cụm store `+0x328`, `+0x32c`, `+0x334`.
- `0x04b20b10`: đọc `a1+0x334`, nhánh và output byte; ngữ cảnh trước đó đọc
  child `+0x790`/`+0x88` và byte `+0x738` trên bản mới. Bản cũ dùng `+0x737`.

Đây là đối chiếu tĩnh cục bộ; tên hàm, toàn bộ control flow, giá trị runtime
và mối liên hệ nhân quả vẫn cần xác minh. Evidence:
`evidence/target_live_20261104/gsp_cross_version_context.json`.

## Việc còn lại

1. Xác định hiệu lực registry/NVKV và hoàn thiện đối chiếu GSP 615.71.09.
2. Phân biệt nguyên nhân ICD Vulkan với quyền DRM/userspace; chưa thay quyền
   hay cấu hình hệ thống. GLM đang phân tích log Vulkan.
3. Xác minh KMS/scanout và GPU output thực tế; chưa có bằng chứng routing PCB.
4. Tìm ROM TU106 revision-matched có provenance độc lập và tài liệu PCB đáng tin.
5. Profiling/counter, thư viện và workload khác còn thiếu; các test đã PASS chỉ
   xác nhận những trường hợp giới hạn mô tả ở trên.

Chi tiết runtime: `TARGET_LIVE_FINDINGS.md`. Log chứng cứ trong
`evidence/target_live_20261104/`; sổ chứng cứ: `EVIDENCE_LEDGER.md`.

## An toàn và giới hạn

Các phép đo hiện hành sử dụng SSH và thử compute/graphics nhỏ; không flash ROM,
ghi MMIO/BAR, reset/reload driver hay thay đổi registry/quyền. Chưa kết luận
được khả năng khôi phục xuất hình hoặc sự hiện diện/thiếu vắng silicon display.

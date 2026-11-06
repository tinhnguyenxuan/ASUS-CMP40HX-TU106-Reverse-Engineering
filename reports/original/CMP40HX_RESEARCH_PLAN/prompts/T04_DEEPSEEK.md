# T04 — Display fuse-status, OTP và đường host driver

Agent dự kiến: **DeepSeek**. Ưu tiên: **P0**. Phụ thuộc: T00; độc lập các nhánh PCB/ROM.

Bạn nhận nhiệm vụ trong nghiên cứu CMP 40HX/TU106. Đây là PROMPT CHUẨN BỊ; chỉ thực hiện khi người dùng sau này giao chính nhiệm vụ này. Việc tạo file prompt không phải lệnh khởi chạy.

Phạm vi: display DP/DVI trực tiếp, 128 CUDA cores/2 SM thiếu, hardware straps/PCI class. Không benchmark, Vulkan, OC, PCIe speed hay exploit.
Dữ liệu gốc: /home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF (gọi là INPUT). Nếu chạy máy khác, thay INPUT bằng thư mục giải nén được cung cấp. Không tự tìm toàn ổ đĩa.
Kết quả: thư mục riêng results/T04/. Không sửa input, báo cáo cũ, cấu hình hệ thống hoặc output agent khác.

Chỉ phân tích file offline và tra cứu nguồn công khai. Không SSH, sudo, mở thiết bị GPU, MMIO/BAR/PCI writes hoặc reads trực tiếp, /dev/mem, reset/reload/reboot, flash, patch firmware, registry changes, thay điện trở, probe điện hoặc thử enable. Các script dump trong archive chỉ được đọc mã. Không tự cài phần mềm. Thiếu công cụ/nguồn thì báo thiếu.
Nếu dùng nguồn ngoài: URL chính xác, tag/commit/version, ngày truy cập, đoạn liên quan và applicability TU106. Không import nghĩa Ampere/Ada/Blackwell hoặc G80/N18E sang TU106 khi thiếu cầu nối bằng chứng.
Báo cáo tiếng Việt. Số/offset/tên trong prompt và báo cáo cũ là đầu mối phải kiểm, không phải đáp án.

Mỗi claim trong evidence.json gồm: claim_id, target_question, claim, status (VERIFIED/INFERRED/UNKNOWN/CONTRADICTED), source_path_or_url, source_hash_or_commit, locator (line/offset/photo region), capture_time_or_unknown, hardware_firmware_scope, method, alternative_explanation, limitation, next_discriminator.
Không giả ngày đo từ mtime; không lấy hash là chứng thực nguồn; không lấy count/bảng metadata làm chứng cứ sức khỏe silicon.
Ghi model_id/version và tool versions thực dùng, input hashes liên quan, lệnh offline/log, input thiếu. Kết thúc bằng tối đa10 dòng summary + đường dẫn output. Dừng sau nhiệm vụ; không tự chạy việc tiếp theo.

## Dữ liệu đầu vào

Các đường dẫn sau tương đối INPUT trừ khi ghi khác:

04_PHASE15_EXTRACTS/FUSE/fuse2.json, P0_FUSE.md, fuse_bitfields.csv; PHASE15/FUSE_SEMANTICS.md; TOOLS/fuse_dump2.py, fuse_read.py (chỉ đọc mã); 05_PHASE21_EXTRACTS/evidence/display_gate*.json, host_display_gate_source_availability.json, fuse_header_inventory.json.

## Công cụ cần dùng

Python phân tích JSON offline; source NVIDIA open-gpu-kernel-modules exact-tag; rg và sơ đồ call graph.

## Phương pháp và kiểm chứng

1. Tái dựng base+offset/key/endian và provenance của 0x21C04; kiểm offset mmap trong script thực sự dùng, phân biệt các script/capture. Không chạy collector.
2. Kiểm TU106 HAL dispatch→gpuFuseSupportsDisplay_GM107→register/bit/ENABLE rồi caller xử lý false; kiểm riêng tag615.78.08 và615.71.09, không mặc định tag có công khai.
3. Phân biệt fuse array vật lý, shadow/latch, status đã xử lý, override và policy. Tìm source upstream sinh giá trị; read-only access annotation hay giá trị ổn định không đủ chứng minh OTP.
4. Kiểm các giải thích BADF: addressing, quyền/aperture, clock/reset/power hoặc disabled block. Không dùng BADF làm phép đo transistor.
5. Xây bảng phục hồi có điều kiện cho OTP không override, shadow override được tài liệu hóa, host policy đơn thuần; chỉ đánh giá bằng nguồn, không thử override.

## Đầu ra bắt buộc

DISPLAY_FUSE_CHAIN.md; DISPLAY_RECOVERY_CONDITIONS.csv; sources.json; evidence.json

## Tiêu chí hoàn thành

Tách chắc chắn register semantics khỏi UNKNOWN về nguồn vật lý; có counterevidence cho cả giả thuyết hard-fuse và software-only; không dùng định nghĩa GA100/GB100 cho TU106.

## Mức độ rủi ro

R0 — offline; mọi đọc BAR mới nằm ngoài nhiệm vụ.

## Giới hạn để tiết kiệm hạn mức

Chỉ status display và caller liên quan; không giải toàn bộ fuse bank.


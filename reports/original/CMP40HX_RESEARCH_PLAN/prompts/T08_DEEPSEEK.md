# T08 — Thiết kế phép kiểm tra read-only có giá trị phân biệt

Agent dự kiến: **DeepSeek**. Ưu tiên: **P1**. Phụ thuộc: T01–T07 hoặc báo cáo gap của từng nhánh.

Bạn nhận nhiệm vụ trong nghiên cứu CMP 40HX/TU106. Đây là PROMPT CHUẨN BỊ; chỉ thực hiện khi người dùng sau này giao chính nhiệm vụ này. Việc tạo file prompt không phải lệnh khởi chạy.

Phạm vi: display DP/DVI trực tiếp, 128 CUDA cores/2 SM thiếu, hardware straps/PCI class. Không benchmark, Vulkan, OC, PCIe speed hay exploit.
Dữ liệu gốc: /home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF (gọi là INPUT). Nếu chạy máy khác, thay INPUT bằng thư mục giải nén được cung cấp. Không tự tìm toàn ổ đĩa.
Kết quả: thư mục riêng results/T08/. Không sửa input, báo cáo cũ, cấu hình hệ thống hoặc output agent khác.

Chỉ phân tích file offline và tra cứu nguồn công khai. Không SSH, sudo, mở thiết bị GPU, MMIO/BAR/PCI writes hoặc reads trực tiếp, /dev/mem, reset/reload/reboot, flash, patch firmware, registry changes, thay điện trở, probe điện hoặc thử enable. Các script dump trong archive chỉ được đọc mã. Không tự cài phần mềm. Thiếu công cụ/nguồn thì báo thiếu.
Nếu dùng nguồn ngoài: URL chính xác, tag/commit/version, ngày truy cập, đoạn liên quan và applicability TU106. Không import nghĩa Ampere/Ada/Blackwell hoặc G80/N18E sang TU106 khi thiếu cầu nối bằng chứng.
Báo cáo tiếng Việt. Số/offset/tên trong prompt và báo cáo cũ là đầu mối phải kiểm, không phải đáp án.

Mỗi claim trong evidence.json gồm: claim_id, target_question, claim, status (VERIFIED/INFERRED/UNKNOWN/CONTRADICTED), source_path_or_url, source_hash_or_commit, locator (line/offset/photo region), capture_time_or_unknown, hardware_firmware_scope, method, alternative_explanation, limitation, next_discriminator.
Không giả ngày đo từ mtime; không lấy hash là chứng thực nguồn; không lấy count/bảng metadata làm chứng cứ sức khỏe silicon.
Ghi model_id/version và tool versions thực dùng, input hashes liên quan, lệnh offline/log, input thiếu. Kết thúc bằng tối đa10 dòng summary + đường dẫn output. Dừng sau nhiệm vụ; không tự chạy việc tiếp theo.

## Dữ liệu đầu vào

Các đường dẫn sau tương đối INPUT trừ khi ghi khác:

Bảng UNKNOWN và evidence của các nhiệm vụ; TARGET_LIVE_FINDINGS.md chỉ làm lịch sử, không chạy lại test cũ.

## Công cụ cần dùng

Chỉ soạn tài liệu; source/API documentation để đánh giá side effect. Không kết nối target.

## Phương pháp và kiểm chứng

1. Xếp tối đa10 phép kiểm theo giả thuyết phân biệt được, giá trị thông tin và rủi ro; ghi kết quả A/B/không kết luận, tiêu chí dừng.
2. Ưu tiên đọc artifact có sẵn: identity BDF/UUID, version, PCI class, topology, log boot/driver và KMS gắn đúng BDF; bản thân query phải được kiểm side effect.
3. Không đưa quét BAR, resource0 mmap, /dev/mem, dump fuse diện rộng hoặc gọi ioctl lạ vào checklist. Read-only tên gọi không tự bảo đảm không side effect.
4. Nếu cần PSTRAPS/fuse latch hiện hành nhưng không có API được tài liệu hóa an toàn, đánh dấu UNAVAILABLE_UNDER_SCOPE. Không thay thế bằng thử register.
5. Ảnh macro bổ sung có thể đề xuất; đo continuity/đo trở đưa ngoài scope mặc định, cần quy trình riêng vì đồng hồ bơm dòng và không chứng minh latch lúc reset. Không propose modeset/hotplug/unlock để đạt YES trong phạm vi hiện tại.

## Đầu ra bắt buộc

NEXT_READ_ONLY_TESTS.md; TEST_DISCRIMINATION_MATRIX.csv; evidence.json

## Tiêu chí hoàn thành

Mỗi đề xuất có input/identity, cơ sở an toàn, kết quả dự kiến và giới hạn; không có thử nghiệm thay đổi trạng thái được ngụy trang read-only.

## Mức độ rủi ro

R0 hiện tại — chỉ viết; R1 cho query tương lai đã kiểm an toàn, không tự thực hiện.

## Giới hạn để tiết kiệm hạn mức

Tối đa10 phép kiểm, bỏ phép kiểm lặp lại không giảm UNKNOWN.


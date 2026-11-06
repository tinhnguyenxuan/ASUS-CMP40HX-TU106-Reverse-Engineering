# T09 — Phản biện độc lập và tổng hợp khả năng phục hồi

Agent dự kiến: **DeepSeek**. Ưu tiên: **P0 ở vòng kết luận**. Phụ thuộc: T00–T08 hoàn tất hoặc có gap rõ ràng.

Bạn nhận nhiệm vụ trong nghiên cứu CMP 40HX/TU106. Đây là PROMPT CHUẨN BỊ; chỉ thực hiện khi người dùng sau này giao chính nhiệm vụ này. Việc tạo file prompt không phải lệnh khởi chạy.

Phạm vi: display DP/DVI trực tiếp, 128 CUDA cores/2 SM thiếu, hardware straps/PCI class. Không benchmark, Vulkan, OC, PCIe speed hay exploit.
Dữ liệu gốc: /home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF (gọi là INPUT). Nếu chạy máy khác, thay INPUT bằng thư mục giải nén được cung cấp. Không tự tìm toàn ổ đĩa.
Kết quả: thư mục riêng results/T09/. Không sửa input, báo cáo cũ, cấu hình hệ thống hoặc output agent khác.

Chỉ phân tích file offline và tra cứu nguồn công khai. Không SSH, sudo, mở thiết bị GPU, MMIO/BAR/PCI writes hoặc reads trực tiếp, /dev/mem, reset/reload/reboot, flash, patch firmware, registry changes, thay điện trở, probe điện hoặc thử enable. Các script dump trong archive chỉ được đọc mã. Không tự cài phần mềm. Thiếu công cụ/nguồn thì báo thiếu.
Nếu dùng nguồn ngoài: URL chính xác, tag/commit/version, ngày truy cập, đoạn liên quan và applicability TU106. Không import nghĩa Ampere/Ada/Blackwell hoặc G80/N18E sang TU106 khi thiếu cầu nối bằng chứng.
Báo cáo tiếng Việt. Số/offset/tên trong prompt và báo cáo cũ là đầu mối phải kiểm, không phải đáp án.

Mỗi claim trong evidence.json gồm: claim_id, target_question, claim, status (VERIFIED/INFERRED/UNKNOWN/CONTRADICTED), source_path_or_url, source_hash_or_commit, locator (line/offset/photo region), capture_time_or_unknown, hardware_firmware_scope, method, alternative_explanation, limitation, next_discriminator.
Không giả ngày đo từ mtime; không lấy hash là chứng thực nguồn; không lấy count/bảng metadata làm chứng cứ sức khỏe silicon.
Ghi model_id/version và tool versions thực dùng, input hashes liên quan, lệnh offline/log, input thiếu. Kết thúc bằng tối đa10 dòng summary + đường dẫn output. Dừng sau nhiệm vụ; không tự chạy việc tiếp theo.

## Dữ liệu đầu vào

Các đường dẫn sau tương đối INPUT trừ khi ghi khác:

Tất cả báo cáo nhiệm vụ và raw citation liên quan; 00_READ_FIRST/EVIDENCE_CONTRADICTIONS.md; các báo cáo Hermes/Codex/ChatGPT trong06 và Phase21.

## Công cụ cần dùng

Đọc báo cáo, tái tính nhỏ offline có mục tiêu; không chạy lại mọi phân tích.

## Phương pháp và kiểm chứng

1. Với mỗi kết luận mạnh, tìm phản đề và raw source độc lập; hai AI trích cùng báo cáo không tạo hai bằng chứng.
2. Kiểm bốn nhảy cóc: BADF→không có silicon;34SM→2SM không tồn tại;0300→có display;DCB rỗng→PHY hỏng. Kiểm polarity fuse, firmware version, parser và nguồn ảnh.
3. Đánh giá riêng DP và DVI, hard-fuse/OTP, firmware/host policy, VBIOS, strap, package/PCB; cho phép nhiều blocker đồng thời.
4. Tạo decision tree phục hồi và bảng cho mỗi mục tiêu: chứng minh/chưa biết/khả năng phần mềm/đòi hỏi phần cứng/không khả thi trong điều kiện nào/phép kiểm tiếp theo.
5. Phân biệt task hoàn tất với phục hồi được chứng minh. Không buộc YES/NO nếu dữ liệu read-only không phân biệt; nêu giới hạn cụ thể và thứ tự việc tiếp theo.

## Đầu ra bắt buộc

FINAL_FEASIBILITY_ASSESSMENT.md; CLAIM_CORRECTIONS.csv; RECOVERY_DECISION_TREE.md; evidence.json

## Tiêu chí hoàn thành

Ba câu hỏi được trả lời bằng verdict có điều kiện và nguồn; không có khẳng định bật lại thành công nếu thiếu bằng chứng chức năng thực; tất cả tranh chấp giữ được trace.

## Mức độ rủi ro

R0 — tổng hợp offline; rủi ro chốt quá chắc từ nhiều nguồn phụ thuộc.

## Giới hạn để tiết kiệm hạn mức

Tối đa một vòng yêu cầu sửa cho mỗi nhánh; chỉ mở lại nhiệm vụ khi có lỗi hoặc nguồn mới.


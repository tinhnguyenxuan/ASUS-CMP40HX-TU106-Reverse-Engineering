# T00 — Chuẩn hóa bằng chứng và mâu thuẫn

Agent dự kiến: **Qwen**. Ưu tiên: **P0**. Phụ thuộc: Không.

Bạn nhận nhiệm vụ trong nghiên cứu CMP 40HX/TU106. Đây là PROMPT CHUẨN BỊ; chỉ thực hiện khi người dùng sau này giao chính nhiệm vụ này. Việc tạo file prompt không phải lệnh khởi chạy.

Phạm vi: display DP/DVI trực tiếp, 128 CUDA cores/2 SM thiếu, hardware straps/PCI class. Không benchmark, Vulkan, OC, PCIe speed hay exploit.
Dữ liệu gốc: /home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF (gọi là INPUT). Nếu chạy máy khác, thay INPUT bằng thư mục giải nén được cung cấp. Không tự tìm toàn ổ đĩa.
Kết quả: thư mục riêng results/T00/. Không sửa input, báo cáo cũ, cấu hình hệ thống hoặc output agent khác.

Chỉ phân tích file offline và tra cứu nguồn công khai. Không SSH, sudo, mở thiết bị GPU, MMIO/BAR/PCI writes hoặc reads trực tiếp, /dev/mem, reset/reload/reboot, flash, patch firmware, registry changes, thay điện trở, probe điện hoặc thử enable. Các script dump trong archive chỉ được đọc mã. Không tự cài phần mềm. Thiếu công cụ/nguồn thì báo thiếu.
Nếu dùng nguồn ngoài: URL chính xác, tag/commit/version, ngày truy cập, đoạn liên quan và applicability TU106. Không import nghĩa Ampere/Ada/Blackwell hoặc G80/N18E sang TU106 khi thiếu cầu nối bằng chứng.
Báo cáo tiếng Việt. Số/offset/tên trong prompt và báo cáo cũ là đầu mối phải kiểm, không phải đáp án.

Mỗi claim trong evidence.json gồm: claim_id, target_question, claim, status (VERIFIED/INFERRED/UNKNOWN/CONTRADICTED), source_path_or_url, source_hash_or_commit, locator (line/offset/photo region), capture_time_or_unknown, hardware_firmware_scope, method, alternative_explanation, limitation, next_discriminator.
Không giả ngày đo từ mtime; không lấy hash là chứng thực nguồn; không lấy count/bảng metadata làm chứng cứ sức khỏe silicon.
Ghi model_id/version và tool versions thực dùng, input hashes liên quan, lệnh offline/log, input thiếu. Kết thúc bằng tối đa10 dòng summary + đường dẫn output. Dừng sau nhiệm vụ; không tự chạy việc tiếp theo.

## Dữ liệu đầu vào

Các đường dẫn sau tương đối INPUT trừ khi ghi khác:

00_READ_FIRST/*.md; CHECKSUMS.sha256; 04_PHASE15_EXTRACTS/CHECKPOINT.json; 05_PHASE21_EXTRACTS/TARGET_LIVE_FINDINGS.md; 06_PRIOR_REPORTS/*.md. Chỉ mở raw artifact khi cần giải quyết một mệnh đề cụ thể.

## Công cụ cần dùng

Trình đọc Markdown/JSON, rg, Python stdlib/hashlib khi cần kiểm hash một input.

## Phương pháp và kiểm chứng

1. Lập danh mục mệnh đề chỉ thuộc display, 2 SM thiếu và straps; gắn tác giả/file/thời điểm, loại bằng chứng và firmware.
2. Tách dữ liệu đo khỏi diễn giải. Giữ cả hai phía mâu thuẫn 0x21C04=0/1 và DATA_ENABLE=0/1, BADF→silicon vắng mặt, 0x650→17TPC.
3. Đánh dấu báo cáo PCB không có ảnh là lịch sử; gói hiện có ảnh/CAD nhưng chưa chứng minh CAD đúng BOM CMP. Không lấy nhiều bản copy làm nhiều quan sát.
4. Lập danh sách input thiếu: binary GSP đúng phiên bản, mã nguồn exact-tag, ROM GeForce có provenance, ảnh gốc nếu preview không đủ. Không tìm/quét toàn workspace.

## Đầu ra bắt buộc

CLAIM_REGISTER.csv; INPUT_GAPS.md; evidence.json

## Tiêu chí hoàn thành

Mỗi mệnh đề quan trọng có nguồn, lớp chứng cứ, phản đề và nhiệm vụ xử lý; thiếu dữ liệu được ghi rõ, không giả định đã có.

## Mức độ rủi ro

R0 — chỉ tài liệu; rủi ro chính là truyền lại kết luận cũ.

## Giới hạn để tiết kiệm hạn mức

Một lượt tóm tắt, tối đa 20 mệnh đề trọng tâm.


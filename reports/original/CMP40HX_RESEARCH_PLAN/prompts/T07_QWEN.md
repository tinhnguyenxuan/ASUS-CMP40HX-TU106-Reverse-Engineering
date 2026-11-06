# T07 — GSP policy display — kiểm chứng có giới hạn

Agent dự kiến: **Qwen**. Ưu tiên: **P1**. Phụ thuộc: T00; chỉ chạy khi có binary đúng hash; dùng T04 để giới hạn caller.

Bạn nhận nhiệm vụ trong nghiên cứu CMP 40HX/TU106. Đây là PROMPT CHUẨN BỊ; chỉ thực hiện khi người dùng sau này giao chính nhiệm vụ này. Việc tạo file prompt không phải lệnh khởi chạy.

Phạm vi: display DP/DVI trực tiếp, 128 CUDA cores/2 SM thiếu, hardware straps/PCI class. Không benchmark, Vulkan, OC, PCIe speed hay exploit.
Dữ liệu gốc: /home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF (gọi là INPUT). Nếu chạy máy khác, thay INPUT bằng thư mục giải nén được cung cấp. Không tự tìm toàn ổ đĩa.
Kết quả: thư mục riêng results/T07/. Không sửa input, báo cáo cũ, cấu hình hệ thống hoặc output agent khác.

Chỉ phân tích file offline và tra cứu nguồn công khai. Không SSH, sudo, mở thiết bị GPU, MMIO/BAR/PCI writes hoặc reads trực tiếp, /dev/mem, reset/reload/reboot, flash, patch firmware, registry changes, thay điện trở, probe điện hoặc thử enable. Các script dump trong archive chỉ được đọc mã. Không tự cài phần mềm. Thiếu công cụ/nguồn thì báo thiếu.
Nếu dùng nguồn ngoài: URL chính xác, tag/commit/version, ngày truy cập, đoạn liên quan và applicability TU106. Không import nghĩa Ampere/Ada/Blackwell hoặc G80/N18E sang TU106 khi thiếu cầu nối bằng chứng.
Báo cáo tiếng Việt. Số/offset/tên trong prompt và báo cáo cũ là đầu mối phải kiểm, không phải đáp án.

Mỗi claim trong evidence.json gồm: claim_id, target_question, claim, status (VERIFIED/INFERRED/UNKNOWN/CONTRADICTED), source_path_or_url, source_hash_or_commit, locator (line/offset/photo region), capture_time_or_unknown, hardware_firmware_scope, method, alternative_explanation, limitation, next_discriminator.
Không giả ngày đo từ mtime; không lấy hash là chứng thực nguồn; không lấy count/bảng metadata làm chứng cứ sức khỏe silicon.
Ghi model_id/version và tool versions thực dùng, input hashes liên quan, lệnh offline/log, input thiếu. Kết thúc bằng tối đa10 dòng summary + đường dẫn output. Dừng sau nhiệm vụ; không tự chạy việc tiếp theo.

## Dữ liệu đầu vào

Các đường dẫn sau tương đối INPUT trừ khi ghi khác:

05_PHASE21_EXTRACTS/GSP_CAPABILITY_GATES.md, GSP_DISPLAY_CONFIG_DATAFLOW.md, GSP_DISPLAY_OBJECT_FIELDS.md, FIRMWARE_PROVENANCE_REPORT.md và evidence/display_object_fields.json. Binary GSP không nằm trong ZIP: cần cung cấp riêng và xác thực.

## Công cụ cần dùng

readelf, disassembler RISC-V có hỗ trợ compressed instructions, Ghidra/Capstone offline, Python VA↔file mapping.

## Phương pháp và kiểm chứng

1. Xác nhận binary/version/hash trước; thiếu binary thì trả NEEDS_INPUT, không tái dựng từ prose.
2. Chỉ tái kiểm cửa sổ worker/consumer/caller đã nêu:615.78.08 worker0x04B30030, consumer0x04B20F54, field+0x334; không disassemble/quét toàn firmware.
3. Truyền tham số/object identity và đường control; phân biệt cached latch, registry missing/default/explicit1, predicate necessary/sufficient. Không gọi key bằng0 là bật display.
4. Chỉ ánh xạ615.71.09 bằng nhiều anchor và CFG; không dùng delta địa chỉ cố định hoặc prologue trùng làm định danh. Byte+0x737 không mặc định giữ nguyên.
5. Selector0x3814 và bits18:19/27 chỉ được đặt tên khi có TU106 evidence. Dừng indirect UNKNOWN, không tự đặt proprietary symbol.

## Đầu ra bắt buộc

GSP_BOUNDED_VERIFICATION.md; VERSION_FUNCTION_MAP.csv; annotated bounded disassembly; evidence.json

## Tiêu chí hoàn thành

Đường policy được chứng minh trên binary có hash hoặc ghi rõ thiếu input; không suy một branch là toàn bộ khả năng phục hồi scanout.

## Mức độ rủi ro

R0 — offline; không patch/load GSP, không cấu hình registry.

## Giới hạn để tiết kiệm hạn mức

Tối đa worker, consumer và một lớp caller/constructor liên quan; chỉ mở rộng nếu có câu hỏi phân biệt cụ thể.


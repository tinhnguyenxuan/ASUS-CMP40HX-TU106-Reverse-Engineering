# T05 — VBIOS/DCB và điều kiện đủ cho khôi phục cổng

Agent dự kiến: **Qwen**. Ưu tiên: **P0**. Phụ thuộc: T00; độc lập các nhánh khác.

Bạn nhận nhiệm vụ trong nghiên cứu CMP 40HX/TU106. Đây là PROMPT CHUẨN BỊ; chỉ thực hiện khi người dùng sau này giao chính nhiệm vụ này. Việc tạo file prompt không phải lệnh khởi chạy.

Phạm vi: display DP/DVI trực tiếp, 128 CUDA cores/2 SM thiếu, hardware straps/PCI class. Không benchmark, Vulkan, OC, PCIe speed hay exploit.
Dữ liệu gốc: /home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF (gọi là INPUT). Nếu chạy máy khác, thay INPUT bằng thư mục giải nén được cung cấp. Không tự tìm toàn ổ đĩa.
Kết quả: thư mục riêng results/T05/. Không sửa input, báo cáo cũ, cấu hình hệ thống hoặc output agent khác.

Chỉ phân tích file offline và tra cứu nguồn công khai. Không SSH, sudo, mở thiết bị GPU, MMIO/BAR/PCI writes hoặc reads trực tiếp, /dev/mem, reset/reload/reboot, flash, patch firmware, registry changes, thay điện trở, probe điện hoặc thử enable. Các script dump trong archive chỉ được đọc mã. Không tự cài phần mềm. Thiếu công cụ/nguồn thì báo thiếu.
Nếu dùng nguồn ngoài: URL chính xác, tag/commit/version, ngày truy cập, đoạn liên quan và applicability TU106. Không import nghĩa Ampere/Ada/Blackwell hoặc G80/N18E sang TU106 khi thiếu cầu nối bằng chứng.
Báo cáo tiếng Việt. Số/offset/tên trong prompt và báo cáo cũ là đầu mối phải kiểm, không phải đáp án.

Mỗi claim trong evidence.json gồm: claim_id, target_question, claim, status (VERIFIED/INFERRED/UNKNOWN/CONTRADICTED), source_path_or_url, source_hash_or_commit, locator (line/offset/photo region), capture_time_or_unknown, hardware_firmware_scope, method, alternative_explanation, limitation, next_discriminator.
Không giả ngày đo từ mtime; không lấy hash là chứng thực nguồn; không lấy count/bảng metadata làm chứng cứ sức khỏe silicon.
Ghi model_id/version và tool versions thực dùng, input hashes liên quan, lệnh offline/log, input thiếu. Kết thúc bằng tối đa10 dòng summary + đường dẫn output. Dừng sau nhiệm vụ; không tự chạy việc tiếp theo.

## Dữ liệu đầu vào

Các đường dẫn sau tương đối INPUT trừ khi ghi khác:

03_VBIOS/CMP40HX_ORIGINAL_1MB.bin và cmp40hx_t4_derivative.bin; 05_PHASE21_EXTRACTS/VBIOS_DISPLAY_ANALYSIS.md; evidence/dcb.json, board_tables.json, rom_inventory.json, rom_dcb_all_inventory.json; NVIDIA DCB spec và parser nguồn.

## Công cụ cần dùng

Python struct có bounds check, hex viewer, EnvyTools nvbios trong môi trường offline không có GPU; giữ log lỗi parser.

## Phương pháp và kiểm chứng

1. Kiểm cấu trúc ROM/PCIR và image base trước DCB; 0x28600/0x2D9AC/0x2DBC5 là đầu mối báo cáo cần kiểm, không là hằng áp mọi ROM.
2. Đối chiếu thủ công header/count/pointer với một decoder độc lập, phân biệt DCB output entries với connector entries, null pointer với bảng rỗng.
3. Kiểm CCB4.1/GPIO/HPD và driver fallback; không dùng layout CCB cũ cho4.1 hoặc index AUX làm bằng chứng đường thật.
4. Tìm tối đa hai ROM tham chiếu độc lập RTX2060S/2070 TU106 có nguồn board/revision/VBIOS/hash. Bản T4 derivative không phải control độc lập; nếu không có thì báo thiếu.
5. Đánh giá thiếu metadata là một blocker hay đã đủ giải thích; xét boot/devinit/chữ ký/tương thích nhưng không patch và không tạo ROM để flash.

## Đầu ra bắt buộc

VBIOS_DISPLAY_TABLES.json; VBIOS_RECOVERY_REPORT.md; REFERENCE_ROM_PROVENANCE.csv; evidence.json

## Tiêu chí hoàn thành

Zero-entry được kiểm bằng bytes và spec/parser hoặc bị bác bỏ có chứng cứ; phân biệt metadata với silicon; không hứa flash GeForce sẽ khôi phục.

## Mức độ rủi ro

R0 — offline; parser không đáng tin chạy giới hạn tài nguyên, không quyền đặc biệt.

## Giới hạn để tiết kiệm hạn mức

Hai ROM trong gói và tối đa hai control đủ provenance; không quét16 variant lại nếu không thêm thông tin.


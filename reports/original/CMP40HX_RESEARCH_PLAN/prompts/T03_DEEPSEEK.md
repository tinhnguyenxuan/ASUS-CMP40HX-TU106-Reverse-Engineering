# T03 — Giải nghĩa STRAP3/4/5, PCI class và Device ID

Agent dự kiến: **DeepSeek**. Ưu tiên: **P0**. Phụ thuộc: T00; tra nguồn độc lập T02, ghép pinmap sau.

Bạn nhận nhiệm vụ trong nghiên cứu CMP 40HX/TU106. Đây là PROMPT CHUẨN BỊ; chỉ thực hiện khi người dùng sau này giao chính nhiệm vụ này. Việc tạo file prompt không phải lệnh khởi chạy.

Phạm vi: display DP/DVI trực tiếp, 128 CUDA cores/2 SM thiếu, hardware straps/PCI class. Không benchmark, Vulkan, OC, PCIe speed hay exploit.
Dữ liệu gốc: /home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF (gọi là INPUT). Nếu chạy máy khác, thay INPUT bằng thư mục giải nén được cung cấp. Không tự tìm toàn ổ đĩa.
Kết quả: thư mục riêng results/T03/. Không sửa input, báo cáo cũ, cấu hình hệ thống hoặc output agent khác.

Chỉ phân tích file offline và tra cứu nguồn công khai. Không SSH, sudo, mở thiết bị GPU, MMIO/BAR/PCI writes hoặc reads trực tiếp, /dev/mem, reset/reload/reboot, flash, patch firmware, registry changes, thay điện trở, probe điện hoặc thử enable. Các script dump trong archive chỉ được đọc mã. Không tự cài phần mềm. Thiếu công cụ/nguồn thì báo thiếu.
Nếu dùng nguồn ngoài: URL chính xác, tag/commit/version, ngày truy cập, đoạn liên quan và applicability TU106. Không import nghĩa Ampere/Ada/Blackwell hoặc G80/N18E sang TU106 khi thiếu cầu nối bằng chứng.
Báo cáo tiếng Việt. Số/offset/tên trong prompt và báo cáo cũ là đầu mối phải kiểm, không phải đáp án.

Mỗi claim trong evidence.json gồm: claim_id, target_question, claim, status (VERIFIED/INFERRED/UNKNOWN/CONTRADICTED), source_path_or_url, source_hash_or_commit, locator (line/offset/photo region), capture_time_or_unknown, hardware_firmware_scope, method, alternative_explanation, limitation, next_discriminator.
Không giả ngày đo từ mtime; không lấy hash là chứng thực nguồn; không lấy count/bảng metadata làm chứng cứ sức khỏe silicon.
Ghi model_id/version và tool versions thực dùng, input hashes liên quan, lệnh offline/log, input thiếu. Kết thúc bằng tối đa10 dòng summary + đường dẫn output. Dừng sau nhiệm vụ; không tự chạy việc tiếp theo.

## Dữ liệu đầu vào

Các đường dẫn sau tương đối INPUT trừ khi ghi khác:

01_BOARDVIEW/CMP40HX_Strap_Report.docx; 00_READ_FIRST/REFERENCES_AND_PROVENANCE.md; 04_PHASE15_EXTRACTS/PCIE/pcie_map.json; kết quả T02 khi có.

## Công cụ cần dùng

Trình đọc mã nguồn/tài liệu, tìm kiếm web nguồn gốc, rg; mọi repo chốt commit/tag.

## Phương pháp và kiểm chứng

1. Tra PSTRAPS NVIDIA/EnvyTools/Nouveau, N18E và tài liệu TU106; lập ma trận phạm vi áp dụng family/package/stepping/board.
2. Tách chân STRAP vật lý, mã latch nhiều mức, bit PSTRAPS và decoded PCI class. Không gán STRAP3=bit3 hay bit4 chỉ từ tên.
3. Tìm bảng tổ hợp STRAP5:3, ngưỡng H/L/M và điều kiện DEVID_SEL/PCIE_CFG/VGA_DEVICE; nếu chỉ có laptop hoặc G80 ghi transfer gap.
4. Lập ba đường nhân quả riêng: strap→class; strap→Device ID; strap→display gate. Chỉ ghi quan hệ có source/caller; không lấy class0300 làm bằng chứng xuất hình.
5. Đối chiếu quan sát lịch sử 0302/1F0B chỉ như một sample; cùng sample không chứng minh quan hệ nhân quả.

## Đầu ra bắt buộc

STRAP_SEMANTICS_MATRIX.csv; PCI_CLASS_CAUSAL_MAP.md; sources.json; evidence.json

## Tiêu chí hoàn thành

Mỗi mapping có nguồn exact-family hoặc nhãn extrapolation/UNKNOWN. Trả lời điều gì phải đúng để R258/R261 ảnh hưởng class và điều gì vẫn không suy ra được về display.

## Mức độ rủi ro

R0 — tra cứu/offline; không đổi strap hoặc PCI config.

## Giới hạn để tiết kiệm hạn mức

Hai lượt tìm nguồn có mục tiêu; không có TU106 thì ghi gap và dừng, không mở rộng vô hạn.


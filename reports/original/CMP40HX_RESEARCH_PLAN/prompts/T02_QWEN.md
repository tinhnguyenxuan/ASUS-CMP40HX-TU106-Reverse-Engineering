# T02 — Sáu strap và trạng thái 12 footprint

Agent dự kiến: **Qwen**. Ưu tiên: **P0**. Phụ thuộc: T00; độc lập T01.

Bạn nhận nhiệm vụ trong nghiên cứu CMP 40HX/TU106. Đây là PROMPT CHUẨN BỊ; chỉ thực hiện khi người dùng sau này giao chính nhiệm vụ này. Việc tạo file prompt không phải lệnh khởi chạy.

Phạm vi: display DP/DVI trực tiếp, 128 CUDA cores/2 SM thiếu, hardware straps/PCI class. Không benchmark, Vulkan, OC, PCIe speed hay exploit.
Dữ liệu gốc: /home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF (gọi là INPUT). Nếu chạy máy khác, thay INPUT bằng thư mục giải nén được cung cấp. Không tự tìm toàn ổ đĩa.
Kết quả: thư mục riêng results/T02/. Không sửa input, báo cáo cũ, cấu hình hệ thống hoặc output agent khác.

Chỉ phân tích file offline và tra cứu nguồn công khai. Không SSH, sudo, mở thiết bị GPU, MMIO/BAR/PCI writes hoặc reads trực tiếp, /dev/mem, reset/reload/reboot, flash, patch firmware, registry changes, thay điện trở, probe điện hoặc thử enable. Các script dump trong archive chỉ được đọc mã. Không tự cài phần mềm. Thiếu công cụ/nguồn thì báo thiếu.
Nếu dùng nguồn ngoài: URL chính xác, tag/commit/version, ngày truy cập, đoạn liên quan và applicability TU106. Không import nghĩa Ampere/Ada/Blackwell hoặc G80/N18E sang TU106 khi thiếu cầu nối bằng chứng.
Báo cáo tiếng Việt. Số/offset/tên trong prompt và báo cáo cũ là đầu mối phải kiểm, không phải đáp án.

Mỗi claim trong evidence.json gồm: claim_id, target_question, claim, status (VERIFIED/INFERRED/UNKNOWN/CONTRADICTED), source_path_or_url, source_hash_or_commit, locator (line/offset/photo region), capture_time_or_unknown, hardware_firmware_scope, method, alternative_explanation, limitation, next_discriminator.
Không giả ngày đo từ mtime; không lấy hash là chứng thực nguồn; không lấy count/bảng metadata làm chứng cứ sức khỏe silicon.
Ghi model_id/version và tool versions thực dùng, input hashes liên quan, lệnh offline/log, input thiếu. Kết thúc bằng tối đa10 dòng summary + đường dẫn output. Dừng sau nhiệm vụ; không tự chạy việc tiếp theo.

## Dữ liệu đầu vào

Các đường dẫn sau tương đối INPUT trừ khi ghi khác:

01_BOARDVIEW/CG161P_R2_boardview.cad; STRAPS_NETLIST_VERIFIED.csv; CMP40HX_Strap_Report.docx; ảnh chưa chú thích tại 02_PCB_PHOTOS/HIRES_ROI và PHONE_PREVIEWS. Overlay chỉ dùng đối chiếu cuối.

## Công cụ cần dùng

Parser GenCAD offline, trình xem ảnh/OCR có kiểm tra thủ công.

## Phương pháp và kiểm chứng

1. Tự trích STRAP0..5→G1 pin→hai chân điện trở→rail, không lấy CSV làm đáp án.
2. Các cặp cần kiểm: R255/R268, R257/R269, R256/R263, R258/R261, R249/R264, R250/R265. Các pin BM5/BK5/BJ5 là đầu mối trong báo cáo, chưa phải kết quả mới.
3. Định vị bằng mốc CAD/ảnh; phân loại từng footprint POPULATED / DNP / UNCERTAIN và độ chắc riêng cho định vị và hiện diện.
4. Không suy trị số trở từ kích thước/màu; không chuyển có/không linh kiện thành mức latch H/L/M nếu thiếu ngưỡng và đường kéo trong chip.
5. Lập vector strap dưới dạng điều kiện, giữ UNKNOWN cho mức hiệu dụng; chuyển yêu cầu giải nghĩa sang T03.

## Đầu ra bắt buộc

STRAP_12_FOOTPRINTS.csv; STRAP_ASSEMBLY_REPORT.md; evidence.json

## Tiêu chí hoàn thành

Đủ 12 hàng, cả pin/net/rail và căn cứ ảnh; không gọi R258=VGA hoặc R261=3D khi chưa có mapping TU106.

## Mức độ rủi ro

R0 — offline; không đề nghị dời/hàn điện trở.

## Giới hạn để tiết kiệm hạn mức

Chỉ vùng strap; ưu tiên STRAP3/4/5, dùng 0/1/2 làm kiểm chéo định vị.


# T01 — Boardview và đường DP/DVI của PCB

Agent dự kiến: **Qwen**. Ưu tiên: **P0**. Phụ thuộc: T00; có thể chuẩn bị độc lập từ input.

Bạn nhận nhiệm vụ trong nghiên cứu CMP 40HX/TU106. Đây là PROMPT CHUẨN BỊ; chỉ thực hiện khi người dùng sau này giao chính nhiệm vụ này. Việc tạo file prompt không phải lệnh khởi chạy.

Phạm vi: display DP/DVI trực tiếp, 128 CUDA cores/2 SM thiếu, hardware straps/PCI class. Không benchmark, Vulkan, OC, PCIe speed hay exploit.
Dữ liệu gốc: /home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF (gọi là INPUT). Nếu chạy máy khác, thay INPUT bằng thư mục giải nén được cung cấp. Không tự tìm toàn ổ đĩa.
Kết quả: thư mục riêng results/T01/. Không sửa input, báo cáo cũ, cấu hình hệ thống hoặc output agent khác.

Chỉ phân tích file offline và tra cứu nguồn công khai. Không SSH, sudo, mở thiết bị GPU, MMIO/BAR/PCI writes hoặc reads trực tiếp, /dev/mem, reset/reload/reboot, flash, patch firmware, registry changes, thay điện trở, probe điện hoặc thử enable. Các script dump trong archive chỉ được đọc mã. Không tự cài phần mềm. Thiếu công cụ/nguồn thì báo thiếu.
Nếu dùng nguồn ngoài: URL chính xác, tag/commit/version, ngày truy cập, đoạn liên quan và applicability TU106. Không import nghĩa Ampere/Ada/Blackwell hoặc G80/N18E sang TU106 khi thiếu cầu nối bằng chứng.
Báo cáo tiếng Việt. Số/offset/tên trong prompt và báo cáo cũ là đầu mối phải kiểm, không phải đáp án.

Mỗi claim trong evidence.json gồm: claim_id, target_question, claim, status (VERIFIED/INFERRED/UNKNOWN/CONTRADICTED), source_path_or_url, source_hash_or_commit, locator (line/offset/photo region), capture_time_or_unknown, hardware_firmware_scope, method, alternative_explanation, limitation, next_discriminator.
Không giả ngày đo từ mtime; không lấy hash là chứng thực nguồn; không lấy count/bảng metadata làm chứng cứ sức khỏe silicon.
Ghi model_id/version và tool versions thực dùng, input hashes liên quan, lệnh offline/log, input thiếu. Kết thúc bằng tối đa10 dòng summary + đường dẫn output. Dừng sau nhiệm vụ; không tự chạy việc tiếp theo.

## Dữ liệu đầu vào

Các đường dẫn sau tương đối INPUT trừ khi ghi khác:

01_BOARDVIEW/CG161P_R2_boardview.cad; Original_Boardview.rar chỉ khi CAD có vấn đề; 02_PCB_PHOTOS/PHONE_PREVIEWS, HIRES_ROI; 06_PRIOR_REPORTS/CMP40HX_PCB_PHASE_CROSSCHECK.md và CMP40HX_PHOTO_VS_CG161P_PHASE_REPORT.md.

## Công cụ cần dùng

GenCAD/OpenBoardView đọc offline, parser text Python, trình xem ảnh; không dùng ảnh sinh bằng AI làm chứng cứ.

## Phương pháp và kiểm chứng

1. Xác định revision, mặt board, đơn vị/tọa độ; chỉ trích subgraph liên quan J1 DP, J5 DVI và G1. Không phân tích VRM/OC.
2. Lần từng lane đến pad GPU qua linh kiện nối tiếp/ghép AC; lập nhánh AUX hoặc DDC, HPD, nguồn cổng, ESD. Phân biệt đường net logic trong CAD với đường đồng thực tế.
3. Đăng ký ảnh với CAD bằng ít nhất ba mốc không thẳng hàng, kiểm thêm mốc độc lập; ghi xoay/lật/phối cảnh và sai số. Không tin overlay có sẵn mặc định.
4. Mỗi đoạn gán CAD_ONLY / PHOTO_SUPPORTED / MEASUREMENT_SUPPORTED / UNKNOWN. Không suy thiếu trace nội lớp từ ảnh bề mặt; không suy toàn tuyến tốt vì có đầu cắm.
5. Liệt kê đoạn nào nếu thiếu sẽ là điều kiện cản trở DP/DVI và loại bằng chứng bổ sung tối thiểu. Không đưa hướng dẫn sửa bo.

## Đầu ra bắt buộc

DISPLAY_ROUTE_MATRIX.csv; PCB_DISPLAY_REPORT.md; sơ đồ đường tín hiệu có dẫn line CAD và tọa độ ảnh; evidence.json

## Tiêu chí hoàn thành

DP và DVI có chuỗi endpoint đầy đủ hoặc điểm đứt thông tin rõ ràng; tách thiết kế GeForce và lắp ráp CMP; mọi kết luận về routing có nguồn.

## Mức độ rủi ro

R0 — offline; nhầm pad hoặc BOM là rủi ro suy luận cao.

## Giới hạn để tiết kiệm hạn mức

Ưu tiên một tuyến DP và một tuyến DVI; dừng tại đoạn không đủ ảnh thay vì suy diễn.


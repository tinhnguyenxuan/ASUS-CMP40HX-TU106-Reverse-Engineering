# T06 — 2 SM thiếu: floorsweeping, fuse và khả năng phục hồi

Agent dự kiến: **DeepSeek**. Ưu tiên: **P0**. Phụ thuộc: T00; độc lập display.

Bạn nhận nhiệm vụ trong nghiên cứu CMP 40HX/TU106. Đây là PROMPT CHUẨN BỊ; chỉ thực hiện khi người dùng sau này giao chính nhiệm vụ này. Việc tạo file prompt không phải lệnh khởi chạy.

Phạm vi: display DP/DVI trực tiếp, 128 CUDA cores/2 SM thiếu, hardware straps/PCI class. Không benchmark, Vulkan, OC, PCIe speed hay exploit.
Dữ liệu gốc: /home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF (gọi là INPUT). Nếu chạy máy khác, thay INPUT bằng thư mục giải nén được cung cấp. Không tự tìm toàn ổ đĩa.
Kết quả: thư mục riêng results/T06/. Không sửa input, báo cáo cũ, cấu hình hệ thống hoặc output agent khác.

Chỉ phân tích file offline và tra cứu nguồn công khai. Không SSH, sudo, mở thiết bị GPU, MMIO/BAR/PCI writes hoặc reads trực tiếp, /dev/mem, reset/reload/reboot, flash, patch firmware, registry changes, thay điện trở, probe điện hoặc thử enable. Các script dump trong archive chỉ được đọc mã. Không tự cài phần mềm. Thiếu công cụ/nguồn thì báo thiếu.
Nếu dùng nguồn ngoài: URL chính xác, tag/commit/version, ngày truy cập, đoạn liên quan và applicability TU106. Không import nghĩa Ampere/Ada/Blackwell hoặc G80/N18E sang TU106 khi thiếu cầu nối bằng chứng.
Báo cáo tiếng Việt. Số/offset/tên trong prompt và báo cáo cũ là đầu mối phải kiểm, không phải đáp án.

Mỗi claim trong evidence.json gồm: claim_id, target_question, claim, status (VERIFIED/INFERRED/UNKNOWN/CONTRADICTED), source_path_or_url, source_hash_or_commit, locator (line/offset/photo region), capture_time_or_unknown, hardware_firmware_scope, method, alternative_explanation, limitation, next_discriminator.
Không giả ngày đo từ mtime; không lấy hash là chứng thực nguồn; không lấy count/bảng metadata làm chứng cứ sức khỏe silicon.
Ghi model_id/version và tool versions thực dùng, input hashes liên quan, lệnh offline/log, input thiếu. Kết thúc bằng tối đa10 dòng summary + đường dẫn output. Dừng sau nhiệm vụ; không tự chạy việc tiếp theo.

## Dữ liệu đầu vào

Các đường dẫn sau tương đối INPUT trừ khi ghi khác:

04_PHASE15_EXTRACTS/TOPOLOGY/silicon_topology.json/.md, topology_unknowns.md; FUSE/fuse2.json; PHASE15/fuse_analysis.json, fuse_deep.json; 06_PRIOR_REPORTS/BAO_CAO_DAY_DU.md; NVIDIA Turing whitepaper và source topology/floorsweep TU106.

## Công cụ cần dùng

Python bitmask offline; source browser NVIDIA/Nouveau/EnvyTools; call/dataflow graph.

## Phương pháp và kiểm chứng

1. Kiểm nguồn 34SM và cấu hình tham chiếu36SM; phân biệt count API, physical SM index, TPC/GPC logical remap và arithmetic128core.
2. Lần fuse/status→TPC-disable mask từng GPC→effective floorsweep→GR/FECS topology→API count. Ghi polarity, units, valid bits, remapping; không giải0x21650=0x0004001F bằng khớp con số.
3. Tách disable do OTP, fuse shadow, firmware/software mask, đơn vị lỗi binning, biến thể die/package; floorsweeping là cơ chế không đồng nghĩa software-only.
4. Thiết kế so sánh controls 34SM RTX2060S và36SM RTX2070 cùng họ/stepping khi có dữ liệu, xét confounder SKU và revision; không tự thu dump mới.
5. Kết luận điều kiện: policy-only là ứng viên phục hồi, OTP không override hoặc defect bắt buộc là cản trở; không xác nhận sức khỏe đơn vị chưa từng được chạy bằng phân tích mask.

## Đầu ra bắt buộc

SM_DISABLE_CHAIN.md; TPC_MASK_CANDIDATES.csv; CUDA128_RECOVERY_MATRIX.md; evidence.json

## Tiêu chí hoàn thành

Trả lời riêng tồn tại transistor, được enumerate, khả dụng điện/chức năng và khả năng khôi phục; mỗi UNKNOWN có phép phân biệt hoặc giới hạn không thể phân biệt bằng read-only.

## Mức độ rủi ro

R0 — offline; không unlock mask, thử SM bị disable hoặc benchmark.

## Giới hạn để tiết kiệm hạn mức

Chỉ một TPC/2SM chênh và pipeline liên quan; không nghiên cứu tăng hiệu năng.


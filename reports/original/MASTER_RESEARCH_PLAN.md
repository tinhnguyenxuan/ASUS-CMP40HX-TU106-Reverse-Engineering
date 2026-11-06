# MASTER RESEARCH PLAN — CMP 40HX / TU106

Ngày lập: 2026-11-05. Trạng thái: **PLAN ONLY — CHƯA THỰC THI**.

Mục tiêu là đánh giá khả năng phục hồi chức năng của chính card CMP 40HX: xuất hình trực tiếp DP/DVI, kích hoạt 2 SM/128 CUDA cores còn thiếu, và quan hệ hardware straps với PCI class/Device ID/display. Kế hoạch không kết luận trước rằng phục hồi được hoặc không được.

## 1. Cơ sở lập kế hoạch và giới hạn

Sử dụng tóm tắt, báo cáo, ảnh và bằng chứng quan trọng trong `GPT6_ASTRA_CMP40HX_HANDOFF.zip`. Theo yêu cầu cuối, không tiếp tục quét mọi file hay reverse engineering toàn firmware. Việc tiếp nhận tài liệu không phải tái xác minh mọi kết luận kỹ thuật.

Archive có 89 tệp; SHA-256:
`71b6f782546e34ad928b76d733d645e04d83a10b0c82dca23e2b886bf9e99f4b`.
Danh mục tiếp nhận: [INPUT_COVERAGE.json](CMP40HX_INDEPENDENT_REVIEW/INPUT_COVERAGE.json).
Bản giải nén dùng làm đầu vào: `CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF/`.

Những điều dưới đây là **đầu mối từ tài liệu bàn giao, chưa phải kết quả nghiên cứu mới**:

| Chủ đề | Bằng chứng/khẳng định đang có | Câu hỏi cần phân biệt |
|---|---|---|
| Display status | Dump lưu có base0x21000, key3076, báo cáo Phase21 diễn giải0x21C04 bit0=1 với ENABLE=0; tài liệu cũ lại ghi0 hoặc enable=1 | Sai capture/offset/polarity, hay khác trạng thái? Nguồn status là OTP, shadow hay policy? |
| Display policy | RmDisableDisplay, field+0x334; host helper GM107 được nói là chọn cho TU106 | Predicate cần hay đủ? Có chạy trên firmware thực tế không? |
| Firmware | RE cũ615.78.08, báo cáo runtime615.71.09 | Mapping có đúng phiên bản? Gói ZIP không chứa binary GSP để tự tái kiểm |
| VBIOS | DCB/output và connector entries được báo cáo bằng0; có hai ROM CMP/derivative | Parser đúng không? Fallback init thế nào? Thiếu metadata có phải blocker duy nhất? |
| PCB | CAD GeForce CG161P R2, ảnh CMP có J1/J5; overlay strap có sẵn | Thiết kế có khớp lắp ráp CMP? Lane/AUX/DDC/HPD đến package có đủ không? |
| 2 SM thiếu | Báo cáo34SM thay vì36SM tham chiếu; raw+0x650 được gán nghĩa chưa chắc | Effective topology từ mask nào? OTP, software floorsweep, defect hay die khác? |
| Straps | CSV gán STRAP3 BM5 R258/R261; STRAP4 BK5 R249/R264; STRAP5 BJ5 R250/R265 | Netlist/ảnh có đúng không? Mapping TU106 đến class/ID có bằng chứng nào? |
| Runtime | Có báo cáo headless render; DP đang connected trên GPU khác | Không được dùng làm bằng chứng xuất hình trực tiếp từ CMP |

Không nghiên cứu benchmark, Tensor/CUPTI/Vulkan, OC, nguồn công suất, PCIe speed hoặc exploit. Không mở lại các nhánh cũ chỉ vì có tài liệu.

## 2. Ba câu hỏi và ngưỡng kết luận

### Display DP/DVI

Đánh giá độc lập chuỗi: controller/head → SOR/PHY → package → PCB/lane và AUX/DDC/HPD → cấu hình VBIOS → driver/GSP/KMS. Có thể nhiều tầng chặn đồng thời.

| Điều kiện được chứng minh trong nghiên cứu tương lai | Đánh giá phục hồi được phép đưa ra |
|---|---|
| OTP vô hiệu hóa chức năng bắt buộc và không có override khả dụng được chứng minh | Không có đường phục hồi bằng phần mềm trong cơ chế đã kiểm; không suy điều này chỉ từ tên FUSE_STATUS |
| Khối die/package bắt buộc không tồn tại hoặc không khả dụng, có bằng chứng trực tiếp | Đổi strap/VBIOS không thể tạo lại khối đó |
| Chỉ policy có thể đảo ngược, toàn bộ hardware chain đã xác nhận | Ứng viên phục hồi bằng phần mềm; chưa gọi thành công trước bằng chứng tín hiệu thực |
| VBIOS thiếu route, hardware tốt | Có điều kiện khả thi ở metadata/init; còn tương thích, chữ ký và các gate khác; không tự flash |
| Thiếu linh kiện hoặc routing PCB | Phần mềm đơn thuần không đủ; phân biệt linh kiện ngoài với trace/package không thể sửa bằng cấu hình |
| Chỉ class đổi0302→0300 | Chứng minh enumeration thay đổi, không chứng minh DP/DVI hoạt động |
| Dữ liệu không phân biệt được các khả năng | UNKNOWN, ghi rõ bằng chứng tối thiểu còn thiếu |

Verdict DP và DVI phải riêng. `RECOVERY_VERIFIED` cần bằng chứng đầu ra vật lý gắn đúng CMP/BDF, màn hình nhận ảnh qua chính cổng và điều kiện đo rõ ràng. Kế hoạch chỉ đọc có thể **không đủ** đạt ngưỡng này; không mở rộng sang thử enable để ép ra YES.

### 128 CUDA cores

Tách bốn mệnh đề: transistor tồn tại; đơn vị được phép enumerate; đơn vị hoạt động đúng; có đường kích hoạt lại khả dụng. Số34SM không giải quyết cả bốn.

Nếu chỉ software mask và có cơ chế hợp lệ thì đánh giá ứng viên có điều kiện. Nếu OTP không override hoặc đơn vị hỏng được chứng minh thì không có đường phục hồi bằng cấu hình thông thường. Nếu chỉ biết effective mask, phải giữ UNKNOWN về sức khỏe/nguồn disable. Phép tính2SM×64 không chứng minh có thể sử dụng chúng.

### Hardware straps

Cần nối đủ các lớp: refdes/pad → net/chân GPU → trạng thái lắp ráp → mức latch hiệu dụng → semantic đúng TU106 → PCI class/Device ID. Quan hệ tới display cần chứng minh riêng. Không dùng tên STRAP3 làm số bit register, không dùng ảnh điện trở để suy mức reset chắc chắn, không áp bảng laptop/G80 nguyên xi.

## 3. Phân công nhiệm vụ

Tên Qwen/DeepSeek là phân công dự kiến, không khẳng định endpoint hoặc phiên bản model đã được cấu hình. Không khởi chạy agent trong phiên lập kế hoạch. Khi triển khai, model xem ảnh phải có công cụ vision; nếu không có, báo thiếu thay vì đoán.

Mỗi prompt dưới đây độc lập về chỉ dẫn, có input, công cụ, phương pháp, đầu ra, tiêu chí hoàn thành, rủi ro và điểm dừng.

| ID | Agent | Nhiệm vụ | Ưu tiên | Phụ thuộc |
|---|---|---|---|---|
| [T00](CMP40HX_RESEARCH_PLAN/prompts/T00_QWEN.md) | Qwen | Chuẩn hóa bằng chứng và mâu thuẫn | P0 | Không |
| [T01](CMP40HX_RESEARCH_PLAN/prompts/T01_QWEN.md) | Qwen | Boardview và đường DP/DVI của PCB | P0 | T00; có thể chuẩn bị độc lập từ input |
| [T02](CMP40HX_RESEARCH_PLAN/prompts/T02_QWEN.md) | Qwen | Sáu strap và trạng thái 12 footprint | P0 | T00; độc lập T01 |
| [T03](CMP40HX_RESEARCH_PLAN/prompts/T03_DEEPSEEK.md) | DeepSeek | Giải nghĩa STRAP3/4/5, PCI class và Device ID | P0 | T00; tra nguồn độc lập T02, ghép pinmap sau |
| [T04](CMP40HX_RESEARCH_PLAN/prompts/T04_DEEPSEEK.md) | DeepSeek | Display fuse-status, OTP và đường host driver | P0 | T00; độc lập các nhánh PCB/ROM |
| [T05](CMP40HX_RESEARCH_PLAN/prompts/T05_QWEN.md) | Qwen | VBIOS/DCB và điều kiện đủ cho khôi phục cổng | P0 | T00; độc lập các nhánh khác |
| [T06](CMP40HX_RESEARCH_PLAN/prompts/T06_DEEPSEEK.md) | DeepSeek | 2 SM thiếu: floorsweeping, fuse và khả năng phục hồi | P0 | T00; độc lập display |
| [T07](CMP40HX_RESEARCH_PLAN/prompts/T07_QWEN.md) | Qwen | GSP policy display — kiểm chứng có giới hạn | P1 | T00; chỉ chạy khi có binary đúng hash; dùng T04 để giới hạn caller |
| [T08](CMP40HX_RESEARCH_PLAN/prompts/T08_DEEPSEEK.md) | DeepSeek | Thiết kế phép kiểm tra read-only có giá trị phân biệt | P1 | T01–T07 hoặc báo cáo gap của từng nhánh |
| [T09](CMP40HX_RESEARCH_PLAN/prompts/T09_DEEPSEEK.md) | DeepSeek | Phản biện độc lập và tổng hợp khả năng phục hồi | P0 ở vòng kết luận | T00–T08 hoàn tất hoặc có gap rõ ràng |

P0 = trực tiếp giảm bất định ba mục tiêu hoặc bảo đảm kết luận không sai. P1 = phân tích sâu có điều kiện hoặc thiết kế kiểm tra tiếp theo. T09 là P0 khi các nhánh cung cấp kết quả, không phải chạy đầu tiên.

## 4. Thứ tự thực hiện sau khi được giao nghiên cứu

1. T00 lập claim register từ tóm tắt, nhận diện input thiếu và mâu thuẫn.
2. Chạy T04 display status và T01 PCB trước để nhận diện hai tầng blocker lớn.
3. T05 kiểm DCB/VBIOS song song khi đủ công cụ offline.
4. T06 xử lý riêng2SM, không chờ nhánh display.
5. T02 lập pinmap/ảnh strap; T03 tra semantic độc lập, chỉ ghép kết quả sau để giảm thiên kiến.
6. Đánh giá sơ bộ các điều kiện phục hồi; nếu còn gap quyết định ở hardware thì không tiêu hạn mức vào quét firmware.
7. T07 chỉ chạy khi có binary đúng hash và câu hỏi caller/policy cụ thể còn ảnh hưởng verdict.
8. T08 thiết kế tối đa10 phép kiểm read-only; không tự chạy.
9. T09 kiểm phản đề, yêu cầu sửa đúng lỗi có bằng chứng, tổng hợp ba verdict.
10. Giao báo cáo và dừng. UNKNOWN có nguyên nhân là kết quả hợp lệ; không tự chuyển sang can thiệp.

Các nhánh T01–T06 dùng chung dữ liệu gốc và không sửa output nhau. Mỗi agent viết `results/Txx/`. Phụ thuộc chỉ yêu cầu artifact đầu vào; không cần giữ toàn bộ hội thoại của agent khác.

## 5. Cách tiết kiệm hạn mức

- Điều phối chỉ giữ master plan, claim register và summary tối đa10 dòng mỗi agent. Raw lớn để trong file có locator.
- Mỗi agent chỉ nhận input của nhiệm vụ; không nhét toàn ZIP vào mọi context.
- Gửi claim IDs và câu hỏi cụ thể khi phản biện. Không yêu cầu “nghiên cứu tiếp toàn bộ”.
- Hash/parse cùng artifact một lần rồi tái sử dụng; chỉ lặp khi input đổi hoặc phát hiện lỗi.
- Không quét16 ROM derivative, toàn fuse bank hoặc toàn GSP nếu không có discriminator mới.
- Tìm nguồn TU106 có mục tiêu; sau hai lượt không có nguồn đủ mạnh, ghi missing evidence và dừng nhánh.
- Chỉ một vòng sửa/đối chiếu cho mỗi nhánh, trừ khi có lỗi quan trọng hoặc nguồn mới.
- Không đặt token budget hay model ID không được xác nhận; ghi model thực dùng trong output để có thể đánh giá chi phí sau.

## 6. Chuẩn bằng chứng và phản biện

Mỗi claim phải có status VERIFIED/INFERRED/UNKNOWN/CONTRADICTED, nguồn+hash/commit, locator, thời điểm hoặc UNKNOWN, board/chip/firmware scope, phương pháp, phản đề và giới hạn.

Không coi báo cáo AI là primary. Không coi checksum đúng là nguồn xác thực; không coi nhiều bản sao hoặc hai model đồng ý là kiểm chứng độc lập. Cần kiểm lại chính byte/line/ảnh liên quan.

Các suy luận bắt buộc phản biện:

- BADF đồng nghĩa block silicon bị cắt.
- 34SM đồng nghĩa2SM không tồn tại hoặc chắc chắn mở lại được.
- 0x0004001F tự nó giải mã được thành17TPC.
- Status trong aperture fuse hoặc ổn định qua boot chứng minh OTP trực tiếp.
- Class0300 hoặc Device ID GeForce chứng minh display.
- Đầu cắm có mặt chứng minh routing/PHY tốt; DCB rỗng chứng minh không có routing.
- CAD GeForce chứng minh BOM CMP; ảnh overlay chứng minh đúng refdes.
- Địa chỉ/field615.78.08 giữ nguyên trên615.71.09.
- API headless thành công chứng minh direct scanout.

Các mục này là đối tượng kiểm chứng, không phải kết luận mới của phiên lập kế hoạch.

## 7. Phạm vi an toàn và mức rủi ro

R0: đọc tài liệu, ảnh, mã nguồn và phân tích artifact offline; chỉ tạo output nghiên cứu trong thư mục riêng.
R1: đề xuất query tương lai qua interface được tài liệu hóa, có kiểm side effect và gắn đúng thiết bị; **chưa thực hiện**.
Ngoài scope: mọi MMIO/BAR/PCI write, raw BAR read chưa có chứng cứ an toàn, /dev/mem, dump diện rộng, thử mask/fuse, flash, patch/load firmware, registry change, reset/reload/reboot, thay điện trở và đo điện trực tiếp.

Không dùng “read-only” trong tên script làm giấy phép chạy. Một số script nguồn mở resource0/mmap; chúng chỉ là tài liệu audit. Không tự cài dependencies hay dùng quyền sudo.

Không đưa đo nguội vào nhiệm vụ agent hiện tại: continuity/ohmmeter vẫn có dòng thử và cần quy trình phần cứng riêng. Có thể ghi là dữ liệu còn thiếu, không chỉ dẫn chủ sở hữu thực hiện ngay.

## 8. Nghiệm thu toàn bộ nghiên cứu tương lai

Đầu ra cuối tối thiểu:

- `FINAL_FEASIBILITY_ASSESSMENT.md`: ba câu trả lời có nguồn, điều kiện phục hồi từng tầng và giới hạn.
- `RECOVERY_DECISION_TREE.md`: DP, DVI và2SM riêng; nhánh YES có điều kiện/NO theo phạm vi/UNKNOWN.
- `CLAIM_CORRECTIONS.csv`: kết luận cũ, tác giả/file, lỗi hoặc thiếu bằng chứng, mức chắc đã sửa.
- `NEXT_READ_ONLY_TESTS.md`: thứ tự phép kiểm có khả năng thay đổi verdict, không chạy.
- Các bảng route,12 footprint, semantic strap, fuse chain, topology và VBIOS từ nhiệm vụ tương ứng.

Nghiệm thu không phụ thuộc việc tìm được cách mở khóa. Đạt khi kết luận có thể kiểm lại, mọi bước suy luận đều có nguồn hoặc nhãn UNKNOWN, và không đánh tráo cơ chế khóa thành bằng chứng phục hồi thành công.

## 9. Giao prompt

Mở [danh sách prompt](CMP40HX_RESEARCH_PLAN/PROMPT_INDEX.md), gửi nguyên nội dung file tương ứng cùng input được chỉ định cho model. Các prompt đã nhúng giới hạn an toàn và định dạng evidence; không cần chuyển toàn lịch sử trò chuyện.

**Kế hoạch dừng tại đây. Không tự khởi chạy nghiên cứu hoặc kết nối card.**


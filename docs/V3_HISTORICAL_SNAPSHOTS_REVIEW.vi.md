# Kiểm kê bổ sung các phiên bản v6–v13 (07/11/2026)

Đã đối chiếu **8 tarball, 1.035 mục tệp thực** theo SHA-256: **977 mục đã có từ V1/V2**, **15 mục trùng giữa các bản mới**, **43 nội dung mới**. Phân loại 43 nội dung mới: **16 báo cáo Markdown, 8 script, 19 tệp JSON/bằng chứng**. Không chạy script hay truy cập GPU trong quá trình đóng gói.

Các phiên bản `MASTER_REPORT.md`, `CHECKPOINT.json`, `TOOLS/verify_all.py`, `UNKNOWN_DATABASE.json` có nội dung khác nhau nên **giữ đủ phiên bản**. Chúng là ảnh chụp tiến trình nghiên cứu, không đồng nghĩa kết luận mới nhất đã đúng. Cần đọc [đính chính](CRITICAL_CORRECTIONS.md) và [kết luận cuối](FINAL_VERDICT.md) trước khi dùng các báo cáo cũ.

Bảng [V3_HISTORICAL_SOURCE_INVENTORY.csv](../manifests/V3_HISTORICAL_SOURCE_INVENTORY.csv) cho thấy 1.035 bản ghi, mỗi tệp gốc, SHA-256, trạng thái trùng, vị trí trong GitHub và kho riêng. [V3_HISTORICAL_UPLOAD_HASHES.csv](../manifests/V3_HISTORICAL_UPLOAD_HASHES.csv) ghi hash 8 gói tar nguyên bản.

**Quy tắc bảo toàn RAW:** Kho riêng chứa *nguyên byte* 8 tarball và từng tệp mới khác hash. Bản công khai giữ văn bản, script, JSON mới đã che IP nội bộ, đường dẫn người dùng, serial card và GPU PDI. Trong dữ liệu công khai, giá trị `0x0000000000000000` có thể là **placeholder PDI đã che**, không phải giá trị thực nghiệm.

Bản công khai V2 cũ còn lộ serial/PDI ở vài báo cáo; V3 đã che lại các mẫu nhận diện đã biết. Đây vẫn là **bản chờ người dùng kiểm tra thủ công**, chưa đảm bảo xử lý hết dữ liệu riêng tư, bản quyền hay script có tác động phần cứng. Không công bố kho RAW riêng trực tiếp.

Các snapshot này **không mở được TPC5**. Thử nghiệm host BAR0 về sau vẫn thất bại; cũng không chứng minh mọi cách mở khóa đều bất khả thi.

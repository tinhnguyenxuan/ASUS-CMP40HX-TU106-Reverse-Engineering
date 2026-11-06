# Kiểm kê bổ sung V4 — ảnh chụp lịch sử v4 và v5

Đã xử lý 7 tarball, gồm **618 tệp thực**: **605 bản đã có trong V3**, **2 mục trùng với nội dung mới trong lượt này**, và **11 nội dung mới độc nhất SHA-256** (**2 Markdown, 4 script Python, 5 JSON**).

Chỉ `cmp40hx_research_v4.tar.gz` và `cmp40hx_research_v5.tar.gz` cung cấp các nội dung mới. Những gói `v2 (1)`, `v3 (1)`, `v6`, `v7_final` và `research (1)` không thêm nội dung file mới, nhưng **7 tarball gốc đều được giữ nguyên byte** trong kho RAW riêng.

Nội dung có giá trị: `GSP/Q1_CONSUMER.md`, báo cáo `MASTER_REPORT.md` v4, các phiên bản `TOOLS/build_db.py`, `TOOLS/verify_all.py` và checkpoint/unknown-database JSON. Đây là chứng tích lịch sử; **không có bằng chứng mở TPC5 mới**. Con số `55/55 PASS` là tuyên bố tự kiểm tra trong bản gốc, không được chạy lại trong quá trình đóng gói.

Xem [V4_SOURCE_INVENTORY.csv](../manifests/V4_SOURCE_INVENTORY.csv) để tìm từng tệp theo hash và đường dẫn, và [V4_UPLOAD_ARCHIVES_SHA256.csv](../manifests/V4_UPLOAD_ARCHIVES_SHA256.csv) để đối chiếu tarball gốc. Trước khi sử dụng kết luận cũ, đọc [CRITICAL_CORRECTIONS.md](CRITICAL_CORRECTIONS.md) và [FINAL_VERDICT.md](FINAL_VERDICT.md).

Bản công khai đã thử lọc thông tin định danh bằng quy tắc tự động; **vẫn cần bạn rà soát thủ công** về thông tin cá nhân, bản quyền và độ an toàn của script. Không chạy script lịch sử nếu chưa hiểu tác động, đặc biệt script có thể chạm vào MMIO hoặc driver. **Không push kho RAW riêng lên GitHub.**

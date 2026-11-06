# Rà soát 10 tệp bổ sung — ngày 06/11/2026

Đợt này có **7 bản tar.gz**, **1 báo cáo Phase 15–20** và **2 tệp tên `.bin.txt` nhưng nội dung là VBIOS nhị phân**. Không chạy script và không thử ghi GPU.

Đối chiếu SHA-256: **toàn bộ 157 tệp từ v15 đã có trong bộ trước**; v14 có đúng 1 báo cáo khác byte; các snapshot còn lại bổ sung tổng cộng **36 nội dung mới** (10 Markdown, 13 Python, 13 JSON). Giữ nguyên mọi phiên bản tar gốc trong **archive riêng tư**, công khai những phần văn bản mới dưới `reports/additional/`, `scripts/additional/`, `evidence/additional/`. Xem bảng 500 bản ghi trong `manifests/SUPPLEMENTAL_SOURCE_INVENTORY.csv`.

**Không gộp các kết luận chưa đồng nhất:**

- Báo cáo VFE đầu kỳ dùng 24 byte; báo cáo 3 nhiệm vụ sửa thành stride 25 byte cho `VFE_VAR` cùng lỗi offset payload cũ.
- Phân tích IBVL ghi 15 blob 32 B ở một báo cáo và 12 digest 32 B ở báo cáo khác. Cần kiểm lại cách đếm, offset, script và phạm vi trước khi khẳng định một con số duy nhất.
- Phase 15–18 từng nói BAR3 có thể redirect tới GPU PA tùy ý, nhưng phép đo Phase 19 bác bỏ cách đọc đó trên host.
- Mô tả ROP SEC2 còn ở mức giả thuyết; không có bằng chứng exploit hoạt động trong các báo cáo này.
- Thử nghiệm root ghi `0x021040` không chứng minh thanh ghi là `EN_SW_OVERRIDE`; TPC5 vẫn chưa mở và display chưa hồi phục.

**Hai file `.bin.txt` không được đưa lên GitHub** chỉ vì có phần đuôi `.txt`: nội dung là byte VBIOS, cần xem xét quyền phân phối. Bản GitHub là **bản chờ rà soát thủ công**, không phải đã được chứng nhận không lộ dữ liệu hoặc bản quyền.

Bản chi tiết có link đến script/báo cáo: [English addendum](SOURCE_PACK_REVIEW_20261106.md).

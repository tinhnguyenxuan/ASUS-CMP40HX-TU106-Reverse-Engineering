# CMP 40HX (TU106-100-A1) — Kho nghiên cứu reverse engineering

**Dự án kết thúc ở trạng thái: chưa mở được TPC5 và chưa phục hồi xuất hình trực tiếp.** Đây là kho dữ liệu phục vụ cộng đồng, không phải công cụ mở khóa.

Hai mục tiêu của dự án là khôi phục **GPC0/TPC5 (2 SM / 128 CUDA)** và **display**. Những gì đo được: `0x021C38 = 0x20`, RM TPC masks `0x1F/0x3F/0x3F`, GR báo `5/6/6 TPC`; TPC5 trả `0xBADF1300` thuộc nhóm FECS floorsweep. Phép ghi thử cuối cùng (`0x021040 ← 1`, `0x021838 |= 0x20`) không mở được TPC5. Chưa biết TPC5 thực sự có lỗi silicon hay không.

**Đọc theo thứ tự:** [Kết luận](docs/FINAL_VERDICT.md), [bảng bằng chứng](docs/EVIDENCE_MATRIX.md), [lỗi và đính chính](docs/CRITICAL_CORRECTIONS.md), [thử nghiệm thất bại](docs/KNOWN_FAILED_APPROACHES.md), rồi tới [báo cáo raw](reports/original/) và [script gốc](scripts/original/).

Đã **giữ báo cáo cũ** để người sau truy vết vì sao có kết luận sai rồi được sửa. Bản GitHub đã khử thông tin mạng nội bộ/đường dẫn cá nhân trong các file phát hiện được và loại file cần kiểm tra bản quyền, ảnh, firmware, VBIOS, dump quá lớn. Kho **COMPLETE RESEARCH ARCHIVE** là bản **riêng tư, giữ byte gốc**, không được đẩy nguyên lên GitHub.

**Cảnh báo:** Các script gốc chưa được kiểm định an toàn và có script truy cập BAR0/MMIO, driver hoặc kernel. Đừng chạy thử trên card đang sử dụng. Chỉ công khai code khi tác giả xác nhận quyền phân phối và xem lại nội dung.

## Gói bổ sung V2

Đã đối chiếu **10 tệp mới tải lên**, chỉ **36 nội dung mới** chưa có trong kho. Xem [báo cáo tiếng Việt](docs/SOURCE_PACK_REVIEW_20261106.vi.md) và [bảng ánh xạ 500 mục](manifests/SUPPLEMENTAL_SOURCE_INVENTORY.csv). Các bản tar nguyên gốc và byte VBIOS giữ trong gói riêng tư.

## V3: bo sung lich su v6-v13

Them **43 noi dung goc moi** tu 8 tarball, giu lai cac bao cao/script phien ban cu va bang doi chieu 1.035 tep. Xem [kiem ke tieng Viet](docs/V3_HISTORICAL_SNAPSHOTS_REVIEW.vi.md). Ban GitHub da che serial va GPU PDI cua card trong cac tep van ban; ban RAW rieng giu nguyen. **Can kiem tra thu cong truoc khi public.**

## V4: bo sung phien ban nghien cuu v4-v5

Them **11 noi dung khac SHA-256** tu 7 tarball moi. Xem [bao cao V4 tieng Viet](docs/V4_ADDITIONAL_SOURCE_REVIEW.vi.md) va [danh muc tung tep](manifests/V4_SOURCE_INVENTORY.csv). Kho RAW rieng giu nguyen tat ca 7 tarball goc; khong dua kho RAW rieng len GitHub.

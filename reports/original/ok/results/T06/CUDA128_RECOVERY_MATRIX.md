# T06 — MA TRẬN KHẢ NĂNG PHỤC HỒI 128 CUDA (2 SM)

Phạm vi: chỉ chênh 1 TPC/2 SM/128 core + pipeline phụ thuộc (FECS dispatch, ROP/L2 không xét). KHÔNG nghiên cứu tăng hiệu năng, KHÔNG thử unlock/benchmark (R0).

## Ma trận kịch bản

| # | Kịch bản nguồn disable | Bằng chứng ủng hộ | Bằng chứng chống | Có thể phục hồi 2 SM? | Phép phân biệt (read-only nếu có) |
|---|---|---|---|---|---|
| S1 | **Policy-only**: TPC18 khỏe, bị floorsweep chủ ý (OTP DISABLE hoặc tương đương), không DEFECTIVE | Gia đình TU106 trải 30/34/36 SM qua SKU ⇒ binning là thực hành chuẩn (INFERRED); GA100 chứng minh DISABLE ≠ DEFECTIVE là 2 fuse riêng | Trên TU106 chưa tìm thấy register DEFECTIVE/DISABLE được đặt tên ⇒ cũng không chứng minh S1 | **Ứng viên phục hồi về nguyên lý**: cơ chế _CP shadow + EN_SW_OVERRIDE đã hoạt động trên CMP 170HX/GA100 (lixiangwuxian/170hx_tips); cần PLM cho phép | Đọc OPT_*_DEFECTIVE nếu Turing có (không public); dump fuse die 2070/2060S đối chứng; phân tích GSP blob đã giải mã tìm handler STATUS_OPT |
| S2 | **OTP đã burn nhưng có SW override bị khóa PLM** | PLM-mask 0xFFFFFF8F xuất hiện 5× trong dump (khớp RESET_PLM/PLM_FECS dmesg); mẫu này giống FUSE_DEBUGCTRL_PLM bị khóa L3 trên AD10x consumer (gpu-unlock-ada issue #109) | Mẫu 0xFFFFFF8F trong dump nằm ở offset 0xD8-0xF4 — không khẳng định là FUSE_DEBUGCTRL_PLM (offset GA100/AD10x ≠ TU106 chưa chứng minh) | Nếu chinh phục được PLM thì S2 ≡ S1; nếu không thì bị chặn vĩnh viễn ở runtime | So offset 0xD8..0xF4 với bảng FUSECTRL TU106 khi có; thử qua FUSECTRL tương tự RIR — bằng cách nào đó read-only không phân biệt được |
| S3 | **Firmware/software mask chồng lên fuse** (GSP feature-gate) | RMDISABLEFEATUREDISABLEMENT chứng minh GSP consumer có bảng feature-gate 10 entry đọc từ fuse registers; CMP là SKU có thể thêm tầng | Tầng này gate tính năng (display/P2P), chưa thấy nó gate TPC/SM count | Có thể phục hồi nếu chỉ là tầng firmware (RMDisableFeatureDisablement tương tự), nhưng chưa có chứng cứ nó áp cho compute units | So sánh config struct GSP (offset 0x50fc/0x5100 bitmask) giữa card 34-SM và 36-SM |
| S4 | **Binning-defect**: TPC18 hỏng vật lý (DEFECTIVE-fused) | BADF1300 ở mọi tầng truy vấn (nhưng xem S5) | Không có bằng chứng trực tiếp | **Không phục hồi được** bằng bất kỳ override nào | Cần register DEFECTIVE tương đương GA100 — không public cho TU106 ⇒ **giới hạn không thể phân biệt bằng read-only hiện có** |
| S5 | **Không có transistor**: die harvest thật (mask silicon khác) hoặc TPC18 ngoài aperture decode | PGRAPH poison toàn 16 MB chứng minh BADF có thể chỉ là "ngoài cửa sổ decode" — bác bỏ logic "BADF ⇒ không tồn tại" | — | Không phục hồi được (không có gì để bật) | Bản đồ aperture 16 MB BAR0 từng 64 KB (TU-06, read-only): nếu một aperture riêng lẻ trả data cho vùng TPC18 thì loại trừ S5 dưới dạng decode; transistor thật sự chỉ die-shot phân biệt được |

## Điều kiện kết luận (theo yêu cầu nhiệm vụ)

- **Policy-only là ứng viên phục hồi duy nhất** (S1/S2/S3 — cả ba đều cần đường ghi/override mà card này chưa chứng minh được).
- **Cản trở tuyệt đối** nếu: OTP không override được (S2 bị PLM khóa vĩnh viễn), hoặc S4/S5 (defect bắt buộc / thiếu transistor).
- **Không được phép tuyên bố**: "TPC18 có/khỏe/chết" từ phân tích mask. Phân tích mask chỉ xác định *ai đọc gì để ra 34*, không xác định *vì sao*.
- **Không xác nhận sức khỏe đơn vị chưa từng chạy** bằng phân tích mask — nguyên tắc này áp cả khi S1 nhiều khả năng nhất.

## Trạng thái dữ liệu thiếu để phân biệt S1 vs S4 vs S5

1. Dump fuse từ TU106 2070 (36 SM) và 2060S (34 SM) — so 0x650/0xC1C/0x524/0x650-neighborhood → giải mã bitfield bằng thực nghiệm thay vì number-match.
2. Bản đồ aperture BAR0 16 MB (TU-06) — loại trừ S5 dạng decode.
3. Header `dev_fuse.h` đầy đủ cho tu102/tu106 — NVIDIA chưa công bố; gpcprobe chỉ chứng minh schema GA100.
4. GSP-RM blob đã giải mã — tìm hàm đọc fuse và dựng topology GR.

**Không tự thu dump mới** (R0) — các mục trên là việc cho phiên sau, không phải việc T06.

## Tool versions / hashes

Python 3.14.9; coreutils 9.4; phân tích offline 2026-11-05T03:49:50+07:00. Nguồn web (truy cập 2026-11-05, branch main của NVIDIA/open-gpu-kernel-modules — commit không chốt, chỉ raw path): dev_fuse.h tu102; gpcprobe README (matstatman); 170hx_tips Gen3_unlock_en.md (lixiangwuxian); rtx-p2p RMDISABLEFEATUREDISABLEMENT.md (kacper-daftcode); gpu-unlock-ada issue #109. Input hashes xem evidence.json.

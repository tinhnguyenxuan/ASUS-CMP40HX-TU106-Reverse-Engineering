# Bổ sung Phase 1–5 cho gói V5 (chỉ các file mới hoặc đổi)

- Đây là gói **tăng dần so với repository V5 đã gửi trước**, không phải một bản chép lại V4/V5.
- `research/vbios_phase1_3/`: 3 tài liệu VBIOS historical từ `vbiosre.zip`, `vbiosrel2.zip`, `vbiosrel3.zip` và README hướng dẫn đọc theo tiến trình sửa lỗi.
- `research/vbios_phase4_6/docs/`: thêm trích đoạn master Phase 4 và Phase 5 chỉ về reverse ROM (các tài liệu khác đã có trong V5 trước).
- `docs/TU106_VBIOS_PHASE1_5_HISTORY.md`: đối chiếu xuyên Phase 1–6, sửa cách đọc những tuyên bố đã bị phiên bản sau hạ mức.
- `manifests/VBIOS_PHASE1_5_ADDON_SOURCES.csv`: provenance file, ZIP, SHA-256 bản thô và bản tuyển chọn.
- Chỉnh liên kết trong README, timeline và cập nhật checksum toàn repository.

**Loại khỏi gói:** test game, FPS/frametime, telemetry Windows/Linux, collectors, benchmark, ROM/binary và bất kỳ file V4/V5 không thay đổi. Không sửa hoặc xóa dữ liệu lịch sử V4/V5.

**Xác minh:** so sánh SHA-256 của từng thành viên V5 và delta, ZIP testzip, kiểm tra không có ROM/binary, không đóng gói file cũ byte-identical. Không thực hiện kiểm thử trên GPU thật hoặc kiểm chứng lại kết luận ROM.

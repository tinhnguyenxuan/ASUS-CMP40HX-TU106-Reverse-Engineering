# Lịch sử reverse VBIOS CMP 40HX (TU106) — Phase 1 đến Phase 5

**Phạm vi:** trích xuất và ghép các tài liệu ROM tĩnh từ những gói do người dùng cung cấp: `vbiosre.zip`, `vbiosrel2.zip`, `vbiosrel3.zip`, `vbiosrel4.zip`, `vbiosrel5.zip` và đối chiếu với kết quả Phase 6 đã được bổ sung trong V5. Không đo game, không chạy GPU thật, không flash ROM.

## Mốc kỹ thuật và cách đọc

| Phase | Nội dung nằm trong tài liệu nguồn | Đọc thêm |
|---|---|---|
| **1** | Lập bản đồ ROM, BIT, Performance P2, Power Base Clock, Memory Clock/Tweak, DCB và các trường chưa biết. Một số định danh trong bản đầu **được sửa về sau**. | [Phân tích lịch sử Phase 1](../research/vbios_phase1_3/docs/PHASE1_FIELD_REVERSE_HISTORICAL.md) |
| **2** | Đối chiếu schema `PERFORMANCE v0x60`, nhận diện 10 clock domains, sửa cách đọc DCB và đánh giá lại các byte 27 MHz HUB/DISP. | [Phase 2](../research/vbios_phase1_3/docs/PHASE2_FIELD_REVERSE_HISTORICAL.md) |
| **3** | Sửa ba lỗi exporter: BIT `P` version, P2 directory pointer và cách trình bày memory timing bitfield; phân biệt `pcie_idx` với tốc độ link thật. | [Phase 3](../research/vbios_phase1_3/docs/PHASE3_FIELD_REVERSE_HISTORICAL.md) |
| **4** | Mở rộng đối chiếu Power/Thermal, PCIe và ROM multi-image; đưa ra các UNKNOWN thay vì suy từ một byte sang runtime. | [Phase 4 — ROM extract](../research/vbios_phase4_6/docs/PHASE4_MASTER_ROM_EXTRACT.md) |
| **5** | Chỉnh 6 lỗi, giải mã thêm VFE (v0x30), làm rõ bit sai khác của LOW POWER GR và giới hạn suy luận firmware/driver. | [Phase 5 — ROM extract](../research/vbios_phase4_6/docs/PHASE5_MASTER_ROM_EXTRACT.md) |
| **6** | Truy chuỗi `P-state.lpwr_entry_idx` → LOW POWER index slot 29 → `pcie_idx` → PCIe slot 30. | [Phase 6 — index chain](../research/vbios_phase4_6/docs/PHASE6_PCIE_INDEX_CHAIN.md) |

## Đính chính quan trọng khi đối chiếu lịch sử

1. **Phase 1 không phải schema cuối cùng.** Trình tự suy luận offset, định danh domain và bằng chứng power/clock đã được chỉnh ở Phase 2 và 3. Không trích khẳng định Phase 1 riêng lẻ như kết luận cuối.
2. **Phase 3 `PCIEGEN` không chứng minh đường truyền PCIe runtime.** Các byte và tên trường giả định phải tách khỏi kết quả link negotiation thật. Phase 6 chỉ chứng minh chuỗi tham chiếu bảng, không giải mã được ý nghĩa của payload PCIe.
3. **Các tuyên bố về RT/Tensor, SM/TPC, display unlock** không thể kết luận chỉ bằng sự có mặt/vắng mặt của field VBIOS. Những phần đó thuộc báo cáo phần cứng/driver riêng và cần bằng chứng độc lập.
4. **VFE, LOW POWER GR, power/thermal** trong Phase 4–5 có các cập nhật và giới hạn được ghi tại [báo cáo Phase 4–6](TU106_VBIOS_PHASE4_6.md). Những phần chưa biết phải giữ nguyên là *UNKNOWN/INSUFFICIENT*.
5. **Bản tuyển chọn không phải xác minh lại giá trị ROM.** Parser/test offline được lưu ở [`research/vbios_phase4_6`](../research/vbios_phase4_6/README.md); các ROM gốc không đi cùng gói xuất bản.

## Cách lựa chọn file để tránh trùng và tránh game benchmark

- Phase 1–3: giữ ba tài liệu **VBIOS_FIELD_REVERSE_ENGINEERING** tương ứng lịch sử, không đưa ba bản của parser, export CSV và nguồn tham chiếu lặp lại (bản mới đã nằm trong V5).
- Phase 4–5: giữ trích đoạn **master report** liên quan ROM, VFE, LOW POWER, driver/firmware và giới hạn bằng chứng. Các tài liệu chi tiết khác đã nằm trong [`vbios_phase4_6`](../research/vbios_phase4_6/README.md) từ lần bổ sung trước.
- Loại tài liệu/kịch bản đo FPS, chạy game, Direct3D/CUDA benchmark, Windows collector/PresentMon/WPR, GPU telemetry, mã nhị phân, VBIOS ROM và đường dẫn cá nhân.
- Các bản ZIP `vbiosrel6(1).zip` và `vbiosrel6(2).zip` có nội dung file đồng nhất trong dữ liệu được cung cấp. Phase 6 **không chép lần nữa** vì V5 đã có.

Nguồn theo file và hash: [VBIOS_PHASE1_5_ADDON_SOURCES.csv](../manifests/VBIOS_PHASE1_5_ADDON_SOURCES.csv). Trước khi công khai cần duyệt quyền sử dụng nội dung và các giả thuyết còn tranh cãi.

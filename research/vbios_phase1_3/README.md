# TU106 VBIOS — Phase 1–3 (historical snapshots)

Kho tư liệu chỉ phục vụ **reverse cấu trúc VBIOS**. Ba bản trong `docs/` là các phiên bản **lịch sử**, được trích từ `vbiosre.zip`, `vbiosrel2.zip`, `vbiosrel3.zip`, và không phải ba kết luận đồng thời đúng.

- [Phase 1 — phân tích bảng BIT, Performance, Memory, DCB](docs/PHASE1_FIELD_REVERSE_HISTORICAL.md)
- [Phase 2 — sửa định danh clock domains, P-State v0x60 và DCB](docs/PHASE2_FIELD_REVERSE_HISTORICAL.md)
- [Phase 3 — sửa exporter, làm rõ PCIe `pcie_idx`, HUB/DISP](docs/PHASE3_FIELD_REVERSE_HISTORICAL.md)
- [Đối chiếu Phase 1–6 và các đính chính](../../docs/TU106_VBIOS_PHASE1_5_HISTORY.md)

**Ưu tiên sử dụng parser mới nhất ở [`../vbios_phase4_6/scripts/`](../vbios_phase4_6/scripts/)** thay vì script lịch sử; không đưa lại code và các CSV đã có để tránh trùng lặp. Các tài liệu có giá trị truy vết quá trình sửa lỗi, không chứng minh khác biệt runtime/driver/GSP, tốc độ PCIe, hiệu năng game hay khả năng mở khóa SM/display.

Không bao gồm ROM, nhị phân, firmware, telemetry, collector, benchmark hoặc hướng dẫn chạy game.

Danh tính nguồn và SHA-256: [manifest](../../manifests/VBIOS_PHASE1_5_ADDON_SOURCES.csv).

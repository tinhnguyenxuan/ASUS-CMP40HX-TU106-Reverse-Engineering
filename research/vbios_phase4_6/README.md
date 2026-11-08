# TU106 VBIOS structural research — Phase 4–6 (curated)

**Tách từ gói nghiên cứu `vbiosrel6(2).zip` để ghép vào kho CMP40HX-TU106-Reverse-Engineering V4.** Đây là bộ phân tích **ROM tĩnh** (không phải công cụ benchmark/game). Bản công khai không chứa ROM, firmware NVIDIA, dump thiết bị, game log hay công cụ thu telemetry Windows/Linux.

**Bắt đầu:** [Báo cáo tổng hợp tiếng Việt](../../docs/TU106_VBIOS_PHASE4_6.md) · [Phase 6 chain](docs/PHASE6_PCIE_INDEX_CHAIN.md) · [Field reverse](docs/VBIOS_FIELD_REVERSE_ENGINEERING.md) · [Unknown fields](data/TU106_UNKNOWN_FIELDS.csv).

## Nội dung

- `docs/`: tài liệu phân tích được tuyển chọn: PCIR/BIT/P2, clocks, power/thermal, voltage/VFE, memory, LPWR GR/PCIe, firmware/driver. Một số mục chỉ chuyên về test runtime đã được lược bỏ; tài liệu còn giữ các **giả thuyết UNKNOWN**.
- `data/TU106_DECODED_FIELDS.csv`: bảng xuất 5.621 dòng dữ liệu theo nguồn, **không tái tạo từ ROM trong lần đóng gói này**.
- `data/TU106_UNKNOWN_FIELDS.csv`: bảng những trường chưa giải mã.
- `data/PHASE4_FIELD_EVIDENCE.csv`: bảng bằng chứng đã bỏ các hàng tập trung vào game/benchmark. Không coi nội dung đó là kết quả kiểm chứng độc lập.
- `scripts/tu106_vbios.py`, `scripts/export_fields.py`, `scripts/phase4/multi_rom_diff.py`: parser và xuất diff ROM **chỉ đọc**.
- `scripts/test_tu106_vbios.py`: regression test trên **3 ROM do người dùng tự cung cấp**, không phải bài test game.
- `scripts/phase4/evidence.py`: tạo lại bảng evidence được tuyển chọn.
- `SOURCE_MANIFEST.csv`: dấu vết nguồn và SHA-256 của từng file đầu vào.

## Sử dụng offline (chỉ khi có quyền sử dụng ROM)

```bash
# Các ROM lưu tại ./roms/ (Git ignore, KHÔNG commit)
python scripts/test_tu106_vbios.py ./roms
python scripts/export_fields.py ./roms ./data
python scripts/phase4/multi_rom_diff.py ./roms/TU106.rom ./roms/219827.rom ./roms/265590.rom -o ./data/semantic_diff.csv
```

Mã được giữ từ nguồn có thể phụ thuộc phiên bản Python/API và cần test thực tế với ROM tương ứng. Công cụ chỉ đọc ROM nhưng exporter ghi các CSV đích (nên tránh ghi đè dữ liệu đã công bố nếu cần so sánh).

## Giới hạn và xuất bản

- Không có ROM nào trong repository; các kết luận từ ROM là **reported analysis** đến khi được kiểm tra lại trên ROM có nguồn rõ.
- Không xác nhận một cách mở khóa TPC/SM, xuất hình vật lý, khả năng RT/Tensor hay giới hạn PCIe thật.
- Không chạy bất kỳ benchmark/game, collector hoặc thiết bị GPU nào để tạo bản này.
- Quyền công bố code/dữ liệu vẫn cần chủ sở hữu xác nhận; tài liệu gốc của nhiều nguồn ngoài chỉ được dẫn chiếu, không được nhúng lại.

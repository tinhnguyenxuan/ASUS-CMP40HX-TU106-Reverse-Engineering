# Bổ sung nghiên cứu VBIOS TU106 — Phase 4–6 (bản công khai, chỉ phân tích tĩnh)

**Nguồn:** `vbiosrel6(2).zip` do chủ dự án cung cấp. Tài liệu này tổng hợp các kết quả báo cáo trong gói và đối chiếu các đính chính ở Phase 5/6, **không** tuyên bố mới đo phần cứng hay benchmark. Đây là nhánh phân tích **VBIOS**, bổ sung — không thay thế — hồ sơ TPC5/floorsweep và Display trong [kết luận V4](FINAL_VERDICT.md).

**Mở tài liệu gốc đã tuyển chọn:** [research/vbios_phase4_6](../research/vbios_phase4_6/README.md).

## 1. Đối tượng và phương pháp

Ba VBIOS được so sánh theo tài liệu nguồn: **CMP 40HX `10DE:1F0B`**, **RTX 2060 SUPER `10DE:1F06`**, **RTX 2070 `10DE:1F07`**. Parser đọc cấu trúc ROM (PCIR image chain → BIT tokens → P2 directory → bảng con); **không** dựa trên raw binary diff đơn thuần. Hai loại offset được tách rõ: `file_offset` (vị trí bản ghi/con trỏ) và `target_offset` (đích con trỏ), tránh lỗi đã ghi trong source v2. 5.621 dòng decoded fields và unknown-field matrix nằm trong [data](../research/vbios_phase4_6/data/).

**Mức bằng chứng:** `PROVEN` (địa chỉ/byte/layout được đối chiếu), `STRONGLY SUPPORTED` (giải thích có nguồn nhưng chưa có consumer), `HYPOTHESIS`, `UNKNOWN`. Các nhãn này phản ánh báo cáo nguồn, không đồng nghĩa kiểm chứng độc lập trên firmware/hardware của lần phát hành GitHub.

## 2. Các phát hiện cấu trúc chính (theo nguồn)

| Thành phần | Giá trị/quan hệ báo cáo | Giới hạn kết luận |
|---|---|---|
| PCI class / display | CMP class `0x030200` (3D controller), GeForce `0x030000` (VGA); BIT `U` display-script ptr bằng 0 ở CMP | Chưa chứng minh có thể khôi phục display engine/hardware |
| P-State v0x60 | CMP không có P-state `0x0A`/`0x0D` như GeForce so sánh | Không phải chứng minh clock runtime thấp hơn |
| Power Budget slot 11 | CMP min/rated/max `110/184/220 W`; RTX 2060 SUPER `125/184/220 W`; RTX 2070 `125/185/222 W` | Là **giá trị bảng ROM**, không phải power cap hay throttle đo thực tế |
| Power Topology slot 15 | Cấu trúc khớp `6 + 20×22 + 15×27 = 851` byte; nguồn báo giống CMP và RTX 2060S | Bảng sensor/topology không chứng minh policy bằng nhau |
| Thermal Policy slot 20 | `10 + 4×40 = 170` byte; byte header CMP khác GeForce | Ý nghĩa field header còn UNKNOWN |
| LOW POWER GR slot 32 | `10 + 5×5 = 35` byte; delta bit trong entry 0 là **bit 3** (`XOR 0x8`), **không phải bit 27** | Ý nghĩa bit 3/consumer vẫn UNKNOWN |
| VFE v0x30 | 20 variables, 150 equations; extent 5.444 byte có các khối RPPM; nguồn báo CMP/2060S trùng trong vùng này | RPPM payload và cách RM sử dụng chưa giải mã đầy đủ |
| PCIe init script | CMP `0x0088610 = 0x1`, GeForce `0x1001`; condition id `86` vs `82` | Không có bằng chứng gọi bit 12 là công tắc Gen3 |
| LOW POWER PCIe slot 30 | Bảng 5 entry × 12 byte; CMP `0xFB` vs GeForce `0xF8` tại byte thứ 8 theo nguồn | Payload chưa có public schema; không thể suy ra speed/width |
| P-state → LPWR → PCIe | Phase 6 mô tả chuỗi `lpwr_entry_idx` → slot 29 → `pcie_idx` → slot 30, nhất quán 10/10 đường trên 3 ROM | Đây là **liên kết chỉ số trong ROM**; driver/GSP consumer chưa xác minh |

Nguồn chi tiết: [Field reverse engineering](../research/vbios_phase4_6/docs/VBIOS_FIELD_REVERSE_ENGINEERING.md), [Power/Thermal](../research/vbios_phase4_6/docs/TU106_POWER_THERMAL_REVERSE.md), [VFE](../research/vbios_phase4_6/docs/VFE_VOLTAGE_DEEP_REVERSE.md), [LOW POWER GR](../research/vbios_phase4_6/docs/LOW_POWER_GR_RESEARCH.md), [Phase 6 LPWR chain](../research/vbios_phase4_6/docs/PHASE6_PCIE_INDEX_CHAIN.md).

## 3. Đính chính bắt buộc khi đọc theo phase

1. **LOW POWER GR:** tài liệu sớm nhầm bit 27 do vị trí byte; kiểm tra số little-endian khẳng định **bit 3** là phần chênh lệch, chức năng bit chưa biết.
2. **VFE:** suy luận từ vùng không đầy đủ từng không đóng extent; phân tích sau bổ sung RPPM và đóng extent nhưng **không** suy ra VFE runtime policy.
3. **PCIe `pcie_idx`:** Phase 4/5 chưa nhận ra đường liên kết LPWR; Phase 6 truy chuỗi index trong ROM. Điều này **không** giải mã payload `LOW POWER PCIe` hoặc giải thích link speed thực tế.
4. **Power limit:** `184 W` trong bảng không chứng minh CMP bị/không bị giới hạn công suất thực lúc chạy. Giá trị table tương đồng chỉ giới hạn suy luận *từ ROM*.
5. **Feature gating:** không tìm thấy một field RT/Tensor hoặc GPC/TPC rõ ràng trong các bảng khảo sát **không** chứng minh các engine hoạt động hoàn toàn hoặc có thể mở khóa.

## 4. Còn UNKNOWN / cần thêm bằng chứng

- Register definition/consumer của `0x0088610`, meaning condition 82/86 và 12-byte LPWR PCIe payload.
- Cơ chế driver/GSP-RM áp chính sách lên các byte ROM; không được coi việc không thấy nhánh trong source mở là bằng chứng phủ định policy mã đóng.
- Ý nghĩa bit 3 LPWR GR; RPPM/VFE full schema; trường mở rộng Power Budget/Thermal Policy; memory strap đang hoạt động.
- Sự tồn tại và trạng thái hữu dụng của TPC5, display engine hoặc RT/Tensor từ phân tích VBIOS đơn lẻ.

Xem [unknown fields](../research/vbios_phase4_6/data/TU106_UNKNOWN_FIELDS.csv) và [evidence matrix V4](EVIDENCE_MATRIX.md). Các nhận định cũ trong các báo cáo lưu trữ lịch sử vẫn phải đọc kèm [corrections V4](CRITICAL_CORRECTIONS.md).

## 5. Phạm vi loại khỏi bản GitHub này

**Theo yêu cầu, không gộp** script PowerShell thu GPU, trace/WPR/PresentMon, CUDA/D3D12 benchmark, test game thực tế, bảng kế hoạch đo FPS/frametime, runbook Windows, hay telemetry cá nhân. Trường hợp kiểm tra parser bằng ROM được giữ vì đó là **unit/regression test offline**, không chạy trò chơi hoặc đo hiệu năng GPU. Dữ liệu CSV đã công bố là kết quả phân tích **ROM theo nguồn** và không chứa ROM gốc.

**Trạng thái xác minh bản bổ sung:** kiểm tra file, cấu trúc và mã nguồn tĩnh khi đóng gói; **không** chạy test trên ROM, không flash/patch, không chạy bất kỳ benchmark hay GPU thực nào.

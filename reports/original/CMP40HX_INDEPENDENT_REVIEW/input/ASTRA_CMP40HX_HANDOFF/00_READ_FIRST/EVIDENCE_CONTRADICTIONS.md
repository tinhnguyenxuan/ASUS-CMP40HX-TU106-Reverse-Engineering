# Bảng bằng chứng, độ chắc và mâu thuẫn

| Mệnh đề | Nguồn | Tình trạng | Cần làm rõ |
|---|---|---|---|
| PCB CG161P REV 2.00, chip CMP40HX-8G | Ảnh PCB thật | Quan sát hình ảnh | Xác thực nhãn trên chip nếu cần |
| Có 6 net STRAP0..5, 12 footprint lên 1V8_AON / xuống GND | GenCAD CG161P R2 | **Đã xác minh NETLIST** | Mức logic khi reset trên card CMP |
| STRAP3 = G1/BM5; R258 ↑, R261 ↓ | GenCAD, report Word | **Đã xác minh NETLIST** | R258/R261 trên CMP đang lắp ra sao? |
| R258/R249/R250 DNP; R261/R264/R265 lắp | Ảnh và overlay trước đó | **Dự đoán từ ảnh** | Ảnh macro nét, đọc silkscreen, đo trở nguội; tránh nhầm tọa độ |
| STRAP5:3 ≈000 | Từ dự đoán resistor | **Suy luận** | Read-only PSTRAPS effective và đo điện trở |
| STRAP3 chọn 0302↔0300 trên TU106 | Envytools/G80+ và sơ đồ N18E khác bo | **Chưa kiểm chứng** | Đúng biến thể Turing, định nghĩa bit/latch, PCI class cùng thời điểm |
| PCI class báo 0302; Device ID 1F0B | v15 PCIE/pcie_map.json | **Historical saved observation** | Bản đọc live BDF+timestamp |
| Raw display fuse/status `0x21C04=1` | v15 `FUSE/fuse2.json`, `regs["3076"]` | **Dữ liệu raw có lưu** | Ý nghĩa physical OTP vs shadow; live reading |
| Một báo cáo sớm ghi `0x21C04=0` | `BAO_CAO_DAY_DU.md` | **Mâu thuẫn** | Kiểm tra script, version, timestamp, endian/offset |
| NVIDIA `DATA_ENABLE=0` tại bit0 của `0x21C04` | Host driver headers/Phase21 | **Code-derived bit semantics** | Kiểm tra exact driver tag, source path/caller |
| PDISP/SOR/DAC trả `0xBADF1301` | Hermes saved display probe | **Observation tại thời điểm đo** | Clock/power/reset/PCI aperture/PLM vs fuse physical |
| DRM không có connector | Phase21 runtime | **Observation firmware/driver** | Vì DCB, fuse, policy hay thiếu board wiring? |
| J1 DP và J5 DVI có cổng, J10 HDMI thiếu | 18 ảnh CMP | **Quan sát hình ảnh** | Continuity GPU→C→J, AUX/HPD/DDC, status PHY |
| ROM CMP DCB connector entries=0 | Codex Phase21 decoder | **Dữ liệu trích parser** | Kiểm tra parser/version và đối chiếu ROM GeForce độc lập |
| CMP 17 TPC / 34 SM = 2176 cores | Runtime/topology saved | **Phần logic đã đo** | TPC mask: physical fuse vs runtime mask |
| TU106 đầy đủ 18 TPC / 36 SM | Turing architecture | **Reference architecture** | Không bảo đảm đơn vị thứ 18 hoạt động tốt trên CMP |
| `fuse+0x650=0x0004001F` | Hermes saved dump | **Có số thô** | Bitfield TU106 và tương quan topology chưa giải nghĩa chắc chắn |
| TPC thứ 18 'bị cắt silicon' | Hermes BAO_CAO_DAY_DU suy BADF | **Không được chứng minh** | Hard-fuse/floor-sweep/circuit physically cut/defect |

### Quy tắc đọc báo cáo cũ
- `BAO_CAO_DAY_DU.md` là nguồn thứ cấp có các kết luận quá chắc; giữ để kiểm chứng phản biện, không coi là fact.
- `CMP40HX_PHOTO_VS_CG161P_PHASE_REPORT.md` đã gán các vị trí SMD từ ảnh, nên yêu cầu Astra **xem lại ảnh**, không chỉ lặp lại.
- `CMP40HX_Strap_Report.docx` dựa trên **CAD GeForce**, không có BOM phiên CMP.
- Phase21 tìm các địa chỉ worker/consumer của **firmware 615.78.08**; địa chỉ không mặc nhiên hợp lệ cho 615.71.09.

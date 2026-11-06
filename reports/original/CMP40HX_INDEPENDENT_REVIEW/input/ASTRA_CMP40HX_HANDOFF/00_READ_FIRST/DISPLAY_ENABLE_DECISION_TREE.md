# DISPLAY CÓ BẬT LẠI ĐƯỢC KHÔNG? — KHUNG QUYẾT ĐỊNH CẦN GPT-6 ASTRA KIỂM TRA

## Kết luận hiện có
**CHƯA CÓ BẰNG CHỨNG DISPLAY ĐÃ ĐƯỢC BẬT LẠI / XUẤT TÍN HIỆU QUA DP HOẶC DVI.** Đây là một mục tiêu đang điều tra, không phải kết luận không thể. Ảnh cho thấy J1 DP và J5 DVI có cổng; GenCAD GeForce cho thấy thiết kế display routing; raw fuse-status v15 `0x21C04=1`, host header NVIDIA định nghĩa enable=0; VBIOS CMP đã được giải mã có DCB không có connector entries. Những yếu tố này có thể chặn đồng thời.

| Phân loại giả thuyết | Bằng chứng đang có | Mức suy luận hiện tại | Điều cần xác định trước khi kết luận có thể bật |
|---|---|---|---|
| OTP/eFuse hard-disabled display trên die | `NV_FUSE_STATUS_OPT_DISPLAY=1` trong dump v15, host predicate false | **Không đủ để xác nhận OTP vật lý** | Nguồn vật lý của status, cơ chế latch/override và TU106 exact code path |
| Firmware/GSP/host policy disabled | Phase21 `RmDisableDisplay`, GSP object +0x334, host gpuFuseSupportsDisplay path | **Có code path**, chưa xác minh nguyên nhân duy nhất | Caller/consumer thực, trạng thái effective runtime, firmware đúng tag |
| VBIOS không có cấu hình connector | 16 ROM variants có DCB connector entries=0 theo parser | **Có bằng chứng ROM thiếu metadata** | DCB parse correctness; ROM reference thật; ảnh hưởng đến firmware init |
| PCB không có đường tín hiệu hoạt động | J1 DP & J5 DVI nhìn thấy; J10 HDMI footprint; đường IFP trong CAD GeForce | **Chưa chứng minh toàn bộ continuity CMP** | AC coupling, HPD/AUX/DDC, reference grounds/ESD/power trên CMP thật |
| Chỉ do STRAP3 chọn PCI class 0302 | R258/R261 nối STRAP3 trên CAD; nhóm STRAP[5:3] dự đoán 000 | **Chưa có mapping TU106 xác thực** | Latch đọc được, PCI class hiện tại và bảng strap TU106; không nhầm class với display enable |

## Quy tắc kết luận
- **CÓ THỂ BẬT BẰNG PHẦN MỀM**: chỉ kết luận khi hardware/các đường output được xác nhận và có cơ chế policy được chứng minh là nguyên nhân đủ, kèm thử nghiệm chức năng được phê duyệt. Chưa đạt ngưỡng đó.
- **CÓ THỂ BẬT SAU KHI BỔ SUNG LINH KIỆN**: cần chứng minh các chân package/routes còn, bộ PHY/controller khả dụng và danh sách BOM/net bị thiếu; hiện chưa đạt.
- **KHÔNG THỂ KHÔI PHỤC**: cần bằng chứng cứng rằng khối chức năng cần thiết thực sự vắng mặt hoặc bị vô hiệu hóa không thể đảo ngược; hiện chưa có đủ bằng chứng.
- **CHƯA XÁC ĐỊNH**: trạng thái đúng với tập dữ liệu hiện tại; tiếp tục bằng phân tích offline/read-only và đo bo nguội, không tự kích hoạt bằng các phép ghi thử.

Phân biệt ba endpoint: (1) PCI class đổi thành 0300, (2) driver tạo DRM/KMS connector, (3) tín hiệu vật lý DP/DVI có thể được màn hình nhận và hiển thị ổn định. Chỉ (3) là bằng chứng mạnh về xuất hình trực tiếp.

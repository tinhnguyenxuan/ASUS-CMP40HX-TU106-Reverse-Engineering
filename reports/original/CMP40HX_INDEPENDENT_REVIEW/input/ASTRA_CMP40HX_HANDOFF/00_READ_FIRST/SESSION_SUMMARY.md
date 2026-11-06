# Tóm tắt phiên nghiên cứu — đủ để GPT-6 Astra tiếp quản (một phiên)

## 1. Thiết bị và câu hỏi thực sự

Người dùng sở hữu GPU mining NVIDIA CMP 40HX 8 GiB, báo cáo nhận diện là TU106-100-A1, PCI vendor/device `10de:1f0b`, ASUS subsystem `1043:8804`, PCB có ký hiệu `CG161P REV 2.00`, VBIOS `90.06.67.00.06`. Thiết kế tham chiếu ở đây là **ASUS DUAL-RTX2060S-O8G-EVO-V2 CG161P R2** (file GenCAD đã gửi). Đừng nhầm thiết kế board GeForce này với BOM/mức logic/fuse của chính bản CMP.

**Ba câu hỏi cần được giải quyết (ưu tiên gần ngang nhau):**

**(Q1) 128 CUDA cores:** TU106 full/RTX 2070 có 36 SM = 2304 cores, CMP 40HX có 34 SM = 2176 cores. Khoảng chênh là **2 SM = 1 TPC = 128 cores**. Số SM được phần mềm báo không nói lên transistor của TPC thứ 18 có bị cắt hay hư hay bị vô hiệu hóa bằng eFuse/floorsweeping. So sánh thêm RTX 2060 SUPER (cũng 34 SM/17 TPC) nhưng không suy ra loại die hoàn toàn giống nhau hay số nhân có thể mở.

**(Q2) Display — CÓ THỂ BẬT LẠI DP/DVI TRỰC TIẾP KHÔNG?:** có thể display engine trên die bị OTP/fuse disable, một lớp firmware/driver chặn, hoặc PCB thiếu mạng output. Có thể **nhiều nguyên nhân cùng tồn tại**. Phải chứng minh riêng sự tồn tại PDISP/head/SOR/PHY, hiệu lực của `0x21C04`, VBIOS DCB/connector metadata và continuity tuyến DP/DVI.

**(Q3) PCI class straps:** 6 chân STRAP0..5 của G1 trên CAD có resistor footprints kéo lên 1.8V/kéo xuống GND. `STRAP3` R258/R261 ứng viên chọn 3D vs VGA theo so sánh tài liệu N18E/Envytools; **chưa có chứng minh bit mapping riêng TU106**, càng chưa xác định nó có đổi fuse hay Device ID.

## 2. Dữ liệu đã có — theo trình tự

1. **Hermes v14/v15:** thu thập VBIOS gốc 1 MiB (SHA256 `dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec`), fuse BAR0 dump, topology, PCI, GSP binary. `v15/FUSE/fuse2.json` có `base=0x21000`, key `regs["3076"] = 1`: offset `0xC04` → địa chỉ `0x21C04`. Những phân tích về bitfield khác còn không chắc.
2. **Hermes Phase 15–20:** báo cáo cũ có nhiều kết luận bị bác bỏ (BAR3 arbitrary GPU PA primitive, PWR mailbox exploit, các nhận định quá chắc từ BADF). Đừng khôi phục các kết luận đó thành sự thật. `BAO_CAO_TONG_HOP_PHASE15_20.md` ghi thay đổi của các giả thuyết. Một báo cáo cũ `BAO_CAO_DAY_DU.md` khẳng định display `0x21C04=0` và TPC thứ 18 đã 'không tồn tại' chỉ từ BADF; mâu thuẫn raw v15 và thiếu bằng chứng transistor vật lý. Giữ nguyên các mâu thuẫn để audit.
3. **Codex Phase 21:** phân tích mã nguồn host và GSP cho đường `RmDisableDisplay`, worker `0x04B30030`, consumer `0x04B20F54`, cached field `+0x334` trong GSP **615.78.08**. Host path TU106 dùng `gpuFuseSupportsDisplay_GM107` và register `NV_FUSE_STATUS_OPT_DISPLAY=0x21C04`, bit0 `DATA_ENABLE=0`; nếu raw bit0=1 predicate display-support false. **Không kết luận đó chắc chắn là OTP vật lý**. Trên target sau đó báo driver/firmware **615.71.09**, cần map lại địa chỉ/dataflow nếu dùng bản đang chạy. Đường driver DRM connector hiện không có, trong khi đồ họa headless hoạt động — chứng tỏ render và physical scanout độc lập.
4. **Boardview GenCAD R2:** GPU G1/BM5=STRAP3, lên `1V8_AON` qua R258, xuống GND qua R261; STRAP4 G1/BK5 R249/R264, STRAP5 G1/BJ5 R250/R265. STRAP0..2 là R255/R268, R257/R269, R256/R263. Boardview GeForce có J1 DisplayPort, J5 DVI, J10 HDMI, cùng net IFPD lanes, AUX, HPD và tụ ghép (C30/C31/C32/C33/C44/C45/C46/C47). Không phải BOM xác nhận trên bản CMP.
5. **Ảnh PCB thật:** 18 ảnh do chủ sở hữu chụp. Ảnh rõ `CG161P REV 2.00`, nhãn CMP40HX-8G. Quan sát trước đó: **J1 DP và J5 DVI có đầu nối vật lý**, J10 HDMI chỉ footprint chưa lắp. Vùng gần thạch anh Y1 27 MHz và GPU G1 có cụm điện trở; R258/R249/R250 được nhận định DNP, R261/R264/R265 trông có SMD → suy luận `STRAP5:3≈000`. **Việc định vị và phân loại resistor qua ảnh là dự đoán, chưa đo điện trở/logic/latch**. Hãy kiểm tra lại bằng boardview và ảnh gốc, không tự coi là đã chắc chắn.
6. **Ảnh footprint trên điện thoại:** `CG161P_R2_STRAP_FOOTPRINTS_PHONE.png`, `CG161P_R2_STRAP3_4_5_ZOOM_PHONE.png`, ảnh chú thích từ PCB. Hình GenCAD có toạ độ/hướng tương đối; ảnh overlay có thể lệch do phối cảnh/hướng xoay.

## 3. Ba điểm đang gây tranh cãi và cách trả lời đúng

**Display fuse:** báo cáo cũ một chỗ `0x21C04=0`, raw v15 tại `0x21C04=1` (chính xác `regs["3076"]`), theo hằng NVIDIA enable=0. Hãy xác thực hiện trạng với provenance; xác định nguồn là OTP hay shadow, chính sách driver hay phần cứng. Poison BADF PDISP/SOR khi đọc không đồng nghĩa transistor vắng mặt hay laser-cut.

**128 CUDA cores:** 34 SM/17 TPC là *số lượng đang có hiệu lực*, không chứng minh die 34 SM thật hoặc TPC thêm còn hoạt động. `fuse+0x650=0x0004001F` chưa có bitfield TU106 đủ chắc. TPC/GPC có offset trả BADF không phân biệt fuse/power/clock/reset/permission/addressing.

**R258/R261:** CAD chứng minh hai footprint trên STRAP3, không chứng minh pin BM5 trực tiếp là `VGA_DEVICE` trên TU106. Đồng thời phải xét STRAP4/5; không được suy diễn `R258 = VGA` hay `R261 = 3D` như quy luật chắc chắn. PCI class, device ID và display fuse là ba tín hiệu riêng.

## 4. Câu trả lời kỳ vọng

Tạo bảng verdict Q1/Q2/Q3 gồm: hiện biết chắc, giả thuyết, bằng chứng trực tiếp, giải thích đối lập, dữ liệu nào có thể phân biệt, thứ tự bước read-only/đo nguội phù hợp; nếu không thể biết chắc bằng nguồn hiện có, nói rõ giới hạn. Không nói 'có thể mở được' chỉ vì cùng TU106. Không gọi 'fuse cứng' chỉ từ tên register `FUSE_STATUS`.

## 5. Điểm mới trong yêu cầu bàn giao cho GPT-6 Astra

Người dùng không yêu cầu chia thành sáu phiên; **GPT-6 Astra là tên mô hình nhận bàn giao**. Câu hỏi ưu tiên số một là **display trên CMP 40HX có thể bật lại và xuất tín hiệu trực tiếp qua J1 DisplayPort/J5 DVI hay không**, với các điều kiện khả thi, không chỉ mô tả nguyên nhân bị disable. Ưu tiên tiếp theo: 128 core thiếu có hard fuse/defect hay bị ẩn, và vai trò chính xác của STRAP3/4/5 trong chuyển PCI class/SKU/display.

Không có kết quả kiểm chứng phục hồi display thành công trong dữ liệu hiện có. Phải nói rõ **chưa chứng minh** và thiết kế chuỗi kiểm chứng an toàn trước khi can thiệp.

# Đối chiếu ảnh PCB CMP 40HX với CG161P REV 2.00 và các Phase reverse engineering

**Phạm vi:** 18 ảnh trong `Quick Share.zip`; GenCAD nguyên bản `CG161P_R2_boardview.cad` trích từ archive RAR (SHA-256 `7338ccead9423c8ddd61f5c1e4f0147d95b3c6da5af3e9bae0a20fbcfab6264d`); báo cáo `CMP40HX_Strap_Report.docx`; Phase 15 fuse dump và tóm tắt Phase 21.

**Phương pháp:** Dùng dấu mốc silkscreen `Y1`, `PU3`, `U11`, `PL1`, `G1` để hiệu chỉnh vị trí linh kiện từ bảng `PLACE` trong GenCAD; quan sát ảnh độ phân giải gốc 6120×8160. Phân biệt rõ component visible, footprint DNP, suy luận điện áp và ý nghĩa register. Không có phép đo điện hay thao tác ghi nào được thực hiện.

## 1. Nhận diện đúng PCB

- Ảnh mặt sau `1793813621663.jpg` hiện rõ `CG161P REV 2.00` (vùng mép phải, chữ xoay); phù hợp boardview ASUS CG161P R2.
- Ảnh mặt trước `1793813621673.jpg` có nhãn `CMP40HX-8G` cùng cụm GPU `G1` và VRAM. Đây là card CMP đang nghiên cứu chứ không phải chỉ ảnh board GeForce dùng đối chiếu.

## 2. Phát hiện mới: dân số điện trở STRAP3/4/5

Cụm 12 footprint nằm sát thạch anh `Y1` 27.000 MHz, phía trên-trái GPU G1. So vị trí linh kiện GenCAD với ảnh `1793813621675.jpg` và `1793813621673.jpg`:

| Strap | GPU pin (CAD) | Pull-up tới 1V8_AON | Quan sát | Pull-down tới GND | Quan sát | Kết luận điều kiện |
|---|---|---|---|---|---|---|
| STRAP3 | G1/BM5 | R258 | Không lắp (2 pad trống) | R261 | Có linh kiện SMD | Có xu hướng LOW |
| STRAP4 | G1/BK5 | R249 | Không lắp | R264 | Có linh kiện SMD | Có xu hướng LOW |
| STRAP5 | G1/BJ5 | R250 | Không lắp | R265 | Có linh kiện SMD | Có xu hướng LOW |

Suy ra **strap vector STRAP5:3 ≈ `000` theo tình trạng lắp linh kiện** nếu PCB giữ nguyên connectivity GenCAD, linh kiện kéo xuống dẫn điện bình thường, đường `1V8_AON/GND` đúng và trạng thái được sample từ các net này. **Đây chưa phải phép đo logic H/L hay bản đọc giá trị latch/strap register.**

Ảnh minh họa đánh dấu: `CMP40HX_STRAP_PHOTO_ANNOTATED.jpg`. Các nhãn được xác định bằng vị trí tương quan Y1/G1 với bản vẽ CAD; nên kiểm tra lại bằng đồng hồ khi card đã ngắt nguồn nếu chuẩn bị can thiệp.

**Lưu ý:** Không đủ căn cứ từ ảnh để suy ngữ nghĩa STRAP3→VGA, vì STRAP5:3 có thể chọn chức năng đa bit tuỳ SKU. Không nên chuyển R258/R261 chỉ vì card hiện khai báo `0302`.

## 3. Tuyến xuất hình thực tế trên CMP

Trong ảnh thật `1793813621666.jpg`:

- **J1 DisplayPort: connector vật lý đã lắp.** Có cụm linh kiện phụ trợ xung quanh.
- **J5 DVI: connector vật lý đã lắp.** Có cụm linh kiện xung quanh.
- **J10 HDMI: chỉ có footprint/pad, không lắp connector.** Có những linh kiện nhỏ đã lắp dọc cạnh footprint.

Vì thế nhận định cũ "PCB CMP 40HX không có bất kỳ cổng xuất hình nào" **không áp dụng cho card chụp này**. Tuy vậy, cả DP/DVI đang lắp cũng chưa chứng minh các lane vi sai, AUX/HPD/DDC thông mạch hoặc display PHY/silicon hoạt động.

CAD GeForce xác minh J1 DP từ G1 IFPD_L0..L3 qua C30..C47, và có net cho AUX/HPD; ảnh thể hiện cụm linh kiện gần cổng, nhưng chưa có phép đối chiếu độc lập tới từng mã tụ trên card CMP (không tự kết luận mọi C30–C47 populated).

Ảnh minh họa: `CMP40HX_PORTS_PHOTO_ANNOTATED.jpg`.

## 4. Đối chiếu dữ liệu firmware / fuse / topology đã có

| Câu hỏi | Kết quả hiện có | Ý nghĩa của ảnh mới |
|---|---|---|
| PCI 3D vs VGA | Phase 15 ghi card enum `0302` | STRAP3/4/5 được lắp theo kiểu kéo xuống; **chưa chứng minh** STRAP3 chọn PCI class |
| Display fuse | Raw v15 `FUSE/fuse2.json`, offset `0xC04` (3076 decimal), tương ứng `0x21C04`: `1`. Định nghĩa NVIDIA `DATA_ENABLE=0` ⇒ display-support predicate false | Card có J1 DP và J5 DVI vật lý; fuse status `1` vẫn có thể làm driver không khởi tạo display, độc lập với cổng |
| Display ROM/DCB | Phase 21 nói connector entries = 0 | Việc J1/J5 đã lắp cho thấy DCB rỗng không đủ chứng minh không có cổng vật lý; VBIOS không khai báo routing vẫn có thể ngăn display |
| Hard OTP? | Chưa xác định `NV_FUSE_STATUS_OPT_DISPLAY` lấy từ physical eFuse hay latch/shadow | Ảnh PCB **không** thể phân biệt OTP hay shadow |
| Thiếu 128 CUDA core | CMP 34 SM / 17 TPC, TU106 full 36 SM / 18 TPC | Ảnh **không** thể phân biệt TPC hỏng/fused-off với TPC bị ẩn bởi phần mềm; không nhìn được cấu trúc trong die |

**Sửa lỗi nhỏ trong báo cáo chéo cũ:** `0xC04` hệ 16 là `3076` hệ 10, không phải `3084`; raw v15 tại `regs["3076"] = 1`, và `regs["3084"] = 1` ở offset khác `0xC0C`. Giá trị display fuse `1` vẫn đúng, nhưng bắt buộc xác minh key offset chính xác.

## 5. Khuyến nghị Phase tiếp theo, chỉ đọc/không sửa

1. Ghi giá trị PCI class/Device ID hiện tại cùng provenance và đối chiếu với STRAP5:3 dự đoán `000`.
2. Đọc hiệu dụng PSTRAPS đúng offset TU106 được xác minh, và lưu cả bitfield lẫn driver/source đối chiếu; không ghi thử các thanh ghi.
3. Đọc lại `0x21C04` qua giao diện read-only đã kiểm chứng an toàn và đối chiếu với phiên firmware đang chạy, nhận diện nguồn OTP/shadow.
4. Tìm net đầy đủ G1→J1/J5 trên CAD, lập danh sách các linh kiện nối tiếp thực sự cần kiểm tra; dùng chụp macro và đo thông mạch **khi ngắt nguồn**, không tự hàn/lắp/đổi strap.
5. Reverse floorsweeping mask TU106 cho TPC còn thiếu từ dump đã có; không gán `BADF` là chứng cứ silicon bị cắt.

**Verdict:** Cả ba STRAP3/4/5 *trông như* được kéo xuống trên card thực; **J1 DisplayPort và J5 DVI hiện diện vật lý**; vẫn chưa chứng minh được GPU xuất hình, hard OTP display, hay tình trạng vật lý của TPC thứ 18. Đây là kết quả mạnh hơn báo cáo CAD-only vì có ảnh lắp thực tế trên board CG161P REV 2.00.

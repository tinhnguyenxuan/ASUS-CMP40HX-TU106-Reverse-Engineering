# CMP 40HX / TU106 — gói bàn giao nghiên cứu cho **một phiên GPT-6 Astra**

**Mục tiêu hiện tại: GPT-6 Astra kết luận khả năng BẬT DISPLAY, cùng hai nhánh hỗ trợ:**

1. 128 nhân CUDA chênh lệch giữa TU106 cấu hình 2304 cores (36 SM, 18 TPC) và CMP 40HX 2176 cores (34 SM, 17 TPC) **có còn transistor trên die, bị fuse/floorsweep, hay chỉ bị firmware che?** Nếu có transistor, có đủ bằng chứng chúng khỏe và có thể sử dụng không?
2. **Display (ưu tiên cao nhất — có BẬT LẠI ĐƯỢC không?):** `NV_FUSE_STATUS_OPT_DISPLAY` tại `BAR0 0x21C04` đang phản ánh eFuse/OTP cứng, shadow/latch, hay policy? Khối PDISP/SOR/PHY trong die tồn tại? Đường DP/DVI trên PCB CMP còn liên tục không? Có thể khôi phục xuất hình trực tiếp hay không?
3. **Straps:** sáu net STRAP0..5 trên CG161P R2, đặc biệt `STRAP3` nối GPU BM5 với R258 (1V8_AON)/R261 (GND), có tác động tới PCI class 0302/0300, Device ID 10DE:1F0B hoặc display enable không? Những bit/nhánh nào có chứng cứ riêng cho TU106?

**Không nghiên cứu:** ép xung, tăng điện áp, benchmark CUDA/Tensor/Vulkan, phát triển exploit, chỉnh power limit, ROP chain, cố mở khóa ngay bằng cách sửa điện trở. Các chức năng CUDA/render cơ bản đã được chứng minh hoạt động, không phải câu hỏi hiện tại.

**Đọc theo thứ tự:** `SESSION_SUMMARY.md` → `EVIDENCE_CONTRADICTIONS.md` → `DISPLAY_ENABLE_DECISION_TREE.md` → `ASTRA_MASTER_PROMPT.md` → raw sources.

**Mức độ bằng chứng:**
- `PRIMARY`: ảnh thật của chính PCB, file GenCAD, VBIOS gốc, dump fuse/PCI lưu dưới dạng raw (nhưng dump cũ vẫn chỉ là historical).
- `SECONDARY`: báo cáo/diễn giải của Hermes, Codex và các tài liệu đối chiếu; có thể nhầm, mâu thuẫn hoặc chưa được kiểm chứng.
- `HYPOTHESIS`: suy luận chức năng một strap, trạng thái OTP, sự tồn tại vật lý của TPC/PDISP.

**Bên trong gói compact:** GenCAD, báo cáo Word, ảnh PCB dạng preview đủ để xem toàn bộ, crop/ảnh đã chú thích, binary VBIOS gốc, các file fuse/topology/PCI của v15, các báo cáo Phase 21 liên quan display, tóm tắt các kết luận sai cũ. Các ảnh ở `PHONE_PREVIEWS` được giảm độ phân giải để dễ gửi qua điện thoại; **không phù hợp khẳng định chắc chắn điện trở 0402 có lắp hay không nếu chi tiết bị mờ**. Cần ảnh nguyên gốc trong `Quick Share.zip` hoặc gói FULL để kiểm tra vi mô.

**Lưu ý:** Một số tên file .bin.txt trong dữ liệu cũ thực chất là binary. Gói này đặt đúng phần mở rộng `.bin` và giữ byte nguyên vẹn; SHA256 trong `CHECKSUMS.sha256`.

**Mặc định chỉ phân tích offline / read-only.** Không ghi OTP, MMIO, PCI config; không đổi/hàn STRAP; không flash ROM hoặc thử firmware patch. Nếu cần thử nghiệm can thiệp, viết proposal riêng và chờ chấp thuận.

**Đây là gói cho một phiên GPT-6 Astra, không có phân công sáu agent.**

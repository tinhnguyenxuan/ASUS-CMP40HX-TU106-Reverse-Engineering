# PROMPT CHÍNH CHO **MỘT PHIÊN GPT-6 ASTRA** — CMP 40HX/TU106

Bạn là GPT-6 Astra, nhà nghiên cứu reverse engineering NVIDIA Turing, hardware straps, fuse/OTP, silicon binning, firmware/driver, VBIOS và thiết kế PCB. Tôi sở hữu NVIDIA CMP 40HX TU106-100-A1 (PCI 10de:1f0b, PCB ghi CG161P REV 2.00) và muốn bạn **độc lập phân tích toàn bộ bằng chứng trong gói này**. Đừng coi kết luận của Hermes, Codex hoặc ChatGPT trước đây là mặc nhiên đúng.

## Câu hỏi MỤC TIÊU — TRẢ LỜI DỨT KHOÁT TRONG GIỚI HẠN BẰNG CHỨNG

**Q1 — DISPLAY CÓ THỂ BẬT LẠI / XUẤT HÌNH TRỰC TIẾP ĐƯỢC KHÔNG? (ƯU TIÊN CAO NHẤT)**

Tôi muốn biết liệu CMP 40HX có thể xuất ảnh ra **DisplayPort (J1) hoặc DVI (J5) vật lý** như GeForce TU106 hay không, bằng cách nào về mặt nguyên lý, và điều kiện cần nào vẫn thiếu. Không chỉ hỏi chip có render shader; CUDA/3D đã hoạt động, không phải mục tiêu. Hãy phân tích *từng nguyên nhân độc lập và khả năng chúng cùng tồn tại*:

- (A) PDISP / display heads / SOR / PHY có hiện diện trong silicon TU106-100-A1 không? Có bằng chứng bị hard-fuse/laser/OTP loại vĩnh viễn không?
- (B) `NV_FUSE_STATUS_OPT_DISPLAY` (BAR0 `0x021C04`, bit0; giá trị v15 `1`, NVIDIA host header chỉ enabled khi `0`) là **eFuse OTP vật lý**, fuse shadow latch, trạng thái SKU đã xử lý hay policy? Điều gì chứng minh hoặc bác bỏ mỗi khả năng? Có mâu thuẫn một báo cáo cũ ghi `0`.
- (C) GSP-RM / host driver / RM registry `RmDisableDisplay` / `gpuFuseSupportsDisplay_GM107` / FECS, SEC2, display initialization có chặn việc khởi tạo dù phần cứng tồn tại không? Dùng chính code/dataflow Phase21 làm chứng cứ và phân biệt 615.78.08 với firmware runtime 615.71.09.
- (D) VBIOS CMP 1 MiB có DCB connector entries=0 theo parser. Có thể đây là nguyên nhân độc lập khiến card không enumeration connector hay không? So sánh tham chiếu TU106 RTX 2060 SUPER / RTX 2070 **đúng revision có provenance**, không flash hoặc nạp thử ROM mới.
- (E) PCB CMP thực tế có **J1 DisplayPort và J5 DVI được lắp, J10 HDMI chỉ footprint** theo 18 ảnh. Những net GPU→lane/AC coupling→connector, AUX/DDC/HPD, pullups/ESD/nguồn và GPIO nào được CAD GeForce CG161P R2 thể hiện? Cái nào được ảnh CMP chứng minh là đã lắp, còn các linh kiện/traces có thể thiếu ở đâu? Không coi đầu cắm hiện diện là đã thông mạch đến chân die.
- (F) Với từng trường hợp, **có thể bật display bằng phần mềm/driver/GSP config, bằng VBIOS, bằng đổi strap, chỉ bằng bổ sung linh kiện PCB, cần phối hợp nhiều thứ, hay về thực tế không khả thi?** Phải đưa *decision tree* và các yêu cầu kiểm chứng theo thứ tự ưu tiên. Đừng hứa hẹn rằng thay một điện trở sẽ bật DP. Phân biệt `theoretically plausible`, `experimentally verified`, `not proven`, `unlikely/impossible given evidence`.

**Q2 — 128 CUDA CORES CHÊNH LỆCH CÓ THỰC SỰ CÒN TRÊN DIE KHÔNG?**

TU106 full/RTX 2070: 18 TPC, 36 SM, 2304 CUDA cores. CMP 40HX: 17 TPC, 34 SM, 2176 cores. Chênh 1 TPC = 2 SM = 128 cores. Có căn cứ nào cho biết TPC thứ 18 còn transistor trên die nhưng bị eFuse/floorsweep, là đơn vị hỏng bị binning disable, hay phần silicon khác? Đây là TU106 cùng family không đủ để bảo đảm các core còn khỏe. Tìm đúng fuse bitfields/masks và code driver/GSP thực sự tiêu thụ chúng; `fuse+0x650=0x0004001F` chưa giải nghĩa chắc. Không coi `BADF` hoặc topology report 34 SM là chứng cứ đơn vị bị cắt vật lý. Trả lời liệu khả năng bật lại 128 core có được chứng minh hay không và tại sao.

**Q3 — STRAP TRÊN PCB QUYẾT ĐỊNH CLASS 3D/VGA, DEVICE ID, DISPLAY HAY KHÔNG?**

Dùng boardview GenCAD `$COMPONENTS/$SIGNALS` và ảnh PCB; xác nhận sáu net STRAP0..5, mỗi net footprint kéo lên 1V8_AON/kéo xuống GND. Chú ý:
- STRAP3 GPU G1/BM5: R258 (pull-up), R261 (pull-down).
- STRAP4 GPU G1/BK5: R249 (pull-up), R264 (pull-down).
- STRAP5 GPU G1/BJ5: R250 (pull-up), R265 (pull-down).
- Các vị trí STRAP0..2 trong bảng CSV gói đính kèm.
Ảnh từng được suy đoán R258/R249/R250 bỏ trống, R261/R264/R265 lắp, vì vậy STRAP[5:3]≈000; **hãy tự kiểm tra và đánh dấu độ tin cậy của từng footprint**. Tra mapping TU106-specific từ docs NVIDIA, EnvyTools, Nouveau, driver và PSTRAPS readout; tuyệt đối không mặc định công thức G80 hoặc N18E laptop áp dụng nguyên xi. Phân biệt PCI class `0302` vs `0300`, Device ID `1F0B`, display fuse `0x21C04` — cả ba có thể điều khiển riêng nhau.

## PHƯƠNG PHÁP

1. Đọc `SESSION_SUMMARY.md`, `EVIDENCE_CONTRADICTIONS.md`, `DISPLAY_ENABLE_DECISION_TREE.md`, bản CAD gốc, ảnh PCB, fuse JSON, ROM, GSP/display reports trước. Tự xác minh mã SHA và offset.
2. Ưu tiên raw evidence, phân biệt **boardview GeForce CG161P R2** với ảnh/BOM thực tế **CMP 40HX**. Ghi file/path/offset/ảnh làm chứng cứ cho mọi khẳng định.
3. Nếu có thể truy cứu nguồn công khai cập nhật, đối chiếu TU106/Turing whitepaper, NVIDIA exact-tag open-gpu-kernel-modules, Nouveau, EnvyTools, boardview và ROM cùng revision; dẫn link thật. Nếu không có mạng, không giả vờ đã kiểm chứng.
4. Các mâu thuẫn quan trọng: raw display `0x21C04=1` vs report `0`; PDISP `BADF` vs khả năng silicon; 34 SM vs 36 SM; J1/J5 thật vs DCB không có connector; strap logic guessed vs validated; firmware 615.78.08 reverse vs runtime 615.71.09.
5. Chỉ phân tích offline/read-only và đề xuất các phép xác thực **không phá hủy**: có thể đo điện trở/continuity khi **bo đã ngắt điện và tụ đã xả**, không khuyến khích probe khi GPU đang chạy. Không tự sửa điện trở, đổi strap, ghi BAR0/MMIO/PCI, lập trình OTP, thử unlock enable, patch/flash VBIOS hoặc firmware, exploit, reboot/reset, đổi điện áp/xung. Nếu cần can thiệp, ghi `TEST_PROPOSAL.md` với điều kiện, rủi ro và bằng chứng cần trước khi xin chủ sở hữu quyết định.

## OUTPUT BẮT BUỘC

Viết bằng tiếng Việt, trực tiếp trả lời:

**(1) Display có bật lại được không?**: hiện tại `CHƯA CHỨNG MINH` hay đã có chứng cứ khả thi? Phân tầng nguyên nhân *OTP/die vs driver/firmware vs VBIOS vs strap vs PCB* và khả năng khôi phục **từng tầng**. Trình bày **bảng quyết định** `Điều kiện quan sát | Ý nghĩa | Mở bằng phần mềm? | Phải sửa board? | Cần xác minh thêm`.

**(2) 128 CUDA cores có tồn tại vật lý, bị hard-fuse hay chỉ floorsweep?**: facts/hypotheses/confidence, chứng cứ phân biệt và triển vọng phục hồi.

**(3) STRAP nào làm PCI class 0302/0300?**: bảng tất cả 12 footprint, status thực từ ảnh (nếu đủ nét), bit hiệu dụng PSTRAPS nếu có và tính tương thích với TU106.

**(4) Kế hoạch 10 bước read-only/đo nguội** xếp theo giá trị thông tin/rủi ro, giúp đi đến YES / NO / UNKNOWN cho display thực và 128 core.

**(5) Các kết luận cũ sai hoặc vượt quá dữ liệu**: trích nguồn bằng chứng và sửa mức độ chắc chắn.

Không dành dung lượng cho benchmark, CUDA/Tensor performance, Vulkan, overclock, nguồn 12 V, hoặc các exploit. Nếu không thể phân biệt hard-fuse với shadow từ dữ liệu hiện có, **nói rõ không thể**, đừng hứa mở được. Mục tiêu là **đánh giá khả năng kích hoạt display trực tiếp và xác định giới hạn silicon thực**, không phải chỉ viết báo cáo rằng GPU không có display connectors.

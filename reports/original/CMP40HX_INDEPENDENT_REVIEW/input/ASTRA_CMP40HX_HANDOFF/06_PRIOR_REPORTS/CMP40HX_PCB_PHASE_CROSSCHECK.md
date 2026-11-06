# Kiểm tra độc lập: CAD CG161P R2 đối chiếu Phase 14–21

Ngày: 2026-11-04. Phạm vi: chỉ **đọc** CAD ASUS GeForce CG161P R2 và dữ liệu lưu trong CMP40HX phase archives; **không** xác nhận cấu hình hàn thực tế của CMP 40HX.

## Nguồn dữ liệu

- `CMP40HX_Strap_Report.docx`, báo cáo 9 trang của người dùng.
- `ASUS DUAL-RTX2060S-O8G-EVO-V2 CG161P R2 BOARDIEW(BDV)(.CAD).rar`, giải nén nội dung GenCAD thành `CG161P_R2_boardview.cad`.
- SHA256 GenCAD: `7338ccead9423c8ddd61f5c1e4f0147d95b3c6da5af3e9bae0a20fbcfab6264d` (khớp báo cáo Word).
- `cmp40hx_research_v15_final.tar.gz` (các file FUSE, TOPOLOGY, PCIE và script).
- `baocao.zip` (Phase 21 Codex: `FUSE_CAPABILITY_MAP.json`, `GSP_CAPABILITY_GATES.md`, evidence/target_live...).
- Nguồn tham khảo bên ngoài: [EnvyTools PSTRAPS](https://github.com/envytools/envytools/blob/master/docs/hw/io/pstraps.rst), [NVIDIA GM107 fuse header 615.71.09](https://fossies.org/dox/NVIDIA-open-gpu-kernel-modules-615.71.09/maxwell_2gm107_2dev__fuse_8h.html), [NVIDIA TU106 whitepaper](https://www.nvidia.com/content/dam/en-zz/Solutions/design-visualization/technologies/turing-architecture/NVIDIA-Turing-Architecture-Whitepaper.pdf).

## A. Bảng 6 strap được xác minh lại độc lập

| Net | GPU G1 pin | Pull-up 1V8_AON | Pull-down GND |
|---|---|---|---|
| STRAP0 | BL3 | R255 | R268 |
| STRAP1 | BL4 | R257 | R269 |
| STRAP2 | BM4 | R256 | R263 |
| STRAP3 | BM5 | R258 | R261 |
| STRAP4 | BK5 | R249 | R264 |
| STRAP5 | BJ5 | R250 | R265 |

- Các kết nối xuất phát từ các `SIGNAL STRAP0..5` và `SIGNAL 1V8_AON`/`SIGNAL GND` của `$SIGNALS`, cũng như `COMPONENT R...` ở `$COMPONENTS`.
- STRAP3: G1/BM5, R258 pin 1=1V8_AON, pin 2=STRAP3; R261 pin 1=STRAP3, pin 2=GND.
- R258 PLACE (2272.874,2580.315) TOP; R261 PLACE (2337.835,2579.528) TOP.
- Đây là **footprint** trong CAD RTX 2060 SUPER, không chứng minh resistor nào đã lắp trên card CMP, không cho biết giá trị ohm hoặc mức logic thật lúc reset.

## B. Display routing có trong boardview GeForce

Trong thiết kế này, các đường video từ GPU G1 đến DP J1 đi qua tụ ghép AC (chỉ net connectivity, không xác nhận tụ đã lắp trên CMP):

| GPU signal | G1 pin | Tụ nối tiếp | Sau tụ → J1 |
|---|---|---|---|
| IFPD_L0 | BM18 | C47 | IFPD_L0_C → J1 pin 1 |
| IFPD_L0* | BM17 | C46 | IFPD_L0_C* → J1 pin 3 |
| IFPD_L1 | BL17 | C33 | IFPD_L1_C → J1 pin 4 |
| IFPD_L1* | BK17 | C32 | IFPD_L1_C* → J1 pin 6 |
| IFPD_L2 | BK15 | C45 | IFPD_L2_C → J1 pin 7 |
| IFPD_L2* | BL15 | C44 | IFPD_L2_C* → J1 pin 9 |
| IFPD_L3 | BM15 | C31 | IFPD_L3_C → J1 pin 10 |
| IFPD_L3* | BM14 | C30 | IFPD_L3_C* → J1 pin 12 |

- `IFPD_AUX_C*` nối J1 pin 17 và D2 về GND; `IFPD_AUX_C` nối J1 pin 15 và D3 về GND. D2/D3 phù hợp vai trò ESD/protection/aux line, nhưng netlist không xác nhận diode thực tế còn được lắp.
- `DP_D_HPD_C` nối J1 pin 18 và C1293 về GND. `DP_D_HPD_R` nối C1296 về GND. `DP_PWR_CD` nối J1 pin 20 và C1282 về GND.
- `Q713/Q714/U663` nằm trong mạch nguồn 12 V; `U666/U667` nằm ở các net quạt. Không nên phân loại chúng thành linh kiện display.
- Các đường xuất hình HDMI/DVI cũng có trong boardview (`J10`, `J5`), nhưng chỉ chứng minh **CAD GeForce** đã có mạng tuyến.

## C. Đối chiếu Phase 14/15/21, những kết luận cần sửa

### C1. PCI 3D class và hardware straps
- **CAD** chứng minh điện trở pull-up/pull-down đến sáu chân strap, và R258/R261 là một ứng viên khảo sát quan trọng.
- **Phase 15** `PCIE/pcie_map.json` ghi `0000:03:00.0 3D controller`, nhưng chỉ chứng minh PCI class đang là 0302, không chứng minh tầng quyết định là STRAP3.
- **EnvyTools** mô tả `PSTRAPS set 1 bit 4`: 0=0302 / 1=0300 trên nhiều NVIDIA G80+; vẫn chưa xác thực mapping này sang chân G1/BM5/STRAP3 của TU106.
- Không thấy bằng chứng đồng thời cho cả hai phía `STRAP5:3` được hàn trên CMP, register PSTRAPS effective trên đúng card, và PCI class ở cùng trạng thái.
- **Kết luận**: circuit tồn tại trong CAD; `R258 ⇄ VGA` / `R261 ⇄ 3D` chưa chứng minh.

### C2. Display fuse `0x21C04`
- `v15/FUSE/fuse2.json`: offset `0xC04` = decimal 3084 = `1` (dump cũ, không phải capture live mới).
- `v15/FUSE/fuse_bitfields.csv`, `FUSE/P0_FUSE.md`, `PHASE15/FUSE_SEMANTICS.md` **đọc ngược cực tính**: nói `1` là enabled.
- Header NVIDIA `NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE = 0x00000000` ⇒ `bit0=0` mới là `ENABLE`; `bit0=1` làm predicate `gpuFuseSupportsDisplay_GM107` false theo phân tích Codex Phase 21.
- Từng có tài liệu tổng hợp cũ `BAO_CAO_DAY_DU.md` ghi `0x21C04=0`, **trái với raw dump v15=1**. Cần giữ nguyên mâu thuẫn, kiểm tra thời điểm/version/cách đọc trước khi kết luận hard OTP.
- `v15/TOOLS/q6_display.py` dùng `mmap(PROT_READ)` đọc PDISP/SOR/DAC, các giá trị `0xBADF1301`; chứng minh không trả dữ liệu register ở những offset đó tại thời điểm dump, **không chứng minh phần tử silicon bị cắt vật lý**.
- `Phase21/GSP_CAPABILITY_GATES.md`: host `kdispStatePreInitLocked_IMPL` có thể reject sau `gpuFuseSupportsDisplay`, là đường capability gate thật. Nhưng **OTP hard fuse vs shadow/status và PCB IFP routing hiện vẫn UNKNOWN**.

### C3. 128 CUDA cores, 17 TPC vs 18 TPC
- TU106 đầy đủ (RTX 2070): 3 GPC × 6 TPC × 2 SM = 36 SM = 2304 CUDA.
- CMP card được báo 34 SM = 17 TPC = 2176 CUDA, trùng cấu hình RTX 2060 SUPER.
- `v15/FUSE/fuse2.json`: offset `0x650`=`0x0004001F`, nhưng `PHASE15/FUSE_SEMANTICS.md` cũng thừa nhận chưa có bitfield TU106 xác thực ⇒ **chưa được phép giải mã đó là physical laser cut**.
- `TOPOLOGY/silicon_topology.md` và báo cáo cũ đôi khi gán địa chỉ TPC/GPC không nhất quán; GPC/TPC instance `BADF` có thể phản ánh disabled, reset, power-gate, inaccessible, hay absent; không phân biệt bằng một mã error.
- Kết luận hiện tại: **1 TPC không khả dụng (2 SM, 128 CUDA)**; việc transistor có hiện diện và có thể mở lại hay không **chưa chứng minh**. 34 SM là active/visible count, không chứng minh die vật lý chỉ có 34 SM.

## D. Bước tiếp theo (không ghi/không mod)

1. Chụp ảnh macro rõ vùng GPU, `R258/R261/R249/R264/R250/R265` **trên card CMP thật**, xác nhận installed/DNP và trị số (đo khi tắt nguồn). Chụp cả cụm cổng DP bị bỏ, C30–C47 và các đường AUX/HPD.
2. Trên target, lưu PCI class/ID với `lspci -Dnn -s 0000:03:00.0` và đọc `setpci -s 0000:03:00.0 08.L` (chỉ đọc, không gắn `=`).
3. Đối chiếu bản đọc hiệu dụng của PSTRAPS bằng register definition TU106 đã xác minh, không quét hay viết các offset suy đoán.
4. Đọc lại display fuse bằng **giao diện read-only đã kiểm chứng an toàn**, lưu timestamp, driver version, GPU UUID và raw value. Không mặc định bit fuse status là OTP cell vật lý.
5. Đối chiếu source GPU TU106 floorsweeping masks với raw fuse status và active SM/TPC counts; cần bản tương đương RTX 2070 và RTX 2060 SUPER có provenance để phân biệt mask vs physical unit.

## Verdict ba câu hỏi

| Câu hỏi | Trạng thái bằng chứng |
|---|---|
| Điện trở có thể quyết định PCI class? | **Có cơ chế strap trên GPU nói chung và footprint thực trong CAD; ánh xạ STRAP3→PCI class trên CMP TU106 chưa chứng minh** |
| Display bị hard fuse hay chỉ thiếu cổng/đường mạch? | **Phase 21 chứng minh driver gate từ fuse-status; hard OTP vs shadow, trạng thái silicon và routing CMP chưa xác định** |
| 128 core có bị khóa không? | **Có 128 core không hoạt động/không hiển thị; không có bằng chứng trực tiếp chúng bị xóa vật lý, laser-cut hay có thể phục hồi** |

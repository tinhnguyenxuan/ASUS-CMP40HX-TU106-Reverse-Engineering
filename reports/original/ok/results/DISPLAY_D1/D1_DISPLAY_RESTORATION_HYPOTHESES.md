# D1-F — CÁC GIẢ THUYẾT CẠNH TRANH

**GPU:** CMP 40HX, TU106-100-A1, PCI `10DE:1F0B`
**Ngày:** 2026-11-06 · Không dùng phần trăm xác suất tự đoán

---

## Bốn giả thuyết (theo yêu cầu E)

- **H1** — Displayless chủ yếu do VBIOS / product configuration.
- **H2** — Displayless do fuse hoặc hardware latch; driver chỉ phản ánh kết quả.
- **H3** — Có nhiều gate độc lập trong VBIOS, GSP và phần cứng.
- **H4** — Display hardware bị vô hiệu hoá hoặc không hoạt động trên die thực tế.

Mỗi giả thuyết: Evidence for / Evidence against / Remaining unknown / Cần thêm gì / Khả năng khôi phục.

---

## H1 — Displayless chủ yếu do VBIOS / product configuration

### Evidence for

1. **`NO_DISPLAY_SUBSYSTEM = 1`** trên CMP, **= 0** trên cả 3 GeForce TU106. Đo trên 5 ROM, bit duy nhất bật (`flags = 0x02` vs `0x00`). Spec NVIDIA định nghĩa bit này là *"Display subsystem isn't included in the GPU (used for displayless coproc)"*.
   - File offset `0x289CE` (CMP) / `0x289A2` (GeForce), raw `00 00 02 00 00` / `8F 4E 00 00 00`.
2. **`DCB entry_count = 0`** trên CMP (signature `0x4EDCBDCB` hợp lệ, `hdr=0x23`, `cnt=0`), **= 16** trên GeForce (5–7 output thật). DCB là bảng connector do VBIOS cung cấp.
3. **ROM CMP build theo nhánh khác hẳn**: `BIOS_VERSION` `90.06.67.00` vs `90.06.44.00/4C/3D`.
4. **Cùng die, khác ROM, khác hành vi** — chứng minh ROM mang thông tin quyết định sản phẩm.

### Evidence against

1. **Gate fuse chạy TRƯỚC khi VBIOS được dùng cho display.** `kdispStatePreInitLocked` (`kern_disp.c:444`) đọc `0x021C04` từ **silicon**, không hỏi VBIOS. Sửa ROM không đổi giá trị đó.
2. **Không tìm được code tiêu thụ `NO_DISPLAY_SUBSYSTEM`.** `grep -rni "coproc|noDisplaySubsystem|NO_DISPLAY"` trên 147 MB source RM → **0 hit liên quan**. GSP cũng không tham chiếu rõ ràng.
3. **`Coproc Build` (B+28 bit1) = 1 trên CẢ CMP lẫn GeForce** (`0x36`) ⇒ không phân biệt được gì, không thể là cờ displayless riêng.
4. **`B+32` khác nhau (0x12 vs 0x10) nhưng vai trò chưa xác định** — nằm ngoài vùng spec rev 1 định nghĩa. Không dùng làm bằng chứng.
5. **Nouveau không đọc VBIOS được** trên card này: `pramin_init` fail ở `0x021C04` trước cả VBIOS parse. VBIOS không phải nơi quyết định duy nhất.

### Remaining unknown

- Ai **tiêu thụ** `NO_DISPLAY_SUBSYSTEM`? (devinit? GSP? không ai?) — **chưa tìm được consumer**.
- Nếu flash ROM GeForce lên CMP, giá trị `0x021C04` có đổi không?

### Cần thêm bằng chứng gì

- **T-A2**: flash ROM GeForce TU106 lên CMP rồi đọc lại `0x021C04`. Nếu vẫn = 1 ⇒ H1 sai (fuse thắng). Nếu = 0 ⇒ H1 có cơ sở.
- Trace consumer của BIT_U trong devinit/GSP (reverse sâu hơn).

### Khả năng khôi phục nếu H1 đúng

**Điều kiện:** sửa hai trường VBIOS (`NO_DISPLAY_SUBSYSTEM = 0`, thêm DCB connector entries) + flash.
**Mức tin cậy:** **THẤP**. Lý do: gate fuse chặn trước, và gate thứ hai (`ipVersion`) chưa đo. Sửa VBIOS một mình **không đủ** để vượt hai gate kia.
**Chưa từng có báo cáo thành công** trong nguồn cmp.wiki (họ nói rõ không có dữ liệu 40HX).

---

## H2 — Displayless do fuse hoặc hardware latch

### Evidence for

1. **`0x021C04 = 0x00000001`** đo được, read-only (`R-I4R` trong header).
2. **Đối chứng cửa sổ fuse thật:** `0x21378 = 0` (NVDEC enabled) và `0x2174C = 1` là hai ô **khác block** trả giá trị khác nhau, có nghĩa riêng ⇒ cửa sổ `0x21000` đang route dữ liệu fuse thật, không phải hằng rác.
3. **Không phần mềm nào ghi được vào đây:** `grep -rn "21C04"` trên 147 MB source RM → **0 store**; header khai báo `R-I4R`; GSP 0 literal hit.
4. **Dịch chuyển cửa sổ chứng minh đây là fuse block:** TU102 `0x2174C` ↔ GA100 `0x82074C`, TU102 `0x21378` ↔ GA100 `0x820378` — cùng Δ `0x7FF000` ⇒ base TU106 = `0x21000`, offset nội bộ `0xC04`.
5. **Nouveau gọi thẳng nó "... display disabled"** — NVIDIA biết ý nghĩa của bit này.
6. **Comment NVIDIA trong RM:** *"Some chips not marked displayless do not support display"* (`kern_gpu_gm107.c:64`) — thừa nhận fuse là nguồn sự thật.

### Evidence against

1. **Không chứng minh được là raw OTP.** Không có đường đọc raw OTP độc lập với shadow register trên TU106. Có thể là **hardware-latched shadow** được set ở reset.
2. **Không loại trừ được devinit/GSP đọc và set nó.** "Không tìm thấy literal" không chứng minh "không có consumer" — địa chỉ có thể đến từ bảng cấu hình hoặc con trỏ hàm.
3. **Khe hở đo đạc:** chưa đọc `0x021C04` trên bất kỳ GeForce TU106 nào. Không có baseline để so sánh (fuse trên GeForce có = 0 không?).
4. **"Giữ nguyên sau reboot" không được dùng làm bằng chứng** — shadow register cũng giữ nguyên nếu cùng điều kiện latch.

### Remaining unknown

- Đây là **raw OTP** hay **shadow/latch**? — **chưa phân biệt được**.
- GeForce TU106 cùng die đọc ra bao nhiêu? — **chưa đo**.
- Mọi CMP 40HX đều = 1, hay chỉ card này? — **chưa đo**.

### Cần thêm bằng chứng gì

- **T-A1**: đọc `0x021C04` ngay sau PCI reset, **trước khi** load driver, khi chưa firmware nào chạy. Nếu vẫn = 1 ⇒ silicon/devinit set, không phải GSP.
- **T-A2**: flash ROM GeForce → đọc lại. Phân biệt fuse cứng vs cấu hình được.
- **T-A3**: so sánh với CMP 40HX thứ hai.
- **Baseline**: đọc `0x021C04` trên RTX 2060S/2070 thật.

### Khả năng khôi phục nếu H2 đúng

**Điều kiện:** phải thay đổi giá trị fuse/latch trên silicon. Không có đường phần mềm: `R-I4R`, 0 store, GSP không chạm.
**Mức tin cậy khôi phục: RẤT THẤP.**
- Nếu là **raw OTP**: **không khôi phục được** bằng phần mềm, định nghĩa là vậy.
- Nếu là **shadow/latch**: lý thuyết có thể có đường ghi đè qua devinit strap hoặc register ẩn — **chưa tìm thấy bằng chứng nào** về đường đó trên TU106 (không có OPT/RECONFIG/OVR cho display, xem CMPWIKI crosscheck §C).
**Chưa bác bỏ được** — nhưng cũng **chưa có bất kỳ bằng chứng nào** ủng hộ khả năng ghi đè.

---

## H3 — Có nhiều gate độc lập trong VBIOS, GSP và phần cứng

### Evidence for

1. **Đã xác định được 4 gate riêng biệt, ở 4 tầng khác nhau:** đây là bằng chứng mạnh nhất cho H3, và H3 hiện là giả thuyết **được ủng hộ nhất**.
   ```
   G1 silicon  : 0x021C04 bit0 = 1                → gpuFuseSupportsDisplay_GM107 = FALSE
   G2 driver   : kern_disp.c:444                  → NV_ERR_NOT_SUPPORTED, KernelDisplay bị huỷ
   G3 GSP      : handler 0x04B9F5CC → ipVersion=0 → gpu.c:6033 hạ xuống DISPv0000
   G4 VBIOS    : NO_DISPLAY_SUBSYSTEM=1, DCB cnt=0 → không connector nào
   G5 board    : linh kiện DP/HDMI                 → CHƯA KIỂM
   ```
2. **G3 tồn tại độc lập với G1** — handler `0x04B9F5CC` (dispatch record `0x04061958`, cmd `0x20800A4B`, size `0x4`) có **nhánh code** trả `ipVersion = 0` khi `*(base+0x1F60)==0` hoặc `*(u8*)(base+0x6EA)==0`. Code bytes thật, xem `D1_GSP_DISPLAY_CALL_GRAPH.md` §6.2.
3. **Comment NVIDIA thừa nhận G3:** `gpu.c:6030` — *"0xFFFFFFFF ipver value happens when Display engines is disabled"*.
4. **G4 độc lập với G1:** DCB là dữ liệu tĩnh trong ROM; sửa được mà không đụng fuse.

### Evidence against

1. **G3 và G5 chưa từng được kích hoạt/đo.** "Gate tồn tại trong code" ≠ "gate đang đóng trên card này". Đây là phân biệt bắt buộc.
2. **G1 và G2 không thực sự độc lập** — G2 chỉ là *consumer* của G1. Tính độc lập thực chất nằm ở G1 vs G3 vs G4 vs G5.
3. **Không chứng minh được G3 đóng** vì control `DISPLAY_GET_IP_VERSION` chưa bao giờ được gửi.

### Remaining unknown

- `ipVersion` thật của CMP 40HX là gì? (nhánh 0/1/2/3/4) — **chưa đo**.
- Nếu vượt G1, G3 có mở không?
- G5 (board) có tồn tại không?

### Cần thêm bằng chứng gì

- **T-B1**: gọi `NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` (0x20800A4B) qua RM API userspace. Đây là **phép kiểm giá trị cao nhất còn lại** — nó trả lời trực tiếp "G3 đóng hay mở".
- Boardview/ảnh PCB → trả lời G5.

### Khả năng khôi phục nếu H3 đúng

**Điều kiện:** phải vượt **tất cả** gate cùng lúc. Không có đường tắt.
**Mức tin cậy:** **RẤT THẤP** — vì G1 (fuse read-only) nằm đầu chuỗi và không có đường phần mềm. Ngay cả khi G3/G4/G5 đều mở, G1 vẫn chặn.
**Điểm có ý nghĩa:** H3 giải thích **tại sao** các nỗ lực một-gate (sửa VBIOS, patch driver, tắt GSP) đều không đem lại display. Đây là giá trị chẩn đoán của H3, không phải giá trị khôi phục.

---

## H4 — Display hardware bị vô hiệu hoá hoặc không hoạt động trên die thực tế

### Evidence for

1. **CMP là SKU mining, NVIDIA chủ động cắt.** Die `TU106-100-A1` là die đầy đủ nhưng sản phẩm không bán kèm display.
2. **Ba dấu hiệu displayless độc lập cùng bật** (silicon fuse / VBIOS policy / DCB rỗng) — nhất quán với một quyết định sản phẩm ở mức die+board, không chỉ phần mềm.
3. **GP104/GP106-based CMP (30HX/50HX) chia sẻ cùng mô hình** — theo cmp.wiki, các CMP đều bị cắt bằng fuse ở nhà máy.
4. **Không có ai trong cộng đồng báo cáo khôi phục display cho bất kỳ CMP nào** (cmp.wiki: các dự án chỉ làm GR engine cho 90HX/70HX, không nói tới display).

### Evidence against

1. **Cùng mask silicon với RTX 2060S/2070** — về mặt thiết kế, block display **có**.
2. **Không có phép đo nào cho thấy PHY/SOR hỏng.** Thiếu bằng chứng hỏng ≠ có bằng chứng hỏng.
3. **`DCB entry_count = 0` chỉ là dữ liệu VBIOS**, không nói gì về silicon — đúng như prompt cảnh báo: *"Không coi thiếu DCB entry là bằng chứng SOR/PHY đã hỏng vật lý."*
4. **CMP 170HX theo cmp.wiki có "full GA100 die with parts switched off at the factory"** — tức fuse, không phải cắt bỏ vật lý. Nếu TU106 cùng mô hình thì hardware còn đó.
5. **Dự án `Icyoung/cmpunlocker tools/gr_unlock`** mở được *"the Graphics (GR) engine (3D, display output, OpenGL/Vulkan/CUDA graphics)"* trên CMP 90HX/70HX — chứng minh display **subsystem** trên dòng CMP không bị cắt vật lý ở mức die (ít nhất với GA10x). Nhưng **không** áp dụng cho 40HX (khác chip, khác driver nhánh).

### Remaining unknown

- CMP 40HX có bị **laser-cut** đường display ở metal layer không? — **chưa kiểm**.
- PHY/SOR có được probe được không nếu gate fuse mở? — **không đo được offline**.
- Board có linh kiện DP/HDMI không? — **chưa kiểm**.

### Cần thêm bằng chứng gì

- **T-D1**: đọc trực tiếp device-id/IP-version register PDISP qua BAR0 (cần địa chỉ register thật — hiện **BLOCKED**).
- Boardview + ảnh PCB.
- So sánh die shot TU106 CMP vs RTX 2060S (nếu có nguồn).

### Khả năng khôi phục nếu H4 đúng

**Điều kiện:** không có — hardware không hoạt động thì phần mềm vô nghĩa.
**Mức tin cậy khôi phục: KHÔNG.**
**Nhưng:** H4 hiện **chưa có bằng chứng trực tiếp**. Không được kết luận H4 là đúng chỉ vì các giả thuyết khác yếu.

---

## Đối chiếu chéo bốn giả thuyết

| | H1 VBIOS | H2 Fuse | H3 Nhiều gate | H4 Hardware hỏng |
|---|---|---|---|---|
| Evidence for (số mục) | 4 | 6 | 4 | 4 |
| Evidence against (số mục) | 5 | 4 | 3 | 5 |
| Bị bác bỏ hoàn toàn? | **Không** (chỉ bị chứng minh là *không đủ*) | **Không** | **Không** | **Không** |
| Được ủng hộ mạnh nhất? | — | **CÓ** (bằng chứng cứng nhất: giá trị silicon đo được) | **CÓ** (giải thích tốt nhất toàn bộ quan sát) | — |
| Khả năng khôi phục | THẤP | RẤT THẤP | RẤT THẤP | KHÔNG |
| Phép kiểm phân biệt | T-A2 | T-A1, T-A2, T-A3 | T-B1 | T-D1 |

### Quan hệ giữa các giả thuyết — không loại trừ nhau

Đây là điểm quan trọng: **H1, H2, H3, H4 KHÔNG loại trừ nhau.** Chúng có thể **đồng thời đúng**:

- H2 (fuse = 1) là **sự thật đo được**.
- H1 (VBIOS displayless) là **sự thật đo được**.
- H3 (nhiều gate) là **cấu trúc** giải thích cách H1+H2+H4 cùng tồn tại.
- H4 (hardware) là **khả năng chưa kiểm**.

Chúng chỉ khác nhau ở **cái nào là nguyên nhân gần (proximate cause)** và **cái nào là điều kiện tiên quyết (prerequisite)**.

**Xếp theo quan hệ nhân quả đã chứng minh:**

```
H2 (fuse, G1)  ──→  H3 gate G2 ──→ display tắt NGAY BÂY GIỜ
                         │
H1 (VBIOS, G4) ──────────┤ (song song, độc lập)
                         │
H3 gate G3 (GSP) ────────┤ (chưa kích hoạt)
                         │
H4 (hardware, G5) ───────┘ (chưa kiểm)
```

**Nguyên nhân gần của "display tắt ngay bây giờ" = H2/G1** (fuse = 1 → `kdispStatePreInitLocked` return).
**Điều kiện để khôi phục = phải vượt G1, rồi G3, rồi G4, rồi G5.**

---

## Tổng hợp: điều kiện thực sự cần để khôi phục display

Xếp theo thứ tự **bắt buộc**, không thể đảo:

| # | Điều kiện | Trạng thái hiện tại | Có đường phần mềm? |
|---|---|---|---|
| 1 | `0x021C04` bit0 đọc ra **0** | **= 1** | **KHÔNG** — `R-I4R`, 0 store toàn RM, GSP không chạm |
| 2 | `ipVersion != 0` từ GSP/hardware | **chưa đo** | Không rõ — cần T-B1 trước |
| 3 | DCB `entry_count > 0` với connector thật | **= 0** | Có (sửa ROM + flash) — nhưng **ngoài giới hạn an toàn**, và vô nghĩa nếu #1 chưa xong |
| 4 | Linh kiện DP/HDMI trên PCB | **chưa kiểm** | Không (phải hàn) |
| 5 | PHY/SOR hoạt động | **chưa kiểm** | Không rõ |

**Không có tổ hợp nào bỏ qua được #1.** Đó là chốt chặn tuyệt đối, và nó nằm ở silicon read-only.

---

## Điều KHÔNG được tuyên bố

| Tuyên bố | Vì sao sai |
|---|---|
| "Display không khôi phục được" | Chưa chứng minh. H4 chưa có bằng chứng trực tiếp; khả năng ghi đè fuse chưa bị bác bỏ. |
| "Chỉ cần sửa VBIOS" | Sai — gate fuse chặn trước, và còn ít nhất 3 gate nữa. |
| "Do GSP" | Sai — GSP không tham gia quyết định hiện tại (control display chưa từng gửi). |
| "Do `RmDisableDisplay`" | Sai — key không được set trên hệ thống này; host RM không chứa key. |
| "Fuse đã cháy cứng, không thể đảo" | Chưa chứng minh được là **raw OTP**; khe hở shadow-latch chưa đóng. |
| "Phần cứng display hỏng" | Chưa có phép đo nào. |
| "Do patcher/cmpunlocker thiếu" | Sai — patcher chỉ mở 3D; cmpunlocker chỉ mở compute. Cả hai không nhắm display. |
| "Do thiếu DCB entry" | Sai — DCB rỗng là hệ quả policy, và là gate **thứ tư**, không phải nguyên nhân gần. |

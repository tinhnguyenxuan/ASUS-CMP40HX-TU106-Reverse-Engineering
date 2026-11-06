# D1-E — PDISP / SOR / DP PHY / HDMI EVIDENCE

**GPU:** CMP 40HX, TU106-100-A1, PCI `10DE:1F0B`
**Source RM:** `615.78.08` @ `1a82fbfda8f321b056eb3568850f9316c5e465c5`
**Ngày:** 2026-11-06 · Chỉ offline + read-only

---

## 0. Câu hỏi phải trả lời

1. Các block PDISP/SOR/DP PHY/HDMI/display clock/power domain **có cơ sở hiện diện** trên TU106-100 không?
2. Phân biệt **thiết kế TU106 đầy đủ** với **tình trạng silicon thực tế** của CMP 40HX.
3. Phép quan sát read-only nào phân biệt được **không hiện diện** / **bị power-gate** / **bị software chặn**?
4. PCB có linh kiện đường DP/HDMI không?
5. Phân biệt **thiếu linh kiện PCB** với **display bị chặn trong GPU**.

---

## 1. Sự hiện diện của block — chứng minh từ source

### 1.1 Register definition headers có được ship cho Turing?

`src/common/inc/swref/published/turing/tu102/` chứa 37 file, **không có** `dev_disp.h`, `dev_sor.h`, `dev_dp.h`, `dev_hdmi.h`.

Nhưng display register definitions **nằm ở cây riêng theo IP version**, không theo chip:

```
src/common/inc/swref/published/disp/
    v02_04/dev_disp.h
    v03_00/dev_disp.h
    v04_00/dev_disp.h
    v04_01/dev_disp.h
    v04_02/dev_disp.h
    v05_01/dev_disp.h
    v05_02/dev_disp.h      ← dòng Turing
```

`disp/v05_02/dev_disp.h` = 33 dòng, là header **chỉ mục** trỏ tới các block con (`SOR`, `PHEAD`, `DAC`, `DP_LINK`…) — nghĩa là NVIDIA **có** định nghĩa register display cho lớp silicon này.

### 1.2 Kết luận về sự hiện diện thiết kế

| Block | Có trong thiết kế TU106? | Bằng chứng |
|---|---|---|
| PDISP (display engine) | **CÓ** | `disp/v05_02/` header; `NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` định nghĩa; `gpuInitDispIpHal_IMPL` (`gpu.c:6018`) có bảng HAL cho IP version |
| SOR | **CÓ** | DCB entry type `0x06` (DisplayPort) / `0x02` (TMDS) trên GeForce cùng die `TU106` |
| DP PHY | **CÓ** | GeForce 2060S cùng die có 1–2 entry DP hoạt động |
| HDMI/TMDS | **CÓ** | GeForce 2060S cùng die có 4–5 entry TMDS |
| Display clock | **CÓ** | `nvidia-drm` log `Changing default dispclk` **không** xuất hiện cho card này — nhưng code path tồn tại trong `kdispInitBrightcStateLoad` |
| Power/reset domain | **CÓ trong thiết kế** | `kdispStateInitLocked` có phần power-domain; chưa chạy tới |

**Đây là sự hiện diện THIẾT KẾ, không phải sự hiện diện ĐANG HOẠT ĐỘNG.** Hai thứ khác nhau.

---

## 2. Phân biệt thiết kế TU106 đầy đủ vs silicon CMP 40HX thực tế

| Lớp | TU106 đầy đủ (RTX 2060S/2070) | CMP 40HX (cùng die `TU106-100-A1`) |
|---|---|---|
| Die | TU106 | TU106-100-A1 — **cùng mask** |
| Số GPC/TPC/SM | 3 GPC × 6 TPC = 18 TPC / 36 SM | 17 TPC / 34 SM (GPC0=0x1F, GPC1=0x3F, GPC2=0x3F) |
| Display block trong thiết kế | Có | **Có** (cùng mask silicon) |
| `0x021C04` bit0 | *chưa đo trên GeForce TU106* | **1** (đo được) |
| `NO_DISPLAY_SUBSYSTEM` | **0** | **1** |
| DCB entry_count | **16** | **0** |
| Display hoạt động | Có | **Không** |

### 2.1 Cái KHÔNG được suy ra

> "CMP 40HX dùng cùng họ silicon với RTX 2060/2070 ⇒ display còn tốt."

Đây là suy luận **sai về逻辑**. Cùng mask thiết kế chỉ nói block **có thể** tồn tại. Nó không nói:
- fuse display trên die cụ thể có bị cháy hay không
- PHY có được laser-cắt hay không
- board có route ra connector hay không

Đúng như prompt yêu cầu: **không suy ra chức năng display còn tốt chỉ vì cùng họ silicon.**

---

## 3. Phép quan sát read-only để phân biệt ba trạng thái

Câu hỏi: **không hiện diện** vs **bị power-gate** vs **bị software chặn**.

### 3.1 Trạng thái thực tế của CMP 40HX: đã xác định được là **bị software chặn**

Đây là kết quả mạnh nhất hiện có, và **không cần** phân biệt hai trạng thái kia:

```
kern_disp.c:444   if (!gpuFuseSupportsDisplay_HAL(pGpu)) return NV_ERR_NOT_SUPPORTED;
```

Chuỗi dừng **trước** khi bất kỳ register display nào bị chạm. Không có `PDISP` write, không có `SOR` power-up, không có PHY training. Vậy **ở thời điểm hiện tại**, nguyên nhân gần là **software block**, không phải power-gate hay vắng mặt — vì cả hai trạng thái kia **chưa từng được kiểm tra**.

### 3.2 Ba phép quan sát read-only có thể phân biệt — CHƯA CHẠY

| # | Phép quan sát | Phân biệt | Khả thi? |
|---|---|---|---|
| **T-D1** | Đọc `NV_PDISP` device-id / IP-version register trực tiếp qua BAR0 (không qua driver) | Nếu trả giá trị hợp lệ (`0x05xxxxxx`) ⇒ block **hiện diện** trong silicon. Nếu trả `0xFFFFFFFF`/0 ⇒ không hiện diện | **CẦN XÁC ĐỊNH ĐỊA CHỈ.** Header `disp/v05_02/dev_disp.h` chỉ 33 dòng, không chứa địa chỉ register on-chip cụ thể. **BLOCKED** |
| **T-D2** | Đọc PDISP clock/power-domain status register (`NV_PDISP_..._STATUS`) | Phân biệt power-gate vs active | **BLOCKED** cùng lý do |
| **T-D3** | Đọc `NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` qua RM API userspace | GSP trả nhánh `0..4`; nhánh 0 ⇒ display không khả dụng | **KHẢ THI** nhưng cần client NV2080 tự viết (nvidia-smi không expose). Đây là **T-B1** bên D1-GSP |

### 3.3 Vì sao T-D1/T-D2 bị BLOCKED — trung thực

Các địa chỉ register display (`NV_PDISP_*`, `NV_SOR_*`, `NV_DP_LINK_*`) **không có** trong phần swref công bố của repo open-gpu-kernel-modules. Chỉ có header chỉ mục. Không được đoán địa chỉ và đọc — đọc sai vùng có thể chạm block khác.

Đây là **giới hạn thật**, không phải UNKNOWN suông: nêu rõ thiếu gì và cần gì.

---

## 4. PCB — có linh kiện đường DP/HDMI không?

### 4.1 Trạng thái: CHƯA KIỂM

Không có boardview hoặc ảnh mặt sau CMP 40HX trong workspace. Các file có:
```
input/ASTRA_CMP40HX_HANDOFF/01_BOARDVIEW/CMP40HX_Strap_Report.docx   (strap, không phải display)
input/ASTRA_CMP40HX_HANDOFF/02_PCB_PHOTOS/ANNOTATED/CMP40HX_PORTS_PHOTO_ANNOTATED.jpg
input/ASTRA_CMP40HX_HANDOFF/02_PCB_PHOTOS/ANNOTATED/CMP40HX_STRAP_PHOTO_ANNOTATED.jpg
```
`CMP40HX_PORTS_PHOTO_ANNOTATED.jpg` có thể chứa thông tin cổng — **chưa phân tích**.

### 4.2 So sánh với CMP khác — dữ liệu từ cmp.wiki

> "Like the 170HX, the 90HX ships with the capacitors on the PCIe lines missing. Without them it runs PCIe 2.0 x4; with them x16."

Đây là **tụ trên đường PCIe**, không phải linh kiện display. Không suy được gì cho DP/HDMI.

Với CMP 170HX: *"Every CMP 170HX carries a full GA100 die with parts of it switched off at the factory"* — fuse tắt, không phải cắt linh kiện.

**Không có dữ liệu PCB display cho bất kỳ CMP nào trong các nguồn đã đọc.**

### 4.3 Phân biệt "thiếu linh kiện PCB" với "display bị chặn trong GPU"

Đây là hai nguyên nhân **hoàn toàn độc lập**, và có thể cùng tồn tại:

| | Thiếu linh kiện PCB | Display bị chặn trong GPU |
|---|---|---|
| Tầng | Board (mạch in, connector, ESD, filter, tụ AC-coupling) | Die / fuse / firmware |
| Triệu chứng | Có CRTC, có connector trong sysfs, nhưng không ra tín hiệu — hoặc không có connector vật lý | Không có CRTC, không có connector, driver từ chối init |
| CMP 40HX hiện tại | **CHƯA KIỂM** | **ĐÃ XÁC NHẬN** — không CRTC (`Cannot find any crtc or sizes`), DCB `cnt=0` |

**Kết luận §4:** hiện tại chỉ chứng minh được **display bị chặn trong GPU**. Việc PCB có linh kiện hay không **hoàn toàn chưa biết**, và **không thể** suy ra từ dữ liệu phần mềm.

---

## 5. Điều đã loại trừ ở lớp D

| Giả thuyết | Trạng thái |
|---|---|
| PDISP/SOR/PHY **không tồn tại trong thiết kế TU106** | **BÁC BỎ** — GeForce cùng die có display hoạt động; header `disp/v05_02` tồn tại |
| Display bị chặn **chỉ** vì thiếu DCB entry | **BÁC BỎ** — DCB rỗng là *hệ quả* của quyết định sản phẩm; gate fuse chặn trước và độc lập |
| Display bị chặn **chỉ** vì fuse, hardware còn tốt | **CHƯA CHỨNG MINH** — chưa có phép đo nào cho thấy PHY/SOR hoạt động được |
| Hardware display **hỏng vật lý** | **CHƯA CHỨNG MINH** — không có phép đo nào cho thấy hỏng |

⇒ **Cả hai chiều đều chưa chứng minh.** Đây là trạng thái trung thực của lớp D.

---

## 6. Điều kiện để lớp D tiến thêm

| Cần | Để làm gì |
|---|---|
| Địa chỉ `NV_PDISP_*` register thật cho Turing (từ tài liệu NVIDIA không công khai, hoặc dump từ một RTX 2060S) | Chạy T-D1: đọc trực tiếp device-id PDISP, phân biệt hiện diện vs vắng mặt |
| Client NV2080 userspace gọi `DISPLAY_GET_IP_VERSION` | Chạy T-B1: biết GSP trả nhánh nào |
| Boardview / ảnh mặt sau CMP 40HX | Xác định linh kiện DP/HDMI |
| Một RTX 2060S vật lý để đọc đối chứng | Có baseline cho mọi phép đo register display |

---

## 7. Hash

| Đối tượng | Giá trị |
|---|---|
| Source RM | `615.78.08` @ `1a82fbfda8f321b056eb3568850f9316c5e465c5` |
| `disp/v05_02/dev_disp.h` | 33 dòng, header chỉ mục |
| GeForce TU106 đối chứng | `dc5395dd…` (CMP) vs `c468ac52…` (2060S #246948) |
| `nvidia-drm` log | `nvidia 0000:03:00.0: [drm] Cannot find any crtc or sizes` |

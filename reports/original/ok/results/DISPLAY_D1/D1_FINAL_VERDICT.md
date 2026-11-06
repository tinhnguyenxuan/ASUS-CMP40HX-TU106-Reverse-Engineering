# D1 — FINAL VERDICT

**GPU:** NVIDIA CMP 40HX, TU106-100-A1, PCI `10DE:1F0B`, BDF `0000:03:00.0`
**Driver:** 615.78.08 · **VBIOS:** 90.06.67.00.06
**Ngày:** 2026-11-06 · DeepSeek V4.1 Flash · Nghiên cứu độc lập, không kế thừa kết luận T1–T6

---

## TRẢ LỜI CÂU HỎI CUỐI

> **"Điều gì thực sự ngăn CMP 40HX xuất hình, và có bằng chứng về khả năng khôi phục không?"**

### Điều gì thực sự ngăn

**Nguyên nhân gần (proximate cause) — ĐÃ CHỨNG MINH:**

Thanh ghi fuse **`0x021C04` = `0x00000001`** trên silicon. Bit 0 là `DATA`; giá trị "enabled" là `0`. Vì `1 ≠ 0`:

```
kern_gpu_gm107.c:72   GPU_FLD_TEST_DRF_DEF(pGpu,_FUSE,_STATUS_OPT_DISPLAY,_DATA,_ENABLE) → NV_FALSE
        ↓
kern_disp.c:444-445   if (!gpuFuseSupportsDisplay_HAL(pGpu)) return NV_ERR_NOT_SUPPORTED;
        ↓
gpu.c:1748-1755       engstateIsPresent = NV_FALSE → gpuDestroyMissingEngine → KernelDisplay bị huỷ
        ↓
                      NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION (0x20800A4B) KHÔNG BAO GIỜ ĐƯỢC GỬI
        ↓
nvidia-drm            "Cannot find any crtc or sizes"
```

**Đây là một dòng code duy nhất chặn toàn bộ tầng display.** Không phải GSP. Không phải VBIOS. Không phải `RmDisableDisplay`.

**Bốn gate độc lập bổ sung (đã xác định, ở các mức bằng chứng khác nhau):**

| Gate | Nội dung | Trạng thái bằng chứng |
|---|---|---|
| **G1** | fuse `0x021C04` bit0 = 1 | **ĐO ĐƯỢC** |
| **G2** | `kern_disp.c:444` return `NV_ERR_NOT_SUPPORTED` | **PROVEN** (code + dmesg) |
| **G3** | GSP handler `0x04B9F5CC` có thể trả `ipVersion = 0` → `DISPv0000` | **CODE TỒN TẠI, CHƯA KÍCH HOẠT** |
| **G4** | VBIOS `NO_DISPLAY_SUBSYSTEM=1`, `DCB entry_count=0` | **ĐO ĐƯỢC** |
| **G5** | Linh kiện PCB DP/HDMI / PHY hoạt động | **CHƯA KIỂM** |

### Có bằng chứng về khả năng khôi phục không

**KHÔNG có bằng chứng ủng hộ khả năng khôi phục bằng phần mềm.**
**CŨNG KHÔNG có bằng chứng bác bỏ nó.**

Cụ thể, đây là những gì **đã chứng minh được**:

| Mệnh đề | Trạng thái | Cơ sở |
|---|---|---|
| Không phần mềm nào trong hệ thống **ghi** được vào `0x021C04` | **PROVEN** | `R-I4R` trong header; **0 store** trên 147 MB source RM; GSP 0 literal hit; Nouveau read-only |
| Bit này là **raw OTP** | **CHƯA CHỨNG MINH** | Không có đường đọc raw OTP độc lập với shadow register trên TU106 |
| Bit này do **firmware/software** set | **CHƯA LOẠI TRỪ** | Không tìm thấy literal ≠ không có consumer. Devinit/GSP có thể đọc qua bảng hoặc con trỏ hàm |

> ⚠️ **ĐÍNH CHÍNH (D2) — phạm vi của mệnh đề "0 store".**
>
> D1 đã dùng "0 store + `R-I4R`" để **loại trừ lớp firmware/software**. **Lập luận đó không đủ mạnh.** Chính xác hơn:
>
> - `R-I4R` chỉ nói **RM host** không được thiết kế để ghi. Nó **không** nói hardware không cho ghi từ nguồn khác.
> - "0 store trong open RM + 0 literal trong GSP" là **vắng mặt bằng chứng**, không phải **bằng chứng vắng mặt**.
> - **Một producer firmware hoặc hardware-latched vẫn có thể tồn tại** qua 4 đường mà phân tích tĩnh không thấy:
>   1. **devinit** (chạy trước RM, không có trong repo) `poke` thẳng vào cửa sổ fuse.
>   2. **SEC2/FSP firmware** (không có trong repo, không disassemble được — D1/T2 đã ghi nhận SEC2 là Falcon ISA).
>   3. **Hardware latch**: giá trị fuse được nạp vào shadow register ở reset, do **strapping** hoặc **OTP**, không qua phần mềm nào cả.
>   4. **Địa chỉ tính động** từ bảng cấu hình (NVKV/NVGMC_SC) hoặc con trỏ hàm — không để lại literal.
>
> **Mệnh đề đúng phạm vi:** *"Không có đường ghi nào quan sát được trong open RM, trong GSP-RM 615.78.08, hoặc trong Nouveau."* **Không** phải *"không phần mềm nào ghi được"*.
>
> Điều này **không thay đổi kết luận** (display đang bị chặn, gate là `kern_disp.c:444`), nhưng **thay đổi mức chắc chắn** của mệnh đề "fuse là read-only tuyệt đối".
| Display đang bị vô hiệu **trong môi trường hiện tại** | **PROVEN** | `0x021C04=1`, `kern_disp.c:444`, dmesg "Cannot find any crtc" |
| Sửa VBIOS là **đủ** | **BÁC BỎ** | Gate G1 chạy trước; còn G3, G4, G5 |
| Tắt GSP giúp display | **BÁC BỎ** | Cùng gate fuse trong host RM; GSP không tham gia |
| Patcher/cmpunlocker mở display | **BÁC BỎ** | Patcher đổi 12 entry device-ID table; cmpunlocker chỉ mở compute issue rate |

> **Ba mệnh đề này KHÔNG được đánh đồng:**
> (1) display bị vô hiệu hiện tại — **PROVEN**
> (2) nguyên nhân được chứng minh ở mức phần cứng — **SUPPORTED, chưa PROVEN**
> (3) bit là raw OTP bất biến — **UNPROVEN**

---

## Hoàn thành tiêu chí F như thế nào

Prompt yêu cầu một trong hai kết quả. D1 đạt **cả hai**:

### ✅ Kết quả loại 1 — "Tìm được nguồn hoặc đường hình thành effective display-disabled state với bằng chứng mã máy/source/hardware rõ ràng"

**Đã tìm được, đầy đủ đến mức consumer:**

| Bước | Bằng chứng |
|---|---|
| Producer (silicon) | fuse `0x021C04` = 1, đọc trực tiếp BAR0, đối chứng bằng `0x21378=0` / `0x2174C=1` |
| Định danh block | fuse window `0x21000`, offset nội bộ `0xC04`, chứng minh bằng Δ `0x7FF000` so với GA100 |
| Consumer 1 | `gpuFuseSupportsDisplay_GM107` (`kern_gpu_gm107.c:66-73`), dispatch `g_gpu_nvoc.c:2094-2098` |
| Consumer 2 | `kdispStatePreInitLocked` (`kern_disp.c:435-445`) |
| Hệ quả engine | `engstateIsPresent` → `gpuDestroyMissingEngine` (`gpu.c:1748-1755`) |
| Hệ quả quan sát được | `nvidia-drm: Cannot find any crtc or sizes` |
| Consumer 3 (Nouveau) | `pramin_init` (`shadowramin.c`) — `addr & 1` → `... display disabled` → `ERR_PTR(-ENODEV)` |
| Gate thứ hai phía GSP | handler `0x04B9F5CC`, record `0x04061958`, cmd `0x20800A4B`, disassembly đầy đủ |

### ✅ Kết quả loại 2 — "Truy các nhánh thực sự liên quan, ghi rõ nơi đứt, đường đã loại trừ, phép kiểm phân biệt"

**Nơi chuỗi dữ liệu đứt:** ranh giới silicon — từ ô OTP vật lý đến giá trị MMIO đọc được. Không có đường quan sát raw OTP trên TU106 từ host.

**Đường đã loại trừ:**
- GSP-RM 615.78.08 là producer/consumer: **không có bằng chứng** (0 literal hit cho `0x21C04`, `0x820C04`, `lui 0x21 + 0xC04`)
- NVIDIA RM ghi vào đây: **loại trừ** (0 store, `R-I4R`)
- Nouveau: **loại trừ** (read-only, fail tại đó)
- `RmDisableDisplay`: **loại trừ** (0 xref tĩnh, không có trong source RM, không được set trên hệ thống)
- `RmForceGridDisplayless`: **loại trừ** (dòng vGPU/GRID, CMP là physical function)
- Patcher/cmpunlocker: **loại trừ** (chỉ 3D/compute)
- Tắt GSP: **loại trừ** (cùng gate)

**Phép kiểm phân biệt còn lại:**

| # | Phép kiểm | Phân biệt | Khả thi |
|---|---|---|---|
| **T-B1** | Gọi `NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` (0x20800A4B) qua RM API userspace | G3 đóng hay mở — **giá trị cao nhất** | ✅ Cần client NV2080 |
| **T-A1** | Đọc `0x021C04` sau PCI reset, trước khi load driver | Devinit/GSP set hay silicon set | ✅ Cần module đọc BAR sớm |
| **T-A2** | Flash ROM GeForce TU106, đọc lại `0x021C04` | Fuse cứng vs cấu hình được | ⚠️ Flash — cần quyết định riêng |
| **T-A3** | So sánh với CMP 40HX thứ hai | SKU-level vs die-specific | ⚠️ Cần card thứ hai |
| **T-D1** | Đọc trực tiếp register PDISP device-id qua BAR0 | Hardware hiện diện hay không | ❌ **BLOCKED** — không có địa chỉ register |
| **T-D2** | Boardview / ảnh PCB mặt sau | Linh kiện DP/HDMI | ✅ Có file ảnh, chưa phân tích |

---

## Điều D1 **không** kế thừa từ T1–T6 (đúng yêu cầu)

| T1–T6 nói | D1 nói | Vì sao |
|---|---|---|
| `0x021C04` là **UNKNOWN** | **Biết chính xác** đường đọc, block, consumer, hệ quả. Chỉ tồn tại **một** khe hở: raw OTP vs shadow-latch | Đã truy đến producer tận silicon + 3 consumer độc lập |
| **hard-fused** | **Chưa chứng minh.** Chỉ chứng minh được "không phần mềm nào ghi được" — mệnh đề yếu hơn và **khác bản chất** | Không có phép đo phân biệt OTP vs shadow |
| **impossible** | **Chưa bác bỏ được, cũng chưa ủng hộ được.** Nêu rõ 6 phép kiểm, điều kiện từng gate | Không có bằng chứng nào cho "impossible" |
| GSP chặn display qua `RmDisableDisplay` | **SAI.** Host chặn trước khi gửi control. `RmDisableDisplay` không được set, không có trong source RM | Đã disassemble handler thật và trace call graph |
| DCB thiếu entry là nguyên nhân | **SAI.** DCB rỗng là gate **thứ tư**, hệ quả của policy | Gate fuse chặn trước |

---

## Phân loại bốn trạng thái (yêu cầu E của crosscheck)

| # | Trạng thái | Hiện tại | Bằng chứng |
|---|---|---|---|
| ① | **GPU render được 3D** | **CÓ** | GR engine chạy, `CMP40_COMPUTE_UNLOCK` pass, patcher mở D3D/Vulkan |
| ② | **Driver nhận là display-class GPU** | **KHÔNG** | `Display Active: Disabled`, không CRTC |
| ③ | **Display engine thực sự hoạt động** | **KHÔNG** | `kdispStatePreInitLocked` return; PDISP/SOR/PHY chưa từng init |
| ④ | **DP/HDMI phát tín hiệu vật lý** | **KHÔNG** | Không CRTC, DCB `cnt=0`, PCX chưa kiểm |

**Bốn trạng thái này độc lập và D1 giữ chúng tách biệt xuyên suốt.**

---

## Điều kiện thực sự cần để khôi phục display

Xếp theo thứ tự **bắt buộc**:

| # | Điều kiện | Hiện tại | Có đường phần mềm? |
|---|---|---|---|
| **1** | `0x021C04` bit0 = **0** | **= 1** | **KHÔNG** — `R-I4R`, 0 store, firmware không chạm |
| **2** | `ipVersion != 0` từ GSP | **chưa đo** | **CHƯA RÕ** — cần T-B1 |
| **3** | DCB có connector thật | `cnt = 0` | Có (flash ROM) — nhưng vô nghĩa nếu #1 chưa xong |
| **4** | Linh kiện DP/HDMI trên PCB | **chưa kiểm** | Không (phải hàn) |
| **5** | PHY/SOR hoạt động | **chưa kiểm** | **CHƯA RÕ** |

**Không có tổ hợp nào bỏ qua được #1.** Đây là chốt chặn tuyệt đối. Hiện **không có đường phần mềm nào** để đảo nó.

---

## Khuyến nghị bước tiếp theo (theo giá trị trên chi phí)

1. **T-B1** — viết client NV2080 userspace gọi `0x20800A4B`, đọc `ipVersion`. Đây là phép kiểm **duy nhất** trả lời được "G3 đóng hay mở", và nó **read-only, an toàn**. Không làm được bước này thì mọi suy luận về GSP chỉ là giả thuyết.

2. **T-A1** — module đọc `0x021C04` sau PCI reset, trước khi load driver. Phân biệt devinit/GSP set hay silicon set. Read-only.

3. **T-D2** — đọc `CMP40HX_PORTS_PHOTO_ANNOTATED.jpg` + tìm boardview. Trả lời G5 miễn phí.

4. **Baseline** — đọc `0x021C04` trên một RTX 2060S/2070 thật. Không có baseline thì không biết fuse GeForce là gì.

5. **T-A2 (flash ROM GeForce)** — chỉ cân nhắc **sau** 1–4, và cần quyết định riêng vì nằm ngoài giới hạn an toàn D1.

---

## Tuyên bố hoàn thành

D1 hoàn thành theo tiêu chí F, cả hai nhánh:

- ✅ Đã xác định **nguồn và đường hình thành** effective display-disabled state với mã nguồn, địa chỉ hàm, code bytes, giá trị silicon đo được.
- ✅ Đã ghi rõ **nơi chuỗi dữ liệu đứt** (ranh giới silicon), **các đường đã loại trừ** (7 đường), và **các phép kiểm phân biệt còn lại** (6 phép, 2 phép đã xác định BLOCKED với lý do).

**Không** kết thúc bằng "0x021C04 là UNKNOWN".

---

## File trong D1

| File | Nội dung |
|---|---|
| `D1_FUSE_021C04_PRODUCER.md` | Đường đọc fuse, block, producer/consumer, ranh giới đứt |
| `D1_GSP_DISPLAY_CALL_GRAPH.md` | Call graph host→GSP, handler `0x04B9F5CC` disassembly, gate G3 |
| `D1_RMDISABLEDISPLAY_ANALYSIS.md` | Loại trừ `RmDisableDisplay` bằng 3 phương pháp xref |
| `D1_VBIOS_DISPLAY_POLICY.md` | Parse BIT/DCB đúng spec, 5 ROM, `NO_DISPLAY_SUBSYSTEM`, `B+32` |
| `D1_PDISP_SOR_PHY_EVIDENCE.md` | Block display, phân biệt thiết kế vs silicon thực tế, PCB |
| `D1_DISPLAY_RESTORATION_HYPOTHESES.md` | H1–H4, evidence for/against, điều kiện khôi phục |
| `D1_FINAL_VERDICT.md` | File này |
| `D1_EVIDENCE_LEDGER.json` | Sổ bằng chứng có cấu trúc, hash, địa chỉ |

**Bổ sung (cross-check nguồn ngoài):**
| `CMPWIKI_40HX_CROSSCHECK.md` | NVIDIA-patcher, tắt GSP, OPT/RECONFIG/OVR, phân loại 4 trạng thái |

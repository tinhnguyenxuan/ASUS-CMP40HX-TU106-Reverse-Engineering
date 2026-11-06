# HYPOTHESIS MATRIX — Nguyên nhân trần 1905 MHz

Câu hỏi trung tâm: **tại sao GPU dừng ở ~1905 MHz?**

Đo thực tế (E07, `scripts/sample_load.py`): dưới tải 84 s, **20/20 mẫu ở
1875–1905 MHz**, 15 mẫu ở đúng **1890**, 1 mẫu **1905**, 4 mẫu **1875**.
Công suất đỉnh **149.7 W** với **PL 184 W**. Nhiệt độ đỉnh **68 °C**.
Từ giây 32.4, `throttle = 0x0000000000000000` — **không limiter nào**.

---

## H1 — 1905 MHz là clock cap trong VBIOS

**Ủng hộ:**
- `nvidia-smi -q` báo `Max Clocks: SM 2100 MHz` (đây là `clocks.max.sm`, không
  phải cap thực tế).
- Clock dừng rất ổn định ở 1890, chỉ nhích 1905 một lần ở mẫu đầu.
- Trong 40 bảng `PERF_PTRS` có nhiều `u16` tần số (E-ledger, `fix12.py`):
  `7000 MHz` (0x1B58) xuất hiện 9 lần, `5000` (0x1388) 4 lần, `3300` (0x0CE4)
  2 lần, `1697` (0x06A1) 3 lần, `1638` (0x0666) 1 lần, `1942` (0x0796),
  `860` (0x035C), `620` (0x026C), `405` (0x0195).

**Phản bác:**
- **Không có giá trị `1890` (0x0762) hay `1905` (0x0771) ở bất kỳ đâu** trong
  40 bảng PERF_PTRS, kể cả quét mọi offset chẵn/lẻ.
- Các `u16` tìm thấy đều là **tần số memory (7000/5000/3300 MHz GDDR6)** và
  **tần số video (405/620/860/1638/1697)**, không phải GPC clock cap.

**Thiếu bằng chứng:** chưa dump hết nội dung 40 bảng để tìm cap dạng PLL
divisor; chưa đối chiếu `CLOCK_PTRS` (`0x2D65F`, 14 domain × 19 B).

**Độ tin: THẤP.**

**Phép thử phân biệt tiếp:** decode `CLOCK_PTRS[0]` 14 domain × 19 B sang
(MHz, divider, VCO); nếu một domain cho đúng 1890 thì H1 đúng.

---

## H2 — Giới hạn do voltage cap

**Ủng hộ:**
- ROM gốc: REL = 1068.75 mV, ALT = 1093.75 mV, OV = 1125 mV.
- Nâng REL/ALT lên 1125 mV (T4) làm **tắt hoàn toàn** `Board Limit` và
  `Reliability` sau ~32 s dưới tải.

**Phản bác:**
- Với T4 (1125 mV, cả 2 limiter `Not Active`): **clock vẫn 1890 MHz**,
  công suất chỉ **149 W** (PL 184 W). Nếu trần là điện áp thì khi đã ở trần
  điện áp cao nhất (bằng OV), clock phải tăng — nhưng không tăng một bậc.
- Điện áp NVVDD runtime **không đọc được** từ userspace (4 đường đã thử âm
  tính: NVML không có `nvmlDeviceGetVoltage`, BAR0 register đề ánh xạ không
  khớp) → **không có bằng chứng trực tiếp** điện áp thực tế là bao nhiêu.

**Thiếu bằng chứng:** giá trị NVVDD thực tại thời điểm 1890 MHz. Không đo được
bằng phần mềm.

**Độ tin: THẤP** (đã bị phản bác mạnh bởi phép đo T4).

**Phép thử phân biệt tiếp:** đo NVVDD bằng phần cứng (đồng hồ vạn năng trên
tụ output VRM) trong lúc chạy tải — cần can thiệp vật lý.

---

## H3 — GPU bị giới hạn bởi V/F table

**Ủng hộ:**
- VFE có **150 slot**, **84 slot có hệ số góc khác 0** (không phải đường phẳng
  như báo cáo trước kết luận).
- `var[7]` = **1981.23 .. 2335.54** — dải MHz. Có **56/150 slot** dùng `var=7`.
- `var[13]` = **450,000 .. 1,243,750** — dải µV. Có **8/150 slot** dùng `var=13`.
- Với T4, slot[0]/[1] (REL/ALT) đổi từ hằng 1068.75/1093.75 → 1125 mV, và
  **đúng là** clock nhích lên: mẫu đầu 1905 MHz thay vì 1890 của ROM gốc.
- `nvidia-smi -lgc 1500` → 1500 MHz, `-lgc 1700` → 1710 MHz (đo phiên trước):
  clock control hoạt động thật, nghĩa là có đường đi qua V/F.

**Phản bác:**
- Nếu trần là V/F table thì VFE phải có một slot cho ra **1890** khi
  `x = 1125000 µV` (var=13). **Không slot nào trong 8 slot `var=13` cho
  y ∈ [1800, 2000]**:
  ```
  slot[  8] c1=0.001669 c2=-4.0e-10  -> y(1125000) = 1278.3
  slot[ 19] c1=0.009700 c2=-2.8e-09  -> y(1125000) = 7322.3
  slot[ 25] c1=0.001377 c2=0         -> y(1125000) =  569.6
  slot[ 28] c1=-0.000386             -> y(1125000) =  -31.5
  slot[ 11/23/26] hang so            -> 500000 / 700000 / 1050000
  slot[ 12] hang so 405
  ```
- Điện áp thực tế **không đọc được** nên không thể chạy ngược phương trình.
- Đơn vị đã đúng (µV, x = 1,125,000 — không phải 1068.75 như báo cáo trước),
  kết quả vẫn không ra MHz. Nghĩa là **không có slot VFE nào biến điện áp
  thành tần số**; quan hệ đó nằm ở nơi khác (PLL/PMU).

**Thiếu bằng chứng:** bảng sinh PLL từ điện áp; ngưỡng `var[7]` thực tế đang
dùng.

**Độ tin: TRUNG BÌNH** — có đường đi qua V/F (bằng chứng `-lgc` + T4 nhích),
nhưng VFE **không** phải nơi phát sinh trần.

**Phép thử phân biệt tiếp:** với T4 đang nạp, sweep `nvmlDeviceSetGpcClkVfOffset`
`+150 / +200 / +220 / +240` và ghi lại clock — nếu vượt 1905 thì trần nằm trong
đường VF offset; nếu vẫn 1890 thì trần nằm ở PLL/PMU.

---

## H4 — GSP-RM hoặc PMU áp đặt giới hạn riêng

**Ủng hộ:**
- GSP-RM là **ELF RISC-V 22.9 MB** với **17 MB code** (`.section_task_rm_elf_text_instance`).
- Có **923 registry key**; **139 entry descriptor** đã parse, gồm
  `PERF_CF_CONTROLLER_GPC_MAX` (id 21, module 273), `_DRAM_MAX` (id 20),
  `_NVD_MAX` (id 23) — **đây chính là bộ điều khiển trần GPC**.
- `OVERCLOCK` xuất hiện 4 lần, `TGP` 3 lần, `OCP` 6 lần trong string.
- Không có XREF cứng → key tra theo tên lúc runtime, đúng kiểu một giới hạn
  chính sách do firmware quyết định.

**Phản bác:**
- `PERF_CF_CONTROLLER_GPC_MAX` id 21 là **tên policy**, chưa chứng minh là cap
  cho CMP 40HX.
- Chưa có phép đo nào cho thấy GSP ghi đè lên VBIOS.

**Thiếu bằng chứng:** giá trị thực của policy 21; disasm hàm consume policy.

**Độ tin: TRUNG BÌNH** — đây là ứng viên mạnh nhất về mặt cấu trúc, nhưng
chưa có phép thử nào phân biệt được.

**Phép thử phân biệt tiếp:** set `PERF_CF_CONTROLLER_GPC_MAX` qua
`NVreg_RegistryDwords` và đo — nhưng đây là **thay đổi cấu hình**, cần phê
duyệt riêng (mục 8).

---

## H5 — Giới hạn liên quan P-state hoặc boost policy

**Ủng hộ:**
- P-state leo đúng P8 → P0 dưới tải, `utilization 100%`.
- `PSTATE` xuất hiện 32 lần trong GSP-RM.

**Phản bác:**
- Đã ở **P0** (P-state cao nhất) mà clock vẫn kẹp → trần nằm **trong** P0,
  không phải do chọn sai P-state.
- `nvidia-smi -q -d PERFORMANCE` báo `Applications Clocks Setting: Not Active`.

**Thiếu bằng chứng:** bảng P-state đầy đủ với clock từng mức.

**Độ tin: THẤP** (bị phản bác bởi "đã ở P0").

**Phép thử phân biệt tiếp:** decode `CLOCK_PTRS` + các bảng `PERF[29..35]`
(`0x56222..0x5636D`) — nhóm này chứa nhiều `u16` memory clock, nghi là
bảng P-state.

---

## H6 — GPU không ổn định ở xung cao hơn

**Ủng hộ:**
- Lịch sử: ép `+367 MHz` (tới ~2017 MHz) gây **màn hình đen + tự restart**.
- `Reliability: Active` bật ở ROM gốc dưới tải (bit 10, `0x400`).
- Cờ `Reliability` là **giám sát lỗi tính toán** — bật nghĩa là firmware phát
  hiện sai số ở mức xung/điện áp hiện tại.

**Phản bác:**
- Với **T4**, `Reliability` chuyển sang `Not Active` sau 32 s mà **không crash,
  không artifact** — nghĩa là 1125 mV là mức ổn định trên card này.
- Nếu trần do không ổn định, nó sẽ **dao động** theo nhiệt độ/tải. Thực tế
  clock **rất ổn định**: 15/20 mẫu đúng 1890 MHz, chỉ tụt 1875 khi nhiệt lên 68 °C.

**Thiếu bằng chứng:** log lỗi ECC/SM; giá trị `Reliability` counter.

**Độ tin: THẤP.**

**Phép thử phân biệt tiếp:** chạy stress có kiểm tra kết quả (memtestG80,
`nvidia-smi -q -d ECC`) ở 1890 để xem có lỗi im lặng không.

---

## Bảng so sánh

| | Giả thuyết | Ủng hộ | Phản bác | Thiếu | Độ tin |
|---|---|---|---|---|---|
| H1 | Clock cap trong VBIOS | 40 bảng có u16 MHz; clock ổn định 1890 | **Không có 1890/1905** ở mọi offset; u16 đều là mem/video clock | decode `CLOCK_PTRS` (PLL) | **THẤP** |
| H2 | Voltage cap | T4 tắt được Board Limit + Reliability | T4 @1125 mV **vẫn 1890 MHz** @149 W | NVVDD runtime (không đọc được) | **THẤP** |
| H3 | V/F table | 84/150 slot có slope; T4 nhích lên 1905; `-lgc` hoạt động | 8 slot `var=13` **không cho 1800–2000** ở 1,125,000 µV | bảng sinh PLL | **TRUNG BÌNH** |
| H4 | GSP-RM/PMU policy | 17 MB code; `PERF_CF_CONTROLLER_GPC_MAX` id 21; 139 descriptor | chưa chứng minh là cap cho SKU này | giá trị policy 21 | **TRUNG BÌNH** |
| H5 | P-state/boost | PSTATE 32 string | **đã ở P0** mà vẫn kẹp | bảng P-state | **THẤP** |
| H6 | Không ổn định | +367 MHz từng crash; `Reliability: Active` ở ROM gốc | T4 sạch limiter, không artifact, clock rất ổn định | ECC log | **THẤP** |

---

## Kết luận có bằng chứng vs chưa giải quyết

### Đã loại bỏ (bằng đo trực tiếp)
- **Trần không phải power limit**: 149 W < PL 184 W.
- **Trần không phải nhiệt**: 68 °C, `HW Thermal Slowdown: Not Active`.
- **Trần không phải limiter tổng quát**: `throttle = 0x0000000000000000` mà
  clock vẫn kẹp.
- **Trần không phải P-state**: đã ở P0.

### Còn mở
Hai ứng viên còn sống, **chưa phân biệt được bằng phép đo read-only**:
1. **H3** — đường V/F (có bằng chứng gián tiếp: T4 nhích 1905, `-lgc` chạy được).
2. **H4** — policy GSP-RM `PERF_CF_CONTROLLER_GPC_MAX` (có cấu trúc nhưng chưa
   có giá trị).

Phép thử phân biệt rẻ nhất và an toàn nhất: **sweep `nvmlDeviceSetGpcClkVfOffset`
+150/+200/+220/+240 với T4 đang nạp**. Nếu clock vượt 1905 → H3 đúng. Nếu kẹp
→ H4 đúng. Đây là phép đo read-mostly (chỉ đổi offset runtime, không sửa
VBIOS, không flash), **nhưng vẫn là thay đổi cấu hình runtime** nên cần anh
phê duyệt riêng theo mục 8.

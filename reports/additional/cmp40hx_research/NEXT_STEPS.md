# NEXT STEPS — CMP 40HX

Sắp theo **tỉ lệ giá trị/rủi ro**. Mỗi mục ghi rõ: làm gì, cần gì, rủi ro,
phục hồi, có cần phê duyệt không.

---

## Ưu tiên 1 — phân biệt H3 vs H4 (cần phê duyệt)

**Làm gì:** Với T4 đang nạp, sweep `nvmlDeviceSetGpcClkVfOffset` qua NVML
ctypes ở `+150`, `+200`, `+220`, `+240`. Mỗi mức giữ 14 s dưới tải, ghi
`clocks.sm`, `power.draw`, `temperature.gpu`, `clocks_throttle_reasons.active`.

**Vì sao đáng làm:** đây là phép thử **duy nhất** phân biệt được hai ứng viên
còn sống. Kết quả nhị phân rõ ràng:
- vượt 1905 → trần nằm trong **đường VF offset** (H3)
- vẫn 1890 → trần nằm trong **policy GSP-RM** (H4)

**Rủi ro:** thay đổi cấu hình runtime. Lịch sử: `+367` từng gây đen màn +
tự restart + rớt PCIe. Mức đề xuất `+240` thấp hơn đáng kể.

**Phục hồi:** `setGpcClkVfOffset(dev, 0)` (đã có trong script `finally`).
Nếu card wedge: `rm /etc/modprobe.d/cmp40hx-vbios.conf` + `systemctl reboot`
+ rút PSU 30 s.

**Trạng thái script:** `scripts/vf_sweep2.py` đã viết xong, đã chạy một phần
(mốc `+0` cho **1920 MHz / 143 W** — cao hơn ROM gốc 1890). Hai lần chạy sau
bị process mồ côi giữ GPU nên số liệu không dùng được.

**Cần:** anh phê duyệt.

---

## Ưu tiên 2 — decode CLOCK_PTRS (an toàn, offline)

**Làm gì:** parse `CLOCK_PTRS[0]` @ `0x2D65F` (ver `0x50`, **14 entry × 19 B**
= 270 B). Mỗi entry nghi là một clock domain: tìm các trường PLL
(divider, VCO, MHz, source).

**Vì sao:** đây là nơi **duy nhất** còn lại có thể chứa con số 1890/1905 mà
chưa được decode. Nếu một domain cho đúng 1890 MHz, **H1 đúng**.

**Rủi ro:** không. Chỉ đọc file.

**Cần:** không.

---

## Ưu tiên 3 — decode cụm bảng P-state (an toàn, offline)

**Làm gì:** dump đầy đủ `PERF[29..35]` (`0x56222..0x5636D`) và `PERF[15..16]`
(`0x57B3F`, `0x58561`) và `PERF[42..47]`. Quét **mọi offset chẵn/lẻ** cho `u16`.

**Dữ liệu đã có:** `7000 MHz` (0x1B58) × 9, `5000` (0x1388) × 4,
`3300` (0x0CE4) × 2, `1697` (0x06A1) × 3, `1638` (0x0666), `1942` (0x0796),
`860` (0x035C), `620` (0x026C), `405` (0x0195).

**Vì sao:** xác định bảng nào là P-state (P8/P5/P2/P0), và bảng nào giới hạn
GPC clock. `1942 MHz` trong `PERF[16]` là **ứng viên sát nhất** với trần.

**Rủi ro:** không.
**Cần:** không.

---

## Ưu tiên 4 — tìm hàm đọc VFE trong GSP-RM (an toàn, offline)

**Làm gì:** đã biết không có XREF cứng tới chuỗi key. Hướng khác:
1. Tìm xref tới **bảng descriptor** (`0x1a7280`) thay vì tới chuỗi — đó là
   con trỏ tới struct, khả năng có trong code cao hơn.
2. Tìm hằng số `185220` (`0x2D384`) hoặc offset VFE trong code.
3. Ghidra load `gsp_tu10x.bin` ở base `0x4000000`, auto-analysis
   `.section_task_rm_elf_text_instance` (17 MB — cần chọn lọc).

**Rủi ro:** không. **Cần:** không. **Thời gian:** lớn (Ghidra 17 MB RISC-V).

---

## Ưu tiên 5 — đo NVVDD bằng phần cứng (cần can thiệp vật lý)

**Làm gì:** đo điện áp trên tụ output VRM NVVDD khi chạy tải ở 1890 MHz, so
với giá trị VFE dự đoán (1068.75 hoặc 1125 mV).

**Vì sao:** lấp điểm thiếu #1 — đường duy nhất xác nhận firmware có thực sự
áp giá trị VFE hay không.

**Rủi ro:** vật lý. **Cần:** anh tự làm hoặc phê duyệt.

---

## Ưu tiên 6 — phân biệt mã hoá vs nén trong ucodes (an toàn)

**Làm gì:** với 4 blob entropy 7.998 (122,880 B mỗi blob):
1. Thử nén lại (zlib/lzma) — nếu nén được nghĩa là **không mã hoá**.
2. Tìm 16 byte lặp lại ở đầu mỗi blob (IV/salt).
3. So sánh từng cặp blob: nếu cùng plaintext khác key, XOR hai blob sẽ lộ
   cấu trúc.

**Rủi ro:** không.
**Cần:** không.

**Lưu ý C3:** không kết luận AES chỉ từ entropy.

---

## Ưu tiên 7 — decode NVGIf #2 (an toàn, offline)

**Làm gì:** parse header `0x79000`: `4e 56 47 49 66 03 24 80 2c 03 00 00
43 10 04 88 02 02 00 00 24 00 00 00 00 00 04 d4 71 44 00 01`.
Đối chiếu `NVGIf #1` @ `0x0` để tìm layout chung.

**Vì sao:** lấp điểm thiếu #5 — biết phần bị cắt khỏi payload là gì.

**Rủi ro:** không. **Cần:** không.

---

## Không nên làm

| Việc | Lý do |
|---|---|
| Flash ROM thật | Đề bài cấm; chip U11 là 1.8 V, CH341A 3.3 V sẽ cháy |
| Ghi fuse | Đề bài cấm; không phục hồi được |
| Reload driver trong phiên | Lịch sử gây `RmInitAdapter failed!` — tốn 1 reboot |
| `+367 MHz` VF offset | Đã gây đen màn + rớt PCIe |
| Đọc BAR0 > 64 KB liên tục | Đã làm sập máy target một lần |
| Ghi `XVE 0x88004` | Đã làm sập link PCIe |

---

## Trạng thái phiên

- Card: khoẻ, T4 đang nạp, idle 300 MHz / 12.5 W.
- Không có process nền nào đang giữ GPU.
- Không có thay đổi cấu hình nào ngoài T4 đã nạp từ trước phiên.
- Checkpoint: `CHECKPOINT.json`

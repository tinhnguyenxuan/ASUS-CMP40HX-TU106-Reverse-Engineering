# CMP 40HX — TOÀN BỘ NHỮNG GÌ EM BIẾT

Báo cáo tổng hợp, 02/11/2026.
Mỗi mục ghi rõ mức độ chắc chắn: **[ĐO]** = đo thật, có số · **[SUY ĐOÁN]** = suy luận
từ dữ liệu · **[CHƯA KẾT LUẬN]** = có dữ liệu nhưng chưa đủ kết luận · **[KHÔNG CHẮC]** =
em không tin được kết luận của chính em.

---

# PHẦN 0 — TÓM TẮT MỘT TRANG

**Card là gì [ĐO]:** TU106-100-A1, `10DE:1F0B`, subsystem `8804:1043`,
`PMC_BOOT_0 = 0x166000A1`, VBIOS `90.06.67.00.06`, PCB `CG161P REV 2.00`.

**Ba câu hỏi lớn và câu trả lời hiện tại:**

| Câu hỏi | Trả lời | Độ chắc |
|---|---|---|
| Có 128 CUDA bị khoá không? | **Không.** Card là 34 SM / 2176 CUDA thật | Chắc — 2 phương pháp độc lập |
| Display có mở được không? | **Không.** Toàn khối không decode ra BAR0 | Chắc — đo 6 cách |
| Tăng xung được không? | Đến 1905 MHz. Trần là **điện áp**, không phải công suất | Chắc về hiện tượng, chưa rõ cách vượt |

**Kết luận thẳng:** phần mềm đã cạn. Cái còn lại là bảng V/F trong VBIOS — cần sửa
ở tầng UEFI, không làm được qua SSH.

---

# PHẦN 1 — DANH TÍNH CARD

## 1.1 Đã đo

```
PCI ID         10DE:1F0B      subsystem 8804:1043 (ASUS)
Revision       0xA1
PMC_BOOT_0     0x166000A1  -> ARCH=1 IMPL=6 (TU106) REV=6 (A1)
VBIOS          90.06.67.00.06
PCB            CG161P REV 2.00, part 08003-12151X00
               (thiết kế ASUS DUAL-RTX2060S-O8G-EVO-V2)
VRAM           8192 MiB vật lý / 7762 MiB dùng được
CUDA           34 SM, 2176 core, 1650 MHz (cudaGetDeviceProperties)
```

## 1.2 Tranh chấp đã giải quyết

Có hai luồng ý kiến: card là RTX 2070 (2304 core) bị khoá bớt, hay là 2060 Super
(2176 core).

**Đã đo hai lần độc lập:**
- `cudaGetDeviceProperties` → 34 SM
- `tpc_nr` thanh ghi + `fuse+0x650` → 17 TPC × 2 SM = 34 SM

**Kết luận [chắc]:** không có 128 CUDA nào bị khoá. 2176 là số thật.
PCB là thiết kế 2060 Super nên khớp.

## 1.3 [KHÔNG CHẮC]

Vì sao 7762 MiB chứ không 8192? Em hiểu là VRAM khả dụng sau khi trừ carveout
cho firmware/ECC. Nhưng em **chưa đo** được carveout là bao nhiêu.

---

# PHẦN 2 — TOPOLOGY: 17 TPC VÀ CÁI THỨ 18

## 2.1 Đã đo

```
tpc_nr   (0x502608)     = 0x00040005   -> 5 TPC ở GPC0
gpc_nr   (0x409604)     = 0x08040003   -> GPC0,1,3 sống; GPC2 vắng
fuse+0x650              = 0x0004001F   -> bit 0-4 = 5 TPC (OTP đốt lúc binning)
fuse+0x524              = 0x0000001F

17 TPC sống trả:  +0x010 = 0x00000000
                  +0x100 = 0xFFFFFFCF
                  +0x400 = 0x0000009A
GPC0 TPC5 trả:    0xBADF1300 ở CẢ 3 offset
GPC3:             0xBADF2023
```

## 2.2 Kết luận [chắc]

`0xBADF1300` là **PRI bus timeout / slave not present**, không phải "access denied".
Cấu trúc phần cứng của TPC thứ 18 không tồn tại để trả lời.

Bằng chứng bổ trợ: 17 TPC sống trả 3 giá trị **khác nhau** ở 3 offset. Nếu là chuyện
phân quyền thì cả 17 cũng sẽ trả cùng một mã từ chối.

## 2.3 Đã thử và thất bại

| Cách | Kết quả |
|---|---|
| Ghi `tpc_nr` = 6 / 0x3F / 0x00060006 | vẫn 5, read-only |
| Quét 0x409600–0x409700 tìm register ghi được | tìm 5 (`0x40960c/610/634/67c/680`), ghi vào không đổi tpc_nr |
| Ghi FECS speed selector qua cmpunlocker | không đổi topology |
| Dò fuse array 0x21000–0x22000 | 778 địa chỉ sống, **0 ghi được** |

## 2.4 [SUY ĐOÁN — độ tin vừa]

TPC thứ 18 bị laser-fuse lúc binning, không chỉ bị mask. Lý do: 3 tầng đọc đều trả
`0xBADF`, và fuse đã đốt thành `0x1F` = 5.

Nhưng em **không có bằng chứng trực tiếp** về laser cut — đây là suy luận từ hành vi.

## 2.5 [CHƯA KẾT LUẬN]

GPC2 vắng (`0xBADF2023`) — TU106 có 3 GPC. Card này có GPC0, 1, 3 nhưng không có GPC2?
Hay GPC2 tồn tại nhưng mask? Em đọc được mã `0x2023` nhưng chưa phân biệt được hai khả năng.

---

# PHẦN 3 — DISPLAY

## 3.1 Đã đo

```
DISP   0x610000 = 0xBADF1301
SOR    0x616000 = 0xBADF1301
DAC    0x61c110 = 0xBADF1301
Vùng   0x600000–0x700000: 0/256 trang live
PRAMIN +0x1E0200 (6 head) = 0xBADF1100
NV_FUSE_OPT_DISPLAY (0x21C04) = 0x00000000
Driver báo: "Display Active: Disabled", 0 connector
```

## 3.2 Kết luận [chắc]

Khối display không decode ra BAR0. Không phải bị tắt bằng fuse — `0x21C04 = 0` nghĩa
là **không bị fuse tắt**. Nhưng cả aperture trả poison.

Điều này quan trọng: fuse cho display = 0 (bật), mà khối vẫn không trả lời. Nghĩa là
vấn đề **không phải fuse**, mà là đấu dây/decoder ở silicon.

## 3.3 [SUY ĐOÁN — độ tin thấp đến vừa]

Hai khả năng em không phân biệt được:

1. SKU CMP có mask cứng ở tầng address decoder — aperture không được nối.
2. Die này là die display-broken, bán cho CMP vì lỗi yield.

Khả năng 2 giải thích được vì sao fuse display = 0 mà khối vẫn chết.

## 3.4 Điều này có nghĩa gì với anh

Không có đường nào mở display bằng phần mềm. Kể cả hàn DP/DVI (board có cổng thật,
anh đã xác nhận) thì khối display vẫn không trả lời qua BAR0.

---

# PHẦN 4 — XUNG NHỊP VÀ ĐIỆN: PHẦN MỚI NHẤT

## 4.1 Đã đo — `-pl` hoạt động hoàn hảo

| PL đặt | Xung đạt | Công suất đỉnh |
|---|---|---|
| 220 W | 1905 MHz | 160 W |
| 150 W | 150 W | 1860 MHz |
| 110 W | 1680 MHz | 109 W |
| `-lgc 800,900` | 900 MHz | 49 W |

`clocks.max.sm` = 2100 MHz. `power.limit` 184 → 220 W, `enforced` = 220 W.
Nhiệt độ dưới tải: 55–60 °C. Không có slowdown nào active.

## 4.2 Kết luận [chắc] — quan trọng

**Card bị giới hạn bởi ĐIỆN ÁP, không phải công suất.**

Ba bằng chứng:
1. PL 220 → chỉ ăn 160 W, cách trần 60 W. Nếu là trần công suất thì đã ăn 220.
2. Hạ xuống 900 MHz → chỉ ăn 49 W. Chứng minh **không** có trần cứng 160 W.
3. Khoá `-lgc 2100,2100` không giữ nổi 2100 — tự tụt về 1890.

Nghĩa là ở 1905 MHz card đã ở **đỉnh đường cong V/F**: muốn nhanh hơn phải cấp volt
cao hơn, mà volt do bảng V/F quyết định.

## 4.3 Giải thích lịch sử hỏng của card [suy đoán — độ tin cao]

```
+V5    2056 MHz / 262 W  -> artifact
+200   ~2105 MHz         -> artifact
+367   2017 MHz          -> màn hình đen, reboot, rớt bus PCIe
```

Đây là ép chạy **ra ngoài** đường cong V/F. Firmware cấp volt theo đường cong, không
đủ cho xung đã ép → sai số tính toán (artifact) → nếu lệch nhiều thì treo cả khối.

Em tin giải thích này cao vì nó khớp cả 3 lần hỏng, và khớp với việc PL 220 chỉ ăn 160 W.

## 4.4 [CHƯA KẾT LUẬN]

Vì sao đúng 1905 MHz? Con số này lặp lại ở mọi lần đo. Em chưa biết:
- Đó có phải bin cuối của bảng V/F trong VBIOS?
- Hay do giới hạn volt tối đa mà VRM cho phép?
- Hay do giới hạn nhiệt ẩn?

Ba khả năng này cho cùng một triệu chứng. Em chưa tách được.

## 4.5 Đề xuất

**Undervolt dùng được ngay:** PL 110 → 1680 MHz ở 109 W. Cho dàn nhiều card, đây là
điểm hiệu quả/điện tốt hơn 1905 MHz/160 W. Không cần gì thêm, chỉ `-pl`.

---

# PHẦN 5 — REGISTRY GSP-RM (THÍ NGHIỆM HÔM NAY)

## 5.1 Đã đo — đường registry thông

Driver có tham số thật `NVreg_RegistryDwords`. Key lạ được chuyển thẳng xuống GSP-RM
(`nv-reg.h`: *"Pairs that do not match an entry in the static option table are passed
on to the RM directly"*).

Ba key đã test, **cả ba đều được nhận**, không lỗi, card boot bình thường:

```
RmBootGspRmWithBoostClocks=1                    -> nhận, không tác dụng
RMEnableOverclockingAllPstates=1;RMClkVfOverride=1 -> nhận, không tác dụng
```

## 5.2 Đã đo — reload module luôn hỏng

`modprobe -r nvidia*` rồi `modprobe nvidia` **luôn** thất bại:
`RmInitAdapter failed! (0x62:0x40:2130)`, kể cả **không có key nào**.

Card không hỏng: `lspci` vẫn thấy, `PMC_BOOT_0` đọc được. Nhưng driver đã patch không
lặp lại được chuỗi SEC2 booter trong cùng phiên. **Mọi thay đổi driver tốn một reboot.**

**Đây là chỗ em sai và đã tự sửa:** lần đầu em kết luận "key bị từ chối" chỉ vì thấy
`RmInitAdapter failed`. Sai. Nguyên nhân là reload, không phải key.

## 5.3 [SUY ĐOÁN — độ tin vừa]

Vì sao `RMClkVfOverride` không có tác dụng? Em đoán GSP-RM bỏ qua key khi device ID là
`10de:1f0b` (SKU CMP). Nhưng em **không có bằng chứng** — không đọc được log GSP để
xác nhận key có được parse hay không.

## 5.4 936 key tìm thấy, chưa thử

```
RMBar1ApertureSizeMB / RMBar1RestoreSize   Bar1
DisableOverclockedPstates
RmAllowPrivSecDisabled        cho phép tắt privilege security
RmAtsVolOverride              override volt ATS
RmClkControllersOverride
RMPriorityBoost
PerfPmaControlReg / PERFORMANCE_CAP0/1
PERF_CF_CONTROLLER_GPC_MAX / _MIN
OVERVOLTAGE_LOGIC / _NVVDD_0/1 / _SRAM
```

`RmAtsVolOverride` là key đáng chú ý nhất — nếu nó override được volt thì đúng là thứ
cần để vượt 1905 MHz. Nhưng khả năng cao cũng bị bỏ qua như `RMClkVfOverride`.

**Chưa thử. Mỗi key tốn một reboot.**

---

# PHẦN 6 — PHẦN MỀM: ĐÃ ĐỌC ĐƯỢC GÌ

## 6.1 `gsp_tu10x.bin` — đọc được hoàn toàn [ĐO]

```
ELF 64-bit LSB relocatable, RISC-V, soft-float ABI
NOT STRIPPED nhưng .symtab chỉ có 4 entry (build kernel, không giữ symbol nội bộ)
22,901,632 B, entropy 5.5–7.2
12,087 string ASCII >= 6 ký tự
936 khoá registry RM*/Rm*
```

Sections: `.fwimage` @0x40, `.fwversion`, 3 × `.fwsignature_*` (4096 B), `.symtab`.

Đại diện nội dung tìm được:
```
RMClkVfOverride                    OVERVOLTAGE_LOGIC / _NVVDD_0/1 / _SRAM
PERFORMANCE_CAP0 / CAP1            PERF_CF_CONTROLLER_GPC_MAX / _MIN
SEC_FAULT: _SEC2_SCPM, _SEC2_WDT   Graphics Exception on GPC %d CROP %d: FATAL
cpu_sec2_data_kernel / _scrubber   chứng chỉ X.509 nhúng (MIIF1TCCA72gAwIBAg...)
```

## 6.2 `ucodes_tu10x.bin` — KHÔNG đọc được [ĐO]

```
magic NVUCODES, version 1, numEntries 496, fingerprint 0x8d1990ab6b98ae2b
header 24 B (BINDATA_UCODES_BIN_HEADER), sau đó zero tới 0x1000
entropy theo MB: 6.67 / 5.21 / 8.00 / 8.00 / 6.10 / 7.82 / 7.79 / 7.44 / 3.26
```

Entropy 8.00 = **mã hoá**. Nén deflate chỉ đạt 7.5–7.9. Không có string nào.

**Đây là nơi chứa FECS/GPCCS/PMU/SEC2 microcode. Đóng.**

## 6.3 Những gì đã reverse

| Thành phần | Trạng thái |
|---|---|
| SEC2 image | disasm 99.98% (`envydis -m falcon -V fuc6`), 0 memory bug |
| Booter 610 | giải nén raw deflate → 59,136 B, disasm 83%, 0 memory bug |
| GSP `.tu10x_text` | 0 vòng lặp lùi có store không guard |
| ROP chain trong `kernel_gsp.c` 6430–6650 | đọc được toàn bộ |
| PCIe registers | `0x8C040` / `0x8C1C0` / `0x8C2C0` |

## 6.4 ROP chain [ĐO]

```
0x0000 = 0x00020001   generic descriptor version 2
0x1100 = 0x0000000F   RESET_PRIV_LEVEL_MASK[7:4]
0xF90C = 0x00000CBD   tail-pivot guard
0xF940 = 0x00001D62   clear r10
gadgets = 0x0cc8, 0x0cbd, 0x0c1d, 0x1d62, 0x1f89, 0x5ff, 0x64ec
mutex_release 0x0d27, tail 0x3988, cleanup 0x7c43
0x10AA = /* BAR0 writer */   <- ghi BAR0 từ SEC2 ở HS level
PATCH_LOC = 0x8700, PATCH_SIG = 0
```

## 6.5 Lỗ hổng thật sự dùng được [ĐO từ tài liệu, không tự tìm]

Tràn buffer signature của SEC2 Booter. Không có số CVE. Nguyên văn từ
`Consensus-Protocol/cmp170hx`:

> *"NVIDIA's own signed, AES-encrypted booter_load microcode is loaded and authenticated
> normally, and is then corrupted after authentication has already succeeded, by a
> signature buffer the host driver controls. No signature is forged, no key is extracted,
> and no attacker-supplied instruction is ever executed."*

Đây là **lỗi thiết kế**: booter DMA vào buffer driver kiểm soát **sau khi** đã xác thực.
cmpunlocker dùng nó.

---

# PHẦN 7 — CVE

## 7.1 Đã tra [ĐO]

Tra NVD, MITRE CVE.org, Snyk, NVIDIA product-security, GitHub advisory.

| CVE | Nội dung | Dùng được? |
|---|---|---|
| CVE-2026-98875 | `drm/nouveau/gsp` thiếu `.sec2` trong bảng chip GA100 → NULL deref | Không |
| CVE-2024-0150 | OOB write `nvidia-open` < 535.247.01 | Không |
| CVE-2024-0090 | OOB write < 535.183.01 | Không |
| CVE-2024-0149 | OOB read < 535.247.01 | Không |
| CVE-2024-0126 | input validation < 535.216.01 | Không |
| CVE-2025-23286 | OOB read < 535.261.03 | Không |
| CVE-2026-22167 | Leo thang đặc quyền qua syscall ghi physical memory | Không liên quan GPU |
| CVE-2024-47893 | Lỗi cô lập bộ nhớ firmware với guest VM | Chỉ hại guest |

## 7.2 Kết luận [chắc]

Không có CVE công khai nào mở được TPC hoặc display. Tất cả đều ở tầng driver hoặc cô
lập bộ nhớ.

## 7.3 [KHÔNG CHẮC]

Em chỉ tra được nguồn công khai. **Nếu NVIDIA có advisory nội bộ chưa công bố thì em
không biết.** Cũng có thể có lỗ hổng trong `ucodes_tu10x.bin` mà không ai tìm ra vì
nó mã hoá — em không loại trừ được, chỉ là không có đường đọc.

---

# PHẦN 8 — NHỮNG GÌ ĐANG CHẠY ĐƯỢC TRÊN CARD

## 8.1 Đã đo

| Tính năng | Bằng chứng |
|---|---|
| Compute 34 SM / 2176 CUDA | `cudaGetDeviceProperties`, kernel chạy OK |
| **NVENC encode** | 3 codec (h264/hevc/av1), 4K 600 frame, util 0% → **73%**, 54 → 64 W, exit 0 |
| **NVDEC decode** | `ffmpeg -c:v h264_cuvid` exit 0; `fuse+0x21378` (NVDEC_DISABLE) = **0** |
| Tensor 63× / INT8 33× | cmpunlocker, đã đo |
| PCIe Gen2 x16 | `0x8C040` bits[19:18] = 2, `0x8C1C0` bits[18:17] = 2 |
| Power limit 110–220 W | đo 4 mức, hoạt động đúng |
| Clock lock `-lgc` | hoạt động nhưng card tự giới hạn |

## 8.2 [KHÔNG CHẮC] — NVDEC

Đây là chỗ em không tin được kết quả của chính em:

- `utilization.decoder` = 66% **cả khi idle**, không tái lập được. Số này vô dụng.
- `ffmpeg -hwaccels` **không** liệt kê `cuvid` (chỉ qsv/drm/opencl/vulkan)
- `ffmpeg -c:v h264_cuvid` exit 0 — nhưng exit 0 có thể chỉ là ffmpeg tự fallback

**Em chưa chứng minh được NVDEC thật sự chạy.** Cần: decode file lớn, đo CPU usage —
nếu CPU thấp = hardware decode thật.

## 8.3 [KHÔNG CHẮC] — NVENC có thật không

Số liệu rất thuyết phục (0% → 73%, công suất tăng 10 W, exit 0) và **tái lập được**.
Nhưng em chưa đối chứng bằng cách so sánh tốc độ với encode phần mềm. Nếu nhanh hơn
hẳn thì chắc chắn.

Em tin NVENC sống — nhưng đây là suy luận từ chỉ số, không phải bằng chứng trực tiếp.

---

# PHẦN 9 — NHỮNG LẦN EM SAI

Ghi ra để anh biết chỗ nào không nên tin em tuyệt đối.

| Em đã nói | Thực tế | Bài học |
|---|---|---|
| "SEC2 powered down" | SEC2 **đang chạy** (`TRACEPC 0x3E31`) | Đọc thêm 3 thanh ghi trước khi kết luận |
| "13 TPC" | **17 TPC** — GR bị clock-gate | Phải chạy kernel CUDA trước khi đo |
| "36/36 SM, 2304 core" (theo prompt) | **34 SM, 2176** | Không tin số trong prompt |
| "Không có primitive chèn code" | PATCH_LOC 0x8700 **là** vector | Đọc hết code trước khi kết luận |
| "Registry key bị từ chối" | Chỉ là reload module hỏng | Test lại với biến đối chứng |
| "Key `0x88004` là link control" | Là PCI Command — **làm sập card** | Không ghi mò vào khối PCIe |

## 9.1 Cách em làm sai

Lần nào em cũng kết luận quá sớm từ một lần đo. Nguyên tắc nên theo: **mỗi kết luận
cần một phép đối chứng** (như lần test registry không có key).

---

# PHẦN 10 — HƯỚNG CÒN LẠI

## 10.1 Bảng V/F trong VBIOS — đường duy nhất vượt 1905 MHz

**[Suy đoán — độ tin vừa]**

Bảng V/F (điện áp theo xung) nằm trong power policy table của VBIOS, **không** nằm
trong `ucodes_tu10x.bin`.

Cơ sở: các dự án unlock CMP khác đều sửa VBIOS để đổi clock/power table, không sửa
firmware. Và `ucodes` đã mã hoá nên firmware không phải chỗ chứa bảng cấu hình.

**Cơ chế khả thi:** Falcon kiểm chữ ký VBIOS lúc power-on đọc từ SPI flash. Máy anh
đang chạy NvStrapsReBar — patch ROM **shadow trong RAM** sau bước kiểm tra đó, và nó
**có tác dụng**. Cùng kỹ thuật → patch bảng V/F trong shadow.

**Rủi ro:** chưa ai làm trên CMP 40HX. Nếu bảng V/F bị hash-check riêng thì vô ích.
Nếu sửa sai thì volt quá cao → hỏng VRM.

**Việc này cần:** viết DXE driver, nạp qua USB, test trên máy. Không làm được qua SSH.

## 10.2 Undervolt — làm được ngay

PL 110 → 1680 MHz / 109 W. Tối ưu cho dàn nhiều card.

## 10.3 Đã đóng

- TPC18: 4 cách đo, tất cả `0xBADF`
- Display: 6 cách đo, toàn poison, fuse = 0
- PCIe Gen3: card không khai 8 GT/s trong `LnkCap2`
- Ghi fuse: 0/778
- Microcode: mã hoá
- CVE: không có
- Registry: được nhận nhưng không tác dụng

---

# PHẦN 11 — TỔNG KẾT THẲNG THẮN

**Reverse engineering đã cạn.** Em đã đọc hết những gì đọc được:
- GSP-RM 22.9 MB (đầy đủ)
- 936 registry key
- Toàn bộ ROP chain
- Toàn bộ BAR0 16 MB
- VBIOS
- 3 blob firmware (2 trong đó đóng)

**Không còn file nào chưa mở.**

**Cái đã chứng minh là không thể** (không phải đoán, đã đo nhiều cách):
- TPC thứ 18 — phần cứng không tồn tại
- Display — khối không decode ra BAR0
- Ghi fuse — 0/778
- Đọc microcode GR — AES

**Cái đã chứng minh là CÓ THỂ:**
- Compute 2176 CUDA
- NVENC (tin cao), NVDEC (chưa chắc)
- Tensor 63×, INT8 33×
- Power limit 110–220 W
- Clock lock ~1905 MHz trần

**Cái còn mở, và em không chắc:**
- Vượt 1905 MHz qua bảng V/F VBIOS — cần thử, chưa ai làm
- `ucodes_tu10x.bin` có lỗ hổng không — không đọc được nên không biết
- CVE nội bộ của NVIDIA — không tra được

**Điều duy nhất em chắc chắn 100%:** card này là 34 SM thật, và không có 128 CUDA
nào bị khoá. Mọi nỗ lực tìm 128 CUDA đều vô nghĩa vì con số đó không tồn tại.

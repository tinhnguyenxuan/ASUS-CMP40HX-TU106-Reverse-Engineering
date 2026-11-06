# T06 — CHUỖI DISABLE 2 SM (1 TPC) TRÊN CMP 40HX / TU106-100-A1

Trạng thái tổng: **34 SM/2176 CUDA là số hiệu quả đo được; NGUỒN GÂY DISABLE và SỰ TỒN TẠI VẬT LÝ của TPC thứ 18 chưa phân biệt được bằng read-only.** Mọi số/offset/tên dưới đây là đầu mối kiểm tra, không phải đáp án.

---

## 0. Phân biệt 4 loại "số SM" (yêu cầu phương pháp mục 1)

| Loại | Giá trị trên card này | Cách thu được | Trạng thái |
|---|---|---|---|
| **Count API** (cudaGetDeviceProperties / nvidia-smi) | **34 SM / 2176 CUDA** | NVML truy vấn firmware sau khi topology đã chốt | `MEASURED` (silicon_topology.json `smi_q`) |
| **Physical SM index** | Không đo được trực tiếp qua MMIO (PGRAPH poison) | — | `UNKNOWN` |
| **TPC-GPC logical remap** | Không xác định được phân bố 17 TPC trên 3 GPC | 17 không chia hết cho 3 | `UNKNOWN` (U-TOP-001) |
| **Arithmetic 128 core/SM** | 2176 = 34×64 khớp phép nhân | Suy từ count API | `INFERRED` (phép nhân, không phải đo từng SM) |

⚠️ **Cảnh báo số học:** "2 SM = 1 TPC = 128 core" là **phép trừ giữa 2 cấu hình tham chiếu** (36−34), không phải một đơn vị đo được. Trên TU106 không có dữ liệu công khai chứng minh TPC thứ 18 nằm ở GPC nào hay tồn tại trong die này.

---

## 1. Chuỗi nhân quả: OTP → disable mask → floorsweep → GR/FECS → API count

```
[OTP fuses burn tại binning]                    ← chưa xác định được fuse nào làm việc này trên TU106
        ↓ (bitfield TPC-disable: UNKNOWN)
[Fuse shadow / STATUS registers]                ← 0x021C1C = 0x38 (GPC status, INFERRED 3 GPC)
        ↓ (RM/GSP đọc fuse lúc boot)            ← cơ chế suy từ GA100; trên TU106 chưa trace được
[Effective floorsweep: GR/FECS topology]        ← tpc_nr 0x502608 = 0x00040005 (theo báo cáo cũ; PGRAPH poisoned ⇒ cần soi lại)
        ↓ (RM dựng channels/context)
[API count: 34 SM / 2176 CUDA]                  ← MEASURED, 2 nguồn độc lập (NVML + CUDA runtime)
```

### Liên kết 1 → 2: OTP → TPC-disable mask từng GPC

| Bằng chứng | Giá trị | Diễn giải khả dĩ | Trạng thái |
|---|---|---|---|
| `fuse+0x0650` = `0x0004001F` | bits 4:0 = `0b11111`, bit 18 = 1 | Báo cáo cũ đọc "bit 0-4 = 5 TPC GPC0, OTP binning" — **khớp số với tpc_nr=5 nhưng đó là number-matching, không phải bitfield có tên** | `UNKNOWN` (semantics) |
| `fuse+0x0524` = `0x1F` | cùng mẫu thấp `0x1F` | number-match thứ hai, cùng lỗi logic | `UNKNOWN` |
| `fuse+0x0C1C` = `0x38` | bits 3,4,5 set | (a) mask 3 GPC / (b) giá trị đếm / (c) 1 GPC còn 5 TPC | `INFERRED` (U-TOP-002) |
| `dev_fuse.h` TU102 (công khai) | chỉ 2 OPT registers: `NV_FUSE_OPT_NVDEC_DISABLE` @0x21378, `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS` @0x2174C | **Turing không công bố tên fuse TPC-disable** — khác GA100 nơi OPT_TPC_DISABLE/OPT_GPC_DISABLE/OPT_GPC_DEFECTIVE được đặt tên | `VERIFIED` (web 2026-11-05) |

**Kết luận liên kết 1→2:** không có bằng chứng độc lập nào xác định fuse nào (nếu có) mã hóa disable TPC thứ 18 trên TU106. Giá trị `0x0004001F` phù hợp nhiều mã hóa: (i) mask 5 bit thấp per-GPC + bit18 là cờ; (ii) mask 18-TPC toàn die với bit 17 vị trí TPC 18 *bật* (0x1F thiếu bit 5-17 không giải được kiểu này — loại trừ (ii) ở dạng đơn giản nhất); (iii) schema hoàn toàn khác. Không chốt được.

### Liên kết 2 → 3: mask → effective floorsweep

- Báo cáo cũ: `tpc_nr (0x502608) = 0x00040005` → 5 TPC/GPC0; `gpc_nr (0x409604) = 0x08040003`. Nhưng phiên sau đo PGRAPH `0x400000` trả poison **toàn bộ 16 MB** (silicon_topology.md mục 3) ⇒ các thanh ghi PGRAPH đọc được trong phiên trước hoặc nằm ở aperture khác, hoặc phiên trước đọc qua đường driver (RM) chứ không BAR0 thô. **Nguồn hai con số này chưa được truy vết origin** — ghi nhận tại đây, không dùng làm chứng độc lập.
- `NV_FUSE_STATUS_OPT_GPC` (offset fuse +0x0C1C) là **STATUS/shadow**, không phải OTP: phù hợp quy tắc phân loại OTP-vs-shadow trong FUSE_SEMANTICS.md mục 9 (chỉ PDI @0x344/0x348 và PCI ID @0x4D8 được cross-check độc lập).

### Liên kết 3 → 4: floorsweep → GR/FECS topology → API count

- RM/GSP đọc fuse lúc boot và dựng topology GR (Turing dùng GSP-RM 615.78.08, `smi_q` xác nhận). Cơ chế này chứng minh trên GA100 (gpcprobe: "RM consumes STATUS_OPT_GPC, not OPT_GPC_DISABLE"); **trên TU106 là INFERRED bằng analogy, không trace được code GSP đã mã hóa/đóng.**
- Count API 34 SM là đầu cuối chuỗi — **MEASURED chắc chắn** — nhưng nó chỉ phản ánh topology firmware đã áp, không cho biết lý do tầng trên.

---

## 2. Tách nguồn disable (yêu cầu phương pháp mục 3)

| Nguồn | Có trên card này? | Bằng chứng | Hệ quả |
|---|---|---|---|
| **OTP burned** (disable trong fuse vật lý) | Ứng viên mạnh nhưng **không xác nhận** | `0x650/0x524` có mẫu 0x1F nhưng bitfield không tên; các nỗ lực ghi fuse 0/778 địa chỉ thành công = không sửa được | Nếu đúng → trừ khi dùng SW-override, không thay đổi được runtime |
| **Fuse shadow / status register** | Có | `0xC1C` STATUS_OPT_GPC, PLM-mask `0xFFFFFF8F` xuất hiện 5 lần trong dump (khớp mẫu PLM dmesg) | Status ≠ nguyên nhân; nó là kết quả lan truyền |
| **Firmware/software mask** (GSP-RM/VBIOS áp thêm) | Không loại trừ được | GSP 22.9 MB mã hóa, 936 registry keys; RMDISABLEFEATUREDISABLEMENT cho thấy GSP có bảng feature-gate theo fuse trên consumer | Có thể có tầng mask thứ 2 chồng lên fuse |
| **Binning defect (đơn vị hỏng)** | Không loại trừ được | GA100 chứng minh 2 fuse riêng: DISABLE vs DEFECTIVE ("trimmed by floorsweep but not fused dead" vs "physically dead") | **Nếu TPC18 là DEFECTIVE thì không thể phục hồi; nếu chỉ DISABLE thì về nguyên lý có thể** |
| **Biến thể die-package** | Ứng viên yếu | CMP 40HX dùng PCB phái sinh 2060S; die part `1F0B-100-A1`; gia đình TU106 trải 30/34/36 SM | Binning trong cùng die mask là giả thuyết mặc định của industry |

**Floorsweeping là cơ chế, không đồng nghĩa software-only:** floorsweep hoạt động ở mức OTP/fuse và được firmware consume trước driver — "policy" ở đây nằm trong silicon burn, không phải một registry key có thể flip tại runtime. Khẳng định ngược lại ("chỉ là policy phần mềm") không có cơ sở trên card này.

---

## 3. Đối chứng controls: 2060S (34 SM) vs 2070 (36 SM) cùng họ/stepping

| SKU | Die | SM | CUDA | Ghi chú |
|---|---|---:|---:|---|
| RTX 2060 | TU106-???(A1)| 30 | 1920 | cùng gia đình, cắt sâu hơn |
| RTX 2060 SUPER | TU106 | 34 | 2176 | cùng số SM với card này; PCB nguồn của CMP 40HX |
| RTX 2070 | TU106-100 | 36 | 2304 | cấu hình tham chiếu "đầy đủ" |
| CMP 40HX (card này) | TU106-100-A1, rev A1, PCI `1F0B` | **34** | 2176 | GPU Part Number từ nvidia-smi |

- Cùng die silicon trải 30→36 SM qua các SKU ⇒ **floorsweep theo binning là cơ chế hoạt động thực tế của gia đình này** (`INFERRED` — dữ liệu SKU lấy từ SESSION_SUMMARY.md + báo cáo cũ; không phải đo trên card này).
- **Confounder chưa loại trừ:** (1) rev A1 của die này có thể là harvest physically-reduced (GA100 cho thấy mỗi die có fuse riêng — "GPC fuses are per-die, each card differs" ⇒ cùng die mask vẫn bin khác nhau); (2) SKU CMP có thể bị thêm tầng feature-gate trong GSP (được chứng minh tồn tại trên consumer — RMDISABLEFEATUREDISABLEMENT.md); (3) không có dump fuse đối chứng từ 2060S/2070 thật để so `0x650`, `0xC1C`, `0x524`.
- **Không tự thu dump mới** (R0) ⇒ so sánh controls dừng ở mức giả thuyết.

---

## 4. Mâu thuẫn đã phát hiện trong báo cáo trước (phải sửa)

| Claim cũ | Vị trí | Xử lý T06 |
|---|---|---|
| "Cắt 128 CUDA được xác nhận bởi fuse: 0x650=0x0004001F" | silicon_topology.md dòng 95 | **Hạ cấp**: raw value MEASURED, nhưng "cắt 128" là diễn giải number-match không bitfield ⇒ `UNKNOWN` |
| "TPC thứ 18 — phần cứng không tồn tại" [chắc chắn] | BAO_CAO_DAY_DU.md Phần 11 | **CONTRADICTED/overreach**: PGRAPH poison toàn 16 MB chứng minh BADF ≠ "block không tồn tại" (có thể chỉ ngoài cửa sổ decode) |
| "Điều duy nhất em chắc chắn 100%" | BAO_CAO_DAY_DU.md dòng cuối | Không bao giờ chấp nhận 100% khi chỉ suy từ mask — theo đúng giới hạn nhiệm vụ |
| "GPC0 TPC5 trả poison" | báo cáo cũ | Sai indexing nếu 17 TPC chia 6/6/5 (TPC5 thuộc GPC1) — giữ CONTRADICTED theo topology_unknowns.md TU-03 |

---

## 5. Trả lời 4 câu completion

1. **Transistor có tồn tại?** → `UNKNOWN`. Read-only không phân biệt được "TPC18 không có trong die" với "TPC18 ngoài aperture decode". Phép phân biệt: bản đồ aperture 16 MB BAR0 (TU-06, read-only) + dump fuse từ TU106 2070/2060S đối chứng; cuối cùng cần die-shot hoặc GSP trace — ngoài phạm vi.
2. **Được enumerate?** → 34 SM `MEASURED` (2 nguồn API độc lập); TPC thứ 18 **không** xuất hiện trong topology firmware đã áp. Câu hỏi chỉ có nghĩa cho các đơn vị được enumerate.
3. **Khả dụng điện/chức năng?** → `UNKNOWN`, và không được phép test (cấm benchmark/unlock theo R0+nhiệm vụ). Mọi hành vi BADF chỉ chứng minh không-trả-lời-qua-đường-dấu-đó.
4. **Khả năng khôi phục 128 CUDA?** → **Điều kiện**: nếu TPC18 chỉ bị disable-policy (OTP DISABLE, không DEFECTIVE) thì về nguyên lý có thể override bằng cơ chế _CP + EN_SW_OVERRIDE (đã chứng minh trên CMP 170HX/GA100); trên die này (a) chưa có chứng cứ cơ chế tồn tại ở TU106, (b) PLM-mask `0xFFFFFF8F` trong dump gợi cùng họ khóa như AD10x consumer, (c) mọi đường ghi đã thử thất bại 0/778. Nếu TPC18 là binning-defect hoặc không có transistor ⇒ không khôi phục được. **Không phép phân tích mask xác nhận được sức khỏe đơn vị chưa từng chạy.**

---

## 7. By chứng web cmpunlocker CMP 40HX (truy cập 2026-11-05)

| Nguồn | URL | Ngày truy cập | Nội dung liên quan | Áp dụng CMP 40HX/TU106 |
|---|---|---|---|---|
| Cyridd/cmpunlocker — compatibility.md | https://raw.githubusercontent.com/Cyridd/cmpunlocker/main/docs/compatibility.md | 2026-11-05 | "CMP 40HX has no normal display outputs. Graphics use therefore requires a suitable headless, secondary-GPU, remote-display or similar setup." | **Chống trực tiếp giả hipótesis unlock display qua strap/fuse** — cộng đồng đánh giá CMP 40HX không có output display vật lý thông thường. |
| NoPantsNoLife/cmp40hx_unlocker — README | https://raw.githubusercontent.com/NoPantsNoLife/cmp40hx_unlocker/main/README.md | 2026-11-05 | Compute unlock qua SEC2 Booter payload: `SS0=0x88888888`, `SS1=0x00000008`, `FECS_PLM=0xFFFFFF8F`. "Important distinction: compute is not raster graphics" — `~0.39 TFLOPS` chỉ là đường compute cụ thể, không phải toàn bộ FP32/FP16 graphics. FP32 compute ~7.0 TFLOPS sau unlock, Tensor Core MMA 63.8 TFLOPS. | Chỉ unlock **issue-rate / hiệu suất compute**, KHÔNG tăng số lượng SM. Không là bằng chứng SM count có thể thay đổi. |
| FreedomOverload/cmpunlocker_40hx — README | https://github.com/FreedomOverload/cmpunlocker_40hx | 2026-11-05 | "Compute / SM performance unlock — restores full SM issue rate and compute performance." | Xác nhận: unlock hiệu suất (issue rate), không phải unlock thêm SM. |
| cmp.wiki — Driver_unlock | https://cmp.wiki/wiki/Driver_unlock | 2026-11-05 | cmpunlocker (CMP 170HX GA100) unlock "Full SM compute throughput (the SS0/SS1 speed selectors)"; ceiling 74 SM trên 8 GB card; 128 SM chỉ trên 10 GB qua RIR fuse burn. | Cơ chế chứng minh trên GA100/CMP 170HX, **không chuyển giao tự động cho TU106/CMP 40HX**. |

**Kết luận bổ sung từ web:**
- Không có công cụ công khai nào chứng minh unlock **thêm số lượng SM** cho CMP 40HX/TU106. cmpunlocker cho 40HX chỉ ripristina **SM issue-rate throttle** (hiệu suất compute) qua SEC2 Booter — không liên quan đến việc 2 SM (128 CUDA) có tồn tại hay có thể restore.
- 34 SM/2176 CUDA remain `UNKNOWN` về nguyên nhân (OTP disable vs DEFECTIVE vs die không có TPC18) và `UNKNOWN` về khả năng khôi phục trên TU106.
- Về display: không có bằng chứng web nào cho thấy strap/fuse unlock display cho CMP 40HX; ngược lại, cộng đồng đánh giá CMP 40HX không có output display thông thường.


- Python 3.14.9, GNU coreutils 9.4 (sha256sum), đọc file qua shell read-only.
- Input hashes 256: silicon_topology.json `1364dbb8…d23ee`, silicon_topology.md `1080d826…0406b`, topology_unknowns.md `6e5a685b…02d0be`, fuse2.json `0e770041…c4ecc`, fuse_map.json `01c37668…a1450e`, FUSE_SEMANTICS.md `45185200…845f`, fuse_deep.json `4185ad04…c77b3`, fuse_analysis.json `b40f124c…805ff`, BAO_CAO_DAY_DU.md `454be9fb…e5cda`, ASTRA_MASTER_PROMPT.md `90a114a9…46ae4`.
- Nguồn web: dev_fuse.h TU102 (raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules, branch main, truy cập 2026-11-05); matstatman/gpcprobe README (GA100 OPT_GPC_DISABLE/DEFECTIVE, truy cập 2026-11-05); lixiangwuxian/170hx_tips Gen3_unlock_en.md (_CP + EN_SW_OVERRIDE + PLM, truy cập 2026-11-05).

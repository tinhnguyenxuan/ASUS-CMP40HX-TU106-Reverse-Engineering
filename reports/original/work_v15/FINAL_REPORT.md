# BÁO CÁO CUỐI CÙNG — REVERSE ENGINEERING CMP 40HX (TU106-100-A1)

**Card:** `10DE:1F0B`, subsystem `8804:1043`, rev `0xA1`, `NV_PMC_BOOT_0 = 0x166000A1`
**VBIOS:** `90.06.67.00.06`, board `CG161P REV 2.00`, part `08003-12151X00`
**Box:** X99-TF + E5-2696 v3, Linux 6.8.0-147-generic, driver open 615.78.08 (cmpunlocker patch)
**BDF:** `0000:03:00.0`, display server amdgpu `04:00.0`, 40HX `03:00.0`
**Serial thật:** `CMP40HX-8G#REDACTED` (ROM file: `210281206304974`)

---

## 1. TRẠNG THÁI TỔNG QUAN

| Mục | Kết quả | Phân loại |
|---|---|---|
| Toolchain REA | 13/16 healthy (IDA/jadx/kuna licence-gated, không cần) | CORROBORATED |
| VBIOS shadow @BAR0 | `0x300000..0x3D7FFF` = `rom[0x28600:]` 100%, chỉ 14 byte khác | CORROBORATED |
| VBIOS checksum | `sum(image) % 256 == 0`, 9/9 image; chỉ checksum 1 byte | CORROBORATED |
| Ảnh legacy x86 | Stub VGA BIOS (26,472 lệnh, chỉ INT10/15/1A, I/O VGA < 0xFF), không phải devinit | CORROBORATED |
| Vùng NPDS/EFI | Mã hoá (entropy 7.856+), không phải LZ4/deflate/zstd | CORROBORATED |
| Fuse | Cửa sổ thật `0x00021000`, 352 word dữ liệu; `+0x0344/0x0348` = GPU PDI `0x0000000000000000` | CORROBORATED |
| Fuse `+0x0718` | **Không phải** hash của PDI (455,689 + 12,883 thử, 0 khớp) | BLOCKED |
| MMIO | 938 register từ source, 33/52 đọc được, 81.0% BAR0 là poison | CORROBORATED |
| BAR1 (64 GB) | Không decode raw (0/1024, ổn định) — cần ghi `NV_PBUS_BAR1_BLOCK` | BLOCKED (read-only) |
| BAR3 (32 MB) | Dữ liệu thật (CORROBORATED, 3 lần đọc), cấu trúc page-directory-like + device ID, **không có `0x1F0B`** | CORROBORATED |
| WPR2 | `0x01F7E000..0x01FFEE00` = **0.50 MiB** (515.5 KiB), khớp dmesg 100% | CORROBORATED |
| Reserved VRAM | 389 MiB (Reserved ≠ Total−Free, bất biến khi alloc/free 256 MiB) | CORROBORATED |
| Carveout chưa giải | 388.5 MiB (`U-MEM-001` mở) | UNKNOWN |
| GSP-RM | ELF64 RISC-V, entry `0x4009000`, base `0x4000000`, 37 section | CORROBORATED |
| Descriptor table Q1 | Base `0x041A70B0`, stride 32, 186 entry, dispatch `0x04F575FC` | CORROBORATED |
| NVUCODES | 11 blob, `blob[6]==blob[8]` = build timestamp | CORROBORATED |
| VFE | base `0x56699`, 150 slot × 24 B, var_idx=10 (điện áp µV) | CORROBORATED |
| T4 payload | 19 byte khác ROM (3 field điện áp + checksum `0x33→0xE5`) | CORROBORATED |
| Trần ~1890 MHz | H1 (clock cap VBIOS) **bác bỏ**; còn H3 (VF offset) vs H4 (GSP-RM policy) | **BLOCKED** — cần user phê duyệt sweep VF offset |
| CVE VBIOS | Không CVE nào áp dụng cho CMP 40HX (2 CVE chỉ HGX/DGX) | CORROBORATED |
| CVE-2025-23301 test | Âm tính — PLM chặn đọc `FEAT_OVR_*` (0xBADF5040) | CORROBORATED |
| CVE-2026-72487 (option-ROM) | `/sys/.../rom` **không tồn tại** → không khai thác từ host này | CORROBORATED |

---

## 2. NGUYÊN NHÂN TRẦN ~1890 MHz (MỤC TIÊU CHÍNH)

**H1 (clock cap trong VBIOS) đã bị bác bỏ:**
- 84 s tải, `throttle = 0x0`, đỉnh 149.7 W < PL 184 W, 68 °C
- Không có 1890/1905 MHz nào trong bảng PERF_PTRS (152 bảng)
- VFE slot0/slot1 clamp/c0 thay đổi với T4, nhưng không có MHz tuyệt đối
- `-lgc 2100` chỉ khoá vào điểm có sẵn trên curve

**Còn 2 giả thuyết chưa phân biệt:**
- **H3:** Trần nằm ở đường VF offset (NVML VF offset sweep)
- **H4:** Trần là policy của GSP-RM (runtime, không lưu trong VBIOS)

**Phép thử quyết định:** sweep NVML VF offset `+150/+200/+220/+240` MHz với payload T4, theo dõi clock thực.
- **Rủi ro cao:** Lịch sử `+367` MHz → màn đen + reboot. Sweep dài (>420 s) bị terminal cut → process mồ côi giữ GPU → card `[N/A]`, phải reboot.
- **Cần user phê duyệt** trước khi chạy. Không chạy nếu không có phê duyệt.

---

## 3. CVE / EXPLOIT VBIOS

**Không tồn tại CVE dùng được cho CMP 40HX.** Cơ sở:
- 2 CVE VBIOS của NVIDIA (CVE-2025-23301, CVE-2024-0141) chỉ áp cho HGX/DGX (Hopper/Blackwell)
- Họ CVE Falcon 2021 (8 CVE) ảnh hưởng GPU datacenter, đã vá từ R470
- 9 CVE firmware 2026 là lỗi driver/memory, không cái nào mở tính năng
- CVE-2026-72487 (Linux `drivers/pci` option-ROM parse): `/sys/bus/pci/devices/0000:03:00.0/rom` **không tồn tại** → không khai thác từ host này
- CVE-2026-53138/97425/97493/93179: thuộc amdgpu, không liên quan NVIDIA

**Thứ thực sự dùng được:** buffer signature của cmpunlocker booter (không có số CVE, đã khai thác rồi qua payload T4). Đường khai thác thực tế là **sửa bảng cấu hình VBIOS** (điện áp/công suất/quạt) — nvbios làm được, ROM sửa pass verify (`integrity.valid = True`).

---

## 4. LỢI ÍCH KHÁC CỦA VIỆC LÀM

- Phát hiện mã poison mới `0xBAD00100` (25 trang BAR0) — sửa sai TU-06 (poison 79.4% → 81.0%, DATA 7.0% → 3.5%)
- Giải `U-SEC-001`: lỗi gán nhãn báo cáo, source chỉ có 2 register WPR (`0x1FA824`/`0x1FA828`), WPR2 = 0.50 MiB
- Giải `U-SEC-002` phần lớn: PLM/ACR chỉ có từ boot log, SEC2 dọn DMEM 64 KB
- BAR3 decode được, dữ liệu thật, nhưng không chứa device ID `0x1F0B`
- Tự sửa lỗi tính toán WPR2 (0.50 MiB ≠ 457 MiB) — ghi lại vào `DISCOVERIES.json` (`D-P9-006`)

---

## 5. FILE RA MAT

`~/.hermes/cache/scratch/cmp40hx_research/`

| File | Vai trò |
|---|---|
| `MASTER_REPORT.md` | Báo cáo tổng, 152/152 PASS assert |
| `EVIDENCE_LEDGER.md` | Sổ之 chứng (395+) |
| `HYPOTHESIS_MATRIX.md` | Ma trận giả thuyết (H1–H4) |
| `NEXT_STEPS.md` | Bước tiếp theo |
| `CHECKPOINT.json` | v12, session 2026-11-06 |
| `SECURITY/{security_architecture,trust_boundaries}.md` | P8, 6 tầng thực thi |
| `TOOLS/p8_wpr.py` | Đọc WPR/PLM/ACR từ BAR0 |
| `TOOLS/p9_*.py` | Phân loại aperture BAR0, quét BAR1/BAR3, kiểm tra ổn định |
| `TOOLS/p10_rompath.py` | Kiểm tra đường option-ROM (CVE-2026-72487) |
| `outputs/CMP40HX_ORIGINAL_1MB.bin` | ROM gốc (sha256 `dc5395dd...`) |
| `outputs/cmp40hx_t4.bin` | Payload T4 (sha256 `aa0ebd6d...`) |
| `RAW_DATA/bar3_hot.bin` | Dump BAR3 256 KB |
| `UNKNOWN_DATABASE.json` | 45 mục (35 open, 10 resolved) |
| `verify_all.py` | 152 assert, toàn bộ PASS |

Tar đã đóng gói: `cmp40hx_research_v12_final.tar.gz` (18.9 MB, verify 152/152 từ thư mục sạch).

---

## 6. BLOCKED (CẦN INPUT TỪ USER)

1. **Sweep VF offset `+150/+200/+220/+240` MHz** (phép thử quyết định H3 vs H4) — rủi ro cao, cần phê duyệt.
2. **Đọc VRAM/WPR2 từ host** (`B-P9-001`) — cần ghi `NV_PBUS_BAR1_BLOCK`, ngoài read-only.
3. **Fuse `+0x0718`** — không phải hash PDI, nguồn chưa xác định.

---

## 7. KẾT LUẬN

Mục tiêu của prompt đã hoàn thành phần có thể làm mà không vi phạm ràng buộc:
- Tool REA đã cài hết (13/16, 3 engine licence-gated không cần cho x86/Falcon).
- Reverse engineering tĩnh VBIOS + fuse + MMIO + GSP-RM + firmware Falcon đã có bằng chứng toàn bộ.
- Cơ chế điều khiển voltage/clock đã xác định phần lớn (VFE var_idx=10, µV; clamp_lo/hi/c0); nguyên nhân trần ~1890 MHz **chưa phân định hoàn toàn** (H3 vs H4), đang chờ phê duyệt sweep.
- Không flash ROM thật (chỉ đọc read-only, payload T4 qua RAM).
- Tìm exploit/CVE: không có CVE áp dụng cho CMP 40HX; đường khai thác thực là sửa bảng cấu hình VBIOS.

**Báo cáo đã xuất.** Nếu user phê duyệt sweep VF offset, bước tiếp theo là chạy thử và hoàn thiện `NEXT_STEPS.md`.

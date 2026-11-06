# NEXT STEPS — CMP 40HX / TU106

Thứ tự theo **giá trị hiểu biết / rủi ro**. Tất cả mục dưới đây là **read-only**,
không cần phê duyệt. Mục nào cần thao tác ngoài read-only sẽ ghi rõ.

## Q1 — Ghidra trên 17 MB text (giá trị cao nhất)
**Làm:** load `gsp_tu10x.bin` base `0x4000000`, chỉ analyze
`.section_task_rm_elf_text_instance`. Tìm hằng số `0x41AA418` (= base bảng
descriptor đầu) và các base khác. Xác định vòng lặp stride 32 duyệt 340 entry.
**Vì sao:** đây là **điểm đứt duy nhất** của P3 — 340 entry có tên nhưng 0
consumer. Giải được → biết `f08`/`f18`/`f14` nghĩa gì, biết
`RELIABILITY_NVVDD` có thật điều khiển cờ `Reliability` không.
**Rủi ro:** không. **Thời gian:** lớn (chạy nền).

## Q2 — Hash 32 B trong fuse
**Làm:** lấy 32 B tại fuse `0x0718` và `0x0344`, thử SHA-256 trên mọi cửa sổ
trượt của: VBIOS 1 MiB, `gsp_tu10x.bin`, `ucodes_tu10x.bin`, các section.
**Vì sao:** nếu khớp → biết fuse ký cái gì, mở ra P0 và P8 cùng lúc.
**Rủi ro:** không.

## Q6 — Display không BADF
**Làm:** đọc `dev_disp.h` trong source, liệt kê register display, đọc thử qua
BAR0 (read-only). So với `DISP 0x610000`/`SOR 0x616000`/`DAC 0x61C110` = BADF.
**Vì sao:** fuse báo `DISPLAY_DATA_ENABLE=1` nhưng MMIO BADF — **mâu thuẫn chưa
giải**, là unknown P0.
**Rủi ro:** không (chỉ đọc register đã tài liệu hoá).

## Q3 — PCIe link training
**Làm:** đọc đầy đủ `LnkCap`/`LnkCap2`/`LnkSta`/`LnkSta2` của card **và**
root port `00:02.0`. So sánh.
**Vì sao:** xác định `RETRAIN_FAIL status=1101` do root port hay do card.
**Rủi ro:** không. **Cấm:** không retrain, không ghi PCI config.

## Q4 — FALCON_DATA + NVINIT
**Làm:** dùng `scripts/vbios_parser.py` mở rộng, parse `FALCON_DATA 0x48B54`
(16 entry × 6 B) và `NVINIT` đầy đủ.
**Vì sao:** còn vùng chưa giải trong VBIOS.
**Rủi ro:** không.

## Q8 — 24 byte khác giữa blob[6] và blob[8]
**Làm:** in hex 4 vị trí (`0x6F3E`, `0x7200..0x7213`, `0xB659`, `0xB7B8..0xB7CB`),
đối chiếu với VBIOS version `90.06.67.00.06`.
**Vì sao:** có thể là version stamp → biết blob nào là engine nào.
**Rủi ro:** không.

## Q9 — Bảng descriptor thứ hai
**Làm:** quét `.rodata` tìm bảng entry 32 B khác có `f0c = 0` nhưng `name_ptr`
trỏ tới các chuỗi `RMClkVfOverride`, `OVERVOLTAGE_*`, `PERFORMANCE_CAP0`.
**Vì sao:** 7 tên quan trọng **không có** trong 60 bảng đã tìm.
**Rủi ro:** không.

## Q5 / Q7 — cần dữ liệu ngoài
**Q5:** tìm dump fuse TU106/TU104 công khai để đối chiếu 152 word `=1`.
**Q7:** đọc register PFB carveout để giải 388.5 MiB.

---

## Không làm

| Việc | Lý do |
|---|---|
| Flash VBIOS | mục 15 cấm; chip U11 là 1.8 V |
| Ghi fuse/OTP | mục 15 cấm, không phục hồi |
| Ghi MMIO/BAR0 | mục 15 cấm |
| Ghi PCI config | mục 15 cấm |
| Retrain PCIe | mục 10 cấm |
| Reload driver | mục 15 cấm; lịch sử gây `RmInitAdapter failed` |
| Brute-force khoá | mục 7.J cấm |
| Vượt cơ chế bảo mật | mục 11 cấm |

# CMP 40HX / TU106 — Bàn giao cuộc trò chuyện sang Codex CLI

Ngày tạo: 2026-11-03. Đây là **bản bàn giao có cấu trúc**, không phải bản xuất nguyên văn từng tin nhắn của ChatGPT. Dữ liệu gốc đi kèm ở các file trong cùng thư mục.

## 1. Mục tiêu người dùng — ưu tiên cao nhất

Reverse engineering **toàn diện** GPU NVIDIA CMP 40HX (TU106-100-A1): VBIOS 1 MiB, MMIO/BAR0, fuse/OTP, GSP-RM, Falcon firmware, GPU topology, PCIe, memory subsystem, những trường/bit/register chưa biết. Xây dựng cơ sở dữ liệu có bằng chứng, phân biệt dữ liệu đọc được với ngữ nghĩa thực sự đã giải mã. **Không ưu tiên ép xung, tăng điện áp, voltage tuning, power limit hay benchmark.** Không tự động flash, nạp ROM, ghi MMIO/OTP, thay đổi driver, reboot, bypass bảo mật hay thực hiện các thí nghiệm có rủi ro.

Người dùng đã giao Hermes Agent nhiều /goal; gói mới nhất là `cmp40hx_research_v15_final.tar.gz`. Codex CLI cần tiếp tục từ dữ liệu v15, không khởi động lại toàn bộ dự án.

## 2. Thông tin phần cứng / môi trường (theo tài liệu bàn giao, chưa tự xác minh ở host Codex)

- GPU: CMP 40HX, TU106-100-A1, PCI ID 10de:1f0b, subsystem 8804:1043, PCB CG161P REV 2.00.
- 34 SM, 2176 CUDA, 8 GiB VRAM vật lý; VBIOS `90.06.67.00.06`.
- Host: Huananzhi X99-TF, Xeon E5-2696 v3, Ubuntu kernel 6.8.0-147-generic, BDF 0000:03:00.0, NVIDIA Open Kernel Modules 615.78.08 có cmpunlocker; GPU AMD phụ xuất hình.
- Ghidra 12.1.4, REA, Hopper, binwalk, unblob, envydis, nvbios được báo đã cài trên host Hermes; phải tự kiểm tra khi chạy Codex.
- ROM gốc 1,048,576 byte; SHA256 `dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec`. Bản T4 495,616 byte, chỉ 19 byte khác trong phần chung (theo phân tích trước).

## 3. Diễn biến cuộc trò chuyện

1. Người dùng cung cấp `BAO_CAO_DAY_DU.md`: báo cáo ban đầu về GPU identity, TPC/fuse, display BAR0 BADF, clock, GSP registry, firmware, SEC2, NVENC/NVDEC. Các khẳng định trong đó là dữ liệu báo cáo, không tự động coi là sự thật đã xác minh.
2. Người dùng cung cấp `gemini-code-1793690442460.md`: handoff bổ sung, có thông tin về `RmLinuxVbiosOverride` và môi trường; file có thể bị cắt giữa phần cấu hình.
3. Người dùng gửi `CMP40HX_ORIGINAL_1MB.bin.txt` và `cmp40hx_t4.bin.txt`: thực chất là binary, chỉ đổi đuôi, không phải text. Phân tích trước chỉ ra các trường float32 liên quan VFE/điện áp và checksum; cần tái xác minh bằng parser.
4. Người dùng yêu cầu prompt `/goal` cho Hermes. Prompt đầu thiên về V/F, GSP; người dùng sau đó làm rõ mục tiêu chính là **reverse engineering toàn GPU và fuse/OTP**, không phải tăng xung/điện.
5. Người dùng gửi `cmp40hx_research.tar.gz`, sau đó `cmp40hx_research_v14_final.tar.gz`, và cuối cùng `cmp40hx_research_v15_final.tar.gz`.
6. Trợ lý trước đánh giá v14 chưa đạt semantic coverage: fuse nhiều word chưa giải nghĩa, MMIO nhiều register mới chỉ tổng hợp, VBIOS nhiều table chưa decode đầy đủ, GSP thiếu function inventory, firmware blob chưa disassemble.
7. Hermes báo v15 hoàn tất Phase 15, 162/162 PASS. Trợ lý trước phản biện rằng test count cần đếm lại, chưa giải quyết unknown mới, và tìm lỗi trong script giải mã RISC-V JAL/callback.
8. Trợ lý đã soạn `/goal` Phase 16 để sửa công cụ, dựng CFG/callgraph, kiểm tra fuse/OTP, firmware, VBIOS và MMIO; người dùng nay muốn chuyển công việc sang Codex CLI.

## 4. Các phát hiện/giả thuyết cần kiểm toán trong Codex

- GSP dispatcher tại file offset/địa chỉ được báo `0x04F575FC`; phải xác minh mapping ELF virtual address ↔ file offset.
- Trợ lý trước báo lỗi trong `PHASE15/gsp_find_caller2.py` về giải mã JAL immediate. Đã nêu lệnh tại `0x04F57970` là `0xC8DFF06F`, `jal x0` với displacement `-0x374`, target `0x04F575FC`. **Hãy kiểm tra độc lập**, không chấp nhận chỉ vì handoff nói vậy.
- Callback: `0x04F57618: lhu a2,-0x88(s0)` và `0x04F57620: jalr a5` theo disassembly được trích; cần phân tích CFG/dataflow để xác định argument thật, không suy luận chỉ từ vị trí field.
- Fuse dump được báo 3072 word = 12,288 byte; 352 word có dữ liệu không zero/non-poison theo tiêu chí cũ. Không đồng nhất requested span, dumped span và actual fuse aperture. Không khẳng định một word `1` là/không là OTP cell chỉ dựa pattern.
- VBIOS có 42 table được parse theo thống kê trước nhưng rất ít table được giải nghĩa đầy đủ. ROM shadow @BAR0 `0x300000` được báo khớp `rom[0x28600:]` trừ 14 byte — cần xác minh lại.
- `ucodes_tu10x.bin` được báo có 11 blob; blob 6 và 8 cùng kích thước 125,696 byte, khác 24 byte. Chưa đủ cơ sở khẳng định mã hóa/phiên bản từ entropy hoặc ngày tháng.
- V15 được báo còn 35 unknown mở trên tổng 45; cần kiểm tra lại `UNKNOWN_DATABASE.json`, coverage và checkpoint.
- 162/162 PASS là tuyên bố Hermes. Trợ lý trước nói đếm được 161 dòng PASS khi chạy `verify_all.py`; hãy chạy lại và phân loại test kiểm tra sự hiện diện/nhất quán dữ liệu với test xác minh ngữ nghĩa.
- Có mâu thuẫn giữa các phiên bản báo cáo/checkpoint; kiểm tra provenance, timestamp, dữ liệu thô.

## 5. Nhiệm vụ ưu tiên khi Codex CLI tiếp nhận

### Phase 16 — Audit và khám phá thực chất

1. **Inventory:** giải nén v15 ở thư mục làm việc riêng; liệt kê file, checksum, checkpoint, phase reports, raw binary, scripts. Không ghi đè archive.
2. **Reproducibility:** chạy test từ thư mục sạch; đếm test thực tế, kiểm tra assertions và độc lập hóa phép xác minh.
3. **Fix RISC-V decoder:** kiểm tra JAL, AUIPC+JALR, compressed control flow, sign extension, mapping file offset/VA; thêm regression tests; tạo CFG và xrefs có provenance.
4. **GSP:** dựng function inventory, caller/callee, dispatcher/callback dataflow, RPC, register accesses; không gán ngữ nghĩa chỉ từ strings.
5. **Fuse/OTP:** chuẩn hóa dump, phân biệt OTP physical vs shadow/strap/status; đối chiếu driver/Nouveau/envytools và topology; giữ unknown khi chưa có bằng chứng.
6. **VBIOS:** kiểm toán parser, 42 tables, unknown fields, image partitions, cross-references và shadow diff.
7. **Firmware:** kiểm toán 11 blobs, metadata, container, ISA, load addresses, khác biệt blob 6/8; chỉ disassembly offline các phần có thể đọc hợp lệ.
8. **MMIO/topology/memory:** ánh xạ register/bitfield với bằng chứng, phân loại BADF, GPC/TPC/ROP/L2, VRAM reserved.
9. **Deliverables:** `PHASE16/TOOLCHAIN_AUDIT.md`, `GSP_CFG_REPORT.md`, `FUSE_OTP_SEMANTICS.md`, `VBIOS_DEEP_ANALYSIS.md`, `FIRMWARE_DEEP_ANALYSIS.md`, `MMIO_TOPOLOGY.md`, `NEW_DISCOVERIES.md`, `REGRESSION_TESTS/`, `EVIDENCE_LEDGER.md`, `UNKNOWN_STATUS.md`, `CHECKPOINT.json`.

### Phương pháp

- Mỗi phát hiện: nguồn file/hash, offset/address, raw value, phương pháp tái lập, bằng chứng ủng hộ/chống, mức tin cậy.
- Phân biệt `MEASURED`, `DECODED`, `CORROBORATED`, `INFERRED`, `UNKNOWN`, `BLOCKED`.
- Không tuyên bố reverse engineering GPU hoàn tất chỉ vì chạy hết script hoặc có nhiều PASS.
- Chỉ chạy offline/read-only an toàn. Không flash/nạp ROM, không ghi MMIO/fuse/PCIe, không reboot/reload driver, không overclock/undervolt, không triển khai exploit/bypass mới. Nếu cần thao tác ngoài phạm vi, lập đề xuất và chờ người dùng phê duyệt.

## 6. Danh sách file đính kèm cần đặt cùng thư mục handoff

- `BAO_CAO_DAY_DU.md` — báo cáo gốc.
- `gemini-code-1793690442460.md` — handoff môi trường, có thể bị cắt.
- `CMP40HX_ORIGINAL_1MB.bin.txt` — **binary ROM**, giữ nguyên byte.
- `cmp40hx_t4.bin.txt` — **binary T4**, giữ nguyên byte.
- `cmp40hx_research.tar.gz` — gói nghiên cứu đầu.
- `cmp40hx_research_v14_final.tar.gz` — gói v14.
- `cmp40hx_research_v15_final.tar.gz` — gói v15, **nguồn làm việc chính**.
- `cmp40hx_v15_independent_audit.py` — script kiểm toán độc lập từ cuộc trò chuyện trước, cần kiểm tra lại.

## 7. Lệnh gợi ý để bắt đầu trong Codex CLI

Trong thư mục có archive và handoff:

```bash
mkdir -p work_v15
# Xem danh sách và kiểm tra đường dẫn archive trước khi giải nén:
tar -tzf cmp40hx_research_v15_final.tar.gz | head -80
# Chỉ giải nén sau khi xác nhận không có path traversal/symlink nguy hiểm.
```

**Prompt mở đầu cho Codex:**

> Đọc `CODEX_CMP40HX_HANDOFF.md` và kiểm tra toàn bộ `cmp40hx_research_v15_final.tar.gz`. Tiếp tục Phase 16 theo mục tiêu reverse engineering toàn diện GPU, ưu tiên kiểm toán dữ liệu và sửa decoder GSP trước, sau đó fuse/OTP, VBIOS, firmware và MMIO. Không nghiên cứu overclock. Chỉ thao tác offline/read-only. Viết phát hiện có bằng chứng và checkpoint; không tuyên bố hoàn tất toàn GPU khi còn unknown.

## 8. Giới hạn của bản bàn giao

Bản này tổng hợp các trao đổi và kết quả được báo trong cuộc trò chuyện, không phải transcript nguyên văn. Các đánh giá của trợ lý trước là **đầu mối cần kiểm tra**, không thay thế việc Codex đọc trực tiếp archive và chạy test. Không có quyền truy cập host Hermes trong môi trường ChatGPT này.

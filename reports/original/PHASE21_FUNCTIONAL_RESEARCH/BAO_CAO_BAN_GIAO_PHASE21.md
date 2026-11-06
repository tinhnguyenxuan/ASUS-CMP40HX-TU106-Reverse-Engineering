# Báo cáo bàn giao Phase 21 — CMP 40HX / TU106

**Ngày bàn giao:** 2026-11-04  
**Trạng thái:** `IN_PROGRESS` — chưa hoàn tất  
**Checkpoint:** `status=IN_PROGRESS`, `complete=false`  
**Firmware chính:** `work_v15/outputs/gsp_tu10x.bin`  
**Firmware SHA-256:** `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`  
**GSP/RM:** `615.78.08`

## Kết luận ngắn

Đính chính khi tiếp tục phiên: summary `local_inventory_2026-11-04_141233.json` dùng nguồn cũ, không phải capture mới. Output collector mới đã lưu nguyên văn trong `evidence/local_inventory_resume_raw.json` lúc `2026-11-04T14:40:37.565111Z`, vẫn không có GPU local phù hợp. Socket hiện tạo được; kết nối thực tế tới `<REDACTED_LAB_IP>:22` trả `No route to host` sau một lần timeout. Xem `evidence/target_access_resume.json`. Các nhận định EPERM bên dưới chỉ mô tả môi trường trước đó.

Đã hoàn tất phần reverse-engineering tĩnh, provenance, audit artifact và thiết kế quy trình capture read-only. Chưa thể kết luận hiện tại GPU có hay không có display silicon/routing, cũng chưa thể kết luận khôi phục display hoặc compute là khả thi, vì sandbox không truy cập được target và không có bằng chứng PCB/ROM tham chiếu độc lập đủ mạnh.

Không có firmware patch, GPU register/BAR write, `/dev/mem`, reset/reload driver, flash ROM, thay đổi registry, exploit hay thao tác đặc quyền nào được thực hiện trong Phase 21.

## Bằng chứng tĩnh đã xác minh

- Worker `RmDisableDisplay` tại `0x04b30030` nhận diện các key `RMRunFub`, `RMFubUseCaseMask`, `RmDisableDisplay` và ghi các kết quả vào các field tương ứng; `RmDisableDisplay == 1` được cache/latch tại object offset `+0x334`.
- Consumer tại `0x04b20f54` đọc `a1+0x334`: khi bằng 0 có thể trả output byte `1`; khi khác 0 đi vào diagnostic path và trả `0`, sau các điều kiện phụ khác.
- `+0x737` là byte cache nhận kết quả từ một indirect call qua slot cùng object `+0xb8`; method/writer chính xác chưa được giải quyết.
- `+0x790` là child pointer trong consumer cụ thể, sau đó đọc child byte `+0x88`; scan toàn image chứng minh offset này có collision ở context khác, nên không gán semantic toàn cục.
- Constructor paths cài consumer tại object-table slot `+0x158`; các predicate `+0x1b0` và `+0x1c8` đi qua accessor selector `0x3814`. Raw predicates đã giải mã, nhưng tên field/class proprietary và semantic TU106 chính xác vẫn chưa biết.
- Literal diagnostic ở `0x04b20fcc/0x04b20fd0` resolve tới `0x05995528`, nằm ngoài mapped inner-ELF sections.
- Host exact-tag `615.78.08` dispatch chọn `gpuFuseSupportsDisplay_GM107` cho TU102/TU104/TU106/TU116/TU117. Header GM107 định nghĩa `NV_FUSE_STATUS_OPT_DISPLAY = 0x21c04`, `DATA=bit 0`, `ENABLE=0`. Raw archived value tại `0x21c04` là `1`, nên archived predicate đánh giá false. Đây chỉ là historical host-side result; không chứng minh OTP/shadow hiện tại hoặc display silicon vắng mặt.
- `0x3814` chỉ có định nghĩa trong các header GA100/GB100 cross-generation cho field khác; không có TU106 semantic definition cục bộ.

## ROM/DCB/PCB

- Inventory có 16 unique ROM contents được giữ lại; các variant chủ yếu khác rất ít byte so với bản CMP40HX gốc hoặc là bản truncate/derivative.
- Quét lại 26 file ROM 1 MiB trong workspace và `/tmp`: 15 hash quan sát được, **0 hash mới** ngoài inventory cũ.
- Parsed communications/GPIO/connector tables của 16 contents giống nhau; connector entries bằng 0. DCB mô tả board tables, không chứng minh physical routing.
- Vùng legacy DCB/script `0x28600:0x37a00`: 14 bản giống baseline; `gen3_a.rom` khác 2 byte, `t_clk.rom` khác 5 byte. Parser script crash sau BIT/DCB errors; không gán semantic script.
- Chưa có ROM tham chiếu độc lập, revision-matched, có chain-of-custody đủ mạnh.
- `CG161P REV2.00` và `TU106-100-A1` chỉ là identifiers được cung cấp/secondary; chưa có ảnh PCB xác thực, schematic, boardview, package pinout hoặc continuity. Không phân loại `BOARD_ROUTED` hay `BOARD_UNROUTED`.

## Runtime và target access

Historical saved runtime trong `work_v15/TOPOLOGY/silicon_topology.json` ghi CMP 40HX, part `1F0B-100-A1`, BDF `00000000:03:00.0`, UUID `GPU-REDACTED`, VBIOS `90.06.67.00.06`, GSP `615.78.08`, Display Attached `No`, Display Active `Disabled`. Đây là historical evidence; `display_probe.json` thiếu command/timestamp metadata và 11 bản copy byte-identical.

Collector đã in output tại `2026-11-04T14:12:33.240212Z`, nhưng summary sau đó đọc nhầm file cũ lúc `09:03:29Z`. Vì vậy artifact dưới đây không xác minh capture mới tại `14:12:33Z`:

- Không có `10de:1f0b` local device.
- `/proc/driver/nvidia/version` không tồn tại.
- `nvidia-smi` missing.
- Artifact: `evidence/local_inventory_2026-11-04_141233.json`.

Fresh target-package collector v5:

- File: `/tmp/phase21-target-package-local-v5/target_package.json`
- BDF requested: `0000:03:00.0`
- Verifier: PASS
- 14 records, 0 successful reads, 14 failed reads
- Package SHA-256: `1380c52e1e2a02c6796543b74ca4cb26b1f12d187c90e537fda389384da6d863`
- Manifest SHA-256: `c5fc387227816bd77551036f227d660223c9e1e61dc8940379ad605135110192`
- Classification: `LOCAL_SANDBOX_ONLY`; không đóng runtime blocker.

Target access rerun v2 tại `2026-11-04T14:13:50.360780Z`:

- `/proc/net/route` empty.
- Chỉ thử tạo AF_INET TCP socket; không connect/authenticate.
- Kết quả: `PermissionError: [Errno 1] Operation not permitted`.
- Artifact: `evidence/target_access_capability_rerun_v2.json`.

## Hermes MCP

Hermes MCP đã được gọi thành công nhưng chỉ expose một channel:

- `agent:main:telegram:dm:1881666059`
- target `telegram:1881666059`

Không có target/API riêng cho “Hermes gốc”, Vilao hoặc Qwen3.8 Flash. Hermes xác nhận chỉ có thể ghi file local và trả lời trong Telegram DM; không có tool gửi sang external API/service.

Các báo cáo Hermes Phase 15–20 đã được hash và phân loại historical secondary. Phase 19 và Phase 20 mâu thuẫn về trạng thái card (300 MHz so với 1905 MHz), nên không dùng làm current state. Runtime topology/display probe trong Hermes cache byte-identical với bản `work_v15`, không thêm quan sát độc lập.

## Năm blocker còn mở

| ID | Cần để đóng | Trạng thái |
|---|---|---|
| `B-RUNTIME-TARGET` | Target package có successful reads, đúng BDF, timestamp và verifier PASS | OPEN |
| `B-EFFECTIVE-REGISTRY` | Runtime registry/NVKV hiện hành cho `RmDisableDisplay`, `RMRunFub`, `RMFubUseCaseMask` | OPEN |
| `B-FUNCTIONAL-DISPLAY` | Display/KMS plus EGL/OpenGL/Vulkan/CUDA tests gắn target UUID | OPEN |
| `B-REFERENCE-ROM` | ROM TU106 revision-matched độc lập, provenance xác thực | OPEN |
| `B-PCB-ROUTING` | Ảnh PCB xác thực plus schematic/boardview/continuity | OPEN |

## Requirement matrix hiện tại

- `cuda_capability`: `MISSING_CURRENT`
- `compute_restriction`: `PROVEN_STATIC`
- `display`: `PROVEN_STATIC` (policy/dataflow; physical capability chưa chứng minh)
- `headless_graphics`: `MISSING_CURRENT`
- `fuse`: `HISTORICAL_ONLY`
- `cross_sku_vbios`: `UNKNOWN`
- `gsp_gates`: `PROVEN_STATIC`
- `feasibility`: `UNKNOWN`
- `safety_repro`: `PROVEN_STATIC`
- `deliverables`: `PROVEN_STATIC`

## Artifact quan trọng

- [CHECKPOINT.json](CHECKPOINT.json)
- [PHASE21_CURRENT_STATE.md](PHASE21_CURRENT_STATE.md)
- [PHASE21_STATUS_REPORT.md](PHASE21_STATUS_REPORT.md)
- [EVIDENCE_LEDGER.md](EVIDENCE_LEDGER.md)
- [REQUIREMENTS_AUDIT.md](REQUIREMENTS_AUDIT.md)
- [TARGET_CAPTURE_CHECKLIST.md](TARGET_CAPTURE_CHECKLIST.md)
- [evidence/blocker_register.json](evidence/blocker_register.json)
- [evidence/requirement_matrix.json](evidence/requirement_matrix.json)
- [evidence/local_target_package_v5.json](evidence/local_target_package_v5.json)
- [evidence/hermes_channel_capability.json](evidence/hermes_channel_capability.json)
- [evidence/closure_readiness.json](evidence/closure_readiness.json)
- [tools/collect_target_package.py](tools/collect_target_package.py)
- [tools/verify_target_package.py](tools/verify_target_package.py)
- [tools/verify_phase21_integrity.py](tools/verify_phase21_integrity.py)

## Lệnh kiểm tra khi tiếp tục

```bash
python3 PHASE21_FUNCTIONAL_RESEARCH/tools/verify_phase21_integrity.py
python3 PHASE21_FUNCTIONAL_RESEARCH/tools/audit_artifact_integrity.py
python3 -m py_compile PHASE21_FUNCTIONAL_RESEARCH/tools/*.py
```

Khi có target thật và được phép capture read-only, chạy collector theo `TARGET_CAPTURE_CHECKLIST.md`, giữ nguyên `target_package.json` và `SHA256SUMS`, chạy verifier, rồi chỉ nâng blocker khi có successful reads và provenance đầy đủ.

## Audit cuối phiên

Aggregate integrity verifier: PASS. Artifact-linkage audit: PASS. 55 evidence JSON parse thành công. Toàn bộ Python tools compile thành công. Checkpoint vẫn `IN_PROGRESS`, `complete=false`. Không có current-target evidence đủ mạnh để tuyên bố hoàn tất hoặc phân loại phần cứng.

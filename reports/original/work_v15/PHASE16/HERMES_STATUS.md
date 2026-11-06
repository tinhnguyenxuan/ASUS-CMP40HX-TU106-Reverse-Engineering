# HERMES STATUS — PHASE16 (CMP40HX / TU106 research continuation)

Thời gian thực: 2026-11-03 21:34:44 +07
Môi trường: chỉ thao tác file offline, không đụng GPU, không thay đổi cấu hình/model.

## 1. Lệnh đã chạy

`/usr/bin/python3 -B -m unittest discover -s /home/REDACTED_USER/codex-work/work_v15/PHASE16/REGRESSION_TESTS -v`

Đầu ra (bao gồm stdout + stderr) đã lưu tại:
`/home/REDACTED_USER/codex-work/work_v15/PHASE16/hermes_regression.log`

## 2. Kết quả test thực tế (không đoán, từ log)

- Ran 18 tests in 0.182s → OK
- Exit code: 0
- Pass: 18 / Fail: 0
- Kết luận: PASS. Log KHÔNG chứa ModuleNotFoundError; capstone 5.0.7 đã có sẵn, import thành công.
- File test: `/home/REDACTED_USER/codex-work/work_v15/PHASE16/REGRESSION_TESTS/test_riscv_audit.py` (18 test case: DecoderTests 11 + FirmwareEvidenceTests 7), toàn bộ đã thu thập và chạy.

## 3. Kết luận đọc từ artifact Codex (chưa tự chứng minh lại)

Nguồn: `/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_summary.json` — tất cả con số dưới đây chỉ là nội dung tệp artifact Codex, tôi ĐÃ ĐỌC tệp, CHƯA tự kiểm chứng lại bằng ELF/disassembly:

- firmware_sha256: `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`
- capstone_version: 5.0.7
- inner_elf_offset: 64
- corrected_loop_va: 83195324; loop_file_offset: 16086524
- function_candidate_start: 83194684
- table_base_va: 68841648; table_base_file_offset: 1732848; entries: 186; ascii_names: 186
- xrefs (2 mục):
  1. pc 82865180 / file_offset 15756380, raw `e7804072`, kind `indirect_call`, encoding `adjacent_auipc_jalr`, target 83194684
  2. pc 83196208 / file_offset 16087408, raw `6ff0dfc8`, kind `jump`, target 83195324, rd 0

## 4. Việc kế tiếp (đề xuất, chưa làm trong lượt này)

Kiểm chứng độc lập:
1. ELF mapping: file offset ↔ virtual address (inner_elf_offset 64, table_base_va/offset, loop_va/offset, function_candidate_start).
2. Caller/callback: hai xref ở trên, riêng biệt indirect_call tại `82865180` (target `83194684`) và jump tại `83196208` (target `83195324`).
3. Callback argument: CFG/dataflow xung quanh `0x04F57618: lhu a2,-0x88(s0)` và `0x04F57620: jalr a5`, xác định argument thật chứ không suy luận từ vị trí field.

## 5. Báo cáo paths

- Log test: `/home/REDACTED_USER/codex-work/work_v15/PHASE16/hermes_regression.log`
- Tệp tham khảo đã đọc: `/home/REDACTED_USER/codex-work/CODEX_CMP40HX_HANDOFF.md`, `/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_summary.json`

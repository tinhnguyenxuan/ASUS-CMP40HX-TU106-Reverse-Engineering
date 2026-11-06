# SEC2_ISA_VALIDATION.md

## Ket qua kiem toan ISA SEC2

### 1. ISA sái sai lệ (FALSE DECODE)

Capstone dục càu đỡ `CS_ARCH_RISCV + CS_MODE_RISCV32 + CS_MODE_RISCVC` để disassemble `image.bin.zst` (61184 bytes).
**Lỗi:** NVIDIA SEC2 Falcon **KHÔNG phải RISC-V**. Falcon là ISA proprietary của NVIDIA, khác RISC-V về encoding, register, và instruction set.

Các lệnh sau đây trong báo cáo cũ **KHÔNG ĐƯỢC coi là mã máy đã xác minh**:

| Địa chỉ (file offset) | Lệnh Capstone (RISC-V+C) | Phân loại | Lý do |
|---|---|---|---|
| 0x238 | `c.lui t3, 0xfffe3` | FALSE DECODE | Falcon không có LUI/C.LUI như RISC-V |
| 0x206 | `lb zero, 0x4f(t3)` | FALSE DECODE | Falcon không có LB/LBU như RISC-V |
| 0x35A2 | `lb sp, -0x25d(t3)` | FALSE DECODE | Tương tự trên |
| 0x04990 | `sb s2, 0x522(zero)` | FALSE DECODE | Falcon không có SB như RISC-V |
| 0x0188C | `sw zero, 0x7e0(s2)` | FALSE DECODE | Tương tự trên |
| 0x0006A | `jal t0, 0xd0010` | FALSE DECODE | Falcon không có JAL như RISC-V |

**Kết luận:** Toàn bộ phân tích SEC2 từ Capstone RISC-V+C là **INVALID**. Không nên trích dẫn bất kỳ lệnh, hằng số, hoặc địa chỉ MMIO nào từ kết quả disassembly này.

### 2. ISA đúng cần dùng

Cần disassembler Falcon ISA chính thống (NVIDIA falcon disassembler, hoặc nhà phân tích binary có module Falcon). Các công cụ có thể dùng:
- `envytools` / `nouveau` firmware disassembly (nếu có module Falcon)
- Binary analysis tool hỗ trợ NVIDIA Falcon ISA (ví dụ: các plugin Ghidra/IDA cho Falcon)
- Ré-eng disassembly từ Nouveau project (reverse-engineered Falcon ISA spec)

### 3. Entry point / Execution address

Chưa xác định được. File offset 0 trong `image.bin.zst` **không nhất thiết** là execution address. Falcon firmware thường có vector table tại một offset cụ thể, không phải byte đầu tiên.

### 4. Hạn chế

- Không có disassembler Falcon ISA trên máy mục tiêu.
- Không được phép cài thêm công cụ reverse-engineering (theo ràng buộc offline/read-only).
- Kết quả disassembly Capstone RISC-V+C đã xem xong → lọt bỏ, không trích dẫn trong báo cáo chính thấc.

## Ghi chú PONYTAIL

# ponytail: SEC2 ISA misidentified as RISC-V+C. All previous disassembly results are false decodes. Do not cite any Falcon instruction from Capstone output. Need proper Falcon disassembler to proceed.

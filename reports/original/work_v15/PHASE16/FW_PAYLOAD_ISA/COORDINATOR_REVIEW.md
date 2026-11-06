# Coordinator review — FW_PAYLOAD_ISA

Reviewed `payload_isa_verified.json`, `run.log`, report, and current `/usr/bin/python3` environment.

- Inventory covers 38 external entries and correctly preserves uncertainty around general ISA/role mapping.
- The JSON explicitly records `capstone_available: true`; this conflicts with the report's statement that Capstone is unavailable and RISC-V could not be disassembled. The environment used for this review has Capstone 5.0.7 at `/home/REDACTED_USER/.local/lib/python3.12/site-packages/capstone`; verify worker runtime/interpreter and run a real RISC-V decode. Do not repeat the unavailable claim without evidence.
- Four bounded Falcon decodes have only medium confidence and low valid-instruction ratios (0.136–0.389); this supports plausible Falcon code presence, not complete payload identity or role. Code-start selection by longest valid prefix is not sufficient alone.
- The report and data disagree in filename spelling (`payload_asi_verified.json` vs actual `payload_isa_verified.json`), a minor reproducibility typo.
- All conclusions about unexamined entries, engine mapping, compression/encryption, and firmware roles remain open.

Follow-up dispatched as `fw_payload_riscv_v1` to resolve RISC-V decoding and broaden per-payload evidence without installing tools or making hardware changes.

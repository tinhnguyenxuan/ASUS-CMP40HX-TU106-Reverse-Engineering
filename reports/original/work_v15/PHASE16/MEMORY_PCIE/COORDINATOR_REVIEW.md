# Coordinator review — MEMORY_PCIE

Reviewed `memory_pcie_verified.json`, report, and source references.

- PCI identity and BAR span claims cite archived config/resource bytes; BAR3 dump provenance is internally tied to the dump tool's 256 KiB window. This is archived evidence, not a fresh runtime measurement.
- Link status is correctly reported from saved `q3_pcie.txt`: endpoint target 5 GT/s, runtime 2.5 GT/s x16; no inference that root port capped it.
- BAR3 inventory and rejected SKU/PDE/PTE hypotheses preserve raw values and reject unsupported structures. BAR3 mapping, allocation semantics, and topology remain UNKNOWN.
- VRAM accounting retains the 1 MiB discrepancy; WPR2 arithmetic uses source field extraction and does not subtract it from NVML reserved memory without overlap evidence.
- No new hardware access occurred. This report completes a bounded archived PCIe/memory audit, not full MMIO/GMMU or GPU reverse engineering.

# Next research steps, ordered by evidence strength

1. Obtain target read-only inventory and original Phase19/20 logs; tie each capture to BDF, UUID, board/revision, ROM and firmware hashes, driver and preexisting patch state. Do not reset to obtain stock. Run collect_readonly.py without sudo; keep absent/denied results rather than reconfiguring the driver.
2. Prioritize compute correctness and current CUDA/Tensor/library support: public functional evidence is stronger than display recovery evidence. Separate correctness from throughput and missing tool support. Avoid redundant large benchmarks; the prompt explicitly permits using public compute research when adequate.
3. Trace the exact 615.78.08 display fuse HAL dispatch and physical-RM display-IP reply. Recover actual inputs and return statuses. A host generic error or static child list does not locate the restriction in silicon.
4. Continue CCB/GPIO and devinit analysis; use the modern Nouveau v4.1 consumer as cross-check. Resolve upper-bit extensions without assuming reserved bits are zero. Obtain trusted TU106 reference ROM with matching revision metadata; the supplied T4 derivative is not one.
5. Obtain CG161P REV2 physical board evidence before designing any output modification. No software-only display restoration claim is presently supported.
6. Only if evidence suggests a specific reversible state-changing experiment, produce TEST_PROPOSAL.md with exact preconditions, expected observation, abort conditions and verified rollback, then seek owner approval. No exploit/unlock is authorized for automatic execution by the current prompt.

Completion requires each prompt requirement to have evidence or a clearly documented unresolved limitation; creating filenames or passing parser checks cannot establish restoration. Current phase remains IN_PROGRESS because live validation, source dataflow, cross-SKU and PCB evidence are incomplete.

# Compute restrictions — static source audit, incomplete

The local third-party patch snapshot is preserved at evidence/sources/0001-cmp40hx-unlock.patch; its exact bytes are hashed in sources/manifest.json. Upstream commit and release are unknown, so this snapshot is not assumed identical to the current website or driver 615.78.08.

The patch changes host RM's Turing Booter flow (kernel_gsp_booter_tu102.c) and Turing GSP support. Its predicate s_isCmp40ComputeUnlock compares PCIDeviceID against packed 0x1F0B10DE; its subdevice macro unconditionally returns true. Thus this is a broad patch target predicate, not proof of the stock driver's CMP classification or a device-ID unlock.

Source constants identify 0x409664/0x40966c as FECS SM speed override registers and use 0x88888888/8 as the desired state. FECS PLM is separate at 0x409650. Source assertions read selectors and privilege/WPR state during the Booter handoff. This establishes what the patch attempts and checks; it does not establish every selector bit's silicon meaning, the mapping from nibbles to SMs/TPCs, or the original writer's firmware PC. Those remain UNKNOWN. Do not infer per-SM mapping from the number of repeated nibbles.

The patch participates in SEC2 Booter execution and security-state handoff before normal GSP initialization; it is not an ordinary userspace CUDA permission change. No patch was applied, built, installed or run here. Exploit test execution would violate the prompt's prohibition on unapproved privileged firmware operations; a future state-changing test needs a concrete TEST_PROPOSAL and owner approval.

Phase19/20's claim that GSP immediately restores host writes is secondary testimony until timestamped raw traces are recovered. Competing explanations include privilege rejection, reset/reinitialization and a firmware writer. Their distinctions require readback timing, protection/error status and firmware/source dataflow. A later readback alone cannot identify the writer. Driver unload/reload persistence cannot establish persistence across a genuine loss of board power.

Public maintainer reports distinguish instruction/workload throughput limits from CUDA availability, and identify a separate Vulkan pipeline command-generation delay. These are outside observations, not measurements of this card. Reference: https://github.com/Cyridd/cmpunlocker . The static snapshot lacks sufficient evidence to claim the current card's Tensor correctness, throughput, library support or profiling status.

Next: recover target firmware hashes and Phase19/20 traces; trace matched stock initialization/capability consumers; keep FECS/GPCCS execution, SEC2 security setup, GSP policy and userspace command emission as separate hypotheses until linked by evidence.

## ROM and generation follow-up

COMPUTE_SELECTOR_EVIDENCE.md now documents original VBIOS condition record 50 testing FECS readout 0x409660 bit16. This is positive evidence for a firmware-table relationship to the cluster, not a write or an original throughput initialization proof. Ampere's differently addressed issue-rate selectors provide comparison context only; their BF16 claims and field assignments are not TU106 measurements.

## Captured API versus selector encoding

ISSUE_RATE_ENCODING_BOUNDARY.md compares the captured V2 values to saved legacy enum names. IMLA6 has a legacy1/64 label; FMLA16/32 value6 lacks a matching legacy label in that header. No cross-API translation, actual throughput divisor or FECS nibble assignment follows. Bounded CUDA/Tensor/SGEMM correctness is already demonstrated; see the regenerated RESTORATION_FEASIBILITY_MATRIX.md for function-specific scope.

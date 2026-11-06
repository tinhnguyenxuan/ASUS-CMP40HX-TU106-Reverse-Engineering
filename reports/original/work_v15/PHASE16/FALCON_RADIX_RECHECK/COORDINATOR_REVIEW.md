# Coordinator review

Job `falcon_radix_recheck_v1` completed with runner exit code 0. The source call `str(skip)/str(limit)` and envydis `%x` parse prove the earlier radix error. Explicit hex probes now compare output bytes to the original payload slices for eight candidate slots. Those matches ground the disassembly bytes but do not prove any true entry or engine mapping.

The bounded CFG audit finds unsound fallthrough edges after unconditional terminators in the earlier deep worker and indirect `call $r1` targets. Its 0 mid-region splits is limited to the inspected 0x200-byte windows. Earlier deep-worker entry/coverage claims must remain provisional until CFG repair and independent entry cross-references.

# Interim coordinator audit (job still running)

The current machine JSON separates 8 candidate-entry traversals from thousands of linear-sweep-only regions. Its byte verification and explicit hexadecimal envydis arguments address the prior radix defect. Entry and engine remain UNKNOWN.

The reported `unresolved_edges=0` is incomplete: the sole reachable block in every slot ends immediately before an invalid/undecodable span, with no terminal instruction and no recorded outgoing edge. From current `machine.json`: slot 20 candidate 0x2A block end 0x68 then invalid [0x68,0x6C); slots 150/156 candidate 0x16 end 0x34 then invalid [0x34,0x38); slots 481/484/487/490/493 end 0x37 then invalid [0x37,0x3B). Each should be labeled as a decode-gap or unresolved continuation, and the bounded reachability must not be called all executable code. The invalid bytes may be data, another ISA mode, or a gap between codelets; current evidence cannot decide.

The worker is still running and may revise output. Recheck the final machine JSON before accepting these counts.

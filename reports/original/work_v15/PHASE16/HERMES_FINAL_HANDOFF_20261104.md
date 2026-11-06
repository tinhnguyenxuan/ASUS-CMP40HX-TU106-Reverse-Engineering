# CMP 40HX / TU106 reverse engineering — Codex handoff to Hermes

Date: 2026-11-04 (Asia/Bangkok). Scope remains the entire offline CMP 40HX/TU106 evidence set. This handoff closes Codex's current supervision pass; it does **not** assert complete GPU reverse engineering. User asked for direct Hermes instructions, without `/goal`.

## How to use this handoff

Read this file, `COORDINATION.json`, `UNKNOWN_DATABASE.json`, and the referenced coordinator reviews before promoting any conclusion. Preserve originals and previous reports. Work from saved binaries, ROM, JSON dumps, and official public source with exact bytes/offsets/hashes. Each new result needs an isolated directory, a reproducible command or script, machine-readable evidence, and a concise report distinguishing proven, inferred, and unknown facts. Do not turn “no evidence in a bounded scan” into absence from the whole GPU.

The requested original Hermes session `20261020_130845_d07427d2` could not be resumed (`invalid_params`). Phase16 work has instead used fresh detached direct Hermes jobs through MCP, without `/goal`; do not claim those jobs executed inside the original session. The four latest jobs below are terminal with runner exit code 0 and no live worker processes.

## Current evidence anchors

- Archive: `../../cmp40hx_transfer/cmp40hx_research_v15_final.tar.gz`, SHA256 `323c96e5bf7d5512ae3e55f6040afa81373c7ab44d1f059165c536fbd2c51a45`.
- GSP binary `outputs/gsp_tu10x.bin`: 22,901,632 bytes, SHA256 `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`.
- NVUCODES `outputs/ucodes_tu10x.bin`: 8,837,632 bytes, SHA256 `6027ab3736f733b5a06e6e61aaae957d1f990426a263849ebcfa8a49eeb4a5d0`. Header has 496 record slots, 38 external payloads, 458 zero external slots; do not conflate the external archive with GSP's distinct internal table.
- Phase16 unknown overlay: `UNKNOWN_DATABASE.json` has 45 items, 36 open and 9 resolved. The baseline database is preserved. Full completion has not been established for GSP, Falcon, topology, VBIOS, MMIO, fuse semantics, memory, security, or engine roles.

## Latest four jobs: accepted facts and corrections

### GSP callback context writer

`GSP_CONTEXT_WRITER/report.md` and `gsp_context_writer.json` verify raw AUIPC/JALR targets: caller `0x04F06C18/1C -> 0x04F5733C`, inner call `0x04F5739C/A0 -> 0x05281930`, helper `0x04F57644/48 -> 0x04F075EC`. The latter requires signed AUIPC immediate `-0x50`. The callback at `0x04F575E0` loads its target from `*(s3+0x30)`; its value is **UNKNOWN**. The local window has no proven direct or alias store to that slot. `a0=s3` at the call; `a1` differs by path (first path unknown after call clobber, back edge helper return); `a2` is loaded from a stack slot the helper may alter.

The callee `0x05281930` has bytes in executable memory. The worker's 4096-instruction linear scan crosses function boundaries and is **not** a callee CFG. `sd ...,+0x30(s1/a5)` in the early region is an offset match, not proof that `s1/a5` aliases the context returned to the caller. One return path sets `a0=0` at `0x05281BFC` before `ret 0x05281C48`; other return paths and returned pointer alias remain unresolved. Do not call this callee an allocator or `context+0x30` writer without path-sensitive proof. See `GSP_CONTEXT_WRITER/COORDINATOR_INTERIM_REVIEW.md` for corrected alias-count caveats.

### GSP NVUCODES table / loop path

`GSP_LOOP_FIELD_PROOF/` split the traversed CFG to 516 nonoverlapping blocks and 2205 unique decoded instructions. It demonstrates a local path through `0x0459C6E8` that forms `s9=0x04584790`, `s10=24`, `s8=0`, then `0x0459C708 add a4,s9,s2` and `0x0459C70C lw a5,0x10(a4)` (`flags+16` on internal record 0). The `s7`-derived load at `0x0459C71C` is a separate unresolved table. Other internal table fields `actualSize+0`, `compressedSize+4`, `pData+8`, `relOffset+20` are not proven to reach base `0x04584790`. This is a bounded CFG; indirect callees are not entered.

`GSP_PATH_FEASIBILITY/` independently recomputed graph dominators and confirmed `0x0459C6E8` does **not** dominate loop header `0x0459C6FC` in the recorded graph. It calls a bypass path infeasible because two reads of `MEM(s0-0x84)` require 496 and 0. **Do not adopt that unconditional infeasibility claim.** Between those reads are direct and indirect calls (`0x0459C6B0`, `0x0459C6CC`) whose memory side effects have not been summarized. The absence of an explicit caller-side store does not prove the stack slot unchanged. Therefore the bypass path's feasibility, loop-wide `s9/s10` invariant, and index induction for every feasible visit remain **UNKNOWN** until callee side effects or a frame-escape proof are established. The local first-record `flags+16` access remains supported by its raw path. The previous `s9_defined_in_entry_block=true` flag is false as written: candidate entry is `0x0459C5E0`, definitions are in block `0x0459C6E8`.

### Falcon CFG and decode gaps

`FALCON_CFG_REBUILD/` fixed envydis `-d/-l` radix usage (arguments parsed with `%x`) and byte-matched decoded instructions from eight candidate payload spans. Candidate starts slot 20 `+0x2A`, others `+0x16` are traversal anchors, **not** verified boot entries. Engine roles remain UNKNOWN. Its default-variant CFG reaches only 30–62 decoded bytes before an undecodable span; the final report's `unresolved_edges=0` omits those decode-gap continuations. Thousands of other linear-sweep regions have no demonstrated reachability, which does not prove they are data.

`FALCON_DECODE_GAP/` independently re-read the bytes from the original container. Slot 20 has `3e74fe00` at candidate offset `0x68`; slots 150/156 have `89000000` at `0x34`; slots 481/484/487/490/493 have `89000000` at `0x37`. Under envydis `fuc4/5/6`, slot 20's bytes decode as `lbra 0xfe74`; under `fuc5/6`, the other seven decode as `mov $r9,0`, followed by syntactically valid instructions. Under default/fuc0/fuc3 they are unknown. The actual Falcon ISA version and true entry are **not established** by a verified manifest or payload header; syntax validity alone is not code proof. Rebuild CFG under a source-grounded mode only, or report each variant separately.

### TU106 topology source

The saved fuse dump proves raw `base+0x650=0x0004001F` and `base+0xC1C=0x00000038`; their topology bitfield meaning is UNKNOWN. The saved sparse MMIO snapshot does not include archived `gpc_nr 0x00409604`, `tpc_nr 0x00502608`, or TPC unit probes. `TOPOLOGY_CONSUMER_SEARCH/REPORT.md` reports no relevant definitions/consumers in official NVIDIA open-gpu-kernel-modules tag `615.78.08`, `/tmp/nvsrc`, or `/tmp/envytools`. Public RM code exposes GPC/TPC counts through control interfaces and per-GPC arrays, but does not tie the archived raw addresses to a TU106 bitfield. The archived 3 GPC / 17 TPC / 34 SM / 64 ROP numbers are claims from old prose, not independently decoded counts from retained samples. A 5/6/6 TPC distribution is arithmetically possible; unequal per-GPC counts are not a contradiction. Treat the source search as bounded to the reported trees/tag. Source-provenance reports disagree on an exact tag commit hash; use release tag and saved file hashes until that hash is independently reconciled.

## Other accepted boundaries from earlier reviews

- WPR2 `VAL[31:4]` fields in TU102/Turing public header decode saved raw LO `0x01F7E000` and HI `0x01FFEE00` to `0x1F7E00000` and `0x1FFEE0000`; numerical difference is `0x80E0000` = 128.875 MiB. Public control API documents exclusive end offsets, but the TU106 raw-HI-to-API-end consumer is not found. GH100 registry margin `<<20` is **not** this conversion. No cryptographic validity or WPR allocation overlap with NVML reserved memory is proven.
- PCI endpoint `10de:1f0b`, BAR0 16 MiB, BAR1 64 GiB aperture, BAR3 32 MiB are archived/config evidence; BAR1 is not VRAM size. NVML reports 8192 MiB VRAM in one snapshot; differing snapshots must remain separate.
- MMIO capture samples only 16 bytes per 4 KiB page (0.390625% of 16 MiB). No full-page absence or full GPC/TPC/SM/ROP inventory follows from those samples.
- VBIOS BIT'i' version bytes at ROM absolute `0x289F4` are `00 67 06 90 06`; major byte is `0x90`, independently checked from ROM. PERFORMANCE v60 remains opaque in existing parser; generic short extent is not established. Shadow/partial bank equality does not imply whole-image equality.
- Fuse `BADF510C` occurrences and poison ranges are raw dump facts; display fuse offset `+0xC04` raw value is 1, with TU106 meaning unresolved. Do not import Maxwell enable semantics.

## Prioritized continuation for Hermes

1. Resolve GSP bypass feasibility by tracing memory side effects/escape of `s0-0x84` across calls at `0x0459C6B0` and `0x0459C6CC`, with path predicates. Keep loop-wide dominance UNKNOWN until proven.
2. Build a bounded CFG for callee `0x05281930`; trace each return's `a0`, and alias/reaching definitions for `s1/a5` at stores `0x05281AC4` and `0x05281BD4` relative to the pointer actually returned to caller. Keep callback target UNKNOWN absent proof.
3. Identify Falcon ISA mode/entry from verified firmware metadata or official code, then rerun mode-correct CFG including explicit decode-gap edges. Keep each of the eight slot roles UNKNOWN unless cross-referenced.
4. Continue unresolved VBIOS PERFORMANCE v60, WPR2 TU106 consumer, MMIO/topology bitfields, and remaining Phase16 unknowns with source-grounded offsets. Record missing capture requirements when offline evidence cannot decide.

All continuation must remain offline/read-only: no hardware probes or writes, firmware loading/flashing, driver/reboot changes, key/signature work, bypass, brute force, or exploit work. This is an evidence handoff, not a completion claim.

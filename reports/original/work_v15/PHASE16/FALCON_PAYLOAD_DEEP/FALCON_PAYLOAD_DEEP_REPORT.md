# FALCON_PAYLOAD_DEEP — deep dive, 8 medium-confidence Falcon payload candidates

Slots: [20, 150, 156, 481, 484, 487, 490, 493]

Method: single full-span envydis (-m falcon) pass per verified container span;
every byte accounted as valid instruction or invalid-decode gap; read-only inputs;
no GPU/MMIO/keys/signatures; no tool install; prior analysis under
PHASE16/FW_PAYLOAD_RISCV left untouched.

## Important: prior entry-offset correction
envydis interprets its -d numeric argument as HEX. The prior phase passed decimal
start values, so its entry labels were mislabeled: slot 20 was labeled "0x24" while
the real bring-up starts at 0x2A (0x36 was mid-stream); slots 150/156/481/484/487/
490/493 were labeled "0x10" while the real bootstrap starts at 0x16. All entry
offsets below are re-derived directly from the bytes.
## Per-candidate summary
| slot | offset | size | sha_ok | entropy | regions | gap bytes | code coverage | primary entry | candidate entries |
|------|--------|------|--------|---------|---------|-----------|---------------|---------------|-------------------|
| 20 | 0x00002F00 | 122880 | True | 3.4807 | 4518 | 103056 | 0.1613 | 0x00002A | 0x00002A, 0x00006C, 0x00007C, 0x000094, 0x0000A1, 0x00844D, 0x008895, 0x00BE29, 0x00BEAF |
| 150 | 0x00161100 | 571136 | True | 4.8686 | 33232 | 411628 | 0.2793 | 0x000016 | 0x000016, 0x000038, 0x000094, 0x0000B3, 0x0000BF, 0x0000DB, 0x0000E8, 0x001009, 0x001031, 0x0010B0, 0x0010BD, 0x0010DA, 0x0010E4, 0x001805, 0x00181D, 0x00193D, 0x0019B5, 0x0019D0, 0x005BAD, 0x005BD6, 0x007FFC, 0x028F7D, 0x03F8D2, 0x03F928, 0x03F930, 0x03F977, 0x03F982, 0x03FA53, 0x04841A, 0x04A8D8, 0x04A90D, 0x04AA6B, 0x04AA75, 0x04AA82, 0x0516EB, 0x062E04, 0x077EC0 |
| 156 | 0x0041A400 | 539136 | True | 4.8136 | 30799 | 389551 | 0.2775 | 0x000016 | 0x000016, 0x000038, 0x000094, 0x0000B3, 0x0000BF, 0x0000DB, 0x0000E8, 0x000FC5, 0x000FF9, 0x001075, 0x001082, 0x00109F, 0x0010A9, 0x00179D, 0x0017B5, 0x0018D5, 0x00194D, 0x001968, 0x00399B, 0x00570F, 0x006E8D, 0x01759A, 0x01B8FE, 0x022C9E, 0x04305F, 0x043094, 0x0431F2, 0x0431FC, 0x043209, 0x045F2B, 0x045FAE, 0x046272, 0x0462C0, 0x047235, 0x049A0D, 0x049F20 |
| 481 | 0x007D2800 | 143360 | True | 4.1983 | 5494 | 119803 | 0.1643 | 0x000016 | 0x000016, 0x00003B, 0x000092, 0x0000A8, 0x0000C8, 0x000120, 0x000136, 0x000152, 0x00015F, 0x00167B, 0x0016B6, 0x001730, 0x00175A, 0x003C96, 0x003CAF, 0x003D2D, 0x003D5A, 0x0043B9, 0x004418, 0x004458, 0x004571, 0x0045A5, 0x0045B0, 0x0045BA, 0x0046E0, 0x00474A, 0x004765, 0x00491C, 0x00542A, 0x005482, 0x0054AF, 0x0054C0, 0x00B996, 0x00F1F3 |
| 484 | 0x007F5800 | 157440 | True | 4.5950 | 6625 | 129192 | 0.1794 | 0x000016 | 0x000016, 0x00003B, 0x000092, 0x0000A8, 0x0000C8, 0x000120, 0x000136, 0x000152, 0x00015F, 0x001C7B, 0x001CB6, 0x001D30, 0x001D5A, 0x004E81, 0x004EAF, 0x004F2D, 0x004F3D, 0x004F5A, 0x0055B9, 0x005618, 0x005771, 0x0057A5, 0x0057B0, 0x0057BA, 0x0058E0, 0x00594A, 0x005965, 0x005B1C, 0x00662A, 0x006682, 0x0066AF, 0x0066C0, 0x00C0A7, 0x00FD2B, 0x01038F, 0x011A63 |
| 487 | 0x0081BF00 | 147712 | True | 2.7862 | 3835 | 130848 | 0.1142 | 0x000016 | 0x000016, 0x00003B, 0x000092, 0x0000A8, 0x0000C8, 0x000120, 0x000136, 0x000152, 0x00015F, 0x00137B, 0x0013B6, 0x001430, 0x00145A, 0x001C1A, 0x003C10, 0x003C48, 0x003CBF, 0x003CEC, 0x00434B, 0x0043A7, 0x0043EA, 0x004503, 0x004537, 0x004542, 0x00454C, 0x004672, 0x0046DC, 0x0046F7, 0x0048AE, 0x005010, 0x005068, 0x005095, 0x0050A6, 0x009C10 |
| 490 | 0x00840000 | 124160 | True | 3.7980 | 4322 | 105698 | 0.1487 | 0x000016 | 0x000016, 0x00003B, 0x000098, 0x0000C8, 0x000120, 0x000136, 0x000152, 0x00015F, 0x000F7B, 0x000FB6, 0x001030, 0x00103D, 0x00105A, 0x00342D, 0x00345B, 0x0034CF, 0x0034FC, 0x0035B7, 0x003AE0, 0x003B3F, 0x003B7F, 0x003C98, 0x003CCC, 0x003CD7, 0x003CE1, 0x003E07, 0x003E71, 0x003E8C, 0x0045B7, 0x00475B, 0x0047B3, 0x0047E0, 0x0047F1 |
| 493 | 0x0085E500 | 62720 | True | 2.4236 | 1673 | 54979 | 0.1234 | 0x000016 | 0x000016, 0x00003B, 0x000098, 0x0000C8, 0x0000EC, 0x000120, 0x000136, 0x000152, 0x00015F, 0x000F16, 0x000F47, 0x000FBB, 0x000FCB, 0x000FE8, 0x0016D0, 0x0016EF, 0x001826, 0x001890, 0x0018AB, 0x002AE0, 0x002B11, 0x003DDD |

## Region statistics (valid-instruction islands vs invalid-decode gaps)
* slot 20: 4518 regions (19824 valid bytes, 16.1% of span), 92750 gaps (103056 gap bytes, 83.9%), largest gap 4 bytes; region sizes min=2 max=75 median=3, regions<8B=4088, regions<16B=4441
* slot 150: 33232 regions (159508 valid bytes, 27.9% of span), 363152 gaps (411628 gap bytes, 72.1%), largest gap 4 bytes; region sizes min=2 max=95 median=3, regions<8B=28819, regions<16B=32445
* slot 156: 30799 regions (149585 valid bytes, 27.7% of span), 346802 gaps (389551 gap bytes, 72.3%), largest gap 4 bytes; region sizes min=2 max=154 median=3, regions<8B=26586, regions<16B=30020
* slot 481: 5494 regions (23557 valid bytes, 16.4% of span), 105079 gaps (119803 gap bytes, 83.6%), largest gap 4 bytes; region sizes min=2 max=51 median=3, regions<8B=5036, regions<16B=5432
* slot 484: 6625 regions (28248 valid bytes, 17.9% of span), 111258 gaps (129192 gap bytes, 82.1%), largest gap 4 bytes; region sizes min=2 max=47 median=3, regions<8B=6083, regions<16B=6555
* slot 487: 3835 regions (16864 valid bytes, 11.4% of span), 122683 gaps (130848 gap bytes, 88.6%), largest gap 4 bytes; region sizes min=2 max=47 median=3, regions<8B=3478, regions<16B=3771
* slot 490: 4322 regions (18462 valid bytes, 14.9% of span), 94636 gaps (105698 gap bytes, 85.1%), largest gap 4 bytes; region sizes min=2 max=47 median=3, regions<8B=3963, regions<16B=4268
* slot 493: 1673 regions (7741 valid bytes, 12.3% of span), 52561 gaps (54979 gap bytes, 87.7%), largest gap 4 bytes; region sizes min=2 max=34 median=3, regions<8B=1475, regions<16B=1631

## Header fields (raw u32 LE, no semantics asserted)
* slot 20: d0c0ff00 00fe0400 bda47e10 fe00f802
* slot 150: d0005e00 00fe0400 bda47e10 5e00f802
* slot 156: d0005e00 00fe0400 bda47e10 5e00f802
* slot 481: d000f000 00fe0400 bda47e10 fb00f802
* slot 484: d000f000 00fe0400 bda47e10 fb00f802
* slot 487: d000f000 00fe0400 bda47e10 fb00f802
* slot 490: d000f000 00fe0400 bda47e10 fd00f802
* slot 493: d0007900 00fe0400 bda47e10 fd00f802

## Header equality groups (identical 16-byte container headers)
* slot 20
* slot 150, slot 156
* slot 481, slot 484, slot 487
* slot 490
* slot 493

## Bootstrap / bring-up code (Falcon-specific, decoded from bytes)
Every payload contains the same bring-up template near offset 0x10-0x180: loads from
a structure indexed by a live-in register, builds 64-bit base values, writes Falcon
special registers $xcbase / $xtargets / $xdbase, performs XRAM operations (xcld / xdld /
xdst), xcwait / xdwait, then indirect call $r1. This is Falcon microcode bring-up, not
generic RISC-V.
* slot 20 primary entry 0x00002A (21 insns, markers ['mov_sp', 'write_$xcbase', 'write_$xtargets']): ld b32 $r2 D[$r0+0x34] ; ld b32 $r1 D[$r0+0x18] ; ld b32 $r12 D[$r0+0x14] ; shl b32 $r9 $r14 0xc ; shl b32 $r15 $r14 0x8 ; ld b32 $r13 D[$r0+0x1c] ; or $r15 $r9 ; ld b32 $r11 D[$r0+0x24]
* slot 150 primary entry 0x000016 (10 insns, markers ['write_$xcbase']): C  ld b32 $r14 D[$r9+0x24] ; ld b32 $r15 D[$r9+0x28] ; ld b32 $r3 D[$r9+0x48] ; ld b32 $r1 D[$r9+0x3c] ; shr b32 $r14 0x8 ; shl b32 $r15 0x18 ; ld b32 $r0 D[$r9+0x4c] ; or $r15 $r14
* slot 156 primary entry 0x000016 (10 insns, markers ['write_$xcbase']): C  ld b32 $r14 D[$r9+0x24] ; ld b32 $r15 D[$r9+0x28] ; ld b32 $r3 D[$r9+0x48] ; ld b32 $r1 D[$r9+0x3c] ; shr b32 $r14 0x8 ; shl b32 $r15 0x18 ; ld b32 $r0 D[$r9+0x4c] ; or $r15 $r14
* slot 481 primary entry 0x000016 (11 insns, markers ['write_$xcbase']): ld b32 $r15 D[$r9+0x24] ; ld b32 $r14 D[$r9+0x28] ; ld b32 $r3 D[$r9+0x48] ; ld b32 $r1 D[$r9+0x3c] ; shr b32 $r15 0x8 ; shl b32 $r14 0x18 ; ld b32 $r10 D[$r9+0x4c] ; or $r14 $r15
* slot 484 primary entry 0x000016 (11 insns, markers ['write_$xcbase']): ld b32 $r15 D[$r9+0x24] ; ld b32 $r14 D[$r9+0x28] ; ld b32 $r3 D[$r9+0x48] ; ld b32 $r1 D[$r9+0x3c] ; shr b32 $r15 0x8 ; shl b32 $r14 0x18 ; ld b32 $r10 D[$r9+0x4c] ; or $r14 $r15
* slot 487 primary entry 0x000016 (11 insns, markers ['write_$xcbase']): ld b32 $r15 D[$r9+0x24] ; ld b32 $r14 D[$r9+0x28] ; ld b32 $r3 D[$r9+0x48] ; ld b32 $r1 D[$r9+0x3c] ; shr b32 $r15 0x8 ; shl b32 $r14 0x18 ; ld b32 $r10 D[$r9+0x4c] ; or $r14 $r15
* slot 490 primary entry 0x000016 (11 insns, markers ['write_$xcbase']): ld b32 $r15 D[$r9+0x24] ; ld b32 $r14 D[$r9+0x28] ; ld b32 $r3 D[$r9+0x48] ; ld b32 $r1 D[$r9+0x3c] ; shr b32 $r15 0x8 ; shl b32 $r14 0x18 ; ld b32 $r10 D[$r9+0x4c] ; or $r14 $r15
* slot 493 primary entry 0x000016 (11 insns, markers ['write_$xcbase']): ld b32 $r15 D[$r9+0x24] ; ld b32 $r14 D[$r9+0x28] ; ld b32 $r3 D[$r9+0x48] ; ld b32 $r1 D[$r9+0x3c] ; shr b32 $r15 0x8 ; shl b32 $r14 0x18 ; ld b32 $r10 D[$r9+0x4c] ; or $r14 $r15

## Candidate entry points (regions writing Falcon special registers)
* slot 20:
  - 0x00002A size=62 insns=21 markers=['mov_sp', 'write_$xcbase', 'write_$xtargets']
  - 0x00006C size=3 insns=1 markers=['xcld']
  - 0x00007C size=16 insns=6 markers=['write_$xdbase', 'xcwait']
  - 0x000094 size=6 insns=2 markers=['xdld']
  - 0x0000A1 size=5 insns=2 markers=['xdwait']
  - 0x00844D size=8 insns=3 markers=['mov_sp', 'xdwait']
  - 0x008895 size=46 insns=15 markers=['mov_sp', 'write_$xdbase', 'write_$xtargets']
  - 0x00BE29 size=44 insns=14 markers=['write_$xdbase', 'write_$xtargets']
  - 0x00BEAF size=11 insns=4 markers=['xdst', 'xdwait']
* slot 150:
  - 0x000016 size=30 insns=10 markers=['write_$xcbase']
  - 0x000038 size=18 insns=6 markers=['write_$xtargets']
  - 0x000094 size=2 insns=1 markers=['xcwait']
  - 0x0000B3 size=8 insns=3 markers=['write_$xtargets', 'xcwait']
  - 0x0000BF size=20 insns=7 markers=['write_$xdbase']
  - 0x0000DB size=6 insns=2 markers=['xdld']
  - 0x0000E8 size=5 insns=2 markers=['xdwait']
  - 0x001009 size=28 insns=9 markers=['write_$xdbase', 'write_$xtargets']
  - 0x001031 size=16 insns=5 markers=['write_$xtargets']
  - 0x0010B0 size=9 insns=3 markers=['xdld']
  - 0x0010BD size=21 insns=7 markers=['xdst']
  - 0x0010DA size=6 insns=2 markers=['write_$xdbase', 'write_$xtargets']
  - 0x0010E4 size=2 insns=1 markers=['xdwait']
  - 0x001805 size=22 insns=7 markers=['xcld']
  - 0x00181D size=6 insns=2 markers=['xcwait']
  - 0x00193D size=8 insns=3 markers=['xdst', 'xdwait']
  - 0x0019B5 size=12 insns=4 markers=['xdld', 'xdwait']
  - 0x0019D0 size=2 insns=1 markers=['xdwait']
  - 0x005BAD size=6 insns=2 markers=['xdld', 'xdst']
  - 0x005BD6 size=6 insns=2 markers=['xdwait']
  - 0x007FFC size=7 insns=3 markers=['xdwait']
  - 0x028F7D size=7 insns=3 markers=['xdwait']
  - 0x03F8D2 size=2 insns=1 markers=['xdwait']
  - 0x03F928 size=4 insns=2 markers=['xdwait']
  - 0x03F930 size=2 insns=1 markers=['xdwait']
  - 0x03F977 size=7 insns=3 markers=['exit', 'xdwait']
  - 0x03F982 size=2 insns=1 markers=['xdwait']
  - 0x03FA53 size=2 insns=1 markers=['xdwait']
  - 0x04841A size=3 insns=1 markers=['write_$xcbase']
  - 0x04A8D8 size=8 insns=3 markers=['xdst', 'xdwait']
  - 0x04A90D size=8 insns=3 markers=['xdst', 'xdwait']
  - 0x04AA6B size=3 insns=1 markers=['xdst']
  - 0x04AA75 size=6 insns=2 markers=['xdld', 'xdst']
  - 0x04AA82 size=5 insns=2 markers=['xdld', 'xdwait']
  - 0x0516EB size=3 insns=1 markers=['xdld']
  - 0x062E04 size=3 insns=1 markers=['write_$xdbase']
  - 0x077EC0 size=3 insns=1 markers=['xcld']
* slot 156:
  - 0x000016 size=30 insns=10 markers=['write_$xcbase']
  - 0x000038 size=18 insns=6 markers=['write_$xtargets']
  - 0x000094 size=2 insns=1 markers=['xcwait']
  - 0x0000B3 size=8 insns=3 markers=['write_$xtargets', 'xcwait']
  - 0x0000BF size=20 insns=7 markers=['write_$xdbase']
  - 0x0000DB size=6 insns=2 markers=['xdld']
  - 0x0000E8 size=5 insns=2 markers=['xdwait']
  - 0x000FC5 size=37 insns=12 markers=['write_$xdbase', 'write_$xtargets']
  - 0x000FF9 size=13 insns=4 markers=['write_$xtargets']
  - 0x001075 size=9 insns=3 markers=['xdld']
  - 0x001082 size=21 insns=7 markers=['xdst']
  - 0x00109F size=6 insns=2 markers=['write_$xdbase', 'write_$xtargets']
  - 0x0010A9 size=2 insns=1 markers=['xdwait']
  - 0x00179D size=22 insns=7 markers=['xcld']
  - 0x0017B5 size=6 insns=2 markers=['xcwait']
  - 0x0018D5 size=8 insns=3 markers=['xdst', 'xdwait']
  - 0x00194D size=12 insns=4 markers=['xdld', 'xdwait']
  - 0x001968 size=2 insns=1 markers=['xdwait']
  - 0x00399B size=8 insns=3 markers=['xdld', 'xdwait']
  - 0x00570F size=2 insns=1 markers=['xdwait']
  - 0x006E8D size=7 insns=3 markers=['xdwait']
  - 0x01759A size=3 insns=1 markers=['write_$xdbase']
  - 0x01B8FE size=2 insns=1 markers=['xdwait']
  - 0x022C9E size=7 insns=3 markers=['xdwait']
  - 0x04305F size=8 insns=3 markers=['xdst', 'xdwait']
  - 0x043094 size=8 insns=3 markers=['xdst', 'xdwait']
  - 0x0431F2 size=3 insns=1 markers=['xdst']
  - 0x0431FC size=6 insns=2 markers=['xdld', 'xdst']
  - 0x043209 size=5 insns=2 markers=['xdld', 'xdwait']
  - 0x045F2B size=2 insns=1 markers=['xdwait']
  - 0x045FAE size=2 insns=1 markers=['xdwait']
  - 0x046272 size=2 insns=1 markers=['xdwait']
  - 0x0462C0 size=2 insns=1 markers=['xdwait']
  - 0x047235 size=3 insns=1 markers=['xcld']
  - 0x049A0D size=2 insns=1 markers=['xdwait']
  - 0x049F20 size=2 insns=1 markers=['xdwait']
* slot 481:
  - 0x000016 size=33 insns=11 markers=['write_$xcbase']
  - 0x00003B size=18 insns=6 markers=['write_$xtargets']
  - 0x000092 size=8 insns=3 markers=['xcld', 'xcwait']
  - 0x0000A8 size=3 insns=1 markers=['xcld']
  - 0x0000C8 size=13 insns=5 markers=['xdst', 'xdwait']
  - 0x000120 size=18 insns=6 markers=['write_$xtargets']
  - 0x000136 size=20 insns=7 markers=['write_$xdbase']
  - 0x000152 size=6 insns=2 markers=['xdld']
  - 0x00015F size=5 insns=2 markers=['xdwait']
  - 0x00167B size=47 insns=15 markers=['write_$xdbase', 'write_$xtargets']
  - 0x0016B6 size=16 insns=5 markers=['write_$xtargets']
  - 0x001730 size=9 insns=3 markers=['xdld']
  - 0x00175A size=10 insns=4 markers=['write_$xdbase', 'write_$xtargets', 'xdwait']
  - 0x003C96 size=13 insns=4 markers=['write_$xdbase']
  - 0x003CAF size=16 insns=5 markers=['write_$xtargets']
  - 0x003D2D size=12 insns=4 markers=['xdld']
  - 0x003D5A size=8 insns=3 markers=['write_$xdbase', 'write_$xtargets', 'xdwait']
  - 0x0043B9 size=6 insns=2 markers=['xcld']
  - 0x004418 size=20 insns=7 markers=['write_$xcbase']
  - 0x004458 size=6 insns=2 markers=['write_$xcbase']
  - 0x004571 size=19 insns=6 markers=['xcld']
  - 0x0045A5 size=9 insns=3 markers=['xcld']
  - 0x0045B0 size=6 insns=2 markers=['xcwait']
  - 0x0045BA size=11 insns=4 markers=['write_$xcbase']
  - 0x0046E0 size=8 insns=3 markers=['xdst', 'xdwait']
  - 0x00474A size=12 insns=4 markers=['xdld', 'xdwait']
  - 0x004765 size=2 insns=1 markers=['xdwait']
  - 0x00491C size=3 insns=1 markers=['write_$xtargets']
  - 0x00542A size=6 insns=2 markers=['write_$xcbase']
  - 0x005482 size=23 insns=7 markers=['xcld']
  - 0x0054AF size=5 insns=2 markers=['xcwait']
  - 0x0054C0 size=13 insns=5 markers=['exit', 'write_$xcbase']
  - 0x00B996 size=6 insns=2 markers=['xdld']
  - 0x00F1F3 size=6 insns=2 markers=['write_$xdbase']
* slot 484:
  - 0x000016 size=33 insns=11 markers=['write_$xcbase']
  - 0x00003B size=18 insns=6 markers=['write_$xtargets']
  - 0x000092 size=8 insns=3 markers=['xcld', 'xcwait']
  - 0x0000A8 size=3 insns=1 markers=['xcld']
  - 0x0000C8 size=13 insns=5 markers=['xdst', 'xdwait']
  - 0x000120 size=18 insns=6 markers=['write_$xtargets']
  - 0x000136 size=20 insns=7 markers=['write_$xdbase']
  - 0x000152 size=6 insns=2 markers=['xdld']
  - 0x00015F size=5 insns=2 markers=['xdwait']
  - 0x001C7B size=47 insns=15 markers=['write_$xdbase', 'write_$xtargets']
  - 0x001CB6 size=16 insns=5 markers=['write_$xtargets']
  - 0x001D30 size=9 insns=3 markers=['xdld']
  - 0x001D5A size=10 insns=4 markers=['write_$xdbase', 'write_$xtargets', 'xdwait']
  - 0x004E81 size=34 insns=11 markers=['write_$xdbase', 'write_$xtargets']
  - 0x004EAF size=16 insns=5 markers=['write_$xtargets']
  - 0x004F2D size=12 insns=4 markers=['xdld']
  - 0x004F3D size=21 insns=7 markers=['xdst']
  - 0x004F5A size=8 insns=3 markers=['write_$xdbase', 'write_$xtargets', 'xdwait']
  - 0x0055B9 size=6 insns=2 markers=['xcld']
  - 0x005618 size=20 insns=7 markers=['write_$xcbase']
  - 0x005771 size=19 insns=6 markers=['xcld']
  - 0x0057A5 size=9 insns=3 markers=['xcld']
  - 0x0057B0 size=6 insns=2 markers=['xcwait']
  - 0x0057BA size=11 insns=4 markers=['write_$xcbase']
  - 0x0058E0 size=8 insns=3 markers=['xdst', 'xdwait']
  - 0x00594A size=12 insns=4 markers=['xdld', 'xdwait']
  - 0x005965 size=2 insns=1 markers=['xdwait']
  - 0x005B1C size=3 insns=1 markers=['write_$xtargets']
  - 0x00662A size=6 insns=2 markers=['write_$xcbase']
  - 0x006682 size=23 insns=7 markers=['xcld']
  - 0x0066AF size=5 insns=2 markers=['xcwait']
  - 0x0066C0 size=13 insns=5 markers=['exit', 'write_$xcbase']
  - 0x00C0A7 size=6 insns=2 markers=['xdst']
  - 0x00FD2B size=3 insns=1 markers=['xdld']
  - 0x01038F size=3 insns=1 markers=['xdld']
  - 0x011A63 size=3 insns=1 markers=['xdst']
* slot 487:
  - 0x000016 size=33 insns=11 markers=['write_$xcbase']
  - 0x00003B size=18 insns=6 markers=['write_$xtargets']
  - 0x000092 size=8 insns=3 markers=['xcld', 'xcwait']
  - 0x0000A8 size=3 insns=1 markers=['xcld']
  - 0x0000C8 size=13 insns=5 markers=['xdst', 'xdwait']
  - 0x000120 size=18 insns=6 markers=['write_$xtargets']
  - 0x000136 size=20 insns=7 markers=['write_$xdbase']
  - 0x000152 size=6 insns=2 markers=['xdld']
  - 0x00015F size=5 insns=2 markers=['xdwait']
  - 0x00137B size=47 insns=15 markers=['write_$xdbase', 'write_$xtargets']
  - 0x0013B6 size=16 insns=5 markers=['write_$xtargets']
  - 0x001430 size=9 insns=3 markers=['xdld']
  - 0x00145A size=10 insns=4 markers=['write_$xdbase', 'write_$xtargets', 'xdwait']
  - 0x001C1A size=2 insns=1 markers=['xcwait']
  - 0x003C10 size=37 insns=12 markers=['write_$xdbase', 'write_$xtargets']
  - 0x003C48 size=9 insns=3 markers=['write_$xtargets']
  - 0x003CBF size=12 insns=4 markers=['xdld']
  - 0x003CEC size=8 insns=3 markers=['write_$xdbase', 'write_$xtargets', 'xdwait']
  - 0x00434B size=6 insns=2 markers=['xcld']
  - 0x0043A7 size=23 insns=8 markers=['write_$xcbase']
  - 0x0043EA size=6 insns=2 markers=['write_$xcbase']
  - 0x004503 size=19 insns=6 markers=['xcld']
  - 0x004537 size=9 insns=3 markers=['xcld']
  - 0x004542 size=6 insns=2 markers=['xcwait']
  - 0x00454C size=11 insns=4 markers=['write_$xcbase']
  - 0x004672 size=8 insns=3 markers=['xdst', 'xdwait']
  - 0x0046DC size=12 insns=4 markers=['xdld', 'xdwait']
  - 0x0046F7 size=2 insns=1 markers=['xdwait']
  - 0x0048AE size=3 insns=1 markers=['write_$xtargets']
  - 0x005010 size=6 insns=2 markers=['write_$xcbase']
  - 0x005068 size=23 insns=7 markers=['xcld']
  - 0x005095 size=5 insns=2 markers=['xcwait']
  - 0x0050A6 size=13 insns=5 markers=['exit', 'write_$xcbase']
  - 0x009C10 size=3 insns=1 markers=['xdld']
* slot 490:
  - 0x000016 size=33 insns=11 markers=['write_$xcbase']
  - 0x00003B size=18 insns=6 markers=['write_$xtargets']
  - 0x000098 size=2 insns=1 markers=['xcwait']
  - 0x0000C8 size=13 insns=5 markers=['xdst', 'xdwait']
  - 0x000120 size=18 insns=6 markers=['write_$xtargets']
  - 0x000136 size=20 insns=7 markers=['write_$xdbase']
  - 0x000152 size=6 insns=2 markers=['xdld']
  - 0x00015F size=5 insns=2 markers=['xdwait']
  - 0x000F7B size=47 insns=15 markers=['write_$xdbase', 'write_$xtargets']
  - 0x000FB6 size=16 insns=5 markers=['write_$xtargets']
  - 0x001030 size=9 insns=3 markers=['xdld']
  - 0x00103D size=21 insns=7 markers=['xdst']
  - 0x00105A size=10 insns=4 markers=['write_$xdbase', 'write_$xtargets', 'xdwait']
  - 0x00342D size=31 insns=10 markers=['write_$xdbase', 'write_$xtargets']
  - 0x00345B size=13 insns=4 markers=['write_$xtargets']
  - 0x0034CF size=12 insns=4 markers=['xdld']
  - 0x0034FC size=8 insns=3 markers=['write_$xdbase', 'write_$xtargets', 'xdwait']
  - 0x0035B7 size=6 insns=2 markers=['write_$xdbase']
  - 0x003AE0 size=6 insns=2 markers=['xcld']
  - 0x003B3F size=20 insns=7 markers=['write_$xcbase']
  - 0x003B7F size=6 insns=2 markers=['write_$xcbase']
  - 0x003C98 size=19 insns=6 markers=['xcld']
  - 0x003CCC size=9 insns=3 markers=['xcld']
  - 0x003CD7 size=6 insns=2 markers=['xcwait']
  - 0x003CE1 size=11 insns=4 markers=['write_$xcbase']
  - 0x003E07 size=8 insns=3 markers=['xdst', 'xdwait']
  - 0x003E71 size=12 insns=4 markers=['xdld', 'xdwait']
  - 0x003E8C size=2 insns=1 markers=['xdwait']
  - 0x0045B7 size=3 insns=1 markers=['write_$xdbase']
  - 0x00475B size=6 insns=2 markers=['write_$xcbase']
  - 0x0047B3 size=23 insns=7 markers=['xcld']
  - 0x0047E0 size=5 insns=2 markers=['xcwait']
  - 0x0047F1 size=13 insns=5 markers=['exit', 'write_$xcbase']
* slot 493:
  - 0x000016 size=33 insns=11 markers=['write_$xcbase']
  - 0x00003B size=18 insns=6 markers=['write_$xtargets']
  - 0x000098 size=2 insns=1 markers=['xcwait']
  - 0x0000C8 size=13 insns=5 markers=['xdst', 'xdwait']
  - 0x0000EC size=3 insns=1 markers=['xcld']
  - 0x000120 size=18 insns=6 markers=['write_$xtargets']
  - 0x000136 size=20 insns=7 markers=['write_$xdbase']
  - 0x000152 size=6 insns=2 markers=['xdld']
  - 0x00015F size=5 insns=2 markers=['xdwait']
  - 0x000F16 size=34 insns=11 markers=['write_$xdbase', 'write_$xtargets']
  - 0x000F47 size=13 insns=4 markers=['write_$xtargets']
  - 0x000FBB size=12 insns=4 markers=['xdld']
  - 0x000FCB size=21 insns=7 markers=['xdst']
  - 0x000FE8 size=8 insns=3 markers=['write_$xdbase', 'write_$xtargets', 'xdwait']
  - 0x0016D0 size=19 insns=6 markers=['xcld']
  - 0x0016EF size=12 insns=4 markers=['xcld']
  - 0x001826 size=8 insns=3 markers=['xdst', 'xdwait']
  - 0x001890 size=12 insns=4 markers=['xdld', 'xdwait']
  - 0x0018AB size=2 insns=1 markers=['xdwait']
  - 0x002AE0 size=26 insns=8 markers=['xcld']
  - 0x002B11 size=2 insns=1 markers=['xcwait']
  - 0x003DDD size=9 insns=3 markers=['write_$xtargets']

## Control flow
* slot 20: 463 CT insns (8 calls all indirect -> target UNKNOWN, 385 branches); 0 escapes below;
  - in-bounds branches: 348
    @0x0000A1 -> 0x131 (abs=0x90 rel_eff=0x131)
    @0x0010B5 -> 0x10BC (abs=0x10BC rel_eff=0x2171)
    @0x0010EA -> 0x10F1 (abs=0x10F1 rel_eff=0x21DB)
    @0x00111A -> 0x1121 (abs=0x1121 rel_eff=0x223B)
    @0x001137 -> 0x2277 (abs=0x1140 rel_eff=0x2277)
    @0x001164 -> 0x116B (abs=0x116B rel_eff=0x22CF)
    @0x00118D -> 0x1195 (abs=0x1195 rel_eff=0x2322)
    @0x0011BA -> 0x11C1 (abs=0x11C1 rel_eff=0x237B)
    @0x001238 -> 0x2477 (abs=0x123F rel_eff=0x2477)
    @0x001279 -> 0x2507 (abs=0x128E rel_eff=0x2507)
  - reachable region starts from primary: 0x00002A
  - orphan region starts (not reachable via direct edges, count 4517): 0x000001, 0x000005, 0x00000B, 0x000016, 0x00001B, 0x00006C, 0x000074, 0x000078, 0x00007C, 0x000094, 0x00009B, 0x0000A1
* slot 150: 7262 CT insns (181 calls all indirect -> target UNKNOWN, 3818 branches); 1 escapes below;
  - escape @0x0018E6: bra b 0xffffffffffffb862 raw=f5087c9f detail=abs=0xFFFFFFFFFFFFB862 rel_eff=0x-2EB8
  - in-bounds branches: 3155
    @0x0000B3 -> 0x157 (abs=0xA4 rel_eff=0x157)
    @0x0000E8 -> 0x1BF (abs=0xD7 rel_eff=0x1BF)
    @0x0003BB -> 0x88E (abs=0x4D3 rel_eff=0x88E)
    @0x0003F0 -> 0x7E6 (abs=0x3F6 rel_eff=0x7E6)
    @0x000557 -> 0xACD (abs=0x576 rel_eff=0xACD)
    @0x0005DB -> 0xCB2 (abs=0x6D7 rel_eff=0xCB2)
    @0x0005E6 -> 0xBCA (abs=0x5E4 rel_eff=0xBCA)
    @0x000611 -> 0xC2A (abs=0x619 rel_eff=0xC2A)
    @0x000620 -> 0xC48 (abs=0x628 rel_eff=0xC48)
    @0x0006B5 -> 0xD8F (abs=0x6DA rel_eff=0xD8F)
  - reachable region starts from primary: 0x000016
  - orphan region starts (not reachable via direct edges, count 33231): 0x000005, 0x00000B, 0x000038, 0x000050, 0x00005E, 0x000068, 0x00006F, 0x000073, 0x00007B, 0x000082, 0x000094, 0x000098
* slot 156: 6793 CT insns (184 calls all indirect -> target UNKNOWN, 3260 branches); 1 escapes below;
  - escape @0x00187E: bra b 0xffffffffffffb7fa raw=f5087c9f detail=abs=0xFFFFFFFFFFFFB7FA rel_eff=0x-2F88
  - in-bounds branches: 2676
    @0x0000B3 -> 0x157 (abs=0xA4 rel_eff=0x157)
    @0x0000E8 -> 0x1BF (abs=0xD7 rel_eff=0x1BF)
    @0x000380 -> 0x818 (abs=0x498 rel_eff=0x818)
    @0x0003B5 -> 0x770 (abs=0x3BB rel_eff=0x770)
    @0x00051C -> 0x53B (abs=0x53B rel_eff=0xA57)
    @0x0005A0 -> 0xC3C (abs=0x69C rel_eff=0xC3C)
    @0x0005AB -> 0xB54 (abs=0x5A9 rel_eff=0xB54)
    @0x0005D6 -> 0xBB4 (abs=0x5DE rel_eff=0xBB4)
    @0x0005E5 -> 0xBD2 (abs=0x5ED rel_eff=0xBD2)
    @0x00067A -> 0xD19 (abs=0x69F rel_eff=0xD19)
  - reachable region starts from primary: 0x000016
  - orphan region starts (not reachable via direct edges, count 30798): 0x000005, 0x00000B, 0x000038, 0x000050, 0x00005E, 0x000068, 0x00006F, 0x000073, 0x00007B, 0x000082, 0x000094, 0x000098
* slot 481: 672 CT insns (18 calls all indirect -> target UNKNOWN, 335 branches); 0 escapes below;
  - in-bounds branches: 291
    @0x00015F -> 0x2AD (abs=0x14E rel_eff=0x2AD)
    @0x000224 -> 0x456 (abs=0x232 rel_eff=0x456)
    @0x000490 -> 0x925 (abs=0x495 rel_eff=0x925)
    @0x0004F0 -> 0x9E5 (abs=0x4F5 rel_eff=0x9E5)
    @0x00051F -> 0xA4C (abs=0x52D rel_eff=0xA4C)
    @0x000722 -> 0xE49 (abs=0x727 rel_eff=0xE49)
    @0x00085D -> 0x10BF (abs=0x862 rel_eff=0x10BF)
    @0x0008B0 -> 0x1165 (abs=0x8B5 rel_eff=0x1165)
    @0x000926 -> 0x1251 (abs=0x92B rel_eff=0x1251)
    @0x0009EA -> 0xBD4 (abs=0xBD4 rel_eff=0x15BE)
  - reachable region starts from primary: 0x000016
  - orphan region starts (not reachable via direct edges, count 5493): 0x000002, 0x00000B, 0x00003B, 0x000054, 0x000062, 0x00006C, 0x000073, 0x000077, 0x00007F, 0x000086, 0x000092, 0x00009C
* slot 484: 750 CT insns (20 calls all indirect -> target UNKNOWN, 384 branches); 0 escapes below;
  - in-bounds branches: 327
    @0x00015F -> 0x2AD (abs=0x14E rel_eff=0x2AD)
    @0x000224 -> 0x456 (abs=0x232 rel_eff=0x456)
    @0x000490 -> 0x925 (abs=0x495 rel_eff=0x925)
    @0x0004F0 -> 0x9E5 (abs=0x4F5 rel_eff=0x9E5)
    @0x00051F -> 0xA4C (abs=0x52D rel_eff=0xA4C)
    @0x000722 -> 0xE49 (abs=0x727 rel_eff=0xE49)
    @0x00085D -> 0x10BF (abs=0x862 rel_eff=0x10BF)
    @0x00089D -> 0x113F (abs=0x8A2 rel_eff=0x113F)
    @0x0009B2 -> 0x1369 (abs=0x9B7 rel_eff=0x1369)
    @0x000A28 -> 0x1455 (abs=0xA2D rel_eff=0x1455)
  - reachable region starts from primary: 0x000016
  - orphan region starts (not reachable via direct edges, count 6624): 0x000002, 0x00000B, 0x00003B, 0x000054, 0x000062, 0x00006C, 0x000073, 0x000077, 0x00007F, 0x000086, 0x000092, 0x00009C
* slot 487: 448 CT insns (19 calls all indirect -> target UNKNOWN, 216 branches); 0 escapes below;
  - in-bounds branches: 192
    @0x00015F -> 0x2AD (abs=0x14E rel_eff=0x2AD)
    @0x000315 -> 0x638 (abs=0x323 rel_eff=0x638)
    @0x000391 -> 0x73D (abs=0x3AC rel_eff=0x73D)
    @0x000610 -> 0xC2E (abs=0x61E rel_eff=0xC2E)
    @0x00068C -> 0xD33 (abs=0x6A7 rel_eff=0xD33)
    @0x00096F -> 0x14C8 (abs=0xB59 rel_eff=0x14C8)
    @0x0009A8 -> 0x14F3 (abs=0xB4B rel_eff=0x14F3)
    @0x0009B3 -> 0x14FE (abs=0xB4B rel_eff=0x14FE)
    @0x0009BA -> 0x1505 (abs=0xB4B rel_eff=0x1505)
    @0x0009C5 -> 0x1510 (abs=0xB4B rel_eff=0x1510)
  - reachable region starts from primary: 0x000016
  - orphan region starts (not reachable via direct edges, count 3834): 0x000002, 0x00000B, 0x00003B, 0x000054, 0x000062, 0x00006C, 0x000073, 0x000077, 0x00007F, 0x000086, 0x000092, 0x00009C
* slot 490: 410 CT insns (18 calls all indirect -> target UNKNOWN, 204 branches); 0 escapes below;
  - in-bounds branches: 185
    @0x00015F -> 0x2AD (abs=0x14E rel_eff=0x2AD)
    @0x000215 -> 0x438 (abs=0x223 rel_eff=0x438)
    @0x000410 -> 0x82E (abs=0x41E rel_eff=0x82E)
    @0x000585 -> 0xB14 (abs=0x58F rel_eff=0xB14)
    @0x000620 -> 0xDE3 (abs=0x7C3 rel_eff=0xDE3)
    @0x00062B -> 0xDEE (abs=0x7C3 rel_eff=0xDEE)
    @0x000632 -> 0xDF5 (abs=0x7C3 rel_eff=0xDF5)
    @0x00063D -> 0xE00 (abs=0x7C3 rel_eff=0xE00)
    @0x000644 -> 0xE07 (abs=0x7C3 rel_eff=0xE07)
    @0x0006B2 -> 0xE83 (abs=0x7D1 rel_eff=0xE83)
  - reachable region starts from primary: 0x000016
  - orphan region starts (not reachable via direct edges, count 4321): 0x000002, 0x00000B, 0x00003B, 0x000055, 0x000062, 0x00006C, 0x000073, 0x000077, 0x00007F, 0x000086, 0x000098, 0x00009C
* slot 493: 303 CT insns (11 calls all indirect -> target UNKNOWN, 141 branches); 1 escapes below;
  - escape @0x0017CF: bra b 0xffffffffffffb74b raw=f5087c9f detail=abs=0xFFFFFFFFFFFFB74B rel_eff=0x-30E6
  - in-bounds branches: 116
    @0x00015F -> 0x2AD (abs=0x14E rel_eff=0x2AD)
    @0x0003C8 -> 0x8A8 (abs=0x4E0 rel_eff=0x8A8)
    @0x0005E8 -> 0xCCC (abs=0x6E4 rel_eff=0xCCC)
    @0x0005F3 -> 0xBE4 (abs=0x5F1 rel_eff=0xBE4)
    @0x00061E -> 0xC44 (abs=0x626 rel_eff=0xC44)
    @0x00062D -> 0xC62 (abs=0x635 rel_eff=0xC62)
    @0x0006C2 -> 0xDA9 (abs=0x6E7 rel_eff=0xDA9)
    @0x0007A1 -> 0xF49 (abs=0x7A8 rel_eff=0xF49)
    @0x0007C0 -> 0xF85 (abs=0x7C5 rel_eff=0xF85)
    @0x000857 -> 0x10B9 (abs=0x862 rel_eff=0x10B9)
  - reachable region starts from primary: 0x000016
  - orphan region starts (not reachable via direct edges, count 1672): 0x000002, 0x00000B, 0x00003B, 0x000055, 0x000062, 0x00006C, 0x000073, 0x000077, 0x00007F, 0x000086, 0x000098, 0x00009C

## Cross-references (immediate constants matched to evidence; class=unmatched means no known referent)
* none — no payload immediate matches a container offset, GSP/SEC2 register address,
  descriptor-table VA/file-offset, or GSP disassembly VA. No meaningful ASCII strings
  found (only 4-6 byte garbage).

## Pairwise comparison
* slots [20, 150]: sha_equal=False common_prefix=1 header_equal=False size_diff=448256 shared_ngram4=167
* slots [20, 156]: sha_equal=False common_prefix=1 header_equal=False size_diff=416256 shared_ngram4=167
* slots [20, 481]: sha_equal=False common_prefix=1 header_equal=False size_diff=20480 shared_ngram4=42
* slots [20, 484]: sha_equal=False common_prefix=1 header_equal=False size_diff=34560 shared_ngram4=44
* slots [20, 487]: sha_equal=False common_prefix=1 header_equal=False size_diff=24832 shared_ngram4=43
* slots [20, 490]: sha_equal=False common_prefix=1 header_equal=False size_diff=1280 shared_ngram4=39
* slots [20, 493]: sha_equal=False common_prefix=1 header_equal=False size_diff=60160 shared_ngram4=35
* slots [150, 156]: sha_equal=False common_prefix=268 header_equal=True size_diff=32000 shared_ngram4=1561
* slots [150, 481]: sha_equal=False common_prefix=2 header_equal=False size_diff=427776 shared_ngram4=138
* slots [150, 484]: sha_equal=False common_prefix=2 header_equal=False size_diff=413696 shared_ngram4=163
* slots [150, 487]: sha_equal=False common_prefix=2 header_equal=False size_diff=423424 shared_ngram4=148
* slots [150, 490]: sha_equal=False common_prefix=2 header_equal=False size_diff=446976 shared_ngram4=142
* slots [150, 493]: sha_equal=False common_prefix=2 header_equal=False size_diff=508416 shared_ngram4=125
* slots [156, 481]: sha_equal=False common_prefix=2 header_equal=False size_diff=395776 shared_ngram4=133
* slots [156, 484]: sha_equal=False common_prefix=2 header_equal=False size_diff=381696 shared_ngram4=163
* slots [156, 487]: sha_equal=False common_prefix=2 header_equal=False size_diff=391424 shared_ngram4=145
* slots [156, 490]: sha_equal=False common_prefix=2 header_equal=False size_diff=414976 shared_ngram4=138
* slots [156, 493]: sha_equal=False common_prefix=2 header_equal=False size_diff=476416 shared_ngram4=123
* slots [481, 484]: sha_equal=False common_prefix=919 header_equal=True size_diff=14080 shared_ngram4=233
* slots [481, 487]: sha_equal=False common_prefix=512 header_equal=True size_diff=4352 shared_ngram4=220
* slots [481, 490]: sha_equal=False common_prefix=12 header_equal=False size_diff=19200 shared_ngram4=173
* slots [481, 493]: sha_equal=False common_prefix=2 header_equal=False size_diff=80640 shared_ngram4=129
* slots [484, 487]: sha_equal=False common_prefix=512 header_equal=True size_diff=9728 shared_ngram4=209
* slots [484, 490]: sha_equal=False common_prefix=12 header_equal=False size_diff=33280 shared_ngram4=181
* slots [484, 493]: sha_equal=False common_prefix=2 header_equal=False size_diff=94720 shared_ngram4=130
* slots [487, 490]: sha_equal=False common_prefix=12 header_equal=False size_diff=23552 shared_ngram4=193
* slots [487, 493]: sha_equal=False common_prefix=2 header_equal=False size_diff=84992 shared_ngram4=133
* slots [490, 493]: sha_equal=False common_prefix=2 header_equal=False size_diff=61440 shared_ngram4=157

## Conclusion
* identity_basis: Falcon-specific special registers ($xcbase/$xtargets/$xdbase/$s10) and instructions (xcld/xdld/xdst/xcwait/xdwait) decoded from payload bytes; common bootstrap template across all 8 payloads. Not derived from size/entropy/header similarity.
* engine_role: UNKNOWN — no source-asserted engine<->Falcon-slot mapping exists (see PHASE16/ENGINE_INTERFACES findings.json); no exact cross-reference to GSP/SEC2 addresses found; role not inferred.
* prior_entry_correction: envydis -d parses numeric args as hex; the prior phase passed decimal start values. Slot 20 was labeled 0x24 (real bring-up start 0x2A; 0x36 was mid-stream); slots 150/156/481/484/487/490/493 were labeled 0x10 (real bootstrap start 0x16). Entries below are re-derived from the bytes.

## UNKNOWN preserved
* Engine/role identity (GSP vs SEC2 vs other Falcon unit): UNKNOWN — no source-asserted engine<->slot mapping; not inferred from code shape. No exact cross-reference to GSP/SEC2/MMIO addresses found in any payload immediate.
* Indirect call targets (call $r1): UNKNOWN (register-indirect, statically unresolvable).
* Branches with ambiguous absolute/relative targets: both interpretations recorded; role of target bytes unresolved where they land in gaps.
* The thousands of small decodable regions interleaved with gaps are consistent with embedded table(s)/codelet(s); individual entries are not classified as code — role UNKNOWN.

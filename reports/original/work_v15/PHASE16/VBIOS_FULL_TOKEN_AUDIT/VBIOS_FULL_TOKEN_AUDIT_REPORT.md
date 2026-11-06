# VBIOS_FULL_TOKEN_AUDIT — CMP 40HX (TU106) ROM/T4/shadow

Created: 2026-11-03T19:10:38.510139+00:00 UTC
Output dir: /home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_FULL_TOKEN_AUDIT

## Inputs (read-only, preserved)
- rom: /tmp/v11chk/outputs/CMP40HX_ORIGINAL_1MB.bin  size=1048576  sha256=dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec
- t4: /tmp/v11chk/outputs/cmp40hx_t4.bin  size=495616  sha256=aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb
- shadow: /tmp/v11chk/RAW_DATA/vbios_shadow.bin  size=1048576  sha256=2715c0b106931b540b5ef6660201919e9297f3f5cdc61432d9a16352c55b717a

## Provenance (envytools source, cited verbatim by file/line/hash)
- repo: /tmp/envytools  git HEAD: f102b82381f3f11cee113d16374c87091db039d9
- bit.c: /tmp/envytools/nvbios/bit.c  sha256=ad7475b67203275e1fe05ac8c910ce2ad431eacb930ca3a858e085dceb87f335
- power.c: /tmp/envytools/nvbios/power.c  sha256=6f4d9d065dd37d8ea49ec3f7a7aeedd2723b13a1c223bc90e90de5be1802c8a6
- nvbios.c: /tmp/envytools/nvbios/nvbios.c  sha256=7e9f739bf8e4b45f168e90b4d6b07c0c0d039a2bdb76f753b38069714f36907f
- bios.c: /tmp/envytools/nvbios/bios.c  sha256=1a87fa1eab4712e120771ef9af0d5df2c81ee7a69dbf43cd38415d6bcdf09ac8

## Conventions
- bit_signature: ff b8 42 49 54 00 00 (envytools bios.c:198)
- bit_header: version u16@+6 (expect 0x0100), hlen u8@+8, rlen u8@+9, entriesnum u8@+10; checksum over header must be 0 (bit.c:70-92); entry: type@0, version@1, t_len u16@2, t_offset u16@4 (bit.c:121-123)
- power_directory: BIT token 'P' (power v2) -> u32 slot array; slot i pointer at dir + i*4 (power.c:82-103 P2_tbls, power.c parse_at)
- mapping_rom_t4: BIT t_offset -> 0x28600 + t_offset ; power u32 -> 0x39600 + u32 (verified vs raw table headers)
- mapping_shadow: BIT t_offset -> direct shadow offset; power u32 -> u32 - 0x28600 (base 0x11000); shadow[i] == rom[i+0x28600] for the mapped region except 14 recorded bytes (see cross_image.shadow_vs_rom_shifted)
- traversal_vs_semantic: offsets/versions/hlen/rlen/counts and extent arithmetic are parser traversal facts; field meanings are source-backed semantic decodes only where cited

## Per-image BIT table
### rom (1048576 bytes)
- BIT signature at 0x287b0; version=0x100 (expect 0x0100); hlen=12 (want 12); rlen=6 (want 6); entriesnum=17
- header checksum mod 256 = 0x0 (envytools requires 0; bit.c:91-92 -> traversal would abort here)
- header raw: [255, 184, 66, 73, 84, 0, 0, 1, 12, 6, 17, 70]
- BIT span: [165808, 165922]
- entries:
   idx  0 type='2'(0x32) ver=1 t_len=4 t_offset=0x0232  -> mapped 0x28832 (0x028600 + t_offset)
   idx  1 type='B'(0x42) ver=2 t_len=37 t_offset=0x023e  -> mapped 0x2883e (0x028600 + t_offset)
   idx  2 type='C'(0x43) ver=2 t_len=44 t_offset=0x0263  -> mapped 0x28863 (0x028600 + t_offset)
   idx  3 type='D'(0x44) ver=1 t_len=4 t_offset=0x028f  -> mapped 0x2888f (0x028600 + t_offset)
   idx  4 type='I'(0x49) ver=1 t_len=36 t_offset=0x0293  -> mapped 0x28893 (0x028600 + t_offset)
   idx  5 type='M'(0x4d) ver=2 t_len=29 t_offset=0x02b7  -> mapped 0x288b7 (0x028600 + t_offset)
   idx  6 type='N'(0x4e) ver=0 t_len=0 t_offset=0x0000 NULL -> mapped None (null pointer (NOP))
   idx  7 type='P'(0x50) ver=2 t_len=224 t_offset=0x02d4  -> mapped 0x288d4 (0x028600 + t_offset)
   idx  8 type='S'(0x53) ver=2 t_len=24 t_offset=0x03b4  -> mapped 0x289b4 (0x028600 + t_offset)
   idx  9 type='T'(0x54) ver=1 t_len=2 t_offset=0x03cc  -> mapped 0x289cc (0x028600 + t_offset)
   idx 10 type='U'(0x55) ver=1 t_len=5 t_offset=0x03ce  -> mapped 0x289ce (0x028600 + t_offset)
   idx 11 type='V'(0x56) ver=1 t_len=6 t_offset=0x03d3  -> mapped 0x289d3 (0x028600 + t_offset)
   idx 12 type='x'(0x78) ver=1 t_len=8 t_offset=0x03d9  -> mapped 0x289d9 (0x028600 + t_offset)
   idx 13 type='d'(0x64) ver=1 t_len=2 t_offset=0x03e1  -> mapped 0x289e1 (0x028600 + t_offset)
   idx 14 type='p'(0x70) ver=2 t_len=4 t_offset=0x03e3  -> mapped 0x289e3 (0x028600 + t_offset)
   idx 15 type='u'(0x75) ver=1 t_len=13 t_offset=0x03e7  -> mapped 0x289e7 (0x028600 + t_offset)
   idx 16 type='i'(0x69) ver=2 t_len=104 t_offset=0x03f4  -> mapped 0x289f4 (0x028600 + t_offset)
- power directory (P): off 0x288d4, t_len 224 (= 56 x 4: True)
### t4 (495616 bytes)
- BIT signature at 0x287b0; version=0x100 (expect 0x0100); hlen=12 (want 12); rlen=6 (want 6); entriesnum=17
- header checksum mod 256 = 0x0 (envytools requires 0; bit.c:91-92 -> traversal would abort here)
- header raw: [255, 184, 66, 73, 84, 0, 0, 1, 12, 6, 17, 70]
- BIT span: [165808, 165922]
- entries:
   idx  0 type='2'(0x32) ver=1 t_len=4 t_offset=0x0232  -> mapped 0x28832 (0x028600 + t_offset)
   idx  1 type='B'(0x42) ver=2 t_len=37 t_offset=0x023e  -> mapped 0x2883e (0x028600 + t_offset)
   idx  2 type='C'(0x43) ver=2 t_len=44 t_offset=0x0263  -> mapped 0x28863 (0x028600 + t_offset)
   idx  3 type='D'(0x44) ver=1 t_len=4 t_offset=0x028f  -> mapped 0x2888f (0x028600 + t_offset)
   idx  4 type='I'(0x49) ver=1 t_len=36 t_offset=0x0293  -> mapped 0x28893 (0x028600 + t_offset)
   idx  5 type='M'(0x4d) ver=2 t_len=29 t_offset=0x02b7  -> mapped 0x288b7 (0x028600 + t_offset)
   idx  6 type='N'(0x4e) ver=0 t_len=0 t_offset=0x0000 NULL -> mapped None (null pointer (NOP))
   idx  7 type='P'(0x50) ver=2 t_len=224 t_offset=0x02d4  -> mapped 0x288d4 (0x028600 + t_offset)
   idx  8 type='S'(0x53) ver=2 t_len=24 t_offset=0x03b4  -> mapped 0x289b4 (0x028600 + t_offset)
   idx  9 type='T'(0x54) ver=1 t_len=2 t_offset=0x03cc  -> mapped 0x289cc (0x028600 + t_offset)
   idx 10 type='U'(0x55) ver=1 t_len=5 t_offset=0x03ce  -> mapped 0x289ce (0x028600 + t_offset)
   idx 11 type='V'(0x56) ver=1 t_len=6 t_offset=0x03d3  -> mapped 0x289d3 (0x028600 + t_offset)
   idx 12 type='x'(0x78) ver=1 t_len=8 t_offset=0x03d9  -> mapped 0x289d9 (0x028600 + t_offset)
   idx 13 type='d'(0x64) ver=1 t_len=2 t_offset=0x03e1  -> mapped 0x289e1 (0x028600 + t_offset)
   idx 14 type='p'(0x70) ver=2 t_len=4 t_offset=0x03e3  -> mapped 0x289e3 (0x028600 + t_offset)
   idx 15 type='u'(0x75) ver=1 t_len=13 t_offset=0x03e7  -> mapped 0x289e7 (0x028600 + t_offset)
   idx 16 type='i'(0x69) ver=2 t_len=104 t_offset=0x03f4  -> mapped 0x289f4 (0x028600 + t_offset)
- power directory (P): off 0x288d4, t_len 224 (= 56 x 4: True)
### shadow (1048576 bytes)
- BIT signature at 0x1b0; version=0x100 (expect 0x0100); hlen=12 (want 12); rlen=6 (want 6); entriesnum=17
- header checksum mod 256 = 0x0 (envytools requires 0; bit.c:91-92 -> traversal would abort here)
- header raw: [255, 184, 66, 73, 84, 0, 0, 1, 12, 6, 17, 70]
- BIT span: [432, 546]
- entries:
   idx  0 type='2'(0x32) ver=1 t_len=4 t_offset=0x0232  -> mapped 0x232 (direct shadow offset)
   idx  1 type='B'(0x42) ver=2 t_len=37 t_offset=0x023e  -> mapped 0x23e (direct shadow offset)
   idx  2 type='C'(0x43) ver=2 t_len=44 t_offset=0x0263  -> mapped 0x263 (direct shadow offset)
   idx  3 type='D'(0x44) ver=1 t_len=4 t_offset=0x028f  -> mapped 0x28f (direct shadow offset)
   idx  4 type='I'(0x49) ver=1 t_len=36 t_offset=0x0293  -> mapped 0x293 (direct shadow offset)
   idx  5 type='M'(0x4d) ver=2 t_len=29 t_offset=0x02b7  -> mapped 0x2b7 (direct shadow offset)
   idx  6 type='N'(0x4e) ver=0 t_len=0 t_offset=0x0000 NULL -> mapped None (null pointer (NOP))
   idx  7 type='P'(0x50) ver=2 t_len=224 t_offset=0x02d4  -> mapped 0x2d4 (direct shadow offset)
   idx  8 type='S'(0x53) ver=2 t_len=24 t_offset=0x03b4  -> mapped 0x3b4 (direct shadow offset)
   idx  9 type='T'(0x54) ver=1 t_len=2 t_offset=0x03cc  -> mapped 0x3cc (direct shadow offset)
   idx 10 type='U'(0x55) ver=1 t_len=5 t_offset=0x03ce  -> mapped 0x3ce (direct shadow offset)
   idx 11 type='V'(0x56) ver=1 t_len=6 t_offset=0x03d3  -> mapped 0x3d3 (direct shadow offset)
   idx 12 type='x'(0x78) ver=1 t_len=8 t_offset=0x03d9  -> mapped 0x3d9 (direct shadow offset)
   idx 13 type='d'(0x64) ver=1 t_len=2 t_offset=0x03e1  -> mapped 0x3e1 (direct shadow offset)
   idx 14 type='p'(0x70) ver=2 t_len=4 t_offset=0x03e3  -> mapped 0x3e3 (direct shadow offset)
   idx 15 type='u'(0x75) ver=1 t_len=13 t_offset=0x03e7  -> mapped 0x3e7 (direct shadow offset)
   idx 16 type='i'(0x69) ver=2 t_len=104 t_offset=0x03f4  -> mapped 0x3f4 (direct shadow offset)
- power directory (P): off 0x2d4, t_len 224 (= 56 x 4: True)

## Per-slot directory audit (56 u32 pointers, P token / P2_tbls)
| idx | P2 name (power.c:82-103) | raw u32 | mapped target (rom) | first bytes | status |
|-----|--------------------------|---------|---------------------|-------------|--------|
|  0 | PERFORMANCE | 0x1ab55 | 0x54155             | 60 0a 05 07 06 0a | UNSUPPORTED_V60 |
|  1 | MEMORY TIMINGS MAPPING | 0x1b000 | 0x54600             | 11 1a 3c 21 0a 07 | HEADER_ONLY |
|  2 | MEMORY TIMINGS | 0x1bac4 | 0x550c4             | 20 06 4a 0c 00 3c | HEADER_ONLY |
|  3 | VOLTAGE | 0x0000 | -                    | - | NULL |
|  4 | THERMAL | 0x0000 | -                    | - | NULL |
|  5 | THERMAL DEVICES | 0x1f123 | 0x58723             | 10 04 03 12 01 00 | DECODED |
|  6 | THERMAL COOLERS | 0x0000 | -                    | - | NULL |
|  7 | PERF SETTINGS SCRIPT | 0x0000 | -                    | - | NULL |
|  8 | VOLT MAPPING | 0x1ce9c | 0x5649c             | 30 09 19 14 18 96 | HEADER_ONLY |
|  9 | VENTURA | 0x0000 | -                    | - | NULL |
| 10 | POWER SENSE | 0x1e3e0 | 0x579e0             | 20 08 31 07 00 00 | HEADER_SOURCE_SHAPE |
| 11 | POWER BUDGET | 0x1e892 | 0x57e92             | 30 2c 42 14 14 00 | DECODED |
| 12 | BOOST | 0x0000 | -                    | - | NULL |
| 13 | CSTEP | 0x0000 | -                    | - | NULL |
| 14 | POWER BASE CLOCK | 0x1ad26 | 0x54326             | 20 13 01 11 04 0a | HEADER_SOURCE_SHAPE |
| 15 | POWER TOPOLOGY | 0x1e53f | 0x57b3f             | 20 06 16 14 1b 0f | HEADER_SOURCE_SHAPE |
| 16 | POWER LEAKAGE | 0x1ef61 | 0x58561             | 10 05 19 0b 00 05 | HEADER_SOURCE_SHAPE |
| 17 | PERF TEST SPEC | 0x1aff2 | 0x545f2             | 10 0e 46 b7 09 28 | DECODED |
| 18 | THERMAL CHANNEL | 0x1f15d | 0x5875d             | 10 09 05 20 00 01 | HEADER_ONLY |
| 19 | THERMAL ADJUSTMENT | 0x1f206 | 0x58806             | 10 04 05 02 00 00 | HEADER_ONLY |
| 20 | THERMAL POLICY | 0x1f079 | 0x58679             | 10 0a 28 04 ff ff | DECODED |
| 21 | PSTATE MEMORY CLK FREQ | 0x0000 | -                    | - | NULL |
| 22 | FAN COOLERS | 0x1f224 | 0x58824             | 10 06 1a 02 00 01 | HEADER_ONLY |
| 23 | POWER FAN_MGMT | 0x1f25e | 0x5885e             | 10 06 36 02 00 01 | HEADER_ONLY |
| 24 | DI/DT | 0x0000 | -                    | - | NULL |
| 25 | FAN TEST | 0x1f2d0 | 0x588d0             | 10 04 05 02 01 00 | HEADER_ONLY |
| 26 | VOLTAGE RAIL | 0x4d7b | 0x3e37b             | ff 83 d9 6d 14 bc | HEADER_ONLY |
| 27 | VOLTAGE DEVICE | 0x4d17 | 0x3e317             | a1 25 f7 28 21 be | HEADER_ONLY |
| 28 | VOLTAGE POLICY | 0x4d8e | 0x3e38e             | 25 c6 2a cb 77 e6 | HEADER_ONLY |
| 29 | LOW POWER | 0x1cc22 | 0x56222             | 10 06 07 05 f4 01 | HEADER_ONLY |
| 30 | LOW POWER PCIe | 0x1cc4b | 0x5624b             | 10 05 0c 05 00 ff | HEADER_ONLY |
| 31 | LOW POWER PCIe-PLATFORM | 0x1cc8c | 0x5628c             | 10 04 0d 05 00 00 | HEADER_ONLY |
| 32 | LOW POWER GR | 0x1ccd1 | 0x562d1             | 10 0a 05 05 00 58 | HEADER_ONLY |
| 33 | LOW POWER MS | 0x1ccf4 | 0x562f4             | 10 07 0f 05 00 0a | HEADER_ONLY |
| 34 | LOW POWER DI | 0x1cd46 | 0x56346             | 10 0e 05 05 ff 58 | HEADER_ONLY |
| 35 | LOW POWER GC6 | 0x1cd6d | 0x5636d             | 10 3a 05 05 ff 00 | HEADER_ONLY |
| 36 | LOW POWER PSI | 0x1cddc | 0x563dc             | 30 09 04 02 c8 00 | HEADER_ONLY |
| 37 | THERM MONITOR | 0x1f214 | 0x58814             | 10 04 02 06 03 00 | HEADER_ONLY |
| 38 | OVERCLOCKING | 0x1f2de | 0x588de             | 10 06 05 02 05 02 | HEADER_ONLY |
| 39 | (unnamed, offset >0x98) | 0x1cded | 0x563ed             | 10 06 18 05 00 00 | OPAQUE_NO_SCHEMA |
| 40 | (unnamed, offset >0x98) | 0x1f2f8 | 0x588f8             | 10 04 13 12 03 00 | OPAQUE_NO_SCHEMA |
| 41 | (unnamed, offset >0x98) | 0x1f452 | 0x58a52             | 10 07 05 12 00 e8 | OPAQUE_NO_SCHEMA |
| 42 | (unnamed, offset >0x98) | 0x1f4b3 | 0x58ab3             | 10 06 18 08 c8 00 | OPAQUE_NO_SCHEMA |
| 43 | (unnamed, offset >0x98) | 0x1f579 | 0x58b79             | 10 05 0a 08 00 81 | OPAQUE_NO_SCHEMA |
| 44 | (unnamed, offset >0x98) | 0x1f704 | 0x58d04             | 10 04 06 04 00 03 | OPAQUE_NO_SCHEMA |
| 45 | (unnamed, offset >0x98) | 0x1f720 | 0x58d20             | 10 04 1d 08 00 00 | OPAQUE_NO_SCHEMA |
| 46 | (unnamed, offset >0x98) | 0x1f5ce | 0x58bce             | 10 04 0d 02 00 00 | OPAQUE_NO_SCHEMA |
| 47 | (unnamed, offset >0x98) | 0x1ce6b | 0x5646b             | 10 04 09 05 0a 00 | OPAQUE_NO_SCHEMA |
| 48 | (unnamed, offset >0x98) | 0x1cdc0 | 0x563c0             | 10 08 04 05 ff 00 | OPAQUE_NO_SCHEMA |
| 49 | (unnamed, offset >0x98) | 0x0000 | -                    | - | NULL |
| 50 | (unnamed, offset >0x98) | 0x0000 | -                    | - | NULL |
| 51 | (unnamed, offset >0x98) | 0x0000 | -                    | - | NULL |
| 52 | (unnamed, offset >0x98) | 0x0000 | -                    | - | NULL |
| 53 | (unnamed, offset >0x98) | 0x0000 | -                    | - | NULL |
| 54 | (unnamed, offset >0x98) | 0x0000 | -                    | - | NULL |
| 55 | (unnamed, offset >0x98) | 0x0000 | -                    | - | NULL |

## Decoded tables (source-backed, field-level)
### slot 5: THERMAL DEVICES (P2 off 0x14)
- source: envy_bios_parse_power_therm_devices (power.c:239; header switch power.c:248; entry fields power.c:260-262)
- version=0x10 hlen=4 rlen=3 entries=18 extent=[362275, 362333] len=58
   entry 0: off=0x58727 raw=[1, 0, 0]
   entry 1: off=0x5872a raw=[2, 0, 0]
   entry 2: off=0x5872d raw=[2, 1, 0]
   entry 3: off=0x58730 raw=[2, 2, 0]
   entry 4: off=0x58733 raw=[0, 3, 0]
   entry 5: off=0x58736 raw=[0, 4, 0]
   entry 6: off=0x58739 raw=[0, 5, 0]
   entry 7: off=0x5873c raw=[0, 0, 0]
   entry 8: off=0x5873f raw=[0, 0, 0]
   entry 9: off=0x58742 raw=[3, 0, 0]
   entry 10: off=0x58745 raw=[0, 1, 0]
   entry 11: off=0x58748 raw=[0, 0, 0]
   entry 12: off=0x5874b raw=[0, 0, 0]
   entry 13: off=0x5874e raw=[0, 0, 0]
   entry 14: off=0x58751 raw=[0, 0, 0]
   entry 15: off=0x58754 raw=[0, 0, 0]
   entry 16: off=0x58757 raw=[0, 0, 0]
   entry 17: off=0x5875a raw=[0, 0, 0]
- unknown bytes preserved: {'header_unknown': []}
### slot 11: POWER BUDGET (P2 off 0x2c)
- source: envy_bios_parse_power_budget (power.c:644; versions 0x10/0x20/0x30 at power.c:654; cap_entry@0x0a for 0x30 at power.c:671-673; entry fields power.c:701-708)
- version=0x30 hlen=44 rlen=66 entries=20 extent=[360082, 361446] len=1364
- cap_entry@0x0a = 2
   entry 0: off=0x57ebe raw=[10, 11, 32, 78, 0, 0, 40, 79, 76, 0, 40, 79, 76, 0, 0, 8, 0, 16, 1, 0, 0, 0, 255, 255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 64, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 1: off=0x57f00 raw=[4, 8, 1, 0, 0, 0, 40, 70, 15, 0, 40, 70, 15, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 2: off=0x57f42 raw=[33, 9, 176, 173, 1, 0, 192, 206, 2, 0, 96, 91, 3, 0, 1, 0, 4, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 43, 7, 0, 12, 128, 16, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 3: off=0x57f84 raw=[4, 3, 232, 3, 0, 0, 0, 250, 0, 0, 224, 40, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 4: off=0x57fc6 raw=[4, 4, 232, 3, 0, 0, 56, 62, 2, 0, 224, 159, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 5: off=0x58008 raw=[0, 5, 232, 3, 0, 0, 208, 120, 2, 0, 152, 171, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 6: off=0x5804a raw=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 7: off=0x5808c raw=[21, 3, 232, 3, 0, 0, 248, 42, 0, 0, 44, 51, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 8: off=0x580ce raw=[21, 4, 232, 3, 0, 0, 104, 66, 0, 0, 56, 99, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 9: off=0x58110 raw=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 10: off=0x58152 raw=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 11: off=0x58194 raw=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 12: off=0x581d6 raw=[21, 18, 160, 134, 1, 0, 128, 44, 3, 0, 128, 44, 3, 0, 0, 2, 1, 0, 0, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 13: off=0x58218 raw=[26, 19, 232, 3, 0, 0, 208, 120, 2, 0, 208, 120, 2, 0, 0, 8, 0, 16, 1, 0, 0, 0, 255, 255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 64, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 14: off=0x5825a raw=[0, 11, 1, 0, 0, 0, 40, 79, 76, 0, 40, 79, 76, 0, 0, 8, 0, 16, 1, 0, 0, 0, 255, 255, 128, 2, 0, 0, 0, 0, 0, 0, 0, 0, 64, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 15: off=0x5829c raw=[10, 11, 1, 0, 0, 0, 40, 79, 76, 0, 40, 79, 76, 0, 0, 8, 0, 16, 1, 0, 0, 0, 255, 255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 65, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 16: off=0x582de raw=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 17: off=0x58320 raw=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 18: off=0x58362 raw=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 19: off=0x583a4 raw=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
### slot 17: PERF TEST SPEC (P2 off 0x44)
- source: envy_bios_parse_power_unk44 (power.c:1188; version switch power.c:1197; hlen@+1 power.c:1199; 'it does not appear as if this table has entries at all' power.c:1200)
- version=0x10 hlen=14 rlen=None entries=0 extent=[345586, 345600] len=14
- unknown bytes preserved: {'note': 'source reads only version@+0 and hlen@+1; bytes +2..+13 kept raw, not interpreted (offset+2/+3 are NOT entry_size/count for this parser)', 'raw': [70, 183, 9, 40, 108, 2, 0, 29, 90, 30, 30, 75]}
### slot 20: THERMAL POLICY (P2 off 0x50)
- source: envy_bios_parse_power_unk50 (power.c:1334; entry field offsets power.c:1396-1405)
- version=0x10 hlen=10 rlen=40 entries=4 extent=[362105, 362275] len=170
   entry 0: off=0x58683 raw=[1, 0, 32, 11, 32, 11, 32, 11, 200, 0, 19, 64, 255, 255, 255, 127, 32, 0, 0, 0, 224, 255, 160, 255, 136, 19, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 1: off=0x586ab raw=[0, 255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   entry 2: off=0x586d3 raw=[0, 0, 96, 10, 32, 8, 0, 11, 200, 0, 19, 64, 255, 255, 255, 127, 32, 0, 0, 0, 224, 255, 160, 255, 136, 19, 0, 128, 96, 10, 2, 0, 192, 10, 2, 0, 0, 11, 1, 0]
   entry 3: off=0x586fb raw=[0, 255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

## Slot 0 — PERFORMANCE v60: UNSUPPORTED
- target: 0x54155; raw header: [96, 10, 5, 7, 6, 10, 1, 7, 0, 1, 7, 0, 0, 0, 255, 133]
- PERFORMANCE v60 — UNSUPPORTED; generic hdr+esz*cnt = 0x0a+0x05*0x07 = 45 bytes explicitly NOT adopted

## Structural facts
- from 'B' (0x2883e) through 'i' (ends 0x28a5c) every target equals previous target + previous t_len (packed, no overlaps, no gaps)
- '2' target 0x28832 len 4 stands apart; gaps at [0x28822,0x28832) and [0x28836,0x2883e)
- no overlap between any BIT-targeted tables; power directory [0x288d4,0x289b4) is P itself and abuts M/S
- gaps: [{'span': [165820, 165938], 'len': 118, 'note': 'between BIT entries end (0x28822) and 2 target (0x28832)'}, {'span': [165942, 165950], 'len': 8, 'note': 'between 2 extent end (0x28836) and B start (0x2883e)'}]
- trailing after i: {'span': [166492, 166512], 'note': 'after i extent end; uncharted bytes'}
- slot extent adjacencies (claimed extents only): [{'slot_i': 10, 'extent_i_end': 359231, 'slot_j_target': 15, 'note': 'extent end of slot 10 == target of slot 15'}, {'slot_i': 16, 'extent_i_end': 362105, 'slot_j_target': 20, 'note': 'extent end of slot 16 == target of slot 20'}, {'slot_i': 20, 'extent_i_end': 362275, 'slot_j_target': 5, 'note': 'extent end of slot 20 == target of slot 5'}]

## Cross-image comparison
- T4 vs rom[0:495616]: 19 byte diffs (T4 is rom prefix with 19 patches):
   0x5669c rom=112 t4=64
   0x5669d rom=118 t4=84
   0x5669e rom=130 t4=137
   0x566a0 rom=112 t4=64
   0x566a1 rom=118 t4=84
   0x566a2 rom=130 t4=137
   0x566a4 rom=112 t4=64
   0x566a5 rom=118 t4=84
   0x566a6 rom=130 t4=137
   0x566b4 rom=176 t4=64
   0x566b5 rom=131 t4=84
   0x566b6 rom=133 t4=137
   0x566b8 rom=176 t4=64
   0x566b9 rom=131 t4=84
   0x566ba rom=133 t4=137
   0x566bc rom=176 t4=64
   0x566bd rom=131 t4=84
   0x566be rom=133 t4=137
   0x767ff rom=51 t4=229
- shadow vs rom[0x28600:0xB9E00]: 14 diffs over 0xD7A00 compared bytes
   shadow=0xd1a88 rom_byte=5 shadow_byte=4
   shadow=0xd1a9a rom_byte=12 shadow_byte=13
   shadow=0xd1c88 rom_byte=209 shadow_byte=225
   shadow=0xd1cb0 rom_byte=51 shadow_byte=48
   shadow=0xd1cb2 rom_byte=52 shadow_byte=50
   shadow=0xd1cb3 rom_byte=57 shadow_byte=53
   shadow=0xd1cb4 rom_byte=55 shadow_byte=49
   shadow=0xd1cb5 rom_byte=52 shadow_byte=51
   shadow=0xd5a1a rom_byte=25 shadow_byte=17
   shadow=0xd5b30 rom_byte=51 shadow_byte=48
   shadow=0xd5b32 rom_byte=52 shadow_byte=50
   shadow=0xd5b33 rom_byte=57 shadow_byte=53
   shadow=0xd5b34 rom_byte=55 shadow_byte=49
   shadow=0xd5b35 rom_byte=52 shadow_byte=51
- banks: legacy1==legacy2: True; EFI1==EFI2: True; directory duplicated at 0xA18D4: True

## Opaque tables (explicit)
- BIT token '2' (i2c): target bytes are all zero; degenerate/empty in this image; no field decode
- BIT token 'N': null pointer (t_offset=0); NOP per bit.c bit_types
- BIT tokens 'B','C','D','I','M','S','T','U','V','x','d','p','u','i': targets lie inside one packed blob with no version-first layout; no envytools field schema matches this image layout; raw bytes preserved, not interpreted
- PERF/slot directory indices 26, 27, 28: non-null u32 pointers whose mapped targets begin 0xff / 0xa1 / 0x25 — not a coherent table header under the image base; stale or out-of-scope pointers
- PERF/slot index 0 (PERFORMANCE): version byte 0x60 (v60); no envytools field parser; generic entry-size formula explicitly rejected
- PERF/slot directory indices 39-55: not named in P2_tbls source (power.c:82-103 ends at offset 0x98); no parser identified

## Per-token status summary
- total tokens audited: 219
  - DECODED: 12
  - HEADER_ONLY: 63
  - HEADER_SOURCE_SHAPE: 12
  - NULL: 51
  - OPAQUE_NO_SCHEMA: 30
  - OPAQUE_PACKED_BLOB: 45
  - POWER_DIRECTORY: 3
  - UNSUPPORTED_V60: 3

## Reproduction
```sh
python3 vbios_full_token_audit.py /tmp/v11chk/outputs/CMP40HX_ORIGINAL_1MB.bin /tmp/v11chk/outputs/cmp40hx_t4.bin /tmp/v11chk/RAW_DATA/vbios_shadow.bin /home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_FULL_TOKEN_AUDIT
```

## Output hashes
- vbios_token_audit.json: c0dbe3f184ece1f52485683506d96629f4e9e6ab303d095a845d28abacb701af
- run_vbios_full_token_audit.sh: cdfe92ac2d3c9bd0947037c0c839e80f48a9938f9a7cf656d5f5ee659e5c4bef

## Method note
Offsets, versions, hlen/rlen/counts and extent arithmetic are parser traversal facts (envytools bit.c/power.c, cited above). 
Semantic field decoding is claimed only for slots 5, 11, 17, 20, strictly version-gated per power.c. 
Slot 0 (v60) and all other tables are deliberately left opaque with reasons stated. 
No hardware access, ROM flashing, keys, or cryptographic semantics involved.

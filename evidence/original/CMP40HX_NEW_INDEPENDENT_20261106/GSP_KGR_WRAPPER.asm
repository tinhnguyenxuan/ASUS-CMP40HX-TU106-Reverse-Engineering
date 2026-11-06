
/tmp/cmp40hx_gsp_inner.elf:	file format elf64-littleriscv

Disassembly of section .section_task_rm_elf_text_instance:

0000000004588000 <.section_task_rm_elf_text_instance>:
 4bb6c90: 13 01 01 ff  	addi	sp, sp, -0x10
 4bb6c94: 23 34 81 00  	sd	s0, 0x8(sp)
 4bb6c98: 13 04 01 01  	addi	s0, sp, 0x10
 4bb6c9c: 83 37 05 00  	ld	a5, 0x0(a0)
 4bb6ca0: 03 34 81 00  	ld	s0, 0x8(sp)
 4bb6ca4: 13 86 05 00  	mv	a2, a1
 4bb6ca8: 83 b7 87 31  	ld	a5, 0x318(a5)
 4bb6cac: b7 36 00 00  	lui	a3, 0x3
 4bb6cb0: b7 15 80 20  	lui	a1, 0x20801
 4bb6cb4: 93 86 06 a6  	addi	a3, a3, -0x5a0
 4bb6cb8: 93 85 75 a2  	addi	a1, a1, -0x5d9
 4bb6cbc: 13 01 01 01  	addi	sp, sp, 0x10
 4bb6cc0: 67 80 07 00  	jr	a5

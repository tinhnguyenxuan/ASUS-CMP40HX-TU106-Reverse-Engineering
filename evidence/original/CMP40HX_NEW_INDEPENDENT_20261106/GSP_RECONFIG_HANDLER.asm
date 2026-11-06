
/tmp/cmp40hx_gsp_inner.elf:	file format elf64-littleriscv

Disassembly of section .section_task_rm_elf_text_instance:

0000000004588000 <.section_task_rm_elf_text_instance>:
 4bbdd1c: 13 01 01 fa  	addi	sp, sp, -0x60
 4bbdd20: 23 38 81 04  	sd	s0, 0x50(sp)
 4bbdd24: 23 30 21 05  	sd	s2, 0x40(sp)
 4bbdd28: 23 34 51 03  	sd	s5, 0x28(sp)
 4bbdd2c: 23 30 61 03  	sd	s6, 0x20(sp)
 4bbdd30: 23 3c 11 04  	sd	ra, 0x58(sp)
 4bbdd34: 23 34 91 04  	sd	s1, 0x48(sp)
 4bbdd38: 23 3c 31 03  	sd	s3, 0x38(sp)
 4bbdd3c: 23 38 41 03  	sd	s4, 0x30(sp)
 4bbdd40: 13 04 01 06  	addi	s0, sp, 0x60
 4bbdd44: 83 37 05 16  	ld	a5, 0x160(a0)
 4bbdd48: 83 a6 05 00  	lw	a3, 0x0(a1)
 4bbdd4c: b7 3a 20 04  	lui	s5, 0x4203
 4bbdd50: 83 b9 87 0e  	ld	s3, 0xe8(a5)
 4bbdd54: b7 27 00 00  	lui	a5, 0x2
 4bbdd58: 03 b6 0a 93  	ld	a2, -0x6d0(s5)
 4bbdd5c: 23 3c c4 fa  	sd	a2, -0x48(s0)
 4bbdd60: 13 06 00 00  	li	a2, 0x0
 4bbdd64: b3 87 f9 00  	add	a5, s3, a5
 4bbdd68: 03 b7 07 f6  	ld	a4, -0xa0(a5)
 4bbdd6c: 23 2a d4 fa  	sw	a3, -0x4c(s0)
 4bbdd70: 13 89 05 00  	mv	s2, a1
 4bbdd74: 13 8b 00 00  	mv	s6, ra
 4bbdd78: 83 b5 07 f5  	ld	a1, -0xb0(a5)
 4bbdd7c: 63 06 07 00  	beqz	a4, 0x4bbdd88 <.section_task_rm_elf_text_instance+0x635d88>
 4bbdd80: 83 c7 b9 6e  	lbu	a5, 0x6eb(s3)
 4bbdd84: 63 9a 07 08  	bnez	a5, 0x4bbde18 <.section_task_rm_elf_text_instance+0x635e18>
 4bbdd88: 13 85 09 00  	mv	a0, s3
 4bbdd8c: 23 34 b4 fa  	sd	a1, -0x58(s0)
 4bbdd90: 97 40 fb ff  	auipc	ra, 0xfffb4
 4bbdd94: e7 80 c0 ec  	jalr	-0x134(ra)
 4bbdd98: 83 35 84 fa  	ld	a1, -0x58(s0)
 4bbdd9c: 03 26 09 00  	lw	a2, 0x0(s2)
 4bbdda0: 13 0a 05 00  	mv	s4, a0
 4bbdda4: 83 b7 05 20  	ld	a5, 0x200(a1)
 4bbdda8: 93 06 44 fb  	addi	a3, s0, -0x4c
 4bbddac: 13 85 09 00  	mv	a0, s3
 4bbddb0: e7 80 07 00  	jalr	a5
 4bbddb4: 9b 04 05 00  	sext.w	s1, a0
 4bbddb8: 63 9a 04 08  	bnez	s1, 0x4bbde4c <.section_task_rm_elf_text_instance+0x635e4c>
 4bbddbc: 83 37 8a 7e  	ld	a5, 0x7e8(s4)
 4bbddc0: 03 26 44 fb  	lw	a2, -0x4c(s0)
 4bbddc4: 93 06 49 00  	addi	a3, s2, 0x4
 4bbddc8: 93 05 0a 00  	mv	a1, s4
 4bbddcc: 13 85 09 00  	mv	a0, s3
 4bbddd0: e7 80 07 00  	jalr	a5
 4bbddd4: 9b 04 05 00  	sext.w	s1, a0
 4bbddd8: 03 37 84 fb  	ld	a4, -0x48(s0)
 4bbdddc: 83 b7 0a 93  	ld	a5, -0x6d0(s5)
 4bbdde0: b3 47 f7 00  	xor	a5, a4, a5
 4bbdde4: 13 07 00 00  	li	a4, 0x0
 4bbdde8: 63 94 07 0c  	bnez	a5, 0x4bbdeb0 <.section_task_rm_elf_text_instance+0x635eb0>
 4bbddec: 83 30 81 05  	ld	ra, 0x58(sp)
 4bbddf0: 03 34 01 05  	ld	s0, 0x50(sp)
 4bbddf4: 03 39 01 04  	ld	s2, 0x40(sp)
 4bbddf8: 83 39 81 03  	ld	s3, 0x38(sp)
 4bbddfc: 03 3a 01 03  	ld	s4, 0x30(sp)
 4bbde00: 83 3a 81 02  	ld	s5, 0x28(sp)
 4bbde04: 03 3b 01 02  	ld	s6, 0x20(sp)
 4bbde08: 13 85 04 00  	mv	a0, s1
 4bbde0c: 83 34 81 04  	ld	s1, 0x48(sp)
 4bbde10: 13 01 01 06  	addi	sp, sp, 0x60
 4bbde14: 67 80 00 00  	ret
 4bbde18: b7 77 00 00  	lui	a5, 0x7
 4bbde1c: 33 07 f7 00  	add	a4, a4, a5
 4bbde20: 83 47 87 46  	lbu	a5, 0x468(a4)
 4bbde24: e3 82 07 f6  	beqz	a5, 0x4bbdd88 <.section_task_rm_elf_text_instance+0x635d88>
 4bbde28: 83 37 07 47  	ld	a5, 0x470(a4)
 4bbde2c: e3 8e 07 f4  	beqz	a5, 0x4bbdd88 <.section_task_rm_elf_text_instance+0x635d88>
 4bbde30: b7 35 9a 05  	lui	a1, 0x59a3
 4bbde34: 93 85 05 77  	addi	a1, a1, 0x770
 4bbde38: 13 05 10 00  	li	a0, 0x1
 4bbde3c: 97 20 a0 00  	auipc	ra, 0xa02
 4bbde40: e7 80 00 f3  	jalr	-0xd0(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bbde44: 93 04 60 05  	li	s1, 0x56
 4bbde48: 6f f0 1f f9  	j	0x4bbddd8 <.section_task_rm_elf_text_instance+0x635dd8>
 4bbde4c: 93 95 04 02  	slli	a1, s1, 0x20
 4bbde50: 37 36 9a 05  	lui	a2, 0x59a3
 4bbde54: 93 d5 05 02  	srli	a1, a1, 0x20
 4bbde58: 13 05 20 00  	li	a0, 0x2
 4bbde5c: 13 06 86 75  	addi	a2, a2, 0x758
 4bbde60: 97 20 a0 00  	auipc	ra, 0xa02
 4bbde64: e7 80 c0 f0  	jalr	-0xf4(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bbde68: 13 06 0b 00  	mv	a2, s6
 4bbde6c: 93 05 00 00  	li	a1, 0x0
 4bbde70: 13 85 04 00  	mv	a0, s1
 4bbde74: 97 80 9e ff  	auipc	ra, 0xff9e8
 4bbde78: e7 80 00 0d  	jalr	0xd0(ra)
 4bbde7c: b7 77 39 04  	lui	a5, 0x4397
 4bbde80: 83 c7 07 8d  	lbu	a5, -0x730(a5)
 4bbde84: 63 96 07 00  	bnez	a5, 0x4bbde90 <.section_task_rm_elf_text_instance+0x635e90>
 4bbde88: 73 00 10 00  	ebreak
 4bbde8c: 6f f0 df f4  	j	0x4bbddd8 <.section_task_rm_elf_text_instance+0x635dd8>
 4bbde90: b7 87 39 04  	lui	a5, 0x4398
 4bbde94: 83 b7 87 c5  	ld	a5, -0x3a8(a5)
 4bbde98: 37 17 11 00  	lui	a4, 0x111
 4bbde9c: 13 07 07 30  	addi	a4, a4, 0x300
 4bbdea0: b3 87 e7 00  	add	a5, a5, a4
 4bbdea4: 23 a0 07 00  	sw	zero, 0x0(a5)
 4bbdea8: 73 00 10 00  	ebreak
 4bbdeac: 6f f0 df f2  	j	0x4bbddd8 <.section_task_rm_elf_text_instance+0x635dd8>
 4bbdeb0: 97 10 93 00  	auipc	ra, 0x931
 4bbdeb4: e7 80 00 b5  	jalr	-0x4b0(ra) <.section_task_rm_elf_text_instance+0xf66a00>

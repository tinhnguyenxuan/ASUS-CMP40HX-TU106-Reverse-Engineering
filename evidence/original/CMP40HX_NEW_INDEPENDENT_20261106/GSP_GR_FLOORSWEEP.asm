
/tmp/cmp40hx_gsp_inner.elf:	file format elf64-littleriscv

Disassembly of section .section_task_rm_elf_text_instance:

0000000004588000 <.section_task_rm_elf_text_instance>:
 4bc63c4: 13 01 01 e0  	addi	sp, sp, -0x200
 4bc63c8: 23 38 81 1e  	sd	s0, 0x1f0(sp)
 4bc63cc: 23 3c 31 1d  	sd	s3, 0x1d8(sp)
 4bc63d0: 23 38 41 1d  	sd	s4, 0x1d0(sp)
 4bc63d4: 23 3c b1 19  	sd	s11, 0x198(sp)
 4bc63d8: 23 3c 11 1e  	sd	ra, 0x1f8(sp)
 4bc63dc: 23 34 91 1e  	sd	s1, 0x1e8(sp)
 4bc63e0: 23 30 21 1f  	sd	s2, 0x1e0(sp)
 4bc63e4: 23 34 51 1d  	sd	s5, 0x1c8(sp)
 4bc63e8: 23 30 61 1d  	sd	s6, 0x1c0(sp)
 4bc63ec: 23 3c 71 1b  	sd	s7, 0x1b8(sp)
 4bc63f0: 23 38 81 1b  	sd	s8, 0x1b0(sp)
 4bc63f4: 23 34 91 1b  	sd	s9, 0x1a8(sp)
 4bc63f8: 23 30 a1 1b  	sd	s10, 0x1a0(sp)
 4bc63fc: 13 04 01 20  	addi	s0, sp, 0x200
 4bc6400: 83 37 05 16  	ld	a5, 0x160(a0)
 4bc6404: 93 8d 05 00  	mv	s11, a1
 4bc6408: 37 37 20 04  	lui	a4, 0x4203
 4bc640c: 83 b4 87 0e  	ld	s1, 0xe8(a5)
 4bc6410: b7 29 00 00  	lui	s3, 0x2
 4bc6414: 37 36 00 00  	lui	a2, 0x3
 4bc6418: b3 89 34 01  	add	s3, s1, s3
 4bc641c: 83 37 07 93  	ld	a5, -0x6d0(a4)
 4bc6420: 23 34 f4 f8  	sd	a5, -0x78(s0)
 4bc6424: 93 07 00 00  	li	a5, 0x0
 4bc6428: 13 0a 05 00  	mv	s4, a0
 4bc642c: 13 06 06 a6  	addi	a2, a2, -0x5a0
 4bc6430: 93 05 00 00  	li	a1, 0x0
 4bc6434: 13 85 0d 00  	mv	a0, s11
 4bc6438: 03 b9 09 f5  	ld	s2, -0xb0(s3)
 4bc643c: 23 34 94 e4  	sd	s1, -0x1b8(s0)
 4bc6440: 23 3c 14 e0  	sd	ra, -0x1e8(s0)
 4bc6444: 97 f0 6a 00  	auipc	ra, 0x6af
 4bc6448: e7 80 c0 31  	jalr	0x31c(ra) <.section_task_rm_elf_text_instance+0xced760>
 4bc644c: 83 b7 09 f6  	ld	a5, -0xa0(s3)
 4bc6450: 63 88 07 0a  	beqz	a5, 0x4bc6500 <.section_task_rm_elf_text_instance+0x63e500>
 4bc6454: 03 c7 b4 6e  	lbu	a4, 0x6eb(s1)
 4bc6458: 13 85 04 00  	mv	a0, s1
 4bc645c: 63 02 07 0a  	beqz	a4, 0x4bc6500 <.section_task_rm_elf_text_instance+0x63e500>
 4bc6460: 37 77 00 00  	lui	a4, 0x7
 4bc6464: b3 87 e7 00  	add	a5, a5, a4
 4bc6468: 03 c7 87 46  	lbu	a4, 0x468(a5)
 4bc646c: 63 0a 07 08  	beqz	a4, 0x4bc6500 <.section_task_rm_elf_text_instance+0x63e500>
 4bc6470: 83 b7 07 47  	ld	a5, 0x470(a5)
 4bc6474: 63 86 07 08  	beqz	a5, 0x4bc6500 <.section_task_rm_elf_text_instance+0x63e500>
 4bc6478: 83 37 0a 16  	ld	a5, 0x160(s4)
 4bc647c: 13 06 84 e6  	addi	a2, s0, -0x198
 4bc6480: 83 b5 07 0f  	ld	a1, 0xf0(a5)
 4bc6484: 97 10 9d 00  	auipc	ra, 0x9d1
 4bc6488: e7 80 80 21  	jalr	0x218(ra) <.section_task_rm_elf_text_instance+0x100f69c>
 4bc648c: 9b 04 05 00  	sext.w	s1, a0
 4bc6490: e3 9a 04 0c  	bnez	s1, 0x4bc6d64 <.section_task_rm_elf_text_instance+0x63ed64>
 4bc6494: 03 36 84 e6  	ld	a2, -0x198(s0)
 4bc6498: 93 06 40 05  	li	a3, 0x54
 4bc649c: 93 05 40 05  	li	a1, 0x54
 4bc64a0: 13 06 86 11  	addi	a2, a2, 0x118
 4bc64a4: 13 05 84 e7  	addi	a0, s0, -0x188
 4bc64a8: 97 f0 6a 00  	auipc	ra, 0x6af
 4bc64ac: e7 80 00 ef  	jalr	-0x110(ra) <.section_task_rm_elf_text_instance+0xced398>
 4bc64b0: 93 05 40 05  	li	a1, 0x54
 4bc64b4: 13 05 84 e7  	addi	a0, s0, -0x188
 4bc64b8: 97 d0 6a 00  	auipc	ra, 0x6ad
 4bc64bc: e7 80 00 50  	jalr	0x500(ra) <.section_task_rm_elf_text_instance+0xceb9b8>
 4bc64c0: b7 07 10 00  	lui	a5, 0x100
 4bc64c4: 93 87 f7 ff  	addi	a5, a5, -0x1
 4bc64c8: 23 38 f4 e2  	sd	a5, -0x1d0(s0)
 4bc64cc: 93 87 4d 54  	addi	a5, s11, 0x544
 4bc64d0: 9b 0b 05 00  	sext.w	s7, a0
 4bc64d4: 23 34 f4 e0  	sd	a5, -0x1f8(s0)
 4bc64d8: 93 8a 04 00  	mv	s5, s1
 4bc64dc: 23 3c b4 e3  	sd	s11, -0x1c8(s0)
 4bc64e0: 03 37 04 e3  	ld	a4, -0x1d0(s0)
 4bc64e4: 83 37 04 e8  	ld	a5, -0x180(s0)
 4bc64e8: b3 f7 e7 00  	and	a5, a5, a4
 4bc64ec: 03 37 84 e7  	ld	a4, -0x188(s0)
 4bc64f0: b3 e7 e7 00  	or	a5, a5, a4
 4bc64f4: 63 96 07 2c  	bnez	a5, 0x4bc67c0 <.section_task_rm_elf_text_instance+0x63e7c0>
 4bc64f8: 93 04 00 00  	li	s1, 0x0
 4bc64fc: 6f 00 c0 26  	j	0x4bc6768 <.section_task_rm_elf_text_instance+0x63e768>
 4bc6500: 83 34 84 e4  	ld	s1, -0x1b8(s0)
 4bc6504: 13 85 04 00  	mv	a0, s1
 4bc6508: 97 b0 fa ff  	auipc	ra, 0xfffab
 4bc650c: e7 80 40 75  	jalr	0x754(ra)
 4bc6510: 23 24 04 e6  	sw	zero, -0x198(s0)
 4bc6514: 93 09 05 00  	mv	s3, a0
 4bc6518: 63 06 09 22  	beqz	s2, 0x4bc6744 <.section_task_rm_elf_text_instance+0x63e744>
 4bc651c: 83 37 89 12  	ld	a5, 0x128(s2)
 4bc6520: 13 85 04 00  	mv	a0, s1
 4bc6524: 13 06 84 e6  	addi	a2, s0, -0x198
 4bc6528: 93 05 09 00  	mv	a1, s2
 4bc652c: e7 80 07 00  	jalr	a5
 4bc6530: 9b 04 05 00  	sext.w	s1, a0
 4bc6534: e3 98 04 00  	bnez	s1, 0x4bc6d44 <.section_task_rm_elf_text_instance+0x63ed44>
 4bc6538: 83 27 84 e6  	lw	a5, -0x198(s0)
 4bc653c: b7 1a 00 00  	lui	s5, 0x1
 4bc6540: 83 34 84 e4  	ld	s1, -0x1b8(s0)
 4bc6544: b3 8a 59 01  	add	s5, s3, s5
 4bc6548: 23 a0 fd 00  	sw	a5, 0x0(s11)
 4bc654c: 23 a2 fd 20  	sw	a5, 0x204(s11)
 4bc6550: 83 b7 8a 9a  	ld	a5, -0x658(s5)
 4bc6554: 93 85 09 00  	mv	a1, s3
 4bc6558: 13 85 04 00  	mv	a0, s1
 4bc655c: e7 80 07 00  	jalr	a5
 4bc6560: 23 a2 ad 54  	sw	a0, 0x544(s11)
 4bc6564: 83 b7 8a 9c  	ld	a5, -0x638(s5)
 4bc6568: 93 85 09 00  	mv	a1, s3
 4bc656c: 13 85 04 00  	mv	a0, s1
 4bc6570: e7 80 07 00  	jalr	a5
 4bc6574: 03 2a 84 e6  	lw	s4, -0x198(s0)
 4bc6578: 23 a4 ad 54  	sw	a0, 0x548(s11)
 4bc657c: 23 2c 04 e4  	sw	zero, -0x1a8(s0)
 4bc6580: 63 0c 0a 08  	beqz	s4, 0x4bc6618 <.section_task_rm_elf_text_instance+0x63e618>
 4bc6584: 13 06 00 00  	li	a2, 0x0
 4bc6588: 6f 00 40 01  	j	0x4bc659c <.section_task_rm_elf_text_instance+0x63e59c>
 4bc658c: 1b 06 16 00  	addiw	a2, a2, 0x1
 4bc6590: 23 2c c4 e4  	sw	a2, -0x1a8(s0)
 4bc6594: 1b 5a 1a 00  	srliw	s4, s4, 0x1
 4bc6598: 63 0e 0a 06  	beqz	s4, 0x4bc6614 <.section_task_rm_elf_text_instance+0x63e614>
 4bc659c: 93 77 1a 00  	andi	a5, s4, 0x1
 4bc65a0: e3 86 07 fe  	beqz	a5, 0x4bc658c <.section_task_rm_elf_text_instance+0x63e58c>
 4bc65a4: 93 17 06 02  	slli	a5, a2, 0x20
 4bc65a8: 93 d6 e7 01  	srli	a3, a5, 0x1e
 4bc65ac: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc65b0: 83 37 09 13  	ld	a5, 0x130(s2)
 4bc65b4: 93 86 46 00  	addi	a3, a3, 0x4
 4bc65b8: b3 86 dd 00  	add	a3, s11, a3
 4bc65bc: 93 05 09 00  	mv	a1, s2
 4bc65c0: e7 80 07 00  	jalr	a5
 4bc65c4: 9b 04 05 00  	sext.w	s1, a0
 4bc65c8: 63 92 04 18  	bnez	s1, 0x4bc674c <.section_task_rm_elf_text_instance+0x63e74c>
 4bc65cc: 83 c7 4a 1c  	lbu	a5, 0x1c4(s5)
 4bc65d0: 03 26 84 e5  	lw	a2, -0x1a8(s0)
 4bc65d4: e3 8c 07 fa  	beqz	a5, 0x4bc658c <.section_task_rm_elf_text_instance+0x63e58c>
 4bc65d8: 93 17 06 02  	slli	a5, a2, 0x20
 4bc65dc: 93 d6 e7 01  	srli	a3, a5, 0x1e
 4bc65e0: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc65e4: 93 86 46 44  	addi	a3, a3, 0x444
 4bc65e8: b3 86 dd 00  	add	a3, s11, a3
 4bc65ec: 93 05 09 00  	mv	a1, s2
 4bc65f0: 97 f0 0b 00  	auipc	ra, 0xbf
 4bc65f4: e7 80 40 5a  	jalr	0x5a4(ra) <.section_task_rm_elf_text_instance+0x6fdb94>
 4bc65f8: 9b 04 05 00  	sext.w	s1, a0
 4bc65fc: 63 98 04 6e  	bnez	s1, 0x4bc6cec <.section_task_rm_elf_text_instance+0x63ecec>
 4bc6600: 03 26 84 e5  	lw	a2, -0x1a8(s0)
 4bc6604: 1b 5a 1a 00  	srliw	s4, s4, 0x1
 4bc6608: 1b 06 16 00  	addiw	a2, a2, 0x1
 4bc660c: 23 2c c4 e4  	sw	a2, -0x1a8(s0)
 4bc6610: e3 16 0a f8  	bnez	s4, 0x4bc659c <.section_task_rm_elf_text_instance+0x63e59c>
 4bc6614: 03 2a 84 e6  	lw	s4, -0x198(s0)
 4bc6618: b7 17 00 00  	lui	a5, 0x1
 4bc661c: b3 87 f9 00  	add	a5, s3, a5
 4bc6620: 83 c7 47 1c  	lbu	a5, 0x1c4(a5)
 4bc6624: 63 9e 07 00  	bnez	a5, 0x4bc6640 <.section_task_rm_elf_text_instance+0x63e640>
 4bc6628: 93 87 4d 44  	addi	a5, s11, 0x444
 4bc662c: 93 86 4d 54  	addi	a3, s11, 0x544
 4bc6630: 13 07 f0 ff  	li	a4, -0x1
 4bc6634: 23 a0 e7 00  	sw	a4, 0x0(a5)
 4bc6638: 93 87 47 00  	addi	a5, a5, 0x4
 4bc663c: e3 9c d7 fe  	bne	a5, a3, 0x4bc6634 <.section_task_rm_elf_text_instance+0x63e634>
 4bc6640: 37 57 55 55  	lui	a4, 0x55555
 4bc6644: 13 07 57 55  	addi	a4, a4, 0x555
 4bc6648: 9b 57 1a 00  	srliw	a5, s4, 0x1
 4bc664c: b3 f7 e7 00  	and	a5, a5, a4
 4bc6650: bb 07 fa 40  	subw	a5, s4, a5
 4bc6654: 37 37 33 33  	lui	a4, 0x33333
 4bc6658: 13 07 37 33  	addi	a4, a4, 0x333
 4bc665c: 9b d6 27 00  	srliw	a3, a5, 0x2
 4bc6660: b3 77 f7 00  	and	a5, a4, a5
 4bc6664: 33 77 d7 00  	and	a4, a4, a3
 4bc6668: bb 87 e7 00  	addw	a5, a5, a4
 4bc666c: 9b da 47 00  	srliw	s5, a5, 0x4
 4bc6670: bb 8a fa 00  	addw	s5, s5, a5
 4bc6674: b7 17 0f 0f  	lui	a5, 0xf0f1
 4bc6678: 93 87 f7 f0  	addi	a5, a5, -0xf1
 4bc667c: b3 fa fa 00  	and	s5, s5, a5
 4bc6680: b7 07 01 01  	lui	a5, 0x1010
 4bc6684: 9b 87 17 10  	addiw	a5, a5, 0x101
 4bc6688: bb 8a fa 02  	<unknown>
 4bc668c: 93 07 00 04  	li	a5, 0x40
 4bc6690: 1b d7 8a 01  	srliw	a4, s5, 0x18
 4bc6694: 23 2e e4 e4  	sw	a4, -0x1a4(s0)
 4bc6698: 9b da 8a 01  	srliw	s5, s5, 0x18
 4bc669c: 63 e8 57 73  	bltu	a5, s5, 0x4bc6dcc <.section_task_rm_elf_text_instance+0x63edcc>
 4bc66a0: 63 82 0a 06  	beqz	s5, 0x4bc6704 <.section_task_rm_elf_text_instance+0x63e704>
 4bc66a4: 13 8a 4d 10  	addi	s4, s11, 0x104
 4bc66a8: 13 09 00 00  	li	s2, 0x0
 4bc66ac: 83 34 84 e4  	ld	s1, -0x1b8(s0)
 4bc66b0: 13 06 09 00  	mv	a2, s2
 4bc66b4: 93 85 09 00  	mv	a1, s3
 4bc66b8: 13 85 04 00  	mv	a0, s1
 4bc66bc: 97 40 01 00  	auipc	ra, 0x14
 4bc66c0: e7 80 c0 b3  	jalr	-0x4c4(ra) <.section_task_rm_elf_text_instance+0x6521f8>
 4bc66c4: 13 06 09 00  	mv	a2, s2
 4bc66c8: 23 20 aa 00  	sw	a0, 0x0(s4)
 4bc66cc: 93 85 09 00  	mv	a1, s3
 4bc66d0: 13 85 04 00  	mv	a0, s1
 4bc66d4: 97 40 01 00  	auipc	ra, 0x14
 4bc66d8: e7 80 00 56  	jalr	0x560(ra) <.section_task_rm_elf_text_instance+0x652c34>
 4bc66dc: 23 20 aa 24  	sw	a0, 0x240(s4)
 4bc66e0: 13 06 09 00  	mv	a2, s2
 4bc66e4: 93 85 09 00  	mv	a1, s3
 4bc66e8: 13 85 04 00  	mv	a0, s1
 4bc66ec: 97 30 03 00  	auipc	ra, 0x33
 4bc66f0: e7 80 c0 86  	jalr	-0x794(ra) <.section_task_rm_elf_text_instance+0x670f58>
 4bc66f4: 23 22 aa 10  	sw	a0, 0x104(s4)
 4bc66f8: 1b 09 19 00  	addiw	s2, s2, 0x1
 4bc66fc: 13 0a 4a 00  	addi	s4, s4, 0x4
 4bc6700: e3 16 59 fb  	bne	s2, s5, 0x4bc66ac <.section_task_rm_elf_text_instance+0x63e6ac>
 4bc6704: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc6708: 93 86 8d 30  	addi	a3, s11, 0x308
 4bc670c: 13 06 44 e5  	addi	a2, s0, -0x1ac
 4bc6710: 93 85 09 00  	mv	a1, s3
 4bc6714: 97 40 01 00  	auipc	ra, 0x14
 4bc6718: e7 80 c0 5f  	jalr	0x5fc(ra) <.section_task_rm_elf_text_instance+0x652d10>
 4bc671c: 9b 04 05 00  	sext.w	s1, a0
 4bc6720: e3 8c 04 dc  	beqz	s1, 0x4bc64f8 <.section_task_rm_elf_text_instance+0x63e4f8>
 4bc6724: 93 95 04 02  	slli	a1, s1, 0x20
 4bc6728: 37 46 9a 05  	lui	a2, 0x59a4
 4bc672c: 13 06 86 fc  	addi	a2, a2, -0x38
 4bc6730: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc6734: 13 05 20 00  	li	a0, 0x2
 4bc6738: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc673c: e7 80 40 63  	jalr	0x634(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6740: 6f 00 80 02  	j	0x4bc6768 <.section_task_rm_elf_text_instance+0x63e768>
 4bc6744: 93 07 00 00  	li	a5, 0x0
 4bc6748: 6f f0 5f df  	j	0x4bc653c <.section_task_rm_elf_text_instance+0x63e53c>
 4bc674c: 37 46 9a 05  	lui	a2, 0x59a4
 4bc6750: 93 95 04 02  	slli	a1, s1, 0x20
 4bc6754: 13 06 06 01  	addi	a2, a2, 0x10
 4bc6758: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc675c: 13 05 20 00  	li	a0, 0x2
 4bc6760: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6764: e7 80 c0 60  	jalr	0x60c(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6768: b7 37 20 04  	lui	a5, 0x4203
 4bc676c: 03 37 84 f8  	ld	a4, -0x78(s0)
 4bc6770: 83 b7 07 93  	ld	a5, -0x6d0(a5)
 4bc6774: b3 47 f7 00  	xor	a5, a4, a5
 4bc6778: 13 07 00 00  	li	a4, 0x0
 4bc677c: 63 96 07 6e  	bnez	a5, 0x4bc6e68 <.section_task_rm_elf_text_instance+0x63ee68>
 4bc6780: 83 30 81 1f  	ld	ra, 0x1f8(sp)
 4bc6784: 03 34 01 1f  	ld	s0, 0x1f0(sp)
 4bc6788: 03 39 01 1e  	ld	s2, 0x1e0(sp)
 4bc678c: 83 39 81 1d  	ld	s3, 0x1d8(sp)
 4bc6790: 03 3a 01 1d  	ld	s4, 0x1d0(sp)
 4bc6794: 83 3a 81 1c  	ld	s5, 0x1c8(sp)
 4bc6798: 03 3b 01 1c  	ld	s6, 0x1c0(sp)
 4bc679c: 83 3b 81 1b  	ld	s7, 0x1b8(sp)
 4bc67a0: 03 3c 01 1b  	ld	s8, 0x1b0(sp)
 4bc67a4: 83 3c 81 1a  	ld	s9, 0x1a8(sp)
 4bc67a8: 03 3d 01 1a  	ld	s10, 0x1a0(sp)
 4bc67ac: 83 3d 81 19  	ld	s11, 0x198(sp)
 4bc67b0: 13 85 04 00  	mv	a0, s1
 4bc67b4: 83 34 81 1e  	ld	s1, 0x1e8(sp)
 4bc67b8: 13 01 01 20  	addi	sp, sp, 0x200
 4bc67bc: 67 80 00 00  	ret
 4bc67c0: 9b 86 fb ff  	addiw	a3, s7, -0x1
 4bc67c4: 93 07 70 00  	li	a5, 0x7
 4bc67c8: 63 e4 d7 2c  	bltu	a5, a3, 0x4bc6a90 <.section_task_rm_elf_text_instance+0x63ea90>
 4bc67cc: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc67d0: 13 07 04 e6  	addi	a4, s0, -0x1a0
 4bc67d4: 13 06 00 00  	li	a2, 0x0
 4bc67d8: 93 05 09 00  	mv	a1, s2
 4bc67dc: 97 d0 0c 00  	auipc	ra, 0xcd
 4bc67e0: e7 80 00 fb  	jalr	-0x50(ra) <.section_task_rm_elf_text_instance+0x70b78c>
 4bc67e4: 9b 04 05 00  	sext.w	s1, a0
 4bc67e8: 63 90 04 4a  	bnez	s1, 0x4bc6c88 <.section_task_rm_elf_text_instance+0x63ec88>
 4bc67ec: 83 34 84 e4  	ld	s1, -0x1b8(s0)
 4bc67f0: 93 9c 0a 02  	slli	s9, s5, 0x20
 4bc67f4: 93 dc 0c 02  	srli	s9, s9, 0x20
 4bc67f8: 13 85 04 00  	mv	a0, s1
 4bc67fc: 97 b0 fa ff  	auipc	ra, 0xfffab
 4bc6800: e7 80 00 46  	jalr	0x460(ra)
 4bc6804: 93 07 c0 54  	li	a5, 0x54c
 4bc6808: b3 87 fc 02  	<unknown>
 4bc680c: 03 36 84 e3  	ld	a2, -0x1c8(s0)
 4bc6810: b7 1d 00 00  	lui	s11, 0x1
 4bc6814: b3 0d b5 01  	add	s11, a0, s11
 4bc6818: 23 30 a4 e4  	sd	a0, -0x1c0(s0)
 4bc681c: 13 07 c4 e5  	addi	a4, s0, -0x1a4
 4bc6820: 93 06 84 e8  	addi	a3, s0, -0x178
 4bc6824: 93 05 09 00  	mv	a1, s2
 4bc6828: 13 85 04 00  	mv	a0, s1
 4bc682c: b3 09 f6 00  	add	s3, a2, a5
 4bc6830: 23 a0 09 00  	sw	zero, 0x0(s3)
 4bc6834: 23 a2 09 20  	sw	zero, 0x204(s3)
 4bc6838: 03 a6 8d 1b  	lw	a2, 0x1b8(s11)
 4bc683c: 23 30 f4 e2  	sd	a5, -0x1e0(s0)
 4bc6840: 97 e0 0b 00  	auipc	ra, 0xbe
 4bc6844: e7 80 40 60  	jalr	0x604(ra) <.section_task_rm_elf_text_instance+0x6fce44>
 4bc6848: 1b 0d 05 00  	sext.w	s10, a0
 4bc684c: 63 18 0d 3e  	bnez	s10, 0x4bc6c3c <.section_task_rm_elf_text_instance+0x63ec3c>
 4bc6850: 03 2b c4 e5  	lw	s6, -0x1a4(s0)
 4bc6854: 63 0e 0b 10  	beqz	s6, 0x4bc6970 <.section_task_rm_elf_text_instance+0x63e970>
 4bc6858: 03 3a 04 e4  	ld	s4, -0x1c0(s0)
 4bc685c: 83 34 84 e4  	ld	s1, -0x1b8(s0)
 4bc6860: 83 b7 8d 9a  	ld	a5, -0x658(s11)
 4bc6864: 93 05 0a 00  	mv	a1, s4
 4bc6868: 13 85 04 00  	mv	a0, s1
 4bc686c: e7 80 07 00  	jalr	a5
 4bc6870: 23 a2 a9 54  	sw	a0, 0x544(s3)
 4bc6874: 83 b7 8d 9c  	ld	a5, -0x638(s11)
 4bc6878: 93 05 0a 00  	mv	a1, s4
 4bc687c: 13 85 04 00  	mv	a0, s1
 4bc6880: e7 80 07 00  	jalr	a5
 4bc6884: 93 07 30 15  	li	a5, 0x153
 4bc6888: b3 87 fc 02  	<unknown>
 4bc688c: 23 a4 a9 54  	sw	a0, 0x548(s3)
 4bc6890: 13 0c 84 e8  	addi	s8, s0, -0x178
 4bc6894: 13 8a 09 00  	mv	s4, s3
 4bc6898: 93 04 10 00  	li	s1, 0x1
 4bc689c: 23 38 74 e1  	sd	s7, -0x1f0(s0)
 4bc68a0: 23 34 f4 e2  	sd	a5, -0x1d8(s0)
 4bc68a4: 83 a7 09 00  	lw	a5, 0x0(s3)
 4bc68a8: 3b 97 a4 01  	sllw	a4, s1, s10
 4bc68ac: 03 26 0c 00  	lw	a2, 0x0(s8)
 4bc68b0: b3 e7 e7 00  	or	a5, a5, a4
 4bc68b4: 23 a0 f9 00  	sw	a5, 0x0(s3)
 4bc68b8: 83 37 09 20  	ld	a5, 0x200(s2)
 4bc68bc: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc68c0: 93 06 84 e5  	addi	a3, s0, -0x1a8
 4bc68c4: 93 05 09 00  	mv	a1, s2
 4bc68c8: e7 80 07 00  	jalr	a5
 4bc68cc: 9b 07 05 00  	sext.w	a5, a0
 4bc68d0: 63 9a 07 2a  	bnez	a5, 0x4bc6b84 <.section_task_rm_elf_text_instance+0x63eb84>
 4bc68d4: 03 26 84 e5  	lw	a2, -0x1a8(s0)
 4bc68d8: 83 a7 49 20  	lw	a5, 0x204(s3)
 4bc68dc: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc68e0: 3b 97 c4 00  	sllw	a4, s1, a2
 4bc68e4: b3 e7 e7 00  	or	a5, a5, a4
 4bc68e8: 23 a2 f9 20  	sw	a5, 0x204(s3)
 4bc68ec: 83 37 09 13  	ld	a5, 0x130(s2)
 4bc68f0: 93 0b 4a 00  	addi	s7, s4, 0x4
 4bc68f4: 93 86 0b 00  	mv	a3, s7
 4bc68f8: 93 05 09 00  	mv	a1, s2
 4bc68fc: e7 80 07 00  	jalr	a5
 4bc6900: 9b 07 05 00  	sext.w	a5, a0
 4bc6904: 63 94 07 2e  	bnez	a5, 0x4bc6bec <.section_task_rm_elf_text_instance+0x63ebec>
 4bc6908: 83 35 04 e4  	ld	a1, -0x1c0(s0)
 4bc690c: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc6910: 13 06 0d 00  	mv	a2, s10
 4bc6914: 97 40 01 00  	auipc	ra, 0x14
 4bc6918: e7 80 40 8e  	jalr	-0x71c(ra) <.section_task_rm_elf_text_instance+0x6521f8>
 4bc691c: 83 35 04 e4  	ld	a1, -0x1c0(s0)
 4bc6920: 23 22 aa 10  	sw	a0, 0x104(s4)
 4bc6924: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc6928: 13 06 0d 00  	mv	a2, s10
 4bc692c: 97 40 01 00  	auipc	ra, 0x14
 4bc6930: e7 80 80 30  	jalr	0x308(ra) <.section_task_rm_elf_text_instance+0x652c34>
 4bc6934: 23 22 aa 34  	sw	a0, 0x344(s4)
 4bc6938: 83 35 04 e4  	ld	a1, -0x1c0(s0)
 4bc693c: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc6940: 13 06 0d 00  	mv	a2, s10
 4bc6944: 97 20 03 00  	auipc	ra, 0x32
 4bc6948: e7 80 40 61  	jalr	0x614(ra) <.section_task_rm_elf_text_instance+0x670f58>
 4bc694c: 23 24 aa 20  	sw	a0, 0x208(s4)
 4bc6950: 83 c7 4d 1c  	lbu	a5, 0x1c4(s11)
 4bc6954: 63 94 07 16  	bnez	a5, 0x4bc6abc <.section_task_rm_elf_text_instance+0x63eabc>
 4bc6958: 1b 0d 1d 00  	addiw	s10, s10, 0x1
 4bc695c: 13 0c 4c 00  	addi	s8, s8, 0x4
 4bc6960: 63 06 ab 01  	beq	s6, s10, 0x4bc696c <.section_task_rm_elf_text_instance+0x63e96c>
 4bc6964: 13 8a 0b 00  	mv	s4, s7
 4bc6968: 6f f0 df f3  	j	0x4bc68a4 <.section_task_rm_elf_text_instance+0x63e8a4>
 4bc696c: 83 3b 04 e1  	ld	s7, -0x1f0(s0)
 4bc6970: 03 37 04 e4  	ld	a4, -0x1c0(s0)
 4bc6974: b7 17 00 00  	lui	a5, 0x1
 4bc6978: b3 07 f7 00  	add	a5, a4, a5
 4bc697c: 83 c7 47 1c  	lbu	a5, 0x1c4(a5)
 4bc6980: 63 88 07 28  	beqz	a5, 0x4bc6c10 <.section_task_rm_elf_text_instance+0x63ec10>
 4bc6984: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc6988: 93 05 44 e6  	addi	a1, s0, -0x19c
 4bc698c: 97 40 a5 ff  	auipc	ra, 0xffa54
 4bc6990: e7 80 40 d1  	jalr	-0x2ec(ra)
 4bc6994: 1b 0a 05 00  	sext.w	s4, a0
 4bc6998: 63 16 0a 3e  	bnez	s4, 0x4bc6d84 <.section_task_rm_elf_text_instance+0x63ed84>
 4bc699c: 83 27 44 e6  	lw	a5, -0x19c(s0)
 4bc69a0: 63 8c 07 08  	beqz	a5, 0x4bc6a38 <.section_task_rm_elf_text_instance+0x63ea38>
 4bc69a4: 93 06 c0 54  	li	a3, 0x54c
 4bc69a8: b3 86 dc 02  	<unknown>
 4bc69ac: 83 37 84 e3  	ld	a5, -0x1c8(s0)
 4bc69b0: b7 55 55 55  	lui	a1, 0x55555
 4bc69b4: 93 85 55 55  	addi	a1, a1, 0x555
 4bc69b8: 37 37 33 33  	lui	a4, 0x33333
 4bc69bc: 13 07 37 33  	addi	a4, a4, 0x333
 4bc69c0: b3 86 d7 00  	add	a3, a5, a3
 4bc69c4: 83 a7 46 54  	lw	a5, 0x544(a3)
 4bc69c8: 1b d6 17 00  	srliw	a2, a5, 0x1
 4bc69cc: 33 76 b6 00  	and	a2, a2, a1
 4bc69d0: bb 87 c7 40  	subw	a5, a5, a2
 4bc69d4: 1b d6 27 00  	srliw	a2, a5, 0x2
 4bc69d8: b3 77 f7 00  	and	a5, a4, a5
 4bc69dc: 33 77 c7 00  	and	a4, a4, a2
 4bc69e0: 3b 87 e7 00  	addw	a4, a5, a4
 4bc69e4: 9b 57 47 00  	srliw	a5, a4, 0x4
 4bc69e8: bb 87 e7 00  	addw	a5, a5, a4
 4bc69ec: 37 17 0f 0f  	lui	a4, 0xf0f1
 4bc69f0: 13 07 f7 f0  	addi	a4, a4, -0xf1
 4bc69f4: b3 f7 e7 00  	and	a5, a5, a4
 4bc69f8: 37 07 01 01  	lui	a4, 0x1010
 4bc69fc: 1b 07 17 10  	addiw	a4, a4, 0x101
 4bc6a00: bb 87 e7 02  	<unknown>
 4bc6a04: 1b d7 87 01  	srliw	a4, a5, 0x18
 4bc6a08: 9b d7 87 01  	srliw	a5, a5, 0x18
 4bc6a0c: 63 0a 07 00  	beqz	a4, 0x4bc6a20 <.section_task_rm_elf_text_instance+0x63ea20>
 4bc6a10: bb 07 f0 40  	negw	a5, a5
 4bc6a14: 13 07 f0 ff  	li	a4, -0x1
 4bc6a18: bb 57 f7 00  	srlw	a5, a4, a5
 4bc6a1c: 23 a2 f6 54  	sw	a5, 0x544(a3)
 4bc6a20: 93 07 c0 54  	li	a5, 0x54c
 4bc6a24: b3 87 fc 02  	<unknown>
 4bc6a28: 83 36 84 e3  	ld	a3, -0x1c8(s0)
 4bc6a2c: 03 a7 09 00  	lw	a4, 0x0(s3)
 4bc6a30: b3 87 f6 00  	add	a5, a3, a5
 4bc6a34: 23 a2 e7 20  	sw	a4, 0x204(a5)
 4bc6a38: 83 37 04 e2  	ld	a5, -0x1e0(s0)
 4bc6a3c: 83 35 04 e4  	ld	a1, -0x1c0(s0)
 4bc6a40: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc6a44: 93 86 87 30  	addi	a3, a5, 0x308
 4bc6a48: 83 37 84 e3  	ld	a5, -0x1c8(s0)
 4bc6a4c: 13 06 44 e5  	addi	a2, s0, -0x1ac
 4bc6a50: b3 86 d7 00  	add	a3, a5, a3
 4bc6a54: 97 40 01 00  	auipc	ra, 0x14
 4bc6a58: e7 80 c0 2b  	jalr	0x2bc(ra) <.section_task_rm_elf_text_instance+0x652d10>
 4bc6a5c: 9b 07 05 00  	sext.w	a5, a0
 4bc6a60: 63 96 07 3a  	bnez	a5, 0x4bc6e0c <.section_task_rm_elf_text_instance+0x63ee0c>
 4bc6a64: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc6a68: 93 06 04 e6  	addi	a3, s0, -0x1a0
 4bc6a6c: 13 06 00 00  	li	a2, 0x0
 4bc6a70: 93 05 09 00  	mv	a1, s2
 4bc6a74: 23 30 f4 e4  	sd	a5, -0x1c0(s0)
 4bc6a78: 97 d0 0c 00  	auipc	ra, 0xcd
 4bc6a7c: e7 80 00 4a  	jalr	0x4a0(ra) <.section_task_rm_elf_text_instance+0x70bf18>
 4bc6a80: 1b 07 05 00  	sext.w	a4, a0
 4bc6a84: 83 37 04 e4  	ld	a5, -0x1c0(s0)
 4bc6a88: 63 14 07 3e  	bnez	a4, 0x4bc6e70 <.section_task_rm_elf_text_instance+0x63ee70>
 4bc6a8c: 9b 8a 1a 00  	addiw	s5, s5, 0x1
 4bc6a90: 13 86 0b 00  	mv	a2, s7
 4bc6a94: 93 05 40 05  	li	a1, 0x54
 4bc6a98: 13 05 84 e7  	addi	a0, s0, -0x188
 4bc6a9c: 97 c0 6a 00  	auipc	ra, 0x6ac
 4bc6aa0: e7 80 00 64  	jalr	0x640(ra) <.section_task_rm_elf_text_instance+0xceb0dc>
 4bc6aa4: 93 05 40 05  	li	a1, 0x54
 4bc6aa8: 13 05 84 e7  	addi	a0, s0, -0x188
 4bc6aac: 97 d0 6a 00  	auipc	ra, 0x6ad
 4bc6ab0: e7 80 c0 f0  	jalr	-0xf4(ra) <.section_task_rm_elf_text_instance+0xceb9b8>
 4bc6ab4: 9b 0b 05 00  	sext.w	s7, a0
 4bc6ab8: 6f f0 9f a2  	j	0x4bc64e0 <.section_task_rm_elf_text_instance+0x63e4e0>
 4bc6abc: 03 26 84 e5  	lw	a2, -0x1a8(s0)
 4bc6ac0: 83 37 84 e2  	ld	a5, -0x1d8(s0)
 4bc6ac4: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc6ac8: 93 16 06 02  	slli	a3, a2, 0x20
 4bc6acc: 93 d6 06 02  	srli	a3, a3, 0x20
 4bc6ad0: 93 86 16 11  	addi	a3, a3, 0x111
 4bc6ad4: b3 86 f6 00  	add	a3, a3, a5
 4bc6ad8: 83 37 84 e3  	ld	a5, -0x1c8(s0)
 4bc6adc: 93 96 26 00  	slli	a3, a3, 0x2
 4bc6ae0: 93 05 09 00  	mv	a1, s2
 4bc6ae4: b3 86 d7 00  	add	a3, a5, a3
 4bc6ae8: 97 f0 0b 00  	auipc	ra, 0xbf
 4bc6aec: e7 80 c0 0a  	jalr	0xac(ra) <.section_task_rm_elf_text_instance+0x6fdb94>
 4bc6af0: 9b 07 05 00  	sext.w	a5, a0
 4bc6af4: e3 82 07 e6  	beqz	a5, 0x4bc6958 <.section_task_rm_elf_text_instance+0x63e958>
 4bc6af8: 37 46 9a 05  	lui	a2, 0x59a4
 4bc6afc: 93 95 07 02  	slli	a1, a5, 0x20
 4bc6b00: 13 06 86 08  	addi	a2, a2, 0x88
 4bc6b04: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc6b08: 13 05 20 00  	li	a0, 0x2
 4bc6b0c: 13 8d 07 00  	mv	s10, a5
 4bc6b10: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6b14: e7 80 c0 25  	jalr	0x25c(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6b18: 03 35 84 e4  	ld	a0, -0x1b8(s0)
 4bc6b1c: 93 06 04 e6  	addi	a3, s0, -0x1a0
 4bc6b20: 13 06 00 00  	li	a2, 0x0
 4bc6b24: 93 05 09 00  	mv	a1, s2
 4bc6b28: 97 d0 0c 00  	auipc	ra, 0xcd
 4bc6b2c: e7 80 00 3f  	jalr	0x3f0(ra) <.section_task_rm_elf_text_instance+0x70bf18>
 4bc6b30: 9b 04 05 00  	sext.w	s1, a0
 4bc6b34: 63 84 04 04  	beqz	s1, 0x4bc6b7c <.section_task_rm_elf_text_instance+0x63eb7c>
 4bc6b38: 93 95 04 02  	slli	a1, s1, 0x20
 4bc6b3c: 37 46 9a 05  	lui	a2, 0x59a4
 4bc6b40: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc6b44: 13 05 20 00  	li	a0, 0x2
 4bc6b48: 13 06 06 04  	addi	a2, a2, 0x40
 4bc6b4c: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6b50: e7 80 00 22  	jalr	0x220(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6b54: 03 36 84 e1  	ld	a2, -0x1e8(s0)
 4bc6b58: 93 05 00 00  	li	a1, 0x0
 4bc6b5c: 13 85 04 00  	mv	a0, s1
 4bc6b60: 97 f0 9d ff  	auipc	ra, 0xff9df
 4bc6b64: e7 80 40 3e  	jalr	0x3e4(ra)
 4bc6b68: 37 77 39 04  	lui	a4, 0x4397
 4bc6b6c: 03 47 07 8d  	lbu	a4, -0x730(a4)
 4bc6b70: 63 1c 07 1a  	bnez	a4, 0x4bc6d28 <.section_task_rm_elf_text_instance+0x63ed28>
 4bc6b74: 73 00 10 00  	ebreak
 4bc6b78: e3 08 0d be  	beqz	s10, 0x4bc6768 <.section_task_rm_elf_text_instance+0x63e768>
 4bc6b7c: 93 04 0d 00  	mv	s1, s10
 4bc6b80: 6f f0 9f be  	j	0x4bc6768 <.section_task_rm_elf_text_instance+0x63e768>
 4bc6b84: 93 95 07 02  	slli	a1, a5, 0x20
 4bc6b88: 37 46 9a 05  	lui	a2, 0x59a4
 4bc6b8c: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc6b90: 13 05 20 00  	li	a0, 0x2
 4bc6b94: 13 06 86 0b  	addi	a2, a2, 0xb8
 4bc6b98: 13 8d 07 00  	mv	s10, a5
 4bc6b9c: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6ba0: e7 80 00 1d  	jalr	0x1d0(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6ba4: 03 36 84 e1  	ld	a2, -0x1e8(s0)
 4bc6ba8: 93 05 00 00  	li	a1, 0x0
 4bc6bac: 13 05 0d 00  	mv	a0, s10
 4bc6bb0: 97 f0 9d ff  	auipc	ra, 0xff9df
 4bc6bb4: e7 80 40 39  	jalr	0x394(ra)
 4bc6bb8: 37 77 39 04  	lui	a4, 0x4397
 4bc6bbc: 03 47 07 8d  	lbu	a4, -0x730(a4)
 4bc6bc0: 63 16 07 00  	bnez	a4, 0x4bc6bcc <.section_task_rm_elf_text_instance+0x63ebcc>
 4bc6bc4: 73 00 10 00  	ebreak
 4bc6bc8: 6f f0 1f f5  	j	0x4bc6b18 <.section_task_rm_elf_text_instance+0x63eb18>
 4bc6bcc: 37 87 39 04  	lui	a4, 0x4398
 4bc6bd0: 03 37 87 c5  	ld	a4, -0x3a8(a4)
 4bc6bd4: b7 16 11 00  	lui	a3, 0x111
 4bc6bd8: 93 86 06 30  	addi	a3, a3, 0x300
 4bc6bdc: 33 07 d7 00  	add	a4, a4, a3
 4bc6be0: 23 20 07 00  	sw	zero, 0x0(a4)
 4bc6be4: 73 00 10 00  	ebreak
 4bc6be8: 6f f0 1f f3  	j	0x4bc6b18 <.section_task_rm_elf_text_instance+0x63eb18>
 4bc6bec: 93 95 07 02  	slli	a1, a5, 0x20
 4bc6bf0: 37 46 9a 05  	lui	a2, 0x59a4
 4bc6bf4: 13 06 06 0a  	addi	a2, a2, 0xa0
 4bc6bf8: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc6bfc: 13 05 20 00  	li	a0, 0x2
 4bc6c00: 13 8d 07 00  	mv	s10, a5
 4bc6c04: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6c08: e7 80 80 16  	jalr	0x168(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6c0c: 6f f0 df f0  	j	0x4bc6b18 <.section_task_rm_elf_text_instance+0x63eb18>
 4bc6c10: 03 37 04 e2  	ld	a4, -0x1e0(s0)
 4bc6c14: 83 36 84 e3  	ld	a3, -0x1c8(s0)
 4bc6c18: 93 07 47 44  	addi	a5, a4, 0x444
 4bc6c1c: b3 87 f6 00  	add	a5, a3, a5
 4bc6c20: 83 36 84 e0  	ld	a3, -0x1f8(s0)
 4bc6c24: b3 86 e6 00  	add	a3, a3, a4
 4bc6c28: 13 07 f0 ff  	li	a4, -0x1
 4bc6c2c: 23 a0 e7 00  	sw	a4, 0x0(a5)
 4bc6c30: 93 87 47 00  	addi	a5, a5, 0x4
 4bc6c34: e3 9c f6 fe  	bne	a3, a5, 0x4bc6c2c <.section_task_rm_elf_text_instance+0x63ec2c>
 4bc6c38: 6f f0 df d4  	j	0x4bc6984 <.section_task_rm_elf_text_instance+0x63e984>
 4bc6c3c: 93 15 0d 02  	slli	a1, s10, 0x20
 4bc6c40: 37 46 9a 05  	lui	a2, 0x59a4
 4bc6c44: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc6c48: 13 05 20 00  	li	a0, 0x2
 4bc6c4c: 13 06 06 0d  	addi	a2, a2, 0xd0
 4bc6c50: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6c54: e7 80 c0 11  	jalr	0x11c(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6c58: 03 36 84 e1  	ld	a2, -0x1e8(s0)
 4bc6c5c: 93 05 00 00  	li	a1, 0x0
 4bc6c60: 13 05 0d 00  	mv	a0, s10
 4bc6c64: 97 f0 9d ff  	auipc	ra, 0xff9df
 4bc6c68: e7 80 00 2e  	jalr	0x2e0(ra)
 4bc6c6c: b7 77 39 04  	lui	a5, 0x4397
 4bc6c70: 83 c7 07 8d  	lbu	a5, -0x730(a5)
 4bc6c74: 93 0a 0d 00  	mv	s5, s10
 4bc6c78: 63 9a 07 08  	bnez	a5, 0x4bc6d0c <.section_task_rm_elf_text_instance+0x63ed0c>
 4bc6c7c: 73 00 10 00  	ebreak
 4bc6c80: 13 8d 0a 00  	mv	s10, s5
 4bc6c84: 6f f0 5f e9  	j	0x4bc6b18 <.section_task_rm_elf_text_instance+0x63eb18>
 4bc6c88: b7 47 9a 05  	lui	a5, 0x59a4
 4bc6c8c: 93 95 04 02  	slli	a1, s1, 0x20
 4bc6c90: 13 86 87 0e  	addi	a2, a5, 0xe8
 4bc6c94: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc6c98: 13 05 20 00  	li	a0, 0x2
 4bc6c9c: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6ca0: e7 80 00 0d  	jalr	0xd0(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6ca4: 03 36 84 e1  	ld	a2, -0x1e8(s0)
 4bc6ca8: 93 05 00 00  	li	a1, 0x0
 4bc6cac: 13 85 04 00  	mv	a0, s1
 4bc6cb0: 97 f0 9d ff  	auipc	ra, 0xff9df
 4bc6cb4: e7 80 40 29  	jalr	0x294(ra)
 4bc6cb8: b7 77 39 04  	lui	a5, 0x4397
 4bc6cbc: 83 c7 07 8d  	lbu	a5, -0x730(a5)
 4bc6cc0: 63 96 07 00  	bnez	a5, 0x4bc6ccc <.section_task_rm_elf_text_instance+0x63eccc>
 4bc6cc4: 73 00 10 00  	ebreak
 4bc6cc8: 6f f0 5f b2  	j	0x4bc67ec <.section_task_rm_elf_text_instance+0x63e7ec>
 4bc6ccc: b7 87 39 04  	lui	a5, 0x4398
 4bc6cd0: 83 b7 87 c5  	ld	a5, -0x3a8(a5)
 4bc6cd4: 37 17 11 00  	lui	a4, 0x111
 4bc6cd8: 13 07 07 30  	addi	a4, a4, 0x300
 4bc6cdc: b3 87 e7 00  	add	a5, a5, a4
 4bc6ce0: 23 a0 07 00  	sw	zero, 0x0(a5)
 4bc6ce4: 73 00 10 00  	ebreak
 4bc6ce8: 6f f0 5f b0  	j	0x4bc67ec <.section_task_rm_elf_text_instance+0x63e7ec>
 4bc6cec: 93 95 04 02  	slli	a1, s1, 0x20
 4bc6cf0: 37 46 9a 05  	lui	a2, 0x59a4
 4bc6cf4: 13 06 86 ff  	addi	a2, a2, -0x8
 4bc6cf8: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc6cfc: 13 05 20 00  	li	a0, 0x2
 4bc6d00: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6d04: e7 80 c0 06  	jalr	0x6c(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6d08: 6f f0 1f a6  	j	0x4bc6768 <.section_task_rm_elf_text_instance+0x63e768>
 4bc6d0c: b7 87 39 04  	lui	a5, 0x4398
 4bc6d10: 83 b7 87 c5  	ld	a5, -0x3a8(a5)
 4bc6d14: b7 16 11 00  	lui	a3, 0x111
 4bc6d18: 93 86 06 30  	addi	a3, a3, 0x300
 4bc6d1c: b3 87 d7 00  	add	a5, a5, a3
 4bc6d20: 23 a0 07 00  	sw	zero, 0x0(a5)
 4bc6d24: 6f f0 9f f5  	j	0x4bc6c7c <.section_task_rm_elf_text_instance+0x63ec7c>
 4bc6d28: 37 87 39 04  	lui	a4, 0x4398
 4bc6d2c: 03 37 87 c5  	ld	a4, -0x3a8(a4)
 4bc6d30: b7 16 11 00  	lui	a3, 0x111
 4bc6d34: 93 86 06 30  	addi	a3, a3, 0x300
 4bc6d38: 33 07 d7 00  	add	a4, a4, a3
 4bc6d3c: 23 20 07 00  	sw	zero, 0x0(a4)
 4bc6d40: 6f f0 5f e3  	j	0x4bc6b74 <.section_task_rm_elf_text_instance+0x63eb74>
 4bc6d44: 93 95 04 02  	slli	a1, s1, 0x20
 4bc6d48: 37 46 9a 05  	lui	a2, 0x59a4
 4bc6d4c: 13 06 86 02  	addi	a2, a2, 0x28
 4bc6d50: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc6d54: 13 05 20 00  	li	a0, 0x2
 4bc6d58: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6d5c: e7 80 40 01  	jalr	0x14(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6d60: 6f f0 9f a0  	j	0x4bc6768 <.section_task_rm_elf_text_instance+0x63e768>
 4bc6d64: 93 95 04 02  	slli	a1, s1, 0x20
 4bc6d68: 37 46 9a 05  	lui	a2, 0x59a4
 4bc6d6c: 13 06 06 10  	addi	a2, a2, 0x100
 4bc6d70: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc6d74: 13 05 20 00  	li	a0, 0x2
 4bc6d78: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6d7c: e7 80 40 ff  	jalr	-0xc(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6d80: 6f f0 9f 9e  	j	0x4bc6768 <.section_task_rm_elf_text_instance+0x63e768>
 4bc6d84: 93 15 0a 02  	slli	a1, s4, 0x20
 4bc6d88: 37 46 9a 05  	lui	a2, 0x59a4
 4bc6d8c: 93 d5 05 02  	srli	a1, a1, 0x20
 4bc6d90: 13 05 20 00  	li	a0, 0x2
 4bc6d94: 13 06 06 07  	addi	a2, a2, 0x70
 4bc6d98: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6d9c: e7 80 40 fd  	jalr	-0x2c(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6da0: 03 36 84 e1  	ld	a2, -0x1e8(s0)
 4bc6da4: 93 05 00 00  	li	a1, 0x0
 4bc6da8: 13 05 0a 00  	mv	a0, s4
 4bc6dac: 97 f0 9d ff  	auipc	ra, 0xff9df
 4bc6db0: e7 80 80 19  	jalr	0x198(ra)
 4bc6db4: b7 77 39 04  	lui	a5, 0x4397
 4bc6db8: 83 c7 07 8d  	lbu	a5, -0x730(a5)
 4bc6dbc: 63 9a 07 06  	bnez	a5, 0x4bc6e30 <.section_task_rm_elf_text_instance+0x63ee30>
 4bc6dc0: 73 00 10 00  	ebreak
 4bc6dc4: 93 04 0a 00  	mv	s1, s4
 4bc6dc8: 6f f0 1f 9a  	j	0x4bc6768 <.section_task_rm_elf_text_instance+0x63e768>
 4bc6dcc: b7 45 9a 05  	lui	a1, 0x59a4
 4bc6dd0: 93 85 05 fe  	addi	a1, a1, -0x20
 4bc6dd4: 13 05 10 00  	li	a0, 0x1
 4bc6dd8: 97 90 9f 00  	auipc	ra, 0x9f9
 4bc6ddc: e7 80 40 f9  	jalr	-0x6c(ra) <.section_task_rm_elf_text_instance+0x1037d6c>
 4bc6de0: 03 36 84 e1  	ld	a2, -0x1e8(s0)
 4bc6de4: 93 05 00 00  	li	a1, 0x0
 4bc6de8: 13 05 00 00  	li	a0, 0x0
 4bc6dec: 97 f0 9d ff  	auipc	ra, 0xff9df
 4bc6df0: e7 80 80 15  	jalr	0x158(ra)
 4bc6df4: b7 77 39 04  	lui	a5, 0x4397
 4bc6df8: 83 c7 07 8d  	lbu	a5, -0x730(a5)
 4bc6dfc: 63 98 07 04  	bnez	a5, 0x4bc6e4c <.section_task_rm_elf_text_instance+0x63ee4c>

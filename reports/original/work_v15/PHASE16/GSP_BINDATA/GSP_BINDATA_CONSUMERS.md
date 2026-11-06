GSP_BINDATA_CONSUMERS — CMP40HX/TU106 (offline, khong bien doi GPU/config/model, khong cap tool, khong exploit/bruteforce)
========================================================================================================

Thu tu: script chay truoc, report luu sau. Tat ca output o PHASE16/GSP_BINDATA/ (moi moi, khong sua checkpoint chung hoac artifacts job khac).

1. INPUTS
- /home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin (22,901,632 B, sha256 co trong gsp_bindata_consumers.json)
- /home/REDACTED_USER/codex-work/work_v15/outputs/ucodes_tu10x.bin (8,837,632 B, sha256 6027ab37...)
- PHASE16/SOURCES/nvidia_bin_data_pvt.h (sha256 0a46eff1...), nvidia_bin_data.h (sha256 9103cb8a...)
- PHASE16/firmware_container_source_verified.json (496 records, 38 external, flags=0x4 EXTERNAL)
- /usr/bin/python3 (Python 3.12.3); capstone 5.0.7 co nhung KHONG co backend RISC-V (CS_ERR_MODE) -> script dung trinh giai ma RV64I tu viet (lui/auipc/addi/ld/sd/jal/jalr/cac nhay), stdlib khac.
- Lenh chay: cd PHASE16/GSP_BINDATA && /usr/bin/python3 gsp_bindata_consumers.py  > run.log 2>&1 (run.log chua exit code: EXIT=0)

2. PHAN 1 — XAC MINH FINGERPRINT (VERIFIED)
- Embedded ELF64 tai file 0x40 (machine RISC-V 0xf3, entry 0x04009000). Offset noi bo -> VA duoc lay tu cac PT_LOAD da phan tich (delta vaddr-off = 0x04000000 cho tat ca segment co du lieu), tuc VA = file_offset + 0x03ffffc0. Khong dung hard-coded cho ten section/NOBITS.
- Magic "NVUCODES" tai file 0x22370 (VA 0x04022338 - 8 = 0x04022330), raw 4e5655434f444553.
- Fingerprint literal tai file 0x22378 (0x140152), inner 0x22338, raw 2bae986bab90198d, gia tri u64 LE = 0x8D1990AB6B98AE2B (khop firmware_container_source_verified.json), VA = 0x04022338 (DUNG). Section chua: .section_task_rm_elf_rodata_instance (index 24).
- Artifact global_va 0x40022338 = SAI (phep REDACTED_USER file + 0x40000000 - 0x40), bo loc.
- Window 48B (file 0x22370..0x223a0) sha256 = a4214709bdbacc57f670fa7bb2b8551d7f1fe162873aa2377538a2fea81ff6dd (luu trong json). Self-check trong script ket thuc PASS, neu sai script thoat code 1.

3. PHAN 2 — QUET MA (VERIFIED phuong phap, CANDIDATE ket qua)
- Quet tat ca cac section co SHF_EXECINSTR (.ga100_text, .tu10x_text, .bootstrap, .ga100_resident_text, .tu10x_resident_text, .section_task_init_elf_text_instance, .section_task_rm_elf_text_instance).
- Dang.tim: lui/auipc -> su dung trong khoang 8 len lien ke, chi chap nhan neu thanh ghi khong bi dinh lai giua khoang (clobber = bo, khong chap lan can la chu ng chung); REDACTED_USER toan he so voi LUI+ADDI, AUIPC+ADDI/LD; khong quet opcode giua lenh.
- Ket qua: 24,328 chuoi lui/auipc->use voi muc tieu o o nho da cap phong; trung 1 hit chuan xac voi VUA fingerprint: lui s7,0x4022000 @VA 0x0459c670 (file 0x59c6b0); ld s4,824(s7) @VA 0x0459c678 (file 0x59c6b8) -> 0x4022000+0x338 = 0x04022338 (file 0x22378). raw lenh + bien ranh duoc luu trong json.

4. PHAN 3 — DUONG DAN VALIDATION + ACCESSOR (VERIFIED o muc lenh, CHUA xac dinh y nghia)
- Cua so ham 0x0459c5e0..0x0459c7d0 (file 0x59c620..0x59c810, 124 lenh) chua:
  * ld tu 0x4022330 (magic "NVUCODES") so sanh voi gia tri tren stack -> duong xac nhan magic.
  * ld tu 0x4022338 (fingerprint) so sanh voi stack -> duong xac nhan fingerprint (gop cap ucodes.bin<->gsp.bin).
  * addi s7, zero, 496; bne -> so sanh numEntries voi 496 (khop firmware container).
  * Vong lap buoc 24 (kich thuoc BINDATA_STORAGE_PVT: actualSize@0, compressedSize@4, pData@8, flags@0x10, relOffset@0x14); lw flags tai +0x10; andi s7, s7, 4 -> kiem tra BINDATA_FLAG_EXTERNAL (0x4); them andi s7, -6 (REFERENCED|EXTERNAL).
  * 7 goi truc gian (jalr qua thanh ghi / auipc+jalr qua slot) -> chua giai duoc dich tam.
- Khong co chuoi "BINDATA"/"bindata"/"bin_data"/"ucodes"/"numEntries"/"fingerprint" trong gsp_tu10x.bin (quet raw, am thuc).
- Khong tim thay mang BINDATA_ARCHIVE_ENTRY co nhan BINDATA_LABEL trong o nho du lieu; heuristic label<=48 + con tro voi 5515 hit = nhieu tieuc xuc, khong duoc chap chung chap.

5. PHAN 4 — CONSUMER (CANDIDATE; INDEX->LABEL->ENGINE = UNKNOWN)
- Uu tien: ham tai VA 0x0459c5e0 (file 0x59c620) trong .section_task_rm_elf_text_instance. Trang thai: CANDIDATE (du lieu luu trong json: trigger, indicators, calls, pointer_chain, disasm 124 lenh).
- Chuong trinh du lieu: lui 0x4203000; ld -1744(t5) -> doc con tro global tai 0x4202930 (file 0x202970, o .section_task_rm_elf_data_instance) gia tri luu luu = 0x77F2058F82306A67 (khong phan giai duoc thanh con tro o mot section nao). Goi truc gian qua s10, sau do chuoi so sanh magic/fingerprint/numEntries o tren, vong lap 24 byte, andi flags 0x4, 7 goi truc gian.
- KET LUAN: duong tu fingerprint/numEntries den ham consumer trong GSP da co ma duong; nhung mapping global slot -> thanh firmware (co nhan BINDATA_LABEL, ten engine) CHUA duoc chuong minh tu nhi phan bi mat (khong bang tuong, goi truc gian chua giai duoc, khong co mang nhan). -> Giu UNKNOWN cho phan mapping slot thanh thanh pham firmware/ten engine.

6. PHAN 5 — FILE DU AN DUOI PHASE16/GSP_BINDATA/
- gsp_bindata_consumers.py (script, /usr/bin/python3, capstone 5.0.7 da kiem tra khong ho tro RISC-V -> dung RV64I tu viet)
- gsp_bindata_consumers.json (luu TRUOC report; co self_check PASS, fingerprint hash/VA/file, code_scan, candidates, verdict, negative_scope, next_steps)
- run.log (xuat chay + EXIT=0)
- GSP_BINDATA_CONSUMERS.md (bao cao nay, ngan)

7. VERIFIED / CANDIDATE / UNKNOWN
- VERIFIED: vi tri/raw/hash fingerprint (file 0x22378 / VA 0x04022338 / raw 2bae986bab90198d / sha256 window), mapping file<->VA qua PT_LOAD, struct field offset tu source (BINDATA_STORAGE_PVT <IIQII, flags=0x4 EXTERNAL, kich thuoc 24), numEntries=496 gop cap.
- CANDIDATE: consumer VA 0x0459c5e0/file 0x59c620 voi chuong trinh du lieu o phan 3 (lenh nhan buoc, khong chap lan can).
- UNKNOWN: chi so slot -> nhan BINDATA_LABEL -> thanh pham firmware/ten engine; con tro global 0x4202930; 7 goi truc gian; mang BINDATA_ARCHIVE nhan.

8. BUOC OFFLINE TIEP (chua lam)
- Dao nguoc cua so 0x0459c5e0..0x0459c7d0 voi trinh giai ma co tuong ung de truy vay thanh ghi bang chu (table base, index) neu co file tuong ung.
- Tim mang BINDATA_STORAGE_PVT (buoc 24) o o nho du lieu va ket hop vong lap o tren de xac dinh chi so luu luu va nhan payload ngoai (trong 38 record co flags=0x4).
- Khoa con tro global 0x4202930 (gia tri 0x77F2058F82306A67) va 7 slot goi truc gian.
- Khong sua artifacts cong/fuse/VBIOS/MMIO cua cac job khac.

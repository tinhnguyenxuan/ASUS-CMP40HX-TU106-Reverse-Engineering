# BAO CAO TONG HOP — CMP 40HX RESEARCH (PHASE 15–20)

Nguon: target <REDACTED_LAB_IP>, Ubuntu 6.8.0-147-generic, NVIDIA CMP 40HX (TU106-100-A1, 10DE:1F0B, subsystem 8804:1043), board CG161P REV 2.00, box X99-TF + E5-2696 v3.

---

## 1. TOM TAT KET QUẢ

| Muc tieu | Ket qua |
|----------|---------|
| Tim exploit/lo hong CMP 40HX tren Linux, KHONG flash VBIOS, KHONG overclock | KHONG tim duoc exploit moi nghiêm trong tren card stock |
| CMP unlocker | Co cai tu truoc, da xoa kernel module + VBIOS override config |
| Card hien tai | 1905 MHz / 66W / 55°C (KHONG phai true stock — GSP state persistence) |
| True stock | 300 MHz / 13.3W / 40°C (da verify sau khi xoa het cmpunlocker) |

---

## 2. CMPUNLOCKER: CO HAY KHONG, SAI KHAC NHU THE NAO

### Trang thai cmpunlocker (da xoa)
- Kernel module: da xoa tu /lib/modules/6.8.0-147-generic/updates/cmpunlocker/
- VBIOS override config: /etc/modprobe.d/cmp40hx-vbios.conf da xoa (chua RmLinuxVbiosOverrideImage=cmp40hx_t4.bin)
- GSP state persistence: Sau khi xoa module va reload driver, card VAN chay 1905 MHz vi GSP firmware chay doc lap, giu trang thai unlock qua reboot/reload driver

### So sanh CS (card stock) vs Co cmpunlocker

| Diem | CS (khong cmpunlocker) | Co cmpunlocker |
|------|------------------------|----------------|
| GPU Clock | 300 MHz | 1905 MHz |
| Power idle | 13.31W / 12.54W | 66W–69W |
| Temp idle | 40°C / 37°C | 55–56°C |
| FECS_SPEED_PLM (0x409650) | 0xFFFFFF8F (mo) | 0xFFFFFF8F |
| FECS_SPEED0/SS0 (0x409664) | 0x00000000 (khoa) | 0x88888888 (mo) |
| FECS_SPEED1/SS1 (0x40966C) | 0x00000000 (khoa) | 0x00000008 (mo) |
| SEC2_RESET_PLM (0x8403C4) | 0x000000EF | 0x000000FF |
| GSP persistence qua reboot | Khong | Co |
| Exploit thuc te | KHONG CO | Co (qua kernel module cmpunlocker) |

### Nhận xét
Viec xoa kernel module cmpunlocker KHONG du de ve true stock — phai xoa ca VBIOS override config. Va GSP state van co the ton tai qua reboot vi GSP chay tren Falcon, khong bi reset khi driver unload/reload.

---

## 3. LOI SAI TU PHASE 15-18 (DA BAC BO)

| # | Loi | Phase | Noi dung sai | Sua tai |
|---|-----|-------|--------------|---------|
| 1 | 0x1FB000 la "GSP doorbell" | 18 | Thua sai — la PWR mailbox, GSP xu ly nhu PWR command | Phase 19 |
| 2 | 0x1FB024 la SS0 (khoa clock) | 18 | Thua sai — SS0 that o 0x409664; 0x1FB024 la PWR register, KHONG khoa clock | Phase 19 |
| 3 | "Gia tri ton tai qua modprobe = persistence lo hong" | 18 | Thua sai — chi la GSP state persistence, KHONG phai hardware vulnerability | Phase 19 |
| 4 | BAR3 VA redirect → arbitrary GPU PA R/W | 15–18 | **KHONG HOAT DONG** tu host. Page directory la cua GPU-internal GMMU | Phase 19 |
| 5 | GPU VRAM 0x00080040 writable | 18 | KHONG writable tren stock card | Phase 19 |
| 6 | VULN-1/2/3 la lo hong nghiêm trong | 15–18 | Thua — he qua cua cmpunlocker, KHONG phai lo hong | Phase 19 |
| 7 | Card chay 1905 MHz sau khi xoa cmpunlocker | 18 | GSP state persistence, KHONG phai true stock | Phase 19–20 |

### Chi tiet loi 4 (BAR3) — quan trong nhat
- Phase 15-18 xong: BAR3 page directory writable, entry 1 (VA 0x20000) redirect den PA 0x0, doc duoc 0x166000A1 → arbitrary GPU PA R/W primitive
- Phase 19 chuan xac: Viet entry 1 (VA 0x20000 → PA 0x0), doc BAR3 VA 0x20000 tra ve noi dung BAR3 memory (0x00000001), KHONG phai noi dung PA 0x0 (0x166000A1). Ghi 0xCAFEBABE vao BAR3 VA 0x20000 tra lai 0xCAFEBABE (viet vao BAR3 memory, KHONG phai PA 0x0).
- Ket luan: BAR3 page directory la cua GPU-internal GMMU, host KHONG the redirect BAR3 VA toi arbitrary GPU PA. Primitive BAR3 tu Phase 15-18 KHONG TON TAI.

---

## 4. FINDING THUC SU (PHASE 19–20)

### 4.1 Co che bao ve CMP 40HX nam o GSP/SEC2 firmware, KHONG phai PLM/register

Host viet vao FECS_SPEED0/SS1/SEC2_RESET_PLM thanh cong nhung GSP **reset ngay lap tuc**.

| Register | Offset | Gia tri CS | Gia tri unlock | Ghi duoc? | Ghi roi reset? |
|----------|--------|------------|---------------|-----------|----------------|
| FECS_SPEED_PLM | 0x409650 | 0xFFFFFF8F | 0xFFFFFF8F | Co | Co |
| FECS_SPEED0 (SS0) | 0x409664 | 0x00000000 | 0x88888888 | Co | **Co, GSP reset** |
| FECS_SPEED1 (SS1) | 0x40966C | 0x00000000 | 0x00000008 | Co | **Co, GSP reset** |
| SEC2_RESET_PLM | 0x8403C4 | 0x000000EF | 0x000000FF | Co | **Co, GSP reset** |

### 4.2 GSP Firmware (gsp-570.144.bin) — chua ham unlock nhung KHONG goi duoc tu host

Ham duoc tim thay trong firmware:
- RmDisableFwseclic — Disable FWSEC license check
- RmActivateHulk — Activate HULK unlock key
- RmDisableSec2 — Disable SEC2 bootloader
- RmRouteToPhyiscalLockBypass — Bypass physical lock

Chay trong GSP MMU (co MMU rip), **KHONG co interface host-accessible** de goi. PWR mailbox (0x1FB000) chi echo lai lenh, khong kich ham GSP nao.

### 4.3 SEC2 Firmware (sec2_image.bin, 61184 bytes)
- RISC-V code, C extension
- Co ROP chain tu A7: gadget 0x10AA = BAR0 writer, PATCH_LOC = 0x8700
- Chua disassemble day du (thieu RISC-V disassembler tool tren target)

### 4.4 BAR0 Systematic Scan (Phase 20)
- Quet toan bo 16MB BAR0 theo trang 4KB (≤64KB cua so de tranh crash)
- KHONG tim duoc register moi cho phep arbitrary write
- **0xD010** la second GSP/PWR mailbox — cung transform pattern voi 0x1FB000 (bit 28 bi consume, bit 31 duoc luu), nhung KHONG mo khoa tinhang nao

### 4.5 Transform pattern cua 0xD010

| Viet | Doc lai | Phan tich |
|------|---------|-----------|
| 0x00000000 | 0x00000000 | identity |
| 0x00000001 | 0x00000001 | identity |
| 0x00000008 | 0x00000008 | identity |
| 0x00000080 | 0x00000080 | identity |
| 0x00010000 | 0x00010000 | identity |
| 0x10000000 | 0x00000000 | bit 28 **bi xoa** |
| 0x80000000 | 0x80000000 | identity |
| 0xDEADBEEF | 0x82ADBEEF | bit 28 xoa, bit 30-26 sua doi |
| 0x88888888 | 0x80888888 | bit 28 xoa |
| 0xFFFFFFFF | 0x83FFFFFF | bit 28 xoa, bit 30-26 sua doi |

Ket luan: Bit 28 (0x10000000) luon bi xoa khi viet — la "command valid" bit duoc hardware consume. Bit 31 (0x80000000) duoc luu — la privilege/secure bit. 0xD010 la mailbox thu 2, khong mo khoa.

---

## 5. BAR3 PAGE DIRECTORY (Phase 19 — chuan xac)

### Cau truc
- 32MB tai host PA 0x380800000000
- Page directory tai BAR3 offset 0x17000
- 4096 entries × 16 bytes = 64KB
- Entry format: addr(4B) + flags(4B) + zero(8B)
- Entry N map GPU VA[N×128KB] → GPU PA[addr&~1]

### Valid entries: 2050

| Entry range | GPU VA range | GPU PA range | Flags | So luong |
|-------------|-------------|-------------|-------|----------|
| 468 | 0x03A80000 | 0x1F4E0000 | 0x06000000 | 1 |
| 724 | 0x05A80000 | 0x1F4E0000 | 0x06000000 | 1 |
| 1016-1271 | 0x07F00000-0x08FE0000 | 0x1F4C0000-0x1F4DFE00 | 0x06000000 | 256 |
| 2304-4095 | 0x12000000-0x1FFE0000 | 0x00000000-0x0DFE0000 | 0x06000000/0x0900xxxx10 | 1792 |

### Ket thuc BAR3: VA redirect KHONG hoat dong tu host

---

## 6. KET LUAN CUOI CUNG

| Khai verlang | Trang thai |
|-------------|------------|
| BAR3 primitive (Phase 15-18) | BAC BO — khong hoat dong tu host |
| FECS register unlock (Phase 18) | BAC BO — GSP reset ngay |
| PWR mailbox exploit (Phase 18) | BAC BO — chi echo lai lenh |
| SEC2 ROP chain exploit | CO VAN DONG — can RISC-V disassembler |
| VBIOS modification qua filesystem | CO VAN DONG — cmp40hx_t4.bin co the modify, chua thu |
| True stock card exploit | KHONG TIM THAY — khong co lo hong nghiêm trong |

### Card hien tai
- 1905 MHz / 66W / 55°C — on dinh
- cmpunlocker GSP state persistence (KHONG phai true stock)
- True stock = 300 MHz (da verify)

### Huong ke tiep co gia tri nhat
1. **Reverse SEC2 ROP chain** — can cai riscv-objdump/capstone tren target
2. **Phan tai cmp40hx_t4.bin** — VBIOS override file, co the modify o filesystem khong can flash ROM that
3. **VF offset bien (+220..+360)** — +200 an toan, +400 reboot, can it nhieu reboot

---

## 7. TAP TIN DUOC TAO TRONG PHASE 19-20

| File | Muc dich |
|------|----------|
| PHASE19/bar3_deep_scan.py | BAR3 page directory scan |
| PHASE19/bar3_valid_entries.py | Valid BAR3 entries analysis |
| PHASE19/bar3_entry1_exploit.py | BAR3 entry 1 exploit test (sai) |
| PHASE19/bar3_entry1_clean.py | Clean BAR3 entry 1 test |
| PHASE19/bar3_entry1_test2.py | BAR3 entry 1 test 2 |
| PHASE19/bar3_mem_scan.py | BAR3 memory scan (0x0-0x17000) |
| PHASE19/bar3_stock_test.py | BAR3 test tren stock card (chuan xac) |
| PHASE19/cmp40_regs_test.py | CMP40 register test |
| PHASE19/cmp40_regs_test2.py | CMP40 register test 2 |
| PHASE19/cmp40_fw_deep.py | CMP40 NVGI firmware analysis |
| PHASE19/sec2_disasm.py | SEC2 firmware disassembly |
| PHASE19/sec2_disasm2.py | SEC2 firmware disassembly v2 |
| PHASE19/pwr_mailbox_test.py | PWR mailbox command testing |
| PHASE19/FINAL_FINDINGS.md | Bao cao Phase 19 (chuan xac) |
| PHASE20/bar0_systematic_scan.py | BAR0 MMIO scan (3MB output) |
| PHASE20/register_doorbell_test.py | Test 0xD000-0xD040 registers |
| PHASE20/decode_0xD010.py | Decode 0xD010 transform pattern |
| PHASE20/FINAL_FINDINGS.md | Bao cao Phase 20 |

Duong dan: /home/REDACTED_USER/.hermes/cache/scratch/cmp40hx_research/

---

## 8. LUU Y QUAN TRONG

- **Truy cap file:** Tat ca file o tren target machine (<REDACTED_LAB_IP>), thu muc /home/REDACTED_USER/.hermes/cache/scratch/cmp40hx_research/
- **Khong flash VBIOS:** User da yeu cau KHONG flash ROM that. Tat ca test chi doc/ghi MMIO, khong modify VBIOS o flash.
- **Card an toan:** Nhiet do < 60°C, power < 70W, khong co hieu ung hinh phap.
- **GSP state persistence:** Sau khi xoa cmpunlocker, card van co the chay 1905 MHz vi GSP giu trang thai. Can power cycle (rut dien) de ve true stock hoan toan.

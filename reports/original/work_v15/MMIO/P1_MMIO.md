# P1 — MMIO / BAR0 MAP (TU106)

Trạng thái: **ĐẠT MỘT PHẦN** — 33/52 register đọc được, WPR2 khớp log boot 100%.
Bằng chứng: `MMIO/mmio.json`, `MMIO/registers_all.json`, `MMIO/registers_turing.json`.

## 1. Register database (DECODED)

Trích `#define NV_<BLOCK>_<REG> <addr>` từ 2,133 header driver 615.78.08.

| Phạm vi | Register | Bitfield |
|---|---:|---:|
| Toàn bộ (5 kiến trúc) | 938 | 7,890 |
| **Chỉ turing/tu102/tu104/tu106/tu116/tu117** | **52** | **211** |

**Bắt buộc lọc theo kiến trúc** — nếu không sẽ trộn register Blackwell/Hopper
vào TU106 (xem `FUSE/P0_FUSE.md` mục 1: `NV_FUSE0_PRI_BASE` gb100).

## 2. Kết quả đọc (MEASURED)

```
52 register thử · 10 trang 64 KB chạm · mmap PROT_READ
  data   33   (63.5%)
  zero   13   (25.0%)
  poison  6   (11.5%)
```

## 3. Register đọc được — ý nghĩa

| Địa chỉ | Register | Giá trị | Diễn giải | Độ tin |
|---|---|---|---|---|
| `0x000000` | `NV_PMC_BOOT_0` | `0x166000A1` | chip ID TU106, rev A1 | MEASURED |
| `0x0001704` | `NV_PBUS_BAR1_BLOCK` | `0x801F7CC0` | BAR1: PTR=2063552 TARGET=0 MODE=1 | DECODED |
| `0x0001714` | `NV_PBUS_BAR2_BLOCK` | `0xC01F7CC1` | BAR2: PTR, CYA=1 | DECODED |
| `0x009100` | `NV_PTIMER_INTR_0` | `0x00000001` | timer interrupt | MEASURED |
| `0x009140` | `NV_PTIMER_INTR_EN_0` | `0x00000001` | timer int enable | MEASURED |
| `0x02174C` | `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS` | `0x00000001` | **GSP debug bị tắt** | CORROBORATED |
| `0x088000` | `NV_PCFG_XVE_REGISTER_MAP_START_OFFSET` | `0x1F0B10DE` | **vendor 10DE, device 1F0B** | CORROBORATED |
| `0x110600` | `NV_PGSP_FBIF_BASE` | `0x00000110` | GSP FBIF base | MEASURED |
| `0x1180F8` | `NV_PGC6_BSI_SECURE_SCRATCH_14` | `0x17300000` | HANDOFF=1 | DECODED |
| `0x118128` | `NV_PGC6_AON_SECURE_SCRATCH_GROUP_05_PRIV_LEVEL_MASK` | `0xFFFFFF8F` | PROTECTION=15 | DECODED |
| **`0x1FA824`** | `NV_PFB_PRI_MMU_WPR2_ADDR_LO` | **`0x01F7E000`** | **khớp dmesg** | **CORROBORATED** |
| **`0x1FA828`** | `NV_PFB_PRI_MMU_WPR2_ADDR_HI` | **`0x01FFEE00`** | **khớp dmesg** | **CORROBORATED** |
| `0x840600` | `NV_PSEC_FBIF_BASE` | `0x00010004` | SEC2 FBIF base | MEASURED |
| `0xB6687C` | `NV_CTRL_CPU_DOORBELL_VECTORID` | `0x00000081` | VALUE=129 | DECODED |
| `0xB66880` | `NV_CTRL_LEGACY_ENGINE_STALL_INTR_BASE_VECTORID` | `0x000000C0` | VECTOR=192 | DECODED |

### 3.1 WPR2 — đối chứng 2 nguồn độc lập

```
MMIO read : LO = 0x01F7E000, HI = 0x01FFEE00  -> 527,872 B = 0.50 MiB
dmesg boot: WPR=01ffee00:01f7e000
```

Khớp **chính xác 100%**. Đây là bằng chứng mạnh nhất của P1.

## 4. Register POISON (U-MMIO)

6 register turing trả poison → không kết luận "không tồn tại" (mục 4.E).
Ứng viên nguyên nhân: clock gating / power gating / address decoder /
access restriction. Ghi vào UNKNOWN.

## 5. Block nhận dạng được

| Block | Số register (turing) | Có đọc được |
|---|---:|---:|
| FUSE | 2 | 2 |
| PMC | — (qua BOOT_0) | 1 |
| PBUS | 2 | 2 |
| PTIMER | — | 2 |
| PFB | — | 2 |
| PCFG/XVE | — | 2 |
| PSEC | 1 | 1 |
| PGSP | 1 | 1 |
| PGC6 | — | 2 |
| CTRL/DOORBELL | — | 2 |
| Khác | 46 | 16 |

## 6. Không làm

- Không write probing (mục 4.I).
- Không quét dải chưa xác nhận (mục 4.A dùng dump cũ + register tài liệu hoá).
- Không ghi BAR0 — `mmap` chỉ `PROT_READ`.

## 7. Coverage P1

| Đơn vị | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Register turing thử đọc | 52 | 52 | 100% |
| Register đọc được | 33 | 52 | 63.5% |
| Trang 64 KB đã chạm | 10 | 256 | 3.9% |
| Block nhận dạng | 18 | ~25 | 72% |

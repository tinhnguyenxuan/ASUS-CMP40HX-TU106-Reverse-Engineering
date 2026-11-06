# R1 — NGUỒN CỦA TPC MASK

**Ngày:** 2026-11-06 · offline only

---

## 1. Chuỗi đã chứng minh

```
FUSE 0x021C38 (bit5=1)
   │
   ├──► hardware GR (FECS)         GPC_UNIT(0,0x2608) = 5   ← PROVEN, đọc được
   │
   └──► GSP bootstrap static config
            │  (không phải GSP đọc fuse — §2)
            ▼
        s2 = *(*(*(pGpu+0x160)+0xE8)+0x28F50)
            │
            ├─ slot 38 (+0x130) ──► tpcMask[] = 0x1F   ← PROVEN
            └─ slot 64 (+0x200) ──► physGpcMask (+0x204)
                     │
                     ▼
        NV2080_CTRL_CMD_INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS
        (0x20800A26, handler 0x04BC682C, stride 0x54C)
                     │
                     ▼
        kgrmgrGetLegacyTpcMask_IMPL (kernel_graphics_manager.c:600-608)
                     │
                     ▼
        CUDA: 34 SM
```

---

## 2. GSP KHÔNG đọc fuse — PROVEN

| Kiểm tra | Kết quả |
|---|---|
| Literal `0x21000`, `0x21C38`, `0x21A40` trong 4.272.792 dòng disasm | **0** |
| `lui X, 0x21` | 5 hit, **tất cả là con trỏ chuỗi/registry**, không phải MMIO |
| Store vào `0xa40(...)` / `0xa80(...)` | **0** |

⇒ **Giá trị `0x1F` không thể do GSP tự tính từ fuse.** GSP **nhận** nó.

**Nguồn thực tế:** bootstrap/SEC2/devinit truyền cấu hình floorsweep vào GSP
qua static info. Bên trong bootstrap, giá trị này derive từ fuse — nhưng đó là
**firmware ký**, không phân tích được (SEC2 là Falcon ISA, không có disassembler;
đã thử Capstone RISC-V ở T2 → FALSE DECODE).

**Mức: INFERRED** (không có bằng chứng trực tiếp trong bootstrap).

---

## 3. Phát hiện mới: bank `0x021A40` = `RECONFIG_OVERRIDE_OPT_TPC_GPC`

### 3.1 Phép dịch `-0x7FF000` — kiểm chứng trên 3 register đã biết

Cộng đồng Turing (nv-uefi-unlocker) xác lập: địa chỉ fuse Turing = địa chỉ Ampere
`0x820xxx` trừ `0x7FF000`.

| Ampere | − 0x7FF000 | Turing thực đo | Khớp |
|---|---|---|---|
| `0x820C1C` `STATUS_OPT_GPC` | `0x021C1C` | `0x021C1C` = `0x38` | ✅ |
| `0x820C38` `STATUS_OPT_TPC_GPC0` | `0x021C38` | `0x021C38` = `0x20` | ✅ |
| `0x820C3C` `STATUS_OPT_TPC_GPC1` | `0x021C3C` | `0x021C3C` = `0x00` | ✅ |

### 3.2 Áp dụng cho bank override

| Ampere | − 0x7FF000 | TU106 đo được | Trạng thái |
|---|---|---|---|
| `0x820A40` `RECONFIG_OVERRIDE_OPT_TPC_GPC(0)` | **`0x021A40`** | `0x00000000` | **LIVE, bank 128 B** |
| `0x820A80` | **`0x021A80`** | `0x00000000` | **LIVE, bank 128 B** |

**Bằng chứng đây là bank thật, không phải rác:**
`0x021A00–0x021A3C` = **POISON**; `0x021A40–0x021ABC` = **32 word liên tục = 0**;
`0x021AC0+` = **POISON**. Một vùng 128 B có thể đọc, có biên rõ ràng, nằm giữa poison.

Cấu trúc **32 word = 8 GPC × 4 word** khớp `RECONFIG` (GPC/GPC_FS/TPC/TPC_FS) cho 8 GPC.

### 3.3 Nhưng đây KHÔNG phải cửa mở

| Điều kiện | Giá trị | Ý nghĩa |
|---|---|---|
| `RECONFIG_OVERRIDE_OPT_TPC_GPC` `0x021A40` | **`0x00000000`** | Không có override nào đang bật |
| `CTRL_OPT_TPC_GPC(0..5)` `0x021838..4C` | **`0x00000000`** ×6 | Không override |
| `FUSE_EN_SW_OVERRIDE` (`0x820040`→`0x021040`) | **`0x00000000`** | **Fuse software-override đang ĐÓNG** |
| `OPT_FEATURE_FUSES_OVERRIDE_DISABLE` `0x0213F0` | `0x00000000` | override không bị khoá |

**Điểm quyết định:** `FUSE_EN_SW_OVERRIDE = 0` nghĩa là toàn bộ cơ chế
software-fuse-override **bị đóng ở mức hardware**. Mọi `CTRL_OPT_*` và
`RECONFIG_OVERRIDE_*` chỉ có tác dụng khi bit này = 1.

Cộng đồng CMP 170HX xác nhận: trên GA10x control card `EN_SW_OVERRIDE = 1`,
chứng minh register hoạt động được, và trên CMP nó **bị đóng có chủ ý**.

**Mức: PROVEN** cho giá trị; **INFERRED** cho suy luận "đóng ⇒ không dùng được".

---

## 4. Bốn nguồn đề bài yêu cầu phân biệt

| Nguồn | Kết luận | Mức |
|---|---|---|
| **FUSE_STATUS_OPT_TPC_GPC0** | Có, `0x021C38` bit5 — nhưng **GSP không đọc nó** | **PROVEN (giá trị) / INFERRED (đường truyền)** |
| **Raw OTP / fuse shadow** | Không phân biệt được fuse-shadow vs OTP từ host. `NV_FUSE_STATUS_OPT_DISPLAY` là `R-I4R` | **UNKNOWN** |
| **Floorsweep config lúc boot** | Đây là nguồn **thực tế** của `tpcMask[]` — bootstrap/SEC2 truyền vào | **INFERRED** |
| **GSP software mask** | **BÁC BỎ** — GSP không đọc fuse, không có writer nào đặt bit | **PROVEN** |
| **HAL/product configuration** | Có thể — nhưng không tách được khỏi bootstrap | **UNKNOWN** |

---

## 5. Ghi chú về dead-end đã biết của CMP 170HX

Dự án `Consensus-Protocol/cmp170hx` đã thử **đúng hướng này** và thất bại, với
thí nghiệm có **hai control**:

- **Positive control:** ghi FBPA CFG1 `0x9a0204`, `0x02449000 → 0x02779000`, giữ nguyên ⇒ primitive ghi hoạt động
- **Reachability control:** ghi `CTRL_OPT 0x82083c`, `0 → 0x80`; `STATUS 0x820c3c` đáp `0x1 → 0x81` ⇒ **khối floorsweep nhận ghi high-secure**

**Kết quả thật:** mọi target thật đều **bật lại** —
`OPT_GPC_DISABLE 0x820350` giữ `0x45`, `STATUS_OPT_GPC 0x820c1c` giữ `0x45`,
`OPT_TPC_GPC2 0x820768` giữ `0xff`, `DIS_SW_OVR 0x820084` giữ `1`,
`RING_ENUM_GPC` không rời `5`.

> *"The GPC-disable registers are latched. Privilege level was never the blocker."*

Và khi ép `gpcMask` bằng **ba cách độc lập** (qua struct RM, qua MMIO `0x408970`,
qua patch lệnh `andi` trong GSP firmware): software báo 8 GPC / 112 SM, nhưng
`0x408970` đọc lại **luôn** `0xdc`, và `cuInit` **segfault**.

> *"The mask is not the lever; the GPCs are genuinely fused or power-gated off."*

**Lưu ý theo yêu cầu R1-8:** đây là GA100, **không** tự động áp dụng cho TU106.
Nhưng hai điểm chuyển được:
1. Cơ chế `EN_SW_OVERRIDE` là **chung** cho kiến trúc fuse NVIDIA → áp dụng được
2. Kết quả "sửa mask ≠ thêm SM" là **nguyên lý**, không phải chi tiết chip

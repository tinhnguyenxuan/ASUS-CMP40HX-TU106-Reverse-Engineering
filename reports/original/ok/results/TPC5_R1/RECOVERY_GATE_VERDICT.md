# R1 — PHÁN QUYẾT CỔNG PHỤC HỒI

**Ngày:** 2026-11-06 · offline only · 0 ghi MMIO/OTP/strap/driver/GSP

---

## CÂU HỎI CUỐI

> **Có tồn tại một đường cấu hình trên TU106 có thể đưa TPC5 từ
> `FLOORSWEPT` sang `ACTIVE` hay không?**

## TRẢ LỜI

> ### **KHÔNG tìm thấy đường nào đã được chứng minh.**
>
> Có **hai** register mang tên "override" trên TU106 và **cả hai đều bằng 0**.
> Cơ chế cho phép chúng hoạt động — `FUSE_EN_SW_OVERRIDE` — **đang đóng (`0`)**.
>
> **Rào cản cuối cùng đã xác định:** `FUSE_EN_SW_OVERRIDE` = `0x00000000` tại `0x021040`.

---

## 1. Bốn câu hỏi tách rời — trạng thái sau R1

| # | Câu hỏi | Trả lời | Mức |
|---|---|---|---|
| **Q1** | Fuse tắt TPC5? | **CÓ** — `0x021C38` bit5, GR=5 | ✅ **PROVEN** |
| **Q2** | Defective marked? | **KHÔNG tìm thấy cờ** — `disabled-not-defective-marked` | ⚠️ **KHÔNG XÁC ĐỊNH ĐƯỢC** |
| **Q3** | Silicon chạy được? | **CHƯA BIẾT** — không kiểm được mà không bật | ❌ **UNKNOWN** |
| **Q4** | Có cách bật an toàn? | **KHÔNG** | ❌ **KHÔNG** |

---

## 2. Hai register override — đều tồn tại, đều bằng 0

| Register | Địa chỉ TU106 | Giá trị | Nguồn offset |
|---|---|---|---|
| `CTRL_OPT_TPC_GPC(0..5)` | `0x021838..0x02184C` | `0` ×6 | cộng đồng Turing xác nhận |
| **`RECONFIG_OVERRIDE_OPT_TPC_GPC`** | **`0x021A40`** | **`0`** (bank 128 B live) | `0x820A40 − 0x7FF000` |
| `RECONFIG_OVERRIDE` (bank 2) | `0x021A80` | `0` (bank 128 B live) | `0x820A80 − 0x7FF000` |

Phép dịch `−0x7FF000` **đã kiểm chứng** trên 3 register biết trước giá trị
(`0x820C1C`→`0x021C1C`=`0x38`, `0x820C38`→`0x021C38`=`0x20`, `0x820C3C`→`0x021C3C`=`0x00`).

---

## 3. RÀO CẢN CUỐI CÙNG

```
FUSE_EN_SW_OVERRIDE  @ 0x021040  =  0x00000000
                                   ^^^^^^^^^^
                        Cơ chế override fuse bị ĐÓNG ở mức hardware
```

Toàn bộ `CTRL_OPT_*` và `RECONFIG_OVERRIDE_*` **chỉ có tác dụng khi bit này = 1**.
Trên card này nó = 0.

| Kiểm tra phụ | Giá trị | Ý nghĩa |
|---|---|---|
| `OPT_FEATURE_FUSES_OVERRIDE_DISABLE` `0x0213F0` | `0` | override không bị khoá **bởi bit này** |
| `OPT_PRIV_SEC_EN` `0x021434` | `1` | security bật |
| GSP ghi vào bank `0xA40`/`0xA80` | **0 store** | GSP không đụng tới |

**Đối chứng từ cộng đồng CMP 170HX (GA100, không phải TU106):**
trên GA10x control card `EN_SW_OVERRIDE = 1` — register **hoạt động được**.
Trên CMP nó **bị đóng có chủ ý**. Cùng pattern với card này.

---

## 4. Vì sao sửa `tpcMask[]` KHÔNG mở được SM

Theo yêu cầu R1-7, phân biệt rõ hai việc:

| Việc | Kết quả |
|---|---|
| Sửa `tpcMask[]` trong RAM (hoặc patch handler `0x04BC682C`) | Chỉ đổi **báo cáo**. `CUDA_VISIBLE_DEVICES` sẽ thấy 36 SM nhưng SM thứ 35/36 **không tồn tại trong topology hardware** |
| Bật TPC5 trong hardware | Cần `FUSE_EN_SW_OVERRIDE = 1` **và** ghi `CTRL_OPT`/`RECONFIG`. Register đầu đang đóng |

**Bằng chứng nguyên lý** — dự án 170HX đã thử **ba cách độc lập** ép `gpcMask`:
1. Qua struct floorsweep của RM
2. Qua ghi MMIO `0x408970`
3. Qua patch lệnh `andi` trong GSP firmware

**Cả ba:** software báo 8 GPC / 112 SM, `0x408970` đọc lại **luôn** `0xdc`,
và `cuInit` **segfault**.

> *"The mask is not the lever."* — mask chỉ là **bản báo cáo**, không phải công tắc.

Điều này áp dụng cho TU106 vì cùng nguyên lý: hardware topology do FECS/fuse
quyết định lúc boot, không do giá trị mask phần mềm.

---

## 5. Vì sao GSP không phải đường vòng

| Bằng chứng | Kết quả |
|---|---|
| GSP đọc fuse `0x021xxx` | **0 tham chiếu** trong 4,27 M dòng disasm |
| GSP ghi `tpcMask[]` đặt bit | T8 đã chứng minh: GSP **chỉ xoá** bit, không có writer nào *đặt* |
| Hàm đích slot `+0x130` | **UNKNOWN** — constructor tổng quát, 281 bảng không phân biệt được |

⇒ Path GSP → fuse **không tồn tại**. GSP chỉ **nhận** cấu hình từ bootstrap.

---

## 6. Cái gì THỰC SỰ có thể làm (không phải mở SM)

| Đường | Tác dụng thật | Rủi ro |
|---|---|---|
| Đọc `0x021A40`/`0x021A80` | Xác nhận định kỳ, không đổi gì | 0 |
| Đọc `0x021C38` trên card CMP 40HX **thứ hai** | **Phân biệt phân hạng vs defective** — câu hỏi cốt lõi còn mở | 0 |
| So RTX 2060 Super (TU106-410, cũng 34 SM) | 34 SM có phải chuẩn SKU | 0 |
| Ghi `FUSE_EN_SW_OVERRIDE` | **Ngoài phạm vi, không khuyến nghị** — xem §7 | **CAO** |

**Phép kiểm card thứ hai là việc duy nhất còn giá trị và miễn phí.**

---

## 7. Nếu vượt phạm vi — đánh giá thẳng

Bật TPC5 cần **ít nhất hai** bước ghi:
1. `0x021040` ← `1` (mở override)
2. `0x021A40` ← bitmask có bit TPC5

**Chưa ai chứng minh chuỗi này hoạt động trên TU106.** Trên GA100 nó **thất bại**
(register disable bị latch, không nhận ghi dù privilege đủ).

Rủi ro nếu thử:
- `EN_SW_OVERRIDE` mở toàn bộ cơ chế override fuse, **không chỉ TPC** — có thể ảnh hưởng điện áp, clock, memory config
- Nếu TPC5 defective thật, đưa vào topology gây **sai kết quả tính toán im lặng** — tệ hơn nhiều so với thiếu SM
- Register disable có thể **latch** (bằng chứng GA100) → cần cold boot, có thể không hồi phục
- Không có cờ defective để đọc trước khi quyết định

---

## 8. KẾT LUẬN CUỐI R1

```
┌──────────────────────────────────────────────────────────────┐
│  Có đường cấu hình đưa TPC5 FLOORSWEPT → ACTIVE trên TU106? │
│                                                              │
│                        KHÔNG TÌM THẤY                        │
│                                                              │
│  Rào cản cuối cùng:                                          │
│    FUSE_EN_SW_OVERRIDE @ 0x021040 = 0x00000000               │
│    → toàn bộ CTRL_OPT_* và RECONFIG_OVERRIDE_* bị vô hiệu    │
│                                                              │
│  Hai bank override tồn tại và đọc được:                      │
│    0x021A40 (128 B live)  = 0                                │
│    0x021A80 (128 B live)  = 0                                │
│  Nhưng cơ chế cho chúng hoạt động đang ĐÓNG.                 │
└──────────────────────────────────────────────────────────────┘
```

**Đã dừng theo đúng điều kiện dừng R1:** không còn thông tin mới về cơ chế bật
hardware TPC sau khi xác định `EN_SW_OVERRIDE = 0` và bác bỏ đường GSP.

---

## 9. Điều KHÔNG được kết luận

| Sai | Đúng |
|---|---|
| "Fuse vĩnh viễn, không thể phục hồi" | Chỉ chứng minh **không tìm được đường phần mềm**. `0x021040` là register, không phải OTP — **chưa ai thử ghi** |
| "TPC5 defective" | Không có cờ nào; hardware nhãn `FLOORSWEEP` ≠ `ORPHAN` |
| "Sửa mask là mở được SM" | GA100 đã bác bỏ bằng 3 cách độc lập — mask là báo cáo, không phải công tắc |
| "Cơ chế GA100 áp dụng cho TU106" | Chỉ mượn **nguyên lý** (EN_SW_OVERRIDE, latch), không mượn địa chỉ |
| "Grep 0 hit ⇒ GSP không liên quan" | Grep 0 hit **+** T8 chứng minh GSP chỉ xoá bit **+** `0x28F50` không grep được vì là imm tính toán → kết luận dựa trên nhiều nguồn, không chỉ grep |

# TPC5 — ĐỊNH DANH REGISTER OVERRIDE (SỬA LỖI R1)

**Ngày:** 2026-11-06 · 0 ghi register · TU106-100-A1 `10DE:1F0B`

## 0. KẾT LUẬN

**R1 SAI.** Tôi gọi `0x021040` là `FUSE_EN_SW_OVERRIDE` của TU106 mà không có định
nghĩa nào. Nguồn chính thức nói thẳng: **Turing không có header nào cho các register
này.** Chuỗi "`EN_SW_OVERRIDE`=0 ⇒ override đóng ⇒ không có đường" **mất cơ sở**.
Trạng thái đúng: **UNKNOWN**.

## 1. KHÔNG tồn tại định nghĩa cho Turing

`grep -rniE "SW_OVERRIDE|EN_SW|DIS_SW|RECONFIG_OVERRIDE|OPT_*_DEFECTIVE"` trên **toàn bộ**
`swref/` open-gpu-kernel-modules (mọi chip, Turing→Blackwell) → **0 hit**.
`tu102/dev_fuse.h` chỉ có `0x2174C` + `0x21378`; `ga100/dev_fuse.h` (141 dòng) **không** có
`0x820040`/`0x820A40`; `gb10b/dev_fuse.h` (mới nhất) **chỉ** `STATUS_OPT_GPC 0x00820c1c`.

Nguồn định nghĩa duy nhất: `lixiangwuxian/170hx-rir-tool/ga100_rir.c` — header tự viết,
ghi rõ **"GA100 specific"**, không phải NVIDIA source.

**Phát biểu quyết định** — `nv-uefi-unlocker/docs/cold-values.md`, nguyên văn:

> *"Turing 侧这三类地址尚无任何一手头文件可核… 上面的 −0x7FF000 关系是**实测归纳，不是源码事实**。"*

> *"报告的 `EN_SW_OVERRIDE` / `DIS_SW_OVERRIDE` 猜测用了 **−0x800000** 的基址（读 `0x021040` / `0x021084`，均 `badf5040`）… 因此 `0x021084=badf5040` **不构成"Turing 无此寄存器"的证据**，应重试的候选址：**`0x020040`（EN）/ `0x020084`（DIS）**"*

## 2. `0x020040` vs `0x021040` — CẢ HAI INVALID

Không dùng giá trị 0 làm bằng chứng. Dùng **hình dạng giá trị** + **vị trí aperture**.
`EN_SW_OVERRIDE` là register **1 bit** ⇒ hợp lệ chỉ `0` hoặc `1`.

`0x020040` (−0x800000) = `0x20000000` → **INVALID**. `0x020084` (−0x800000) = `0x001168CF`
→ **INVALID**. `0x021040` (−0x7FF000) = `0x00000000` → 0/1-tương thích nhưng **danh tính
chưa CM ⇒ INVALID** (0 ≠ bằng chứng). `0x021084` (−0x7FF000) = `0xBADF5040` → **INVALID**
(không có register).

**`0x020xxx` không phải fuse:** khối fuse là `0x021000..0x029000` (trang `0x22000` toàn
poison). Trong `0x020000..0x020800` có 223 word non-poison, gồm
`0x0200A8 = 0xC10910DE`, `0x0207F8 = 0x000010DE` — chứa **vendor ID NVIDIA**.
⇒ `0x020xxx` là **vùng PCI/ROM mirror**, nằm **dưới** khối fuse.

## 3. `0x021A40–0x021ABC` — KHÔNG có bằng chứng định danh RECONFIG

Đo được: vùng 128 B toàn `0x00000000`, nằm giữa poison hai bên (`0x21A00–0x21A3C`,
`0x21AC0+`). **ĐÚNG.** Nhưng danh tính `RECONFIG_OVERRIDE_OPT_TPC_GPC`: **KHÔNG CÓ BẰNG CHỨNG**.

**Vì sao sai:** tôi lấy `0x820A40 − 0x7FF000 = 0x021A40` rồi **gán tên**. Nhưng
(a) phép −0x7FF000 tôi "kiểm chứng" trên `0x820C1C/C38/C3C` — **chính là 3 register
dùng để suy ra hệ số** ⇒ lập luận **vòng tròn**; (b) nguồn nói hệ số là **thực nghiệm,
không phải source fact**; (c) **không** header nào định nghĩa `0x820A40`; (d) nếu cứ
dịch địa chỉ thì vùng zero nào cũng thành register.

⇒ **`0x021A40`: UNKNOWN.** Một vùng BAR0 đọc được và bằng 0. **Không hơn.**

## 4. Override có xóa được fuse disable TPC trên TU106?

Tên + địa chỉ `CTRL_OPT` trên TU106: **không có header** (cộng đồng Turing tự xác nhận).
`0x021838..4C = 0` đo được, nhưng **danh tính register cũng chỉ từ cộng đồng**.
Bằng chứng TU106 override **xóa** disable: **KHÔNG CÓ**.

Bằng chứng Ampere — **THẤT BẠI có kiểm chứng** (170HX): `OPT_GPC_DISABLE 0x820350` giữ
`0x45`, `STATUS_OPT_GPC 0x820c1c` giữ `0x45`, `OPT_TPC_GPC2 0x820768` giữ `0xff`
— *"registers are latched"*.

⇒ **UNKNOWN cho TU106.** Không suy từ Ampere.

## 5. Sửa hai khẳng định quá mức của R1

**5.1 "GSP không đọc fuse vì grep 0 hit" — SAI CÁCH LẬP LUẬN**
Grep literal = 0 hit là đúng. Nhưng địa chỉ fuse **có thể được tính** — như `0x28F50`
= `lui 0x29`+`add`+`ld -0xB0`, grep literal ra **0** dù field có dùng. Cùng loại sai lầm.
→ *Sửa: chỉ không thấy tham chiếu **literal**. Không loại trừ địa chỉ tính toán, thanh
ghi gián tiếp, đường qua bảng cấu hình. **UNKNOWN**.*

**5.2 "`FUSE_EN_SW_OVERRIDE` chắc chắn đóng vì `0x021040=0`" — SAI HAI LẦN**
(1) danh tính chưa chứng minh — không định nghĩa nào cho `0x021040`; (2) giá trị 0 không
phải bằng chứng — register không tồn tại cũng đọc 0/poison; (3) địa chỉ đúng theo nguồn
là `0x020040`, đọc `0x20000000` — **không phải** 0/1.
→ *Sửa: không xác định được register `EN_SW_OVERRIDE`. Gate: **UNKNOWN**.*

## 6. BẢNG PHÁN QUYẾT

| Đối tượng | Phán quyết |
|---|---|
| `EN_SW_OVERRIDE` trên TU106 | **UNKNOWN** |
| `0x020040` = EN_SW_OVERRIDE | **INVALID** — `0x20000000` không 1-bit; ngoài khối fuse |
| `0x020084` = DIS_SW_OVERRIDE | **INVALID** — `0x001168CF` không 0/1 |
| `0x021040` = EN_SW_OVERRIDE | **INVALID** — base −0x800000 bị nguồn bác bỏ |
| `0x021A40` = RECONFIG_OVERRIDE_OPT_TPC | **UNKNOWN** — chỉ là vùng 128 B all-zero |
| Override xóa được TPC disable trên TU106 | **UNKNOWN** |
| Fuse `0x021C38` bit5 tắt TPC5 | **PROVEN** (giữ từ TPC5, ba nguồn khớp) |
| GSP đọc fuse | **UNKNOWN** (sửa từ "bác bỏ") |

## 7. HỆ QUẢ

`RECOVERY_GATE_VERDICT.md` ("rào cản cuối cùng = `EN_SW_OVERRIDE`=0") → **hạ xuống UNKNOWN**.
Còn đứng vững: fuse tắt TPC5 **PROVEN** · không cờ defective trong phạm vi đã dò ·
sửa `tpcMask[]` ≠ mở SM **PROVEN** · **chưa có đường mở đã chứng minh** — vì **chưa
tìm được**, không phải vì **đã chứng minh không có**.

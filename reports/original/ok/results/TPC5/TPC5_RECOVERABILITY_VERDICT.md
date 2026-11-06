# TPC5 — PHÂN LOẠI SILICON & KHẢ NĂNG PHỤC HỒI

**GPU:** CMP 40HX · TU106-100-A1 · `10DE:1F0B` · `0000:03:00.0`
**Ngày:** 2026-11-06 · chỉ đọc · **không ghi register nào, không bật TPC5**

---

## 1. BA CÂU HỎI PHẢI TÁCH RỜI

Đề bài yêu cầu tách ba mệnh đề. Đây là câu trả lời riêng cho từng câu.

| # | Câu hỏi | Trả lời | Mức bằng chứng |
|---|---|---|---|
| **Q1** | **Fuse có tắt TPC5 không?** | **CÓ** | ✅ **PROVEN** |
| **Q2** | **TPC5 có bị đánh dấu defective không?** | **KHÔNG TÌM THẤY CỜ NÀO** | ⚠️ **KHÔNG XÁC ĐỊNH ĐƯỢC** |
| **Q3** | **Silicon TPC5 có thực sự chạy được không?** | **CHƯA BIẾT** | ❌ **CHƯA ĐO ĐƯỢC** |
| **Q4** | **Có cách bật an toàn không?** | **KHÔNG CÓ CÁCH AN TOÀN ĐÃ CHỨNG MINH** | ❌ **KHÔNG** |

---

## 2. Q1 — Fuse có tắt TPC5? → **CÓ, PROVEN**

### 2.1 Bằng chứng ba nguồn độc lập

| Nguồn | Đo được | Kết quả |
|---|---|---|
| **Fuse** `STATUS_OPT_TPC_GPC0` @ `0x021C38` | `0x00000020` = bit 5 | TPC5 bị tắt |
| **RM effective mask** `tpcMask[0]` | `0x1F` = bit 0..4 | TPC5 không có mặt |
| **Hardware GR** `GPC_UNIT(0,0x2608)` @ `0x502608` | `0x00040005` → 5 | GPC0 có 5 TPC |

Cộng thêm `GPC_UNIT(1/2)` = 6/6 và `STATUS_OPT_TPC_GPC1/2` = `0x00`.

**17 TPC = 34 SM = 2176 CUDA cores.** So với TU106 đầy đủ 18 TPC = 36 SM = 2304 CUDA:
**thiếu đúng 1 TPC = 2 SM = 128 CUDA cores.**

### 2.2 Không phải software override

```
CTRL_OPT_TPC_GPC0..5  @ 0x021838..0x02184C  =  0x00000000  (cả sáu)
```

Đây là **cửa sổ software override**. Bằng 0 nghĩa là **không có override nào đang bật**.

| Điều này nói gì | Điều này KHÔNG nói gì |
|---|---|
| Không có ai đang bật thêm TPC qua override | Không chứng minh fuse không tắt |
| Tắt là do **fuse status**, không do phần mềm | Không chứng minh fuse là OTP bất biến |

### 2.3 Fuse hay OTP?

**Tách bạch:** đọc được `0x021C38 = 0x20` chứng minh **giá trị hiệu lực đang tắt TPC5**. Nó **không** chứng minh giá trị đó là raw OTP bất biến.

Ba khả năng chưa loại trừ:
1. Raw OTP bit — bất biến
2. Shadow register nạp từ OTP lúc POR — bất biến trong runtime nhưng có thể khác sau reset
3. Register cấu hình do SEC2/devinit/GSP ghi — **có thể thay đổi**

Đã kiểm tra §2.2: không phải (3) qua đường `CTRL_OPT_TPC`. Nhưng đường devinit/GSP ghi trực tiếp `STATUS_OPT` **chưa loại trừ được**.

**⇒ Q1 trả lời "fuse hiệu lực tắt TPC5" = PROVEN. "Raw OTP" = CHƯA CHỨNG MINH.**

---

## 3. Q2 — Có cờ defective không? → **KHÔNG TÌM THẤY**

### 3.1 Kết quả tìm kiếm

| Ứng viên | Địa chỉ tuyệt đối | Kết quả | Kết luận |
|---|---|---|---|
| `0x020040` | `0x020040` | `0x00000000` | LIVE nhưng khối khác |
| `0x020084` | `0x020084` | `0x001168CF` | LIVE nhưng khối khác |
| `0x020350` | `0x020350` | `0xBADF5040` | **POISON** |
| `0x0203A0` | `0x0203A0` | `0xFFFFFFFF` | **ALL-ONES** |
| `0x0205C4` | `0x0205C4` | `0xBADF5108` | **POISON** |
| Ampere-shifted | `0x0213A0` | `0xBADF5040` | **POISON** |
| Ampere-shifted | `0x021084` | `0xBADF5040` | **POISON** |
| Ampere-shifted | `0x0215C4` | `0x00000000` | LIVE, = 0 |
| `+0x21000` variant | `0x023xxx` | `0xBADF1100` ×5 | **POISON toàn bộ** |

**Không ứng viên nào mang bitmask defect.**

### 3.2 Bằng chứng mạnh hơn: hardware tự phân loại

Phép đọc `TPC_UNIT` cho GPC0 phát hiện **mã poison khác nhau**:

| Đơn vị | Poison | Giải mã (`dev_pri_ringstation_sys.h`) | Nghĩa |
|---|---|---|---|
| GPC0 TPC0–4, offset +000 | `0xBADF5040` | `FECS_PRI_CLIENT_ERR` | TPC có mặt, offset không map |
| **GPC0 TPC5, mọi offset** | **`0xBADF1300`** | **`FECS_PRI_FLOORSWEEP`** | **TPC bị floorsweep** |
| GPC3/4/5 | `0xBADF2023/24/25` | `FECS_PRI_ORPHAN` | GPC không tồn tại |

> **Hardware phân biệt rõ ba trạng thái: có mặt / floorswept / không tồn tại.**
>
> TPC5 nhận nhãn **`FLOORSWEEP`**, không phải `ORPHAN`. Tức **TPC5 có mặt trong thiết kế silicon nhưng bị loại khỏi cấu hình.**

### 3.3 Đây là câu trả lời cho Q2, và nó có hai mặt

| Mặt | Nội dung |
|---|---|
| **Tích cực** | TPC5 **không phải orphan**. Nó tồn tại trong silicon, không phải vùng địa chỉ trống. Việc "cắt transistor" bị **giảm khả năng**. |
| **Tiêu cực** | `FLOORSWEEP` là **trạng thái cấu hình**, không phải **kết quả kiểm định**. Nó nói "bị loại khỏi cấu hình", KHÔNG nói "hỏng" cũng KHÔNG nói "tốt". |

### 3.4 Phân loại theo ba mức đề bài yêu cầu

| Mức | Định nghĩa | Áp dụng cho TPC5 |
|---|---|---|
| **defective-marked** | Có cờ nói TPC hỏng | ❌ **Không có cờ nào tìm được** |
| **disabled-not-defective-marked** | Bị tắt, không có cờ hỏng | ✅ **ĐÚNG MÔ TẢ NÀY** |
| **unknown** | Không đủ dữ liệu | ⚠️ Đúng một phần: thiếu dữ liệu chất lượng |

> ## **PHÂN LOẠI: `disabled-not-defective-marked`**
>
> TPC5 bị tắt bởi fuse (`0x021C38` bit 5), **không** có cờ defective nào tìm thấy, và hardware gắn nhãn `FLOORSWEEP` (không phải `ORPHAN`).
>
> **Lưu ý giới hạn:** "không có cờ defective" ≠ "không defective". Có thể cờ đó tồn tại ở nơi chưa dò được (vùng fuse chưa đặt tên, OTP riêng, dữ liệu SEC2). Kết luận đúng là: **trong phạm vi đã dò — fuse, GR, 5 ứng viên, header open-source — không có bằng chứng defective.**

---

## 4. Q3 — Silicon có chạy được? → **CHƯA BIẾT**

### 4.1 Điều đã biết

| Bằng chứng | Suy ra |
|---|---|
| `FECS_PRI_FLOORSWEEP` ≠ `ORPHAN` | TPC5 **có** trong thiết kế |
| GPC0 TPC0–4 hoạt động bình thường | GPC0 nói chung khỏe mạnh |
| `GPC_UNIT(0,0x0000)` = `0x8700029F` = GPC1/2 | GPC0 block **không dị dạng** so với hai GPC kia |
| GPC0 có 5/6 TPC hoạt động | không phải GPC bị loại hàng loạt |

### 4.2 Điều chưa biết — và tại sao không biết

| Câu hỏi | Vì sao chưa trả lời được |
|---|---|
| TPC5 có transistor vật lý? | Không có ảnh die; không có FIB-SEM; không có cách đọc từ host |
| TPC5 có lỗi chức năng? | **Không thể kiểm mà không bật** — mà bật là ghi register (bị cấm) |
| TPC5 hỏng do đâu? | Không có dữ liệu wafer/test log của NVIDIA |

### 4.3 Suy luận thống kê — nêu rõ đây là suy luận, không phải đo

Với 34 SM hoạt động ổn định và chỉ 1 TPC bị tắt:

- Nếu TPC5 **defective thật** → đây là một die bị lỗi cục bộ, được cứu bằng cách tắt 1 TPC. Hợp lý về mặt sản xuất.
- Nếu TPC5 **tốt nhưng bị tắt vì phân hạng** → CMP 40HX được cắt xuống 34 SM một cách có chủ ý.

**Cả hai đều phù hợp với dữ liệu hiện có.** Không có dữ liệu nào phân biệt được.
Đáng chú ý: `STATUS_OPT_TPC_GPC0 = 0x20` chỉ tắt **một** TPC ở **một** GPC, không theo pattern đối xứng (như TU104 #187 tắt TPC0 ở **cả năm** GPC — rõ ràng là cắt cấu hình).

**Nhưng:** CMP 40HX là SKU duy nhất dùng TU106 với 34 SM. RTX 2060 Super / 2070 dùng 34 SM **cũng vậy** (TU106-410/400). Nếu 34 SM là cấu hình chuẩn của một SKU TU106, thì việc tắt 1 TPC có thể là **chuẩn sản phẩm**, không phải cứu die lỗi.

→ **Không kết luận được. Cần dữ liệu từ nhiều card CMP 40HX để so sánh.**

---

## 5. Q4 — Có cách bật an toàn? → **KHÔNG CÓ**

### 5.1 Các đường lý thuyết

| Đường | Cơ chế | Đánh giá |
|---|---|---|
| **`CTRL_OPT_TPC_GPC0`** @ `0x021838` | Software override — ghi bit để bật TPC | **Hiện = 0**, nên về lý thuyết có chỗ để ghi. **Nhưng đây là ghi register — bị cấm tuyệt đối.** Chưa ai chứng minh ghi vào đây bật được TPC bị fuse tắt |
| **`OPT_FEATURE_FUSES_OVERRIDE_DISABLE`** @ `0x0213F0` | Nếu = 1 thì override bị khoá | **Hiện = 0** → override **không** bị khoá. Đây là điều kiện *cần* nhưng **không đủ** |
| Patch GSP-RM | Sửa `tpcMask` trong static info | Cần patch firmware — **bị cấm**; và T8 đã chứng minh GSP **chỉ xoá** bit, không có writer nào *đặt* bit |
| Patch driver | Bỏ qua `floorsweepingMasks.tpcMask` | Không giải quyết: hardware vẫn ở 17 TPC, chỉ làm hỏng đồng bộ |
| Đọc fuse mask chuẩn | — | Không có tác dụng, chỉ đọc |

### 5.2 Đánh giá rủi ro nếu ghi `CTRL_OPT_TPC_GPC0`

**Phân tích lý thuyết, KHÔNG thực hiện:**

| Rủi ro | Mức | Lý do |
|---|---|---|
| TPC5 defective thật → treo GPU / sai kết quả tính toán | **CAO** | Nếu fuse tắt vì lỗi silicon, bật lại đưa đơn vị hỏng vào đường tính toán |
| Gây lỗi ECC / sai số im lặng | **CAO** | Compute không có cách phát hiện kết quả sai ở tầng ứng dụng |
| Mất ổn định driver | TRUNG BÌNH | RM được cấu hình cho 17 TPC; số TPC thay đổi runtime có thể phá giả định |
| Không khôi phục được | TRUNG BÌNH | Cần biết cách khôi phục giá trị gốc; fuse là nguồn, không phải register |
| Brick card | **THẤP-TRUNG BÌNH** | Register override thường reset được, nhưng chưa kiểm chứng trên TU106 |
| Hỏng vĩnh viễn silicon | **THẤP** | Ghi register không phá transistor |

### 5.3 Kết luận Q4

> **Không có cách bật TPC5 nào được chứng minh là an toàn.**
>
> Điều kiện *cần* đã thoả (`OPT_FEATURE_FUSES_OVERRIDE_DISABLE = 0`), nhưng:
> - Chưa ai chứng minh ghi `CTRL_OPT_TPC_GPC0` bật được TPC đã fuse tắt
> - TPC5 có thể defective — không có cách biết trước khi bật
> - Không có cờ defective để đọc trước khi quyết định
>
> **Với thông tin hiện có, bật TPC5 là đánh cược mù.** Rủi ro cao nhất là **sai kết quả tính toán mà không báo lỗi** — điều này tệ hơn nhiều so với việc có ít SM hơn.

---

## 6. TỔNG KẾT PHÂN LOẠI

```
┌─────────────────────────────────────────────────────────┐
│  Q1  Fuse tắt TPC5?        →  CÓ.   PROVEN.            │
│      (0x021C38 bit5, RM 0x1F, GR 5 TPC — ba nguồn khớp) │
│                                                          │
│  Q2  Defective marked?     →  KHÔNG TÌM THẤY CỜ.        │
│      Phân loại: disabled-not-defective-marked            │
│      Hardware nhãn: FECS_PRI_FLOORSWEEP (≠ ORPHAN)      │
│                                                          │
│  Q3  Silicon chạy được?    →  CHƯA BIẾT.                │
│      Không thể kiểm mà không bật. Không có ảnh die.     │
│                                                          │
│  Q4  Bật an toàn?          →  KHÔNG CÓ CÁCH ĐÃ CHỨNG MINH│
│      Điều kiện cần thoả, điều kiện đủ chưa ai chứng minh│
└─────────────────────────────────────────────────────────┘
```

### 6.1 Một câu trả lời cho "phân hạng hay defective"

**Không phân biệt được bằng dữ liệu hiện có.**

Dữ liệu ủng hộ **phân hạng sản phẩm** hơn:
- Hardware nhãn `FLOORSWEEP`, không phải `ORPHAN` → TPC5 có mặt trong silicon
- Chỉ tắt 1 TPC ở 1 GPC, không theo pattern đối xứng
- `OPT_FEATURE_FUSES_OVERRIDE_DISABLE = 0` → override không bị khoá
- CMP 40HX là SKU 34 SM, có thể là cấu hình chuẩn

Dữ liệu **không loại trừ** defective:
- Không có cờ defective **không có nghĩa** là không defective
- Fuse có thể tắt TPC5 vì nó hỏng, mà không ghi cờ riêng
- Không có FIB/ảnh die để chứng minh transistor tồn tại

**Kết luận đúng mức:** `disabled-not-defective-marked` — bị tắt, không có dấu hiệu defective, **nhưng không chứng minh được là tốt**.

---

## 7. ĐIỀU KIỆN ĐỂ TIẾN XA HƠN (không thực hiện trong nhiệm vụ này)

| # | Phép kiểm | Trả lời được | Chi phí / rủi ro |
|---|---|---|---|
| 1 | So fuse `0x021C38` trên **nhiều card CMP 40HX khác** | Phân hạng vs defective | Thấp — read-only. **Nếu mọi card đều `0x20` → phân hạng. Nếu khác nhau → defective ngẫu nhiên.** |
| 2 | So với RTX 2060 Super (TU106-410, cũng 34 SM) | 34 SM có phải chuẩn SKU | Thấp — read-only |
| 3 | Đọc `0x021C38` sau cold boot nhiều lần | Fuse vs shadow | Thấp — read-only |
| 4 | Ghi `CTRL_OPT_TPC_GPC0` bit 5 | Silicon có chạy | **CAO — vượt giới hạn, không khuyến nghị** |
| 5 | Ảnh die / FIB-SEM | Transistor có tồn tại | Rất cao — cần phá hủy card |

**Phép #1 là phép kiểm rẻ nhất và có sức phân biệt cao nhất.** Nếu có thêm card CMP 40HX, đọc duy nhất một register sẽ trả lời được câu hỏi cốt lõi.

---

## 8. KHÔNG ĐƯỢC KẾT LUẬN

| Sai | Đúng |
|---|---|
| "TC5 defective" | Không có cờ defective nào; không chứng minh được |
| "TC5 chắc chắn tốt, chỉ bị khoá" | Hardware nói `FLOORSWEEP` — trạng thái cấu hình, không phải chất lượng |
| "Bật `CTRL_OPT_TPC_GPC0` là an toàn vì override không bị khoá" | `OPT_FEATURE_FUSES_OVERRIDE_DISABLE=0` chỉ là điều kiện **cần** |
| "Cắt transistor" | `FLOORSWEEP` ≠ `ORPHAN` → TPC5 **có mặt** trong silicon |
| "Grep không thấy ⇒ không có register defect" | Chỉ kết luận "không có trong 5 ứng viên + header open-source" |
| "34 SM nghĩa là die lỗi" | 2060 Super cũng 34 SM — có thể là chuẩn SKU |

---

## 9. Artifact

| File | Nội dung |
|---|---|
| `TPC5_RAW_FUSE_COMPARISON.md` | Xác minh fuse + đối chiếu RM + hardware GR |
| `TPC5_DEFECT_REGISTER_EVIDENCE.md` | 5 ứng viên + đối chiếu TU104 #187 + mã poison |
| `TPC5_RECOVERABILITY_VERDICT.md` | File này |

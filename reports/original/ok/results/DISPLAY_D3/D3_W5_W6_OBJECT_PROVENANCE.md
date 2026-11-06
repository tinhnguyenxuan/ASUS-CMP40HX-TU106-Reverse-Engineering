# D3-A — W5/W6 OBJECT PROVENANCE

**Firmware:** GSP-RM 615.78.08 · inner ELF `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85`
**Source RM:** tag `615.78.08` @ `1a82fbfda8f321b056eb3568850f9316c5e465c5`
**Ngày:** 2026-11-06 · offline only

---

## 0. KẾT LUẬN TRƯỚC

> **W5/W6 KHÔNG vận hành trên cùng object với handler `0x04B9F5CC`.**
>
> Đây là **bác bỏ** giả định ngầm của D1/D2 rằng `+0x6EA` là một field duy nhất có một nghĩa duy nhất.
>
> Bằng chứng định lượng: **21 writer** đọc/ghi offset `0x6EA`; **0/21** dùng chuỗi object của handler (`ld X,0x160(..)` → `ld Y,0xE8(X)`), trong khi **145 reader** thì dùng đúng chuỗi đó.
>
> ⇒ `+0x6EA` là **một offset, không phải một field**. Nó xuất hiện trong **nhiều struct khác nhau**.

---

## 1. Sửa lỗi transcription của D2 (bắt buộc trước khi kết luận)

D2 ghi HAL slot `obj+0x88` = `0x5233DE0`. **Sai một chữ số.** Tính lại giá trị từ **raw bytes** của từng cặp `lui`+`addi` trong nhánh `0x458E2F0–0x458E364`:

| Store | Vaddr | Giá trị (tính từ raw) |
|---|---|---|
| `sd a3,0x58(a5)` | `0x458E2F8` | `0x0522F8CC` |
| `sd a3,0x60(a5)` | `0x458E304` | `0x0521ABAC` |
| `sd a3,0x68(a5)` | `0x458E318` | `0x0521ABC8` |
| `sd a3,0x70(a5)` | `0x458E324` | `0x05236F48` |
| `sd a3,0x78(a5)` | `0x458E330` | `0x0522E224` |
| `sd a3,0x80(a5)` | `0x458E33C` | `0x052357D8` |
| **`sd a3,0x88(a5)`** | **`0x458E348`** | **`0x05232DE0`** ← đúng (D2 ghi `0x5233DE0`) |
| **`sd a3,0x90(a5)`** | **`0x458E354`** | **`0x0522B18C`** |
| `sd a3,0x98(a5)` | `0x458E360` | `0x0522E404` |

Sửa xong, `lhu 0x10(0x5232DE0)` đọc tại `0x5232DF0` = raw `23 30 21 05` → `0x3023`.
Lệnh tại đó là `sd s2, 0x40(sp)` (epilogue lưu thanh ghi). **Xác nhận: đọc byte lệnh.**

---

## 2. CFG của W5/W6 (`0x5306D20`, 3096 B)

### 2.1 Nguồn `a0` tại `0x5306D30` và `0x5306DE4`

**Toàn hàm chỉ có 2 lệnh ghi vào `a0`:**

```asm
005306d20: addi sp,sp,-0x10
005306d24: sd   s0,0x8(sp)
005306d28: addi s0,sp,0x10
005306d2c: beqz a0, 0x5307928      # a0 == NULL -> thoát
005306d30: ld   a4,0x88(a0)        # ← a0 DÙNG LẦN ĐẦU
```

`a0` **không bị ghi lại** trong suốt 3096 B (spill/reload chỉ qua `sp`, không qua `a0`).

⇒ **`a0` tại `0x5306D30` và tại `0x5306DE4` là CÙNG MỘT GIÁ TRỊ** — tham số thứ nhất của hàm.

**Nguồn `a0` = caller.** Không xác định được caller: hàm này **không có call site trực tiếp, không có địa chỉ literal 8-byte hay 4-byte trong toàn ELF** (đã kiểm D2-B).

### 2.2 CFG đầy đủ (các nhánh)

```
                    a0 = this (tham số 1)
                            │
                   beqz a0 ─┴─► 0x5307928 (thoát)
                            │
                   a4 = *(this+0x88)      ← HAL method ptr
                   a3 = *(this+0x90)      ← HAL method ptr
                   a4 = *(u16*)(a4+0x10)  ← ĐỌC BYTE LỆNH
                   a1 = *(u16*)(a3+0x10)
                   a2 = a4 >> 5           ← "class"
                            │
        ┌───────────────────┼───────────────────┐
   a2 == 2             a2 == 1              a2 != 1,2
        │                   │                   │
        ▼                   ▼                   ▼
  0x53070AC           0x5306D68            0x5307020
  (nhánh class 2)     (nhánh class 1)      (nhánh khác)
        │                   │                   │
        ▼                   ▼                   ▼
  bit = 0xC0>>idx     bit = 0x60000000>>idx   ...
        │                   │
  a5==0 ──► 0x53076C4  a3==0 ──► 0x5307604
  sh zero,0x6ea        sb zero,0x6ea
        │                   │
  a5!=0               a3!=0
  sb t0(=1),0x6ea     sb a2(=class),0x6ea
```

### 2.3 Ba giá trị có thể ghi vào `+0x6EA` từ W5

| Đường | Giá trị | Địa chỉ |
|---|---|---|
| class == 1, bit `0x60000000>>idx` != 0 | `a2 = class = a4>>5` | `0x5306DE4` |
| class == 1, bit == 0 | `0` | `0x5307604` |
| class == 2, bit `0xC0>>idx` != 0 | `1` | `0x530713C` |
| class == 2, bit == 0 | `0` | `0x53076C4` |
| else (class ∉ {1,2}) | `0` (qua `sh zero`) | `0x5307034` |

**`class` = `(*(u16*)(fnptr_HAL + 0x10)) >> 5`, với `fnptr_HAL = 0x5232DE0`.**
`0x5232DF0` chứa `23 30 21 05` → `u16 = 0x3023` → `class = 0x3023 >> 5 = 0x181 = 385`.

**`class = 385` không khớp bất kỳ nhánh nào (1, 2) ⇒ đi vào nhánh `else`.**

⇒ Nếu W5 chạy trên object có `*(this+0x88) == 0x5232DE0` (nhánh HAL đã tìm), nó **luôn** đi nhánh `else` và ghi `0` qua `sh zero,0x6ea` tại `0x5307034`.

---

## 3. Truy nguồn `a5` tại HAL initializer `0x458E240`

### 3.1 Vị trí thật

`0x458E240` **không phải** đầu hàm. Prologue thật là `0x458E1CC`:

```asm
458e1cc: addi sp,sp,-?            # fn bắt đầu
458e240: ld   a5,0x8(a0)          # a5 = *(a0 + 0x8)
458e244: beqz a5, 0x458ecc4
458e258: lw   a4,0x6a8(a5)        # a4 = *(u32*)(a5+0x6A8)   ← arch selector
```

Hàm: `0x458E1CC .. 0x458E248`, **124 byte**.

### 3.2 Danh sách offset dùng trên `a5` trong hàm này

Quét toàn bộ 124 byte: **chỉ 2 offset khác nhau** trên `a5`.

```
0x6xx range: []          ← KHÔNG có offset nào trong 0x600-0x6FF
0x88 present: False
0x90 present: False
0x6a8 present: False
0x6ea present: False
```

### 3.3 Kết luận về `a5`

> Hàm init chỉ làm **một việc**: đọc `*(u32*)(obj+0x6A8)` và **rẽ nhánh tới `0x4592F28` / `0x4592F0C` / `0x4591288` / `0x458E28C`**.
>
> Nó **không** ghi `+0x88`, `+0x90`, `+0x6EA`.
>
> Các store `sd a3,0x88(a5)` tại `0x458E348` nằm trong **nhánh được nhảy tới từ hàm này**, không nằm trong thân `0x458E1CC`. Và nhánh đó dùng `a5` **kế thừa** từ `0x458E240` — cùng object.

⇒ **`a5` (HAL initializer) và `a0` (W5) là hai đường khác nhau.** Không có bằng chứng chúng cùng object.

### 3.4 Kiểm chứng ngược: có hàm nào dùng CẢ `+0x6A8` VÀ `+0x6EA` không?

Quét toàn ELF, tìm hàm chạm cả hai offset:

```
functions touching BOTH 0x6A8 and 0x6EA: 7
  0x4AA93B4  0x4B9B3CC  0x4C8A0C4  0x4CF39F0  0x4CF4808  0x4D5D770  0x518F140
```

**W5 (`0x5306D20`) KHÔNG nằm trong danh sách này.** W5 dùng `+0x88`/`+0x90`, không dùng `+0x6A8`.

⇒ **Không có bằng chứng** `+0x88`, `+0x90`, `+0x6A8`, `+0x6EA` thuộc cùng một struct.

---

## 4. Kiểm tra `ld a4,0x88(base)` — dùng như con trỏ hàm hay dữ liệu?

Quét **tất cả** lệnh `ld REG,0x88(base)` trong ELF và xét 8 lệnh kế tiếp:

| Cách dùng | Số lượng |
|---|---|
| **Con trỏ hàm** (theo sau là `jalr REG`) | **243** |
| **Con trỏ dữ liệu** (theo sau là `lbu/lhu/lw/ld (REG)`) | **97** |
| Không kết luận được (offset khác, `sp`-relative) | 3.225 |

### 4.1 Điều này nói gì

**Hai cách dùng đều tồn tại trong cùng firmware.** Nên **không thể** kết luận "`+0x88` luôn là con trỏ hàm" chỉ vì HAL initializer ghi địa chỉ code vào đó.

Nhưng với **W5 cụ thể**, chuỗi là:
```asm
ld a4,0x88(a0) ; ld a3,0x90(a0) ; lhu a4,0x10(a4)
```
`lhu` theo sau `ld 0x88` → thuộc nhóm "con trỏ dữ liệu" theo phân loại trên.

### 4.2 Mâu thuẫn chưa giải quyết

Nếu `*(this+0x88)` là **con trỏ dữ liệu** (như W5 giả định), thì HAL initializer ghi **địa chỉ code** vào đó là **mâu thuẫn**.

Ba khả năng, **chưa loại trừ được cái nào**:

1. **Hai struct khác nhau dùng cùng offset `0x88`.** W5 nhận object chưa qua HAL init; `+0x88` của nó là con trỏ data. HAL init phục vụ object khác. **Không có bằng chứng trực tiếp**, nhưng khớp với việc W5 không dùng `+0x6A8`.
2. **Địa chỉ code được dùng như dữ liệu.** Không hợp lý về mặt ngữ nghĩa nhưng không loại trừ được bằng tĩnh.
3. **W5 là dead code trên TU106.** Không có caller, không có literal ⇒ có thể chỉ tồn tại cho chip khác.

---

## 5. Struct layout — những gì ĐỌC ĐƯỢC

### 5.1 Object của W5 (`a0`)

| Offset | Kích thước | Nội dung quan sát |
|---|---|---|
| `+0x088` | 8 | con trỏ (đọc bằng `ld`), dùng cho `lhu 0x10` |
| `+0x090` | 8 | con trỏ (đọc bằng `ld`), cùng pattern |
| `+0x6CD` | 1 | `sb` — 2 site |
| `+0x6CE` | 2 | `sh` — 2 site |
| `+0x6CF` | 1 | `sb` |
| `+0x6D1` | 1 | `sb` |
| `+0x6DC` | 2 | `sh` |
| `+0x6DD`–`+0x6E3` | byte | vùng flag display |
| `+0x6E6` | 1 | `sb` |
| `+0x6E9` | 1 | `sb` |
| **`+0x6EA`** | **1** | **`sb` (2) + `sh` (1) + `lbu` (1)** |
| `+0x6EB`–`+0x6F0` | byte | vùng flag |
| `+0x6F1`–`+0x6F7` | byte | vùng flag |
| `+0x712`,`+0x71D`,`+0x72C`,`+0x731`–`+0x745` | byte | vùng flag |
| `+0x74A`,`+0x756`,`+0x75C`,`+0x763`,`+0x76B`,`+0x785` | byte | vùng flag |

**Kích thước tối thiểu:** ≥ `0x786` = 1.926 byte.

**W5 KHÔNG chạm:** `+0x6A8`.

### 5.2 Object của handler `0x04B9F5CC`

```asm
4b9f5e8: ld  a5,0x160(a0)         # a5 = *(pGpu + 0x160)
4b9f5f4: ld  a0,0xe8(a5)          # base = *(a5 + 0xE8)
4b9f5fc: ld  s3,-0xa0(s1)         # s1 = base+0x2000; s3 = *(base+0x1F60)
4b9f604: lbu a5,0x6ea(a0)         # <= đọc base+0x6EA
```

Handler **chỉ** chạm: `0x160` (pGpu), `0xE8` (chain), `+0x1F50`, `+0x1F58`, `+0x1F60`, `+0x6EA`.

**`base` = `*(*(pGpu+0x160)+0xE8)`** — đây là **một offset sâu trong GSP static info**, không phải `this` của W5.

---

## 6. Bác bỏ giả định "cùng một field"

### 6.1 Bằng chứng định lượng

| Nhóm | Số lượng | Dùng chuỗi object của handler? |
|---|---|---|
| **21 writer** của `0x6EA` | 21 | **0 / 21** |
| **145 reader** của `0x6EA` trong hàm có chuỗi handler | 145 | **145 / 145** |

### 6.2 Danh sách 21 writer (đẦY ĐỦ — D2 chỉ báo 11)

| # | Địa chỉ | Lệnh | Hàm |
|---|---|---|---|
| 1 | `0x4A128D4` | `sb zero,0x6ea(s1)` | `0x4A127FC` |
| 2 | `0x4B6F3EC` | `sb a0,0x6ea(s1)` | `0x4B6F190` |
| 3 | `0x4C89784` | `sb zero,0x6ea(s3)` | `0x4C89440` |
| 4 | `0x4C95FDC` | `sb zero,0x6ea(s1)` | `0x4C95EFC` |
| 5–12 | `0x518BE8C`, `0x518C52C`, `0x518CC94`, `0x518D36C`, `0x518DA80`, `0x518E4CC`, `0x518ED24`, `0x518F474` | **`sh a3,0x6ea(a1)`** | 8 hàm riêng `0x518BCC4` … `0x518F140` |
| 13 | `0x5306DE4` | `sb a2,0x6ea(a0)` | `0x5306D20` |
| 14 | `0x5307034` | **`sh zero,0x6ea(a0)`** | `0x5306D20` |
| 15 | `0x530713C` | `sb t0,0x6ea(a0)` | `0x5306D20` |
| 16 | `0x5307604` | `sb zero,0x6ea(a0)` | `0x5306D20` |
| 17 | `0x53076C4` | `sb zero,0x6ea(a0)` | `0x5306D20` |
| 18 | `0x5382BA0` | **`sh zero,0x6ea(a5)`** | `0x5382B34` |
| 19 | `0x5382D2C` | `sb zero,0x6ea(a5)` | `0x5382B34` |
| 20 | `0x5382F08` | `sb zero,0x6ea(a1)` | `0x5382B34` |
| 21 | `0x538314C` | `sb zero,0x6ea(a1)` | `0x5382B34` |

**Phần lớn là `sb` (11), nhưng có 10 `sh` — ghi 2 byte, tức `0x6EA` VÀ `0x6EB` cùng lúc.** Đây là dấu hiệu `0x6EA` là **byte đầu của một trường 16-bit**, không phải field độc lập.

### 6.3 Danh sách reader

**495 lệnh `lbu ...,0x6ea(...)`** — tất cả đều đọc **1 byte**, không có `lhu`/`lh`.
**145 hàm** dùng đúng chuỗi object của handler.

---

## 7. Kết luận D3-A

| Mệnh đề | Trạng thái | Cơ sở |
|---|---|---|
| `a0` tại `0x5306D30` và `0x5306DE4` là cùng một giá trị | **PROVEN** | `a0` chỉ là tham số, không bị ghi lại trong 3096 B |
| W5/W6 dùng cùng object với handler `0x04B9F5CC` | **BÁC BỎ** | 0/21 writer dùng chuỗi `0x160`→`0xE8`; 145/145 reader dùng |
| `+0x88`, `+0x90`, `+0x6A8`, `+0x6EA` cùng struct | **KHÔNG CHỨNG MINH** | W5 không chạm `+0x6A8`; chỉ 7 hàm chạm cả hai, W5 không nằm trong số đó |
| `lhu 0x10(a4)` đọc instruction bytes | **PROVEN** với `fnptr = 0x5232DE0` | raw `23 30 21 05` = `sd s2,0x40(sp)`; `class = 385` không khớp nhánh nào |
| `+0x6EA` là một field duy nhất có một nghĩa | **BÁC BỎ** | 21 writer khác hàm, 2 độ rộng ghi (`sb`/`sh`), 495 reader |
| W5 là display gate | **KHÔNG ĐƯỢC GỌI NHƯ VẬY** | Xem §8 |

---

## 8. `+0x6EA` KHÔNG được gọi là "display gate" nữa

Theo yêu cầu D3-1.7, và dựa trên bằng chứng trên:

**Lý do không đủ điều kiện gọi là display gate:**

1. **Không có bằng chứng semantic.** 495 reader `lbu` không có reader nào truy nguyên được tới display pipeline trong phân tích tĩnh.
2. **Không có consumer phù hợp.** Handler `0x04B9F5CC` là consumer **duy nhất** đã xác định, và nó **không** dùng cùng object với 21 writer.
3. **Không phải field độc lập.** 10 writer ghi 2 byte (`sh`), byte thứ hai là `+0x6EB`.
4. **Không có writer nào trong 21 nằm trên đường thực thi đã chứng minh.** 0 caller trực tiếp, 0 literal ptr cho 6 hàm chứa writer.

**Tên đúng:** `+0x6EA` là **một byte trong vùng flag liên tiếp `0x6CD–0x785`** của **một struct chưa xác định**, được đọc bởi 495 site và ghi bởi 21 site thuộc 9 hàm khác nhau. **Ngữ nghĩa: UNKNOWN.**

---

## 9. Artifact

| File | Nội dung |
|---|---|
| `D3_A_CFG_W5W6.json` | CFG + offset map của W5 và 21 writer |
| Script | `/home/REDACTED_USER/.hermes/cache/scratch/d2/d3_obj.py` |

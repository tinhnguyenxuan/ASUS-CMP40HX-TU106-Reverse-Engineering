# D3-D — KHẢ THI CHẨN ĐOÁN DISPLAY

**Ngày:** 2026-11-06 · Phân tích lý thuyết · **Không triển khai, không chạy**

---

## 0. KẾT LUẬN

> **Có 3 kênh chẩn đoán khả thi, xếp theo rủi ro tăng dần. Chỉ kênh #1 an toàn và nằm trong phạm vi.**
>
> Kênh #2 và #3 cần quyết định riêng của người dùng vì vượt giới hạn D3 (sửa/chạy module).
>
> **Không kênh nào trả lời được câu C** (PDISP/SOR/PHY vật lý) mà không có thiết bị đo.

---

## 1. Ba câu hỏi độc lập — trạng thái bằng chứng

| # | Câu hỏi | Trạng thái | Bằng chứng hiện có |
|---|---|---|---|
| **A** | Vì sao host RM từ chối display? | **PROVEN** | `0x021C04=1` → `gpuFuseSupportsDisplay_GM107=FALSE` → `kern_disp.c:444` `NV_ERR_NOT_SUPPORTED` → `gpuRemoveMissingEngineClasses` → dmesg `Cannot find any crtc or sizes` |
| **B** | GSP có nhận diện Display IP trên CMP 40HX? | **CHƯA ĐO** | Handler `0x04B9F5CC` chưa bao giờ chạy. Control `0x20800A4B` bị `RMCTRL_FLAGS_INTERNAL` chặn (D3-C) |
| **C** | PDISP/SOR/PHY hoạt động trên silicon + PCB? | **TÁCH LÀM 3 — xem D3-E** | **Thiết kế: PROVEN có đường.** Lanelist GENCAD: GPU pin → tụ coupling → J1(DP)/J5(DVI)/J10(HDMI). **Populate: CHƯA BIẾT** (`CMP population UNKNOWN`). **Silicon SOR/PHY: CHƯA CHỨNG MINH** |

### 1.1 Ba mệnh đề KHÔNG suy ra nhau

```
A (host từ chối)  ──✗──►  B (GSP có thấy display?)
       │
       └──✗──►  C (PHY/PCB hoạt động?)
```

| Suy luận sai | Vì sao sai |
|---|---|
| "A đúng ⇒ GSP cũng không thấy display" | A là gate host đọc **fuse**. B là gate GSP đọc **struct runtime**. Hai nguồn khác nhau |
| "A đúng ⇒ hardware hỏng" | Fuse là **cấu hình sản phẩm**, không phải lỗi vật lý. `TU106-100-A1` là die đầy đủ |
| "Fuse tắt ⇒ PHY không được cấp nguồn" | Chưa có bằng chứng. Fuse gate chặn **ở phần mềm** trước khi chạm bất kỳ register PHY nào |
| "B sai ⇒ C sai" | Không liên quan |

---

## 2. Kênh chẩn đoán #1 — đọc metadata card (AN TOÀN, TRONG PHẠM VI)

### 2.1 Phép đo

| Phép | Lệnh | Trả lời |
|---|---|---|
| Xác nhận `0x021C04` | Đọc BAR0 offset `0x21C04` (đã làm D1) | A |
| Xác nhận gate đã chạy | `dmesg \| grep -c "Cannot find any crtc"` | A |
| Xác nhận class bị gỡ | `nvidia-smi --query-gpu=display_active,display_attached` | A |
| Kiểm PCB (ảnh) | `CMP40HX_PORTS_PHOTO_ANNOTATED.jpg` | C (một phần) |
| Kiểm registry key SMC | `/proc/driver/nvidia/params` (đã làm D2-G) | loại trừ W4 |

### 2.2 Giá trị

- **Củng cố A** (đã đủ bằng chứng, không cần thêm)
- **Thu hẹp C**: nếu ảnh cho thấy có connector DP/HDMI và linh kiện → C khả thi hơn; nếu không có → C gần như bị bác bỏ

### 2.3 Rủi ro

**Bằng không.** Tất cả read-only.

---

## 3. Kênh #2 — module kernel chẩn đoán đọc `ipVersion`

### 3.1 Kiến trúc

Xem `D3_KERNEL_INTERNAL_QUERY_PATH.md` §5.1.

```c
// KHÔNG PHẢI CODE ĐỂ CHẠY — chỉ mô tả đường đi
pRmApi = rmapiGetInterface(RMAPI_GPU_LOCK_INTERNAL);
pRmApi->Control(pRmApi, pGpu->hInternalClient, pGpu->hInternalSubdevice,
                NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION,
                &params, sizeof(params));
```

### 3.2 Cái được

- `params.ipVersion` — trả lời **câu B** trực tiếp
- Nếu `ipVersion == 0` → GSP cũng không thấy display
- Nếu `ipVersion != 0` → GSP **có** thấy display ⇒ gate G3 mở ⇒ nguyên nhân gốc hoàn toàn ở host (fuse)

### 3.3 Rủi ro

| Rủi ro | Mức | Chi tiết |
|---|---|---|
| **Dereference `base` chưa cấp phát** | **CAO** | `base = *(*(pGpu+0x160)+0xE8)`. Nếu display chưa init, cấu trúc này có thể NULL/chưa cấp ⇒ **kernel oops** |
| **Deadlock** | TRUNG BÌNH | Phải gọi ngoài context đã giữ GPU lock |
| `params` rác | THẤP | Zero trước khi gọi |
| Tác dụng phụ handler | **BẰNG KHÔNG** | 1 store vào output, callback 0 store (D2-D) |

### 3.4 Vì sao rủi ro #1 không loại trừ được

Firmware **stripped, 0 symbol**. Không xác định được tĩnh ai cấp `*(pGpu+0x160)`.
Trong RM open source, `pGpu+0x160` không map được sang field có tên (GSP-FW struct layout không công bố).
⇒ **Không chứng minh được an toàn bằng phân tích offline.**

### 3.5 Trạng thái

**NGOÀI PHẠM VI D3** — yêu cầu cấm "sửa hoặc chạy module trên máy GPU". Cần quyết định riêng.

---

## 4. Kênh #3 — đo trực tiếp PDISP/SOR/PHY

### 4.1 Vì sao BLOCKED

| Cần | Có không |
|---|---|
| Địa chỉ `NV_PDISP_*` register cho Turing | **KHÔNG** — `swref/published/turing/tu102/` chỉ có 37 file, không có `dev_disp.h`. Cây `disp/v05_02/` chỉ là header chỉ mục 33 dòng |
| Địa chỉ `NV_SOR_*`, `NV_DP_LINK_*` | **KHÔNG** — cùng lý do |
| Boardview CMP 40HX | **KHÔNG** trong workspace |
| Thiết bị đo tín hiệu (scope/analyzer) | **KHÔNG** |
| Quyền ghi MMIO để thử bật PHY | **BỊ CẤM** |

### 4.2 Điều duy nhất làm được: ảnh PCB

`input/ASTRA_CMP40HX_HANDOFF/02_PCB_PHOTOS/ANNOTATED/CMP40HX_PORTS_PHOTO_ANNOTATED.jpg`

**Chưa phân tích.** Đây là phép kiểm **rẻ nhất và duy nhất** cho câu C hiện có.

Nếu ảnh cho thấy **có** connector DP/HDMI + linh kiện AC-coupling → C còn khả năng.
Nếu **không có** connector nào → C bị bác bỏ mạnh (không thể xuất hình vật lý dù silicon tốt).

---

## 5. Bảng tổng hợp khả thi

| Kênh | Trả lời | Rủi ro | Trong phạm vi D3? | Giá trị |
|---|---|---|---|---|
| **#1 Metadata read-only** | A (củng cố), C (một phần) | **BẰNG KHÔNG** | ✅ **CÓ** | Trung bình |
| **#1b Ảnh PCB** | **C** | **BẰNG KHÔNG** | ✅ **CÓ** | **CAO — chưa làm** |
| **#2 Module kernel** | **B** | **CAO** (oops) | ❌ **KHÔNG** | **CAO** cho B |
| **#3 Register PHY** | **C** | — | ❌ **KHÔNG** | BLOCKED |

### 5.1 Khuyến nghị thứ tự

1. **#1b — đọc ảnh PCB.** Miễn phí, chưa làm, trả lời một phần câu C.
2. **#1 — củng cố A** (đã đủ, không cần).
3. **#2 — chỉ sau khi người dùng chấp nhận rủi ro oops.**

---

## 6. Điều KHÔNG được kết luận

| Sai | Vì sao |
|---|---|
| "Vì A đúng nên B chắc cũng đúng" | Hai gate độc lập, hai nguồn dữ liệu khác nhau |
| "Vì A đúng nên hardware hỏng" | Fuse ≠ hỏng vật lý |
| "Fuse read-only ⇒ display không bao giờ khôi phục được" | D1 đã sửa: `R-I4R` chỉ nói RM host không ghi. Devinit/SEC2/hardware-latch chưa loại trừ |
| "`+0x6EA` là display gate" | D3-A/D3-B bác bỏ: 21 writer, 0/21 dùng object của handler, 10 writer ghi 2 byte |

---

## 7. Tổng kết D3-D

| Mục | Kết quả |
|---|---|
| Câu A | **PROVEN** — `0x021C04=1` → `kern_disp.c:444` |
| Câu B | **CHƯA ĐO, không đo được bằng read-only** |
| Câu C | **CHƯA CHỨNG MINH** — thiếu địa chỉ register + boardview + thiết bị đo |
| Kênh an toàn còn lại | **Ảnh PCB** (chưa làm) + metadata read-only |
| Kênh trả lời B | Module kernel — **rủi ro oops chưa loại trừ, ngoài phạm vi** |
| Ba câu hỏi tách biệt | **ĐÃ TÁCH** — không suy ra nhau |

# D1-C — `RmDisableDisplay` ANALYSIS

**GSP ELF:** SHA-256 `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85`
**Driver:** 615.78.08 · **Source:** tag `615.78.08` @ `1a82fbfda8f321b056eb3568850f9316c5e465c5`

---

## 1. Kết luận ngắn

| Mệnh đề | Trạng thái | Cơ sở |
|---|---|---|
| `RmDisableDisplay` là **registry key** trong GSP-RM | **PROVEN** | Chuỗi nằm trong blob tên registry key, cạnh `PanelBrightnessLimits`, `RmDisableDispMacro`, `RMEnableSingleHeadMultiDisplay` |
| `RmDisableDisplay` là **producer** của trạng thái display-disabled hiện tại | **BÁC BỎ (cho đường hiện tại)** | Host RM chưa từng gửi lệnh display nào cho GSP — gate fuse chặn ở dòng 444 trước đó |
| Có xref tĩnh tới key này trong ELF | **0 hit** | Ba phương pháp độc lập, xem §2 |
| Key này có tác dụng nếu được set | **SUPPORTED, chưa test** | Tên + vị trí trong blob registry; không xác minh được consumer do ELF stripped |
| Key này đang được set trên CMP 40HX | **KHÔNG** | Không có registry entry từ host; `nvidia-smi -q` không hiện; dmesg không nhắc |

---

## 2. Tìm xref — ba phương pháp, đều âm tính

Chuỗi: `"RmDisableDisplay\x00"` tại file offset `0x9E928` → **vaddr `0x409E928`** (trong `.rm_rodata`, vaddr `0x401d000`, file `0x1d000`, size `0x1e4000`).

### 2.1 Con trỏ 64-bit

```python
pat = struct.pack('<Q', 0x409E928)   # e9 9e 09 04 00 00 00 00
d.find(pat)   # → không có hit nào trong toàn bộ 22.901.568 byte
```
Kết quả: **0 hit** (cả `.rm_data`, `.rm_rodata`, `.rm_text`).

### 2.2 Con trỏ 32-bit

```python
pat = struct.pack('<I', 0x409E928)   # e9 9e 09 04
```
Kết quả: **0 hit**.

### 2.3 `auipc + addi` (RISC-V PC-relative)

Quét toàn bộ `.rm_text` (vaddr `0x4588000`, file `0x588000`, `0x1039000` byte = 272.171.008 byte mã), giải mã từng `AUIPC` và kiểm hai instruction kế tiếp cho `addi rd, rd, imm`:

```python
for i in range(0, len(text)-8, 4):
    w = struct.unpack_from('<I', text, i)[0]
    if (w & 0x7F) != 0x17: continue            # AUIPC
    rd = (w>>7)&0x1F; imm20 = w & 0xFFFFF000
    if imm20 & 0x80000000: imm20 -= 0x100000000
    hi = (tva + i + imm20) & 0xFFFFFFFF
    for j in (4, 8):
        w2 = struct.unpack_from('<I', text, i+j)[0]
        if (w2 & 0x7F) == 0x13 and ((w2>>15)&0x1F) == rd and ((w2>>7)&0x1F) == rd:
            imm = w2>>20
            if imm & 0x800: imm -= 0x1000
            addr = (hi + imm) & 0xFFFFFFFF
            # so với 0x409E928
```
Kết quả: **0 xref** cho cả `RmDisableDisplay` và `RmForceGridDisplayless` (`0x408A2E0`).

### 2.4 Vì sao âm tính — và vì sao nó KHÔNG chứng minh key không tồn tại

GSP tra registry key qua **bảng có chỉ số/hash**, không qua con trỏ chuỗi trực tiếp. Bằng chứng: khi quét `.rm_data` tìm các "run" gồm ≥8 con trỏ 32-bit liên tiếp trỏ vào vùng ảnh, tất cả các bảng tìm được (`0x602924`, `0x91EC34`, `0xBB25B8`, `0xBB2BDC`, `0x13E2968`) đều trỏ tới vùng `0x040xxxxx` — **không** bảng nào trỏ tới `0x0409Exxx`.

⇒ Kết luận đúng đắn: **không có xref tĩnh trực tiếp**. Không được suy thành "key không được dùng".

---

## 3. Phía host — không có đối tác

```
grep -rn "RmDisableDisplay" /home/REDACTED_USER/cmp_build_ogkm/src/          → 0 hit
grep -rn "RM_DISABLE_DISPLAY|DISABLE_DISPLAY" src/nvidia/inc/ src/nvidia/interface/  → 0 hit
grep -rln "RmDisableDisplay" /home/REDACTED_USER/cmp_build_ogkm/             → 0 file
```

Không có hằng số, không có `NV_REG_STR_*`, không có `RMCFG_FEATURE_*` tương ứng trong open-gpu-kernel-modules 615.78.08.

**Ý nghĩa:** `RmDisableDisplay` chỉ có thể được set qua:
1. `NVreg_RegistryDwords=RmDisableDisplay=1` (module param, do người dùng đặt)
2. Registry Windows trong môi trường khác
3. GSP tự đặt dựa trên cấu hình đọc được

Trên target hiện tại: `/proc/driver/nvidia/params` chỉ có `EnableGpuFirmware: 18`, `EnableGpuFirmwareLogs: 2`. **Không có entry `RmDisableDisplay`.**

⇒ **Key này không được set.** Nó không thể là nguyên nhân.

---

## 4. Các key display khác trong blob — cùng tình trạng

| Key | Vị trí | Vai trò suy đoán | Đang set? |
|---|---|---|---|
| `RmForceGridDisplayless` | `0x408A2E0` (ngữ cảnh: `…Not Available\0\0\0Compute\0RmForceGridDisplayless\0\0GRID-Virtual-PC,2.0;Quadro-Virtual-DWS,…`) | Buộc chế độ displayless kiểu GRID | Không |
| `RmDisableDisplay` | `0x409E928` | Tắt display | Không |
| `RmDisableDispMacro` | cạnh trên | Tắt macro display | Không |
| `RMDispLowPowerFeatures` | `0x409Exxx` | Low-power display | Không |
| `RmDispInitLatencyDispclkOptimization` | — | Tối ưu dispclk | Không |

Ngữ cảnh chuỗi `RmForceGridDisplayless` nằm ngay trong danh sách **tên sản phẩm GRID** (`GRID-Virtual-PC,2.0;Quadro-Virtual-DWS,…`) ⇒ đây là feature của dòng vGPU/GRID, **không phải CMP**.

CMP 40HX là physical function, không phải vGPU. `osIsGridSupported(pGpu)` trả `NV_FALSE` (`gpu.c:1947-1952`).

---

## 5. Trả lời trực tiếp câu hỏi B.1

> "Xác định nguồn thực tế của `RmDisableDisplay`."

**Trả lời:** Producer **không xác định được** trong firmware stripped — nhưng **đã chứng minh không cần thiết phải xác định**:

1. Key không được set trên hệ thống này (§3).
2. Đường thực thi chưa bao giờ tới được GSP phần display (§ D1-B §5) — `kdispStatePreInitLocked` return ở dòng 444, trước `NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION`.
3. Ngay cả khi `RmDisableDisplay` được set, nó chỉ có thể **thêm** một gate; gate fuse đã đủ để chặn.

⇒ `RmDisableDisplay` **không phải producer của trạng thái hiện tại**. Đây là kết quả phủ định có bằng chứng, không phải "UNKNOWN".

---

## 6. Điều còn chưa biết (trung thực)

- Consumer thật của `RmDisableDisplay` trong GSP: **không xác định** (ELF stripped, bảng tra gián tiếp).
- Nếu set `RmDisableDisplay=0` (hoặc bỏ key) thì có mở được gate không: **chưa test** — và test này chỉ có ý nghĩa **sau khi** gate fuse đã được xử lý, vì hiện tại nó không chạy tới.

### Phép kiểm phân biệt

| # | Phép kiểm | Giá trị |
|---|---|---|
| T-C1 | `NVreg_RegistryDwords="RmForceGridDisplayless=0;RmDisableDisplay=0"` + reload module, xem dmesg có thêm log display không | Thấp — gate fuse chặn trước, dự kiến không đổi. Chỉ nên làm **sau** T-A1/T-B1 |
| T-C2 | So sánh `nvidia-smi -q` trước/sau khi set key | Xác nhận key có hiệu lực vật lý hay bị bỏ qua |

⚠️ Cả hai đều cần thay đổi cấu hình driver — **ngoài phạm vi "không thay driver" của D1**, chỉ đề xuất.

---

## 7. Hash

| Đối tượng | Giá trị |
|---|---|
| GSP ELF | `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85` |
| `RmDisableDisplay` | vaddr `0x409E928`, file `0x9E928` |
| `RmForceGridDisplayless` | vaddr `0x408A2E0`, file `0x8A2E0` |
| Source RM | `1a82fbfda8f321b056eb3568850f9316c5e465c5` |

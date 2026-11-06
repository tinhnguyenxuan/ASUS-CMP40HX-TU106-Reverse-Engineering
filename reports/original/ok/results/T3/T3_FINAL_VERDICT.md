# T3_FINAL_VERDICT.md

## T3 FINAL VERDICT — CMP 40HX TU106 DISPLAY POLICY

### 1. Tổng kết các vấn đề đã sửa từ T2

| Vấn đề T2 (sai) | Sửa trong T3 | Bý chứng |
|-----------------|--------------|-----------|
| "6 tokens trong BIT" | **17 tokens** (parser đúng) | BIT header: cnt=17, verified trên 5 ROM |
| "Không có Token U" | **Token U tồn tại** tại index [10] | U data: CMP=0000020000 (NO_DISP=1), GeForce=8f4e000000 (NO_DISP=0) |
| "GeForce DCB entries=0 sai" | **Đúng, entries=0** | Parse lại từ con trỏ DCB hợp lệ (0x2D8FC/0x2D90C) |
| "B+32 = Coproc Build" | **Chưa xác định được chức năng** | Không gán nhãn, cần tài liệu NVIDIA chính thức |
| "0x21C04 không thuộc fuse controller" | **UNKNOWN nguồn** | tu102/dev_fuse.h không định nghĩa, nhưng driver đọc qua fuse HAL |

### 2. Bảng verdict theo PROVEN/SUPPORTED/UNKNOWN

| Câu hỏi | Verdict | Bý chứng (byte offset / cấu trúc / source) |
|---------|---------|---------------------------------------------|
| CMP VBIOS có cờ NO_DISPLAY_SUBSYSTEM? | **SUPPORTED** | BIT U data 0x289CE: `00 00 02 00 00`, DCF=0x02, bit1=1 |
| GeForce VBIOS có cờ NO_DISPLAY_SUBSYSTEM? | **SUPPORTED (không)** | BIT U data 0x289A2: `8f 4e 00 00 00`, DCF=0x00, bit1=0 |
| BIT có 17 tokens (không phải 6)? | **PROVEN** | BIT header: token_count=17, checksum=0x3246, verified 5 ROM |
| BIOSDATA version 2, 37 byte | **PROVEN** | Token B: length=37, offset=0x023E, data_off=0x2883E |
| B+32 byte: CMP=0x12, GeForce=0x10 | **PROVEN** | CMP: `...04 00 12 2a...`, GeForce: `...04 00 10 5b...` |
| B+32 là "Coproc Build"? | **UNKNOWN** | Không có tài liệu NVIDIA chính thức xác nhận |
| DCB entries=0 (cả CMP và GeForce)? | **SUPPORTED** | DCB version=170 (CMP) / 4 (GeForce), entry_count=0 |
| Driver đọc fuse 0x21C04 gate display? | **SUPPORTED** | kern_disp.c:444, kernel_gsp_tu102.c:1361, g_gpu_nvoc.c:2097 |
| Fuse 0x21C04 live = 0x00000001 | **PROVEN** | Read-only MMIO read trên target <REDACTED_LAB_IP> |
| Fuse 0x21C04 là raw OTP? | **UNKNOWN** | tu102/dev_fuse.h không định nghĩa; không có bằng chứng trực tiếp |
| Fuse 0x21C04 là shadow/latch? | **UNKNOWN** | Không thể phân biệt từ live read |
| Fuse 0x21C04 là firmware config? | **UNKNOWN** | Không tìm thấy mã ghi vào 0x21C04 |
| cmpunlocker thay đổi 0x21C04? | **SUPPORTED (không)** | T09: fuse vẫn = 1 sau unlock |
| BIT Token U có consumer kernel? | **UNKNOWN (không tìm thấy)** | Không có mã trong kernel source 615.78.08 |
| SEC2 điều khiển trực tiếp display? | **UNKNOWN** | Không tìm thấy liên hệ trực tiếp trong driver source |
| Display CMP 40HX bị hard-fused vĩnh viễn? | **UNKNOWN** | Không có bằng chứng OTP trực tiếp cho 0x21C04 |

### 3. Đồ thị phụ thuộc gate (tóm tắt)

```
Fuse 0x21C04 (DATA=1, GATE FALSE)
    │
    ├─→ kern_disp.c:444 → Display init chặn (NOT_SUPPORTED)
    │
    ├─→ kernel_gsp_tu102.c:1361 → VGA workspace không tính
    │
    └─→ KernelDisplay có thể không được init
            │
            ├─→ disp_objs.c:95 → Display API chặn
            │
            └─→ GridDisplayless vs KernelDisplay loại trừ nhau
```

BIT Token U (NO_DISPLAY_SUBSYSTEM=1 cho CMP) **không có consumer kernel** được xác định. Có thể được đọc bởi userspace driver.

### 4. Kết luận cuối cùng

1. **CMP 40HX VBIOS có cờ NO_DISPLAY_SUBSYSTEM=1** trong BIT Token U (0x289CE, DCF=0x02). GeForce ROMs không có cờ này (DCF=0x00).

2. **Driver gate display qua fuse 0x21C04** (đọc bởi gpuFuseSupportsDisplay_GM107 trên TU106). Live read = 0x00000001 → host gate FALSE → display không thể init qua kernel path.

3. **Không thể kết luận "hard-fused vĩnh viễn"** vì nguồn 0x21C04 là UNKNOWN (tu102/dev_fuse.h không định nghĩa, không có bằng chứng OTP trực tiếp).

4. **SEC2 không được chứng minh có liên hệ trực tiếp với đường quyết định display.** SEC2 được dùng trong cmpunlocker compute path, GSP UNTOUCHED.

5. **DCB không phải nguồn duy nhất quyết định display** — GeForce có U=0 nhưng DCB entries=0, có nghĩa là connector data nằm ở nơi khác.

6. **B+32 byte (0x12 CMP vs 0x10 GeForce)** là sự khác biệt được xác nhận, nhưng chức năng chưa xác định được — không gán nhãn "Coproc Build".

### 5. File đầu ra T3

| File | Nội dung |
|------|----------|
| `results/T3/BIT_VALIDATED_CLEAN.json` | Dữ liệu BIT parsed từ 5 ROM (17 tokens) |
| `results/T3/BIOSDATA_B_LAYOUT.md` | Layout BIOSDATA version 2, 37 byte, B+32 phân tích |
| `results/T3/DCB_POINTER_VALIDATION.md` | DCB con trỏ và cấu trúc, tất cả entries=0 |
| `results/T3/DISPLAY_FUSE_PROVENANCE.md` | Nguồn 0x21C04, phân loại UNKNOWN |
| `results/T3/DISPLAY_GATE_DEPENDENCY_GRAPH.md` | Đồ thị 3 gate, phân biệt độc lập/phụ thuộc |
| `results/T3/T3_FINAL_VERDICT.md` | Tổng kết verdict bảng |

### 6. Ràng buộc đã tuân thủ

- ❌ Không flash ROM
- ❌ Không ghi MMIO
- ❌ Không sửa OTP/RIR
- ❌ Không reset GPU
- ✅ Chỉ phân tích offline và đọc phần cứng read-only đã kiểm toán

## Ghi chú PONYTAIL

# ponytail: T3 hoàn tất. CMP có NO_DISPLAY_SUBSYSTEM=1, GeForce=0. Fuse 0x21C04 live=1 (gate FALSE) nhưng nguồn UNKNOWN. SEC2 không liên quan trực tiếp display. 5 file đầu ra đã ghi.

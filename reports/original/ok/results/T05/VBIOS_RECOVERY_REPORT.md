# T05 — VBIOS/DCB và điều kiện đủ khôi phục cổng display

Ngày thực hiện: 2026-11-05 (+07). Phạm vi R0: phân tích offline hai ROM được cung cấp; không flash, không patch ROM, không kết nối GPU.

## Kết luận ngắn

- Hai ROM đều được parse độc lập bằng Python `struct` có bounds-check; cả hai có PCIR vendor `0x10de`, device `0x1f0b`.
- DCB được xác định tại `0x2D9AC`, version `0x41`, signature `0x4EDCBDCB` hợp lệ, header size `35`, **entry count = 0**, entry size `8`.
- Bảng `connector` không null nhưng header version `0x40`, header size `5`, entry count `0`, entry size `4`; vì vậy không có connector entry để ánh xạ DP/DVI/HDMI trong DCB này.
- CCB 4.1 có 15 records; các records 3–9 khai báo DPAUX ports 0–6 theo decoder v4.1. Điều này chỉ chứng minh bảng communications có khai báo các port; không chứng minh DCB output route hay PHY hoạt động.
- GPIO 4.1 có 32 records; bản decoder giữ raw fields và không tự gán HPD từ tag không khớp danh mục HPD đã kiểm. Không được biến bảng GPIO thành bằng chứng có tín hiệu.
- I2C Devices có 32 records, nhưng `type` cần hiểu theo bảng I2C 4.1; parser hiện giữ raw/type bytes, không dùng chúng để tuyên bố DDC hoạt động.
- Hai ROM có cùng DCB header và các bảng display liên quan; `cmp40hx_t4_derivative.bin` **không phải reference ROM độc lập**.
- Không có ROM RTX 2060 SUPER/RTX 2070 có provenance đủ mạnh trong package để làm control. Vì vậy không thể kết luận zero-entry là đặc tính mọi TU106 hay riêng CMP này.

## 1. Input và hash

| File | Kích thước | SHA-256 |
|---|---:|---|
| `03_VBIOS/CMP40HX_ORIGINAL_1MB.bin` | 1,048,576 | `dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec` |
| `03_VBIOS/cmp40hx_t4_derivative.bin` | 495,616 | `aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb` |
| `05_PHASE21_EXTRACTS/evidence/dcb.json` | package evidence | `5e621d549928f4536a0c1d588dfa9c7d8a2803d09ef82682ab93c5a48aeb5aa3` |

ROM được nhận diện trong PCIR bởi vendor/device, không suy provenance từ tên file.

## 2. Decoder và đối chiếu spec

Decoder chính: `results/T05/parse_vbios_corrected.py`; output: `results/T05/VBIOS_DISPLAY_TABLES.json`.

Đối chiếu source parser EnvyTools snapshot offline:

- `/tmp/envytools/nvbios/dcb.c` — DCB 4.0/4.1 đọc header 23+ bytes và các pointer ở các field chuẩn; hash `acf1dc633fb2e1ebd78bef48c890610c02e3bc38c4e66fea82c45857527e91c6`.
- `/tmp/envytools/nvbios/conn.c` — CONN v4.0 header/record; hash `918667bffc36e641d78ee97aa2dcaeb5f189f0b1fbe71df0356fa6588030a65f`.
- `/tmp/envytools/nvbios/gpio.c` — GPIO v4.1 header/record; hash `116953726fe1028e55dccfcde88fec2569209293b8a0ee8a406e4af5721f1d46`.
- NVIDIA DCB 4.x Specification: <https://nvidia.github.io/open-gpu-doc/DCB/DCB-4.x-Specification.html>, truy cập `2026-11-05`. Nguồn mô tả DCB header, signature, entry count, connector pointer; DCB 4.1 tái sử dụng assignment masks cho pad macro/pad link. Applicability: specification cho DCB 4.x, trực tiếp liên quan format `0x41`; không tự xác nhận riêng board CMP.

Lưu ý quan trọng: các offset pointer trong DCB này được parser EnvyTools xử lý theo `legacy_image_base = 0x28600`; không được cộng pointer vào `dcb_abs`. Parser ban đầu trong output cũ đã dùng sai cơ sở cho nhiều table và tạo header giả dạng `0x00005555`; output hiện tại đã sửa và chạy lại.

## 3. Kết quả DCB hai ROM

### 3.1 Header

Bytes header tại `0x2D9AC`:

`41 23 00 08 4f 54 cb bd dc 4e aa 4b 00 00 00 00 00 00 40 55 c5 55 01 00 00 00 00 00 00 00 00 00 00 00`

Giải mã:

- version `0x41`
- header size `0x23` = 35
- entry count `0x00`
- entry size `0x08`
- signature field bytes at `+0x06`: `cb bd dc 4e` → little-endian `0x4EDCBDCB`
- communications pointer relative `0x544F`
- GPIO pointer relative `0x4BAA`
- input/cinema/spread-spectrum pointers `0`
- I2C Devices pointer `0x5540`
- connector pointer `0x55C5`
- flags `0x01`
- HDTV/switched-output pointers `0`

Cả hai ROM cho cùng header và cùng các pointer/records display-related.

### 3.2 Connector table

`legacy_base + 0x55C5 = 0x2DBC5`:

- version `0x40`
- header size `5`
- entry count `0`
- entry size `4`
- raw header: `40 05 00 04 00`

Theo DCB specification, entry count là số display device entries và connector table pointer null/invalid làm bảng absent/invalid; ở đây pointer **có mặt**, nhưng count **bằng 0**. Kết luận đúng là `VERIFIED`: ROM không cung cấp connector records trong bảng này. Đây không đủ để kết luận GPU die không có display engine, cũng không đủ một mình để kết luận PCB thiếu trace.

### 3.3 DCB device entries

Header DCB có `entry_count = 0`, nên không có DCB device entry để decode `type`, `heads`, `connector index`, `output resource` hoặc DP link masks. Không được gọi đây là “0 connector” theo nghĩa vật lý; chỉ là **0 record cấu hình trong ROM**.

### 3.4 Communications Control Block

`0x2DA4F`:

- version `0x41`, header size `6`, count `15`, record size `4`.
- DPAUX decode theo v4.1: records 3–9 lần lượt khai báo DPAUX `0,1,2,3,4,5,6`.
- records 0–2 có I2C ports 0–2 nhưng DPAUX field reserved/`31`; records 10–14 là `0xFF`/unused.

Đây là khai báo communications resource trong VBIOS. Vì `entry_count=0`, không có display device nào tham chiếu các resources này. Do đó không được suy từ DPAUX declarations rằng DP output usable.

### 3.5 GPIO 4.1

`0x2D1AA`:

- version `0x41`, header size `6`, count `32`, record size `6`.
- parser lưu `line`, `tag`, `special_output`, `special_input`, và raw bytes.
- Không có tag nào khớp các hằng HPD được kiểm từ `bios.h` snapshot. Đây chỉ là kết quả decoder/enum hiện có; tag không nhận diện được có thể là reserved/vendor-specific, không đồng nghĩa không có HPD.

### 3.6 I2C Devices

`0x2DB40`:

- version `0x40`, header size `5`, count `32`, record size `4`.
- parser giữ raw records và byte type; không gán DDC/AUX functionality từ các byte chưa được nối với connector entry.

## 4. Hai ROM có độc lập không?

`cmp40hx_t4_derivative.bin` có PCIR chỉ chứa hai image đầu giống phần tương ứng của ROM 1MB và có cùng DCB tại cùng offset, cùng header/table records. Nó là derivative/variant cùng family CMP, không phải control độc lập RTX 2060S/2070.

Package inventory có các ROM khác ở đường `/tmp`, nhưng tên/hash không cung cấp provenance GeForce model/board/revision đủ để dùng làm reference control. Theo scope T05, không đưa chúng vào kết luận control.

## 5. Điều kiện khôi phục DP/DVI

### Điều đã chứng minh

1. DCB của hai ROM được cung cấp không mô tả display device entries.
2. Connector table tồn tại nhưng không có records.
3. DCB metadata không đủ để tạo route DP/DVI/HDMI trong driver.
4. CCB/GPIO/I2C tables còn tồn tại không bù được việc thiếu device entries.

### Điều chưa chứng minh

- `entry_count=0` là nguyên nhân duy nhất display bị vô hiệu hóa hay chỉ là một blocker VBIOS.
- VBIOS init script/devinit có thể tạo route ngoài DCB hay không.
- Host driver/GSP có cho phép display nếu thay metadata hay không.
- Display engine, SOR/PHY, package pins và PCB population có thực sự hoạt động hay không.
- DVI/HDMI route trên bản CMP thực tế; T01 chỉ phân tích CAD/net naming của design GeForce và không chứng nhận population CMP.

### Verdict có điều kiện

- **DP:** không có bằng chứng `RECOVERY_VERIFIED`. Nếu fuse/policy được mở nhưng ROM vẫn entry-zero, metadata/init vẫn là blocker cần xử lý; tuy nhiên việc flash/sửa ROM ngoài R0 và không đủ để hứa thành công.
- **DVI:** chưa có DCB route và chưa có evidence output path runtime; verdict `UNKNOWN/BLOCKED` trong scope R0. Không suy từ việc có DVI nets trên CAD thành khả năng khôi phục.
- **Phần mềm đơn thuần:** không đủ cơ sở. Cần đồng thời giải quyết display gate, VBIOS/init, hardware routing/population và driver compatibility.

## 6. Completion và gap

T05 hoàn tất cho hai ROM được chỉ định: PCIR/DCB/header/pointers/zero-entry/CCB/GPIO/I2C đã được kiểm offline và output JSON được tái tạo bằng parser corrected. Còn thiếu reference ROM độc lập có provenance; đánh dấu `UNKNOWN`, không tự tải hoặc tự nhận diện ROM ngoài package.

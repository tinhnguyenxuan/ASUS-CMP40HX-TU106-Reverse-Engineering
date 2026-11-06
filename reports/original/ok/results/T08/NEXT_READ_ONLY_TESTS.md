# T08 — Các phép kiểm read-only có giá trị phân biệt

Ngày: 2026-11-05 (+07). Đây là thiết kế phép kiểm, **không phải log đã chạy trên card**. R0 hiện tại chỉ cho phép đọc artifact offline; không SSH, không mở resource GPU, không ioctl lạ, không reset/reload/reboot.

## Nguyên tắc dừng

- Mỗi query tương lai phải gắn đúng BDF `0000:03:00.0`, driver/GSP version và timestamp.
- Không dùng tên “read-only” để mặc định an toàn; interface phải được tài liệu hóa và có positive control.
- Không suy OTP từ một giá trị STATUS; không suy transistor từ BADF; không suy display từ class `0300`; không suy direct scanout từ headless render.
- Nếu A/B không tách được giả thuyết, ghi `UNKNOWN`, không chuyển thành YES/NO.
- Không modeset, hotplug test, benchmark, unlock, write BAR/MMIO, flash hoặc thay strap trong checklist này.

## Thứ tự ưu tiên

### 1. Chốt identity hiện tại — `T08-01`

Đọc capture có timestamp của BDF, PCI ID/class, driver và GSP/firmware. So sánh với archive:

- Nếu exact tuple là `615.71.09`, mọi địa chỉ/source static `615.78.08` phải giữ scope riêng.
- Nếu exact tuple khác, dừng việc ghép các phase theo phiên bản.
- Nếu BDF/PCI ID khác, dừng vì toàn bộ kết luận card-specific bị treo.

**Kết quả không phân biệt:** chỉ chốt identity; không trả lời display/SM.

### 2. Kiểm provenance `0x021C04` qua điều kiện boot — `T08-02`

Chỉ đề xuất khi có interface read-only đã xác minh cho TU106 và liveness gate. Đọc `NV_FUSE_STATUS_OPT_DISPLAY` qua đúng aperture, có positive-control word; lặp trước/sau cold power cycle.

- Không đổi qua cold boot: tăng trọng lượng giả thuyết OTP-like, nhưng chưa chứng minh OTP thô.
- Đổi qua cold boot: ủng hộ shadow/strap/policy-derived.
- Read fail/poison: chỉ nói path không hợp lệ/không khả dụng, không nói fuse hay silicon.

Phép này không được thực hiện trong T08.

### 3. Đối chiếu host gate với display-IP response — `T08-03`

Dùng log/KMS capability response được tài liệu hóa, gắn đúng BDF và driver. So sánh ba tầng: `gpuFuseSupportsDisplay` gate, display preinit result, capability/connector response.

- Gate false + preinit `NV_ERR_NOT_SUPPORTED`: củng cố software host gate.
- Gate false nhưng independent IP response usable: giữ mâu thuẫn, không chọn một bên.
- Không có response: không coi là display silicon absent.

### 4–5. Tách DP và DVI — `T08-04`, `T08-05`

Nếu có artifact/runtime query hợp lệ, ghi riêng DP J1 và DVI J5. Identity phải chứng minh connector thuộc CMP BDF, không phải GPU khác. HPD/AUX/DDC response chỉ chứng minh từng sideband/endpoint ở tầng tương ứng; không tự chứng minh pixel scanout.

DP và DVI không được gộp verdict. T01 hiện chỉ chứng minh CAD route; photo prior cho biết J1/J5 physical connector nhưng sideband IC và CMP BOM vẫn chưa được chốt.

### 6. Chốt effective registry — `T08-06`

Đọc actual global/per-device registry hoặc GSP trace qua interface đã biết. Không gọi ioctl không tài liệu hóa.

- `RmDisableDisplay=1`: chứng minh software policy input veto tại GSP path 615.78.08.
- absent/0: chỉ loại một policy input trong nguồn đã đọc; không chứng minh fuse/display hardware.
- Không thấy key trong archive: không đồng nghĩa runtime absent.

### 7. ROM control — `T08-07`

Cần ROM RTX 2060 SUPER và RTX 2070 TU106 có board/revision/source/hash. Parse cùng corrected parser; so `entry_count`, CONN, CCB/GPIO/I2C và init-related data.

- Control populated, CMP zero: CMP-specific metadata blocker mạnh hơn.
- Control cũng zero: zero-entry có thể là family/variant behavior.
- Không có provenance: không dùng làm control.

### 8. Fuse/topology controls — `T08-08`

Cần dump có provenance từ TU106 34-SM và 36-SM. Chỉ so sánh các offset sau khi exact family/revision/aperture/driver match. Correlation không tự map semantics; cần loại trừ software topology mask.

### 9. Exact 615.71.09 binary — `T08-09`

Cung cấp GSP/SEC2 exact runtime, xác minh `.fwversion` và hash, sau đó chỉ lặp bounded windows T07. Không dùng delta địa chỉ từ 615.78.08.

### 10. Strap-to-class source — `T08-10`

Cần source/VBIOS/devinit TU106-family nói trực tiếp mapping strap vector → class/ID. Tài liệu G80+/N18E hiện chỉ là analogies/extrapolation; không đủ để chốt `STRAP3/4/5 → 0302/0300`.

## Bảng trạng thái hiện tại

| Nhóm | Đã có | Chưa có |
|---|---|---|
| Identity | historical BDF/ID và static 615.78.08 artifacts | fresh runtime tuple |
| Display fuse | archived `0x021C04=1`, host decode false | live/current provenance OTP vs shadow |
| GSP policy | bounded 615.78.08 dataflow | exact 615.71.09 mapping/effective value |
| DP | CAD route + prior photo connector | CMP BOM/sideband/runtime signal |
| DVI | CAD route + prior photo connector | CMP BOM/sideband/runtime signal |
| VBIOS | two CMP ROMs, DCB zero entries | authenticated GeForce control ROM |
| 2 SM | 34 SM/2176 CUDA effective count | physical existence/health/override path |
| Straps | netlist; STRAP3/4/5 photo inference | TU106 semantic mapping and latch read |

Không phép kiểm nào trong T08 đã được thực hiện trên card; kết quả hiện tại của tất cả test là `NOT_RUN` hoặc `NEEDS_INPUT` như ghi trong CSV.
# FINAL FEASIBILITY ASSESSMENT — CMP 40HX / TU106

Ngày: 2026-11-05 (+07)
Phạm vi: tổng hợp độc lập package `ASTRA_CMP40HX_HANDOFF`, T00–T09; bổ sung bằng chứng live SSH read-only vào host <REDACTED_LAB_IP> (tinh, mật khẩu do user cung cấp). Không GPU/MMIO/BAR/PCI write, không flash, không reset/reload/reboot, không can thiệp card.

## 1. Kết luận điều hành

### DP trực tiếp — `UNKNOWN / NOT_RECOVERY_VERIFIED`

Có ba lớp bằng chứng khác nhau:

1. **PCB design:** GenCAD CG161P R2 có lane `IFPD_L0–L3`, AUX, HPD từ J1 tới G1 qua các linh kiện AC-coupling. Đây là `CAD_ONLY`; sideband đi qua các IC multi-pin chưa định danh đầy đủ trong CMP BOM.
2. **Card photo:** prior report nhận diện J1 DP physical connector đã lắp; đây là `CORROBORATED` cho sự hiện diện connector, không phải chứng minh tín hiệu.
3. **Host/GSP/VBIOS:** archived fuse-status `0x021C04=1` được host predicate exact 615.78.08 đánh giá với `DATA_ENABLE=0`, nên gate display host là `FALSE` cho snapshot lưu trữ. Live nvidia-smi 615.71.09 xác nhận `Display Attached: No`, `Display Active: Disabled` trên CMP 40HX (GPU 0, BDF 03:00.0). Hai ROM CMP có DCB `entry_count=0` và connector table `count=0`.

Vì vậy, DP có route thiết kế và connector vật lý nhưng chưa chứng minh đồng thời: CMP population/sideband, display IP/PHY, effective policy, init metadata, đúng firmware runtime và tín hiệu vật lý. Không có cơ sở nói “đổi class/strap là DP sẽ chạy”.

### DVI trực tiếp — `UNKNOWN / NOT_RECOVERY_VERIFIED`

J5 DVI được nhận diện trong photo prior report và GenCAD có các nhóm TMDS IFPA/IFPB tới G1 ở mức `CAD_ONLY`. Tuy nhiên DDC/HPD đi qua IC, CMP BOM chưa được xác nhận đầy đủ, và hai ROM CMP không có DCB device entries. Không có capture runtime DVI/HPD/DDC hoặc bằng chứng monitor nhận pixel từ đúng BDF. Live DRM: `card0-DP-1 connected` thuộc card khác (BDF 04:00.0), không phải CMP 40HX (card1/BDF 03:00.0); card1 không expose connector status nào. DVI không được suy từ DP.

### +128 CUDA / 2 SM — `UNKNOWN / CONDITIONAL`

`34 SM / 2176 CUDA` là `MEASURED` ở effective API/topology. Nó không giải quyết bốn mệnh đề khác:

- transistor của TPC/SM thứ 18 có tồn tại hay không: `UNKNOWN`;
- đơn vị đó có được enumerate hay không: không xuất hiện trong effective topology;
- đơn vị đó có hoạt động/khỏe hay không: `UNKNOWN`;
- có đường re-enable hợp lệ hay không: `UNKNOWN`.

`fuse+0x0650=0x0004001F`, `fuse+0x0524=0x1F` và `STATUS+0x0C1C=0x38` là raw values/đầu mối. Không có TU106 public field definition chứng minh diễn giải “5 TPC bị cắt” hoặc “TPC18 chắc chắn không tồn tại”. `BADF`/PGRAPH poison không phân biệt được block absent với wrong aperture, access lock, reset/power hoặc decode failure.

128 CUDA chỉ là ứng viên có điều kiện nếu chứng minh được: TPC bị policy-only disable, không phải defect/thiếu transistor, và có override path hợp lệ trên TU106 mà PLM/GSP không chặn. Evidence GA100/170HX về `_CP + EN_SW_OVERRIDE` không tự áp dụng cho TU106.

### Strap / PCI class / Device ID — `UNKNOWN` về quan hệ nhân quả

Netlist xác minh:

- STRAP3 = `BM5`, `R258` pull-up, `R261` pull-down;
- STRAP4 = `BK5`, `R249`/`R264`;
- STRAP5 = `BJ5`, `R250`/`R265`.

Tài liệu envytools cho biết semantic PSTRAPS ở các họ cũ hơn; bảng N18E là họ/laptop khác. Chưa có direct TU106 source chứng minh `BM5` là bit nào, tổ hợp `STRAP5:3` chọn PCI class nào, hoặc strap chọn Device ID `1F0B`/GeForce ID nào. `class 0302` + `10DE:1F0B` là historical saved observation; class `0300` nếu xuất hiện chỉ chứng minh enumeration, không chứng minh output.

## 2. Display fuse và policy: điều đã chốt

### 2.1 Archived STATUS decode

Input `fuse2.json` lưu `regs["3076"] = 1`, tương ứng key `0x0C04` trong fuse aperture base `0x021000`, tức absolute `0x021C04` theo mapping của `fuse_dump2.py`.

Header/source exact tag 615.78.08 được kiểm trong T04:

```c
#define NV_FUSE_STATUS_OPT_DISPLAY              0x00021C04
#define NV_FUSE_STATUS_OPT_DISPLAY_DATA                 0:0
#define NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE  0x00000000
```

Host helper dispatch TU106 → `gpuFuseSupportsDisplay_GM107`; predicate test `DATA == ENABLE`. Do đó raw bit `1` → host display-support predicate `false` cho archived snapshot. Claim cũ “bit1 = display bật” bị `CONTRADICTED`.

### 2.2 Điều chưa chốt

Header chỉ chứng minh host decode và access semantics; không chứng minh physical source của STATUS là OTP cell thô. STATUS là R-only; OPT registers lân cận có kiểu RW/INIT, nhưng public source không đủ để xác định mux/shadow/strap pipeline của TU106. Live target read hiện chưa có; capture timestamp của dump cũ không xác định được.

GSP 615.78.08 có thêm software configuration path cho `RmDisableDisplay`: host registry → NVKV → `GSP_INIT` → list → worker field `+0x334` → bounded consumers. Tuy nhiên effective key/value trên target chưa được capture; exact GSP 615.71.09 runtime cũng thiếu.

## 3. VBIOS/DCB correction quan trọng

Parser đầu tiên tạo header/table sai vì cộng pointer vào `dcb_abs`. Parser corrected dùng các pointer theo `legacy_image_base=0x28600`, khớp EnvyTools source và saved handoff.

Kết quả hai ROM:

- DCB `0x2D9AC`, version `0x41`, header 35, signature `0x4EDCBDCB` valid;
- `entry_count=0`, `entry_size=8`;
- CONN pointer `0x55C5` → table `0x2DBC5`, version `0x40`, count `0`;
- CCB 4.1: 15 records, DPAUX 0–6 ở records 3–9;
- GPIO 4.1: 32 records;
- I2C Devices: 32 records.

CCB/GPIO/I2C còn dữ liệu không bù cho việc không có DCB device entries. DCB zero-entry là metadata blocker candidate; không phải proof display engine/PHY/PCB absent. `cmp40hx_t4_derivative.bin` không phải reference GeForce độc lập.

## 4. Các lỗi phương pháp đã sửa

1. Đảo polarity `NV_FUSE_STATUS_OPT_DISPLAY`: sửa về `DATA_ENABLE=0`.
2. Trộn firmware `615.78.08` với runtime `615.71.09`: tách scope; T07 đánh dấu `NEEDS_INPUT` cho 615.71.09.
3. Dùng BADF để kết luận transistor không tồn tại: hạ thành `UNKNOWN`.
4. Dùng number-match `0x0004001F` để gọi mask TPC: hạ thành `UNKNOWN`.
5. Gọi DCB zero-entry là không có display silicon: hạ thành metadata evidence.
6. Gọi T4 derivative là control độc lập: bác bỏ.
7. Gọi strap name `STRAP3` là bit3/bit4 TU106: giữ `UNKNOWN`.
8. Gọi class `0300` hoặc headless render là direct scanout: bác bỏ.
9. Gọi firmware strings `RmActivateHulk`/`RmDisableSec2` là host-callable exploit: không chấp nhận.
10. Gọi package checksum là provenance: chỉ giữ là internal integrity.

Chi tiết: `CLAIM_CORRECTIONS.csv`.

## 5. Khả năng phục hồi theo tầng

| Tầng | Kết quả hiện tại | Điều kiện để có thể nói “có đường” | Trạng thái |
|---|---|---|---|
| PCI class | historical `0302` | direct TU106 strap/class mapping + effective latch | UNKNOWN |
|| Device ID | historical `1F0B` | direct strap/fuse/firmware mapping | UNKNOWN |
|| Display host gate | archived predicate false + live `Display Attached: No / Active: Disabled` | current exact-driver evidence + policy/source separation | VERIFIED archived + live / UNKNOWN current policy |
| GSP `RmDisableDisplay` | static config path exists on 615.78.08 | effective runtime key/value | CORROBORATED path / UNKNOWN value |
| VBIOS DCB | zero device entries | devinit alternative or compatible reference metadata | VERIFIED metadata / UNKNOWN sufficiency |
| DP PCB | CAD lane + J1 photo | CMP population/sideband/PHY/runtime signal | CAD_ONLY + UNKNOWN physical |
| DVI PCB | CAD TMDS + J5 photo | CMP population/DDC/HPD/PHY/runtime signal | CAD_ONLY + UNKNOWN physical |
| 2 SM | 34 effective SM | policy-only source + valid TU106 override + healthy transistor | UNKNOWN/conditional |

## 6. Final answer to “có khôi phục được không?”

- **Không thể xác nhận khôi phục được** từ package hiện tại.
- **Không thể xác nhận chắc chắn không thể khôi phục** ở các tầng mà dữ liệu còn phân biệt không đủ: physical STATUS provenance, TU106 TPC defect/disable semantics, exact runtime GSP, CMP BOM/sideband and output signal.
- Có các blocker mạnh đã được chứng minh ở tầng metadata/policy snapshot: archived host display gate false và CMP VBIOS DCB không có device entries.
- Đường software-only chỉ là **conditional candidate**, không phải kế hoạch thao tác: phải đồng thời vượt policy, init metadata, driver/version, board sideband/PHY và physical output.
- Không có `RECOVERY_VERIFIED` cho DP, DVI hoặc 128 CUDA.

## 7. Dữ liệu cần nếu muốn giảm UNKNOWN ở vòng sau

Theo thứ tự giá trị thông tin:

1. Exact runtime identity capture: BDF/class/ID/driver/GSP + timestamp.
2. Exact `615.71.09` GSP/SEC2 artifact có hash/provenance.
3. Authenticated TU106 GeForce reference ROM (2060 SUPER/2070) và parse cùng corrected parser.
4. Effective registry/GSP read-only evidence cho `RmDisableDisplay`.
5. TU106 34-SM/36-SM control fuse/topology dumps có provenance.
6. CMP physical BOM/continuity and documented DP/DVI HPD/AUX/DDC status.
7. TU106 direct strap-to-class/ID evidence.

Các mục trên chỉ là input/thiết kế kiểm theo T08; không được hiểu là đã chạy.

## 8. By chứng web cmpunlocker/cmp.wiki (truy cập 2026-11-05)

| Nguồn | URL | Ngày truy cập | Nội dung liên quan | Áp dụng CMP 40HX/TU106 |
|---|---|---|---|---|
| Cyridd/cmpunlocker — compatibility.md | https://raw.githubusercontent.com/Cyridd/cmpunlocker/main/docs/compatibility.md | 2026-11-05 | "CMP 40HX has no normal display outputs. Graphics use therefore requires a suitable headless, secondary-GPU, remote-display or similar setup." | **Chống trực tiếp giả hipótesis unlock display qua strap/fuse** — cộng đồng đánh giá CMP 40HX không có output display vật lý thông thường. |
| NoPantsNoLife/cmp40hx_unlocker — README | https://raw.githubusercontent.com/NoPantsNoLife/cmp40hx_unlocker/main/README.md | 2026-11-05 | Compute unlock qua SEC2 Booter payload: `SS0=0x88888888`, `SS1=0x00000008`, `FECS_PLM=0xFFFFFF8F`. "compute is not raster graphics". FP32 compute ~7.0 TFLOPS sau unlock; Tensor Core MMA 63.8 TFLOPS. | Chỉ unlock **SM issue-rate / hiệu suất compute**, KHÔNG tăng số lượng SM. Không là bằng chứng SM count có thể thay đổi. |
| FreedomOverload/cmpunlocker_40hx — README | https://github.com/FreedomOverload/cmpunlocker_40hx | 2026-11-05 | "Compute / SM performance unlock — restores full SM issue rate and compute performance." | Xác nhận: unlock hiệu suất (issue rate), không phải unlock thêm SM. |
| cmp.wiki — Driver_unlock | https://cmp.wiki/wiki/Driver_unlock | 2026-11-05 | cmpunlocker (CMP 170HX GA100) unlock "Full SM compute throughput (the SS0/SS1 speed selectors)"; ceiling 74 SM trên 8 GB card; 128 SM chỉ trên 10 GB qua RIR fuse burn. | Cơ chế chứng minh trên GA100/CMP 170HX, **không chuyển giao tự động cho TU106/CMP 40HX**. |
| cmp.wiki — Full_SM_unlock | https://cmp.wiki/wiki/Full_SM_unlock | 2026-11-05 | CMP 170HX stock 70/128 SM; 74 SM ceiling 8 GB card; 128 SM chỉ 10 GB qua RIR fuse burn + EN_SW_OVERRIDE. | Ứng viên so sánh TU106, không áp trực tiếp. |

**Kết luận bổ sung từ web:**
- Không có công cụ công khai nào chứng minh unlock **thêm số lượng SM** cho CMP 40HX/TU106. cmpunlocker cho 40HX chỉ ripristina **SM issue-rate throttle** (hiệu suất compute) qua SEC2 Booter — không liên quan đến việc 2 SM (128 CUDA) có tồn tại hay có thể restore.
- Về display: không có bằng chứng web nào cho thấy strap/fuse unlock display cho CMP 40HX; ngược lại, cộng đồng đánh giá CMP 40HX không có output display thông thường.
- Kết luận tổng thể của T09 không đổi: chưa chứng minh khôi phục được DP/DVI hoặc 128 CUDA cores; cũng chưa chứng minh chắc chắn không thể.


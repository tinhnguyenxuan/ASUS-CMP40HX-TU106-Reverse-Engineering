# T07 — Kiểm chứng bounded GSP policy display

Ngày: 2026-11-05 (+07). Phạm vi R0: static/offline; không gọi GPU, không SSH, không MMIO/BAR, không patch firmware.

## Verdict

- Binary GSP có thể kiểm chứng trong package là `615.78.08`, SHA-256 `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`; `.fwversion` và inner ELF inventory khớp.
- Trên binary này, hai site dùng chuỗi `RmDisableDisplay` được xác định bằng raw instructions; worker copy giá trị cấu hình vào field `+0x334`, và consumer `0x04b20f54` đọc field đó để cho ra byte capability 1/0 trong các nhánh bounded đã kiểm.
- Host source/firmware evidence nối được đường cấu hình: registry database → `osPackageRegistry()` → NVKV → `GMCAPI_CMD_GSP_INIT (0x00010001)` → GSP configuration list → readers của `RmDisableDisplay`.
- Đây là **software-policy path**, không phải bằng chứng display fuse, display engine, PHY, PCB route hoặc output signal.
- Binary exact `615.71.09` — version ghi trong runtime target history — **không có trong package**. Không dùng delta địa chỉ/prologue để suy ánh xạ 615.71.09.

## 1. Provenance binary

Nguồn: `work_v15/outputs/gsp_tu10x.bin`.

- Bytes: 22,901,632.
- SHA-256: `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`.
- `.fwversion`: `615.78.08`.
- Inner ELF machine: RISC-V (`243`), inner entry `0x04010000` theo inventory.
- Inner ELF section mapping dùng để phân biệt VA với file offset; các VA trong report là inner-ELF VA, không phải file offsets.

**Lưu ý provenance:** manifest ZIP ban đầu **KHÔNG** chứa binary GSP. Binary `615.78.08` trên được lấy từ nguồn **ngoài gói ASTRA_CMP40HX_HANDOFF**, cần khai báo provenance riêng khi dùng làm kết luận chính thức.

Binary `gsp-570.144.bin` tồn tại ngoài package là artifact khác, SHA `3052aee2872182a14d8d7c069e3a14fe4642405894b24692c4aca4101dfb1809`; không dùng nó để thay thế 615.71.09.

**Đầu mène cần kiểm lại khi tiếp tục:** theo bàn handoff phiên trước, GSP `615.71.09` có thể được lưu tại `PHASE21_FUNCTIONAL_RESEARCH/evidence/target_live_20261104/gsp_tu10x_615.71.09.bin` — chưa cần yêu cầu cung cấp lại, chỉ cần xác thực tồn tại và hash khi bắt đầu phiên mới.

## 2. Bounded dataflow đã kiểm

### 2.1 Configuration worker

`0x04B30030` nhận object/config argument thứ hai; tại `0x04B30050`, argument này được copy vào `s3`.

Các string và store đã kiểm bằng raw bytes:

- `RMRunFub` tại mapped VA `0x040B3010` → byte `1` vào `s3+0x328` khi điều kiện phù hợp.
- `RMFubUseCaseMask` tại `0x040B3020` → word vào `s3+0x32c`.
- `RmDisableDisplay` tại `0x040B3038` → word `1` vào `s3+0x334` khi lookup thành công và value bằng `1`.

Verifier: `/home/REDACTED_USER/codex-work/PHASE21_FUNCTIONAL_RESEARCH/tools/verify_display_object_fields.py` — PASS.

### 2.2 Hai site gọi helper

Raw xrefs cho thấy string `RmDisableDisplay` được hình thành và helper `0x045E130C` được gọi tại:

- site A `0x04840368` → helper `0x045E130C`.
- site B `0x04B300C0` → helper `0x045E130C`.

Helper là configuration read wrapper có fallback path; exact API symbol và effective value source chưa được recovered.

### 2.3 Consumer bounded

Consumer `0x04B20F54`:

- đọc `lw a5,0x334(a1)` tại `0x04B20F80`;
- field zero → fall-through ghi byte `1` tại `0x04B20F8C`;
- field nonzero → nhánh diagnostic/negative ghi byte `0` tại `0x04B20FE4`;
- consumer được cài vào slot `+0x158` tại ba construction sites.

Site A cũng có nhánh riêng: `RmDisableDisplay == 1` bypass predicate HAL `+0x1c8` và trả byte zero; nếu key missing thì dùng các cached prerequisites khác. Vì vậy không được rút gọn toàn bộ firmware thành một branch duy nhất.

### 2.4 Selector `0x3814`

Hai predicate bounded được giải mã:

- HAL slot `+0x1b0`, target `0x04B19EA4`: `(word & 0x000c0000) != 0`.
- HAL slot `+0x1c8`, target `0x04B1A018`: `(word >> 27) & 1`.

Cả hai gọi accessor với selector/offset `0x3814`. Exact TU106 field name, physical aperture and relation to archived fuse read chưa được chứng minh. Không gán selector này thành `NV_FUSE_FEATURE_READOUT` chỉ dựa trên tài liệu GA100/GB100.

## 3. Configuration ingress

Official host-source evidence ghi nhận:

`host registry` → `osPackageRegistry()` → packed registry → `_kgspEncodePackedRegistryKeys()` → NVKV system-info → `GMCAPI_CMD_GSP_INIT = 0x00010001` → firmware decoder → typed list → `RmDisableDisplay` readers.

Các verifier đã chạy:

- `verify_display_object_fields.py`: PASS.
- `verify_display_dataflow.py`: 9 raw encoding checks PASS.
- `verify_host_registry_producer.py`: 10 source-path checks PASS; 2 archived RegistryDwords hits; 0 archived `RmDisableDisplay` text hits.

Không có bằng chứng archived text rằng target đã explicit set `RmDisableDisplay`. Điều này không loại trừ per-device registry, internal entries hoặc config bị thiếu khỏi handoff.

## 4. Phiên bản 615.71.09

Runtime history trong package nói `615.71.09`, nhưng không có exact GSP binary/hash tương ứng. Vì vậy:

- không chốt VA/branch của 615.71.09;
- không suy bằng delta cố định từ 615.78.08;
- ghi `NEEDS_INPUT` trong `VERSION_FUNCTION_MAP.csv`.

## 5. Giới hạn và hệ quả phục hồi

T07 chứng minh được một software configuration/policy path trên GSP 615.78.08. Nó **không** chứng minh:

- giá trị `RmDisableDisplay` hiệu dụng trên card;
- path đã chạy trong boot hiện tại;
- host fuse predicate đã được bypass;
- display IP/SOR/PHY tồn tại hoặc được clock/reset;
- VBIOS DCB zero-entry có thể được thay thế bằng config;
- DP/DVI phát tín hiệu.

Kết luận hợp lệ: GSP policy là một tầng blocker/điều kiện cần có thể tồn tại, nhưng chưa có bằng chứng nó là blocker duy nhất hoặc có đường override an toàn. Việc đổi registry/patch firmware/flash không thuộc T07 và không được thực hiện.

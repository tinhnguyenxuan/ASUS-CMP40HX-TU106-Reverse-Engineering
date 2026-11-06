# TU106: truy vết tới producer trong GSP-RM

Thu thập live lúc 18:15–18:18 UTC, 05-11-2026 (01:15–01:18 Bangkok, 06-11). GPU UUID `GPU-REDACTED`, BDF `0000:03:00.0`, ID `10de:1f0b`, driver và GSP version `615.71.09`. SSH đã hoạt động với mật khẩu người dùng cung cấp; không lưu mật khẩu trong artifact. Dữ liệu firmware cài đặt khớp hash bản được phân tích. Version do `nvidia-smi` báo và hash của file cài đặt **không phải phép đọc lại hash của image đang resident trên GPU**.

## Kết quả mới

- Producer thấp nhất xác minh được: handler GSP-RM thực sự của `INTERNAL_STATIC_GR_GET_FLOORSWEEPING_MASKS` ở VA `0x4bc63c4`, lấy từng TPC mask qua lời gọi hàm ảo `ld a5,0x130(s2); jalr a5`, truyền con trỏ tới `floorsweepingMasks[grIdx].tpcMask[gpc]`. Điều này vượt qua ranh giới control kernel trong báo cáo trước. Chưa xác định được implementation cụ thể của hàm ảo trên card và chưa chứng minh được đường MMIO tới fuse hoặc việc sửa bởi firmware. Không suy MMIO hay OTP từ tên hàm ảo.
- GSP-RM thực sự có hai entry riêng `0x20800a26` → `0x20800a27`: handler của entry đầu tạo lệnh `0x20800a27`, kích thước `0x2a60`, rồi gọi qua function pointer. Entry sau trực tiếp tạo structure. Đây là hai method ID khác nhau, dùng cùng ABI; header công khai chỉ hiện rõ constant của KGR và message ID `0x27` của GR.
- GR reconfiguration `0x2080123b` tồn tại trong bảng method của firmware dưới flag **INTERNAL**, handler VA `0x4bbdd1c`, size 24. Handler gọi hai hàm ảo; hàm thứ hai nhận pointer đến output tại offset `+4`. Chưa phân giải đích ảo và nguồn dữ liệu. GPU wrapper `0x208001e7` chỉ có implementation C dưới DEBUG/DEVELOP, không có entry đó trong bảng host generated của release đã kiểm tra và không thấy literal 32-bit của command trong firmware. Không khẳng định chip thiếu cơ chế.
- Thử cả hai control trên card cho logical GPC 0–2: tất cả trả `0x56 = NV_ERR_NOT_SUPPORTED`, buffer không đổi. KGR internal `0x20800a26` cũng trả 0x56. Host đã cấp thành công client/device/subdevice, và control GET thay thế `0x2080123c` thành công, nên không quy lỗi cho SSH hoặc GPU chung. Không dùng sudo để cố vượt internal routing.
- Đường GET thay thế là `GR_GET_SM_ISSUE_RATE_MODIFIER_V2`: tám cặp `(index, value)` lần lượt `(0,6), (2,6), (3,0), (4,6), (5,6), (6,6), (7,6), (8,6)`. Source gọi đây là giá trị speed-select/fuse và đọc static info. Đây là một lớp dữ liệu fuse-derived khác đã truy cập được, **không phải** OTP raw TPC, defect map hoặc bằng chứng TPC lành/hỏng. Các con số không được giải mã thành khả năng TPC.

## Call graph: host → GSP → virtual producer

Các đường dẫn sau là source NVIDIA tag `615.71.09` (annotated tag `d2a24f90...`, commit `61dcc93722ecb418bb5f2e00923f05b4b8051dd1`). Hai file `kernel_graphics.c` và `g_subdevice_nvoc.c` đã tải lại từ tag và khớp SHA-256 source cục bộ.

```text
User RM GET_TPC_MASK 0x2080122b
  host Subdevice::subdeviceCtrlCmdKGrGetTpcMask_IMPL
    kernel_graphics.c:3589–3639
  -> kgrmgrGetLegacyTpcMask -> legacy static floorsweepingMasks.tpcMask[gpcId]
    kernel_graphics_manager.c:612–627 (non-MIG)
  <- kgrmgrSetLegacyKgraphicsStaticInfo memcpy static info
    kernel_graphics_manager.c:365–378
  <- host static info filled by pRmApi->Control with Subdevice handle
    kernel_graphics.c:1130–1163,1258–1270
    method 0x20800a26, structure 8 x 0x54c = 0x2a60
  -> host export Subdevice::subdeviceCtrlCmdKGrInternalStaticGetFloorsweepingMasks
    generated/g_subdevice_nvoc.c:6179–6194, flags 0x1c0c0
  -> in GSP offload, host RM resource control route-to-physical
    kernel/rmapi/resource.c:260–290; NV_RM_RPC_CONTROL
  -> GSP Subdevice dispatch 0x20800a26: entry -> 0x4bb6c90
  -> VA 0x4bb6c90 loads command 0x20800a27 and size 0x2a60;
     forwards via function pointer at object +0x318
  -> GSP Subdevice dispatch 0x20800a27: entry -> 0x4bc63c4
  -> 0x4bc652c virtual call obtains GPC mask;
     0x4bc65b0–0x4bc65c0 calls virtual function at object +0x130,
     with GPC index in a2 and &output.tpcMask[index] in a3
  -> underlying TU106-specific virtual function / values used to initialize it:
     NOT RESOLVED; no identified raw fuse address, OTP, policy or defect.
```

`ctrl2080internal.h:290–344` quy định layout: `gpcMask +0`, `tpcMask +4` (64 dword), `tpcCount +0x104`, `physGpcMask +0x204`; output array theo GR local index. Trong non-MIG, header xác định `tpcMask` index là physical GPC; trong MIG là logical. Handler GR zero toàn buffer, gọi ảo lấy GPC mask, lặp các bit GPC và truyền con trỏ tới `tpcMask`; nhánh khác dành cho cấu hình khác có tồn tại. Các địa chỉ VA là trong ELF GSP đã trích, không phải BAR hay địa chỉ file trực tiếp. [Raw dispatch](GSP_DISPATCH.json), [KGR wrapper](GSP_KGR_WRAPPER.asm), [GR handler](GSP_GR_FLOORSWEEP.asm); script [inspect_gsp_dispatch.py](inspect_gsp_dispatch.py) tái lập bảng. Cấu trúc entry giải mã theo format generated NVOC (`pFunc`, flags, access, method, size, class); các method, size và flags khớp source/ABI, không dựa chỉ vào string.

Nguồn host gồm nhánh VSI khác ở `kernel_graphics.c:893–894,1022–1023`; đồ thị chính là nhánh gọi internal control. Mode GSP được báo live; không có instrumentation từng RPC của lần khởi tạo trước đó. [Source consumer](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/nvidia/src/kernel/gpu/gr/kernel_graphics.c#L1258), [RPC routing](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/nvidia/src/kernel/rmapi/resource.c#L260), [ABI](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080internal.h#L303).

## ABI, quyền và tầng từ chối reconfiguration

`0x2080123b` có `gpc` u32 offset 0, `tpcReconfigMask` u32 offset 4, `grRouteInfo` offset 8 gồm u32 flags và u64 route căn 8, tổng 24 byte. Input gpc là **logical**, route NONE là 0. Firmware handler `0x4bbdd1c` đọc input, qua virtual function offset `0x200` và sau đó offset `0x7e8`, truyền `&params->tpcReconfigMask`; [disassembly](GSP_RECONFIG_HANDLER.asm). Chưa biết hàm ảo có trả OTP, mask khả dụng, chính sách hay tổ hợp nào; từ mô tả header chỉ biết đó là mask reconfigurable.

Phân biệt kết quả đo với suy luận về điểm từ chối:

1. Host release generated không có export `0x2080123b` hoặc `0x208001e7` khi tìm toàn `src/nvidia/generated`. `resControlLookup_IMPL`, [rs_resource.c:118–133](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/nvidia/src/libraries/resserv/src/rs_resource.c#L118), trả 0x56 nếu không tìm thấy method của object và các lớp liên quan. Đây là tầng host lookup dự kiến cho hai lệnh này; chưa có trace runtime tại call site nên không tuyên bố đã quan sát trực tiếp PC trả lỗi. GSP có entry `0x3b` không có nghĩa user request đã đến GSP.
2. Với `0x20800a26`, host có metadata `INTERNAL | ROUTE_TO_PHYSICAL`; [control.c:802–806](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/nvidia/src/kernel/rmapi/control.c#L802) từ chối request không phải internal bằng 0x56. Đây là rào cản host có thể xác định từ code, nhưng trace runtime không chứng minh duy nhất đường thực thi đó đã là nơi trả status. Không có lý do để diễn giải 0x56 là TPC reconfig mask bằng 0.
3. `0x208001e7` wrapper của source [subdevice_ctrl_gpu_kernel.c:1893–1936](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/nvidia/src/kernel/gpu/subdevice/subdevice_ctrl_gpu_kernel.c#L1893) nằm trong `#if DEBUG || DEVELOP`, gọi GR `0x3b`. Release live báo `Release Build`; không khẳng định DEBUG/DEVELOP chỉ dựa vào chuỗi này, mà đối chiếu thêm bảng export release và kết quả thực nghiệm.

Script chỉ gửi GET qua RM ioctl, cấp object tạm, đóng file descriptor; không map BAR, gọi SET, viết MMIO/fuse hoặc reset. Handler GSP có các lời gọi ảo chưa phân giải hoàn toàn; control internal bị từ chối trong thử nghiệm, nên không khẳng định đã kiểm tra được mọi side effect có thể xảy ra nếu nó được gọi nội bộ. [`LIVE_RM_CANDIDATES_V2.json`](LIVE_RM_CANDIDATES_V2.json) là raw request/response và status từng control; bản V1 dùng script SHA `a9b4aeb9935293db58d4950159ad9249c696f97b203d0b0b4ac24bd325fe2283`, bản V2 dùng script được lưu cùng báo cáo. User-level ioctl không cho biết PC chính xác trả status.

## Raw fuse / firmware / effective

| Lớp | Phát hiện | Có chứng minh nguồn mask TPC? |
|---|---|---|
| OTP / RIR raw | Không đọc; tool GA100 thực tế ghi FUSECTRL/FUSEADDR/DEBUGCTRL kể cả khi dump RIR | Không |
| OPT / defective TU106 | Header TU102 công khai có OPT NVDEC/GSP debug, không có TPC disable/defect; [envytools pfuse.xml](https://github.com/envytools/envytools/blob/f102b82381f3f11cee113d16374c87091db039d9/rnndb/bus/pfuse.xml) có tên `TPC_DISABLE_MASK` trong map lịch sử chung nhưng không chứng minh nội dung địa chỉ tương ứng TU106 | Không; không đọc địa chỉ chưa xác thực |
| Firmware reconfiguration | Entry/hàm ảo GSP tồn tại; GET bị từ chối từ userland | Không biết output hay input upstream |
| Firmware GR floorsweep | Handler GSP điền mask qua virtual call; pointer đích chưa phân giải | Biết producer cuối trước cache, không biết phép tính upstream |
| Static fuse-derived SM rate | GET V2 thành công và đọc cached SM speed-select | Không liên quan TPC disable; không gọi raw OTP |
| Effective topology | Mask đầu vào lịch sử `1f/3f/3f` qua GET RM | Có topology, không đủ xác định nguyên nhân |

## GA100 đối chiếu TU106

Đã đọc code [ga100_rir.c commit 03a612a](https://github.com/lixiangwuxian/170hx-rir-tool/blob/03a612af5f6ebfdd8df50fe9e88cacce7c512a54/ga100_rir.c), [gpc_probe.py commit 7aa144b](https://github.com/matstatman/gpcprobe/blob/7aa144b81c06c98f3210118ba8ab2e707ddeeb13/gpc_probe.py) và [ghi chép GA100](https://github.com/Consensus-Protocol/cmp170hx/blob/main/docs/unlock/register-reference.md). Nhãn ở đó là mô hình và dữ liệu cộng đồng GA100; không mặc định là định nghĩa NVIDIA cho TU106.

| Cơ chế GA100 | Phát hiện TU106 trong phiên này |
|---|---|
| OPT disable / defective | Không tìm được TPC OPT/defective TU106 đáng tin; không thể suy nguyên nhân từ active mask |
| RECONFIG | Có GSP RM method reconfigurable mask, nhưng không chứng minh tương đương GA100 register hoặc đọc được trên card |
| CTRL_OPT / RECONF_OVR | Chưa xác nhận TPC override TU106, địa chỉ, cực tính, hoặc trạng thái |
| STATUS_OPT | Có effective RM topology nhưng không chứng minh nó là bản sao trực tiếp fuse STATUS TU106 |
| SW override gate / CP | Có GA100 definitions và ghi chú gate ở code; chưa xác nhận gate TPC hoặc CP TU106 |
| RIR | GA100 code có encoder và lệnh đọc/ghi; chưa xác nhận cấu trúc, số slot hay gate TU106. Lệnh dump RIR của tool có **ghi MMIO điều khiển**, do đó không chạy |
| Defective ≠ disabled | Là phân biệt logic hữu ích; không có defect map TU106 để áp dụng cho mẫu |

Một [patch GA100 của cmpunlocker](https://github.com/amoghmunikote/cmpunlocker/blob/2c7e2ecd7944e791fec040d2680036beb4a9327b/driver/patches/sec2-postbl-plm-ss-cfg.patch#L173) đọc STATUS trước/sau khi ghi RECONF_OVR; đây là mô tả mã thí nghiệm, không tự chứng minh kết quả trên mọi card. [CMP.WIKI Full SM unlock](https://cmp.wiki/wiki/Full_SM_unlock) tường thuật mô hình `STATUS = OPT | (RECONFIG & ~OVR)` và các báo cáo 70→74 SM; trang ghi chép GA100 khác dùng cách mô tả fuse floor có thể gây nhầm giữa OPT và RECONFIG. Không giải quyết mâu thuẫn đó bằng cách chọn một kết luận làm đúng cho TU106. Không dùng địa chỉ, công thức OR, cực tính hoặc quy trình ghi GA100 để kết luận TU106. Một register `STATUS` hay fuse-derived có thể đã chịu các tầng điều chỉnh; chữ `OPT` không tự chứng minh byte đọc được là vật lý OTP thô.

## Phép thử có khả năng phân biệt giả thuyết

Ưu tiên hoàn toàn chỉ đọc: phân giải function pointer `+0x130` cho đúng đối tượng TU106 trong GSP bằng truy vết constructor/HAL table theo firmware được hash; dựng dataflow tới ít nhất một nguồn register hoặc trường được khởi tạo. Đối chiếu định nghĩa register Turing độc lập và kiểm tra ngữ nghĩa đọc, security, cực tính, index cũng như side effects; sau đó mới đọc thụ động các register TU106 đã xác nhận và lưu raw cùng timestamp. So sánh trên cùng card:

- Nếu một nguồn OTP/disable TU106 đã xác thực đặt bit tương ứng và các tầng reconfig/override không bổ sung bit đó, điều này ủng hộ disable có nguồn fuse; vẫn chưa xác định defect hay tính lành.
- Nếu OTP/disable được xác thực không đặt bit tương ứng nhưng một trạng thái policy/reconfig/override xác thực đặt bit, ủng hộ tầng sau fuse là nguyên nhân; phải chứng minh ánh xạ và tính đầy đủ của các tầng trước khi loại trừ OTP khác.
- Đọc defect flag TU106 độc lập nếu có, đối chiếu disable: flag là phân loại sản xuất, không phải phép thử chức năng. Không có những nguồn độc lập này thì hai giả thuyết vẫn tương đương quan sát.

Điều kiện tiên quyết: tài liệu/trace đủ xác thực; chưa có chứng cứ để đọc thăm dò địa chỉ GA100 trên TU106 hoặc điều khiển fuse controller. Không ghi MMIO/OTP/RIR, flash, reset hay bật TPC trong phiên này.

## Evidence ledger

| ID | Artifact | Ý nghĩa và giới hạn |
|---|---|---|
| L1 | [LIVE_IDENTITY.txt](LIVE_IDENTITY.txt), [LIVE_ADDITIONAL.txt](LIVE_ADDITIONAL.txt) | Capture SSH mới UUID, BDF, driver/GSP, file hash; file hash không phải hash image resident |
| L2 | [LIVE_RM_CANDIDATES_V2.json](LIVE_RM_CANDIDATES_V2.json), [probe_rm_get.py](probe_rm_get.py) | 0x3b/e7/internal bị 0x56; alternative 0x3c thành công; JSON ghi raw bytes |
| L3 | [GSP_DISPATCH.json](GSP_DISPATCH.json), 3 file ASM | Binary GSP 615.71.09; method entries/handler được kiểm toán có giới hạn |
| L4 | [raw/ssh_batch_stderr.txt](raw/ssh_batch_stderr.txt), [raw/ssh_batch_exit.txt](raw/ssh_batch_exit.txt) | Batch key auth không thành công; sau đó password SSH thành công, không phải lỗi mạng GPU |
| L5 | [SHA256SUMS_CONTINUED](SHA256SUMS_CONTINUED) | Hash mọi artifact mới; `SOURCE_SHA256.txt` của lần trước giữ riêng. Firmware outer SHA `78e0a2c8e4bd8a2faa1ff36137209669cdf60bd698b8f723dcf52869df82b909`, embedded ELF SHA `afa9ce3f65c28e1f6ab8c449e20e08bbb273855e3a97b1f5d332f57dfa9d68ea` |
| L6 | [SOURCE_PROVENANCE.txt](SOURCE_PROVENANCE.txt) | Commit, hash và nguồn công khai của các file GA100 đã đối chiếu |
| L7 | [LIVE_KERNEL_LOG.txt](LIVE_KERNEL_LOG.txt) | `journalctl` không có entry sau truy vấn; không chứng minh chắc chắn không có thay đổi trạng thái GPU |

Giới hạn hiện tại: chưa truy tới implementation của function pointer TPC TU106, chưa quan sát trực tiếp raw fuse/reconfig/defect, và chưa instrument kernel để xác nhận PC của từng lỗi 0x56. Những giới hạn này không thể xóa bằng cách đếm lại SM hay bằng suy luận từ GA100.

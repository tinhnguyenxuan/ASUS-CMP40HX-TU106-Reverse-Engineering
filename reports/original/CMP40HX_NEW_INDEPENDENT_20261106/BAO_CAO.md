# Nghiên cứu độc lập CMP 40HX TU106: nguồn floorsweep

Ngày 06-11-2026. Phạm vi: kiểm toán lại ba đầu vào, NVIDIA open GPU kernel modules 615.71.09, tài liệu NVIDIA và CMP.WIKI. **Chưa có phép đo SSH mới**: thử SSH tới `REDACTED_USER@<REDACTED_LAB_IP>` bằng BatchMode bị sandbox từ chối tạo socket (`socket: Operation not permitted`), trước xác thực và trước khi chạy lệnh từ xa. Đây là lỗi môi trường cục bộ, không phải bằng chứng máy đích từ chối truy cập. Các giá trị live dưới đây là đầu vào cũ, không phải quan sát độc lập mới.

## Kết luận

- Đã truy vết thêm một tầng: trong nhánh khởi tạo bình thường, kernel RM gọi `NV2080_CTRL_CMD_INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS`, sao chép kết quả vào staticInfo, rồi graphics manager sao chép vào legacy cache; API topology đọc cache này. Vì vậy mask cũ là kết quả cuối của đường RM, chưa chỉ ra tín hiệu gốc. Mã công khai đã kiểm tra không giải thích cách phía phục vụ control nội bộ tạo mask từ fuse hoặc firmware. Không tự động gán toàn bộ logic này cho GSP mà chưa xác nhận mode/đường RPC và implementation trên máy.
- Whitepaper NVIDIA xác nhận full TU106 có ba GPC, sáu TPC mỗi GPC. Như vậy đối chiếu mask đầu vào `1f/3f/3f` với thiết kế đầy đủ xác định GPC0/TPC5 là vị trí thiếu trong topology được RM báo, nếu nhận dạng TU106 của mẫu đúng và chỉ số vật lý của API được hiểu đúng. Điều này củng cố giả thiết 18 slot nhưng không kiểm tra vật lý die cụ thể hoặc tính lành của slot.
- Chưa có dữ liệu cho phép quyết định OTP, reconfiguration, firmware policy hay defective state. Không chứng minh được có thể bật lại, cũng không chứng minh bất khả thi.
- Header TU102/Turing công bố trong source 615.71.09 chỉ có hai định nghĩa fuse unrelated tới TPC: không có bản đồ OPT/RECONFIG/OVR/RIR cho TPC. Đây là giới hạn tài liệu công khai, không chứng minh phần cứng TU106 không có các cơ chế đó. Các tên GA100 không thể được chuyển nguyên xi sang TU106.

## Kiểm tra nguồn và đường dữ liệu

Source cục bộ `/home/REDACTED_USER/.hermes/cache/scratch/ogk/open-gpu-kernel-modules-615.71.09`, `version.mk` ghi `615.71.09`; tên phiên bản không tự chứng minh mọi byte khớp bản phát hành, nên các hash quan trọng được ghi trong `SOURCE_SHA256.txt`. Đối chiếu đường dẫn với [tag NVIDIA 615.71.09](https://github.com/NVIDIA/open-gpu-kernel-modules/tree/615.71.09). NVIDIA nêu kernel modules phải khớp phiên bản GSP firmware và userspace; chưa kiểm tra lại việc khớp trên máy live trong phiên này.

1. [`kernel_graphics.c` 1258–1270](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/nvidia/src/kernel/gpu/gr/kernel_graphics.c#L1258): `pRmApi->Control` lấy `INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS`, rồi `portMemCopy` phần `floorsweepingMasks[grIdx]`. File cũng có đường sao chép từ VSI ở dòng 893 và 1022; không suy mọi cấu hình đều cùng một đường.
2. [`kernel_graphics_manager.c` 377–378, 610–627](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/nvidia/src/kernel/gpu/gr/kernel_graphics_manager.c#L377): static info được sao vào legacy cache; `kgrmgrGetLegacyTpcMask` đọc `tpcMask[gpcId]`. [Control GR](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/nvidia/src/kernel/gpu/gr/kernel_graphics.c#L3600) cũng trả trường này trong static info. Cấu trúc internal có cả `gpcMask`, `physGpcMask`, `tpcMask`, `tpcCount` và mapping; tên `phys` không biến tất cả mask thành raw OTP.
3. [TU102 dev_fuse.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/common/inc/swref/published/turing/tu102/dev_fuse.h) không cung cấp bit TPC, reconfig, defect hay RIR. Việc ký hiệu `OPT` xuất hiện cho NVDEC/GSP debug chứng minh cách đặt tên fuse ở header, không chứng minh register TPC tương đương GA100.
4. [Whitepaper Turing appendix B](https://www.nvidia.com/content/dam/en-zz/Solutions/design-visualization/technologies/turing-architecture/NVIDIA-Turing-Architecture-Whitepaper.pdf#page=61): full TU106 có sáu TPC/GPC. Đây là kiến trúc danh định, không phải ảnh die hay báo cáo sức khỏe của mẫu CMP.

## API còn có thể khảo sát

- [`GR_GET_TPC_RECONFIG_MASK`, 0x2080123b](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gr.h#L1988): input `gpc` là **logical index**, output là mask TPC reconfigurable, có `grRouteInfo` căn 8 byte. Không đồng nhất logical GPC với physical nếu chưa chứng minh mapping. Header không nói mask này là OTP, defective hay là các TPC có thể phục hồi. Chưa xác minh implementation, định tuyến, quyền, ABI đầy đủ, tính hỗ trợ TU106, hay giá trị live; không coi tên là bằng chứng GA100 register.
- [`GPU_GET_TPC_RECONFIG_MASK`, 0x208001e7](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gpu.h#L4683), input/output hai `NvU32`; wrapper ở [`subdevice_ctrl_gpu_kernel.c` 1893–1935](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/nvidia/src/kernel/gpu/subdevice/subdevice_ctrl_gpu_kernel.c#L1893) được bao `DEBUG || DEVELOP`, gọi GR control. Do đó không được khẳng định wrapper tồn tại trong build production. GR control có routing và khả năng export riêng; chưa thể kết luận từ wrapper rằng GR control không hoạt động.
- [`INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS`](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.71.09/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080internal.h#L303) cung cấp thêm topology và metadata, nhưng là interface nội bộ; cần xác nhận quyền, kích thước và ngữ nghĩa trước khi gọi. Kể cả thành công, nó có thể chỉ trả lại cùng kết quả đã xử lý, không nhất thiết là phép đo độc lập của fuse.
- Kiểm tra thêm RM fuse interface và sysfs/NVML có thể hữu ích, nhưng không tìm thấy trong các header được rà một API công khai chứng minh đọc riêng OTP/defect TPC TU106. Không diễn giải lỗi `NOT_SUPPORTED` hay access denied là giá trị zero hoặc bằng chứng không có phần cứng.

## Đối chiếu GA100

[CMP.WIKI](https://cmp.wiki/wiki/Fuses_and_floorsweep_maps) và [nguồn cộng đồng GA100](https://github.com/Consensus-Protocol/cmp170hx/blob/main/docs/hardware/ga100-silicon.md) phân biệt các lớp OPT disable, RECONFIG, CTRL_OPT/override, STATUS và defective; đây là quan sát/diễn giải cộng đồng, không phải tài liệu TU106. [Công cụ 170HX](https://cmp.wiki/wiki/170hx-rir-tool) mô tả RIR tác động gate software override trên một biến thể GA100; bản thân ghi gate không chứng minh SM lành. Ngay cả lệnh gắn tên dump/read có thể ghi thanh ghi điều khiển để chọn hàng hoặc đổi chế độ truy cập; không sử dụng tool GA100 cho TU106, không giả định đọc RIR là thụ động, và không lấy địa chỉ/công thức GA100 làm TU106.

| Giả thuyết | Đánh giá |
|---|---|
| `0x1f` trực tiếp là OTP raw | Bác bỏ cách diễn giải API: source cho thấy giá trị cached topology; chưa bác bỏ khả năng một OTP upstream tạo ra cùng kết quả. |
| Firmware policy là nguyên nhân duy nhất | Chưa kiểm chứng; không có dữ liệu tách lớp. |
| OTP fuse disable TPC5 | Chưa kiểm chứng; status hiệu dụng không đủ chứng minh OTP gốc, cần bản đồ fuse xác thực và phép đọc phù hợp. |
| TPC5 defective / hoạt động tốt | Cả hai chưa kiểm chứng; disable không đồng nghĩa defective, kể cả defective flag nếu tìm được cũng là trạng thái đánh dấu, không thay thế kiểm thử chức năng. |
| Reconfiguration/override GA100 tồn tại và có cùng ngữ nghĩa/địa chỉ trên TU106 | Chưa chứng minh; tên control chung không đủ chứng cứ. |
| Không có override vì header TU102 không định nghĩa | Bác bỏ suy luận từ bằng chứng thiếu: header chỉ là tập công bố. |
| Có thể khôi phục hoặc không thể khôi phục | Chưa kiểm chứng; mask hoặc thay đổi báo cáo software đơn thuần không chứng minh hoạt động chức năng. |

## Phép đo kế tiếp khi SSH hoạt động

1. Chụp mới UTC, UUID/BDF, PCI ID, driver, GSP mode/version, module flavor; ghi lệnh, stdout/stderr, exit code và hash công cụ. Xác minh mẫu và phiên bản trước khi so sánh.
2. Kiểm toán ABI và quyền rồi gọi GET reconfig cho từng logical GPC và ghi status riêng, không mặc định mapping. Đối chiếu với GPC physical mapping và mask effective; ghi rõ control có thể chỉ là reconfigurability chứ không phải trạng thái disable. Ghi trường hợp unsupported/denied như kết quả âm tính có giới hạn.
3. Truy từ implementation phía firmware hoặc tài liệu TU106 độc lập đến từng lớp OPT, reconfiguration, defect, gate và status, cả cực tính, index, security và tính side effect. Chỉ đọc thanh ghi khi đã có provenance TU106 đáng tin và xác nhận đường đọc không cần write điều khiển. Cần các quan sát tách biệt trên cùng card, và nếu có thể mẫu TU106 đối chứng. RIR command cần audit toàn bộ side effect; không dùng chuỗi write-select dưới quyền hiện tại.
4. Phân biệt policy bằng chứng cứ về inputs firmware và quan sát trước/sau có kiểm soát chỉ khi được phép; tìm defect flag độc lập và cuối cùng kiểm thử chức năng riêng nếu một thay đổi trong tương lai được phê duyệt. Không thực hiện override, ghi MMIO, fuse, reset hay chạy thử phục hồi trong nghiên cứu này.

Đầu vào lịch sử: [báo cáo](../PHASE_TU106_FLOORSWEEP_INDEPENDENT/BAO_CAO_MOI_TPC_CMP40HX.md), [truy vết RM](../PHASE_TU106_FLOORSWEEP_INDEPENDENT/RM_TOPOLOGY_FINDINGS.md), [kết quả RM](../PHASE_TU106_FLOORSWEEP_INDEPENDENT/LIVE_RM_QUERY_V2.json). Tệp JSON là stdout được lưu trong JSON, với script hash và exit code, nhưng không có chứng thực mật mã gắn phép đo với card; không thay thế phép đo hiện tại.

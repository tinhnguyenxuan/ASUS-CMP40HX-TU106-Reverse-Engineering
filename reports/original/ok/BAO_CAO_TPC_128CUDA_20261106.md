# CMP 40HX — nghiên cứu TPC / 128 CUDA cores

Ngày 2026-11-06. Phạm vi: dữ liệu đã lưu, source driver và hai bài báo; không ghi MMIO, không override, không đổi firmware. Đây là báo cáo **chưa hoàn tất**: chưa truy vấn được physical TPC mask từ RM, không xác định vị trí TPC bị tắt.

## 1. Kết luận

CUDA đã báo 34 SM trên GPU 0000:03:00.0 trong capture trước; cấu hình tham chiếu 36 SM chênh 2 SM, tương đương 128 CUDA cores theo kiến trúc tham chiếu. Không có bằng chứng hiện tại rằng TPC bổ sung còn tốt hoặc có thể khôi phục. Cũng không có bằng chứng nó bị cắt transistor hoặc hư vật lý. Không gán xác suất.

| Lớp | Giá trị | Tình trạng |
|---|---|---|
| Physical die trên CMP | số GPC/TPC có transistor, physical coordinates, sức khỏe từng TPC | UNKNOWN |
| Cấu hình TU106 tham chiếu | RTX 2070 36 SM, tức 18 TPC nếu 2 SM/TPC | tham chiếu, không phải chứng minh die cụ thể |
| Topology đang hoạt động | 34 SM theo CUDA, 17 TPC nếu áp dụng 2 SM/TPC | 34 SM đo được trước; 17 TPC là suy luận kiến trúc |
| GPC → mask TPC theo driver | chưa có kết quả RM query gắn BDF này | UNKNOWN |
| SM logical → GPC/TPC physical | chưa có mapping đã xác thực | UNKNOWN |
| Vị trí TPC thứ 18 | GPC ID và TPC slot không xác định | UNKNOWN; không giả định GPC cuối hay bit cuối |

## 2. Dump fuse lịch sử

Nguồn `input/ASTRA_CMP40HX_HANDOFF/04_PHASE15_EXTRACTS/FUSE/fuse2.json`, base `0x21000`. Đọc keys decimal; thời điểm/chuỗi thu thập cần kiểm thêm. Đây là giá trị đọc được, không tự động là OTP:

| Offset tương đối | Địa chỉ | Raw | Diễn giải TPC trên TU106 |
|---|---|---:|---|
| 0x524 | 0x21524 | 0x00000000 | UNKNOWN |
| 0x650 | 0x21650 | 0x0004001f | UNKNOWN |
| 0xc1c | 0x21c1c | 0x00000038 | UNKNOWN, chưa suy mask GPC/TPC |

Các số trên không phải fuse masks được giải mã. Các báo cáo cũ gán 0x1f hay 0x4001f vào một GPC chỉ từ trùng số là không đủ chứng cứ. `0x21524` bằng **0 trong file này**, trái một số diễn giải cũ. Không sử dụng tên GA100/Ada làm định nghĩa TU106.

## 3. Đường truy vấn driver có triển vọng

Source local `/tmp/nvsrc/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080grmgr.h` khai báo `NV2080_CTRL_CMD_GRMGR_GET_GR_FS_INFO = 0x20803801`, query 1 GPC_COUNT, 2 CHIPLET_GPC_MAP, 3 TPC_MASK. Đầu vào TPC_MASK là logical/local GPC ID; tài liệu struct mô tả kết quả là physical TPC mask trong các trường hợp client được hỗ trợ. Phải đọc status của từng query và phân biệt ID chiplet/logical. `/tmp/nvsrc/nvidia/generated/g_hal_stubs.h` liệt kê TU10X cho RPC tương ứng. Đây là bằng chứng API/source tồn tại, **không phải kết quả runtime** và chưa chứng minh phiên bản local khớp 615.71.09.

Ngày 2026-11-06, SSH đến <REDACTED_LAB_IP>:22 timed out; không có capture mới. Chưa triển khai/call NV2080 RM control: còn phải xác minh source exact-tag, client/subdevice handles, ABI, permissions và side effects. Không nạp nvdebug hay driver mới. Nếu query thành công, lưu UUID/BDF/version, raw request/response, individual NV_STATUS, GPC-map và TPC masks; đối chiếu tổng bit TPC với 34 SM, không giả định zero bits chứng minh transistor.

## 4. Hai bài báo và đánh số

[Bakita & Anderson, Hardware Compute Partitioning on NVIDIA GPUs](https://par.nsf.gov/servlets/purl/10480322): phần IV/Fig. 5 so sánh hai mẫu GTX 1060 3GB GP106 cùng 9 SM nhưng vị trí TPC không hoạt động khác nhau giữa GPC0/GPC1; logical TPC numbering được đánh lại. Đó là bằng chứng vị trí không thể suy chỉ từ SKU/count, không phải quan sát CMP này. Mask dùng để chia workload trên các SM/TPC đã khả dụng; không phải bằng chứng mở TPC bị floorsweep.

[Bakita & Anderson 2025](https://drops.dagstuhl.de/storage/00lipics/lipics-vol335-ecrts2025/html/LIPIcs.ECRTS.2025.21/LIPIcs.ECRTS.2025.21.html): SM ID–GPC mapping có thể không liên tiếp và driver cấu hình xen kẽ; tác giả sửa giả định tuyến tính của libsmctrl. Vì thế không nhóm SM ID thành các đoạn liên tiếp để đoán physical GPC. Đây là kết quả phương pháp, không phải bản đồ xác minh cho card này.

Mã [libsmctrl](https://github.com/atomicapple0/libsmctrl/blob/master/libsmctrl.c) đọc `/proc/gpu*/gpc*_tpc_mask` từ module nvdebug, bỏ slot bị disable và đánh lại index. Không thể đánh đồng mask logic thu được với OTP hoặc vị trí hình học trên die. Module đó chưa xác nhận hiện diện trên target và không được nạp trong nghiên cứu này.

## 5. Fuse, defect và override

| Giả thuyết | Dữ liệu phân biệt cần có | Kết luận |
|---|---|---|
| Fuse/status disable | Định nghĩa TU106 đúng stepping, polarity, provenance và luồng GSP→mask | UNKNOWN |
| Defective fuse/đơn vị hỏng | Field defective TU106 và kết quả tương ứng, hoặc kiểm định phần cứng độc lập | UNKNOWN |
| Runtime mask/policy | Source dataflow của TPC mask, trạng thái cấu hình và đối chứng cùng chip | UNKNOWN |
| Logical renumbering | RM physical mask + ánh xạ GPC và SM IDs | Chưa quan sát được |
| Software override TU106 | Định nghĩa và caller TU106 exact tag chứng minh cơ chế và điều kiện | Chưa tìm được, không suy từ GA100 |

Truy vấn trạng thái hoặc cùng thiết kế die không chứng minh TPC không hoạt động còn tốt. Xác nhận chức năng 2 SM chưa được enumerate cần bằng chứng chức năng riêng; bài toán đó vượt phạm vi read-only hiện tại.

## 6. Các tiền lệ

- GP106 GTX 1060 3GB/6GB là ví dụ cấu hình khác nhau và Fig.5 cho thấy vị trí floorsweep khác nhau giữa hai mẫu. Không phải chứng cứ đã bật lại TPC thiếu.
- NV40 GeForce 6800 từng có báo cáo softmod mở pipeline trên một số card. Đây là thế hệ/cơ chế khác, không chứng minh TU106 có override hoặc SM CMP còn tốt.
- Radeon HD 6950 từng có báo cáo thay BIOS để mở thêm shader trên một số mẫu. Kiến trúc, fuse và cơ chế boot khác; không suy rộng sang NVIDIA/TU106 hoặc tất cả mẫu 6950.

## 7. Nghiên cứu tiếp theo không ghi

1. Xác minh tag nguồn 615.71.09 và hợp đồng RM query, sau đó thu GPC_COUNT/CHIPLET_GPC_MAP/TPC_MASK nếu card truy cập được và phương thức an toàn.
2. Đối chiếu GSP firmware 615.71.09 đã lưu với source/caller và provenance, tìm nơi khởi tạo cấu trúc floorsweep; không patch.
3. Tìm TU106-specific documentation cho disable vs defective và nguồn của status; nếu thiếu thì giữ UNKNOWN.
4. So sánh mẫu RTX 2060 SUPER/2070 với dữ liệu có provenance và cùng version; đối chứng loại trừ một số giả thuyết, không chứng minh TPC card CMP này tốt.
5. Chỉ khi có mapping và nguồn mask đủ chắc mới phân loại theo GPC/slot; không hứa kết luận về health hoặc phục hồi từ read-only.

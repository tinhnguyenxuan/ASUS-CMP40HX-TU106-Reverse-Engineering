# Báo cáo mới: TPC và khả năng khôi phục 128 CUDA cores trên CMP 40HX

**Trạng thái:** Đã đo được topology hiệu dụng; chưa xác định nguyên nhân TPC không hoạt động hay khả năng khôi phục.

**Thời điểm truy vấn:** 17:49:18 UTC ngày 05/11/2026, tương đương 00:49:18 ngày 06/11/2026 theo giờ Bangkok.

## 1. Kết luận chính

Driver của card báo có **17 TPC đang hoạt động, gồm 34 SM**. Mask cho thấy **TPC 5 của GPC 0 không nằm trong tập đang hoạt động**. Nếu die của card này có sáu slot TPC trên mỗi GPC như cấu hình đầy đủ dùng để so sánh, GPC 0 / TPC 5 là ứng viên cho TPC thứ 18.

Mask không cho biết slot đó có transistor hiện diện, còn hoạt động tốt hay bị vô hiệu hóa ở tầng nào. Vì vậy, việc khôi phục thêm **2 SM / 128 CUDA cores** hiện vẫn là **chưa xác định**, không phải đã thành công hoặc đã chứng minh bất khả thi.

## 2. Danh tính và dữ liệu mới

| Thuộc tính | Giá trị |
|---|---|
| GPU | NVIDIA CMP 40HX, PCI ID `10de:1f0b` |
| PCI BDF | `0000:03:00.0` |
| UUID | `GPU-REDACTED` |
| Driver | `615.71.09` |
| VBIOS | `90.06.67.00.06` |
| Số SM theo CUDA | 34 |

Danh tính và phiên bản được thu từ máy card qua SSH, lưu tại [LIVE_CAPTURE_20261106.json](LIVE_CAPTURE_20261106.json). Kết quả CUDA được lưu tại [LIVE_CUDA_SM_QUERY.json](LIVE_CUDA_SM_QUERY.json).

## 3. TPC mask đọc qua NVIDIA Resource Manager

| Physical GPC ID | Mask TPC hoạt động | Các TPC đang hoạt động | TPC | SM |
|---|---:|---|---:|---:|
| 0 | `0x1f` | 0, 1, 2, 3, 4 | 5 | 10 |
| 1 | `0x3f` | 0, 1, 2, 3, 4, 5 | 6 | 12 |
| 2 | `0x3f` | 0, 1, 2, 3, 4, 5 | 6 | 12 |
| **Tổng** | — | — | **17** | **34** |

GPC mask là `0x7`. Các lệnh GET GPC mask, TPC mask và SM mapping đều trả `NV_OK`. Tập 34 SM trong mapping khớp với 17 bit TPC hoạt động; mỗi TPC hoạt động có hai SM trong mapping.

Thứ tự SM ID được driver trả về xen kẽ giữa các GPC; không thể suy vị trí GPC bằng cách chia dãy SM ID thành ba đoạn liên tiếp. Toàn bộ mapping và kết quả thô ở [LIVE_TPC_TOPOLOGY.json](LIVE_TPC_TOPOLOGY.json) và [LIVE_RM_QUERY_V2.json](LIVE_RM_QUERY_V2.json).

## 4. Vì sao mask này chưa giải đáp fuse

Source NVIDIA đúng tag `615.71.09` cho thấy handler `GET_TPC_MASK` lấy mask từ `kgrmgrGetLegacyTpcMask`, hàm này trả trường `floorsweepingMasks.tpcMask[gpcId]` đã được driver lưu. Đây là **topology hiệu dụng do driver công bố**; đường tạo giá trị ban đầu từ fuse, firmware và các cấu hình khác chưa được xác minh đầy đủ.

Trong header cùng tag có control `GET_TPC_RECONFIG_MASK`. Sự tồn tại của tên và cấu trúc control là một đầu mối nghiên cứu, nhưng chưa chứng minh control được hỗ trợ trên TU106 của card này, cũng chưa chứng minh TU106 có cơ chế override tương đương GA100. Chưa gọi control này trên card.

| Câu hỏi | Trạng thái hiện tại |
|---|---|
| GPC 0 / TPC 5 được driver báo đang hoạt động? | **Không:** bit 5 của active mask bằng 0. |
| Đây có phải slot TPC thứ 18 của die này? | **Có điều kiện:** là ứng viên nếu GPC 0 có sáu slot; chưa xác minh trực tiếp sự hiện diện vật lý. |
| TPC bị OTP/fuse disable? | **Chưa biết.** |
| TPC bị đánh dấu defective hay hỏng? | **Chưa biết.** |
| Firmware hoặc software reconfiguration có vai trò? | **Chưa biết.** |
| Có thể bật lại và chạy đúng 2 SM? | **Chưa chứng minh.** |

## 5. Kiểm chứng và phạm vi thao tác

Truy vấn đầu bằng tài khoản thường và bằng sudo đều trả mã `0x1b` khi cấp đối tượng GPU RM. Đối chiếu source cho thấy driver kiểm tra tiến trình có mở file descriptor của thiết bị GPU. Sau khi script mở `/dev/nvidia0` và giữ descriptor đó, cùng truy vấn đã thành công bằng tài khoản thường.

Script cấp các đối tượng RM tạm để gọi lệnh GET; kết quả, mã trả về và hash script được lưu cùng artifact. Không ghi MMIO/BAR, không sửa fuse, không reset GPU và không thử kích hoạt TPC.

## 6. Hướng nghiên cứu tiếp theo

1. Truy nguồn tạo `floorsweepingMasks.tpcMask` trong GSP/driver `615.71.09`, phân biệt dữ liệu fuse với cấu hình firmware.
2. Kiểm toán ABI, quyền và khả năng hỗ trợ TU106 của `GET_TPC_RECONFIG_MASK` trước khi cân nhắc truy vấn chỉ đọc.
3. Tìm định nghĩa TU106 đáng tin cậy cho các trường disable và defective; đối chiếu với dữ liệu có provenance của card TU106 khác.
4. Xác minh số slot vật lý theo GPC cho đúng die/stepping. Dù xác định được mask, cần bằng chứng chức năng riêng mới biết một TPC bị vô hiệu hóa còn hoạt động tốt hay không.

Chi tiết source và cách kiểm chứng: [RM_TOPOLOGY_FINDINGS.md](RM_TOPOLOGY_FINDINGS.md). Danh mục hash artifact: [SHA256SUMS](SHA256SUMS).

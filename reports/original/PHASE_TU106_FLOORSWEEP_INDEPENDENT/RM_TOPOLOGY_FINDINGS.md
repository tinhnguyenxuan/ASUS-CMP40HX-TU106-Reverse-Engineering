# Kết quả RM topology — 615.71.09

Thời gian UTC: 2026-11-05T17:49:18.115907+00:00
GPU UUID GPU-REDACTED; BDF 0000:03:00.0; xác thực đối chiếu LIVE_CAPTURE_20261106.json. Raw, mã trả về và SHA script: LIVE_RM_QUERY_V2.json. NVIDIA source tag615.71.09 commit 61dcc93722ecb418bb5f2e00923f05b4b8051dd1.

| Physical GPC | Active TPC mask | Active slots | TPC | SM |
|---|---:|---|---:|---:|
| 0 | 0x1f | 0,1,2,3,4 | 5 | 10 |
| 1 | 0x3f | 0,1,2,3,4,5 | 6 | 12 |
| 2 | 0x3f | 0,1,2,3,4,5 | 6 | 12 |

Mask bit5 GPC0 không bật. Nếu TU106 này có 6 slot TPC mỗi GPC thì GPC0/TPC5 là slot còn thiếu; số slot vật lý/đơn vị tồn tại và tình trạng sức khỏe không được chứng minh bằng mask. Bản đồ từng SM trong LIVE_TPC_TOPOLOGY.json; 17 cặp TPC mỗi cặp2SM, trùng các mask. ID đan xen, không chia liên tục theo GPC.

API GET_TPC_MASK handler theo tag lấy kgrmgrGetLegacyTpcMask, trả tpcMask[gpcId] được cache; GET_SM_TO_GPC_TPC_MAPPINGS trả globalSmOrder. Do đó là topology driver, không phải fuse raw. Các control cấp client/device/subdevice tạm và GET, không ghi MMIO/fuse/reset/override. Thử đầu user và sudo trả 0x1b khi chưa mở /dev/nvidia0; driver nv_is_gpu_accessible kiểm tra file descriptor của GPU. Mở node thiết bị trong tiến trình rồi thành công với user thường.

GET_TPC_RECONFIG_MASK có trong ctrl2080gr.h dòng1988; wrapper GPU được bao DEBUG/DEVELOP trong subdevice_ctrl_gpu_kernel.c:1893; việc có tên không chứng minh TU106 có hoặc cho phép override. Chưa kiểm tra chức năng này live, và không suy công thức GA100.

UNKNOWN: nguyên nhân bit0, nguồn OTP/defective/soft policy, tình trạng transistor, khả năng khôi phục. Không chứng minh thành công hoặc bất khả thi.

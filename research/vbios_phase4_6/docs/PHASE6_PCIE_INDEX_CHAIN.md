# Phase 6 — P-state / LOW POWER / PCIe mapping (ROM-only)

**Phạm vi:** tổng hợp phần phân tích tĩnh của `PHASE6_MASTER_REPORT_VI.md` trong gói đầu vào. Bản GitHub này **không** mang theo công cụ đo thực tế hoặc test game.

## Chuỗi tham chiếu nhận diện

```text
PERFORMANCE v0x60: P-state.lpwr_entry_idx
       -> P2 slot 29 (LOW POWER index table), entry N
       -> entry byte 0: pcie_idx
       -> P2 slot 30 (LOW POWER PCIe), entry pcie_idx
```

- Slot 29 có cấu trúc quan sát `{ver=0x10, hlen=6, entry_size=7, count=5}`: `6+5×7=41` byte, kết thúc ngay đầu slot 30.
- Năm byte đầu của một entry tương ứng các index `pcie_idx, gr_idx, ms_idx, di_idx, gc6_idx` trong `nvgpu`; TU106 có 2 byte mở rộng chưa đủ bằng chứng định danh.
- Byte đầu của các entry slot 29 lần lượt là `0,1,2,2,2`; byte thứ 6 (index 6, đếm từ 0) lần lượt `0,1,2,3,4`.
- Theo báo cáo nguồn, trên ba ROM có **10/10** đường tham chiếu nhất quán; **không xác minh lại trên ROM trong bản phát hành này**, vì ROM không được phát hành.

| ROM | Chuỗi theo các P-state hiện hữu (như nguồn báo cáo) |
|---|---|
| CMP 40HX | `0x07→0→0→0`, `0x0C→4→2→2`, `0x0F→4→2→2` |
| RTX 2060 SUPER / RTX 2070 | `0x07→0→0→0`, `0x0A→1→1→1`, `0x0C/0x0D/0x0F→4→2→2` |

**Giới hạn quan trọng:** Có thể chứng minh cách các index được liên kết trong ROM qua parser/struct, **không chứng minh** consumer trong driver/GSP đọc chúng theo cách đó ở runtime. Chưa xác định ý nghĩa payload 12 byte của slot 30; không được gọi byte chênh lệch là công tắc PCIe Gen 1/3.

Nguồn trong gói đầu vào: `docs/PHASE6_MASTER_REPORT_VI.md`, phần 1; đối chiếu thêm [VBIOS Field RE](VBIOS_FIELD_REVERSE_ENGINEERING.md), [PCIe Register Deep Reverse](TU106_PCIE_REGISTER_DEEP_REVERSE.md).

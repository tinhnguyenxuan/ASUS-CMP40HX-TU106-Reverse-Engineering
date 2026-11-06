# T04 — Chuỗi display fuse-status, OTP và đường host driver (CMP 40HX / TU106)

Phạm vi: chỉ `NV_FUSE_STATUS_OPT_DISPLAY` (0x021C04) + caller host liên quan. Không giải toàn bộ fuse bank; không đọc BAR mới (R0 offline). Ngày làm: 2026-11-04 (UTC).

## 0. Input

Đủ theo nhiệm vụ. Lưu ý path: `TOOLS/` nằm tại `04_PHASE15_EXTRACTS/TOOLS/` (không phải `TOOLS/` cấp gốc như mô tả) — chứa `fuse_dump2.py`, `fuse_read.py`, chỉ đọc mã, KHÔNG chạy. Hash 12 file input khớp `CHECKSUMS.sha256` (tra ngày 2026-11-04). Các evidence JSON Phase-21 dùng làm đầu vào đối chiếu, không coi là bằng chứng độc lập mới.

## 1. Tái dựng provenance đo 0x21C04 (MEASURED — lưu trữ)

**fuse_dump2.py** (hash c2484927…): mở `/sys/bus/pci/devices/0000:03:00.0/resource0`, `mmap` PROT_READ 16 MB, đọc little-endian (`<I`) theo trang 4 KB từ `FUSE = 0x021000`, span mặc định 0x8000 (0x21000–0x29000). Key trong `regs` = **byte offset trong cửa sổ fuse**. Word tuyệt đối 0x021C04 ⇒ key 3076 (0xC04).

**fuse_read.py** (hash 58a99a69…): logic aperture KÉP trong cùng script — `base = 0x00820000`; nếu `addr >= base` thì `offset = addr − 0x820000`, **ngược lại** `offset = addr − 0x00021000`. Với 0x021C04: offset = 0xC04 trên resource0. Điểm rủi ro đã phân loại: hai aperture cùng một khối code; trên card này cửa sổ 0x820000 KHÔNG map fuse (P0_FUSE.md §1: 0x00820000 trả 0x166000a1 = giá trị PMC_BOOT_0, 53/64 register poison) ⇒ cửa sổ 0x21000 là aperture đúng cho TU106; tính đúng đắn của fuse_read.py với TU106 phụ thuộc giả định đó, không phải cấu hình tuyên bố.

**Giá trị lưu trữ** (`fuse2.json`, hash 0e770041…, không suy thời điểm đo từ mtime — capture_time = unknown):

| offset | register | giá trị |
|---|---|---|
| 0x0C04 | NV_FUSE_STATUS_OPT_DISPLAY | **0x00000001** |
| lân cận | 0x0C00=1, 0x0C08=0, 0x0C0C=0xF, 0x0C10=1 | — |
| 0x1378 | NV_FUSE_OPT_NVDEC_DISABLE | 0x0 (không disable) |
| 0x174C | NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS | 0x1 |

Khớp `fuse_bitfields.csv` (reg_value 0x1, field 1, DECODED) và `display_gate.json` (raw_archived 0x1).

## 2. Chuỗi host driver (DECODED từ nguồn chính thức, chốt tag)

Tag→commit đã xác minh qua GitHub API (annotated tag, tagger NVIDIA, chữ ký SSH có nhưng verification `unknown_key` — không xác minh được chữ ký):

- **615.78.08** → tag object 4bfe30bb → commit **1a82fbfda8f321b056eb3568850f9316c5e465c5** (tagged 2026-10-07)
- **615.71.09** → tag object d2a24f90 → commit **61dcc93722ecb418bb5f2e00923f05b4b8051dd1** (tagged 2026-09-09)

### 2.1 Bitfield nguồn (header @78.08, fetch trực tiếp)

`src/common/inc/swref/published/maxwell/gm107/dev_fuse.h`:

```c
#define NV_FUSE_STATUS_OPT_DISPLAY              0x00021C04 /* R-I4R */
#define NV_FUSE_STATUS_OPT_DISPLAY_DATA                 0:0 /* R-IVF */
#define NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE  0x00000000 /* R---V */
```

⇒ **ENABLE encoding = 0**, access R- (read-only từ PRI).

`src/common/inc/swref/published/turing/tu102/dev_fuse.h` chỉ định nghĩa 2 register: `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS` (0x2174C, RWIVF) và `NV_FUSE_OPT_NVDEC_DISABLE` (0x21378, RWIVF INIT=0) — **không** chứa STATUS_OPT_DISPLAY. Cầu nối địa chỉ cho họ TU thực sự là header GM107 (khớp kết luận `fuse_header_inventory.json`). So sánh access code: OPT_* là **RW-**IVF (có INIT value — kiểu opt/shadow), STATUS là **R-**IVF (chỉ đọc) — đầu mối cho phân tầng §4.

### 2.2 Dispatch HAL (cả hai tag, xác minh trực tiếp)

`src/nvidia/generated/g_gpu_nvoc.c` — `__nvoc_init_funcTable_OBJGPU`: TU102/TU104/**TU106**/TU116/TU117 → `gpuFuseSupportsDisplay_GM107`. Gán GM107 tại **dòng 2096 @78.08** (block 2093–2114) và **dòng 2107 @71.09** (block 2104–2125). Thân HAL `src/nvidia/src/kernel/gpu/arch/maxwell/kern_gpu_gm107.c` (hàm tại ~dòng 66, cùng nội dung hai tag):

```c
/* Read fuse for display supported status.
 * Some chips not marked displayless do not support display */
NvBool gpuFuseSupportsDisplay_GM107(OBJGPU *pGpu)
{
    return GPU_FLD_TEST_DRF_DEF(pGpu, _FUSE, _STATUS_OPT_DISPLAY, _DATA, _ENABLE);
}
```

i.e. test `DATA == 0`. **Sửa số liệu lưu trữ:** `display_gate.json` ghi dispatch source_lines 1941/1943 — số đo trực tiếp @78.08 là 2096 (block 2093–2114); caller kern_disp.c là dòng 443 (sourcegraph) / 444 (bản cache lệch ±1 dòng). Không thay đổi kết luận, chỉ chỉnh locator.

### 2.3 Caller và cách xử lý false (@78.08, danh sách đầy đủ — sourcegraph `gpuFuseSupportsDisplay_HAL count:100`, matchCount 4, exhaustive: 1 define + 3 caller)

| File:dòng (78.08) | Hàm | Xử lý khi gate = false |
|---|---|---|
| `src/nvidia/arch/nvalloc/unix/src/osinit.c:1097` | `RmSetConsolePreservationParams` | return sớm — bỏ console preservation (sau check vGPU) |
| `src/nvidia/src/kernel/gpu/disp/kern_disp.c:443` | `kdispStatePreInitLocked_IMPL` | trả `NV_ERR_NOT_SUPPORTED` — display pre-init dừng |
| `src/nvidia/src/kernel/gpu/gsp/arch/turing/kernel_gsp_tu102.c:651` | layout WPR meta | bỏ VGA workspace: `vgaWorkspaceOffset = fbSize − DRF_SIZE(NV_PRAMIN)` |

Macro: `g_gpu_nvoc.h:3841` `#define gpuFuseSupportsDisplay_HAL(pGpu) gpuFuseSupportsDisplay_DISPATCH(pGpu)`.

### 2.4 Áp giá trị đo vào decode

STATUS data bit0 = 1, ENABLE encoding = 0 ⇒ test sai ⇒ `gpuFuseSupportsDisplay` = false ⇒ driver 615.71.09/615.78.08 **coi card là displayless** tại cả 3 caller. Đây là decode xác định của giá trị đo lưu trữ, không phải phỏng đoán silicon.

## 3. Mâu thuẫn với báo cáo lưu trữ (CONTRADICTED)

`P0_FUSE.md` §5.1 và `FUSE_SEMANTICS.md` dòng 33: "bit0 = 1 → fuse báo display **bật**". Sai chiều: cả hai bỏ qua ENABLE encoding = 0 trong chính header được trích. Đọc đúng theo driver: bit0 = 1 ⇒ display bị coi là KHÔNG hỗ trợ. `display_gate.json` đã tự đạt `evaluated_support=false` (class ARCHIVED_STATUS_GATE_FALSE) — hướng đúng, nhưng sai số dòng dispatch (§2.2).

## 4. Phân tầng nguồn vật lý — register semantics tách khỏi nguồn OTP

- **OPT_*** (0x1378, 0x174C): access RWIVF, có INIT value ⇒ kiểu opt/shadow, có đường ghi từ PRI trong header definition.
- **STATUS_OPT_DISPLAY**: access R-I4R / R-IVF — chỉ đọc, không INIT. Trong phạm vi nguồn công khai (search exhaustive 2 tag, không có setter, không module param), **không có code nào ghi** register này trong đường host đã xem — điều này chỉ chứng minh giao diện thanh ghi là read-only, **KHÔNG chứng minh** "không có override bằng phần mềm" tổng thể; nguồn OTP/shadow và cơ chế override khác (GSP, devinit, VBIOS, registry) vẫn chưa được xác định.
- Không có public source nào của họ Turing chứng minh giá trị STATUS đọc về là (a) OTP cell thô, (b) shadow latch, (c) strap-derived, hay (d) giá trị đã xử lý/override. Public open-gpu-kernel-modules chỉ cho thấy host ĐỌC và test — selector GSP +0x3814 cũng không giải nghĩa được từ nguồn công khai (khớp limits của `fuse_header_inventory.json`).
- **Kết luận: đường driver → đọc 0x21C04 đã được bằng chứng** (dispatch TU106 → `gpuFuseSupportsDisplay_GM107` → test bit0). Điều **CHƯA** được bằng chứng là nguồn vật lý sinh giá trị và cơ chế tạo status (OTP vs shadow vs strap vs xử lý khác). Một lần đọc R- không đủ chứng minh OTP.

## 5. BADF và các giải thích thay thế

Poison (0xBADF5040/0xBADF1300/0xBADF1100) trên BAR0 KHÔNG phải phép đo transistor. Đã có counterevidence cụ thể: cửa sổ 0x820000 trên card này trả về 0x166000a1 (giá trị PMC_BOOT_0) ⇒ aperture GB100 không map fuse ⇒ BADF có thể do addressing sai aperture. Các giải thích BADF khác (quyền/aperture, clock/reset/power, disabled block) đều chưa loại trừ được offline. Không dùng count/metadata fuse (352 data/2202 poison/518 zero) làm chứng "sức khỏe silicon".

## 6. Counterevidence hai chiều (phục vụ completion)

- **Chống hard-fuse (OTP tất yếu):** toàn bộ chuỗi chỉ dựa trên decode một STATUS R-; chưa có chứng cứ trực tiếp cell OTP; BADF có thể do clock/power; header OPT_* liền kề là RW có INIT ⇒ tồn tại cơ chế opt/shadow ghi được trong cùng block.
- **Chống software-only (host đọc nhầm hoàn toàn):** giá trị 1 ổn định và các reg lân cận đọc đúng chiều (NVDEC_DIS=0, GSP_DEBUG_DIS=1); decode là chủ đích (comment "displayless"); không tìm thấy override path **trong phạm vi open modules đã xem** — điều này KHÔNG bằng chứng không có override ở tầng GSP/registry/VBIOS khác.

Phân tích phục hồi có điều kiện: `DISPLAY_RECOVERY_CONDITIONS.csv` (chỉ đánh giá bằng nguồn, không thử override).

## 7. Hạn chế

Chữ ký tag chưa xác minh key; kernel/GSP RM đóng không xem được (selector GSP +0x3814 mở); giá trị 0x21C04 là đo lưu trữ (capture_time unknown), chưa đối chiếu đo mới (nằm ngoài R0). Nouveau/VBIOS behavior chưa kiểm trong nhiệm vụ này.

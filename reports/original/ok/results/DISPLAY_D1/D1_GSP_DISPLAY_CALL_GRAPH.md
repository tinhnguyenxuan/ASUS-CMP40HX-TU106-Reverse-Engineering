# D1-B — CALL GRAPH DISPLAY: HOST RM → GSP 615.78.08

**GSP ELF:** `gsp_tu10x_615.78.08_inner.elf`, SHA-256 `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85`
**Nguồn:** trích từ wrapper `0c6124c1…3eeb3b`, `dd skip=64 count=22901568`
**Disassembler:** `/usr/lib/llvm-18/bin/llvm-objdump -d --triple=riscv64`
**Source:** open-gpu-kernel-modules `615.78.08` @ `1a82fbfda8f321b056eb3568850f9316c5e465c5`

---

## 7. Kết quả trung tâm

> **Gate display nằm ở host RM, tại `kdispStatePreInitLocked_IMPL` dòng 444.**
> Khi gate đó trả `NV_ERR_NOT_SUPPORTED`, object `KernelDisplay` bị huỷ **trước khi** lệnh `NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` được gửi tới GSP.
>
> **Nhưng GSP có gate riêng** — handler `0x04B9F5CC` tồn tại và có thể trả `ipVersion = 0`. Nó chỉ **chưa được gọi**. Xem §6.

---

## 2. Gate thật — host, không phải GSP

`src/nvidia/src/kernel/gpu/disp/kern_disp.c:435-446`
```c
435|kdispStatePreInitLocked_IMPL(OBJGPU        *pGpu,
436|                             KernelDisplay *pKernelDisplay)
437|{
438|    NV_STATUS status;
439|    RM_API *pRmApi = GPU_GET_PHYSICAL_RMAPI(pGpu);
440|    NvU32   hClient = pGpu->hInternalClient;
441|    NvU32   hSubdevice = pGpu->hInternalSubdevice;
442|    NV2080_CTRL_INTERNAL_DISPLAY_GET_IP_VERSION_PARAMS ctrlParams;
443|
444|    if (!gpuFuseSupportsDisplay_HAL(pGpu))
445|       return NV_ERR_NOT_SUPPORTED;
446|
```

Dòng 444 chạy **trước**:
- `NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` (dòng 448) — không bao giờ được gửi
- `gpuInitDispIpHal()` (dòng 459) — không bao giờ chạy
- `kdispUpdatePdbAfterIpHalInit()` (dòng 461)
- `kdispAllocateCommonHandle()` (dòng 463)
- `kdispStateInitLocked` (dòng 556) và `kdispInitBrightcStateLoad` (dòng 594)

⇒ **Toàn bộ tầng display của RM không được khởi tạo.** Không có lệnh GSP nào về PDISP/SOR/DP/HDMI được phát.

---

## 3. Hệ quả trong state machine engine

`src/nvidia/src/kernel/gpu/gpu.c:1744-1768`
```c
1744|        pEngstate = gpuGetEngstate(pGpu, curEngDescriptor);
1745|
1746|        if (pEngstate != NULL)
1747|        {
1748|            if (!pEngstate->getProperty(pEngstate, PDB_PROP_ENGSTATE_IS_MISSING) &&
1749|                engstateIsPresent(pGpu, pEngstate))
1750|            {
1751|                continue;
1752|            }
1753|
1754|            gpuDestroyMissingEngine(pGpu, pEngstate);
1755|            pEngstate = NULL;
1756|        }
...
1762|        NV_PRINTF(LEVEL_INFO, "engine 0x%06x:%d is missing, removing\n", ...);
1764|        rmStatus = gpuDeleteEngineOnPreInit(pGpu, curEngDescriptor);
```

`engstateIsPresent_IMPL` (`eng_state.c:403-412`) → `gpuCheckEngine_HAL(pGpu, pEngstate->engDesc)`.

`src/nvidia/src/kernel/gpu/gpu.c:6751-6765`
```c
6751|    switch (ENGDESC_FIELD(engDesc, _CLASS))
6752|    {
6753|        case ENG_CLASS_LSFM:
6754|        case ENG_CLASS_PMU:
6755|        case ENG_CLASS_CLK:
6756|        case ENG_CLASS_ACR:
6757|        case ENG_CLASS_DISP:
6758|            return NV_FALSE;
...
6764|        case ENG_CLASS_KERNEL_DISPLAY:
6765|            return IS_FW_CLIENT(pGpu);
```

Hai nhánh khác nhau, đừng lẫn:
- `ENG_CLASS_DISP` (legacy display engine) → **luôn** `NV_FALSE`, không phụ thuộc phần cứng. Đây là engine cổ, không liên quan.
- `ENG_CLASS_KERNEL_DISPLAY` → `IS_FW_CLIENT(pGpu)` = `IS_GSP_CLIENT(pGpu) || IS_DCE_CLIENT(pGpu)` (`g_gpu_nvoc.h:6222`). Với GSP-enabled 615.78.08 → **`NV_TRUE`**.

⇒ **KernelDisplay CÓ được tạo.** Nó bị huỷ **sau đó**, khi `kdispStatePreInit` trả lỗi — không phải vì engine vắng mặt.

Kiểm chứng: `PDB_PROP_KDISP_IS_MISSING` chỉ được set cho **virtual function (VF)**; CMP 40HX là physical function ⇒ property này không bật.

---

## 4. Truy vết GSP cho display — âm tính có kiểm soát

### 4.1 Chuỗi `RmDisableDisplay` có trong firmware nhưng không được tham chiếu

| Bước | Kết quả |
|---|---|
| Tìm `"RmDisableDisplay\x00"` | file offset `0x9E928` → vaddr `0x409E928` trong `.rm_rodata` |
| Ngữ cảnh chuỗi | `…PanelBrightnessLimits\0\0\0RmDisableDisplay\0\0\0\0\0\0\0\0RmDisableDispMacro\0\0\0\0CRT\0\0\0\0D…` — nằm trong **blob tên registry key**, cùng chỗ với `PanelBrightnessLimits`, `RmDisableDispMacro` |
| Con trỏ 64-bit tới `0x409E928` toàn file | **0 hit** |
| Con trỏ 32-bit tới `0x409E928` toàn file | **0 hit** |
| `auipc+addi` materialise `0x409E928` trong `.rm_text` | **0 hit** (quét toàn bộ `0x1039000` byte) |
| Tương tự cho `"RmForceGridDisplayless"` @ `0x408A2E0` | cũng **0 hit** cả 3 cách |

Bảng tra key của GSP không dùng con trỏ trực tiếp tới chuỗi (đã kiểm: các bảng run-of-vaddr trong `.rm_data` chỉ trỏ tới `0x04xxxxxx` vùng khác). Vì vậy **không kết luận được** "key không tồn tại"; chỉ kết luận được **"không có xref tĩnh trực tiếp"**.

### 4.2 RM open-source không chứa `RmDisableDisplay`

```
grep -rn "RmDisableDisplay" <toàn bộ 147 MB source RM>  → 0 hit
grep -rn "RM_DISABLE_DISPLAY|DISABLE_DISPLAY" src/nvidia/inc/ src/nvidia/interface/  → 0 hit
```

⇒ `RmDisableDisplay` là **registry key chỉ tồn tại trong blob của GSP-RM**, không có đối tác phía host. Nó không thể là producer của trạng thái hiện tại vì host RM chưa bao giờ hỏi GSP về display.

---

## 5. Call graph hoàn chỉnh (đã đóng)

```
HOST                                                          | GSP
──────────────────────────────────────────────────────────────|──────────────────
gpuStatePreInit (gpu.c)                                       |
  └─ gpuDetermineEngineOrder / gpuCheckEngine                 |
       └─ ENG_CLASS_KERNEL_DISPLAY → IS_FW_CLIENT → NV_TRUE   |
            ⇒ KernelDisplay constructed                       |
                                                              |
gpuStatePreInit → engine StatePreInit loop                    |
  └─ kdispStatePreInitLocked (kern_disp.c:435)                |
       └─ gpuFuseSupportsDisplay_HAL                          |
       │    = gpuFuseSupportsDisplay_GM107 (g_gpu_nvoc.c:2098)|
       │      └─ GPU_REG_RD32(0x021C04) = 0x00000001          |
       │         DATA=1 != ENABLE(0) ⇒ NV_FALSE               |
       ├─ return NV_ERR_NOT_SUPPORTED  ← **ĐIỂM DỪNG**        |
       │                                                      |
       ✗ NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION  ────╳ KHÔNG GỬI
       ✗ gpuInitDispIpHal                                     |
       ✗ kdispStateInitLocked                                 |
       ✗ kdispInitBrightcStateLoad                            |
                                                              |
  └─ engstateIsPresent = NV_FALSE                              |
       └─ gpuDestroyMissingEngine → objDelete(KernelDisplay)   |
            ⇒ class DISPLAY_COMMON gỡ khỏi classDB             |
                                                              |
nvidia-drm: "Cannot find any crtc or sizes"
```

**Đường dữ liệu không bị đứt ở đây** — nó bị **chặn có chủ đích** tại một điểm xác định. Đây là kết quả loại 1 của mục F.

---

## 6. Gate phía GSP — ĐÃ TÌM ĐƯỢC HANDLER THẬT

### 6.1 Định vị control trong dispatch table

`NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` = **`0x20800A4B`**
(`ctrl2080internal.h:915`; params `{ NvU32 ipVersion; }`, message id `0x4B`)

Tìm literal trong `.rm_rodata` (vaddr `0x401d000`, file `0x1d000`) → **1 hit** tại `vaddr 0x4061958`.
Record (stride 32, layout `{u32 cmd, u32 size, u64 const, u64 handler, u32 flags}`):

```
record @0x04061958 raw: 4b 0a 80 20 04 00 00 00 c8 04 07 04 00 00 00 00 cc f5 b9 04 00 00 00 00 c0 00 00 00 00 00 00 00
  cmd     = 0x20800A4B
  size    = 0x4
  const   = 0x00000000040704C8     (giống hệt mọi record khác — bảng hợp lệ)
  handler = 0x04B9F5CC
  flags   = 0x000000C0
```

Đối chứng với record A26 đã biết (T7): `0x40614B8` → `cmd=0x20800A26 size=0x2A60 const=0x040704C8 handler=0x04BC682C` — cùng `const`, cùng stride ⇒ cách parse đúng.

### 6.2 Disassembly handler `0x04B9F5CC` (code bytes thật)

```
4b9f5e8: 83 37 05 16   ld   a5, 0x160(a0)          # a5 = *(pGpu+0x160)
4b9f5ec: b7 24 00 00   lui  s1, 0x2
4b9f5f0: 13 89 05 00   mv   s2, a1                 # s2 = a1 = out params → ipVersion*
4b9f5f4: 03 b5 87 0e   ld   a0, 0xe8(a5)           # a0 = *(a5+0xE8)  = base
4b9f5f8: b3 04 95 00   add  s1, a0, s1             # s1 = base + 0x2000
4b9f5fc: 83 b9 04 f6   ld   s3, -0xa0(s1)          # s3 = *(base + 0x1F60)
4b9f600: 63 86 09 00   beqz s3, 0x4b9f60c          # nếu s3==0 → nhánh ipVersion=0
4b9f604: 83 47 a5 6e   lbu  a5, 0x6ea(a0)          # a5 = *(u8*)(base+0x6EA)  ← FLAG
4b9f608: 63 96 07 02   bnez a5, 0x4b9f634          # nếu !=0 → nhánh lấy ipVersion thật
4b9f60c: 93 07 00 00   li   a5, 0x0
4b9f610: 23 20 f9 00   sw   a5, 0x0(s2)             # *ipVersion = 0   ← DISPv0000
4b9f614: ...                                          (epilogue)
4b9f628: 13 05 00 00   li   a0, 0x0                # return NV_OK
4b9f630: 67 80 00 00   ret

# nhánh "thật" khi s3 != 0 và flag != 0:
4b9f634: 83 b5 04 f5   ld   a1, -0xb0(s1)          # a1 = *(base+0x1F50) — callback slot
4b9f638: 97 70 0e 00   auipc ra, 0xe7
4b9f63c: e7 80 80 cc   jalr -0x338(ra)             # gọi → a0 = status
4b9f640: 63 0e 05 00   beqz a0, 0x4b9f65c          # status==0 → nhánh khác
4b9f644: b7 77 00 00   lui  a5, 0x7
4b9f648: b3 89 f9 00   add  s3, s3, a5             # s3 += 0x7000
4b9f64c: 83 c7 89 46   lbu  a5, 0x468(s3)          # đọc byte phụ
4b9f650: 63 84 07 02   beqz a5, 0x4b9f678
4b9f654: 93 07 40 00   li   a5, 0x4                # → a5 = 4
4b9f658: 6f f0 9f fb   j    0x4b9f610              # *ipVersion = 4
4b9f65c: 83 b7 84 f5   ld   a5, -0xa8(s1)          # *(base+0x1F58)
4b9f660: 83 a7 87 25   lw   a5, 0x258(a5)          # field +0x258
4b9f664: 63 96 07 00   bnez a5, 0x4b9f670
4b9f668: 93 07 20 00   li   a5, 0x2                # → a5 = 2
4b9f66c: 6f f0 5f fa   j    0x4b9f610
4b9f670: 93 07 10 00   li   a5, 0x1                # → a5 = 1
4b9f674: 6f f0 df f9   j    0x4b9f610
4b9f678: 93 07 30 00   li   a5, 0x3                # → a5 = 3
4b9f67c: 6f f0 5f f9   j    0x4b9f610
```

### 6.3 Đọc được gì

| Quan sát | Ý nghĩa |
|---|---|
| `*ipVersion = 0` khi `s3 == 0` **hoặc** `*(u8*)(base+0x6EA) == 0` | Đây **chính là** đường sinh ra giá trị `0xFFFFFFFF`/`0` mà `gpuInitDispIpHal` xử lý |
| Đường "thật" gọi qua `*(base+0x1F50)` (callback slot), không phải hằng số | ipVersion phụ thuộc **trạng thái runtime**, không phải hằng biên dịch |
| Giá trị trả về chỉ là `0/1/2/3/4` (không phải `0x05020000` hex IP ver) | Handler này trả **enum nhánh**, không phải IP version số; nhánh 4 = display đầy đủ |
| 11 site `sb ...,0x6ea(rs1)` | Byte flag được ghi ở nhiều nơi: `0x4A128D4` (`sb zero`), `0x4B6F3EC` (`sb a0` ← kết quả `jalr 0x250(s1)`), `0x4C89784`, `0x4C95FDC`, `0x5306DE4`, `0x530713C`, `0x5307604`, `0x53076C4`, `0x5382D2C`, `0x5382F08`, `0x538314C` |

### 6.4 Nhánh code **tồn tại** ≠ trạng thái **thực tế** của CMP 40HX

Đây là phân biệt bắt buộc:

| | Nhánh trong code | Trạng thái CMP 40HX |
|---|---|---|
| `ipVersion = 0` → `DISPv0000` | **TỒN TẠI** (`0x4B9F60C`–`0x4B9F610`) | **CHƯA BIẾT** — handler chưa từng được gọi |
| `ipVersion = 4` (display đầy đủ) | **TỒN TẠI** (`0x4B9F654`) | **CHƯA BIẾT** |
| `gpuInitDispIpHal` hạ `0xFFFFFFFF → 0` | **TỒN TẠI** (`gpu.c:6033-6036`) | **Chưa chạy tới** — gate fuse chặn trước |

⇒ **Không được nói** "GSP đã trả 0 cho card này" — chưa đo. **Chỉ được nói**: đường đó tồn tại, và nếu host vượt được gate fuse thì nó sẽ là gate tiếp theo.

### 6.5 Trả lời câu B.7 ("bỏ một gate ở host có còn gate khác?")

**CÓ.** Ít nhất hai gate nữa, cả hai đã có nhánh xử lý trong code NVIDIA:

1. **Gate GSP/`ipVersion`** — `gpuInitDispIpHal_IMPL` tại `gpu.c:6033-6036`:
   ```c
   6029|    //
   6030|    // 0xFFFFFFFF ipver value happens when Display engines is disabled.  NVOC Disp IP
   6031|    // halspec doesn't have a hal variant maps to this value.  Convert it to DISPv0000.
   6032|    //
   6033|    if (ipver == 0xFFFFFFFF)
   6034|    {
   6035|        ipver = 0;
   6036|    }
   ```
   Comment của chính NVIDIA: **`0xFFFFFFFF` = "Display engines is disabled"** ⇒ hạ xuống `DISPv0000` = HAL display rỗng.

2. **Gate VBIOS/DCB** — `DCB entry_count = 0` (xem `D1_VBIOS_DISPLAY_POLICY.md`). Không có connector nào được khai báo ⇒ không có output nào để quét, dù engine có chạy.

3. **Gate board** — linh kiện DP/HDMI trên PCB (xem `D1_PDISP_SOR_PHY_EVIDENCE.md`) — **chưa kiểm**.

⇒ Bỏ gate fuse ở host **không đủ**. Đó là lý do kết luận D1 không tuyên bố "sửa một chỗ là xong".

---

## 7. Trả lời các câu hỏi B.1–B.7

| # | Câu hỏi | Trả lời |
|---|---|---|
| B.1 | Nguồn thực tế của `RmDisableDisplay` | **Không xác định được producer**, nhưng **đã loại trừ** nó khỏi đường hiện tại: 0 xref tĩnh; host RM không chứa key; host chưa từng gửi lệnh display nào cho GSP |
| B.2 | Hàm liên quan display/KernelDisplay/PDISP/SOR/DP/HDMI | Xác định `kdispStatePreInitLocked`, `kdispStateInitLocked`, `kdispInitBrightcStateLoad`, `gpuInitDispIpHal`, **handler GSP `0x04B9F5CC`** (DISPLAY_GET_IP_VERSION). Các object PDISP/SOR/DP **không được khởi tạo** nên không có frame nào để phân tích |
| B.3 | Call graph host RM → GSP | §5. Đứt ở host trước khi sang GSP |
| B.4 | Điều kiện GSP từ chối tạo display object | Handler `0x04B9F5CC` trả `ipVersion = 0` khi `*(base+0x1F60)==0` **hoặc** `*(u8*)(base+0x6EA)==0` (§6.2). Đây là điều kiện **duy nhất** tìm được trong firmware. `RmForceGridDisplayless`/`RmDisableDisplay` không có xref tĩnh |
| B.5 | Fuse-check / VBIOS-check / product-policy-check nào được thực hiện | **Fuse-check: CÓ** — `gpuFuseSupportsDisplay_GM107` @ 0x021C04. **VBIOS-check: CÓ** — `NO_DISPLAY_SUBSYSTEM=1`, `DCB entry_count=0`. **Product-policy: KHÔNG tìm thấy** trong đường thực thi |
| B.6 | Phân biệt host không tạo KernelDisplay vs GSP/hardware từ chối | **KernelDisplay CÓ được tạo** (ENG_CLASS_KERNEL_DISPLAY → `IS_FW_CLIENT` = TRUE). Nó bị **huỷ sau** khi pre-init fail. Vậy đây là **host RM chặn**, không phải GSP từ chối |
| B.7 | Bỏ một gate ở host còn gate khác không | **CÒN** — `ipver == 0xFFFFFFFF` ⇒ `DISPv0000` (gpu.c:6033-6036), cộng gate VBIOS DCB rỗng (xem D1-VBIOS) |

---

## 8. Giới hạn của phân tích này (trung thực)

- GSP ELF **stripped hoàn toàn**: 0 symbol, không `.symtab`, không dynamic symbol. Mọi kết luận về GSP dựa trên literal search + `auipc/addi` scan + bảng dispatch (T7), không dựa trên tên hàm.
- Không thể chứng minh "GSP không bao giờ chặn display" — chỉ chứng minh được "trong 615.78.08, không có đường nào tới việc đó **được kích hoạt** bởi cấu hình hiện tại".
- `NV2080_CTRL_INTERNAL_DISPLAY_GET_IP_VERSION` chưa được gọi nên **chưa biết** GSP sẽ trả `ipVersion` gì cho CMP 40HX.

### Phép kiểm phân biệt còn lại

| # | Phép kiểm | Cần gì |
|---|---|---|
| T-B1 | Gọi trực tiếp `NV2080_CTRL_CMD_INTERNAL_DISPLAY_GET_IP_VERSION` qua RM API từ userspace, đọc `ipVersion` | Viết client NV2080 (nvidia-smi không expose). Read-only. **Đây là phép kiểm giá trị cao nhất còn lại** |
| T-B2 | Nếu T-B1 trả `0xFFFFFFFF` ⇒ gate thứ hai phía GSP/hardware đã đóng, bỏ gate fuse vô nghĩa | — |
| T-B3 | Nếu T-B1 trả `0x05xx0000` (DISP v05) ⇒ GSP **có** thông tin display ⇒ gate thứ hai mở, chỉ fuse chặn | — |

---

## 9. Hash

| Đối tượng | Giá trị |
|---|---|
| GSP wrapper | `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b` |
| GSP inner ELF | `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85` |
| ELF entry | `0x4009000` |
| `.rm_text` | vaddr `0x4588000`, file `0x588000`, size `0x1039000` |
| `.rm_rodata` | vaddr `0x401d000`, file `0x1d000`, size `0x1e4000` |
| `.rm_data` | vaddr `0x4201000`, file `0x201000`, size `0x387000` |
| `RmDisableDisplay` string | vaddr `0x409E928` |
| `RmForceGridDisplayless` string | vaddr `0x408A2E0` |

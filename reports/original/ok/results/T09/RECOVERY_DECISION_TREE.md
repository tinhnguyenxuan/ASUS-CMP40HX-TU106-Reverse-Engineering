# Decision tree phục hồi — CMP 40HX / TU106

Ngày: 2026-11-05 (+07). Đây là kết luận offline có điều kiện, không phải chứng minh phục hồi thành công.

## A. DP (J1)

```text
Có connector J1 trên card thật?
├─ Có (photo prior report: CORROBORATED)
│  └─ CAD có lane IFPD_L0–L3/AUX/HPD tới G1?
│     ├─ Có ở mức GenCAD (CAD_ONLY)
│     │  └─ CMP population + sideband IC + HPD/AUX runtime đã chứng minh?
│     │     ├─ Chưa → UNKNOWN; software-only chưa đủ
│     │     └─ Có → kiểm display gate + VBIOS/init + physical output
│     └─ Không → board routing blocker
└─ Chưa xác nhận → UNKNOWN

Display host gate:
├─ Archived STATUS 0x021C04 raw=1 + exact 615.78.08 predicate DATA==0
│  └─ host gate evaluates FALSE (DECODED for archived snapshot)
│     ├─ physical STATUS provenance OTP/shadow/strap? UNKNOWN
│     ├─ GSP RmDisableDisplay effective value? UNKNOWN
│     └─ 615.71.09 exact mapping? NEEDS_INPUT
└─ Không được suy display silicon absent

VBIOS:
├─ Supplied CMP ROM DCB 0 entries + CONN count 0 (VERIFIED)
│  └─ display device metadata absent in this ROM
│     ├─ devinit/alternative init can compensate? UNKNOWN
│     └─ authenticated GeForce control ROM? MISSING
└─ Không flash/patch trong scope

Verdict DP: UNKNOWN / NOT RECOVERY_VERIFIED.
Ứng viên phần mềm chỉ tồn tại nếu đồng thời chứng minh policy override, init metadata tương thích,
board sideband/PHY và output physical; hiện chưa đủ điều kiện.
```

## B. DVI (J5)

```text
J5 physical connector?
├─ Có theo prior photo report (CORROBORATED)
│  └─ CAD IFPA/IFPB TMDS lanes tới G1?
│     ├─ Có (CAD_ONLY)
│     │  └─ DDC/HPD/sideband và CMP BOM verified?
│     │     ├─ Chưa → UNKNOWN
│     │     └─ Có → kiểm gate + VBIOS/init + physical output
│     └─ Không → board blocker
└─ Chưa xác nhận → UNKNOWN

DCB supplied ROM:
├─ no DCB device entries
│  └─ DVI route/config not described by DCB
│     ├─ DVI có devinit fallback? UNKNOWN
│     └─ GeForce reference ROM? MISSING

Verdict DVI: UNKNOWN / NOT RECOVERY_VERIFIED.
Không suy DVI từ DP và không suy output từ việc connector được hàn.
```

## C. Hai SM / 128 CUDA

```text
API/topology báo gì?
└─ 34 SM / 2176 CUDA (MEASURED)
   ├─ 2 SM còn lại có transistor? UNKNOWN
   ├─ TPC18 được enumerate? không xuất hiện trong effective topology
   ├─ TPC18 hoạt động/khỏe? UNKNOWN
   └─ nguồn disable là gì?
      ├─ 0x0004001F semantics TU106? UNKNOWN
      ├─ STATUS 0xC1C=0x38 semantics? UNKNOWN
      ├─ OTP DISABLE vs DEFECTIVE? UNKNOWN
      └─ GSP/software mask? possible, not proven

Nếu policy-only và có override hợp lệ trên TU106:
└─ 128 CUDA recovery = candidate/conditional
Nếu DEFECTIVE hoặc transistor absent:
└─ không phục hồi bằng software
Nếu PLM/firmware chặn override:
└─ không có đường đã chứng minh

Verdict: 34 SM là số hiệu quả đo được; 128 CUDA recovery UNKNOWN/CONDITIONAL,
không có RECOVERY_VERIFIED.
```

## D. Strap → PCI class/Device ID/display

```text
Netlist:
STRAP3 = BM5, R258 pull-up, R261 pull-down (VERIFIED netlist)
STRAP4 = BK5, R249/R264; STRAP5 = BJ5, R250/R265 (VERIFIED netlist)

Population:
STRAP3/4/5 low tendency theo prior photo (INFERRED/CORROBORATED input),
STRAP0/1/2 UNKNOWN.

Semantics:
├─ envytools G80+ gives family strap fields
├─ N18E gives a different Turing laptop table
└─ direct TU106 mapping BM5 → PSTRAPS bit/class/ID absent

Verdict:
- class observed 0302 and device 1F0B are historical saved observations;
- STRAP5:3 → 0302/0300: UNKNOWN;
- STRAP → Device ID: UNKNOWN;
- class 0300, if ever observed, would prove enumeration only, not DP/DVI output.
```

## E. Stop conditions

- Không ghép source 615.78.08 vào runtime 615.71.09 khi chưa có exact binary/anchor.
- Không gọi DCB zero-entry là “silicon displayless”.
- Không gọi `BADF` là bằng chứng transistor không tồn tại.
- Không gọi `0x0004001F` là mask 5 TPC khi chưa có TU106 semantic definition.
- Không coi tên GSP `RmDisableSec2`/`RmActivateHulk` là host-callable exploit.
- Không thử write/flash/strap/unlock để ép verdict trong nghiên cứu R0.

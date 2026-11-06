# Sổ bằng chứng
E01: LIVE_SSH_EVIDENCE.json + raw/ssh_batchmode.txt: SSH BatchMode exit 255, Permission denied; không có lệnh GPU thực thi. Lần thử đầu trước đó trả No route to host.
E02: raw/source_inventory.json + raw/manager.c: NVIDIA tag 615.71.09 static cached legacy mask; chưa biết tag runtime.
E03: raw/gr.h, grmgr.h, internal.h: schema/query definitions; không chứng minh caller bất kỳ có quyền hoặc support trên card.
E04: fuse2.json lịch sử, hash và raw values trong FUSE_RAW_VS_EFFECTIVE.md, không phải live.
E05: bốn trang CMP Wiki và source gpcprobe trong CMPWIKI_GA100_MECHANISM.md: dữ liệu cộng đồng GA100; không nhập semantics sang TU106.

E06: LIVE_CAPTURE_20261106.json: successful live capture using prior existing credential, driver615.71.09, BDF and UUID verified; requested multiprocessor_count field unsupported.
E07: LIVE_CUDA_SM_QUERY.json: current CUDA SM count; no GPC/TPC mask.

E08: LIVE_RM_QUERY_V2.json; tag615.71.09; GPC0=0x1f GPC1=0x3f GPC2=0x3f; SM mapping count34; source script hash in JSON. Consistency:17 active TPC,2 SM each; no fuse provenance.
E09: initial RM allocate status0x1b due to no open per-GPU device descriptor, as explained in kernel-open/nvidia/nv.c nv_is_gpu_accessible; V2 opened /dev/nvidia0, succeeded without sudo.

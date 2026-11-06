#!/bin/sh
# Replay: VBIOS full token audit (read-only; outputs only under /home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_FULL_TOKEN_AUDIT)
set -eu
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$DIR/vbios_full_token_audit.py" /tmp/v11chk/outputs/CMP40HX_ORIGINAL_1MB.bin /tmp/v11chk/outputs/cmp40hx_t4.bin /tmp/v11chk/RAW_DATA/vbios_shadow.bin /home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_FULL_TOKEN_AUDIT
echo "--- outputs ---"
ls -la /home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_FULL_TOKEN_AUDIT
echo "--- hashes ---"
cat /home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_FULL_TOKEN_AUDIT/output_hashes.json

#!/usr/bin/env python3
"""D2: callers of the functions that write *(base+0x6EA).

llvm-objdump already resolves PC-relative targets and prints them in a
trailing comment: `jalr -0x228(ra) <sym+0x...>`. Parsing that comment is the
reliable path on a stripped ELF; decoding auipc+jalr by hand is redundant.
"""
import re, json

DIS = 'gsp.dis'
TARGETS = {0x4a127fc: 'W1_clr_cond', 0x4b6f190: 'W2_main_init',
           0x4c896cc: 'W3_clr_poll', 0x4c95efc: 'W4_clr_vercheck',
           0x5306d20: 'W5_ctor_bf', 0x5307018: 'W6_ctor_bf2',
           0x53075f0: 'W7_clr_cold', 0x53076a8: 'W8_clr_cold2',
           0x5382c14: 'W9_ctor_sec', 0x538307c: 'W10_ctor_sec2'}

pat = re.compile(r'^\s*([0-9a-f]+):\s*((?:[0-9a-f]{2} )+)\s*\t?([a-z0-9.]+)?\s*(.*)$')
tgt_re = re.compile(r'<[^>]*?\+0x([0-9a-f]+)>')
ins, order = {}, []
for ln in open(DIS, errors='replace'):
    m = pat.match(ln)
    if not m:
        continue
    a = int(m.group(1), 16)
    ins[a] = (m.group(2).replace(' ', '').lower(), (m.group(3) or '').strip(), (m.group(4) or '').strip())
    order.append(a)
order.sort()

pr = []
for a, (raw, mn, ops) in ins.items():
    if len(raw) == 8:
        w = int.from_bytes(bytes.fromhex(raw), 'little')
        if (w & 0x7F) == 0x13 and ((w >> 7) & 0x1F) == 2 and ((w >> 15) & 0x1F) == 2:
            pr.append(a)
pr.sort()
SEC = 0x4588000  # .section_task_rm_elf_text_instance base; all targets live here


def fn_of(a):
    lo = hi = None
    for p in pr:
        if p <= a:
            lo = p
        elif p > a:
            hi = p
            break
    return lo, hi


def resolve(a, ops):
    m = tgt_re.search(ops)
    if not m:
        return None
    return SEC + int(m.group(1), 16)


calls = []
for a in order:
    raw, mn, ops = ins[a]
    if mn in ('jalr', 'jal', 'call', 'tail'):
        t = resolve(a, ops)
        if t:
            calls.append((a, t))
print(f"resolved {len(calls)} direct calls")

out = {}
for t, name in sorted(TARGETS.items()):
    hits = [c for c, tg in calls if tg == t]
    out[name] = dict(target=hex(t), caller_count=len(hits), callers=[])
    print(f"\n=== {name} @ {hex(t)}  callers: {len(hits)}")
    for c in hits[:30]:
        lo, hi = fn_of(c)
        out[name]['callers'].append(dict(call_site=hex(c), caller_fn=hex(lo) if lo else None,
                                         caller_size=(hi - lo) if lo and hi else None))
        print(f"    call@{hex(c)}  in fn {hex(lo) if lo else '?'}  size={(hi-lo) if lo and hi else '?'}")
    if len(hits) > 30:
        print(f"    ... {len(hits)-30} more")
json.dump(out, open('callers6ea.json', 'w'), indent=2)

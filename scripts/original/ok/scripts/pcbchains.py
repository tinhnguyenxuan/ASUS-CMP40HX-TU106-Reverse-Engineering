#!/usr/bin/env python3
"""D3: trace GPU display pin -> coupling component -> connector, from GENCAD netlist.

Board: CG161P_R2 (ASUS GeForce reference design, GENCAD 1.4, rev date 2021-12-14)
ponytail: parses only $SIGNALS nodes; $TRACKS ignored — electrical continuity is
already asserted by shared net names, physical routing adds nothing here.
"""
import re, sys, json

CAD = 'CG161P_R2_boardview.cad'


def load():
    d = open(CAD, 'rb').read().decode('latin-1')
    i, j = d.find('$SIGNALS'), d.find('$ENDSIGNALS')
    sig, sigs, comp_pins = None, {}, {}
    for l in d[i:j].split('\n'):
        s = l.strip()
        if s.startswith('SIGNAL '):
            sig = s.split(None, 1)[1]
            sigs[sig] = []
        elif s.startswith('NODE ') and sig:
            parts = s.split(None, 1)[1].rsplit(None, 1)
            if len(parts) == 2:
                ref, pin = parts
                sigs[sig].append((ref, pin))
                comp_pins.setdefault(ref, {})[pin] = sig
    return sigs, comp_pins


def main():
    sigs, comp = load()
    print(f"signals={len(sigs)}  components-with-pins={len(comp)}")

    CONN = {'J1': 'DisplayPort 20P (S_DISPLAY_20P_5HOLD_LF3)',
            'J10': 'HDMI (SO_HDMI_38P_9H_C1_COLAY_LF3)',
            'J5': 'DVI (SO_DVI_24P_4HD_RA_C1_LF3)'}

    # GPU pins whose net also reaches a connector, directly or via one 2-pin part
    gpu_pins = comp.get('G1', {})
    print(f"\nG1 (GPU) pins in netlist: {len(gpu_pins)}")

    chains = []
    for pin, net in gpu_pins.items():
        nodes = sigs.get(net, [])
        refs = {r for r, _ in nodes}
        direct_conn = refs & set(CONN)
        via = None
        if not direct_conn:
            # try one 2-pin coupling part (C/R) on the same net
            for r, p in nodes:
                if re.match(r'^C\d+$|^R\d+$', r) and r != 'G1':
                    other = '2' if p == '1' else '1'
                    n2 = comp.get(r, {}).get(other)
                    if n2:
                        refs2 = {x for x, _ in sigs.get(n2, [])}
                        c2 = refs2 & set(CONN)
                        if c2:
                            via = (r, n2, c2)
                            break
        if direct_conn or via:
            chains.append(dict(gpu_pin=pin, net=net, direct=sorted(direct_conn),
                               via_net=via[1] if via else None,
                               via_part=via[0] if via else None,
                               connector=sorted(via[2]) if via else sorted(direct_conn)))

    print(f"\n=== GPU display pins reaching a connector: {len(chains)} ===")
    by_conn = {}
    for c in chains:
        for k in c['connector']:
            by_conn.setdefault(k, []).append(c)
    for k in sorted(by_conn):
        print(f"\n  {k}  ({CONN.get(k,'?')})  <- {len(by_conn[k])} GPU pins")
        for c in by_conn[k][:14]:
            via = f"via {c['via_part']} -> {c['via_net']}" if c['via_part'] else 'DIRECT'
            print(f"     G1 {c['gpu_pin']:5s} net {c['net']:18s} {via}")
        if len(by_conn[k]) > 14:
            print(f"     ... {len(by_conn[k])-14} more")

    json.dump(chains, open('d3_pcb_chains.json', 'w'), indent=2)
    print(f"\nwrote d3_pcb_chains.json ({len(chains)} chains)")


if __name__ == '__main__':
    main()

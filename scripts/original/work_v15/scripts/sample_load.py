#!/usr/bin/env python3
"""D: lay mau theo thoi gian duoi tai. Read-only. Xuat measure_timeseries.json.

Dung: python3 sample_load.py [giay]
"""
import json
import subprocess
import sys
import time

FIELDS = ("clocks.sm,clocks.mem,power.draw,power.limit,temperature.gpu,"
          "utilization.gpu,pstate,clocks_throttle_reasons.active,"
          "clocks_throttle_reasons.hw_slowdown,"
          "clocks_throttle_reasons.sw_power_cap,"
          "clocks_throttle_reasons.hw_thermal_slowdown,"
          "clocks_throttle_reasons.sw_thermal_slowdown")


def snap():
    try:
        r = subprocess.run(["nvidia-smi", f"--query-gpu={FIELDS}",
                            "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode:
            return None
        return dict(zip(FIELDS.split(","),
                        [x.strip() for x in r.stdout.strip().split(",")]))
    except Exception:
        return None


def main():
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    burn = subprocess.Popen(["./load", str(dur + 10)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rows = []
    t0 = time.time()
    try:
        while time.time() - t0 < dur:
            s = snap()
            if s:
                s["t"] = round(time.time() - t0, 1)
                rows.append(s)
            time.sleep(4)
    finally:
        burn.terminate()
        try:
            burn.wait(timeout=10)
        except Exception:
            burn.kill()

    print(f"=== {len(rows)} mau trong {dur}s duoi tai ===")
    print(f"  {'t':>5s} {'SM':>7s} {'MEM':>6s} {'W':>7s} {'PL':>6s} {'T':>3s} "
          f"{'UTIL':>5s} {'PST':>4s}  throttle")
    for r in rows:
        print(f"  {r['t']:>5} {r['clocks.sm']:>7s} {r['clocks.mem']:>6s} "
              f"{r['power.draw']:>7s} {r['power.limit']:>6s} "
              f"{r['temperature.gpu']:>3s} {r['utilization.gpu']:>5s} "
              f"{r['pstate']:>4s}  {r['clocks_throttle_reasons.active']}")

    # thong ke
    sms = []
    for r in rows:
        try:
            s = r["clocks.sm"].replace(" MHz", "").strip()
            if s.isdigit():
                s = int(s)
                if s > 500:
                    sms.append(s)
        except Exception:
            pass
    if sms:
        from collections import Counter
        c = Counter(sms)
        print(f"\n  SM clock duoi tai: min={min(sms)} max={max(sms)} "
              f"tb={sum(sms) / len(sms):.0f} MHz")
        print(f"  phan bo: {c.most_common(6)}")
        print(f"  so mau o 1905 MHz: {c.get(1905, 0)}/{len(sms)}")
        print(f"  so mau o 1890 MHz: {c.get(1890, 0)}/{len(sms)}")
    thr = set(r["clocks_throttle_reasons.active"] for r in rows)
    print(f"  throttle active: {thr}")

    json.dump(dict(duration=dur, samples=rows,
                   sm_values=sms,
                   histogram=dict(__import__("collections").Counter(sms))),
              open("measure_timeseries.json", "w"), indent=1)
    print("\n  -> measure_timeseries.json")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""D: do read-only. Khong doi cau hinh. Xuat outputs/measure_readonly.json.

Dung: python3 measure.py   (tren target, khong can root cho query)
"""
import json
import os
import subprocess
import sys

Q = ("clocks.sm,clocks.mem,clocks.gr,power.draw,power.limit,"
     "power.default_limit,power.max_limit,power.min_limit,"
     "temperature.gpu,temperature.memory,utilization.gpu,"
     "pstate,pcie.link.gen.current,pcie.link.width.current,"
     "clocks_throttle_reasons.active,clocks_throttle_reasons.gpu_idle,"
     "clocks_throttle_reasons.sw_power_cap,"
     "clocks_throttle_reasons.hw_slowdown,"
     "clocks_throttle_reasons.hw_thermal_slowdown,"
     "clocks_throttle_reasons.hw_power_brake_slowdown,"
     "clocks_throttle_reasons.sw_thermal_slowdown,"
     "clocks_throttle_reasons.hw_slowdown_thermal,"
     "clocks_throttle_reasons.sync_boost,"
     "clocks.max.sm,clocks.max.memory,"
     "enforced.power.limit,fan.speed,compute_mode")


def q(fields=Q):
    try:
        r = subprocess.run(["nvidia-smi", f"--query-gpu={fields}",
                            "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return {"error": r.stderr.strip()[:300]}
        return dict(zip(fields.split(","), [x.strip() for x in r.stdout.strip().split(",")]))
    except Exception as e:
        return {"error": str(e)}


def logs():
    try:
        r = subprocess.run(["dmesg"], capture_output=True, text=True, timeout=10)
        keys = ("NVRM", "gsp", "GSP", "power", "clock", "volt", "fuse", "pstate")
        return [l for l in r.stdout.splitlines() if any(k in l for k in keys)][-40:]
    except Exception as e:
        return [f"loi: {e}"]


def main():
    idle = q()
    print("=== D: do read-only (khong doi cau hinh) ===")
    print("--- idle ---")
    for k, v in idle.items():
        print(f"  {k:<48s} {v}")

    # nvidia-smi -q phan clock/voltage/power
    print("\n--- nvidia-smi -q (clock/power/limit) ---")
    try:
        r = subprocess.run(["nvidia-smi", "-q", "-d", "CLOCK,POWER,PERFORMANCE"],
                           capture_output=True, text=True, timeout=20)
        for l in r.stdout.splitlines():
            s = l.strip()
            if s and any(k in s for k in ("Clocks", "Power", "Perf", "Limit",
                                          "Clock", "MHz", "W", "Idle", "Apps",
                                          "Default", "Min", "Max")):
                print(f"  {s}")
    except Exception as e:
        print(f"  loi: {e}")

    # NVML: doc VF offset + voltage neu co
    print("\n--- NVML doc (khong ghi) ---")
    try:
        import ctypes
        ml = ctypes.CDLL("libnvidia-ml.so.1")
        ml.nvmlInit_v2()
        dev = ctypes.c_void_p()
        ml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev))
        res = {}
        for nm, arg in (("GpcClkVfOffset", 1), ("MemClkVfOffset", 1),
                        ("PowerManagementLimit", 1), ("EnforcedPowerLimit", 1),
                        ("ClockInfo", 2), ("Temperature", 2)):
            f = getattr(ml, f"nvmlDeviceGet{nm}", None)
            if not f:
                res[nm] = "khong co API"
                continue
            if nm in ("GpcClkVfOffset", "MemClkVfOffset"):
                v = ctypes.c_int()
                f.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
                rc = f(dev, ctypes.byref(v))
                res[nm] = v.value if rc == 0 else f"rc={rc}"
            else:
                v = ctypes.c_uint()
                f.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
                rc = f(dev, ctypes.byref(v))
                res[nm] = v.value if rc == 0 else f"rc={rc}"
            print(f"  {nm:<24s} {res[nm]}")

        # thu API voltage (thuong khong co tren consumer)
        for nm in ("nvmlDeviceGetVoltage", "nvmlDeviceGetPowerUsage"):
            f = getattr(ml, nm, None)
            print(f"  {nm:<24s} {'CO API' if f else 'KHONG CO'}")
        ml.nvmlShutdown()
    except Exception as e:
        print(f"  loi NVML: {e}")
        res = {}

    print("\n--- dmesg (NVRM/gsp/power/clock) ---")
    lg = logs()
    for l in lg[-20:]:
        print(f"  {l[:150]}")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "measure_readonly.json")
    json.dump(dict(idle=idle, nvml=res, dmesg=lg[-40:]), open(out, "w"), indent=1)
    print(f"\n  -> {out}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""P5/P6/P7/P8: thu thap read-only tren target. Xuat JSON.

Dung (tren target): python3 phase5678.py out.json
Khong ghi PCI config, khong retrain, khong doi strap.
"""
import json
import os
import subprocess
import sys

BDF = "0000:03:00.0"


def run(cmd, to=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=to)
        return r.stdout.strip()
    except Exception as e:
        return f"ERR:{e}"


def rd(path):
    try:
        return open(path).read().strip()
    except Exception as e:
        return f"ERR:{e}"


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "p5678.json"
    d = {"bdf": BDF}

    # ================= P7: PCIe =================
    d["pcie"] = {}
    lspci = run(f"lspci -D -vv -s {BDF}")
    d["pcie"]["lspci_vv"] = lspci
    regions = []
    for line in lspci.splitlines():
        s = line.strip()
        if s.startswith("Region"):
            regions.append(s)
        elif s.startswith(("Control:", "Status:", "Latency:", "Interrupt:")):
            d["pcie"].setdefault("misc", []).append(s)
    d["pcie"]["regions"] = regions
    d["pcie"]["resource_file"] = rd(f"/sys/bus/pci/devices/{BDF}/resource")
    d["pcie"]["config_space_64"] = run(
        f"od -An -tx1 -N64 /sys/bus/pci/devices/{BDF}/config")
    d["pcie"]["current_link_speed"] = rd(
        f"/sys/bus/pci/devices/{BDF}/current_link_speed")
    d["pcie"]["current_link_width"] = rd(
        f"/sys/bus/pci/devices/{BDF}/current_link_width")
    d["pcie"]["max_link_speed"] = rd(
        f"/sys/bus/pci/devices/{BDF}/max_link_speed")
    d["pcie"]["max_link_width"] = rd(
        f"/sys/bus/pci/devices/{BDF}/max_link_width")
    lspci_t = run("lspci -D -vvv -s " + BDF)
    d["pcie"]["capabilities"] = [l.strip() for l in lspci_t.splitlines()
                                 if "LnkCap" in l or "LnkSta" in l
                                 or "LnkCtl" in l or "DevCap" in l
                                 or "ReBar" in l or "Resizable" in l
                                 or "Physical Slot" in l]

    # ================= P6: memory =================
    d["memory"] = {}
    d["memory"]["smi"] = run(
        "nvidia-smi --query-gpu=memory.total,memory.used,memory.free "
        "--format=csv,noheader")
    d["memory"]["smq"] = run("nvidia-smi -q -d MEMORY")
    d["memory"]["bar1_total"] = rd(
        "/proc/driver/nvidia/gpus/0000:03:00.0/information")

    # ================= P5: topology =================
    d["topology"] = {}
    d["topology"]["smi_q"] = run("nvidia-smi -q | head -80")
    d["topology"]["sm_count"] = run(
        "nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader")
    d["topology"]["gpu_uuid"] = run(
        "nvidia-smi --query-gpu=uuid --format=csv,noheader")

    # ================= P8: security =================
    d["security"] = {}
    d["security"]["dmesg_wpr"] = run(
        "dmesg 2>/dev/null | grep -iE 'WPR|SEC2|secure|signature|auth' | tail -20")
    d["security"]["iommu_group"] = rd(
        f"/sys/bus/pci/devices/{BDF}/iommu_group/type")
    d["security"]["dma_mask"] = run(
        f"cat /sys/bus/pci/devices/{BDF}/dma_mask_bits 2>/dev/null")

    json.dump(d, open(out, "w"), indent=1)
    print(f"=== P5/P6/P7/P8 -> {out} ===\n")

    print("--- P7 PCIe ---")
    for r in d["pcie"]["regions"]:
        print(f"  {r}")
    print(f"  link: {d['pcie']['current_link_speed']} x"
          f"{d['pcie']['current_link_width']} "
          f"(max {d['pcie']['max_link_speed']} x{d['pcie']['max_link_width']})")
    for c in d["pcie"]["capabilities"][:8]:
        print(f"  {c}")

    print("\n--- P6 memory ---")
    print(f"  {d['memory']['smi']}")
    for line in d["memory"]["smq"].splitlines():
        s = line.strip()
        if "Total" in s or "Reserved" in s or "Used" in s or "Free" in s \
                or "BAR1" in s:
            print(f"  {s}")

    print("\n--- P8 security (dmesg) ---")
    for line in d["security"]["dmesg_wpr"].splitlines()[:8]:
        print(f"  {line[:140]}")
    print(f"  IOMMU type: {d['security']['iommu_group']}")


if __name__ == "__main__":
    main()
#!/bin/bash
echo "=========== 1. SYSTEM ==========="
uname -a; cat /etc/os-release 2>/dev/null | head -3
echo "--- uptime/boot ---"; uptime
echo
echo "=========== 2. SUDO ==========="
sudo -n -l 2>&1 | head -20
echo
echo "=========== 3. SECURE BOOT / LOCKDOWN ==========="
mokutil --sb-state 2>/dev/null || echo "mokutil: n/a"
cat /sys/kernel/security/lockdown 2>/dev/null || echo "lockdown: not exposed"
echo "--- module signing ---"; grep -E "CONFIG_MODULE_SIG|CONFIG_STRICT_KERNEL_RWX|CONFIG_STRICT_MODULE_RWX|CONFIG_KALLSYMS_ALL|CONFIG_DEVMEM|CONFIG_IO_STRICT_DEVMEM|CONFIG_RANDOMIZE_BASE|CONFIG_MODULE_FORCE_LOAD" /boot/config-$(uname -r) 2>/dev/null
echo
echo "=========== 4. GPU BAR PERMS ==========="
ls -l /sys/bus/pci/devices/0000:03:00.0/resource0 2>/dev/null
ls -l /dev/mem /dev/kmem /dev/port 2>/dev/null
echo "--- iomem around GPU ---"; sudo grep -i "nvidia\|03:00" /proc/iomem 2>/dev/null | head
echo
echo "=========== 5. NVIDIA MODULE ==========="
lsmod | grep -i nvidia
echo "--- params ---"; cat /proc/driver/nvidia/params 2>/dev/null | head -40
echo
echo "=========== 6. NETWORK EXPOSURE ==========="
sudo ss -tulnp 2>/dev/null | head -25
echo
echo "=========== 7. KERNEL TARGETS ==========="
echo "kallsyms readable: $(head -c 20 /proc/kallsyms 2>/dev/null | grep -c '0000000000000000' || echo) "
sudo grep -E " (commit_creds|prepare_kernel_cred|native_write_cr4|modprobe_path)$" /proc/kallsyms 2>/dev/null | head
echo "--- /proc/sys/kernel ---"
cat /proc/sys/kernel/kptr_restrict /proc/sys/kernel/dmesg_restrict /proc/sys/kernel/perf_event_paranoid /proc/sys/kernel/unprivileged_bpf_disabled 2>/dev/null

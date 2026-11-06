cd /tmp/captest && cp /tmp/cap.c /tmp/Makefile . 2>/dev/null
make -C /lib/modules/$(uname -r)/build M=/tmp/captest modules >/dev/null 2>&1
modinfo /tmp/captest/cap.ko 2>/dev/null | grep -iE "^sig|vermagic"
sudo insmod /tmp/captest/cap.ko 2>&1 && echo "*** UNSIGNED MODULE LOADED OK ***" || echo "LOAD FAILED"
sudo dmesg | tail -2
sudo rmmod cap 2>/dev/null

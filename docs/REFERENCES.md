# External reference starting points

These URLs are provided as background to the archived original reports. They are **not assertions** that a method demonstrated on a different GPU architecture applies to TU106.

- [CMP.WIKI — Full SM unlock](https://cmp.wiki/wiki/Full_SM_unlock) — GA100/CMP170HX reference; RIR and software-override claims must **not** be blindly ported to Turing.
- [NVIDIA open-gpu-kernel-modules](https://github.com/NVIDIA/open-gpu-kernel-modules) — source, headers and RM API structures; always match the source tag to the recorded driver/GSP build.
- [Nouveau Linux driver](https://nouveau.freedesktop.org/) — alternative open driver context for GPU engine/topology handling.
- [nv-uefi-unlocker issue #187](https://github.com/physicsdolphin/nv-uefi-unlocker/issues/187) — Turing register-mapping uncertainty and floorsweep discussion.
- [Envytools](https://github.com/envytools/envytools) — VBIOS parser and NVIDIA reverse engineering ecosystem.

Review cited sources and original licenses independently before reproducing or distributing third-party code.

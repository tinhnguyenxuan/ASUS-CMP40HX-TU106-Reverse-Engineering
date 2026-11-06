#!/usr/bin/env python3
"""
Read-only userspace diagnostic for EGL/Vulkan/NVIDIA linkage.

Writes a JSON report to stdout. Reads filesystem and runs read-only subprocesses
with a timeout. Does NOT modify the system, does NOT use sudo, does NOT touch
GPU registers/MMIO, does NOT reset or reload drivers, and does NOT open device
nodes for writing.

Usage: python3 diagnose_userspace.py [--nodes /dev/dri/card1 /dev/dri/renderD129]
                                 [--icd-dir /usr/share/vulkan/icd.d]
                                 [--egl-dir /usr/share/glvnd/egl_vendor.d]
                                 [--timeout 10] [--self-check]

Intended to run on the target machine by a later step; this file is only
authored here, not executed on the target.
"""
import argparse
import datetime
import grp
import json
import os
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile

DEFAULT_NODES = ["/dev/dri/card1", "/dev/dri/renderD129"]
DEFAULT_ICD_DIR = "/usr/share/vulkan/icd.d"
DEFAULT_EGL_DIR = "/usr/share/glvnd/egl_vendor.d"
LIBS = ["libGLX_nvidia.so.0", "libEGL_nvidia.so.0", "libEGL.so.1", "libvulkan.so.1"]
TOOLS = ["nvcc", "nvidia-smi", "eglinfo", "glxinfo", "vulkaninfo", "deviceQuery"]
PROC_MODULES = "/proc/modules"
PROC_NVIDIA_VERSION = "/proc/driver/nvidia/version"
MODSET_PARAM = "/sys/module/nvidia_drm/parameters/modeset"


def run(argv, timeout=10):
    """Run a read-only command, never raise on failure."""
    if not shutil.which(argv[0]):
        return {"argv": argv, "status": "TOOL_MISSING"}
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False
        )
        out = {
            "argv": argv,
            "returncode": result.returncode,
            "stdout": result.stdout[:200000],
            "stderr": result.stderr[:65536],
        }
    except subprocess.TimeoutExpired:
        return {"argv": argv, "status": "TIMEOUT", "timeout": timeout}
    except OSError as exc:  # pragma: no cover - defensive
        return {"argv": argv, "status": "OS_ERROR", "error": str(exc)}
    return out


def read_text(path, limit=65536):
    """Best-effort read-only text read; returns content or an error object."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(limit)
        return data.decode("utf-8", errors="replace")
    except OSError as exc:
        return {"error": str(exc), "path": str(path)}


def stat_node(path):
    """Read-only stat + permission probe of a device node."""
    result = {"path": path, "exists": False}
    try:
        st = os.stat(path)
    except OSError as exc:
        result["error"] = str(exc)
        return result
    result["exists"] = True
    result["mode"] = stat.filemode(st.st_mode)
    result["mode_octal"] = oct(stat.S_IMODE(st.st_mode))
    result["uid"] = st.st_uid
    result["gid"] = st.st_gid
    try:
        result["owner"] = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        result["owner"] = str(st.st_uid)
    try:
        result["group"] = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        result["group"] = str(st.st_gid)
    result["access"] = {
        "read": os.access(path, os.R_OK),
        "write": os.access(path, os.W_OK),
        "execute": os.access(path, os.X_OK),
    }
    open_result = {"ok": False}
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fstat(fd)
            open_result["ok"] = True
        finally:
            os.close(fd)
    except PermissionError as exc:
        open_result["error"] = "PermissionError"
        open_result["errno"] = getattr(exc, "errno", None)
    except FileNotFoundError as exc:
        open_result["error"] = "FileNotFoundError"
    except OSError as exc:
        open_result["error"] = "OSError"
        open_result["errno"] = getattr(exc, "errno", None)
    result["open_rdonly"] = open_result
    return result


def resolve_lib(name):
    """Resolve a library name via ldconfig + realpath (read-only)."""
    result = {"name": name, "ldconfig": [], "realpath": None, "exists": None}
    probed = run(["ldconfig", "-p"], timeout=10)
    if probed.get("status") == "OK" or "returncode" in probed:
        for line in probed.get("stdout", "").splitlines():
            if name not in line:
                continue
            parts = line.split()
            candidate = None
            if "=>" in parts:
                arrow = parts.index("=>")
                if arrow + 1 < len(parts):
                    candidate = parts[arrow + 1]
            if candidate:
                result["ldconfig"].append(
                    {"soname": parts[0] if parts else name, "path": candidate}
                )
    real = None
    for entry in result["ldconfig"]:
        real = os.path.realpath(entry["path"])
        break
    if real is None:
        # Direct realpath of the soname itself (may still resolve via loader cache).
        real = os.path.realpath(name)
    result["realpath"] = real
    if real:
        result["exists"] = os.path.exists(real)
    return result


def ldd_lib(path):
    """Run ldd on a library and list missing dependencies (read-only)."""
    result = {"path": path, "missing": [], "status": None}
    if not path or not os.path.exists(path):
        result["status"] = "SKIP_NO_PATH"
        return result
    probed = run(["ldd", path], timeout=10)
    result["status"] = probed.get("status") or "RAN"
    result["stdout"] = probed.get("stdout", "")
    result["stderr"] = probed.get("stderr", "")
    if probed.get("status") in ("TOOL_MISSING", "TIMEOUT", "OS_ERROR"):
        return result
    for line in probed.get("stdout", "").splitlines():
        if "not found" in line:
            token = line.split()[0] if line.split() else line
            result["missing"].append(token)
    return result


def scan_manifests(directory):
    """List ICD/EGL vendor manifests; read JSON; check library_path existence."""
    results = []
    directory = os.path.abspath(directory)
    try:
        names = sorted(os.listdir(directory))
    except OSError as exc:
        return {"directory": directory, "error": str(exc), "files": []}
    for name in names:
        if not name.endswith(".json"):
            continue
        full = os.path.join(directory, name)
        entry = {"directory": directory, "file": name, "path": full}
        parsed = read_text(full)
        entry["parsed"] = False
        entry["library_path"] = None
        entry["lib_exists"] = None
        entry["lib_realpath"] = None
        entry["read_error"] = None
        if isinstance(parsed, dict) and "error" in parsed:
            entry["read_error"] = parsed["error"]
            results.append(entry)
            continue
        try:
            data = json.loads(parsed)
            entry["parsed"] = True
            icd = data.get("ICD") or data.get("icd") or {}
            entry["library_path"] = icd.get("library_path")
            entry["api_version"] = icd.get("api_version")
            entry["file_format_version"] = data.get("file_format_version")
            lib = entry["library_path"]
            if lib:
                if os.path.isabs(lib):
                    real = os.path.realpath(lib)
                elif '/' in lib:
                    real = os.path.realpath(os.path.join(directory, lib))
                else:
                    real = resolve_lib(lib)['realpath']
                entry["lib_realpath"] = real
                entry["lib_exists"] = os.path.exists(real)
        except (ValueError, TypeError) as exc:
            entry["read_error"] = "JSON_ERROR: " + str(exc)
        results.append(entry)
    return results


def current_user():
    uid = os.getuid()
    try:
        name = pwd.getpwuid(uid).pw_name
    except KeyError:
        name = str(uid)
    groups = []
    for gid in os.getgroups():
        try:
            groups.append(grp.getgrgid(gid).gr_name)
        except KeyError:
            groups.append(str(gid))
    return {"uid": uid, "name": name, "groups": groups}


def nvidia_modules():
    text = read_text(PROC_MODULES)
    entries = []
    if isinstance(text, str):
        for line in text.splitlines():
            fields = line.split()
            if not fields:
                continue
            if fields[0].startswith("nvidia"):
                entries.append(
                    {
                        "name": fields[0],
                        "size": fields[1] if len(fields) > 1 else None,
                        "used": fields[3] if len(fields) > 3 else None,
                        "state": fields[-1] if fields else None,
                    }
                )
    return {
        "nvidia": entries,
        "nvidia_drm_loaded": any(e["name"] == "nvidia_drm" for e in entries),
    }


def tools_status():
    return {tool: shutil.which(tool) for tool in TOOLS}


def self_check():
    """Exercise parsing helpers on synthetic files in a private temp dir."""
    with tempfile.TemporaryDirectory(prefix="diagnose_userspace_selfcheck_") as tmp:
        icd_dir = os.path.join(tmp, "icd.d")
        os.mkdir(icd_dir)
        with open(os.path.join(icd_dir, "fake_icd.json"), "w") as handle:
            json.dump(
                {
                    "file_format_version": "1.0.1",
                    "ICD": {"library_path": "/nonexistent/libfake.so.0", "api_version": "1.0.0"},
                },
                handle,
            )
        manifests = scan_manifests(icd_dir)
        assert len(manifests) == 1
        assert manifests[0]["parsed"] is True
        assert manifests[0]["library_path"] == "/nonexistent/libfake.so.0"
        assert manifests[0]["lib_exists"] is False

        node_dir = os.path.join(tmp, "dri")
        os.mkdir(node_dir)
        fake_node = os.path.join(node_dir, "renderX")
        fd = os.open(fake_node, os.O_RDWR | os.O_CREAT, 0o600)
        os.close(fd)
        stat_result = stat_node(fake_node)
        assert stat_result["exists"] is True
        assert stat_result["open_rdonly"]["ok"] is True

        unresolved = resolve_lib("libdoes_not_exist.so.0")
        assert unresolved["exists"] in (False, None)

        missing = ldd_lib("/nonexistent/nope.so.0")
        assert missing["status"] == "SKIP_NO_PATH"

        assert current_user()["uid"] == os.getuid()
    return {"self_check": "PASS"}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only EGL/Vulkan userspace diagnostic (JSON to stdout)."
    )
    parser.add_argument("--nodes", nargs="*", default=DEFAULT_NODES)
    parser.add_argument("--icd-dir", default=DEFAULT_ICD_DIR)
    parser.add_argument("--egl-dir", default=DEFAULT_EGL_DIR)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Run internal parser self-check on synthetic temp files.",
    )
    args = parser.parse_args(argv)

    if args.self_check:
        report = self_check()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    report = {
        "schema": "phase21-userspace-diagnostic-v1",
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "user": current_user(),
        "nodes": [stat_node(node) for node in args.nodes],
        "libraries": {
            name: {
                "resolve": resolve_lib(name),
                "ldd": ldd_lib(resolve_lib(name).get("realpath") or ""),
            }
            for name in LIBS
        },
        "vulkan_icd_manifests": scan_manifests(args.icd_dir),
        "egl_vendor_manifests": scan_manifests(args.egl_dir),
        "modules": nvidia_modules(),
        "modeset_param": read_text(MODSET_PARAM),
        "nvidia_driver_version": read_text(PROC_NVIDIA_VERSION),
        "tools": tools_status(),
        "timeout_seconds": args.timeout,
        "read_only": True,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

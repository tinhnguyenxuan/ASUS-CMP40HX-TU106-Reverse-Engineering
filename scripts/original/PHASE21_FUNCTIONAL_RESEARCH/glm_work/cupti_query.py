#!/usr/bin/env python3
"""
Read-only discovery probe for libcupti via stdlib ctypes.

Locates an existing libcupti on the filesystem (fixed common CUDA
directories + bounded globs only), loads it, calls the two documented
basic APIs cuptiGetVersion and cuptiGetResultString, and writes a JSON
report to stdout.

Does NOT: use profiling counters, subscribe callbacks, change permissions
or config, use sudo, touch GPU/MMIO, read secrets, or modify the system.
Existing policy RmProfilingAdminOnly=1 is left unchanged.

A successful cuptiGetVersion only proves the CUPTI library is loadable and
exports version metadata -- it does NOT prove counter access or profiling
correctness.

Intended to run on the target machine by a later step; this file is only
authored here, not executed on the target.
"""
import argparse
import ctypes
import datetime
import glob
import json
import os
import sys

SCHEMA = "phase21-cupti-query-v1"
COMMAND = "cupti_query"
MAX_GLOB_MATCHES = 8

BASE_DIRS = [
    "/usr/local/cuda/lib64",
    "/usr/local/cuda/lib64/stubs",
    "/usr/lib/x86_64-linux-gnu",
    "/usr/lib",
    "/opt/cuda/lib64",
]

CUPTI_GLOBS = ["libcupti.so*", "libcupti.so"]


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def candidate_dirs():
    """Fixed common CUDA library dirs, plus $CUDA_HOME/$CUDA_PATH/lib64 if set (not a secret)."""
    dirs = list(BASE_DIRS)
    for env_name in ("CUDA_HOME", "CUDA_PATH"):
        value = os.environ.get(env_name)
        if value:
            dirs.append(os.path.join(value, "lib64"))
            dirs.append(os.path.join(value, "lib64", "stubs"))
    seen = []
    for d in dirs:
        if d not in seen and os.path.isdir(d):
            seen.append(d)
    return seen


def bounded_glob(directory, pattern):
    """Sorted, capped glob matches for one directory (bounded scan)."""
    matches = glob.glob(os.path.join(directory, pattern))
    matches = sorted(matches)
    return matches[:MAX_GLOB_MATCHES]


def collect_paths():
    paths = []
    for directory in candidate_dirs():
        for pattern in CUPTI_GLOBS:
            for path in bounded_glob(directory, pattern):
                if path not in paths:
                    paths.append(path)
    return paths


def load_library(path):
    result = {"path": path, "loaded": False, "error": None}
    try:
        handle = ctypes.CDLL(path)
    except OSError as exc:  # load failure is reported, not raised
        result["error"] = "{0}: {1}".format(type(exc).__name__, exc)
        return result, None
    result["loaded"] = True
    return result, handle


def bind_basic_api(handle):
    """Bind only the two documented basic CUPTI APIs, correct ctypes ABI (Linux x86-64 default C ABI)."""
    handle.cuptiGetVersion.restype = ctypes.c_int
    handle.cuptiGetVersion.argtypes = [ctypes.POINTER(ctypes.c_uint)]
    handle.cuptiGetResultString.restype = ctypes.c_int
    handle.cuptiGetResultString.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]


def query_version(handle):
    """Call cuptiGetVersion, then cuptiGetResultString for the returned code."""
    out = {"rc": None, "version": None, "result_string": None, "result_string_rc": None}
    version = ctypes.c_uint(0)
    try:
        rc = handle.cuptiGetVersion(ctypes.byref(version))
    except (OSError, AttributeError) as exc:
        out["rc"] = "EXCEPTION: {0}: {1}".format(type(exc).__name__, exc)
        return out
    out["rc"] = int(rc)
    if rc == 0:
        out["version"] = int(version.value)
    try:
        result_text = ctypes.c_char_p()
        string_rc = handle.cuptiGetResultString(ctypes.c_int(rc), ctypes.byref(result_text))
        rs = result_text.value
    except (OSError, AttributeError) as exc:
        out["result_string_rc"] = "EXCEPTION: {0}: {1}".format(type(exc).__name__, exc)
        return out
    out["result_string_rc"] = int(string_rc)
    out["result_string"] = rs.decode("utf-8", errors="replace") if rs is not None else None
    return out


def build_report():
    paths = collect_paths()
    load_results = []
    handle = None
    selected = None
    for path in paths:
        entry, h = load_library(path)
        load_results.append(entry)
        if h is not None and handle is None:
            handle = h
            selected = path
    version_out = {"rc": None, "version": None, "result_string": None, "result_string_rc": None}
    if handle is not None:
        bind_basic_api(handle)
        version_out = query_version(handle)
    return {
        "schema": SCHEMA,
        "utc": utc_now(),
        "command": COMMAND,
        "read_only": True,
        "cuda_home_env": {"CUDA_HOME": os.environ.get("CUDA_HOME"), "CUDA_PATH": os.environ.get("CUDA_PATH")},
        "searched_dirs": candidate_dirs(),
        "paths_tried": paths,
        "lib_load": load_results,
        "selected": selected,
        "cuptiGetVersion": version_out,
        "notes": [
            "Version query is discovery only: a successful cuptiGetVersion proves the library loads and exports version metadata; it does NOT prove counter access or profiling correctness.",
            "No profiling counters, callbacks, permissions, config changes, or sudo were used.",
            "Existing policy RmProfilingAdminOnly=1 was not read or modified by this script.",
        ],
    }


def self_check():
    """Pure-Python check: path bounding and report shape, no GPU or libcupti needed."""
    paths = collect_paths()
    assert isinstance(paths, list)
    for directory in candidate_dirs():
        for pattern in CUPTI_GLOBS:
            matches = bounded_glob(directory, pattern)
            assert len(matches) <= MAX_GLOB_MATCHES
            assert matches == sorted(matches)
    report = build_report()
    assert report["schema"] == SCHEMA
    assert report["command"] == COMMAND
    assert report["read_only"] is True
    assert set(report["cuptiGetVersion"]) == {"rc", "version", "result_string", "result_string_rc"}
    json.dumps(report, ensure_ascii=False)
    return {"self_check": "PASS"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only libcupti version probe (JSON to stdout).")
    parser.add_argument("--self-check", action="store_true", help="Run internal checks without a GPU or libcupti.")
    args = parser.parse_args(argv)
    if args.self_check:
        print(json.dumps(self_check(), indent=2, ensure_ascii=False))
        return 0
    print(json.dumps(build_report(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Headless EGL/OpenGL ES 2 shader+raster correctness probe (stdlib ctypes only).

Process-only: a temporary GLVND vendor manifest selecting libEGL_nvidia.so.0
is written to a NamedTemporaryFile and __EGL_VENDOR_LIBRARY_FILENAMES is set
before CDLL("libEGL.so.1"). EGL devices are enumerated with eglQueryDevicesEXT
and only the device whose eglQueryDeviceStringEXT DRM/render-node string
matches /dev/dri/card1 or /dev/dri/renderD129 (BDF 03:00.0 per
TARGET_LIVE_FINDINGS.md) is used -- never an unverified ordinal. The
EGL_NV_device_cuda extension + CUDA PCI bus id path records the
0000:03:00.0 mapping when the DRM strings are absent.

A platform-device display is opened, EGL is initialized, OpenGL ES is bound,
a PBUFFER + ES2 + RGBA8 config is chosen, a 4x4 pbuffer and ES2 context are
created and made current. Then:

1. glClearColor red + glClear, glReadPixels: all 16 pixels must be red
   (clear path verified; a silent draw failure cannot later pass).
2. GLES2 vertex + fragment shaders are compiled with explicit
   glShaderSource(char**) bindings; compile status and info logs recorded.
3. Program linked; link status and program info log recorded.
4. "position" attribute bound, one VBO with a full-screen clip-space
   triangle (-1,-1),(3,-1),(-1,3), viewport 4x4, glDrawArrays(TRIANGLES).
5. Fragment shader emits constant vec4(0,1,0,1); glReadPixels requires all
   16 pixels == (0,255,0,255).

glGetError is collected after every call; the probe passes only when every
collected GL/EGL code is 0 (not merely when the error list is empty).
program/shaders/VBO/context/surface/display are cleaned up before exit.

Writes a JSON report to stdout. Intended to run on the target machine by a
later step; this file is only authored here, not executed on the target.

Does NOT: change system config, use sudo, touch MMIO/GPU registers, reset or
reload drivers, write to DRM nodes, or read secrets. Manifest/env changes are
process-only; context, surface and display are cleaned up on completion.

Scope: raster/shader correctness on a pbuffer only. A pass proves shader
compile/link, VBO draw and pixel readback work on the matched device -- it
does NOT prove scanout (no display/present path is exercised).
"""

import argparse
import ctypes
import datetime
import hashlib
import json
import os
import sys
import tempfile

SCHEMA = "phase21-egl-shader-v1"
COMMAND = "egl_shader_probe"
VENDOR_LIBRARY = "libEGL_nvidia.so.0"
EGL_DISPATCHER = "libEGL.so.1"
TARGET_NODES = ("/dev/dri/card1", "/dev/dri/renderD129")  # BDF 03:00.0, TARGET_LIVE_FINDINGS.md
MANIFEST = {"file_format_version": "1.0.0", "ICD": {"library_path": VENDOR_LIBRARY}}
PBUFFER_SIZE = 4
EXPECTED_RED = [255, 0, 0, 255]
EXPECTED_GREEN = [0, 255, 0, 255]
EXPECTED_PIXEL_COUNT = PBUFFER_SIZE * PBUFFER_SIZE

VERTEX_SOURCE = "attribute vec4 position;\nvoid main() {\n    gl_Position = position;\n}\n"
FRAGMENT_SOURCE = "precision mediump float;\nvoid main() {\n    gl_FragColor = vec4(0.0, 1.0, 0.0, 1.0);\n}\n"

# EGL / EGL_EXT_device_* / EGL_EXT_platform_device constants
EGL_NONE = 0x3038
EGL_SUCCESS = 0x3000
EGL_TRUE = 1
EGL_FALSE = 0
EGL_NO_DISPLAY = 0
EGL_OPENGL_ES_API = 0x30A0
EGL_PBUFFER_BIT = 0x0001
EGL_OPENGL_ES2_BIT = 0x0004
EGL_RENDERABLE_TYPE = 0x3040
EGL_SURFACE_TYPE = 0x3033
EGL_RED_SIZE = 0x3024
EGL_GREEN_SIZE = 0x3023
EGL_BLUE_SIZE = 0x3022
EGL_ALPHA_SIZE = 0x3021
EGL_WIDTH = 0x3057
EGL_HEIGHT = 0x3056
EGL_CONTEXT_CLIENT_VERSION = 0x3098
EGL_VENDOR = 0x3053
EGL_VERSION = 0x3054
EGL_EXTENSIONS = 0x3055
EGL_PLATFORM_DEVICE_EXT = 0x313F
EGL_DEVICE_EXT = 0x322C
EGL_DRM_DEVICE_FILE_EXT = 0x3233
EGL_RENDER_DEVICE = 0x3377
EGL_CUDA_DEVICE_NV = 0x323A  # eglQueryDeviceAttribEXT attr for EGL_NV_device_cuda ordinal

# OpenGL ES 2 constants
GL_NO_ERROR = 0
GL_FALSE = 0
GL_TRUE = 1
GL_COLOR_BUFFER_BIT = 0x00004000
GL_RGBA = 0x1908
GL_UNSIGNED_BYTE = 0x1401
GL_FLOAT = 0x1406
GL_VERTEX_SHADER = 0x8B31
GL_FRAGMENT_SHADER = 0x8B30
GL_COMPILE_STATUS = 0x8B81
GL_LINK_STATUS = 0x8B82
GL_INFO_LOG_LENGTH = 0x8B84
GL_ARRAY_BUFFER = 0x8892
GL_STATIC_DRAW = 0x88E4
GL_TRIANGLES = 0x0004
GL_VENDOR = 0x1F00
GL_RENDERER = 0x1F01
GL_VERSION = 0x1F02

# ctypes types matching the EGL ABI
EGLBoolean = ctypes.c_int
EGLenum = ctypes.c_uint
EGLint = ctypes.c_int
EGLDisplay = ctypes.c_void_p
EGLConfig = ctypes.c_void_p
EGLContext = ctypes.c_void_p
EGLSurface = ctypes.c_void_p
EGLDeviceEXT = ctypes.c_void_p

# ctypes types matching the OpenGL ES 2 ABI
GLuint = ctypes.c_uint
GLint = ctypes.c_int
GLsizei = ctypes.c_int
GLsizeiptr = ctypes.c_ssize_t
GLboolean = ctypes.c_ubyte
GLbitfield = ctypes.c_uint


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def step(name, ok, result=None, error=None):
    return {"step": name, "ok": bool(ok), "result": result, "error": error}


def egl_hex(code):
    return None if code is None else "0x%04x" % (int(code) & 0xFFFF)


def cstr(raw):
    return raw.decode("utf-8", errors="replace") if raw is not None else None


def bind_fn(lib, name, restype, argtypes, steps):
    """Bind one exported EGL function with explicit argtypes/restype."""
    try:
        fn = getattr(lib, name)
    except AttributeError as exc:
        steps.append(step("bind_egl_" + name, False, error="{0}: {1}".format(type(exc).__name__, exc)))
        return None
    fn.restype = restype
    fn.argtypes = list(argtypes)
    return fn


def resolve_proc(lib, name, restype, argtypes, steps):
    """Resolve an extension/GL entry point via eglGetProcAddress with explicit signature."""
    ptr = lib.eglGetProcAddress(name.encode("ascii"))
    if not ptr:
        steps.append(step("resolve_" + name, False, error="eglGetProcAddress returned NULL"))
        return None
    try:
        return ctypes.CFUNCTYPE(restype, *argtypes)(ctypes.cast(ptr, ctypes.c_void_p).value)
    except TypeError as exc:
        steps.append(step("resolve_" + name, False, error="{0}: {1}".format(type(exc).__name__, exc)))
        return None


def group_pixels(data):
    return [list(data[i:i + 4]) for i in range(0, len(data), 4)]


def pixels_all_red(pixels):
    return len(pixels) == EXPECTED_PIXEL_COUNT and all(p == EXPECTED_RED for p in pixels)


def pixels_all_green(pixels):
    return len(pixels) == EXPECTED_PIXEL_COUNT and all(p == EXPECTED_GREEN for p in pixels)


def shader_source_args(source):
    """Build (count, char**, GLint* length) args for glShaderSource."""
    src = source.encode("utf-8") + b"\0"
    strings = (ctypes.c_char_p * 1)(src)
    lengths = (ctypes.c_int * 1)(len(src))
    return 1, ctypes.cast(strings, ctypes.POINTER(ctypes.c_char_p)), ctypes.cast(
        lengths, ctypes.POINTER(ctypes.c_int)
    )


def shader_info_log(getiv, get_info_log, object_id):
    """Query the info log for a shader/program object."""
    length = GLint(0)
    getiv(object_id, GL_INFO_LOG_LENGTH, ctypes.byref(length))
    size = max(int(length.value), 1)
    buf = ctypes.create_string_buffer(size)
    actual = GLint(0)
    get_info_log(object_id, size, ctypes.byref(actual), buf)
    return cstr(buf.value)


def self_check():
    """Pure-Python checks, no GPU and no libEGL needed."""
    red = bytes(EXPECTED_RED * EXPECTED_PIXEL_COUNT)
    green = bytes(EXPECTED_GREEN * EXPECTED_PIXEL_COUNT)
    assert pixels_all_red(group_pixels(red)) is True
    assert pixels_all_green(group_pixels(green)) is True
    corrupted = bytearray(green)
    corrupted[0] = 1
    assert pixels_all_green(bytes(corrupted)) is False
    assert len(group_pixels(green)) == EXPECTED_PIXEL_COUNT
    assert json.loads(json.dumps(MANIFEST)) == MANIFEST
    assert "/dev/dri/card1" in TARGET_NODES and "/dev/dri/renderD129" in TARGET_NODES
    assert EGL_NONE == 0x3038 and EGL_SUCCESS == 0x3000
    assert EGL_WIDTH == 0x3057 and EGL_HEIGHT == 0x3056
    assert EGL_RED_SIZE == 0x3024 and EGL_GREEN_SIZE == 0x3023
    assert EGL_BLUE_SIZE == 0x3022 and EGL_ALPHA_SIZE == 0x3021
    assert GL_VERTEX_SHADER == 0x8B31 and GL_FRAGMENT_SHADER == 0x8B30
    assert GL_COMPILE_STATUS == 0x8B81 and GL_LINK_STATUS == 0x8B82
    assert GL_ARRAY_BUFFER == 0x8892 and GL_STATIC_DRAW == 0x88E4
    return {"self_check": "PASS"}


def run_probe():
    steps = []
    egl_errors = []
    gl_errors = []
    devices_out = []
    selected = None  # dict with index/drm_device/render_node; "handle" holds ctypes device
    egl_client_vendor = None

    display = None
    config = None
    surface = None
    context = None
    egl_version = None
    egl_client_vendor = None
    gl_vendor = None
    gl_renderer = None
    gl_version = None
    pixels = []
    pixels_red = False
    pixels_green = False
    config_checks = []
    shader = {
        "vertex": {"source": VERTEX_SOURCE, "compile_status": None, "info_log": None},
        "fragment": {"source": FRAGMENT_SOURCE, "compile_status": None, "info_log": None},
        "program": {"link_status": None, "info_log": None, "attrib_position": None},
    }

    tmp = None
    lib = None

    def check_egl(where):
        code = lib.eglGetError()
        if code != EGL_SUCCESS:
            entry = {"where": where, "code": egl_hex(code)}
            egl_errors.append(entry)
            steps.append(step(where + ":egl_error", False, error=egl_hex(code)))
        return code == EGL_SUCCESS

    def check_gl(where):
        code = gl_get_error()
        entry = {"where": where, "code": int(code)}
        gl_errors.append(entry)
        return code == GL_NO_ERROR

    # --- 1. process-only vendor manifest + load libEGL dispatcher ---
    try:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=True)
        json.dump(MANIFEST, tmp)
        tmp.flush()
        os.environ["__EGL_VENDOR_LIBRARY_FILENAMES"] = tmp.name
        steps.append(step("write_manifest", True, result={"path": tmp.name, "content": MANIFEST}))
    except (OSError, ValueError) as exc:
        steps.append(step("write_manifest", False, error="{0}: {1}".format(type(exc).__name__, exc)))
    try:
        lib = ctypes.CDLL(EGL_DISPATCHER)
        steps.append(step("load_egl", True, result=EGL_DISPATCHER))
    except OSError as exc:
        steps.append(step("load_egl", False, error="{0}: {1}".format(type(exc).__name__, exc)))

    # --- 2. core EGL bindings (all explicit argtypes/restype) ---
    if lib is not None:
        for name, restype, argtypes in [
            ("eglInitialize", EGLBoolean, [EGLDisplay, ctypes.POINTER(EGLint), ctypes.POINTER(EGLint)]),
            ("eglTerminate", EGLBoolean, [EGLDisplay]),
            ("eglQueryString", ctypes.c_char_p, [EGLDisplay, EGLint]),
            ("eglChooseConfig", EGLBoolean, [EGLDisplay, ctypes.POINTER(EGLint), ctypes.POINTER(EGLConfig), EGLint, ctypes.POINTER(EGLint)]),
            ("eglGetConfigAttrib", EGLBoolean, [EGLDisplay, EGLConfig, EGLint, ctypes.POINTER(EGLint)]),
            ("eglCreatePbufferSurface", EGLSurface, [EGLDisplay, EGLConfig, ctypes.POINTER(EGLint)]),
            ("eglCreateContext", EGLContext, [EGLDisplay, EGLConfig, EGLContext, ctypes.POINTER(EGLint)]),
            ("eglMakeCurrent", EGLBoolean, [EGLDisplay, EGLSurface, EGLSurface, EGLContext]),
            ("eglDestroySurface", EGLBoolean, [EGLDisplay, EGLSurface]),
            ("eglDestroyContext", EGLBoolean, [EGLDisplay, EGLContext]),
            ("eglGetError", EGLint, []),
            ("eglBindAPI", EGLBoolean, [EGLenum]),
            ("eglGetProcAddress", ctypes.c_void_p, [ctypes.c_char_p]),
        ]:
            if bind_fn(lib, name, restype, argtypes, steps) is None:
                lib = None
                break

    # --- 3. extension entry points via eglGetProcAddress ---
    egl_query_devices = None
    egl_query_device_string = None
    egl_get_platform_display = None
    if lib is not None:
        egl_query_devices = resolve_proc(lib, "eglQueryDevicesEXT", EGLBoolean,
                                         [EGLint, ctypes.POINTER(EGLDeviceEXT), ctypes.POINTER(EGLint)], steps)
        egl_query_device_string = resolve_proc(lib, "eglQueryDeviceStringEXT", ctypes.c_char_p,
                                               [EGLDeviceEXT, EGLint], steps)
        egl_get_platform_display = resolve_proc(lib, "eglGetPlatformDisplayEXT", EGLDisplay,
                                                [EGLenum, ctypes.c_void_p, ctypes.POINTER(EGLint)], steps)
        if None in (egl_query_devices, egl_query_device_string, egl_get_platform_display):
            steps.append(step("extension_procs", False, error="one or more EGL extension entry points missing"))

    # --- 4. enumerate devices; match by DRM/render-node string only (no ordinal) ---
    if lib is not None and None not in (egl_query_devices, egl_query_device_string):
        num = EGLint(0)
        rc = egl_query_devices(0, None, ctypes.byref(num))
        check_egl("eglQueryDevicesEXT(count)")
        count = num.value if rc else 0
        steps.append(step("eglQueryDevicesEXT", bool(rc and count > 0), result={"count": count, "rc": bool(rc)}))
        if rc and count > 0:
            dev_array = (EGLDeviceEXT * count)()
            rc = egl_query_devices(count, dev_array, ctypes.byref(num))
            check_egl("eglQueryDevicesEXT(list)")
            found = num.value if rc else 0
            for i in range(min(count, found)):
                dev = dev_array[i]
                drm = None
                render = None
                raw = egl_query_device_string(dev, EGL_DRM_DEVICE_FILE_EXT)
                drm = cstr(raw)
                raw = egl_query_device_string(dev, EGL_RENDER_DEVICE)
                render = cstr(raw)
                matched = drm in TARGET_NODES or render in TARGET_NODES
                extensions = cstr(egl_query_device_string(dev, EGL_EXTENSIONS)) or ''
                if not matched and 'EGL_NV_device_cuda' in extensions.split():
                    query_attrib = resolve_proc(lib, 'eglQueryDeviceAttribEXT', EGLBoolean, [EGLDeviceEXT, EGLint, ctypes.POINTER(ctypes.c_ssize_t)], steps)
                    ordinal = ctypes.c_ssize_t()
                    if query_attrib and query_attrib(dev, EGL_CUDA_DEVICE_NV, ctypes.byref(ordinal)):
                        cuda = ctypes.CDLL('libcuda.so.1')
                        cuda.cuInit.argtypes = [ctypes.c_uint]
                        cuda.cuInit.restype = ctypes.c_int
                        cuda.cuDeviceGetPCIBusId.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
                        cuda.cuDeviceGetPCIBusId.restype = ctypes.c_int
                        bus = ctypes.create_string_buffer(32)
                        if cuda.cuInit(0) == 0 and cuda.cuDeviceGetPCIBusId(bus, 32, int(ordinal.value)) == 0:
                            matched = bus.value.decode() == '0000:03:00.0'
                            steps.append(step('EGL_CUDA_DEVICE_NV_to_BDF', matched, result=bus.value.decode()))
                entry = {"index": i, "drm_device": drm, "render_node": render, "matched": matched}
                devices_out.append(entry)
                if matched and selected is None:
                    selected = entry
                    selected["handle"] = dev  # ctypes handle, excluded from JSON output
    if selected is None:
        steps.append(step("select_device", False, error="no device matched {0}; ordinal fallback disabled".format(list(TARGET_NODES))))

    # --- 5. platform device display ---
    if selected is not None and lib is not None and egl_get_platform_display is not None:
        display = egl_get_platform_display(EGL_PLATFORM_DEVICE_EXT, selected["handle"], None)
        check_egl("eglGetPlatformDisplayEXT")
        steps.append(step("eglGetPlatformDisplayEXT", display is not None,
                          result={"selected_index": selected.get("index")}))
        if display is None:
            steps.append(step("eglGetPlatformDisplayEXT", False, error="returned EGL_NO_DISPLAY"))

    # --- 6. initialize EGL ---
    if display is not None:
        major = EGLint(0)
        minor = EGLint(0)
        rc = lib.eglInitialize(display, ctypes.byref(major), ctypes.byref(minor))
        check_egl("eglInitialize")
        egl_version = [major.value, minor.value] if rc else None
        steps.append(step("eglInitialize", bool(rc), result={"major": major.value, "minor": minor.value}))
        if rc:
            raw = lib.eglQueryString(display, EGL_VENDOR)
            egl_client_vendor = cstr(raw)
            check_egl("eglQueryString(EGL_VENDOR)")

    # --- 7. bind OpenGL ES API ---
    if display is not None and egl_version is not None:
        rc = lib.eglBindAPI(EGL_OPENGL_ES_API)
        check_egl("eglBindAPI")
        steps.append(step("eglBindAPI", bool(rc), result={"api": "EGL_OPENGL_ES_API"}))
        if not rc:
            display = None  # cannot create an ES context without the API bound

    # --- 8. choose PBUFFER + ES2 + RGBA8 config ---
    config_ok = False
    if display is not None:
        cfg_list = [EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
                    EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
                    EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8,
                    EGL_NONE]
        cfg_attribs = (EGLint * len(cfg_list))(*cfg_list)
        num_config = EGLint(0)
        config = EGLConfig()
        rc = lib.eglChooseConfig(display, cfg_attribs, ctypes.byref(config), 1, ctypes.byref(num_config))
        check_egl("eglChooseConfig")
        config_ok = bool(rc and num_config.value == 1 and config.value != 0)
        steps.append(step("eglChooseConfig", config_ok, result={"num_config": num_config.value}))
        if config_ok:
            for name, attr, expected in [
                ("surface_type", EGL_SURFACE_TYPE, EGL_PBUFFER_BIT),
                ("renderable_type", EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT),
                ("red_size", EGL_RED_SIZE, 8),
                ("green_size", EGL_GREEN_SIZE, 8),
                ("blue_size", EGL_BLUE_SIZE, 8),
                ("alpha_size", EGL_ALPHA_SIZE, 8),
            ]:
                value = EGLint(0)
                rc = lib.eglGetConfigAttrib(display, config, attr, ctypes.byref(value))
                check_egl("eglGetConfigAttrib(" + name + ")")
                ok = bool(rc and ((value.value & expected) == expected if name in ('surface_type', 'renderable_type') else value.value == expected))
                config_checks.append({"attribute": name, "expected": expected, "actual": value.value if rc else None, "ok": ok})
                if not ok:
                    config_ok = False
            steps.append(step("verify_config_attribs", config_ok, result=config_checks))

    # --- 9. create 4x4 pbuffer surface ---
    if config_ok:
        pb_attribs = (EGLint * 5)(EGL_WIDTH, PBUFFER_SIZE, EGL_HEIGHT, PBUFFER_SIZE, EGL_NONE)
        surface = lib.eglCreatePbufferSurface(display, config, pb_attribs)
        check_egl("eglCreatePbufferSurface")
        steps.append(step("eglCreatePbufferSurface", surface is not None, result={"width": PBUFFER_SIZE, "height": PBUFFER_SIZE}))

    # --- 10. create ES2 context ---
    if surface is not None:
        ctx_attribs = (EGLint * 3)(EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE)
        context = lib.eglCreateContext(display, config, None, ctx_attribs)
        check_egl("eglCreateContext")
        steps.append(step("eglCreateContext", context is not None, result={"client_version": 2}))

    # --- 11. make current ---
    if context is not None:
        rc = lib.eglMakeCurrent(display, surface, surface, context)
        check_egl("eglMakeCurrent")
        steps.append(step("eglMakeCurrent", bool(rc)))

    # --- 12. resolve GL entry points via eglGetProcAddress ---
    gl_get_error = None
    gl_clear_color = None
    gl_clear = None
    gl_read_pixels = None
    gl_get_string = None
    gl_create_shader = None
    gl_shader_source = None
    gl_compile_shader = None
    gl_get_shaderiv = None
    gl_get_shader_info_log = None
    gl_create_program = None
    gl_attach_shader = None
    gl_link_program = None
    gl_get_programiv = None
    gl_get_program_info_log = None
    gl_get_attrib_location = None
    gl_gen_buffers = None
    gl_bind_buffer = None
    gl_buffer_data = None
    gl_vertex_attrib_pointer = None
    gl_enable_vertex_attrib_array = None
    gl_viewport = None
    gl_draw_arrays = None
    gl_detach_shader = None
    gl_delete_shader = None
    gl_delete_program = None
    gl_delete_buffers = None
    if context is not None:
        gl_get_error = resolve_proc(lib, "glGetError", EGLenum, [], steps)
        gl_clear_color = resolve_proc(lib, "glClearColor", None, [ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float], steps)
        gl_clear = resolve_proc(lib, "glClear", None, [GLbitfield], steps)
        gl_read_pixels = resolve_proc(lib, "glReadPixels", None,
                                      [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, EGLenum, EGLenum, ctypes.c_void_p], steps)
        gl_get_string = resolve_proc(lib, "glGetString", ctypes.c_char_p, [EGLenum], steps)
        gl_create_shader = resolve_proc(lib, "glCreateShader", GLuint, [EGLenum], steps)
        gl_shader_source = resolve_proc(lib, "glShaderSource", None,
                                        [GLuint, GLsizei, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(GLint)], steps)
        gl_compile_shader = resolve_proc(lib, "glCompileShader", None, [GLuint], steps)
        gl_get_shaderiv = resolve_proc(lib, "glGetShaderiv", None, [GLuint, EGLenum, ctypes.POINTER(GLint)], steps)
        gl_get_shader_info_log = resolve_proc(lib, "glGetShaderInfoLog", None,
                                              [GLuint, GLsizei, ctypes.POINTER(GLint), ctypes.POINTER(ctypes.c_char)], steps)
        gl_create_program = resolve_proc(lib, "glCreateProgram", GLuint, [], steps)
        gl_attach_shader = resolve_proc(lib, "glAttachShader", None, [GLuint, GLuint], steps)
        gl_link_program = resolve_proc(lib, "glLinkProgram", None, [GLuint], steps)
        gl_use_program = resolve_proc(lib, "glUseProgram", None, [GLuint], steps)
        gl_get_programiv = resolve_proc(lib, "glGetProgramiv", None, [GLuint, EGLenum, ctypes.POINTER(GLint)], steps)
        gl_get_program_info_log = resolve_proc(lib, "glGetProgramInfoLog", None,
                                               [GLuint, GLsizei, ctypes.POINTER(GLint), ctypes.POINTER(ctypes.c_char)], steps)
        gl_get_attrib_location = resolve_proc(lib, "glGetAttribLocation", EGLint, [GLuint, ctypes.c_char_p], steps)
        gl_gen_buffers = resolve_proc(lib, "glGenBuffers", None, [GLsizei, ctypes.POINTER(GLuint)], steps)
        gl_bind_buffer = resolve_proc(lib, "glBindBuffer", None, [EGLenum, GLuint], steps)
        gl_buffer_data = resolve_proc(lib, "glBufferData", None,
                                      [EGLenum, GLsizeiptr, ctypes.c_void_p, EGLenum], steps)
        gl_vertex_attrib_pointer = resolve_proc(lib, "glVertexAttribPointer", None,
                                                [GLuint, GLint, EGLenum, GLboolean, GLsizei, ctypes.c_void_p], steps)
        gl_enable_vertex_attrib_array = resolve_proc(lib, "glEnableVertexAttribArray", None, [GLuint], steps)
        gl_viewport = resolve_proc(lib, "glViewport", None, [ctypes.c_int, ctypes.c_int, GLsizei, GLsizei], steps)
        gl_draw_arrays = resolve_proc(lib, "glDrawArrays", None, [EGLenum, GLint, GLsizei], steps)
        gl_detach_shader = resolve_proc(lib, "glDetachShader", None, [GLuint, GLuint], steps)
        gl_delete_shader = resolve_proc(lib, "glDeleteShader", None, [GLuint], steps)
        gl_delete_program = resolve_proc(lib, "glDeleteProgram", None, [GLuint], steps)
        gl_delete_buffers = resolve_proc(lib, "glDeleteBuffers", None, [GLsizei, ctypes.POINTER(GLuint)], steps)
        if None in (gl_get_error, gl_clear_color, gl_clear, gl_read_pixels, gl_get_string,
                    gl_create_shader, gl_shader_source, gl_compile_shader, gl_get_shaderiv,
                    gl_get_shader_info_log, gl_create_program, gl_attach_shader, gl_link_program,
                    gl_get_programiv, gl_get_program_info_log, gl_get_attrib_location,
                    gl_gen_buffers, gl_bind_buffer, gl_buffer_data, gl_vertex_attrib_pointer,
                    gl_enable_vertex_attrib_array, gl_viewport, gl_draw_arrays,
                    gl_detach_shader, gl_delete_shader, gl_delete_program, gl_delete_buffers):
            steps.append(step("gl_entry_points", False, error="one or more GL entry points missing"))

    gl_ready = None not in (gl_get_error, gl_clear_color, gl_clear, gl_read_pixels,
                            gl_create_shader, gl_shader_source, gl_compile_shader, gl_get_shaderiv,
                            gl_get_shader_info_log, gl_create_program, gl_attach_shader, gl_link_program,
                            gl_get_programiv, gl_get_program_info_log, gl_get_attrib_location,
                            gl_gen_buffers, gl_bind_buffer, gl_buffer_data, gl_vertex_attrib_pointer,
                            gl_enable_vertex_attrib_array, gl_viewport, gl_draw_arrays,
                            gl_detach_shader, gl_delete_shader, gl_delete_program, gl_delete_buffers)

    vs = 0
    fs = 0
    program = 0
    vbo_id = GLuint(0)
    attrib_loc = -1

    # --- 13. clear red, verify clear path (silent draw failure cannot pass) ---
    if gl_ready:
        gl_clear_color(1.0, 0.0, 0.0, 1.0)
        check_gl("glClearColor")
        gl_clear(GL_COLOR_BUFFER_BIT)
        check_gl("glClear")
        buf = ctypes.create_string_buffer(PBUFFER_SIZE * PBUFFER_SIZE * 4)
        addr = ctypes.cast(buf, ctypes.c_void_p).value
        gl_read_pixels(0, 0, PBUFFER_SIZE, PBUFFER_SIZE, GL_RGBA, GL_UNSIGNED_BYTE, addr)
        check_gl("glReadPixels(red)")
        pixels = group_pixels(buf.raw)
        pixels_red = pixels_all_red(pixels)
        steps.append(step("glClearColor+glClear(red)", True, result={"color": EXPECTED_RED}))
        steps.append(step("glReadPixels(red)", bool(pixels_red), result={"count": len(pixels), "all_red": pixels_red}))

        # --- 14. vertex shader: source (char**), compile, status + log ---
        vs = int(gl_create_shader(GL_VERTEX_SHADER))
        check_gl("glCreateShader(vertex)")
        count, src_ptr, len_ptr = shader_source_args(VERTEX_SOURCE)
        gl_shader_source(vs, count, src_ptr, len_ptr)
        check_gl("glShaderSource(vertex)")
        gl_compile_shader(vs)
        check_gl("glCompileShader(vertex)")
        cstatus = GLint(0)
        gl_get_shaderiv(vs, GL_COMPILE_STATUS, ctypes.byref(cstatus))
        shader["vertex"]["compile_status"] = bool(cstatus.value)
        shader["vertex"]["info_log"] = shader_info_log(gl_get_shaderiv, gl_get_shader_info_log, vs)
        steps.append(step("glCompileShader(vertex)", shader["vertex"]["compile_status"],
                          result={"info_log": shader["vertex"]["info_log"]}))

        # --- 15. fragment shader: source, compile, status + log ---
        fs = int(gl_create_shader(GL_FRAGMENT_SHADER))
        check_gl("glCreateShader(fragment)")
        count, src_ptr, len_ptr = shader_source_args(FRAGMENT_SOURCE)
        gl_shader_source(fs, count, src_ptr, len_ptr)
        check_gl("glShaderSource(fragment)")
        gl_compile_shader(fs)
        check_gl("glCompileShader(fragment)")
        fstatus = GLint(0)
        gl_get_shaderiv(fs, GL_COMPILE_STATUS, ctypes.byref(fstatus))
        shader["fragment"]["compile_status"] = bool(fstatus.value)
        shader["fragment"]["info_log"] = shader_info_log(gl_get_shaderiv, gl_get_shader_info_log, fs)
        steps.append(step("glCompileShader(fragment)", shader["fragment"]["compile_status"],
                          result={"info_log": shader["fragment"]["info_log"]}))

        # --- 16. program: attach, link, status + log, attrib location ---
        program = int(gl_create_program())
        check_gl("glCreateProgram")
        gl_attach_shader(program, vs)
        check_gl("glAttachShader(vertex)")
        gl_attach_shader(program, fs)
        check_gl("glAttachShader(fragment)")
        gl_link_program(program)
        check_gl("glLinkProgram")
        lstatus = GLint(0)
        gl_get_programiv(program, GL_LINK_STATUS, ctypes.byref(lstatus))
        shader["program"]["link_status"] = bool(lstatus.value)
        shader["program"]["info_log"] = shader_info_log(gl_get_programiv, gl_get_program_info_log, program)
        attrib_loc = gl_get_attrib_location(program, b"position")
        check_gl("glGetAttribLocation")
        shader["program"]["attrib_position"] = attrib_loc
        steps.append(step("glLinkProgram", shader["program"]["link_status"],
                          result={"attrib_position": attrib_loc, "info_log": shader["program"]["info_log"]}))
        if gl_use_program is None:
            raise RuntimeError("glUseProgram unavailable")
        gl_use_program(program)
        check_gl("glUseProgram")

        # --- 17. VBO full-screen triangle, viewport 4x4, draw ---
        positions = (ctypes.c_float * 6)(-1.0, -1.0, 3.0, -1.0, -1.0, 3.0)
        gl_gen_buffers(1, ctypes.byref(vbo_id))
        check_gl("glGenBuffers")
        gl_bind_buffer(GL_ARRAY_BUFFER, vbo_id.value)
        check_gl("glBindBuffer")
        gl_buffer_data(GL_ARRAY_BUFFER, ctypes.sizeof(positions), ctypes.cast(positions, ctypes.c_void_p), GL_STATIC_DRAW)
        check_gl("glBufferData")
        if attrib_loc >= 0:
            gl_vertex_attrib_pointer(attrib_loc, 2, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
            check_gl("glVertexAttribPointer")
            gl_enable_vertex_attrib_array(attrib_loc)
            check_gl("glEnableVertexAttribArray")
        else:
            steps.append(step("glVertexAttribPointer", False, error="position attribute location %d" % attrib_loc))
        gl_viewport(0, 0, PBUFFER_SIZE, PBUFFER_SIZE)
        check_gl("glViewport")
        gl_draw_arrays(GL_TRIANGLES, 0, 3)
        check_gl("glDrawArrays")

        # --- 18. read back green (clear was red; draw must have overwritten) ---
        buf = ctypes.create_string_buffer(PBUFFER_SIZE * PBUFFER_SIZE * 4)
        addr = ctypes.cast(buf, ctypes.c_void_p).value
        gl_read_pixels(0, 0, PBUFFER_SIZE, PBUFFER_SIZE, GL_RGBA, GL_UNSIGNED_BYTE, addr)
        check_gl("glReadPixels(green)")
        gl_errors.append({"where": "glGetString", "code": gl_get_error()})
        pixels = group_pixels(buf.raw)
        pixels_green = pixels_all_green(pixels)
        gl_vendor = cstr(gl_get_string(GL_VENDOR))
        gl_renderer = cstr(gl_get_string(GL_RENDERER))
        gl_version = cstr(gl_get_string(GL_VERSION))
        steps.append(step("glDrawArrays+glReadPixels(green)", bool(pixels_green),
                          result={"count": len(pixels), "all_green": pixels_green}))
        steps.append(step("glGetString", True, result={"vendor": gl_vendor, "renderer": gl_renderer, "version": gl_version}))

        # --- 19. clean GL objects: detach/delete shaders, program, VBO ---
        if program:
            if vs:
                gl_detach_shader(program, vs)
                check_gl("glDetachShader(vertex)")
            if fs:
                gl_detach_shader(program, fs)
                check_gl("glDetachShader(fragment)")
        if vs:
            gl_delete_shader(vs)
            check_gl("glDeleteShader(vertex)")
        if fs:
            gl_delete_shader(fs)
            check_gl("glDeleteShader(fragment)")
        if program:
            gl_delete_program(program)
            check_gl("glDeleteProgram")
        if vbo_id.value:
            gl_delete_buffers(1, ctypes.byref(vbo_id))
            check_gl("glDeleteBuffers")

    # --- 20. cleanup: release, destroy context, destroy surface, terminate ---
    if lib is not None:
        if display is not None and (surface is not None or context is not None):
            lib.eglMakeCurrent(display, None, None, None)
            check_egl("eglMakeCurrent(release)")
            steps.append(step("eglMakeCurrent(release)", True))
        if context is not None:
            rc = lib.eglDestroyContext(display, context)
            check_egl("eglDestroyContext")
            steps.append(step("eglDestroyContext", bool(rc)))
        if surface is not None:
            rc = lib.eglDestroySurface(display, surface)
            check_egl("eglDestroySurface")
            steps.append(step("eglDestroySurface", bool(rc)))
        if display is not None:
            rc = lib.eglTerminate(display)
            check_egl("eglTerminate")
            steps.append(step("eglTerminate", bool(rc)))

    # --- 21. pass only if matched GPU, NVIDIA renderer, shaders+draw+readback OK, no errors ---
    matched_gpu = selected is not None
    nvidia_hardware = bool(gl_renderer and "NVIDIA" in gl_renderer)
    egl_clean = len(egl_errors) == 0
    gl_clean = all(entry["code"] == GL_NO_ERROR for entry in gl_errors)
    shader_ok = bool(shader["vertex"]["compile_status"] and shader["fragment"]["compile_status"]
                     and shader["program"]["link_status"])
    draw_ok = pixels_all_green(pixels)
    passed = bool(matched_gpu and nvidia_hardware and shader_ok and draw_ok and egl_clean and gl_clean)

    selected_json = {k: v for k, v in selected.items() if k != "handle"} if selected else None

    report = {
        "schema": SCHEMA,
        "utc": utc_now(),
        "command": COMMAND,
        "read_only": True,
        "vendor_library": VENDOR_LIBRARY,
        "egl_dispatcher": EGL_DISPATCHER,
        "target_nodes": list(TARGET_NODES),
        "manifest": MANIFEST,
        "manifest_path": tmp.name if tmp is not None else None,
        "manifest_auto_cleanup": True,
        "steps": steps,
        "egl_errors": egl_errors,
        "gl_errors": gl_errors,
        "devices": devices_out,
        "selected_device": selected_json,
        "egl_version": egl_version,
        "egl_client_vendor": egl_client_vendor,
        "gl": {"vendor": gl_vendor, "renderer": gl_renderer, "version": gl_version},
        "shaders": shader,
        "pixels": {
            "size": [PBUFFER_SIZE, PBUFFER_SIZE],
            "count": EXPECTED_PIXEL_COUNT,
            "expected_per_pixel": EXPECTED_GREEN,
            "read": pixels,
            "all_match": pixels_green,
            "clear_red_verified": pixels_red,
        },
        "matched_gpu": matched_gpu,
        "nvidia_hardware": nvidia_hardware,
        "egl_errors_clean": egl_clean,
        "gl_errors_clean": gl_clean,
        "pass": passed,
        "source_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
        "notes": [
            "This probe verifies shader compile/link, VBO draw and glReadPixels raster correctness on a 4x4 pbuffer only.",
            "A pass does NOT prove scanout: no display/present path is exercised (raster/shader correctness, not scanout).",
            "Clear-red-first means a silent draw failure leaves red pixels and cannot pass; final expectation is all green (0,255,0,255).",
            "Device selection matches eglQueryDeviceStringEXT output against /dev/dri/card1 or /dev/dri/renderD129 (BDF 03:00.0); no unverified ordinal is used.",
            "EGL_NV_device_cuda ordinal -> CUDA PCI bus id path records the 0000:03:00.0 mapping when DRM strings are absent.",
            "Manifest and environment changes are process-only; the temp manifest is removed via NamedTemporaryFile cleanup. No sudo, config, group, MMIO, or driver changes.",
        ],
    }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Headless EGL/OpenGL ES 2 shader+raster correctness probe (JSON to stdout).")
    parser.add_argument("--self-check", action="store_true", help="Run internal checks without a GPU or libEGL.")
    args = parser.parse_args(argv)
    if args.self_check:
        print(json.dumps(self_check(), indent=2, ensure_ascii=False))
        return 0
    print(json.dumps(run_probe(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

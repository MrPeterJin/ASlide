from __future__ import annotations

import importlib.util
import sys
import types
import ctypes
from ctypes import POINTER, c_char_p, c_ubyte, cast
from io import BytesIO
from pathlib import Path

from PIL import Image


def test_associated_image_read_frees_native_buffer_after_copy(monkeypatch) -> None:
    from Aslide.kfb import kfb_lowlevel

    image = Image.new("RGB", (2, 2), (255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    payload = buffer.getvalue()

    native_array = (c_ubyte * len(payload))(*payload)
    freed: list[object] = []

    def fake_dimensions(osr, name):
        return (2, 2), len(payload)

    def fake_read(osr, name, out_ptr):
        typed_ptr = cast(out_ptr, POINTER(POINTER(c_ubyte)))
        typed_ptr[0] = cast(native_array, POINTER(c_ubyte))
        return True

    def fake_free(ptr):
        freed.append(ptr)
        return 0

    monkeypatch.setattr(
        kfb_lowlevel, "kfbslide_get_associated_image_dimensions", fake_dimensions
    )
    monkeypatch.setattr(kfb_lowlevel, "_kfbslide_read_associated_image", fake_read)
    monkeypatch.setattr(kfb_lowlevel, "DeleteImageDataFunc", fake_free)

    result = kfb_lowlevel.kfbslide_read_associated_image(object(), "label")

    assert result.size == (2, 2)
    assert len(freed) == 1
    assert freed[0]


class _DummyFunc:
    def __init__(self, name: str) -> None:
        self.name = name
        self.argtypes = None
        self.restype = None
        self.errcheck = None

    def __call__(self, *args, **kwargs):
        return 0


class _DummyLibrary:
    def __getattr__(self, name: str) -> _DummyFunc:
        return _DummyFunc(name)


def test_kfb_loader_prefers_bundled_library_paths(monkeypatch) -> None:
    module_path = (
        Path(__file__).resolve().parents[1] / "Aslide" / "kfb" / "kfb_lowlevel.py"
    )
    bundled_dir = module_path.parent / "lib"
    calls: list[str] = []

    def fake_cdll(name: str, mode: int | None = None) -> _DummyLibrary:
        calls.append(str(name))
        return _DummyLibrary()

    lowlevel_module = types.ModuleType("openslide.lowlevel")
    lowlevel_module.__dict__.update(
        {
            "OpenSlideError": Exception,
            "OpenSlideUnsupportedFormatError": Exception,
            "_utf8_p": c_char_p,
            "_check_string": lambda result, func, args: result,
            "_check_close": lambda result, func, args: None,
        }
    )

    openslide_module = types.ModuleType("openslide")
    openslide_module.__dict__["lowlevel"] = lowlevel_module

    version_module = types.ModuleType("openslide._version")
    version_module.__dict__["__version__"] = "test"

    monkeypatch.setattr(ctypes.cdll, "LoadLibrary", fake_cdll)
    monkeypatch.setattr(ctypes, "CDLL", fake_cdll)
    monkeypatch.setitem(sys.modules, "openslide", openslide_module)
    monkeypatch.setitem(sys.modules, "openslide.lowlevel", lowlevel_module)
    monkeypatch.setitem(sys.modules, "openslide._version", version_module)

    spec = importlib.util.spec_from_file_location(
        "test_kfb_lowlevel_loader", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    expected_prefix = [
        str(bundled_dir / "libjpeg.so.9"),
        str(bundled_dir / "libkfbslide.so"),
        str(bundled_dir / "libImageOperationLib.so"),
    ]

    assert calls[: len(expected_prefix)] == expected_prefix

from __future__ import annotations

from ctypes import POINTER, c_ubyte, cast
from io import BytesIO

from PIL import Image


def test_associated_image_read_does_not_free_native_buffer(monkeypatch) -> None:
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
    assert freed == []

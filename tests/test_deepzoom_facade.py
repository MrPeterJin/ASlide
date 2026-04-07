from __future__ import annotations


def test_deepzoom_uses_registry_entry(monkeypatch, fake_backend_classes) -> None:
    from Aslide.aslide import Slide
    from Aslide.deepzoom import DeepZoom
    from Aslide.registry import FormatEntry

    fake_slide_backend, fake_deepzoom_backend = fake_backend_classes

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="fake",
            extensions=(".fake",),
            slide_backend=fake_slide_backend,
            deepzoom_backend=fake_deepzoom_backend,
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.fake")
    deepzoom = DeepZoom(slide)

    assert deepzoom.backend.__class__ is fake_deepzoom_backend
    assert deepzoom.tile_count == 85


def test_deepzoom_delegates_tile_calls(monkeypatch, fake_backend_classes) -> None:
    from Aslide.aslide import Slide
    from Aslide.deepzoom import DeepZoom
    from Aslide.registry import FormatEntry

    fake_slide_backend, fake_deepzoom_backend = fake_backend_classes

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="fake",
            extensions=(".fake",),
            slide_backend=fake_slide_backend,
            deepzoom_backend=fake_deepzoom_backend,
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.fake")
    deepzoom = DeepZoom(slide)

    assert deepzoom.get_dzi("jpeg") == "dzi:jpeg"
    assert deepzoom.get_tile(2, (3, 4)) == (2, (3, 4))

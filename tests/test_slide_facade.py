from __future__ import annotations


def test_slide_uses_registry_selected_backend(
    monkeypatch, fake_backend_classes
) -> None:
    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    fake_slide_backend, _ = fake_backend_classes

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="fake",
            extensions=(".fake",),
            slide_backend=fake_slide_backend,
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.fake")

    assert slide.backend.format_id == "fake"
    assert slide.dimensions == (100, 50)


def test_slide_context_manager_closes_backend(
    monkeypatch, fake_backend_classes
) -> None:
    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    fake_slide_backend, _ = fake_backend_classes

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="fake",
            extensions=(".fake",),
            slide_backend=fake_slide_backend,
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    with Slide("demo.fake") as slide:
        backend = slide.backend

    assert backend.closed is True


def test_slide_label_image_uses_backend_contract(
    monkeypatch, fake_backend_classes
) -> None:
    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    fake_slide_backend, _ = fake_backend_classes

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="fake",
            extensions=(".fake",),
            slide_backend=fake_slide_backend,
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.fake")

    assert slide.label_image() == "label-image"


def test_associated_images_falls_back_to_generated_thumbnail(
    monkeypatch, fake_associated_images_backend
) -> None:
    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="fake",
            extensions=(".fake",),
            slide_backend=fake_associated_images_backend,
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.fake")

    assert slide.associated_images["label"] == "label-image"
    assert slide.associated_images["macro"] == "macro-image"
    assert slide.associated_images["thumbnail"] == ("generated-thumbnail", (512, 512))


def test_associated_images_fallback_preserves_lazy_backend_mapping(
    monkeypatch, fake_lazy_associated_images_backend
) -> None:
    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="fake",
            extensions=(".fake",),
            slide_backend=fake_lazy_associated_images_backend,
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.fake")
    lazy_images = slide.backend.associated_images

    assert slide.associated_images["label"] == "label-image"
    assert lazy_images.accessed_keys == ["label"]
    assert slide.associated_images["thumbnail"] == ("generated-thumbnail", (512, 512))

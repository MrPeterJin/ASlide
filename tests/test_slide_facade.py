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

    backend = None
    with Slide("demo.fake") as slide:
        backend = slide.backend

    assert backend is not None
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


def test_slide_preserves_brightfield_read_region_behavior(
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
            slide_family="brightfield",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.fake")

    assert slide.slide_family == "brightfield"
    assert slide.read_region((1, 2), 0, (3, 4)) == ((1, 2), 0, (3, 4))


def test_slide_rejects_generic_reads_for_multiplex_slides(
    monkeypatch, fake_multiplex_backend
) -> None:
    import pytest

    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="qptiff",
            extensions=(".qptiff",),
            slide_backend=fake_multiplex_backend,
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.qptiff")

    assert slide.slide_family == "multiplex"
    with pytest.raises(Exception, match="biomarker|multiplex|channel"):
        slide.read_region((1, 2), 0, (3, 4))


def test_slide_exposes_explicit_biomarker_reads_for_multiplex_slides(
    monkeypatch, fake_multiplex_backend
) -> None:
    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="qptiff",
            extensions=(".qptiff",),
            slide_backend=fake_multiplex_backend,
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.qptiff")

    assert slide.list_biomarkers() == ["DAPI", "CD3"]
    assert slide.read_biomarker_region((1, 2), 0, (3, 4), biomarker="DAPI") == (
        (1, 2),
        0,
        (3, 4),
        "DAPI",
    )


def test_slide_treats_he_qptiff_as_brightfield(
    monkeypatch, fake_he_qptiff_backend
) -> None:
    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="qptiff",
            extensions=(".qptiff",),
            slide_backend=fake_he_qptiff_backend,
            slide_family="qptiff",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("paired_he.qptiff")

    assert slide.slide_family == "brightfield"
    assert slide.read_region((1, 2), 0, (3, 4)) == ((1, 2), 0, (3, 4), "HE")

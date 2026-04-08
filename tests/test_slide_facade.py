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
    assert slide.qptiff_semantics == "brightfield"
    assert slide.read_region((1, 2), 0, (3, 4)) == ((1, 2), 0, (3, 4), "HE")


def test_slide_exposes_qptiff_semantics_for_multiplex_qptiff(
    monkeypatch, fake_multiplex_backend
) -> None:
    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="qptiff",
            extensions=(".qptiff",),
            slide_backend=fake_multiplex_backend,
            slide_family="qptiff",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.qptiff")

    assert slide.slide_family == "multiplex"
    assert slide.qptiff_semantics == "multiplex"


def test_slide_treats_ome_tiff_as_multiplex_and_exposes_biomarkers(
    monkeypatch, fake_ome_multiplex_backend
) -> None:
    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="ome_tiff",
            extensions=(".tif", ".tiff"),
            slide_backend=fake_ome_multiplex_backend,
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("roi/141Pr_141Pr_SMA.ome.tiff")

    assert slide.slide_family == "multiplex"
    assert slide.list_biomarkers() == ["SMA", "CD3", "DAPI"]


def test_slide_keeps_generic_tiff_as_brightfield_single_image(
    monkeypatch, fake_generic_tiff_backend
) -> None:
    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="openslide",
            extensions=(".tif", ".tiff"),
            slide_backend=fake_generic_tiff_backend,
            slide_family="brightfield",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("tiles/reg001_X01_Y01.tif")

    assert slide.slide_family == "brightfield"
    assert slide.read_region((0, 0), 0, (16, 16)) == ((0, 0), 0, (16, 16))


def test_slide_treats_mcd_as_multiplex(monkeypatch, fake_mcd_backend) -> None:
    import pytest

    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="mcd",
            extensions=(".mcd",),
            slide_backend=fake_mcd_backend,
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("COVID_SAMPLE_6.mcd")

    assert slide.slide_family == "multiplex"
    assert slide.list_biomarkers() == ["DNA1", "CD3", "CD20"]
    with pytest.raises(Exception, match="biomarker|multiplex|channel"):
        slide.read_region((0, 0), 0, (8, 8))


def test_mcd_backend_prefers_largest_acquisition_and_exposes_metadata(
    monkeypatch,
) -> None:
    from Aslide.mcd.mcd_slide import McdSlide

    class FakeAcquisition:
        def __init__(self, acq_id, description, width, height):
            self.id = acq_id
            self.description = description
            self.width_px = width
            self.height_px = height
            self.width_um = float(width)
            self.height_um = float(height)
            self.pixel_size_x_um = 1.0
            self.pixel_size_y_um = 1.0
            self.channel_names = ["Pr141", "Ir191"]
            self.channel_labels = ["aSMA", "DNA1"]
            self.channel_metals = ["Pr", "Ir"]
            self.channel_masses = [141, 191]

    class FakeSlide:
        def __init__(self):
            self.acquisitions = [
                FakeAcquisition(1, "ROI_small", 100, 100),
                FakeAcquisition(2, "ROI_large", 300, 200),
            ]

    class FakeMCDFile:
        def __init__(self, path):
            self.path = path
            self.slides = [FakeSlide()]

        def open(self):
            return None

        def close(self):
            return None

        def read_acquisition(self, acquisition):
            import numpy as np

            return np.ones(
                (2, acquisition.height_px, acquisition.width_px), dtype=np.float32
            )

    monkeypatch.setattr("Aslide.mcd.mcd_slide._MCDFile", FakeMCDFile)

    slide = McdSlide("demo.mcd")

    assert slide.dimensions == (300, 200)
    assert slide.properties["mcd.selected-acquisition-id"] == "2"
    assert slide.properties["mcd.selected-acquisition-description"] == "ROI_large"
    assert slide.list_biomarkers() == ["aSMA", "DNA1"]


def test_slide_passes_acquisition_id_to_mcd_backend(monkeypatch) -> None:
    from Aslide.aslide import Slide
    from Aslide.registry import FormatEntry

    class RecordingMcdBackend:
        def __init__(self, path: str, acquisition_id: int | None = None):
            self.path = path
            self.acquisition_id = acquisition_id
            self.level_count = 1
            self.dimensions = (300, 200)
            self.level_dimensions = ((300, 200),)
            self.level_downsamples = (1.0,)
            self.properties = {"mcd.selected-acquisition-id": str(acquisition_id)}
            self.associated_images = {}

        def close(self) -> None:
            return None

        def get_best_level_for_downsample(self, downsample: float) -> int:
            return 0

        def list_biomarkers(self) -> list[str]:
            return ["aSMA"]

        def get_default_display_biomarker(self) -> str:
            return "aSMA"

        def read_biomarker_region(self, location, level, size, biomarker):
            return (location, level, size, biomarker)

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="mcd",
            extensions=(".mcd",),
            slide_backend=RecordingMcdBackend,
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.mcd", acquisition_id=3)

    assert slide.backend.acquisition_id == 3
    assert slide.properties["mcd.selected-acquisition-id"] == "3"

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


def test_deepzoom_preserves_brightfield_construction(
    monkeypatch, fake_backend_classes
) -> None:
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
            slide_family="brightfield",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.fake")
    deepzoom = DeepZoom(slide)

    assert deepzoom.backend.__class__ is fake_deepzoom_backend
    assert getattr(deepzoom.backend, "biomarker", None) is None


def test_deepzoom_passes_explicit_biomarker_for_multiplex_slides(
    monkeypatch, fake_multiplex_backend, fake_multiplex_deepzoom_backend
) -> None:
    from Aslide.aslide import Slide
    from Aslide.deepzoom import DeepZoom
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="qptiff",
            extensions=(".qptiff",),
            slide_backend=fake_multiplex_backend,
            deepzoom_backend=fake_multiplex_deepzoom_backend,
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.qptiff")
    deepzoom = DeepZoom(slide, biomarker="CD3")

    assert deepzoom.backend.biomarker == "CD3"


def test_deepzoom_uses_biomarker_aware_ome_tiff_backend(
    monkeypatch,
) -> None:
    from PIL import Image

    from Aslide.aslide import Slide
    from Aslide.deepzoom import DeepZoom
    from Aslide.registry import FormatEntry

    class RecordingOmeBackend:
        def __init__(self, path: str):
            self.path = path
            self.format_id = "ome_tiff"
            self.dimensions = (1024, 1024)
            self.level_count = 1
            self.level_dimensions = ((1024, 1024),)
            self.level_downsamples = (1.0,)
            self.properties = {
                "openslide.vendor": "ome-tiff",
                "ome.channels": "CD3,DAPI",
            }
            self.associated_images = {}
            self.requested_biomarkers: list[str] = []

        def close(self) -> None:
            return None

        def get_best_level_for_downsample(self, downsample: float) -> int:
            return 0

        def list_biomarkers(self) -> list[str]:
            return ["CD3", "DAPI"]

        def has_biomarker(self, name: str) -> bool:
            return name in {"CD3", "DAPI"}

        def get_default_display_biomarker(self) -> str:
            return "DAPI"

        def read_biomarker_region(self, location, level, size, biomarker):
            self.requested_biomarkers.append(biomarker)
            return Image.new("RGBA", size, (1, 2, 3, 255))

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="ome_tiff",
            extensions=(".tif", ".tiff"),
            slide_backend=RecordingOmeBackend,
            deepzoom_backend=lambda: (
                __import__(
                    "Aslide.ome_tiff.ome_tiff_deepzoom",
                    fromlist=["OmeTiffDeepZoomGenerator"],
                ).OmeTiffDeepZoomGenerator
            ),
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.ome.tif")
    deepzoom = DeepZoom(slide, biomarker="CD3")

    assert deepzoom.biomarker == "CD3"
    tile = deepzoom.get_tile(0, (0, 0))
    assert tile.size[0] > 0 and tile.size[1] > 0
    assert slide.backend.requested_biomarkers == ["CD3"]


def test_deepzoom_defaults_to_dapi_for_multiplex_slides(
    monkeypatch, fake_multiplex_backend, fake_multiplex_deepzoom_backend
) -> None:
    from Aslide.aslide import Slide
    from Aslide.deepzoom import DeepZoom
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="qptiff",
            extensions=(".qptiff",),
            slide_backend=fake_multiplex_backend,
            deepzoom_backend=fake_multiplex_deepzoom_backend,
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.qptiff")
    deepzoom = DeepZoom(slide)

    assert deepzoom.backend.biomarker == "DAPI"
    assert deepzoom.biomarker == "DAPI"


def test_deepzoom_exposes_selected_biomarker_for_multiplex_slides(
    monkeypatch, fake_multiplex_backend, fake_multiplex_deepzoom_backend
) -> None:
    from Aslide.aslide import Slide
    from Aslide.deepzoom import DeepZoom
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="qptiff",
            extensions=(".qptiff",),
            slide_backend=fake_multiplex_backend,
            deepzoom_backend=fake_multiplex_deepzoom_backend,
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.qptiff")
    deepzoom = DeepZoom(slide, biomarker="CD3")

    assert deepzoom.biomarker == "CD3"


def test_deepzoom_falls_back_when_backend_does_not_accept_biomarker(
    monkeypatch, fake_multiplex_backend, fake_backend_classes
) -> None:
    from Aslide.aslide import Slide
    from Aslide.deepzoom import DeepZoom
    from Aslide.registry import FormatEntry

    _, fake_deepzoom_backend = fake_backend_classes

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="ome_tiff",
            extensions=(".tif",),
            slide_backend=fake_multiplex_backend,
            deepzoom_backend=fake_deepzoom_backend,
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.ome.tif")
    deepzoom = DeepZoom(slide)

    assert deepzoom.backend.__class__ is fake_deepzoom_backend


def test_deepzoom_raises_when_default_dapi_missing_for_multiplex_slides(
    monkeypatch, fake_multiplex_deepzoom_backend
) -> None:
    import pytest

    from Aslide.aslide import Slide
    from Aslide.deepzoom import DeepZoom
    from Aslide.registry import FormatEntry

    class NoDapiMultiplexBackend:
        def __init__(self, path: str):
            self.path = path
            self.format_id = "fake-multiplex"
            self.dimensions = (100, 50)
            self.level_count = 1
            self.level_dimensions = ((100, 50),)
            self.level_downsamples = (1.0,)
            self.properties = {"vendor": "fake-multiplex"}
            self.associated_images = {}
            self.biomarkers = ("CD3", "CD20")

        def close(self) -> None:
            return None

        def get_best_level_for_downsample(self, downsample: float) -> int:
            return 0

        def list_biomarkers(self) -> list[str]:
            return list(self.biomarkers)

        def get_biomarkers(self) -> list[str]:
            return self.list_biomarkers()

        def has_biomarker(self, name: str) -> bool:
            return name in self.biomarkers

        def get_default_display_biomarker(self) -> str:
            raise ValueError("DAPI not available")

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="qptiff",
            extensions=(".qptiff",),
            slide_backend=NoDapiMultiplexBackend,
            deepzoom_backend=fake_multiplex_deepzoom_backend,
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.qptiff")

    with pytest.raises(Exception, match="DAPI"):
        DeepZoom(slide)


def test_deepzoom_passes_biomarker_for_hdf5_family_multiplex_slides(
    monkeypatch, fake_multiplex_backend, fake_multiplex_deepzoom_backend
) -> None:
    from Aslide.aslide import Slide
    from Aslide.deepzoom import DeepZoom
    from Aslide.registry import FormatEntry

    def fake_resolve_path(path: str) -> FormatEntry:
        return FormatEntry(
            format_id="hdf5",
            extensions=(".h5", ".hdf5", ".h5ad"),
            slide_backend=fake_multiplex_backend,
            deepzoom_backend=fake_multiplex_deepzoom_backend,
            slide_family="multiplex",
        )

    monkeypatch.setattr("Aslide.aslide.registry.resolve_path", fake_resolve_path)

    slide = Slide("demo.h5ad")
    deepzoom = DeepZoom(slide, biomarker="CD3")

    assert deepzoom.backend.biomarker == "CD3"
    assert deepzoom.biomarker == "CD3"

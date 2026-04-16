from __future__ import annotations

from pathlib import Path
import sys
from dataclasses import dataclass, field
from collections.abc import Iterator, Mapping
from typing import Any

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class FakeSlideBackend:
    path: str
    format_id: str = "fake"
    dimensions: tuple[int, int] = (100, 50)
    level_count: int = 1
    level_dimensions: tuple[tuple[int, int], ...] = ((100, 50),)
    level_downsamples: tuple[float, ...] = (1.0,)
    properties: dict[str, str] = field(default_factory=lambda: {"vendor": "fake"})
    associated_images: Mapping[str, Any] = field(default_factory=dict)
    mpp: float = 0.25
    magnification: float = 40.0
    closed: bool = False

    def close(self) -> None:
        self.closed = True

    def get_best_level_for_downsample(self, downsample: float) -> int:
        return 0

    def get_thumbnail(self, size: tuple[int, int]) -> tuple[str, tuple[int, int]]:
        return ("thumbnail", size)

    def read_region(
        self,
        location: tuple[int, int],
        level: int,
        size: tuple[int, int],
    ) -> tuple[tuple[int, int], int, tuple[int, int]]:
        return (location, level, size)

    def label_image(self) -> str:
        return "label-image"


class FakeDeepZoomBackend:
    def __init__(
        self,
        slide: Any,
        tile_size: int = 254,
        overlap: int = 1,
        limit_bounds: bool = False,
    ) -> None:
        self.slide = slide
        self.tile_size = tile_size
        self.overlap = overlap
        self.limit_bounds = limit_bounds
        self.level_count = 4
        self.level_tiles = ((1, 1), (2, 2), (4, 4), (8, 8))
        self.level_dimensions = ((16, 16), (32, 32), (64, 64), (128, 128))
        self.tile_count = 85

    def get_dzi(self, image_format: str) -> str:
        return f"dzi:{image_format}"

    def get_tile(
        self, level: int, address: tuple[int, int]
    ) -> tuple[int, tuple[int, int]]:
        return (level, address)


class FakeMultiplexDeepZoomBackend(FakeDeepZoomBackend):
    def __init__(
        self,
        slide: Any,
        tile_size: int = 254,
        overlap: int = 1,
        limit_bounds: bool = False,
        biomarker: str | None = None,
    ) -> None:
        super().__init__(slide, tile_size, overlap, limit_bounds)
        self.biomarker = biomarker


@pytest.fixture
def fake_backend_classes() -> tuple[type[FakeSlideBackend], type[FakeDeepZoomBackend]]:
    return FakeSlideBackend, FakeDeepZoomBackend


@dataclass
class FakeAssociatedImagesBackend(FakeSlideBackend):
    associated_images: Mapping[str, Any] = field(
        default_factory=lambda: {"label": "label-image", "macro": "macro-image"}
    )

    def get_thumbnail(self, size: tuple[int, int]) -> tuple[str, tuple[int, int]]:
        return ("generated-thumbnail", size)


@pytest.fixture
def fake_associated_images_backend() -> type[FakeAssociatedImagesBackend]:
    return FakeAssociatedImagesBackend


class LazyAssociatedImagesMap(Mapping[str, Any]):
    def __init__(self) -> None:
        self.accessed_keys: list[str] = []

    def __iter__(self) -> Iterator[str]:
        yield "label"
        yield "macro"

    def __len__(self) -> int:
        return 2

    def __getitem__(self, key: str) -> Any:
        self.accessed_keys.append(key)
        if key == "label":
            return "label-image"
        if key == "macro":
            return "macro-image"
        raise KeyError(key)

    def keys(self):
        return {"label": None, "macro": None}.keys()

    def items(self):
        raise AssertionError(
            "lazy associated images should not be eagerly materialized"
        )


@dataclass
class FakeLazyAssociatedImagesBackend(FakeSlideBackend):
    associated_images: Mapping[str, Any] = field(
        default_factory=LazyAssociatedImagesMap
    )

    def get_thumbnail(self, size: tuple[int, int]) -> tuple[str, tuple[int, int]]:
        return ("generated-thumbnail", size)


@pytest.fixture
def fake_lazy_associated_images_backend() -> type[FakeLazyAssociatedImagesBackend]:
    return FakeLazyAssociatedImagesBackend


@dataclass
class FakeMultiplexBackend:
    path: str
    format_id: str = "fake-multiplex"
    dimensions: tuple[int, int] = (100, 50)
    level_count: int = 1
    level_dimensions: tuple[tuple[int, int], ...] = ((100, 50),)
    level_downsamples: tuple[float, ...] = (1.0,)
    properties: dict[str, str] = field(
        default_factory=lambda: {"vendor": "fake-multiplex"}
    )
    associated_images: dict[str, Any] = field(default_factory=dict)
    biomarkers: tuple[str, ...] = ("DAPI", "CD3")
    closed: bool = False

    def close(self) -> None:
        self.closed = True

    def get_best_level_for_downsample(self, downsample: float) -> int:
        return 0

    def list_biomarkers(self) -> list[str]:
        return list(self.biomarkers)

    def get_biomarkers(self) -> list[str]:
        return self.list_biomarkers()

    def has_biomarker(self, name: str) -> bool:
        return name in self.biomarkers

    def get_default_display_biomarker(self) -> str:
        if "DAPI" not in self.biomarkers:
            raise ValueError("DAPI not available")
        return "DAPI"

    def read_biomarker_region(
        self,
        location: tuple[int, int],
        level: int,
        size: tuple[int, int],
        biomarker: str,
    ) -> tuple[tuple[int, int], int, tuple[int, int], str]:
        if biomarker not in self.biomarkers:
            raise ValueError(f"Unknown biomarker: {biomarker}")
        return (location, level, size, biomarker)


@pytest.fixture
def fake_multiplex_backend() -> type[FakeMultiplexBackend]:
    return FakeMultiplexBackend


@pytest.fixture
def fake_multiplex_deepzoom_backend() -> type[FakeMultiplexDeepZoomBackend]:
    return FakeMultiplexDeepZoomBackend


@dataclass
class FakeOmeMultiplexBackend(FakeMultiplexBackend):
    format_id: str = "fake-ome"
    biomarkers: tuple[str, ...] = ("SMA", "CD3", "DAPI")
    sibling_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.sibling_paths = (
            "/tmp/141Pr_141Pr_SMA.ome.tiff",
            "/tmp/170Er_170Er_CD3.ome.tiff",
            "/tmp/171Yb_171Yb_Histone3.ome.tiff",
        )


@pytest.fixture
def fake_ome_multiplex_backend() -> type[FakeOmeMultiplexBackend]:
    return FakeOmeMultiplexBackend


@dataclass
class FakeGenericTiffBackend(FakeSlideBackend):
    format_id: str = "generic-tiff"
    properties: dict[str, str] = field(
        default_factory=lambda: {"openslide.vendor": "OpenSlide", "format": "tiff"}
    )


@pytest.fixture
def fake_generic_tiff_backend() -> type[FakeGenericTiffBackend]:
    return FakeGenericTiffBackend


@dataclass
class FakeMcdBackend(FakeMultiplexBackend):
    format_id: str = "mcd"
    biomarkers: tuple[str, ...] = ("DNA1", "CD3", "CD20")


@pytest.fixture
def fake_mcd_backend() -> type[FakeMcdBackend]:
    return FakeMcdBackend


@dataclass
class FakeHeQptiffBackend:
    path: str
    format_id: str = "qptiff"
    dimensions: tuple[int, int] = (120, 80)
    level_count: int = 1
    level_dimensions: tuple[tuple[int, int], ...] = ((120, 80),)
    level_downsamples: tuple[float, ...] = (1.0,)
    properties: dict[str, str] = field(
        default_factory=lambda: {"qptiff.biomarkers": "H&E", "vendor": "fake-he-qptiff"}
    )
    associated_images: Mapping[str, Any] = field(default_factory=dict)
    biomarkers: tuple[str, ...] = ("H&E",)
    slide_family: str = "brightfield"

    def close(self) -> None:
        return None

    def get_best_level_for_downsample(self, downsample: float) -> int:
        return 0

    def list_biomarkers(self) -> list[str]:
        return list(self.biomarkers)

    def get_biomarkers(self) -> list[str]:
        return self.list_biomarkers()

    def read_region(
        self, location: tuple[int, int], level: int, size: tuple[int, int]
    ) -> tuple[tuple[int, int], int, tuple[int, int], str]:
        return (location, level, size, "HE")

    def get_thumbnail(self, size: tuple[int, int]) -> tuple[str, tuple[int, int]]:
        return ("he-thumbnail", size)


@pytest.fixture
def fake_he_qptiff_backend() -> type[FakeHeQptiffBackend]:
    return FakeHeQptiffBackend


@dataclass
class FakeCziBackend(FakeSlideBackend):
    format_id: str = "czi"
    properties: dict[str, str] = field(
        default_factory=lambda: {"vendor": "fake-czi", "format": "czi"}
    )
    slide_family: str = "czi"

    def classify_slide_family(self) -> str:
        return "multiplex"


@pytest.fixture
def fake_czi_backend() -> type[FakeCziBackend]:
    return FakeCziBackend

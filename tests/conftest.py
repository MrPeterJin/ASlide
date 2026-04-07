from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Iterator, Mapping
from typing import Any

import pytest


@dataclass
class FakeSlideBackend:
    path: str
    format_id: str = "fake"
    dimensions: tuple[int, int] = (100, 50)
    level_count: int = 1
    level_dimensions: tuple[tuple[int, int], ...] = ((100, 50),)
    level_downsamples: tuple[float, ...] = (1.0,)
    properties: dict[str, str] = field(default_factory=lambda: {"vendor": "fake"})
    associated_images: dict[str, Any] = field(default_factory=dict)
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


@pytest.fixture
def fake_backend_classes() -> tuple[type[FakeSlideBackend], type[FakeDeepZoomBackend]]:
    return FakeSlideBackend, FakeDeepZoomBackend


@dataclass
class FakeAssociatedImagesBackend(FakeSlideBackend):
    associated_images: dict[str, Any] = field(
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
        return ["label", "macro"]

    def items(self):
        raise AssertionError(
            "lazy associated images should not be eagerly materialized"
        )


@dataclass
class FakeLazyAssociatedImagesBackend(FakeSlideBackend):
    associated_images: LazyAssociatedImagesMap = field(
        default_factory=LazyAssociatedImagesMap
    )

    def get_thumbnail(self, size: tuple[int, int]) -> tuple[str, tuple[int, int]]:
        return ("generated-thumbnail", size)


@pytest.fixture
def fake_lazy_associated_images_backend() -> type[FakeLazyAssociatedImagesBackend]:
    return FakeLazyAssociatedImagesBackend

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PIL import Image
from openslide import AbstractSlide
import tifffile


class GenericTiffSlide(AbstractSlide):
    @classmethod
    def detect_format(cls, filename: Any) -> str | None:
        with tifffile.TiffFile(filename) as tiff:
            if tiff.is_ome:
                return None
        return "generic_tiff"

    def __init__(self, filename: str):
        AbstractSlide.__init__(self)
        self._filename = filename
        self._path = Path(filename)
        with tifffile.TiffFile(filename) as tiff:
            self._series = tiff.series[0]
            self._shape = tuple(int(value) for value in self._series.shape)
            self._dtype = tiff.pages[0].dtype
            self._description = str(getattr(tiff.pages[0], "description", "") or "")

    @property
    def level_count(self) -> int:
        return 1

    @property
    def dimensions(self) -> tuple[int, int]:
        return (self._shape[-1], self._shape[-2])

    @property
    def level_dimensions(self) -> tuple[tuple[int, int], ...]:
        return (self.dimensions,)

    @property
    def level_downsamples(self) -> tuple[float, ...]:
        return (1.0,)

    @property
    def properties(self) -> dict[str, str]:
        return {
            "openslide.vendor": "tifffile",
            "tiff.axes": self._series.axes,
            "tiff.description": self._description,
        }

    @property
    def associated_images(self) -> dict[str, Image.Image]:
        return {}

    def close(self) -> None:
        return None

    def get_best_level_for_downsample(self, downsample: float) -> int:
        return 0

    def read_region(
        self, location: tuple[int, int], level: int, size: tuple[int, int]
    ) -> Image.Image:
        if level != 0:
            raise ValueError("Generic TIFF backend currently supports only level 0")
        x, y = location
        width, height = size
        with tifffile.TiffFile(str(self._path)) as tiff:
            data = np.asarray(tiff.asarray())
        plane = _first_plane_2d(data)
        region = plane[y : y + height, x : x + width]
        if region.size == 0:
            region = np.zeros((height, width), dtype=np.uint8)
        if region.dtype != np.uint8:
            region = _normalize_to_uint8(region)
        rgba = np.stack([region, region, region, np.full_like(region, 255)], axis=-1)
        return Image.fromarray(rgba, mode="RGBA")

    def get_thumbnail(self, size: tuple[int, int]) -> Image.Image:
        image = self.read_region((0, 0), 0, self.dimensions)
        image.thumbnail(size)
        return image


def _first_plane_2d(data: NDArray[Any]) -> NDArray[Any]:
    plane = np.asarray(data)
    while plane.ndim > 2:
        plane = plane[0]
    return plane


def _normalize_to_uint8(data: NDArray[Any]) -> NDArray[np.uint8]:
    data = np.asarray(data)
    minimum = float(data.min())
    maximum = float(data.max())
    if maximum <= minimum:
        return np.zeros(data.shape, dtype=np.uint8)
    scaled = (data - minimum) / (maximum - minimum)
    return (scaled * 255).astype(np.uint8)

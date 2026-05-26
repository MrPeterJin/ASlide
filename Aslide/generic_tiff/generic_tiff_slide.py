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
            self._axes = self._series.axes
            self._dtype = tiff.pages[0].dtype
            self._description = str(getattr(tiff.pages[0], "description", "") or "")
            self._mpp = _extract_tiff_mpp(tiff.pages[0])

    @property
    def level_count(self) -> int:
        return 1

    @property
    def dimensions(self) -> tuple[int, int]:
        return _dimensions_from_axes(self._shape, self._axes)

    @property
    def level_dimensions(self) -> tuple[tuple[int, int], ...]:
        return (self.dimensions,)

    @property
    def level_downsamples(self) -> tuple[float, ...]:
        return (1.0,)

    @property
    def properties(self) -> dict[str, str]:
        props = {
            "openslide.vendor": "tifffile",
            "tiff.axes": self._axes,
            "tiff.description": self._description,
        }
        if self._mpp is not None:
            mpp_x, mpp_y = self._mpp
            props["openslide.mpp-x"] = str(mpp_x)
            props["openslide.mpp-y"] = str(mpp_y)
        return props

    @property
    def mpp(self) -> float | None:
        if self._mpp is None:
            return None
        mpp_x, mpp_y = self._mpp
        return (mpp_x + mpp_y) / 2

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
        image = _as_displayable_image(data, self._axes)
        region = image[y : y + height, x : x + width]
        if region.size == 0:
            return Image.new("RGBA", (width, height))
        if region.ndim == 2:
            if region.dtype != np.uint8:
                region = _normalize_to_uint8(region)
            rgba = np.stack(
                [region, region, region, np.full_like(region, 255)], axis=-1
            )
            return Image.fromarray(rgba, mode="RGBA")
        if region.dtype != np.uint8:
            region = _normalize_to_uint8(region)
        if region.shape[-1] == 3:
            alpha = np.full(region.shape[:2] + (1,), 255, dtype=np.uint8)
            region = np.concatenate([region, alpha], axis=-1)
        return Image.fromarray(region, mode="RGBA")

    def get_thumbnail(self, size: tuple[int, int]) -> Image.Image:
        image = self.read_region((0, 0), 0, self.dimensions)
        image.thumbnail(size)
        return image


def _dimensions_from_axes(shape: tuple[int, ...], axes: str) -> tuple[int, int]:
    if "X" in axes and "Y" in axes:
        return (shape[axes.index("X")], shape[axes.index("Y")])
    return (shape[-1], shape[-2])


def _as_displayable_image(data: NDArray[Any], axes: str) -> NDArray[Any]:
    array = np.asarray(data)
    if array.ndim == 2:
        return array
    if axes.endswith("YXS") and array.ndim == 3:
        return array
    while array.ndim > 3:
        array = array[0]
    if array.ndim == 3 and array.shape[0] in {3, 4} and "Y" in axes and "X" in axes:
        array = np.moveaxis(array, 0, -1)
    elif array.ndim == 3 and array.shape[-1] not in {3, 4}:
        array = array[..., 0]
    return array


def _normalize_to_uint8(data: NDArray[Any]) -> NDArray[np.uint8]:
    data = np.asarray(data)
    minimum = float(data.min())
    maximum = float(data.max())
    if maximum <= minimum:
        return np.zeros(data.shape, dtype=np.uint8)
    scaled = (data - minimum) / (maximum - minimum)
    return (scaled * 255).astype(np.uint8)


def _extract_tiff_mpp(page: Any) -> tuple[float, float] | None:
    x_resolution = _resolution_value(page.tags.get("XResolution"))
    y_resolution = _resolution_value(page.tags.get("YResolution"))
    if not x_resolution or not y_resolution:
        return None

    unit_tag = page.tags.get("ResolutionUnit")
    unit = int(unit_tag.value) if unit_tag is not None else 2
    if unit == 2:  # inch
        microns_per_unit = 25400.0
    elif unit == 3:  # centimeter
        microns_per_unit = 10000.0
    else:
        return None

    return (microns_per_unit / x_resolution, microns_per_unit / y_resolution)


def _resolution_value(tag: Any) -> float | None:
    if tag is None:
        return None
    value = tag.value
    if isinstance(value, tuple) and len(value) == 2:
        numerator, denominator = value
        if denominator == 0:
            return None
        return float(numerator) / float(denominator)
    return float(value)

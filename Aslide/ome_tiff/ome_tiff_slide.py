from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image
from openslide import AbstractSlide
import tifffile

from ..errors import (
    MissingDefaultBiomarkerError,
    UnknownBiomarkerError,
    UnsupportedOperationError,
)
from .probe import is_ome_tiff_candidate


class OmeTiffSlide(AbstractSlide):
    @classmethod
    def detect_format(cls, filename: str) -> str | None:
        if is_ome_tiff_candidate(filename):
            return "ome_tiff"
        return None

    def __init__(self, filename: str):
        AbstractSlide.__init__(self)
        self._filename = filename
        self._channels: dict[str, Path] = {}
        self._channel_order: list[str] = []
        self._channel_indices: dict[str, int] = {}
        self._shape: tuple[int, int] = (0, 0)
        self._dtype = None
        self._mpp = None
        self._single_file_path: Path | None = None
        self._single_file_axes: str | None = None
        self._discover_channels(Path(filename))

    def _discover_channels(self, anchor_path: Path) -> None:
        if not is_ome_tiff_candidate(str(anchor_path)):
            raise ValueError(
                f"Not an OME-compatible TIFF multiplex anchor: {anchor_path}"
            )

        anchor_signature = self._read_signature(anchor_path)
        self._shape = anchor_signature["shape"]
        self._dtype = anchor_signature["dtype"]
        self._mpp = anchor_signature["mpp"]

        if anchor_signature["ome_channels"]:
            self._single_file_path = anchor_path
            self._single_file_axes = anchor_signature["axes"]
            for index, label in enumerate(anchor_signature["ome_channels"]):
                self._channels[label] = anchor_path
                self._channel_order.append(label)
                self._channel_indices[label] = index
            return

        for candidate in sorted(anchor_path.parent.iterdir()):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in {".tif", ".tiff"}:
                continue
            if not is_ome_tiff_candidate(str(candidate)):
                continue
            try:
                signature = self._read_signature(candidate)
            except Exception:
                continue
            if signature["shape"] != self._shape or signature["dtype"] != self._dtype:
                continue
            label = signature["label"]
            if label in self._channels:
                continue
            self._channels[label] = candidate
            self._channel_order.append(label)

        if not self._channel_order:
            raise ValueError(f"No readable channels discovered for {anchor_path}")

    def _read_signature(self, path: Path) -> dict[str, Any]:
        with tifffile.TiffFile(path) as tiff:
            series = tiff.series[0]
            page = tiff.pages[0]
            page_name = page.tags.get("PageName")
            x_resolution = page.tags.get("XResolution")
            ome_channels = _extract_ome_channel_names(tiff.ome_metadata)
            mpp = None
            if x_resolution is not None:
                num, den = x_resolution.value
                if num:
                    mpp = 25400.0 * den / num
            return {
                "shape": tuple(int(value) for value in series.shape[-2:]),
                "axes": series.axes,
                "dtype": page.dtype,
                "label": str(page_name.value) if page_name else path.stem,
                "mpp": mpp,
                "ome_channels": ome_channels,
            }

    @property
    def level_count(self) -> int:
        return 1

    @property
    def dimensions(self) -> tuple[int, int]:
        return (self._shape[1], self._shape[0])

    @property
    def level_dimensions(self) -> tuple[tuple[int, int], ...]:
        return (self.dimensions,)

    @property
    def level_downsamples(self) -> tuple[float, ...]:
        return (1.0,)

    @property
    def properties(self) -> dict[str, str]:
        properties = {
            "openslide.vendor": "ome-tiff",
            "ome.channel-count": str(len(self._channel_order)),
            "ome.channels": ",".join(self._channel_order),
        }
        if self._mpp is not None:
            properties["openslide.mpp-x"] = str(self._mpp)
            properties["openslide.mpp-y"] = str(self._mpp)
        return properties

    @property
    def associated_images(self) -> dict[str, Image.Image]:
        return {}

    def close(self) -> None:
        return None

    def get_best_level_for_downsample(self, downsample: float) -> int:
        return 0

    def list_biomarkers(self) -> list[str]:
        return list(self._channel_order)

    def read_region(
        self, location: tuple[int, int], level: int, size: tuple[int, int]
    ) -> Image.Image:
        raise UnsupportedOperationError(
            "OME-TIFF multiplex slides require an explicit biomarker; use read_biomarker_region()"
        )

    def has_biomarker(self, name: str) -> bool:
        return name in self._channels

    def get_default_display_biomarker(self) -> str:
        for biomarker in self._channel_order:
            upper = biomarker.upper()
            if "DAPI" in upper or "HISTONE" in upper:
                return biomarker
        if self._channel_order:
            return self._channel_order[0]
        raise MissingDefaultBiomarkerError("No biomarker available for display")

    def read_biomarker_region(
        self,
        location: tuple[int, int],
        level: int,
        size: tuple[int, int],
        biomarker: str,
    ) -> Image.Image:
        if level != 0:
            raise ValueError(
                "OME-TIFF multiplex backend currently supports only level 0"
            )
        if biomarker not in self._channels:
            raise UnknownBiomarkerError(f"Biomarker '{biomarker}' not found")

        x, y = location
        width, height = size
        with tifffile.TiffFile(self._channels[biomarker]) as tiff:
            data = tiff.asarray()
        if self._single_file_path is not None and self._single_file_axes is not None:
            channel_index = self._channel_indices[biomarker]
            plane = _extract_channel_plane(
                np.asarray(data), self._single_file_axes, channel_index
            )
        else:
            plane = np.asarray(data)
        region = np.asarray(plane[y : y + height, x : x + width])
        if region.size == 0:
            region = np.zeros((height, width), dtype=np.uint8)
        if region.dtype != np.uint8:
            region = _normalize_to_uint8(region)
        rgba = np.stack([region, region, region, np.full_like(region, 255)], axis=-1)
        return Image.fromarray(rgba, mode="RGBA")


def _normalize_to_uint8(data: np.ndarray) -> np.ndarray:
    data = np.asarray(data)
    if data.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    minimum = float(data.min())
    maximum = float(data.max())
    if maximum <= minimum:
        return np.zeros(data.shape, dtype=np.uint8)
    scaled = (data - minimum) / (maximum - minimum)
    return (scaled * 255).astype(np.uint8)


def _extract_ome_channel_names(ome_metadata: str | None) -> list[str]:
    if not ome_metadata:
        return []
    root = ET.fromstring(ome_metadata)
    ns = {"ome": "http://www.openmicroscopy.org/Schemas/OME/2016-06"}
    channels = root.findall(".//ome:Channel", ns)
    names: list[str] = []
    for index, channel in enumerate(channels):
        names.append(channel.attrib.get("Name") or f"Channel {index}")
    return names


def _extract_channel_plane(
    data: np.ndarray, axes: str, channel_index: int
) -> np.ndarray:
    array = np.asarray(data)
    if axes == "CYX":
        return array[channel_index]
    if axes == "YX":
        return array
    if "C" in axes:
        axis = axes.index("C")
        return np.take(array, channel_index, axis=axis)
    return array

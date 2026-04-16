from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .adapter import CziAdapter
from ..errors import UnsupportedOperationError


class _CziSlideAdapter(Protocol):
    @property
    def dimensions(self) -> tuple[int, int]: ...

    @property
    def level_count(self) -> int: ...

    @property
    def level_dimensions(self) -> tuple[tuple[int, int], ...]: ...

    @property
    def level_downsamples(self) -> tuple[float, ...]: ...

    @property
    def properties(self) -> dict[str, str]: ...

    def classify_slide_family(self) -> str: ...

    def read_region(
        self,
        location: tuple[int, int],
        level: int,
        size: tuple[int, int],
    ) -> Any: ...

    def get_thumbnail(self, size: tuple[int, int]) -> Any: ...

    def list_biomarkers(self) -> list[str]: ...

    def get_default_display_biomarker(self) -> str: ...

    def read_biomarker_region(
        self,
        location: tuple[int, int],
        level: int,
        size: tuple[int, int],
        biomarker: str,
    ) -> Any: ...

    def get_best_level_for_downsample(self, downsample: float) -> int: ...

    def close(self) -> None: ...


class CziSlide:
    def __init__(self, filename: str, adapter: _CziSlideAdapter | None = None):
        self.filename = filename
        if adapter is None:
            try:
                adapter = CziAdapter.from_bioformats(filename)
            except ImportError as exc:
                raise ImportError(
                    "CZI adapter dependency is not configured; Bio-Formats backend is unavailable"
                ) from exc
        self._adapter = adapter
        self._slide_family = self._adapter.classify_slide_family()

    @property
    def slide_family(self) -> str:
        return self._slide_family

    def classify_slide_family(self) -> str:
        return self._adapter.classify_slide_family()

    @property
    def dimensions(self) -> tuple[int, int]:
        return self._adapter.dimensions

    @property
    def level_count(self) -> int:
        return self._adapter.level_count

    @property
    def level_dimensions(self) -> tuple[tuple[int, int], ...]:
        return self._adapter.level_dimensions

    @property
    def level_downsamples(self) -> tuple[float, ...]:
        return self._adapter.level_downsamples

    @property
    def properties(self) -> Mapping[str, Any]:
        return self._adapter.properties

    def get_best_level_for_downsample(self, downsample: float) -> int:
        return self._adapter.get_best_level_for_downsample(downsample)

    def read_region(
        self, location: tuple[int, int], level: int, size: tuple[int, int]
    ) -> Any:
        if self.slide_family != "brightfield":
            raise UnsupportedOperationError(
                "CZI multiplex slides require an explicit biomarker"
            )
        return self._adapter.read_region(location, level, size)

    def get_thumbnail(self, size: tuple[int, int]) -> Any:
        if self.slide_family != "brightfield":
            raise UnsupportedOperationError(
                "CZI multiplex slides do not support generic thumbnails"
            )
        return self._adapter.get_thumbnail(size)

    def list_biomarkers(self) -> list[str]:
        if self.slide_family != "multiplex":
            raise UnsupportedOperationError(
                "CZI brightfield slides do not expose biomarkers"
            )
        return self._adapter.list_biomarkers()

    def get_default_display_biomarker(self) -> str:
        if self.slide_family != "multiplex":
            raise UnsupportedOperationError(
                "CZI brightfield slides do not expose biomarkers"
            )
        return self._adapter.get_default_display_biomarker()

    def read_biomarker_region(
        self,
        location: tuple[int, int],
        level: int,
        size: tuple[int, int],
        biomarker: str,
    ) -> Any:
        if self.slide_family != "multiplex":
            raise UnsupportedOperationError(
                "CZI brightfield slides do not expose biomarkers"
            )
        return self._adapter.read_biomarker_region(location, level, size, biomarker)

    def close(self) -> None:
        self._adapter.close()

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SlideBackend(Protocol):
    level_count: int
    dimensions: tuple[int, int]
    level_dimensions: Any
    level_downsamples: Any
    properties: Any

    def close(self) -> None: ...


@runtime_checkable
class DeepZoomBackend(Protocol):
    level_count: int
    level_tiles: Any
    level_dimensions: Any
    tile_count: int

    def get_dzi(self, image_format: str) -> str: ...

    def get_tile(self, level: int, address: tuple[int, int]) -> Any: ...

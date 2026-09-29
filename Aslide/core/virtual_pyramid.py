from __future__ import annotations

from math import ceil
from typing import Final, Protocol, runtime_checkable

from PIL import Image


_DEFAULT_PIXEL_BUDGET: Final = 16_000_000
_SOURCE_BLOCK_SIZE: Final = 2048
_LEVEL_STEP: Final = 4


@runtime_checkable
class SingleLevelBackend(Protocol):
    @property
    def dimensions(self) -> tuple[int, int]: ...

    @property
    def level_count(self) -> int: ...

    @property
    def level_dimensions(self) -> tuple[tuple[int, int], ...]: ...

    @property
    def level_downsamples(self) -> tuple[float, ...]: ...

    def read_region(
        self,
        location: tuple[int, int],
        level: int,
        size: tuple[int, int],
    ) -> Image.Image: ...

    def close(self) -> None: ...


class VirtualPyramidLevelError(ValueError):
    pass


def needs_virtual_pyramid(
    level_dimensions: tuple[tuple[int, int], ...],
    pixel_budget: int = _DEFAULT_PIXEL_BUDGET,
) -> bool:
    return (
        len(level_dimensions) == 1
        and level_dimensions[0][0] * level_dimensions[0][1] > pixel_budget
    )


class VirtualPyramidSlide:
    def __init__(
        self,
        backend: SingleLevelBackend,
        pixel_budget: int = _DEFAULT_PIXEL_BUDGET,
    ):
        self._backend: SingleLevelBackend = backend
        levels, downsamples = _virtual_levels(
            backend.dimensions,
            pixel_budget,
        )
        self._level_dimensions: tuple[tuple[int, int], ...] = levels
        self._level_downsamples: tuple[float, ...] = downsamples

    @property
    def dimensions(self) -> tuple[int, int]:
        return self._level_dimensions[0]

    @property
    def level_count(self) -> int:
        return len(self._level_dimensions)

    @property
    def level_dimensions(self) -> tuple[tuple[int, int], ...]:
        return self._level_dimensions

    @property
    def level_downsamples(self) -> tuple[float, ...]:
        return self._level_downsamples

    def get_best_level_for_downsample(self, downsample: float) -> int:
        best_level = 0
        for level, level_downsample in enumerate(self._level_downsamples):
            if level_downsample > downsample:
                break
            best_level = level
        return best_level

    def read_region(
        self,
        location: tuple[int, int],
        level: int,
        size: tuple[int, int],
    ) -> Image.Image:
        if level == 0:
            return self._backend.read_region(location, level, size)
        if level < 0 or level >= self.level_count:
            raise VirtualPyramidLevelError(f"Invalid level: {level}")

        downsample = int(self._level_downsamples[level])
        output = Image.new("RGBA", size, (255, 255, 255, 0))
        output_block_size = max(1, _SOURCE_BLOCK_SIZE // downsample)

        for output_y in range(0, size[1], output_block_size):
            block_height = min(output_block_size, size[1] - output_y)
            for output_x in range(0, size[0], output_block_size):
                block_width = min(output_block_size, size[0] - output_x)
                block = self._read_scaled_block(
                    location,
                    (output_x, output_y),
                    (block_width, block_height),
                    downsample,
                )
                output.paste(block, (output_x, output_y))

        return output

    def get_thumbnail(self, size: tuple[int, int]) -> Image.Image:
        requested_downsample = max(
            self.dimensions[0] / size[0],
            self.dimensions[1] / size[1],
        )
        level = self.get_best_level_for_downsample(requested_downsample)
        image = self.read_region((0, 0), level, self.level_dimensions[level])
        image.thumbnail(size, Image.Resampling.LANCZOS)
        return image

    def close(self) -> None:
        self._backend.close()

    def _read_scaled_block(
        self,
        region_location: tuple[int, int],
        output_offset: tuple[int, int],
        output_size: tuple[int, int],
        downsample: int,
    ) -> Image.Image:
        source_x = region_location[0] + output_offset[0] * downsample
        source_y = region_location[1] + output_offset[1] * downsample
        source_width = min(output_size[0] * downsample, self.dimensions[0] - source_x)
        source_height = min(output_size[1] * downsample, self.dimensions[1] - source_y)
        if source_width <= 0 or source_height <= 0:
            return Image.new("RGBA", output_size, (255, 255, 255, 0))

        source = self._backend.read_region(
            (source_x, source_y),
            0,
            (source_width, source_height),
        ).convert("RGBA")
        padded_size = (output_size[0] * downsample, output_size[1] * downsample)
        if source.size != padded_size:
            padded = Image.new("RGBA", padded_size, (255, 255, 255, 0))
            padded.paste(source, (0, 0))
            source = padded
        return source.resize(output_size, Image.Resampling.BOX)


def _virtual_levels(
    dimensions: tuple[int, int],
    pixel_budget: int,
) -> tuple[tuple[tuple[int, int], ...], tuple[float, ...]]:
    levels = [dimensions]
    downsamples = [1.0]
    downsample = 1

    while levels[-1][0] * levels[-1][1] > pixel_budget:
        downsample *= _LEVEL_STEP
        levels.append(
            (
                ceil(dimensions[0] / downsample),
                ceil(dimensions[1] / downsample),
            )
        )
        downsamples.append(float(downsample))

    return tuple(levels), tuple(downsamples)

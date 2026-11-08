from __future__ import annotations

from math import ceil

import numpy as np
from numpy.typing import NDArray
import tifffile


def read_tiff_region(
    page: tifffile.TiffPage,
    location: tuple[int, int],
    size: tuple[int, int],
) -> NDArray[np.generic]:
    x, y = location
    width, height = size
    x_end = min(x + width, page.imagewidth)
    y_end = min(y + height, page.imagelength)
    if x < 0 or y < 0 or x >= x_end or y >= y_end:
        return np.empty((0, 0), dtype=page.dtype)

    samples = page.samplesperpixel if page.samplesperpixel > 1 else 1
    output_shape = (y_end - y, x_end - x, samples)
    output = np.zeros(output_shape, dtype=page.dtype)
    for index in _intersecting_segments(page, x, y, x_end, y_end):
        offset = page.dataoffsets[index]
        byte_count = page.databytecounts[index]
        file_handle = page.parent.filehandle
        _ = file_handle.seek(offset)
        encoded = file_handle.read(byte_count)
        decoded, position, shape = _decode_segment(page, encoded, index)
        if decoded is None:
            continue
        _copy_intersection(output, decoded, position, shape, x, y, x_end, y_end)

    if samples == 1:
        return output[..., 0]
    return output


def _decode_segment(
    page: tifffile.TiffPage,
    encoded: bytes,
    index: int,
) -> tuple[
    NDArray[np.generic] | None,
    tuple[int, int, int, int, int],
    tuple[int, int, int, int],
]:
    """Decode a segment without forcing cropped edge tiles to full tile size."""
    decode_kwargs = {
        "jpegtables": page.jpegtables,
        "jpegheader": page.keyframe.jpegheader,
        "_fullsize": False,
    }
    try:
        return page.decode(encoded, index, **decode_kwargs)
    except (ValueError, tifffile.TiffFileError) as decode_error:
        if not page.is_tiled:
            raise
        try:
            return _decode_cropped_jpeg_tile(page, encoded, index)
        except Exception:
            # The segment is not a cropped JPEG bitstream, or it is corrupt.
            # Preserve the standard decoder's diagnostic in either case.
            raise decode_error


def _decode_cropped_jpeg_tile(
    page: tifffile.TiffPage,
    encoded: bytes,
    index: int,
) -> tuple[
    NDArray[np.generic],
    tuple[int, int, int, int, int],
    tuple[int, int, int, int],
]:
    """Decode a JPEG tile using dimensions stored in its JPEG bitstream."""
    try:
        import imagecodecs
    except ImportError:
        # Preserve tifffile's normal missing-codec error when imagecodecs is
        # unavailable instead of masking it with an unrelated import failure.
        return page.decode(
            encoded,
            index,
            jpegtables=page.jpegtables,
            jpegheader=page.keyframe.jpegheader,
            _fullsize=False,
        )

    _empty, position, declared_shape = page.decode(
        None,
        index,
        jpegtables=page.jpegtables,
        jpegheader=page.keyframe.jpegheader,
        _fullsize=False,
    )
    decoded = np.asarray(
        imagecodecs.jpeg_decode(
            encoded,
            bitspersample=page.bitspersample,
            tables=page.jpegtables,
            header=page.keyframe.jpegheader,
        )
    )
    if decoded.ndim == 2:
        decoded = decoded[..., np.newaxis]
    if decoded.ndim != 3:
        raise tifffile.TiffFileError(
            f"JPEG tile {index} decoded to unsupported shape {decoded.shape}"
        )

    decoded = decoded[np.newaxis, ...]
    actual_shape = (
        decoded.shape[0],
        decoded.shape[1],
        decoded.shape[2],
        decoded.shape[3],
    )
    # A malformed JPEG must not extend beyond the tile declared by the IFD.
    shape = tuple(
        min(actual, declared)
        for actual, declared in zip(actual_shape, declared_shape)
    )
    return decoded, position, shape


def _intersecting_segments(
    page: tifffile.TiffPage,
    x: int,
    y: int,
    x_end: int,
    y_end: int,
) -> tuple[int, ...]:
    if page.is_tiled:
        segment_width = page.tilewidth
        segment_height = page.tilelength
        columns = ceil(page.imagewidth / segment_width)
        rows = ceil(page.imagelength / segment_height)
        spatial_indices = tuple(
            row * columns + column
            for row in range(y // segment_height, ceil(y_end / segment_height))
            for column in range(x // segment_width, ceil(x_end / segment_width))
        )
        segments_per_plane = rows * columns
    else:
        segment_height = page.rowsperstrip
        spatial_indices = tuple(range(y // segment_height, ceil(y_end / segment_height)))
        segments_per_plane = ceil(page.imagelength / segment_height)

    if int(page.planarconfig) == int(tifffile.PLANARCONFIG.SEPARATE):
        return tuple(
            plane * segments_per_plane + index
            for plane in range(page.samplesperpixel)
            for index in spatial_indices
        )
    return spatial_indices


def _copy_intersection(
    output: NDArray[np.generic],
    decoded: NDArray[np.generic],
    position: tuple[int, int, int, int, int],
    shape: tuple[int, int, int, int],
    request_x: int,
    request_y: int,
    request_x_end: int,
    request_y_end: int,
) -> None:
    sample, _, segment_y, segment_x, _ = position
    _, declared_height, declared_width, declared_samples = shape
    segment_height = min(declared_height, decoded.shape[1])
    segment_width = min(declared_width, decoded.shape[2])
    segment_samples = min(declared_samples, decoded.shape[3])
    overlap_x = max(request_x, segment_x)
    overlap_y = max(request_y, segment_y)
    overlap_x_end = min(request_x_end, segment_x + segment_width)
    overlap_y_end = min(request_y_end, segment_y + segment_height)
    if overlap_x >= overlap_x_end or overlap_y >= overlap_y_end:
        return

    source = decoded[
        0,
        overlap_y - segment_y : overlap_y_end - segment_y,
        overlap_x - segment_x : overlap_x_end - segment_x,
        :,
    ]
    destination = output[
        overlap_y - request_y : overlap_y_end - request_y,
        overlap_x - request_x : overlap_x_end - request_x,
    ]
    if segment_samples == 1 and output.shape[-1] > 1:
        destination[..., sample] = source[..., 0]
    else:
        destination[..., :segment_samples] = source

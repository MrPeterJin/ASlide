from typing import BinaryIO, Final


_MARKER: Final = b"\xff\xfe\xff"
_PREVIEW_RECORD: Final = _MARKER + b"\x07" + "Preview".encode("utf-16le")
_SEARCH_CHUNK_SIZE: Final = 1024 * 1024
_HEADER_READ_SIZE: Final = 1024


class ZypMetadataNotFoundError(ValueError):
    pass


def locate_metadata_start(file: BinaryIO, file_size: int) -> int:
    cursor = file_size
    overlap = len(_PREVIEW_RECORD) - 1

    while cursor > 0:
        chunk_start = max(0, cursor - _SEARCH_CHUNK_SIZE)
        _ = file.seek(chunk_start)
        chunk = file.read(cursor - chunk_start + overlap)
        search_end = len(chunk)
        candidate_index = chunk.rfind(_PREVIEW_RECORD, 0, search_end)

        while candidate_index >= 0:
            search_end = candidate_index
            if candidate_index < cursor - chunk_start:
                candidate = chunk_start + candidate_index
                if _is_valid_preview_header(file, file_size, candidate):
                    return candidate
            candidate_index = chunk.rfind(_PREVIEW_RECORD, 0, search_end)

        cursor = chunk_start

    raise ZypMetadataNotFoundError("Invalid ZYP file: no valid metadata header found")


def _is_valid_preview_header(
    file: BinaryIO,
    file_size: int,
    candidate: int,
) -> bool:
    _ = file.seek(candidate)
    header = file.read(min(_HEADER_READ_SIZE, file_size - candidate))
    segments = _first_segments(header, count=5)
    if len(segments) != 5:
        return False

    name, position_key, position_value, length_key, length_value = segments
    if name != "Preview" or position_key != "StartPosition":
        return False
    if length_key != "DataLength":
        return False

    try:
        position = int(position_value)
        length = int(length_value)
    except ValueError:
        return False

    return position >= 0 and length > 0 and position + length <= candidate


def _first_segments(data: bytes, count: int) -> list[str]:
    segments: list[str] = []
    cursor = 0

    while len(segments) < count:
        marker = data.find(_MARKER, cursor)
        if marker < 0 or marker + 4 > len(data):
            break

        text_length = data[marker + 3] * 2
        text_start = marker + 4
        text_end = text_start + text_length
        if text_end > len(data):
            break

        try:
            segments.append(data[text_start:text_end].decode("utf-16le"))
        except UnicodeDecodeError:
            return []
        cursor = text_end

    return segments

from __future__ import annotations

import numpy as np

from Aslide.ome_tiff.ome_tiff_slide import _extract_channel_plane


def test_extract_channel_plane_treats_i_axis_as_ome_channel_axis() -> None:
    data = np.arange(3 * 4 * 5, dtype=np.uint16).reshape(3, 4, 5)

    plane = _extract_channel_plane(data, "IYX", 1)

    assert plane.shape == (4, 5)
    np.testing.assert_array_equal(plane, data[1])

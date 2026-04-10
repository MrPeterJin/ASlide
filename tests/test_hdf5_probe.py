from __future__ import annotations

import h5py
import numpy as np


def test_hdf5_probe_accepts_channel_first_raster_with_markers(tmp_path) -> None:
    from Aslide.hdf5_family import is_hdf5_multiplex_candidate

    path = tmp_path / "demo.hdf5"
    with h5py.File(path, "w") as handle:
        dataset = handle.create_dataset("IMC", data=np.zeros((2, 8, 6), dtype=np.uint8))
        dataset.attrs["markers"] = [b"DNA1", b"CD3"]

    assert is_hdf5_multiplex_candidate(str(path)) is True


def test_hdf5_probe_accepts_h5ad_when_it_contains_a_supported_raster(tmp_path) -> None:
    from Aslide.hdf5_family import is_hdf5_multiplex_candidate

    path = tmp_path / "image_backed.h5ad"
    with h5py.File(path, "w") as handle:
        handle.attrs["encoding-type"] = "anndata"
        dataset = handle.create_dataset(
            "images/multiplex", data=np.zeros((3, 10, 10), dtype=np.uint8)
        )
        dataset.attrs["channel_names"] = [b"DNA1", b"CD3", b"CD20"]

    assert is_hdf5_multiplex_candidate(str(path)) is True


def test_hdf5_probe_rejects_table_only_h5ad(tmp_path) -> None:
    from Aslide.hdf5_family import is_hdf5_multiplex_candidate

    path = tmp_path / "table_only.h5ad"
    with h5py.File(path, "w") as handle:
        handle.attrs["encoding-type"] = "anndata"
        handle.create_group("obs")
        handle.create_group("var")
        handle.create_dataset("X", data=np.zeros((5, 4), dtype=np.float32))

    assert is_hdf5_multiplex_candidate(str(path)) is False


def test_hdf5_slide_prefers_top_level_candidate_when_multiple_exist(tmp_path) -> None:
    from Aslide.hdf5_family import Hdf5Slide

    path = tmp_path / "multi_candidate.hdf5"
    with h5py.File(path, "w") as handle:
        root = handle.create_dataset("IMC", data=np.zeros((2, 4, 4), dtype=np.uint8))
        root.attrs["markers"] = [b"DNA1", b"CD3"]
        nested = handle.create_dataset(
            "images/aux", data=np.zeros((2, 4, 4), dtype=np.uint8)
        )
        nested.attrs["markers"] = [b"DNA1", b"CD3"]

    slide = Hdf5Slide(str(path))
    try:
        assert slide.properties["hdf5.dataset"] == "/IMC"
    finally:
        slide.close()

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SAMPLE_CZI = Path(
    "/jhcnas2/Spatial_Proteomics/Raw_Data/HE-SP/HistoPlexer/MACEGEJ/mdsc_panel/MACEGEJ_rescan.czi"
)


def _bioformats_available() -> bool:
    return (
        importlib.util.find_spec("bioformats") is not None
        and importlib.util.find_spec("javabridge") is not None
    )


def test_real_czi_sample_is_runtime_classified_and_uses_family_specific_reads() -> None:
    if not SAMPLE_CZI.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_CZI}")

    if not _bioformats_available():
        pytest.skip("bioformats or javabridge is unavailable")

    from Aslide import Slide

    with Slide(str(SAMPLE_CZI)) as slide:
        assert slide.slide_family in {"brightfield", "multiplex"}

        if slide.slide_family == "brightfield":
            region = slide.read_region((0, 0), 0, (64, 64))
            assert region.size == (64, 64)
        else:
            biomarkers = slide.list_biomarkers()
            assert biomarkers

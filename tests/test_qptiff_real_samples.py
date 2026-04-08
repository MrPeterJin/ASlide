from __future__ import annotations

from pathlib import Path


SAMPLE_HE_QPTIFF = Path(
    "/jhcnas2/Spatial_Proteomics/Raw_Data/Private/SP_IpLab/paired_HE/1072_Scan1.qptiff"
)
SAMPLE_MULTIPLEX_QPTIFF = Path(
    "/jhcnas2/Spatial_Proteomics/Raw_Data/Private/SP_IpLab/14-plex_FFPE_Human_Brain.qptiff"
)


def test_real_he_qptiff_is_classified_as_brightfield_and_supports_read_region() -> None:
    import pytest

    from Aslide import Slide

    if not SAMPLE_HE_QPTIFF.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_HE_QPTIFF}")

    with Slide(str(SAMPLE_HE_QPTIFF)) as slide:
        assert slide.slide_family == "brightfield"
        region = slide.read_region((0, 0), 0, (64, 64))
        assert region.size == (64, 64)


def test_real_he_qptiff_supports_deepzoom_after_brightfield_classification() -> None:
    import pytest

    from Aslide import DeepZoom, Slide

    if not SAMPLE_HE_QPTIFF.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_HE_QPTIFF}")

    with Slide(str(SAMPLE_HE_QPTIFF)) as slide:
        assert slide.slide_family == "brightfield"
        deepzoom = DeepZoom(slide)
        assert deepzoom.level_count > 0


def test_real_multiplex_qptiff_is_classified_as_multiplex() -> None:
    import pytest

    from Aslide import Slide

    if not SAMPLE_MULTIPLEX_QPTIFF.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_MULTIPLEX_QPTIFF}")

    with Slide(str(SAMPLE_MULTIPLEX_QPTIFF)) as slide:
        assert slide.slide_family == "multiplex"
        biomarkers = slide.list_biomarkers()
        assert "DAPI" in biomarkers

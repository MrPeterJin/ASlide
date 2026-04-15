from __future__ import annotations

from pathlib import Path

import pytest


SAMPLE_MCD = Path(
    "/jhcnas2/Spatial_Proteomics/Raw_Data/SP-ScProAtlas/12-Single-cell/sample_data/COVID_SAMPLE_6/COVID_SAMPLE_6.mcd"
)
SAMPLE_OME = Path(
    "/jhcnas2/Spatial_Proteomics/Raw_Data/SP-VirTues/1SpatialVizScore/IMC_data/zenodo/IMC_cohort_1/ROI0011_B7/141Pr_141Pr_SMA.ome.tiff"
)
SAMPLE_TIFF = Path(
    "/jhcnas2/Spatial_Proteomics/Raw_Data/SP-ScProAtlas/4-Coordinated/PKG - CRC_FFPE-CODEX_CellNeighs_v1/Tonsil_HandE/reg001_X01_Y01.tif"
)
SAMPLE_HE_TIFF = Path(
    "/jhcnas2/Spatial_Proteomics/Raw_Data/SP-OtherAtlas/HTAN/Breast_Pre-Cancer_Atlas/H&E/01_500_10_1_15_999_70.tiff"
)
SAMPLE_HE_TIF = Path(
    "/jhcnas2/Spatial_Proteomics/Raw_Data/SP-OtherAtlas/HTAN/Colon_Molecular_Atlas_Project/H&E/HTA11_1391_20000010116110030010000009999.tif"
)
SAMPLE_STANDARD_OME = Path(
    "/jhcnas2/Spatial_Proteomics/Raw_Data/SP-OtherAtlas/HTAN/Breast_Pre-Cancer_Atlas/MIBI/Point2201_31610.ome.tif"
)
SAMPLE_HDF5 = Path(
    "/jhcnas2/Spatial_Proteomics/Raw_Data/SP-VirTues/6metabolomics-protein/scSpaMet_submission_data/08_scSpaMet_submission_data/Processed/IMC/L11.hdf5"
)
SAMPLE_IMS = Path(
    "/jhcnas2/Spatial_Proteomics/Raw_Data/SP/IBEX/Human_Jejunum_Automated_IBEX.ims"
)
IMS_SAMPLE_DIR = Path("/jhcnas2/Spatial_Proteomics/Raw_Data/SP/IBEX")
IMS_SAMPLES = tuple(sorted(IMS_SAMPLE_DIR.glob("*.ims")))


def test_real_ome_anchor_is_classified_as_multiplex_and_discovers_channels() -> None:
    import pytest

    from Aslide import Slide

    if not SAMPLE_OME.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_OME}")

    with Slide(str(SAMPLE_OME)) as slide:
        assert slide.slide_family == "multiplex"
        assert len(slide.list_biomarkers()) > 1


def test_real_generic_tiff_stays_single_image() -> None:
    import pytest

    from Aslide import Slide

    if not SAMPLE_TIFF.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_TIFF}")

    with Slide(str(SAMPLE_TIFF)) as slide:
        assert slide.slide_family == "brightfield"


def test_real_he_tiff_preserves_rgb_dimensions() -> None:
    import pytest

    from Aslide import Slide

    if not SAMPLE_HE_TIFF.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_HE_TIFF}")

    with Slide(str(SAMPLE_HE_TIFF)) as slide:
        assert slide.slide_family == "brightfield"
        assert slide.dimensions == (11264, 11264)


def test_real_he_tif_preserves_rgb_dimensions() -> None:
    import pytest

    from Aslide import Slide

    if not SAMPLE_HE_TIF.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_HE_TIF}")

    with Slide(str(SAMPLE_HE_TIF)) as slide:
        assert slide.slide_family == "brightfield"
        assert slide.dimensions == (32811, 28339)


def test_real_standard_ome_tif_uses_single_file_channels() -> None:
    import pytest

    from Aslide import Slide

    if not SAMPLE_STANDARD_OME.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_STANDARD_OME}")

    with Slide(str(SAMPLE_STANDARD_OME)) as slide:
        assert slide.slide_family == "multiplex"
        biomarkers = slide.list_biomarkers()
        assert len(biomarkers) == 45
        assert "CD3" in biomarkers
        assert slide.dimensions == (1024, 1024)
        region = slide.read_biomarker_region((0, 0), 0, (64, 64), "CD3")
        assert region.size == (64, 64)


def test_real_mcd_path_is_supported_or_fails_precisely() -> None:
    import pytest

    from Aslide import Slide

    if not SAMPLE_MCD.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_MCD}")

    with Slide(str(SAMPLE_MCD)) as slide:
        assert slide.slide_family == "multiplex"
        biomarkers = slide.list_biomarkers()
        assert len(biomarkers) > 0
        assert "aSMA" in biomarkers or "CD3" in biomarkers


def test_real_mcd_supports_explicit_acquisition_selection() -> None:
    import pytest

    from Aslide import Slide

    if not SAMPLE_MCD.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_MCD}")

    with Slide(str(SAMPLE_MCD), acquisition_id=2) as slide:
        assert slide.slide_family == "multiplex"
        assert slide.properties["mcd.selected-acquisition-id"] == "2"
        assert slide.properties["mcd.selected-acquisition-description"] == "ROI_002"
        assert slide.dimensions == (1500, 1250)


def test_real_hdf5_family_is_classified_as_multiplex() -> None:
    import pytest

    from Aslide import Slide

    if not SAMPLE_HDF5.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_HDF5}")

    with Slide(str(SAMPLE_HDF5)) as slide:
        assert slide.slide_family == "multiplex"
        assert "SMA" in slide.list_biomarkers()
        assert "CD3" in slide.list_biomarkers()


def test_real_hdf5_family_supports_biomarker_reads() -> None:
    import pytest

    from Aslide import Slide

    if not SAMPLE_HDF5.exists():
        pytest.skip(f"Missing sample file: {SAMPLE_HDF5}")

    with Slide(str(SAMPLE_HDF5)) as slide:
        region = slide.read_biomarker_region((0, 0), 0, (32, 24), "CD3")
        assert region.size == (32, 24)


@pytest.mark.parametrize("sample_ims", IMS_SAMPLES, ids=lambda path: path.stem)
def test_real_ims_is_classified_as_multiplex_and_exposes_pyramid(
    sample_ims: Path,
) -> None:
    from Aslide import Slide

    if not IMS_SAMPLES:
        pytest.skip(f"Missing IMS samples in: {IMS_SAMPLE_DIR}")

    with Slide(str(sample_ims)) as slide:
        assert slide.slide_family == "multiplex"
        biomarkers = slide.list_biomarkers()
        assert len(biomarkers) > 1
        assert all(biomarker.strip() for biomarker in biomarkers)
        assert slide.level_count > 1
        assert slide.level_dimensions[0] == slide.dimensions
        assert slide.level_downsamples[-1] > 1.0
        assert any(
            marker.upper().find("HOECHST") >= 0
            or marker.upper().find("DAPI") >= 0
            or marker.upper().find("DNA") >= 0
            or marker.upper().find("HISTONE") >= 0
            for marker in biomarkers
        )


@pytest.mark.parametrize("sample_ims", IMS_SAMPLES, ids=lambda path: path.stem)
def test_real_ims_supports_biomarker_reads_and_deepzoom(sample_ims: Path) -> None:
    from Aslide import DeepZoom, Slide

    if not IMS_SAMPLES:
        pytest.skip(f"Missing IMS samples in: {IMS_SAMPLE_DIR}")

    with Slide(str(sample_ims)) as slide:
        biomarker = slide.get_default_display_biomarker()
        region = slide.read_biomarker_region((0, 0), 0, (64, 48), biomarker)
        assert region.size == (64, 48)
        assert biomarker in slide.list_biomarkers()

        deepzoom = DeepZoom(slide)
        tile = deepzoom.get_tile(0, (0, 0))
        assert tile.size[0] > 0 and tile.size[1] > 0

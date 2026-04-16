from __future__ import annotations

import pytest


def test_classify_czi_family_prefers_transmitted_light_brightfield() -> None:
    from Aslide.czi.metadata import NormalizedCziMetadata, classify_czi_family

    metadata = NormalizedCziMetadata(
        channel_count=3,
        illumination_types=("Transmitted",),
        pixel_type="bgr24",
    )

    assert classify_czi_family(metadata) == "brightfield"


def test_classify_czi_family_detects_fluorophore_or_wavelength_multiplex() -> None:
    from Aslide.czi.metadata import NormalizedCziMetadata, classify_czi_family

    metadata = NormalizedCziMetadata(
        channel_count=4,
        fluorophore_names=("DAPI", "CD3"),
        excitation_wavelengths=(405.0, 488.0),
    )

    assert classify_czi_family(metadata) == "multiplex"


def test_classify_czi_family_rejects_conflicting_evidence() -> None:
    from Aslide.czi.metadata import NormalizedCziMetadata, classify_czi_family

    metadata = NormalizedCziMetadata(
        channel_count=3,
        illumination_types=("Transmitted", "Epifluorescence"),
        fluorophore_names=("DAPI",),
        pixel_type="bgr24",
    )

    with pytest.raises(ValueError, match="conflict|classification"):
        classify_czi_family(metadata)


def test_classify_czi_family_rejects_insufficient_evidence() -> None:
    from Aslide.czi.metadata import NormalizedCziMetadata, classify_czi_family

    metadata = NormalizedCziMetadata(channel_count=1)

    with pytest.raises(LookupError, match="insufficient|unknown"):
        classify_czi_family(metadata)

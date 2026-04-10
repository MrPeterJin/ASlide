from __future__ import annotations

import importlib
import os


def test_registry_exposes_expected_backend_capabilities() -> None:
    from Aslide.registry import registry

    kfb_entry = registry.get("kfb")
    sdpc_entry = registry.get("sdpc")
    openslide_entry = registry.get("openslide")

    assert kfb_entry.capabilities.has_label_image is True
    assert kfb_entry.capabilities.has_color_correction is True
    assert sdpc_entry.capabilities.requires_bootstrap is True
    assert openslide_entry.capabilities.has_deepzoom is True


def test_vsi_entry_reports_optional_dependency_availability() -> None:
    from Aslide.registry import registry

    vsi_entry = registry.get("vsi")

    assert isinstance(vsi_entry.is_available(), bool)


def test_opencv_helper_import_has_no_side_effects(monkeypatch) -> None:
    monkeypatch.setenv("LD_LIBRARY_PATH", "baseline")

    module = importlib.import_module("Aslide.opencv")
    importlib.reload(module)

    assert os.environ["LD_LIBRARY_PATH"] == "baseline"


def test_vsi_module_exports_authoritative_backend() -> None:
    from Aslide.vsi import VsiSlide
    from Aslide.vsi.bioformats_vsi_slide import BioFormatsVsiSlide

    assert VsiSlide is BioFormatsVsiSlide


def test_registry_exposes_ome_and_mcd_multiplex_capabilities() -> None:
    from Aslide.registry import registry

    ome_entry = registry.get("ome_tiff")
    mcd_entry = registry.get("mcd")

    assert ome_entry.slide_family == "multiplex"
    assert ome_entry.capabilities.supports_biomarkers is True
    assert ome_entry.capabilities.requires_explicit_channel_read is True

    assert mcd_entry.slide_family == "multiplex"
    assert mcd_entry.capabilities.supports_biomarkers is True
    assert mcd_entry.capabilities.requires_explicit_channel_read is True


def test_registry_exposes_hdf5_multiplex_capabilities() -> None:
    from Aslide.registry import registry

    entry = registry.get("hdf5")

    assert entry.slide_family == "multiplex"
    assert entry.capabilities.supports_biomarkers is True
    assert entry.capabilities.requires_explicit_channel_read is True

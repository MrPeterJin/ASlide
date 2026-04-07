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

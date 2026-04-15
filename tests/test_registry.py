from __future__ import annotations

import pytest


def test_registry_module_exists_and_exposes_global_registry() -> None:
    from Aslide.registry import registry

    assert registry is not None


def test_registry_resolves_case_insensitive_extension() -> None:
    from Aslide.registry import FormatEntry, FormatRegistry

    registry = FormatRegistry()
    entry = FormatEntry(format_id="kfb", extensions=(".kfb",), slide_backend=object)
    registry.register(entry)

    resolved = registry.resolve_path("sample.KFB")

    assert resolved.format_id == "kfb"


def test_registry_raises_for_unsupported_extension() -> None:
    from Aslide.registry import FormatRegistry

    registry = FormatRegistry()

    with pytest.raises(LookupError):
        registry.resolve_path("sample.unknown")


def test_registry_skips_unavailable_entries(fake_backend_classes) -> None:
    from Aslide.registry import FormatEntry, FormatRegistry

    fake_slide_backend, _ = fake_backend_classes
    registry = FormatRegistry()
    registry.register(
        FormatEntry(
            format_id="fake",
            extensions=(".fake",),
            slide_backend=fake_slide_backend,
            availability_check=lambda: False,
        )
    )

    with pytest.raises(LookupError):
        registry.resolve_path("demo.fake")


def test_registry_entries_can_declare_slide_family_and_multiplex_capabilities(
    fake_backend_classes,
) -> None:
    from Aslide.capabilities import BackendCapabilities
    from Aslide.registry import FormatEntry

    fake_slide_backend, _ = fake_backend_classes

    entry = FormatEntry(
        format_id="qptiff",
        extensions=(".qptiff",),
        slide_backend=fake_slide_backend,
        slide_family="multiplex",
        capabilities=BackendCapabilities(
            supports_biomarkers=True,
            requires_explicit_channel_read=True,
            default_display_biomarker="DAPI",
        ),
    )

    assert entry.slide_family == "multiplex"
    assert entry.capabilities.supports_biomarkers is True
    assert entry.capabilities.requires_explicit_channel_read is True
    assert entry.capabilities.default_display_biomarker == "DAPI"


def test_qptiff_registry_entry_is_no_longer_statically_multiplex() -> None:
    from Aslide.registry import registry

    entry = registry.get("qptiff")

    assert entry.slide_family != "multiplex"


def test_registry_prefers_probe_matched_ome_entry_over_generic_tiff(
    fake_ome_multiplex_backend, fake_generic_tiff_backend
) -> None:
    from Aslide.registry import FormatEntry, FormatRegistry

    registry = FormatRegistry()
    registry.register(
        FormatEntry(
            format_id="ome_tiff",
            extensions=(".tif", ".tiff"),
            slide_backend=fake_ome_multiplex_backend,
            slide_family="multiplex",
            probe=lambda path: path.endswith(".ome.tiff"),
        )
    )
    registry.register(
        FormatEntry(
            format_id="openslide",
            extensions=(".tif", ".tiff"),
            slide_backend=fake_generic_tiff_backend,
        )
    )

    resolved = registry.resolve_path("roi/marker.ome.tiff")

    assert resolved.format_id == "ome_tiff"


def test_registry_falls_back_to_generic_tiff_when_probe_rejects(
    fake_ome_multiplex_backend, fake_generic_tiff_backend
) -> None:
    from Aslide.registry import FormatEntry, FormatRegistry

    registry = FormatRegistry()
    registry.register(
        FormatEntry(
            format_id="ome_tiff",
            extensions=(".tif", ".tiff"),
            slide_backend=fake_ome_multiplex_backend,
            slide_family="multiplex",
            probe=lambda path: False,
        )
    )
    registry.register(
        FormatEntry(
            format_id="openslide",
            extensions=(".tif", ".tiff"),
            slide_backend=fake_generic_tiff_backend,
        )
    )

    resolved = registry.resolve_path("roi/channel.tiff")

    assert resolved.format_id == "openslide"


def test_default_registry_exposes_mcd_entry() -> None:
    from Aslide.registry import registry

    entry = registry.get("mcd")

    assert entry.slide_family == "multiplex"
    assert ".mcd" in entry.extensions


def test_default_registry_exposes_hdf5_entry() -> None:
    from Aslide.registry import registry

    entry = registry.get("hdf5")

    assert entry.slide_family == "multiplex"
    assert entry.capabilities.supports_biomarkers is True
    assert ".h5" in entry.extensions
    assert ".hdf5" in entry.extensions
    assert ".h5ad" in entry.extensions


def test_default_registry_exposes_ims_entry() -> None:
    from Aslide.registry import registry

    entry = registry.get("ims")

    assert entry.slide_family == "multiplex"
    assert entry.capabilities.supports_biomarkers is True
    assert entry.capabilities.requires_explicit_channel_read is True
    assert ".ims" in entry.extensions


def test_registry_prefers_hdf5_probe_for_h5ad(fake_multiplex_backend) -> None:
    from Aslide.registry import FormatEntry, FormatRegistry

    registry = FormatRegistry()
    registry.register(
        FormatEntry(
            format_id="hdf5",
            extensions=(".h5", ".hdf5", ".h5ad"),
            slide_backend=fake_multiplex_backend,
            slide_family="multiplex",
            probe=lambda path: path.endswith("supported.h5ad"),
        )
    )

    resolved = registry.resolve_path("demo.supported.h5ad")

    assert resolved.format_id == "hdf5"

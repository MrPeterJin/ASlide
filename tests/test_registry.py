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

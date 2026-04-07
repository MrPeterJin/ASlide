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

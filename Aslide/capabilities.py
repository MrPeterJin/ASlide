from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackendCapabilities:
    has_label_image: bool = False
    has_color_correction: bool = False
    has_associated_images: bool = True
    has_deepzoom: bool = False
    requires_bootstrap: bool = False

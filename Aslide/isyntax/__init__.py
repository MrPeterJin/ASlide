"""
iSyntax format support for ASlide
"""

try:
    from .isyntax_slide import IsyntaxSlide, open_isyntax_slide
    ISYNTAX_AVAILABLE = True
except ImportError:
    IsyntaxSlide = None
    open_isyntax_slide = None
    ISYNTAX_AVAILABLE = False

__all__ = ['IsyntaxSlide', 'open_isyntax_slide', 'ISYNTAX_AVAILABLE']


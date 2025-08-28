"""
VSI slide reader implementation.
Based on Bio-Formats CellSensReader implementation.
Licensed under GPL v2+ (compatible with Bio-Formats license)
"""

import os
import logging
from typing import Tuple, List, Dict, Any, Optional
from PIL import Image

from openslide import AbstractSlide

# Import Bio-Formats implementation
try:
    from .bioformats_vsi_slide import BioFormatsVsiSlide
    BIOFORMATS_AVAILABLE = True
except ImportError:
    BIOFORMATS_AVAILABLE = False


logger = logging.getLogger(__name__)


class VsiSlide(AbstractSlide):
    """
    VSI slide reader using Bio-Formats implementation.
    """
    
    def __init__(self, filename: str):
        """Initialize VSI slide reader."""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"VSI file not found: {filename}")
        
        self._filename = filename
        
        # Use Bio-Formats implementation
        if not BIOFORMATS_AVAILABLE:
            raise ImportError("Bio-Formats is required for VSI support. Please install python-bioformats.")
        
        try:
            logger.info("Initializing Bio-Formats VSI reader...")
            self._bioformats_slide = BioFormatsVsiSlide(filename)
            logger.info("Successfully initialized Bio-Formats VSI reader")
        except Exception as e:
            logger.error(f"Bio-Formats initialization failed: {e}")
            raise

    # Delegate all properties and methods to Bio-Formats implementation
    
    @property
    def level_count(self) -> int:
        """Number of levels in the slide."""
        return self._bioformats_slide.level_count

    @property
    def dimensions(self) -> Tuple[int, int]:
        """Dimensions of level 0 (width, height)."""
        return self._bioformats_slide.dimensions

    @property
    def level_dimensions(self) -> Tuple[Tuple[int, int], ...]:
        """Dimensions of each level."""
        return self._bioformats_slide.level_dimensions

    @property
    def level_downsamples(self) -> Tuple[float, ...]:
        """Downsample factor for each level."""
        return self._bioformats_slide.level_downsamples

    @property
    def properties(self) -> Dict[str, str]:
        """Slide properties."""
        return self._bioformats_slide.properties

    @property
    def associated_images(self) -> Dict[str, Image.Image]:
        """Associated images."""
        return self._bioformats_slide.associated_images

    @property
    def mpp(self) -> Optional[float]:
        """Microns per pixel."""
        return self._bioformats_slide.mpp

    def read_region(self, location: Tuple[int, int], level: int, size: Tuple[int, int]) -> Image.Image:
        """Read a region from the slide."""
        return self._bioformats_slide.read_region(location, level, size)

    def get_best_level_for_downsample(self, downsample: float) -> int:
        """Get the best level for a given downsample factor."""
        return self._bioformats_slide.get_best_level_for_downsample(downsample)

    def get_thumbnail(self, size: Tuple[int, int]) -> Image.Image:
        """Get a thumbnail of the slide."""
        return self._bioformats_slide.get_thumbnail(size)

    def close(self):
        """Close the slide and clean up resources."""
        if hasattr(self, '_bioformats_slide') and self._bioformats_slide:
            self._bioformats_slide.close()

    @classmethod
    def detect_format(cls, filename: str) -> Optional[str]:
        """Detect if a file is in VSI format."""
        if not BIOFORMATS_AVAILABLE:
            return None

        return BioFormatsVsiSlide.detect_format(filename)

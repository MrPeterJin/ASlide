"""
Bio-Formats based VSI slide reader for ASlide.
This implementation uses the python-bioformats wrapper to read VSI files.
"""

import os
import logging
import numpy as np
from typing import Tuple, List, Dict, Any, Optional
from PIL import Image

try:
    import bioformats
    import javabridge
    BIOFORMATS_AVAILABLE = True
except ImportError:
    BIOFORMATS_AVAILABLE = False

from openslide import AbstractSlide

logger = logging.getLogger(__name__)


class BioFormatsVsiSlide(AbstractSlide):
    """VSI slide reader using Bio-Formats."""
    
    def __init__(self, filename: str):
        """Initialize VSI slide using Bio-Formats."""
        if not BIOFORMATS_AVAILABLE:
            raise ImportError("Bio-Formats not available. Install with: pip install python-bioformats")
        
        self._filename = filename
        self._metadata = None
        self._ome = None
        self._image_reader = None
        self._java_started = False
        
        # Start Java VM if not already started
        if not javabridge.get_env():
            javabridge.start_vm(class_path=bioformats.JARS)
            self._java_started = True
        
        try:
            # Get metadata
            self._metadata = bioformats.get_omexml_metadata(filename)
            self._ome = bioformats.OMEXML(self._metadata)
            self._image_reader = bioformats.ImageReader(filename)
            
            # Initialize slide properties
            self._init_properties()
            
        except Exception as e:
            self.close()
            raise Exception(f"Failed to initialize VSI slide: {e}")
    
    def _init_properties(self):
        """Initialize slide properties from Bio-Formats metadata."""
        if self._ome.image_count == 0:
            raise ValueError("No images found in VSI file")
        
        # Use the first (main) image
        main_image = self._ome.image(0)
        pixels = main_image.Pixels
        
        # Basic dimensions
        self._level_count = 1  # Bio-Formats handles pyramid levels internally
        self._dimensions = (pixels.SizeX, pixels.SizeY)
        self._level_dimensions = [self._dimensions]
        self._level_downsamples = [1.0]
        
        # Try to get physical pixel size
        self._mpp_x = self._mpp_y = None
        try:
            phys_x = pixels.PhysicalSizeX
            phys_y = pixels.PhysicalSizeY
            if phys_x is not None and phys_y is not None:
                # Convert to microns per pixel (MPP)
                self._mpp_x = float(phys_x)
                self._mpp_y = float(phys_y)
                logger.info(f"Physical pixel size from OME: {self._mpp_x} x {self._mpp_y} microns")
            else:
                logger.warning("Physical pixel size not available in OME metadata, will try properties")
        except Exception as e:
            logger.warning(f"Failed to get physical pixel size from OME: {e}")

        # If OME metadata doesn't have physical size, try to get it from properties later
        # This will be handled in the mpp property getter
        
        # Properties dictionary
        self._properties = {
            'openslide.vendor': 'Olympus',
            'openslide.comment': 'cellSens VSI format (Bio-Formats)',
        }
        
        if self._mpp_x and self._mpp_y:
            self._properties['openslide.mpp-x'] = str(self._mpp_x)
            self._properties['openslide.mpp-y'] = str(self._mpp_y)
        
        # Add Bio-Formats metadata
        if hasattr(main_image, 'Name') and main_image.Name:
            self._properties['bioformats.image.name'] = main_image.Name
        
        self._properties['bioformats.pixel.type'] = pixels.PixelType
        self._properties['bioformats.size.c'] = str(pixels.SizeC)
        self._properties['bioformats.size.z'] = str(pixels.SizeZ)
        self._properties['bioformats.size.t'] = str(pixels.SizeT)
    
    @property
    def level_count(self) -> int:
        """Number of levels in the image pyramid."""
        return self._level_count
    
    @property
    def dimensions(self) -> Tuple[int, int]:
        """Dimensions of level 0 image."""
        return self._dimensions
    
    @property
    def level_dimensions(self) -> List[Tuple[int, int]]:
        """List of (width, height) tuples for each level."""
        return self._level_dimensions
    
    @property
    def level_downsamples(self) -> List[float]:
        """List of downsample factors for each level."""
        return self._level_downsamples
    
    @property
    def properties(self) -> Dict[str, str]:
        """Metadata properties."""
        return self._properties.copy()
    
    @property
    def associated_images(self) -> Dict[str, Image.Image]:
        """Associated images (thumbnails, labels, etc.)."""
        # Bio-Formats handles associated images differently
        # For now, return empty dict
        return {}
    
    @property
    def mpp(self) -> Optional[float]:
        """Microns per pixel."""
        # First try the stored values
        if self._mpp_x and self._mpp_y:
            return (self._mpp_x + self._mpp_y) / 2

        # Fallback: get from properties
        props = self.properties
        if 'openslide.mpp-x' in props and 'openslide.mpp-y' in props:
            try:
                mpp_x = float(props['openslide.mpp-x'])
                mpp_y = float(props['openslide.mpp-y'])
                return (mpp_x + mpp_y) / 2
            except (ValueError, TypeError):
                pass

        return None
    
    @property
    def magnification(self) -> Optional[float]:
        """Get slide magnification."""
        # Check properties
        props = self.properties
        if 'openslide.objective-power' in props:
            try:
                return float(props['openslide.objective-power'])
            except:
                pass
        
        # Fallback to MPP calculation
        mpp = self.mpp
        if mpp and mpp > 0:
            return 10.0 / mpp
        return None
    
    def read_region(self, location: Tuple[int, int], level: int, size: Tuple[int, int]) -> Image.Image:
        """Read a region from the slide."""
        if level != 0:
            raise ValueError("Bio-Formats VSI reader only supports level 0")
        
        x, y = location
        width, height = size
        
        try:
            # Read region using Bio-Formats
            img_array = self._image_reader.read(
                c=0, z=0, t=0, series=0, rescale=False,
                XYWH=(x, y, width, height)
            )
            
            # Convert to PIL Image
            if len(img_array.shape) == 3:
                # RGB image
                return Image.fromarray(img_array)
            else:
                # Grayscale image
                return Image.fromarray(img_array, mode='L')
                
        except Exception as e:
            logger.error(f"Failed to read region {location} at level {level}: {e}")
            # Return a placeholder image
            placeholder = np.zeros((height, width, 3), dtype=np.uint8)
            return Image.fromarray(placeholder)
    
    def get_best_level_for_downsample(self, downsample: float) -> int:
        """Get the best level for a given downsample factor."""
        # With Bio-Formats, we only have level 0
        return 0
    
    def get_thumbnail(self, size: Tuple[int, int]) -> Image.Image:
        """Get a thumbnail of the slide."""
        thumb_width, thumb_height = size
        slide_width, slide_height = self._dimensions

        # Calculate scale factor
        scale_x = slide_width / thumb_width
        scale_y = slide_height / thumb_height
        scale = max(scale_x, scale_y)

        # Calculate the size to read at reduced resolution
        read_width = min(int(slide_width / scale), slide_width)
        read_height = min(int(slide_height / scale), slide_height)

        # For efficiency, read a smaller region and then resize
        # Use a maximum read size to avoid memory issues
        max_read_size = 2048
        if read_width > max_read_size or read_height > max_read_size:
            read_scale = max(read_width / max_read_size, read_height / max_read_size)
            read_width = int(read_width / read_scale)
            read_height = int(read_height / read_scale)

        # Read from the center of the image for better representation
        start_x = max(0, (slide_width - read_width) // 2)
        start_y = max(0, (slide_height - read_height) // 2)

        region = self.read_region((start_x, start_y), 0, (read_width, read_height))

        # Resize to requested thumbnail size
        return region.resize(size, Image.Resampling.LANCZOS)
    
    @classmethod
    def detect_format(cls, filename: str) -> Optional[str]:
        """Detect if a file is in VSI format."""
        if not BIOFORMATS_AVAILABLE:
            return None

        try:
            # Basic check - VSI files should have .vsi extension
            if not filename.lower().endswith('.vsi'):
                return None

            # Try to read the file header
            with open(filename, 'rb') as f:
                header = f.read(8)
                if len(header) == 8:
                    # Check for TIFF magic bytes (VSI files are TIFF-based)
                    if header[:4] in [b'II*\x00', b'MM\x00*']:
                        return "cellSens VSI (Bio-Formats)"
        except (OSError, IOError):
            pass

        return None

    def close(self):
        """Close the slide and clean up resources."""
        if self._image_reader:
            try:
                self._image_reader.close()
            except:
                pass
            self._image_reader = None

        # Clean up Java VM if we started it
        if self._java_started:
            try:
                import javabridge
                if javabridge.get_env():
                    javabridge.kill_vm()
                    logger.info("Java VM cleaned up by Bio-Formats VSI slide")
            except:
                pass
            self._java_started = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

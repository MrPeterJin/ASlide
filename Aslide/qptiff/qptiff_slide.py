"""
QPTiff slide reader for ASlide
Supports reading .qptiff files using the qptifffile library
"""

import os
import numpy as np
from PIL import Image
from typing import Optional, Tuple, List, Dict, Any

try:
    from qptifffile import QPTiffFile
    QPTIFFFILE_AVAILABLE = True
except ImportError:
    QPTIFFFILE_AVAILABLE = False
    QPTiffFile = None

from openslide import AbstractSlide


class QptiffSlide(AbstractSlide):
    """QPTiff slide reader using qptifffile library"""
    
    def __init__(self, filename: str):
        """Initialize QPTiff slide
        
        Args:
            filename: Path to .qptiff file
        """
        if not QPTIFFFILE_AVAILABLE:
            raise ImportError("qptifffile library is not available. Please install it with: pip install qptifffile")
        
        AbstractSlide.__init__(self)
        self.__filename = filename
        self._qptiff = QPTiffFile(filename)
        
        # Get basic information
        self._biomarkers = self._qptiff.get_biomarkers()
        self._series = self._qptiff.series[0] if self._qptiff.series else None
        
        if not self._series:
            raise ValueError(f"No series found in QPTiff file: {filename}")
        
        # Cache properties
        self._level_count = len(self._series.levels)
        self._level_dimensions = tuple((level.shape[2], level.shape[1]) for level in self._series.levels)
        self._level_downsamples = self._calculate_downsamples()
        
        # Set format for compatibility
        self.format = os.path.splitext(os.path.basename(filename))[-1]
    
    def __repr__(self):
        return f'{self.__class__.__name__}({self.__filename!r})'
    
    @classmethod
    def detect_format(cls, filename: str) -> Optional[str]:
        """Detect if file is QPTiff format"""
        if not QPTIFFFILE_AVAILABLE:
            return None
        
        try:
            # Check file extension first
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.qptiff']:
                return None
            
            # Try to open the file
            with QPTiffFile(filename) as f:
                biomarkers = f.get_biomarkers()
                if biomarkers:
                    return "qptiff"
            return None
        except Exception:
            return None
    
    def close(self):
        """Close the QPTiff file"""
        if hasattr(self, '_qptiff') and self._qptiff:
            self._qptiff.close()
            self._qptiff = None
    
    @property
    def level_count(self) -> int:
        """The number of levels in the image"""
        return self._level_count
    
    @property
    def level_dimensions(self) -> Tuple[Tuple[int, int], ...]:
        """A list of (width, height) tuples, one for each level"""
        return self._level_dimensions
    
    @property
    def level_downsamples(self) -> Tuple[float, ...]:
        """A list of downsample factors for each level"""
        return self._level_downsamples
    
    @property
    def dimensions(self) -> Tuple[int, int]:
        """The dimensions of level 0 (width, height)"""
        return self._level_dimensions[0] if self._level_dimensions else (0, 0)
    
    @property
    def mpp(self) -> Optional[float]:
        """Microns per pixel"""
        # Try to get from series metadata if available
        # qptifffile usually stores resolution in metadata
        try:
            if hasattr(self._series, 'axes') and 'X' in self._series.axes:
                # This depends on qptifffile implementation
                pass
        except:
            pass
        return None

    @property
    def magnification(self) -> Optional[float]:
        """Get slide magnification"""
        # Fallback to MPP calculation if mpp becomes available
        mpp = self.mpp
        if mpp and mpp > 0:
            return 10.0 / mpp
        return None

    @property
    def properties(self) -> Dict[str, str]:
        """Slide properties"""
        props = {
            'openslide.vendor': 'QPTiff',
            'qptiff.biomarkers': ','.join(self._biomarkers),
            'qptiff.biomarker-count': str(len(self._biomarkers)),
        }
        
        # Add level information
        for i, (w, h) in enumerate(self._level_dimensions):
            props[f'openslide.level[{i}].width'] = str(w)
            props[f'openslide.level[{i}].height'] = str(h)
            props[f'openslide.level[{i}].downsample'] = str(self._level_downsamples[i])
        
        return props
    
    @property
    def associated_images(self) -> Dict[str, Image.Image]:
        """Get associated images (thumbnails, etc.)"""
        # QPTiff files don't typically have associated images like label/macro
        # But we can create a thumbnail from the lowest resolution level
        result = {}
        
        try:
            # Create thumbnail from the lowest resolution level
            if self._level_count > 0:
                last_level = self._level_count - 1
                # Use the first biomarker for thumbnail
                if self._biomarkers:
                    thumbnail_data = self._qptiff.read_region(
                        layers=[self._biomarkers[0]], 
                        level=last_level
                    )
                    # Handle different data ranges from qptifffile
                    if thumbnail_data.dtype == np.uint8 and thumbnail_data.max() <= 1:
                        # Data is uint8 but in 0-1 range, scale to 0-255
                        normalized = (thumbnail_data * 255).astype(np.uint8)
                    elif thumbnail_data.max() > thumbnail_data.min():
                        # Standard normalization for other cases
                        normalized = ((thumbnail_data - thumbnail_data.min()) /
                                    (thumbnail_data.max() - thumbnail_data.min()) * 255).astype(np.uint8)
                    else:
                        normalized = np.zeros_like(thumbnail_data, dtype=np.uint8)
                    
                    result['thumbnail'] = Image.fromarray(normalized)
        except Exception:
            pass
        
        return result
    
    def get_best_level_for_downsample(self, downsample: float) -> int:
        """Get the best level for a given downsample factor.

        This mirrors OpenSlide's behavior:
        - Return the largest level whose downsample is <= target
        - This ensures we don't over-downsample (lose resolution)
        """
        if not self._level_downsamples:
            return 0

        downsamples = self._level_downsamples

        # If target is smaller than level 0, return level 0
        if downsample < downsamples[0]:
            return 0

        # Find the largest level with downsample <= target
        for i in range(1, len(downsamples)):
            if downsamples[i] > downsample:
                return i - 1

        # Target is >= all levels, return the last level
        return len(downsamples) - 1
    
    def read_region(self, location: Tuple[int, int], level: int, size: Tuple[int, int]) -> Image.Image:
        """Read a region from the slide
        
        Args:
            location: (x, y) tuple giving the top left pixel in the level 0 reference frame
            level: the level number
            size: (width, height) tuple giving the region size
            
        Returns:
            PIL Image object
        """
        x, y = location
        width, height = size
        
        if level >= self._level_count:
            raise ValueError(f"Level {level} not available (max level: {self._level_count - 1})")
        
        # Calculate position at the requested level
        downsample = self._level_downsamples[level]
        level_x = int(x / downsample)
        level_y = int(y / downsample)
        
        try:
            # For now, use the first biomarker (DAPI is usually first and most informative)
            # In the future, this could be made configurable
            biomarker = self._biomarkers[0] if self._biomarkers else None
            if not biomarker:
                raise ValueError("No biomarkers available in QPTiff file")
            
            # Read the region
            region_data = self._qptiff.read_region(
                layers=[biomarker],
                pos=(level_x, level_y),
                shape=(height, width),  # Note: qptifffile uses (height, width)
                level=level
            )
            
            # Convert to PIL Image
            # Handle different data ranges from qptifffile
            if region_data.dtype == np.uint8 and region_data.max() <= 1:
                # Data is uint8 but in 0-1 range, scale to 0-255
                normalized = (region_data * 255).astype(np.uint8)
            elif region_data.max() > region_data.min():
                # Standard normalization for other cases
                normalized = ((region_data - region_data.min()) /
                            (region_data.max() - region_data.min()) * 255).astype(np.uint8)
            else:
                normalized = np.zeros_like(region_data, dtype=np.uint8)
            
            # Convert grayscale to RGB for compatibility
            if len(normalized.shape) == 2:
                rgb_data = np.stack([normalized] * 3, axis=-1)
            else:
                rgb_data = normalized
            
            return Image.fromarray(rgb_data)
            
        except Exception as e:
            # Return a blank image if reading fails
            blank = np.zeros((height, width, 3), dtype=np.uint8)
            return Image.fromarray(blank)
    
    def read_region_biomarker(self, location: Tuple[int, int], level: int, size: Tuple[int, int], 
                             biomarker: str) -> Image.Image:
        """Read a region for a specific biomarker
        
        Args:
            location: (x, y) tuple giving the top left pixel in the level 0 reference frame
            level: the level number
            size: (width, height) tuple giving the region size
            biomarker: name of the biomarker to read
            
        Returns:
            PIL Image object
        """
        if biomarker not in self._biomarkers:
            raise ValueError(f"Biomarker '{biomarker}' not found. Available: {self._biomarkers}")
        
        x, y = location
        width, height = size
        
        if level >= self._level_count:
            raise ValueError(f"Level {level} not available (max level: {self._level_count - 1})")
        
        # Calculate position at the requested level
        downsample = self._level_downsamples[level]
        level_x = int(x / downsample)
        level_y = int(y / downsample)
        
        try:
            # Read the region for the specific biomarker
            region_data = self._qptiff.read_region(
                layers=[biomarker],
                pos=(level_x, level_y),
                shape=(height, width),  # Note: qptifffile uses (height, width)
                level=level
            )
            
            # Convert to PIL Image
            # Handle different data ranges from qptifffile
            if region_data.dtype == np.uint8 and region_data.max() <= 1:
                # Data is uint8 but in 0-1 range, scale to 0-255
                normalized = (region_data * 255).astype(np.uint8)
            elif region_data.max() > region_data.min():
                # Standard normalization for other cases
                normalized = ((region_data - region_data.min()) /
                            (region_data.max() - region_data.min()) * 255).astype(np.uint8)
            else:
                normalized = np.zeros_like(region_data, dtype=np.uint8)
            
            # Convert grayscale to RGB for compatibility
            if len(normalized.shape) == 2:
                rgb_data = np.stack([normalized] * 3, axis=-1)
            else:
                rgb_data = normalized
            
            return Image.fromarray(rgb_data)
            
        except Exception as e:
            # Return a blank image if reading fails
            blank = np.zeros((height, width, 3), dtype=np.uint8)
            return Image.fromarray(blank)
    
    def get_biomarkers(self) -> List[str]:
        """Get list of available biomarkers"""
        return self._biomarkers.copy()

    def get_thumbnail(self, size: Tuple[int, int]) -> Image.Image:
        """Get a thumbnail of the slide

        Args:
            size: (width, height) tuple giving the maximum size of the thumbnail

        Returns:
            PIL Image object
        """
        # Read from the lowest resolution level
        last_level = self._level_count - 1
        thumb = self.read_region((0, 0), last_level, self._level_dimensions[last_level])

        # Resize to requested size while maintaining aspect ratio
        thumb.thumbnail(size, Image.LANCZOS)
        return thumb

    def _calculate_downsamples(self) -> Tuple[float, ...]:
        """Calculate downsample factors for each level"""
        if not self._level_dimensions:
            return tuple()

        base_width, base_height = self._level_dimensions[0]
        downsamples = []

        for width, height in self._level_dimensions:
            # Calculate downsample based on width (assuming square pixels)
            downsample = base_width / width
            downsamples.append(downsample)

        return tuple(downsamples)

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False

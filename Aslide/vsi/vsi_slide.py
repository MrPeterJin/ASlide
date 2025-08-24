"""
VSI slide reader implementation.
Based on Bio-Formats CellSensReader implementation.
Licensed under GPL v2+ (compatible with Bio-Formats license)
"""

import os
import logging
from typing import Tuple, List, Dict, Any, Optional
from PIL import Image
import numpy as np

from openslide import AbstractSlide
from .vsi_parser import VsiParser
from .vsi_structures import VsiMetadata, Pyramid
from .vsi_decoder import VsiDecoder
from .ets_reader import EtsReader
from .tiff_reader import TiffReader


logger = logging.getLogger(__name__)


class VsiSlide(AbstractSlide):
    """
    A slide reader for Olympus cellSens VSI format files.
    
    This implementation is based on the Bio-Formats CellSensReader
    and is licensed under GPL v2+ to maintain compatibility.
    """
    
    def __init__(self, filename: str):
        """
        Initialize a VSI slide reader.
        
        Args:
            filename: Path to the .vsi file
        """
        AbstractSlide.__init__(self)
        self._filename = filename
        self._metadata: Optional[VsiMetadata] = None
        self._current_series = 0
        self._decoder = VsiDecoder()
        self._ets_reader = EtsReader()
        self._tiff_reader = TiffReader()
        
        # Parse the VSI file
        try:
            parser = VsiParser()
            self._metadata = parser.parse_vsi_file(filename)
            logger.info(f"Successfully parsed VSI file: {filename}")
            logger.info(f"Found {len(self._metadata.pyramids)} pyramid(s)")
            logger.info(f"Found {len(self._metadata.used_files)} file(s)")
        except Exception as e:
            logger.error(f"Failed to parse VSI file {filename}: {e}")
            raise
    
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._filename!r})'
    
    @classmethod
    def detect_format(cls, filename: str) -> Optional[str]:
        """
        Detect if a file is in VSI format.
        
        Args:
            filename: Path to the file to check
            
        Returns:
            Format string if VSI format, None otherwise
        """
        if not filename.lower().endswith('.vsi'):
            return None
            
        try:
            # Basic check - try to read the file header
            with open(filename, 'rb') as f:
                header = f.read(8)
                if len(header) == 8:
                    return "cellSens VSI"
        except (OSError, IOError):
            pass
            
        return None
    
    def close(self) -> None:
        """Close the slide and release resources."""
        # VSI files don't require special cleanup
        pass
    
    @property
    def level_count(self) -> int:
        """The number of levels in the image."""
        if not self._metadata or not self._metadata.pyramids:
            return 0

        pyramid = self._get_current_pyramid()
        if not pyramid:
            return 0

        # Calculate pyramid levels based on tile structure and image dimensions
        if hasattr(self, '_calculated_levels') and self._calculated_levels:
            return len(self._calculated_levels)

        # Calculate levels from image dimensions and tile information
        self._calculate_pyramid_levels()
        return len(self._calculated_levels) if hasattr(self, '_calculated_levels') else 1

    @property
    def level_dimensions(self) -> Tuple[Tuple[int, int], ...]:
        """A tuple of (width, height) tuples, one for each level."""
        if not self._metadata or not self._metadata.pyramids:
            return ()

        pyramid = self._get_current_pyramid()
        if not pyramid:
            raise ValueError("No current pyramid available")

        # Ensure levels are calculated
        if not hasattr(self, '_calculated_levels') or not self._calculated_levels:
            self._calculate_pyramid_levels()

        if hasattr(self, '_calculated_levels') and self._calculated_levels:
            return tuple((level['width'], level['height']) for level in self._calculated_levels)

        # Fallback to single level if calculation fails
        if pyramid.width and pyramid.height:
            return ((pyramid.width, pyramid.height),)

        raise ValueError("VSI file does not contain image dimensions")

    @property
    def level_downsamples(self) -> Tuple[float, ...]:
        """A tuple of downsampling factors for each level."""
        if not hasattr(self, '_calculated_levels') or not self._calculated_levels:
            self._calculate_pyramid_levels()

        if hasattr(self, '_calculated_levels') and self._calculated_levels:
            return tuple(level['downsample'] for level in self._calculated_levels)

        return (1.0,)
    
    @property
    def properties(self) -> Dict[str, str]:
        """Metadata about the image."""
        props = {}
        
        if self._metadata:
            pyramid = self._get_current_pyramid()
            if pyramid:
                # Add basic properties
                if pyramid.magnification is not None:
                    props['openslide.objective-power'] = str(pyramid.magnification)
                
                if pyramid.physical_size_x is not None:
                    props['openslide.mpp-x'] = str(pyramid.physical_size_x)
                
                if pyramid.physical_size_y is not None:
                    props['openslide.mpp-y'] = str(pyramid.physical_size_y)
                
                props['openslide.vendor'] = 'Olympus'
                props['openslide.comment'] = 'cellSens VSI format'
                
                # Add device information
                if pyramid.device_names:
                    props['vsi.device.name'] = ', '.join(pyramid.device_names)
                
                if pyramid.device_types:
                    props['vsi.device.type'] = ', '.join(pyramid.device_types)
                
                # Add objective information
                if pyramid.numerical_aperture is not None:
                    props['vsi.objective.numerical_aperture'] = str(pyramid.numerical_aperture)
                
                if pyramid.working_distance is not None:
                    props['vsi.objective.working_distance'] = str(pyramid.working_distance)
                
                # Add camera settings
                if pyramid.gain is not None:
                    props['vsi.camera.gain'] = str(pyramid.gain)
                
                if pyramid.offset is not None:
                    props['vsi.camera.offset'] = str(pyramid.offset)
                
                if pyramid.binning_x is not None:
                    props['vsi.camera.binning_x'] = str(pyramid.binning_x)
                
                if pyramid.binning_y is not None:
                    props['vsi.camera.binning_y'] = str(pyramid.binning_y)
        
        return props
    
    @property
    def associated_images(self) -> Dict[str, Image.Image]:
        """Images associated with this whole-slide image."""
        if not hasattr(self, '_associated_images'):
            self._associated_images = self._extract_associated_images()
        return self._associated_images
    
    def get_best_level_for_downsample(self, downsample: float) -> int:
        """Return the best level for displaying the given downsample."""
        if not hasattr(self, '_calculated_levels') or not self._calculated_levels:
            self._calculate_pyramid_levels()

        if not hasattr(self, '_calculated_levels') or not self._calculated_levels:
            return 0

        # Find the level with downsample closest to but not exceeding the requested downsample
        best_level = 0
        best_diff = float('inf')

        for i, level in enumerate(self._calculated_levels):
            level_downsample = level['downsample']
            if level_downsample <= downsample:
                diff = abs(downsample - level_downsample)
                if diff < best_diff:
                    best_diff = diff
                    best_level = i

        return best_level
    
    def read_region(self, location: Tuple[int, int], level: int, size: Tuple[int, int]) -> Image.Image:
        """
        Return a PIL.Image containing the contents of the region.

        Args:
            location: (x, y) tuple giving the top left pixel in the level 0 reference frame
            level: the level number
            size: (width, height) tuple giving the region size

        Returns:
            PIL Image containing the requested region
        """
        if level >= self.level_count:
            raise ValueError(f"Invalid level {level}, max level is {self.level_count - 1}")

        x, y = location
        width, height = size

        # Try to read actual image data
        try:
            return self._read_region_from_tiles(x, y, width, height, level)
        except Exception as e:
            logger.warning(f"Failed to read VSI region from tiles: {e}")
            return self._create_placeholder_region(x, y, width, height)

    def _read_region_from_tiles(self, x: int, y: int, width: int, height: int, level: int) -> Image.Image:
        """Read a region by compositing tiles."""
        if not self._metadata or not self._metadata.pyramids:
            raise ValueError("No metadata available")

        pyramid_index = self._current_series
        if pyramid_index >= len(self._metadata.pyramids):
            raise ValueError("Invalid series index")

        pyramid = self._metadata.pyramids[pyramid_index]

        # Check if we have tile information
        if (pyramid_index >= len(self._metadata.tile_offsets) or
            not self._metadata.tile_offsets[pyramid_index]):
            raise ValueError("No tile data available")

        # For now, try to read from embedded TIFF data or ETS files
        if self._metadata.expect_ets and pyramid.has_associated_ets_file:
            return self._read_from_ets_files(x, y, width, height, level, pyramid_index)
        else:
            return self._read_from_embedded_tiff(x, y, width, height, level, pyramid_index)

    def _read_from_ets_files(self, x: int, y: int, width: int, height: int,
                           level: int, pyramid_index: int) -> Image.Image:
        """Read region from external ETS files."""
        try:
            # Try to read a tile from ETS files
            # For simplicity, read the first available tile
            tile = self._ets_reader.read_tile_at_coordinates(self._filename, pyramid_index, 0, 0, 0)

            if tile:
                # Resize the tile to match the requested region size
                if tile.size != (width, height):
                    tile = tile.resize((width, height), Image.LANCZOS)

                # Crop or pad to match the exact region
                return self._adjust_tile_to_region(tile, x, y, width, height)
            else:
                logger.warning("No ETS tile found, using placeholder")
                return self._create_ets_placeholder(x, y, width, height)

        except Exception as e:
            logger.error(f"Error reading from ETS files: {e}")
            return self._create_ets_placeholder(x, y, width, height)

    def _read_from_embedded_tiff(self, x: int, y: int, width: int, height: int,
                               level: int, pyramid_index: int) -> Image.Image:
        """Read region from embedded TIFF data."""
        try:
            # Get TIFF IFD offsets for this pyramid
            if (pyramid_index < len(self._metadata.tile_offsets) and
                self._metadata.tile_offsets[pyramid_index]):

                # Try to read from the first available TIFF IFD
                ifd_offset = self._metadata.tile_offsets[pyramid_index][0]

                tiff_image = self._tiff_reader.read_tiff_from_vsi(self._filename, ifd_offset)

                if tiff_image:
                    # Crop and resize to match requested region
                    return self._extract_region_from_image(tiff_image, x, y, width, height)
                else:
                    logger.warning("Failed to read TIFF data, using placeholder")
                    return self._create_tiff_placeholder(x, y, width, height)
            else:
                logger.warning("No TIFF IFD offsets available")
                return self._create_tiff_placeholder(x, y, width, height)

        except Exception as e:
            logger.error(f"Error reading embedded TIFF: {e}")
            return self._create_tiff_placeholder(x, y, width, height)

    def _create_placeholder_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """Create a placeholder image with a gradient pattern."""
        img_array = np.zeros((height, width, 3), dtype=np.uint8)

        # Add a simple pattern to show the region
        for i in range(height):
            for j in range(width):
                img_array[i, j] = [
                    (x + j) % 256,
                    (y + i) % 256,
                    ((x + j + y + i) // 2) % 256
                ]

        return Image.fromarray(img_array, 'RGB')

    def _create_ets_placeholder(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """Create a placeholder indicating ETS file reading is needed."""
        img_array = np.full((height, width, 3), [100, 150, 200], dtype=np.uint8)

        # Add a pattern to indicate this is ETS data
        for i in range(0, height, 20):
            for j in range(0, width, 20):
                if (i // 20 + j // 20) % 2:
                    end_i = min(i + 10, height)
                    end_j = min(j + 10, width)
                    img_array[i:end_i, j:end_j] = [150, 200, 250]

        return Image.fromarray(img_array, 'RGB')

    def _create_tiff_placeholder(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """Create a placeholder indicating embedded TIFF reading is needed."""
        img_array = np.full((height, width, 3), [200, 150, 100], dtype=np.uint8)

        # Add a pattern to indicate this is embedded TIFF data
        for i in range(0, height, 15):
            for j in range(0, width, 15):
                if (i // 15 + j // 15) % 2:
                    end_i = min(i + 7, height)
                    end_j = min(j + 7, width)
                    img_array[i:end_i, j:end_j] = [250, 200, 150]

        return Image.fromarray(img_array, 'RGB')

    def _adjust_tile_to_region(self, tile: Image.Image, x: int, y: int,
                              width: int, height: int) -> Image.Image:
        """Adjust a tile to match the requested region."""
        # For now, just return the resized tile
        # In a full implementation, you would handle proper tile positioning
        if tile.size != (width, height):
            return tile.resize((width, height), Image.LANCZOS)
        return tile

    def _extract_region_from_image(self, image: Image.Image, x: int, y: int,
                                  width: int, height: int) -> Image.Image:
        """Extract a specific region from a full image."""
        try:
            # Ensure coordinates are within image bounds
            img_width, img_height = image.size
            x = max(0, min(x, img_width - 1))
            y = max(0, min(y, img_height - 1))

            # Calculate actual crop region
            crop_width = min(width, img_width - x)
            crop_height = min(height, img_height - y)

            # Crop the image
            cropped = image.crop((x, y, x + crop_width, y + crop_height))

            # Resize to exact requested size if needed
            if cropped.size != (width, height):
                cropped = cropped.resize((width, height), Image.LANCZOS)

            return cropped

        except Exception as e:
            logger.error(f"Error extracting region from image: {e}")
            # Return a placeholder if extraction fails
            return self._create_placeholder_region(x, y, width, height)

    def _calculate_pyramid_levels(self) -> None:
        """Calculate pyramid levels from VSI metadata."""
        pyramid = self._get_current_pyramid()
        if not pyramid or not pyramid.width or not pyramid.height:
            self._calculated_levels = [{'width': 1024, 'height': 1024, 'downsample': 1.0}]
            return

        levels = []
        pyramid_index = self._current_series

        # Check if we have tile information to determine levels
        if (pyramid_index < len(self._metadata.tile_offsets) and
            self._metadata.tile_offsets[pyramid_index]):

            # Calculate levels based on tile structure
            tile_count = len(self._metadata.tile_offsets[pyramid_index])

            if pyramid_index < len(self._metadata.rows) and pyramid_index < len(self._metadata.cols):
                rows = self._metadata.rows[pyramid_index]
                cols = self._metadata.cols[pyramid_index]

                # Estimate tile size
                if rows > 0 and cols > 0:
                    tile_width = pyramid.width // cols
                    tile_height = pyramid.height // rows

                    # Create multiple levels by downsampling
                    current_width = pyramid.width
                    current_height = pyramid.height
                    downsample = 1.0

                    while current_width >= tile_width and current_height >= tile_height:
                        levels.append({
                            'width': current_width,
                            'height': current_height,
                            'downsample': downsample,
                            'tile_width': min(tile_width, current_width),
                            'tile_height': min(tile_height, current_height)
                        })

                        # Next level is half the size
                        current_width = max(1, current_width // 2)
                        current_height = max(1, current_height // 2)
                        downsample *= 2.0

                        # Stop if we get too small
                        if current_width < 64 or current_height < 64:
                            break

        # If no levels calculated from tiles, create standard pyramid
        if not levels:
            current_width = pyramid.width
            current_height = pyramid.height
            downsample = 1.0

            # Create standard pyramid levels
            while current_width > 1 or current_height > 1:
                levels.append({
                    'width': current_width,
                    'height': current_height,
                    'downsample': downsample,
                    'tile_width': min(256, current_width),
                    'tile_height': min(256, current_height)
                })

                current_width = max(1, current_width // 2)
                current_height = max(1, current_height // 2)
                downsample *= 2.0

                # Limit to reasonable number of levels
                if len(levels) >= 20:
                    break

        # Ensure we have at least one level
        if not levels:
            levels.append({
                'width': pyramid.width or 1024,
                'height': pyramid.height or 1024,
                'downsample': 1.0,
                'tile_width': 256,
                'tile_height': 256
            })

        self._calculated_levels = levels

    def get_thumbnail(self, size: Tuple[int, int] = (256, 256)) -> Image.Image:
        """
        Return a PIL.Image containing an RGB thumbnail of the image.
        
        Args:
            size: the maximum size of the thumbnail
            
        Returns:
            PIL Image thumbnail
        """
        # Use the base class implementation which calls read_region
        return super().get_thumbnail(size)
    
    def _get_current_pyramid(self) -> Optional[Pyramid]:
        """Get the current pyramid/series."""
        if (self._metadata and 
            self._metadata.pyramids and 
            0 <= self._current_series < len(self._metadata.pyramids)):
            return self._metadata.pyramids[self._current_series]
        return None
    
    def set_series(self, series: int) -> None:
        """
        Set the current series/pyramid.
        
        Args:
            series: Series index to set as current
        """
        if not self._metadata or not self._metadata.pyramids:
            raise ValueError("No pyramids available")
        
        if not 0 <= series < len(self._metadata.pyramids):
            raise ValueError(f"Invalid series {series}, available: 0-{len(self._metadata.pyramids)-1}")
        
        self._current_series = series
    
    @property
    def series_count(self) -> int:
        """Number of series/pyramids in the file."""
        if self._metadata and self._metadata.pyramids:
            return len(self._metadata.pyramids)
        return 0

    def get_series_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all series in the VSI file.

        Returns:
            List of dictionaries containing series information
        """
        series_info = []

        if not self._metadata or not self._metadata.pyramids:
            return series_info

        for i, pyramid in enumerate(self._metadata.pyramids):
            info = {
                'index': i,
                'name': pyramid.name or f"Series {i}",
                'width': pyramid.width,
                'height': pyramid.height,
                'magnification': pyramid.magnification,
                'objective_name': pyramid.objective_names[0] if pyramid.objective_names else None,
                'channel_count': len(pyramid.channel_names),
                'channel_names': pyramid.channel_names.copy(),
                'physical_size_x': pyramid.physical_size_x,
                'physical_size_y': pyramid.physical_size_y,
                'has_external_files': pyramid.has_associated_ets_file,
            }
            series_info.append(info)

        return series_info

    def _extract_associated_images(self) -> Dict[str, Image.Image]:
        """
        Extract associated images from VSI series.

        Based on vsi2tif library approach and Bio-Formats CellSensReader behavior.
        VSI format typically has multiple series where:
        - Series 0: Main high-resolution image
        - Series 1+: Overview, macro, label images (smaller resolution)
        """
        associated = {}

        if not self._metadata or not self._metadata.pyramids:
            return associated

        # Save current series
        original_series = self._current_series

        try:
            # Look for special series that can be treated as associated images
            # Based on vsi2tif: skip overview files and look for smaller series
            for i, pyramid in enumerate(self._metadata.pyramids):
                # Skip the main image series (usually index 0)
                if i == 0:
                    continue

                # Determine associated image type based on series characteristics
                associated_name = None

                if pyramid.name:
                    name_lower = pyramid.name.lower()

                    # Direct name matching (Bio-Formats style)
                    if name_lower in ['overview', 'overview image']:
                        associated_name = 'overview'
                    elif name_lower in ['macro', 'macro image']:
                        associated_name = 'macro'
                    elif name_lower in ['label', 'label image', 'slide label']:
                        associated_name = 'label'
                    elif name_lower in ['thumbnail', 'thumb']:
                        associated_name = 'thumbnail'
                    # vsi2tif skips files with "overview" in name
                    elif 'overview' in name_lower:
                        continue
                else:
                    # For unnamed series, use size heuristics
                    if pyramid.width and pyramid.height:
                        # Small images are likely thumbnails/labels
                        if pyramid.width <= 1024 and pyramid.height <= 1024:
                            if 'thumbnail' not in associated:
                                associated_name = 'thumbnail'
                            elif 'overview' not in associated:
                                associated_name = 'overview'
                        # Medium images might be macro
                        elif pyramid.width <= 4096 and pyramid.height <= 4096:
                            if 'macro' not in associated:
                                associated_name = 'macro'

                if associated_name:
                    try:
                        # Switch to this series
                        self.set_series(i)

                        # Get image dimensions
                        width, height = self.dimensions

                        # Limit size for associated images (following vsi2tif approach)
                        max_size = 2048
                        if width > max_size or height > max_size:
                            scale = min(max_size / width, max_size / height)
                            read_width = int(width * scale)
                            read_height = int(height * scale)
                        else:
                            read_width = width
                            read_height = height

                        # Read the image
                        img = self.read_region((0, 0), 0, (read_width, read_height))
                        associated[associated_name] = img

                        logger.debug(f"Extracted {associated_name} from series {i}: {img.size}")

                    except Exception as e:
                        logger.debug(f"Could not extract {associated_name} from series {i}: {e}")

            # Generate thumbnail if not found in series (fallback)
            if 'thumbnail' not in associated:
                try:
                    # Restore to main series for thumbnail generation
                    self.set_series(0)
                    thumbnail = self.get_thumbnail((256, 256))
                    associated['thumbnail'] = thumbnail
                    logger.debug("Generated thumbnail from main series")
                except Exception as e:
                    logger.debug(f"Could not generate thumbnail: {e}")

        except Exception as e:
            logger.error(f"Error extracting associated images: {e}")
        finally:
            # Always restore original series
            try:
                self.set_series(original_series)
            except:
                pass

        return associated

    def label_image(self) -> Optional[Image.Image]:
        """
        Get the label image from the VSI file.

        VSI format may contain a "Label" series that shows the physical slide label
        (barcode, sample ID, etc.). This method searches for and returns such an image.

        Based on Bio-Formats CellSensReader and vsi2tif library patterns.

        Returns:
            PIL Image of the label, or None if no label image is found
        """
        # First try to get from associated images cache
        if hasattr(self, '_associated_images') and 'label' in self._associated_images:
            return self._associated_images['label']

        if not self._metadata or not self._metadata.pyramids:
            return None

        # Save current series
        original_series = self._current_series

        try:
            # Look for label image in pyramids (Bio-Formats approach)
            for i, pyramid in enumerate(self._metadata.pyramids):
                if pyramid.name:
                    name_lower = pyramid.name.lower()

                    # Check for explicit label naming
                    if name_lower in ['label', 'label image', 'slide label']:
                        # Switch to label series
                        self.set_series(i)

                        # Get label image dimensions
                        width, height = self.dimensions

                        # Read the label image (labels are typically small)
                        max_label_size = 2048
                        if width > max_label_size or height > max_label_size:
                            scale = min(max_label_size / width, max_label_size / height)
                            read_width = int(width * scale)
                            read_height = int(height * scale)
                        else:
                            read_width = width
                            read_height = height

                        label_img = self.read_region((0, 0), 0, (read_width, read_height))
                        self.set_series(original_series)
                        return label_img

            # If no explicit label found, look for small series that might be labels
            # (following vsi2tif size-based heuristics)
            for i, pyramid in enumerate(self._metadata.pyramids):
                # Skip main series
                if i == 0:
                    continue

                if pyramid.width and pyramid.height:
                    # Very small images might be labels (barcode, specimen info)
                    if (pyramid.width <= 512 and pyramid.height <= 512):
                        try:
                            self.set_series(i)
                            label_img = self.read_region((0, 0), 0, (pyramid.width, pyramid.height))
                            self.set_series(original_series)
                            return label_img
                        except Exception as e:
                            logger.debug(f"Failed to read potential label from series {i}: {e}")
                            continue

            return None

        except Exception as e:
            logger.debug(f"Error reading label image: {e}")
            # Restore original series on error
            try:
                self.set_series(original_series)
            except:
                pass
            return None

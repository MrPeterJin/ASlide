"""
TRON format slide reader for ASlide

TRON format is a ZIP-based whole slide image format that contains:
- Pyramid structure with multiple zoom levels (0/, 1/, 2/, etc.)
- JPEG tiles organized in x/y coordinate system
- Associated images (label, sample, macro, thumbnail, blank)
- Metadata in .tron binary file
"""

import os
import zipfile
import tempfile
import shutil
from PIL import Image
import struct
import math
from typing import Dict, List, Tuple, Optional, Any


class TronSlide:
    """
    A class for reading TRON format whole slide images.
    
    TRON files are ZIP archives containing:
    - Hierarchical directory structure for pyramid levels
    - JPEG tiles in each level
    - Associated images (label, macro, thumbnail, etc.)
    - Binary metadata file (.tron)
    """
    
    def __init__(self, filepath: str):
        """
        Initialize TronSlide with the given file path.
        
        Args:
            filepath: Path to the .tron file
        """
        self.filepath = filepath
        self._temp_dir = None
        self._zip_file = None
        self._level_count = 0
        self._level_dimensions = []
        self._level_downsamples = []
        self._properties = {}
        self._associated_images = {}
        self._tile_size = (256, 256)  # Default tile size, will be determined from actual tiles

        # Initialize MPP values
        self.mpp_x = None
        self.mpp_y = None
        
        # Open and analyze the TRON file
        self._open_tron_file()
        self._analyze_structure()
        self._load_metadata()
        self._load_associated_images()
    
    def _open_tron_file(self):
        """Open the TRON ZIP file and extract to temporary directory."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"TRON file not found: {self.filepath}")

        if not zipfile.is_zipfile(self.filepath):
            raise ValueError(f"File is not a valid ZIP archive: {self.filepath}")

        # Create temporary directory for extraction
        self._temp_dir = tempfile.mkdtemp(prefix='tron_')

        # Extract ZIP contents with proper path handling
        with zipfile.ZipFile(self.filepath, 'r') as zip_ref:
            for member in zip_ref.infolist():
                # Convert Windows-style paths to Unix-style
                member.filename = member.filename.replace('\\', '/')
                zip_ref.extract(member, self._temp_dir)
    
    def _analyze_structure(self):
        """Analyze the directory structure to determine pyramid levels and dimensions."""
        if not self._temp_dir:
            return

        # Find all level directories (numeric directories)
        level_dirs = []
        for item in os.listdir(self._temp_dir):
            item_path = os.path.join(self._temp_dir, item)
            if os.path.isdir(item_path) and item.isdigit():
                level_dirs.append(int(item))

        level_dirs.sort()
        self._level_count = len(level_dirs)

        # Store tile coordinate ranges for each level
        self._tile_ranges = []

        # Analyze each level
        for level in level_dirs:
            level_path = os.path.join(self._temp_dir, str(level), '1')

            if not os.path.exists(level_path):
                continue

            # Find the tile coordinate ranges
            min_x, max_x = float('inf'), -1
            min_y, max_y = float('inf'), -1
            tile_files = []

            try:
                for x_dir in os.listdir(level_path):
                    x_path = os.path.join(level_path, x_dir)
                    if os.path.isdir(x_path) and x_dir.isdigit():
                        x_coord = int(x_dir)
                        min_x = min(min_x, x_coord)
                        max_x = max(max_x, x_coord)

                        for y_file in os.listdir(x_path):
                            if y_file.endswith('.jpg'):
                                y_coord = int(y_file.replace('.jpg', ''))
                                min_y = min(min_y, y_coord)
                                max_y = max(max_y, y_coord)
                                tile_files.append(os.path.join(x_path, y_file))

                # Skip levels with no tiles
                if max_x < 0 or max_y < 0 or not tile_files:
                    continue

                # Store tile coordinate range for this level
                self._tile_ranges.append((min_x, min_y, max_x, max_y))

                # Determine tile size from first tile
                if tile_files and len(self._level_dimensions) == 0:
                    try:
                        with Image.open(tile_files[0]) as img:
                            self._tile_size = img.size
                    except Exception:
                        pass  # Keep default tile size

                # Calculate level dimensions based on tile coordinate range
                tile_width, tile_height = self._tile_size
                level_width = (max_x - min_x + 1) * tile_width
                level_height = (max_y - min_y + 1) * tile_height

                self._level_dimensions.append((level_width, level_height))

            except Exception:
                continue

        # Calculate downsamples (relative to level 0)
        if self._level_dimensions:
            base_width, base_height = self._level_dimensions[0]
            for width, height in self._level_dimensions:
                downsample = base_width / width if width > 0 else 1.0
                self._level_downsamples.append(downsample)
    
    def _load_metadata(self):
        """Load metadata from .tron file if present."""
        tron_file = os.path.join(self._temp_dir, '.tron')
        if os.path.exists(tron_file):
            try:
                with open(tron_file, 'rb') as f:
                    # Read TRON header
                    header = f.read(4)
                    if header == b'TRON':
                        # This is a TRON metadata file
                        # For now, just store basic info
                        self._properties['tron.format'] = 'TRON'
                        self._properties['tron.version'] = '1.0'

                        # Try to parse MPP information from binary data
                        self._parse_mpp_from_binary(f)

            except Exception as e:
                # If we can't read metadata, continue without it
                pass
        
        # Set basic properties
        self._properties['tron.level-count'] = str(self._level_count)
        self._properties['tron.tile-width'] = str(self._tile_size[0])
        self._properties['tron.tile-height'] = str(self._tile_size[1])

        # Add MPP to properties if available
        if self.mpp_x is not None:
            self._properties['openslide.mpp-x'] = str(self.mpp_x)
        if self.mpp_y is not None:
            self._properties['openslide.mpp-y'] = str(self.mpp_y)

    def _parse_mpp_from_binary(self, file_handle):
        """Parse MPP information from binary TRON metadata."""
        try:
            # Reset to beginning after header
            file_handle.seek(4)

            # Read the entire binary content
            binary_data = file_handle.read()

            # Try to find common MPP-related patterns in the binary data
            # Look for floating point values that might represent pixel size
            import struct

            # Common patterns to search for:
            # 1. Look for "PixelSize" or similar strings
            # 2. Look for floating point values in reasonable MPP range (0.1 - 10.0)

            # Search for text patterns first
            text_patterns = [
                b'PixelSizeX', b'PixelSizeY',
                b'pixelsize', b'pixel_size',
                b'MPP', b'mpp',
                b'Resolution', b'resolution'
            ]

            for pattern in text_patterns:
                pos = binary_data.find(pattern)
                if pos != -1:
                    # Found a pattern, try to extract nearby float values
                    self._extract_mpp_near_position(binary_data, pos)
                    break

            # If no text patterns found, try to find reasonable float values
            if self.mpp_x is None or self.mpp_y is None:
                self._extract_mpp_from_floats(binary_data)

        except Exception as e:
            # If parsing fails, continue without MPP
            pass

    def _extract_mpp_near_position(self, binary_data, position):
        """Extract MPP values near a found text pattern."""
        try:
            import struct

            # Search in a window around the found position
            start = max(0, position - 100)
            end = min(len(binary_data), position + 100)
            window = binary_data[start:end]

            candidates = []

            # Try to find float values in this window
            for i in range(0, len(window) - 4, 1):
                try:
                    # Try little-endian float
                    value = struct.unpack('<f', window[i:i+4])[0]
                    if 0.05 <= value <= 2.0:  # More restrictive MPP range
                        candidates.append(value)
                except:
                    continue

            # If we found candidates, use the most reasonable ones
            if candidates:
                # Sort candidates and look for similar values (likely X and Y)
                candidates.sort()

                # Look for pairs of similar values
                for i, val1 in enumerate(candidates):
                    for val2 in candidates[i+1:]:
                        if abs(val1 - val2) < 0.1:  # Very similar values
                            self.mpp_x = val1
                            self.mpp_y = val2
                            return

                # If no similar pairs, use the first reasonable value for both
                if candidates:
                    self.mpp_x = candidates[0]
                    self.mpp_y = candidates[0]  # Assume square pixels

        except Exception:
            pass

    def _extract_mpp_from_floats(self, binary_data):
        """Extract MPP by scanning for reasonable float values."""
        try:
            import struct

            candidates = []

            # Scan for float values in reasonable MPP range
            for i in range(0, len(binary_data) - 4, 4):
                try:
                    # Try little-endian float
                    value = struct.unpack('<f', binary_data[i:i+4])[0]
                    if 0.05 <= value <= 2.0:  # More restrictive MPP range
                        candidates.append(value)
                except:
                    continue

            # If we found candidates, use statistical analysis
            if candidates:
                from collections import Counter

                # Round to 3 decimal places to group similar values
                rounded_candidates = [round(c, 3) for c in candidates]
                counter = Counter(rounded_candidates)
                most_common = counter.most_common(10)

                # Look for the most reasonable MPP values
                # Prefer values that appear multiple times and are in typical range
                reasonable_values = []
                for value, count in most_common:
                    if 0.08 <= value <= 0.5 and count >= 2:  # Typical microscopy MPP range
                        reasonable_values.append(value)

                if reasonable_values:
                    # Use the most common reasonable value
                    self.mpp_x = reasonable_values[0]
                    # Look for a similar value for Y, or use the same
                    if len(reasonable_values) > 1:
                        # Find the closest value to mpp_x
                        closest = min(reasonable_values[1:], key=lambda x: abs(x - self.mpp_x))
                        if abs(closest - self.mpp_x) < 0.05:  # Very similar
                            self.mpp_y = closest
                        else:
                            self.mpp_y = self.mpp_x  # Assume square pixels
                    else:
                        self.mpp_y = self.mpp_x  # Assume square pixels

        except Exception:
            pass

    def _load_associated_images(self):
        """Load associated images (label, macro, thumbnail, etc.)."""
        associated_files = ['label', 'macro', 'thumbnail', 'sample', 'blank']
        
        for assoc_name in associated_files:
            assoc_path = os.path.join(self._temp_dir, assoc_name)
            if os.path.exists(assoc_path):
                try:
                    self._associated_images[assoc_name] = Image.open(assoc_path).copy()
                except Exception:
                    pass  # Skip if can't load
    
    @property
    def level_count(self) -> int:
        """Number of levels in the pyramid."""
        return self._level_count
    
    @property
    def dimensions(self) -> Tuple[int, int]:
        """Dimensions of level 0 (base level)."""
        if self._level_dimensions:
            return self._level_dimensions[0]
        return (0, 0)
    
    @property
    def level_dimensions(self) -> List[Tuple[int, int]]:
        """List of (width, height) tuples for each level."""
        return self._level_dimensions.copy()
    
    @property
    def level_downsamples(self) -> List[float]:
        """List of downsample factors for each level."""
        return self._level_downsamples.copy()
    
    @property
    def properties(self) -> Dict[str, str]:
        """Dictionary of slide properties."""
        return self._properties.copy()
    
    @property
    def associated_images(self) -> Dict[str, Image.Image]:
        """Dictionary of associated images."""
        return self._associated_images.copy()
    
    def get_best_level_for_downsample(self, downsample: float) -> int:
        """
        Get the best level for a given downsample factor.
        
        Args:
            downsample: Desired downsample factor
            
        Returns:
            Level number (0-based)
        """
        if not self._level_downsamples:
            return 0
        
        best_level = 0
        best_diff = abs(self._level_downsamples[0] - downsample)
        
        for i, level_downsample in enumerate(self._level_downsamples):
            diff = abs(level_downsample - downsample)
            if diff < best_diff:
                best_diff = diff
                best_level = i
        
        return best_level
    
    def get_thumbnail(self, size: Tuple[int, int]) -> Image.Image:
        """
        Get a thumbnail of the slide.
        
        Args:
            size: (width, height) tuple for thumbnail size
            
        Returns:
            PIL Image thumbnail
        """
        # Try to use existing thumbnail first
        if 'thumbnail' in self._associated_images:
            thumb = self._associated_images['thumbnail'].copy()
            thumb.thumbnail(size, Image.Resampling.LANCZOS)
            return thumb
        
        # Otherwise create from highest level
        if self._level_count > 0:
            highest_level = self._level_count - 1
            level_width, level_height = self._level_dimensions[highest_level]
            
            # Read the entire highest level (should be small)
            region = self.read_region((0, 0), highest_level, (level_width, level_height))
            region.thumbnail(size, Image.Resampling.LANCZOS)
            return region
        
        # Fallback: create empty image
        return Image.new('RGB', size, (255, 255, 255))

    def read_region(self, location: Tuple[int, int], level: int, size: Tuple[int, int]) -> Image.Image:
        """
        Read a region from the slide.

        Args:
            location: (x, y) tuple giving the top left pixel in the level 0 reference frame
            level: Level number (0-based)
            size: (width, height) tuple giving the region size

        Returns:
            PIL Image of the requested region (padded with white if beyond boundaries)
        """
        if level < 0 or level >= self._level_count:
            raise ValueError(f"Invalid level {level}, must be 0-{self._level_count-1}")

        if not self._temp_dir:
            raise RuntimeError("TRON file not properly opened")

        x, y = location
        width, height = size

        # Adjust coordinates for the requested level
        downsample = self._level_downsamples[level]
        level_x = int(x / downsample)
        level_y = int(y / downsample)
        level_width = width
        level_height = height

        # Create output image with white background (for padding)
        result = Image.new('RGB', (level_width, level_height), (255, 255, 255))

        # Get tile coordinate range for this level
        if level >= len(self._tile_ranges):
            return result  # Return white image if level doesn't exist

        min_tile_x, min_tile_y, max_tile_x, max_tile_y = self._tile_ranges[level]
        tile_width, tile_height = self._tile_size

        # Convert level pixel coordinates to tile coordinates for this specific level
        # Each level has its own tile coordinate system starting from (min_tile_x, min_tile_y)
        start_tile_x = level_x // tile_width + min_tile_x
        start_tile_y = level_y // tile_height + min_tile_y
        end_tile_x = (level_x + level_width - 1) // tile_width + min_tile_x
        end_tile_y = (level_y + level_height - 1) // tile_height + min_tile_y

        # Read tiles and composite them
        for tile_y in range(start_tile_y, end_tile_y + 1):
            for tile_x in range(start_tile_x, end_tile_x + 1):
                # Skip tiles outside the available range for this level
                if (tile_x < min_tile_x or tile_x > max_tile_x or
                    tile_y < min_tile_y or tile_y > max_tile_y):
                    continue

                tile_path = os.path.join(self._temp_dir, str(level), '1', str(tile_x), f'{tile_y}.jpg')

                if os.path.exists(tile_path):
                    try:
                        with Image.open(tile_path) as tile:
                            # Calculate tile position in level pixel coordinates
                            # Convert tile coordinates back to pixel coordinates for this level
                            tile_level_x = (tile_x - min_tile_x) * tile_width
                            tile_level_y = (tile_y - min_tile_y) * tile_height

                            # Calculate intersection with requested region
                            src_left = max(0, level_x - tile_level_x)
                            src_top = max(0, level_y - tile_level_y)
                            src_right = min(tile_width, level_x + level_width - tile_level_x)
                            src_bottom = min(tile_height, level_y + level_height - tile_level_y)

                            # Calculate destination position in result image
                            dst_left = max(0, tile_level_x - level_x)
                            dst_top = max(0, tile_level_y - level_y)
                            dst_right = dst_left + (src_right - src_left)
                            dst_bottom = dst_top + (src_bottom - src_top)

                            # Ensure we don't go outside the result image bounds
                            if (src_right > src_left and src_bottom > src_top and
                                dst_left >= 0 and dst_top >= 0 and
                                dst_right <= level_width and dst_bottom <= level_height):

                                # Crop the tile if necessary
                                if (src_left > 0 or src_top > 0 or
                                    src_right < tile_width or src_bottom < tile_height):
                                    tile_crop = tile.crop((src_left, src_top, src_right, src_bottom))
                                else:
                                    tile_crop = tile.copy()

                                # Paste into result (areas outside bounds remain white)
                                result.paste(tile_crop, (dst_left, dst_top))

                    except Exception:
                        # Skip problematic tiles, leave white padding
                        continue

        return result

    def read_fixed_region(self, location: Tuple[int, int], level: int, size: Tuple[int, int]) -> Image.Image:
        """
        Read a region with fixed size (same as read_region for TRON format).

        Args:
            location: (x, y) tuple giving the top left pixel in the level 0 reference frame
            level: Level number (0-based)
            size: (width, height) tuple giving the region size

        Returns:
            PIL Image of the requested region
        """
        return self.read_region(location, level, size)

    def close(self):
        """Clean up temporary files and close the slide."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
            except Exception:
                pass  # Best effort cleanup
            self._temp_dir = None

        # Close associated images
        for img in self._associated_images.values():
            try:
                img.close()
            except Exception:
                pass
        self._associated_images.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.close()

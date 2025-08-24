"""
VSI DeepZoom generator implementation.
Based on Bio-Formats CellSensReader implementation.
Licensed under GPL v2+ (compatible with Bio-Formats license)
"""

import math
import logging
from typing import Tuple, Optional
from PIL import Image
from xml.etree.ElementTree import ElementTree, Element, SubElement
from io import BytesIO

from .vsi_slide import VsiSlide


logger = logging.getLogger(__name__)


class VsiDeepZoomGenerator:
    """DeepZoom generator for VSI format slides."""
    
    def __init__(self, slide: VsiSlide, tile_size: int = 254, overlap: int = 1, limit_bounds: bool = False):
        """
        Create a DeepZoomGenerator wrapping a VSI slide object.
        
        Args:
            slide: VSI slide object
            tile_size: Width and height of a single tile
            overlap: Number of extra pixels to add to each interior edge of a tile
            limit_bounds: True to render only the non-empty slide region
        """
        self.slide = slide
        self._tile_size = tile_size
        self._overlap = overlap
        self._limit_bounds = limit_bounds
        
        # Calculate zoom levels
        self._calculate_levels()
    
    def _calculate_levels(self) -> None:
        """Calculate the number of zoom levels."""
        if not self.slide.dimensions:
            self._level_count = 0
            self._level_dimensions = []
            return
        
        # Start with the slide dimensions
        width, height = self.slide.dimensions
        
        # Calculate levels by repeatedly halving dimensions
        levels = []
        while width > 1 or height > 1:
            levels.append((width, height))
            width = max(1, width // 2)
            height = max(1, height // 2)
        
        # Add the final 1x1 level
        levels.append((1, 1))
        
        # Reverse to have smallest first
        levels.reverse()
        
        self._level_count = len(levels)
        self._level_dimensions = levels
    
    @property
    def level_count(self) -> int:
        """The number of Deep Zoom levels in the image."""
        return self._level_count
    
    @property
    def level_dimensions(self) -> list:
        """A list of (width, height) tuples, one for each Deep Zoom level."""
        return self._level_dimensions.copy()
    
    @property
    def tile_count(self) -> int:
        """The total number of Deep Zoom tiles in the image."""
        if not self._level_dimensions:
            return 0
        
        total = 0
        for width, height in self._level_dimensions:
            cols = int(math.ceil(width / self._tile_size))
            rows = int(math.ceil(height / self._tile_size))
            total += cols * rows
        
        return total
    
    def get_tile_count(self, level: int) -> Tuple[int, int]:
        """
        Return the number of tiles in the specified level.
        
        Args:
            level: Deep Zoom level
            
        Returns:
            (columns, rows) tuple
        """
        if level < 0 or level >= self._level_count:
            raise ValueError(f"Invalid level {level}")
        
        width, height = self._level_dimensions[level]
        cols = int(math.ceil(width / self._tile_size))
        rows = int(math.ceil(height / self._tile_size))
        
        return (cols, rows)
    
    def get_tile_dimensions(self, level: int, address: Tuple[int, int]) -> Tuple[int, int]:
        """
        Return the dimensions of the specified tile.
        
        Args:
            level: Deep Zoom level
            address: (column, row) tuple
            
        Returns:
            (width, height) tuple
        """
        if level < 0 or level >= self._level_count:
            raise ValueError(f"Invalid level {level}")
        
        col, row = address
        level_width, level_height = self._level_dimensions[level]
        
        # Calculate tile dimensions
        tile_width = min(self._tile_size, level_width - col * self._tile_size)
        tile_height = min(self._tile_size, level_height - row * self._tile_size)
        
        return (tile_width, tile_height)
    
    def get_tile(self, level: int, address: Tuple[int, int]) -> Image.Image:
        """
        Return a PIL.Image for the specified tile.
        
        Args:
            level: Deep Zoom level
            address: (column, row) tuple
            
        Returns:
            PIL Image
        """
        if level < 0 or level >= self._level_count:
            raise ValueError(f"Invalid level {level}")
        
        col, row = address
        
        # Get level dimensions
        level_width, level_height = self._level_dimensions[level]
        
        # Calculate tile position and size
        tile_x = col * self._tile_size
        tile_y = row * self._tile_size
        tile_width, tile_height = self.get_tile_dimensions(level, address)
        
        # Calculate the corresponding region in the original slide
        slide_width, slide_height = self.slide.dimensions
        
        # Scale factors
        scale_x = slide_width / level_width
        scale_y = slide_height / level_height
        
        # Calculate region in slide coordinates
        slide_x = int(tile_x * scale_x)
        slide_y = int(tile_y * scale_y)
        slide_w = int(tile_width * scale_x)
        slide_h = int(tile_height * scale_y)
        
        # Ensure we don't go beyond slide boundaries
        slide_x = min(slide_x, slide_width - 1)
        slide_y = min(slide_y, slide_height - 1)
        slide_w = min(slide_w, slide_width - slide_x)
        slide_h = min(slide_h, slide_height - slide_y)
        
        try:
            # Read the region from the slide
            # Use the best level for the current downsample
            downsample = max(scale_x, scale_y)
            slide_level = self.slide.get_best_level_for_downsample(downsample)
            
            # Read the region
            region = self.slide.read_region((slide_x, slide_y), slide_level, (slide_w, slide_h))
            
            # Resize to tile dimensions if necessary
            if region.size != (tile_width, tile_height):
                region = region.resize((tile_width, tile_height), Image.LANCZOS)
            
            return region
            
        except Exception as e:
            logger.error(f"Error generating tile at level {level}, address {address}: {e}")
            
            # Return a placeholder tile
            placeholder = Image.new('RGB', (tile_width, tile_height), (128, 128, 128))
            return placeholder
    
    def get_dzi(self, format: str = 'jpeg') -> str:
        """
        Return a string containing the XML metadata for the .dzi file.
        
        Args:
            format: Format of the individual tiles ('png' or 'jpeg')
            
        Returns:
            DZI XML string
        """
        if not self.slide.dimensions:
            raise ValueError("No slide dimensions available")
        
        width, height = self.slide.dimensions
        
        # Create XML structure
        image = Element('Image', 
                       TileSize=str(self._tile_size),
                       Overlap=str(self._overlap), 
                       Format=format,
                       xmlns='http://schemas.microsoft.com/deepzoom/2008')
        
        SubElement(image, 'Size', Width=str(width), Height=str(height))
        
        # Convert to string
        tree = ElementTree(element=image)
        buf = BytesIO()
        tree.write(buf, encoding='UTF-8', xml_declaration=True)
        
        return buf.getvalue().decode('UTF-8')
    
    def get_tile_data(self, level: int, address: Tuple[int, int], format: str = 'jpeg') -> bytes:
        """
        Return the tile data as bytes in the specified format.
        
        Args:
            level: Deep Zoom level
            address: (column, row) tuple
            format: Output format ('jpeg' or 'png')
            
        Returns:
            Tile data as bytes
        """
        tile = self.get_tile(level, address)
        
        # Convert to bytes
        buf = BytesIO()
        
        if format.lower() == 'png':
            tile.save(buf, 'PNG')
        else:
            # Default to JPEG
            if tile.mode == 'RGBA':
                # JPEG doesn't support transparency, convert to RGB
                background = Image.new('RGB', tile.size, (255, 255, 255))
                background.paste(tile, mask=tile.split()[-1] if tile.mode == 'RGBA' else None)
                tile = background
            elif tile.mode not in ['RGB', 'L']:
                tile = tile.convert('RGB')
            
            tile.save(buf, 'JPEG', quality=90)
        
        return buf.getvalue()

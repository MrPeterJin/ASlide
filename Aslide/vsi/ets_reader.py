"""
ETS (External Tile Storage) file reader for VSI format.
Based on Bio-Formats CellSensReader implementation.
Licensed under GPL v2+ (compatible with Bio-Formats license)
"""

import os
import struct
import logging
from typing import BinaryIO, Optional, Tuple, List
from PIL import Image
import numpy as np

from .vsi_decoder import VsiDecoder
from . import vsi_constants as const


logger = logging.getLogger(__name__)


class EtsReader:
    """Reader for ETS (External Tile Storage) files used by VSI format."""
    
    def __init__(self):
        self.decoder = VsiDecoder()
    
    def read_tile_from_ets(self, ets_file_path: str, tile_index: int = 0) -> Optional[Image.Image]:
        """
        Read a tile from an ETS file.
        
        Args:
            ets_file_path: Path to the ETS file
            tile_index: Index of the tile to read (usually 0 for single-tile ETS files)
            
        Returns:
            PIL Image or None if reading failed
        """
        if not os.path.exists(ets_file_path):
            logger.warning(f"ETS file not found: {ets_file_path}")
            return None
        
        try:
            with open(ets_file_path, 'rb') as f:
                return self._read_ets_tile(f, tile_index)
        except Exception as e:
            logger.error(f"Error reading ETS file {ets_file_path}: {e}")
            return None
    
    def _read_ets_tile(self, f: BinaryIO, tile_index: int) -> Optional[Image.Image]:
        """Read a tile from an open ETS file."""
        try:
            # ETS files typically contain TIFF-like data
            # Read the file header to determine format
            f.seek(0)
            header = f.read(16)
            
            if len(header) < 16:
                logger.warning("ETS file too small")
                return None
            
            # Check for TIFF magic bytes
            if header[:4] in [b'II*\x00', b'MM\x00*']:
                return self._read_tiff_from_ets(f)
            
            # Check for JPEG magic bytes
            elif header[:2] == b'\xff\xd8':
                return self._read_jpeg_from_ets(f)
            
            # Check for PNG magic bytes
            elif header[:8] == b'\x89PNG\r\n\x1a\n':
                return self._read_png_from_ets(f)
            
            # Try to read as raw data
            else:
                return self._read_raw_from_ets(f)
                
        except Exception as e:
            logger.error(f"Error reading ETS tile: {e}")
            return None
    
    def _read_tiff_from_ets(self, f: BinaryIO) -> Optional[Image.Image]:
        """Read TIFF data from ETS file."""
        try:
            f.seek(0)
            # Use PIL to read TIFF data
            img = Image.open(f)
            # Make a copy since we're closing the file
            return img.copy()
        except Exception as e:
            logger.error(f"Error reading TIFF from ETS: {e}")
            return None
    
    def _read_jpeg_from_ets(self, f: BinaryIO) -> Optional[Image.Image]:
        """Read JPEG data from ETS file."""
        try:
            f.seek(0)
            data = f.read()
            return self.decoder.decode_tile(data, const.JPEG, 0, 0)
        except Exception as e:
            logger.error(f"Error reading JPEG from ETS: {e}")
            return None
    
    def _read_png_from_ets(self, f: BinaryIO) -> Optional[Image.Image]:
        """Read PNG data from ETS file."""
        try:
            f.seek(0)
            data = f.read()
            return self.decoder.decode_tile(data, const.PNG, 0, 0)
        except Exception as e:
            logger.error(f"Error reading PNG from ETS: {e}")
            return None
    
    def _read_raw_from_ets(self, f: BinaryIO) -> Optional[Image.Image]:
        """Read raw data from ETS file."""
        try:
            f.seek(0)
            data = f.read()
            
            # Try to guess dimensions from file size
            file_size = len(data)
            
            # Common tile sizes
            common_sizes = [256, 512, 1024, 2048]
            
            for size in common_sizes:
                # Try RGB (3 bytes per pixel)
                if file_size == size * size * 3:
                    return self.decoder.decode_tile(data, const.RAW, size, size, const.UCHAR, 3)
                
                # Try grayscale (1 byte per pixel)
                elif file_size == size * size:
                    return self.decoder.decode_tile(data, const.RAW, size, size, const.UCHAR, 1)
                
                # Try 16-bit grayscale (2 bytes per pixel)
                elif file_size == size * size * 2:
                    return self.decoder.decode_tile(data, const.RAW, size, size, const.USHORT, 1)
            
            logger.warning(f"Could not determine dimensions for raw ETS data (size: {file_size})")
            return None
            
        except Exception as e:
            logger.error(f"Error reading raw data from ETS: {e}")
            return None
    
    def find_ets_files_for_pyramid(self, vsi_path: str, pyramid_index: int) -> List[str]:
        """
        Find ETS files associated with a specific pyramid.
        
        Args:
            vsi_path: Path to the main VSI file
            pyramid_index: Index of the pyramid/series
            
        Returns:
            List of ETS file paths
        """
        ets_files = []
        
        try:
            base_dir = os.path.dirname(vsi_path)
            base_name = os.path.splitext(os.path.basename(vsi_path))[0]
            
            # Look for the pixels directory
            pixels_dir = os.path.join(base_dir, f"_{base_name}_")
            if not os.path.exists(pixels_dir):
                return ets_files
            
            # Look for stack directories
            stack_pattern = f"stack{pyramid_index:05d}"
            stack_dir = os.path.join(pixels_dir, stack_pattern)
            
            if os.path.exists(stack_dir):
                # Scan for ETS files in the stack directory
                for filename in sorted(os.listdir(stack_dir)):
                    if filename.endswith('.ets'):
                        ets_files.append(os.path.join(stack_dir, filename))
            
            # Also check for alternative naming patterns
            for stack_dir_name in os.listdir(pixels_dir):
                stack_dir_path = os.path.join(pixels_dir, stack_dir_name)
                if os.path.isdir(stack_dir_path) and stack_dir_name.startswith('stack'):
                    for filename in sorted(os.listdir(stack_dir_path)):
                        if filename.endswith('.ets'):
                            full_path = os.path.join(stack_dir_path, filename)
                            if full_path not in ets_files:
                                ets_files.append(full_path)
        
        except OSError as e:
            logger.warning(f"Error scanning for ETS files: {e}")
        
        return ets_files
    
    def get_tile_coordinates_from_filename(self, ets_filename: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Extract tile coordinates from ETS filename.
        
        Args:
            ets_filename: Name of the ETS file (e.g., "frame_t_000_z_000_c_000.ets")
            
        Returns:
            (t, z, c, tile_index) tuple or None if parsing failed
        """
        try:
            # Remove extension
            name = os.path.splitext(ets_filename)[0]
            
            # Parse frame_t_XXX_z_YYY_c_ZZZ pattern
            if name.startswith('frame_'):
                parts = name.split('_')
                if len(parts) >= 6:
                    t = int(parts[2])
                    z = int(parts[4]) 
                    c = int(parts[6])
                    return (t, z, c, 0)
            
            # Parse other common patterns
            # tile_x_Y_z_Z.ets
            elif name.startswith('tile_'):
                parts = name.split('_')
                if len(parts) >= 4:
                    x = int(parts[2])
                    z = int(parts[4]) if len(parts) > 4 else 0
                    return (0, z, 0, x)
            
            return None
            
        except (ValueError, IndexError) as e:
            logger.debug(f"Could not parse ETS filename {ets_filename}: {e}")
            return None
    
    def read_tile_at_coordinates(self, vsi_path: str, pyramid_index: int, 
                               t: int = 0, z: int = 0, c: int = 0) -> Optional[Image.Image]:
        """
        Read a tile at specific coordinates.
        
        Args:
            vsi_path: Path to the main VSI file
            pyramid_index: Index of the pyramid/series
            t: Time index
            z: Z-stack index
            c: Channel index
            
        Returns:
            PIL Image or None if not found
        """
        ets_files = self.find_ets_files_for_pyramid(vsi_path, pyramid_index)
        
        for ets_file in ets_files:
            filename = os.path.basename(ets_file)
            coords = self.get_tile_coordinates_from_filename(filename)
            
            if coords and coords[0] == t and coords[1] == z and coords[2] == c:
                return self.read_tile_from_ets(ets_file)
        
        return None

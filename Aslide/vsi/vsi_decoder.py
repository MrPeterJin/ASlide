"""
VSI image decoder for handling compressed tile data.
Based on Bio-Formats CellSensReader implementation.
Licensed under GPL v2+ (compatible with Bio-Formats license)
"""

import io
import logging
from typing import BinaryIO, Optional, Tuple
from PIL import Image
import numpy as np

from . import vsi_constants as const


logger = logging.getLogger(__name__)


class VsiDecoder:
    """Decoder for VSI image data."""
    
    def __init__(self):
        self.supported_compressions = {
            const.RAW: self._decode_raw,
            const.JPEG: self._decode_jpeg,
            const.JPEG_2000: self._decode_jpeg2000,
            const.JPEG_LOSSLESS: self._decode_jpeg_lossless,
            const.PNG: self._decode_png,
            const.BMP: self._decode_bmp,
        }
    
    def decode_tile(self, data: bytes, compression: int, width: int, height: int, 
                   pixel_type: int = const.UCHAR, samples_per_pixel: int = 3) -> Optional[Image.Image]:
        """
        Decode a tile from compressed data.
        
        Args:
            data: Raw tile data
            compression: Compression type constant
            width: Tile width in pixels
            height: Tile height in pixels
            pixel_type: Pixel data type
            samples_per_pixel: Number of samples per pixel (1=grayscale, 3=RGB)
            
        Returns:
            PIL Image or None if decoding failed
        """
        if compression not in self.supported_compressions:
            logger.warning(f"Unsupported compression type: {compression}")
            return self._create_placeholder_tile(width, height, samples_per_pixel)
        
        try:
            decoder_func = self.supported_compressions[compression]
            return decoder_func(data, width, height, pixel_type, samples_per_pixel)
        except Exception as e:
            logger.error(f"Failed to decode tile with compression {compression}: {e}")
            return self._create_placeholder_tile(width, height, samples_per_pixel)
    
    def _decode_raw(self, data: bytes, width: int, height: int, 
                   pixel_type: int, samples_per_pixel: int) -> Optional[Image.Image]:
        """Decode raw uncompressed data."""
        try:
            # Calculate expected data size
            bytes_per_sample = self._get_bytes_per_sample(pixel_type)
            expected_size = width * height * samples_per_pixel * bytes_per_sample
            
            if len(data) < expected_size:
                logger.warning(f"Insufficient raw data: got {len(data)}, expected {expected_size}")
                return None
            
            # Convert to numpy array
            if pixel_type == const.UCHAR:
                dtype = np.uint8
            elif pixel_type == const.USHORT:
                dtype = np.uint16
            elif pixel_type == const.FLOAT:
                dtype = np.float32
            else:
                logger.warning(f"Unsupported pixel type for raw decode: {pixel_type}")
                return None
            
            # Reshape data
            img_array = np.frombuffer(data[:expected_size], dtype=dtype)
            
            if samples_per_pixel == 1:
                # Grayscale
                img_array = img_array.reshape((height, width))
                mode = 'L' if dtype == np.uint8 else 'I;16'
            elif samples_per_pixel == 3:
                # RGB
                img_array = img_array.reshape((height, width, 3))
                mode = 'RGB'
            elif samples_per_pixel == 4:
                # RGBA
                img_array = img_array.reshape((height, width, 4))
                mode = 'RGBA'
            else:
                logger.warning(f"Unsupported samples per pixel: {samples_per_pixel}")
                return None
            
            # Convert to PIL Image
            if dtype != np.uint8:
                # Convert to uint8 for PIL
                if dtype == np.uint16:
                    img_array = (img_array / 256).astype(np.uint8)
                elif dtype == np.float32:
                    img_array = (img_array * 255).astype(np.uint8)
                mode = 'L' if samples_per_pixel == 1 else 'RGB'
            
            return Image.fromarray(img_array, mode)
            
        except Exception as e:
            logger.error(f"Error decoding raw data: {e}")
            return None
    
    def _decode_jpeg(self, data: bytes, width: int, height: int, 
                    pixel_type: int, samples_per_pixel: int) -> Optional[Image.Image]:
        """Decode JPEG compressed data."""
        try:
            img = Image.open(io.BytesIO(data))
            
            # Ensure correct size
            if img.size != (width, height):
                img = img.resize((width, height), Image.LANCZOS)
            
            # Ensure correct mode
            if samples_per_pixel == 1 and img.mode != 'L':
                img = img.convert('L')
            elif samples_per_pixel == 3 and img.mode != 'RGB':
                img = img.convert('RGB')
            elif samples_per_pixel == 4 and img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            return img
            
        except Exception as e:
            logger.error(f"Error decoding JPEG data: {e}")
            return None
    
    def _decode_jpeg2000(self, data: bytes, width: int, height: int, 
                        pixel_type: int, samples_per_pixel: int) -> Optional[Image.Image]:
        """Decode JPEG 2000 compressed data."""
        try:
            # PIL supports JPEG 2000 if the plugin is available
            img = Image.open(io.BytesIO(data))
            
            if img.size != (width, height):
                img = img.resize((width, height), Image.LANCZOS)
            
            if samples_per_pixel == 1 and img.mode != 'L':
                img = img.convert('L')
            elif samples_per_pixel == 3 and img.mode != 'RGB':
                img = img.convert('RGB')
            
            return img
            
        except Exception as e:
            logger.error(f"Error decoding JPEG 2000 data: {e}")
            return None
    
    def _decode_jpeg_lossless(self, data: bytes, width: int, height: int, 
                             pixel_type: int, samples_per_pixel: int) -> Optional[Image.Image]:
        """Decode lossless JPEG compressed data."""
        # Lossless JPEG is more complex and may require specialized libraries
        logger.warning("Lossless JPEG decoding not fully implemented")
        return self._create_placeholder_tile(width, height, samples_per_pixel)
    
    def _decode_png(self, data: bytes, width: int, height: int, 
                   pixel_type: int, samples_per_pixel: int) -> Optional[Image.Image]:
        """Decode PNG compressed data."""
        try:
            img = Image.open(io.BytesIO(data))
            
            if img.size != (width, height):
                img = img.resize((width, height), Image.LANCZOS)
            
            if samples_per_pixel == 1 and img.mode != 'L':
                img = img.convert('L')
            elif samples_per_pixel == 3 and img.mode != 'RGB':
                img = img.convert('RGB')
            elif samples_per_pixel == 4 and img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            return img
            
        except Exception as e:
            logger.error(f"Error decoding PNG data: {e}")
            return None
    
    def _decode_bmp(self, data: bytes, width: int, height: int, 
                   pixel_type: int, samples_per_pixel: int) -> Optional[Image.Image]:
        """Decode BMP compressed data."""
        try:
            img = Image.open(io.BytesIO(data))
            
            if img.size != (width, height):
                img = img.resize((width, height), Image.LANCZOS)
            
            if samples_per_pixel == 1 and img.mode != 'L':
                img = img.convert('L')
            elif samples_per_pixel == 3 and img.mode != 'RGB':
                img = img.convert('RGB')
            
            return img
            
        except Exception as e:
            logger.error(f"Error decoding BMP data: {e}")
            return None
    
    def _get_bytes_per_sample(self, pixel_type: int) -> int:
        """Get the number of bytes per sample for a pixel type."""
        if pixel_type in [const.CHAR, const.UCHAR]:
            return 1
        elif pixel_type in [const.SHORT, const.USHORT]:
            return 2
        elif pixel_type in [const.INT, const.UINT, const.FLOAT]:
            return 4
        elif pixel_type in [const.LONG, const.ULONG, const.DOUBLE]:
            return 8
        else:
            logger.warning(f"Unknown pixel type: {pixel_type}")
            return 1
    
    def _create_placeholder_tile(self, width: int, height: int, samples_per_pixel: int) -> Image.Image:
        """Create a placeholder tile when decoding fails."""
        if samples_per_pixel == 1:
            # Grayscale placeholder
            img_array = np.full((height, width), 128, dtype=np.uint8)
            return Image.fromarray(img_array, 'L')
        else:
            # RGB placeholder with a pattern
            img_array = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Create a checkerboard pattern
            for i in range(height):
                for j in range(width):
                    if (i // 8 + j // 8) % 2:
                        img_array[i, j] = [200, 200, 200]  # Light gray
                    else:
                        img_array[i, j] = [100, 100, 100]  # Dark gray
            
            return Image.fromarray(img_array, 'RGB')

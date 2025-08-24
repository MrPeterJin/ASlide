"""
Embedded TIFF reader for VSI format.
Based on Bio-Formats CellSensReader implementation.
Licensed under GPL v2+ (compatible with Bio-Formats license)
"""

import os
import struct
import logging
from typing import BinaryIO, Optional, Tuple, List, Dict, Any
from PIL import Image
import numpy as np

from .vsi_decoder import VsiDecoder
from . import vsi_constants as const


logger = logging.getLogger(__name__)


class TiffReader:
    """Reader for embedded TIFF data in VSI files."""
    
    def __init__(self):
        self.decoder = VsiDecoder()
    
    def read_tiff_from_vsi(self, vsi_file_path: str, ifd_offset: int) -> Optional[Image.Image]:
        """
        Read TIFF data from VSI file at specified IFD offset.
        
        Args:
            vsi_file_path: Path to the VSI file
            ifd_offset: Offset to the TIFF IFD
            
        Returns:
            PIL Image or None if reading failed
        """
        try:
            with open(vsi_file_path, 'rb') as f:
                return self._read_tiff_ifd(f, ifd_offset)
        except Exception as e:
            logger.error(f"Error reading TIFF from VSI file {vsi_file_path}: {e}")
            return None
    
    def _read_tiff_ifd(self, f: BinaryIO, offset: int) -> Optional[Image.Image]:
        """Read TIFF Image File Directory and extract image data."""
        try:
            f.seek(offset)
            
            # Read number of directory entries
            num_entries_data = f.read(2)
            if len(num_entries_data) < 2:
                return None
            
            num_entries = struct.unpack('<H', num_entries_data)[0]
            
            # Read directory entries
            tiff_tags = {}
            for _ in range(num_entries):
                entry_data = f.read(12)
                if len(entry_data) < 12:
                    break
                
                tag, data_type, count, value_offset = struct.unpack('<HHII', entry_data)
                tiff_tags[tag] = {
                    'type': data_type,
                    'count': count,
                    'value': value_offset
                }
            
            # Extract essential TIFF tags
            width = self._get_tiff_tag_value(f, tiff_tags, 256)  # ImageWidth
            height = self._get_tiff_tag_value(f, tiff_tags, 257)  # ImageLength
            bits_per_sample = self._get_tiff_tag_value(f, tiff_tags, 258, default=8)  # BitsPerSample
            compression = self._get_tiff_tag_value(f, tiff_tags, 259, default=1)  # Compression
            photometric = self._get_tiff_tag_value(f, tiff_tags, 262, default=1)  # PhotometricInterpretation
            samples_per_pixel = self._get_tiff_tag_value(f, tiff_tags, 277, default=1)  # SamplesPerPixel
            
            # Get strip/tile information
            strip_offsets = self._get_tiff_tag_array(f, tiff_tags, 273)  # StripOffsets
            strip_byte_counts = self._get_tiff_tag_array(f, tiff_tags, 279)  # StripByteCounts
            
            if not strip_offsets or not strip_byte_counts:
                # Try tile-based TIFF
                tile_offsets = self._get_tiff_tag_array(f, tiff_tags, 324)  # TileOffsets
                tile_byte_counts = self._get_tiff_tag_array(f, tiff_tags, 325)  # TileByteCounts
                tile_width = self._get_tiff_tag_value(f, tiff_tags, 322, default=256)  # TileWidth
                tile_height = self._get_tiff_tag_value(f, tiff_tags, 323, default=256)  # TileLength
                
                if tile_offsets and tile_byte_counts:
                    return self._read_tiled_tiff(f, width, height, tile_offsets, tile_byte_counts,
                                               tile_width, tile_height, compression, bits_per_sample,
                                               samples_per_pixel, photometric)
            else:
                # Strip-based TIFF
                return self._read_stripped_tiff(f, width, height, strip_offsets, strip_byte_counts,
                                              compression, bits_per_sample, samples_per_pixel, photometric)
            
            logger.warning("No valid strip or tile data found in TIFF")
            return None
            
        except Exception as e:
            logger.error(f"Error reading TIFF IFD: {e}")
            return None
    
    def _get_tiff_tag_value(self, f: BinaryIO, tags: Dict[int, Dict], tag: int, default: Any = None) -> Any:
        """Get a single value from a TIFF tag."""
        if tag not in tags:
            return default
        
        tag_info = tags[tag]
        data_type = tag_info['type']
        count = tag_info['count']
        value = tag_info['value']
        
        # For single values that fit in 4 bytes, value is stored directly
        if count == 1 and data_type in [1, 3, 4]:  # BYTE, SHORT, LONG
            if data_type == 1:  # BYTE
                return value & 0xFF
            elif data_type == 3:  # SHORT
                return value & 0xFFFF
            else:  # LONG
                return value
        
        # For larger values, need to read from offset
        try:
            current_pos = f.tell()
            f.seek(value)
            
            if data_type == 1:  # BYTE
                data = f.read(count)
                result = struct.unpack(f'<{count}B', data)[0] if count == 1 else struct.unpack(f'<{count}B', data)
            elif data_type == 3:  # SHORT
                data = f.read(count * 2)
                result = struct.unpack(f'<{count}H', data)[0] if count == 1 else struct.unpack(f'<{count}H', data)
            elif data_type == 4:  # LONG
                data = f.read(count * 4)
                result = struct.unpack(f'<{count}I', data)[0] if count == 1 else struct.unpack(f'<{count}I', data)
            else:
                result = default
            
            f.seek(current_pos)
            return result
            
        except Exception as e:
            logger.debug(f"Error reading TIFF tag {tag}: {e}")
            return default
    
    def _get_tiff_tag_array(self, f: BinaryIO, tags: Dict[int, Dict], tag: int) -> Optional[List[int]]:
        """Get an array of values from a TIFF tag."""
        if tag not in tags:
            return None
        
        tag_info = tags[tag]
        data_type = tag_info['type']
        count = tag_info['count']
        value = tag_info['value']
        
        if count == 0:
            return None
        
        try:
            # For arrays, value is always an offset
            current_pos = f.tell()
            f.seek(value)
            
            if data_type == 4:  # LONG
                data = f.read(count * 4)
                result = list(struct.unpack(f'<{count}I', data))
            elif data_type == 3:  # SHORT
                data = f.read(count * 2)
                result = list(struct.unpack(f'<{count}H', data))
            else:
                result = None
            
            f.seek(current_pos)
            return result
            
        except Exception as e:
            logger.debug(f"Error reading TIFF tag array {tag}: {e}")
            return None
    
    def _read_stripped_tiff(self, f: BinaryIO, width: int, height: int, 
                          strip_offsets: List[int], strip_byte_counts: List[int],
                          compression: int, bits_per_sample: int, 
                          samples_per_pixel: int, photometric: int) -> Optional[Image.Image]:
        """Read strip-based TIFF data."""
        try:
            # Read all strips and concatenate
            image_data = b''
            
            for offset, byte_count in zip(strip_offsets, strip_byte_counts):
                f.seek(offset)
                strip_data = f.read(byte_count)
                
                if compression == 1:  # No compression
                    image_data += strip_data
                else:
                    # Decode compressed strip
                    decoded_strip = self._decode_compressed_data(strip_data, compression, 
                                                               width, height // len(strip_offsets),
                                                               bits_per_sample, samples_per_pixel)
                    if decoded_strip:
                        image_data += decoded_strip
            
            # Convert to PIL Image
            return self._create_image_from_data(image_data, width, height, 
                                              bits_per_sample, samples_per_pixel, photometric)
            
        except Exception as e:
            logger.error(f"Error reading stripped TIFF: {e}")
            return None
    
    def _read_tiled_tiff(self, f: BinaryIO, width: int, height: int,
                        tile_offsets: List[int], tile_byte_counts: List[int],
                        tile_width: int, tile_height: int, compression: int,
                        bits_per_sample: int, samples_per_pixel: int, photometric: int) -> Optional[Image.Image]:
        """Read tile-based TIFF data."""
        try:
            # Calculate tile grid
            tiles_across = (width + tile_width - 1) // tile_width
            tiles_down = (height + tile_height - 1) // tile_height
            
            # Create output image
            if samples_per_pixel == 1:
                mode = 'L'
                img_array = np.zeros((height, width), dtype=np.uint8)
            else:
                mode = 'RGB'
                img_array = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Read and place tiles
            for tile_idx, (offset, byte_count) in enumerate(zip(tile_offsets, tile_byte_counts)):
                tile_x = (tile_idx % tiles_across) * tile_width
                tile_y = (tile_idx // tiles_across) * tile_height
                
                f.seek(offset)
                tile_data = f.read(byte_count)
                
                # Decode tile
                if compression == 1:  # No compression
                    tile_image = self._create_image_from_data(tile_data, tile_width, tile_height,
                                                            bits_per_sample, samples_per_pixel, photometric)
                else:
                    decoded_data = self._decode_compressed_data(tile_data, compression,
                                                              tile_width, tile_height,
                                                              bits_per_sample, samples_per_pixel)
                    if decoded_data:
                        tile_image = self._create_image_from_data(decoded_data, tile_width, tile_height,
                                                                bits_per_sample, samples_per_pixel, photometric)
                    else:
                        continue
                
                if tile_image:
                    # Place tile in output image
                    tile_array = np.array(tile_image)
                    end_x = min(tile_x + tile_width, width)
                    end_y = min(tile_y + tile_height, height)
                    
                    if samples_per_pixel == 1:
                        img_array[tile_y:end_y, tile_x:end_x] = tile_array[:end_y-tile_y, :end_x-tile_x]
                    else:
                        img_array[tile_y:end_y, tile_x:end_x] = tile_array[:end_y-tile_y, :end_x-tile_x]
            
            return Image.fromarray(img_array, mode)
            
        except Exception as e:
            logger.error(f"Error reading tiled TIFF: {e}")
            return None
    
    def _decode_compressed_data(self, data: bytes, compression: int, width: int, height: int,
                              bits_per_sample: int, samples_per_pixel: int) -> Optional[bytes]:
        """Decode compressed tile/strip data."""
        try:
            if compression == 1:  # No compression
                return data
            elif compression == 5:  # LZW
                logger.warning("LZW compression not implemented")
                return None
            elif compression == 7:  # JPEG
                # Use decoder to handle JPEG
                img = self.decoder.decode_tile(data, const.JPEG, width, height, 
                                             const.UCHAR, samples_per_pixel)
                if img:
                    return np.array(img).tobytes()
            elif compression == 8:  # Deflate
                import zlib
                return zlib.decompress(data)
            else:
                logger.warning(f"Unsupported compression: {compression}")
                return None
        except Exception as e:
            logger.error(f"Error decoding compressed data: {e}")
            return None
    
    def _create_image_from_data(self, data: bytes, width: int, height: int,
                              bits_per_sample: int, samples_per_pixel: int, 
                              photometric: int) -> Optional[Image.Image]:
        """Create PIL Image from raw image data."""
        try:
            if bits_per_sample == 8:
                dtype = np.uint8
            elif bits_per_sample == 16:
                dtype = np.uint16
            else:
                logger.warning(f"Unsupported bits per sample: {bits_per_sample}")
                return None
            
            # Calculate expected data size
            expected_size = width * height * samples_per_pixel * (bits_per_sample // 8)
            if len(data) < expected_size:
                logger.warning(f"Insufficient data: got {len(data)}, expected {expected_size}")
                return None
            
            # Create numpy array
            img_array = np.frombuffer(data[:expected_size], dtype=dtype)
            
            if samples_per_pixel == 1:
                img_array = img_array.reshape((height, width))
                mode = 'L'
            elif samples_per_pixel == 3:
                img_array = img_array.reshape((height, width, 3))
                mode = 'RGB'
            elif samples_per_pixel == 4:
                img_array = img_array.reshape((height, width, 4))
                mode = 'RGBA'
            else:
                logger.warning(f"Unsupported samples per pixel: {samples_per_pixel}")
                return None
            
            # Handle photometric interpretation
            if photometric == 0:  # WhiteIsZero
                img_array = 255 - img_array if dtype == np.uint8 else 65535 - img_array
            
            # Convert to 8-bit if needed
            if dtype == np.uint16:
                img_array = (img_array / 256).astype(np.uint8)
                
            return Image.fromarray(img_array, mode)
            
        except Exception as e:
            logger.error(f"Error creating image from data: {e}")
            return None

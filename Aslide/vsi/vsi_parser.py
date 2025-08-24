"""
VSI file parser implementation.
Based on Bio-Formats CellSensReader implementation.
Licensed under GPL v2+ (compatible with Bio-Formats license)
"""

import os
import struct
import logging
from typing import BinaryIO, Optional, Dict, Any, List, Tuple
from datetime import datetime

from . import vsi_constants as const
from .vsi_structures import VsiMetadata, Pyramid, TileCoordinate


logger = logging.getLogger(__name__)


class VsiParser:
    """Parser for VSI file format."""
    
    def __init__(self):
        self.metadata = VsiMetadata()
        self._current_pyramid: Optional[Pyramid] = None
        self._little_endian = True
        self._current_tile_coordinate: Optional[TileCoordinate] = None
        self._current_tile_index = 0
        self._current_level = 0
        self._in_tile_system = False
        self._in_external_data = False
        
    def parse_vsi_file(self, file_path: str) -> VsiMetadata:
        """Parse a VSI file and extract metadata."""
        logger.info(f"Parsing VSI file: {file_path}")
        
        with open(file_path, 'rb') as f:
            # Check if this is a valid VSI file
            if not self._is_valid_vsi_file(f):
                raise ValueError("Not a valid VSI file")
            
            # Parse the file structure
            f.seek(8)  # Skip header
            self._read_tags(f, False, "")
            
            # Find associated files
            self._find_associated_files(file_path)
            
        return self.metadata
    
    def _is_valid_vsi_file(self, f: BinaryIO) -> bool:
        """Check if the file is a valid VSI file."""
        f.seek(0)

        # Read the first 32 bytes to check for VSI signature
        header = f.read(32)
        if len(header) < 32:
            return False

        # Check for VSI magic bytes and structure
        # VSI files start with a specific tag structure
        try:
            # Try to read the first tag
            tag, field_type, next_field, data_size = struct.unpack('<IIII', header[:16])

            # Basic validation - check if values are reasonable
            if data_size > 1024 * 1024 * 100:  # 100MB max for first tag
                return False

            if field_type > 10000:  # Reasonable field type range
                return False

            # Check if we can read some basic VSI tags
            f.seek(0)
            return self._check_vsi_tags(f)

        except struct.error:
            return False

    def _check_vsi_tags(self, f: BinaryIO) -> bool:
        """Check if file contains valid VSI tags."""
        try:
            # Try to read a few tags to validate structure
            for _ in range(10):  # Check first 10 tags
                tag_data = f.read(32)
                if len(tag_data) < 32:
                    break

                tag, field_type, next_field, data_size = struct.unpack('<IIII', tag_data[:16])

                # Skip the data
                if data_size > 0:
                    f.seek(data_size, 1)

                # Check for known VSI tags
                if tag in [const.COLLECTION_VOLUME, const.MULTIDIM_IMAGE_VOLUME,
                          const.IMAGE_FRAME_VOLUME, const.DOCUMENT_PROPERTIES]:
                    return True

                # Move to next tag
                if next_field == 0:
                    break

                current_pos = f.tell()
                f.seek(current_pos - 32 + next_field)

            return False

        except (struct.error, OSError):
            return False
    
    def _find_associated_files(self, vsi_path: str) -> None:
        """Find associated ETS files and other related files."""
        base_dir = os.path.dirname(vsi_path)
        base_name = os.path.splitext(os.path.basename(vsi_path))[0]
        
        # Add the main VSI file
        self.metadata.used_files.append(vsi_path)
        
        # Look for associated directory
        pixels_dir = os.path.join(base_dir, f"_{base_name}_")
        if os.path.exists(pixels_dir):
            self._scan_pixels_directory(pixels_dir)
    
    def _scan_pixels_directory(self, pixels_dir: str) -> None:
        """Scan the pixels directory for ETS files."""
        try:
            for stack_dir_name in sorted(os.listdir(pixels_dir)):
                stack_dir_path = os.path.join(pixels_dir, stack_dir_name)
                if os.path.isdir(stack_dir_path):
                    self._scan_stack_directory(stack_dir_path)
        except OSError as e:
            logger.warning(f"Could not scan pixels directory {pixels_dir}: {e}")
    
    def _scan_stack_directory(self, stack_dir: str) -> None:
        """Scan a stack directory for frame files."""
        try:
            for file_name in sorted(os.listdir(stack_dir)):
                file_path = os.path.join(stack_dir, file_name)
                if file_name.endswith('.ets') and file_name.startswith('frame_'):
                    self.metadata.used_files.append(file_path)
                else:
                    self.metadata.extra_files.append(file_path)
        except OSError as e:
            logger.warning(f"Could not scan stack directory {stack_dir}: {e}")
    
    def _read_tags(self, f: BinaryIO, populate_metadata: bool, tag_prefix: str) -> None:
        """Read and parse VSI tags from the file."""
        try:
            while True:
                # Read tag header
                tag_data = f.read(32)
                if len(tag_data) < 32:
                    break
                
                # Parse tag header
                tag, field_type, next_field, data_size = struct.unpack('<IIII', tag_data[:16])
                fp = f.tell() - 32
                
                # Handle different field types
                value = self._read_tag_value(f, field_type, data_size, tag)
                
                # Process the tag
                logger.debug(f"Processing tag {tag} with value {value}")
                self._process_tag(tag, value, tag_prefix, populate_metadata)
                
                # Move to next field
                if next_field == 0 or tag == -494804095:  # End marker
                    if fp + data_size + 32 < self._get_file_size(f) and fp + data_size >= 0:
                        f.seek(fp + data_size + 32)
                    break
                
                if fp + next_field < self._get_file_size(f) and fp + next_field >= 0:
                    f.seek(fp + next_field)
                else:
                    break
                    
        except Exception as e:
            logger.debug(f"Failed to read all tags: {e}")
    
    def _get_file_size(self, f: BinaryIO) -> int:
        """Get the size of the file."""
        current_pos = f.tell()
        f.seek(0, 2)  # Seek to end
        size = f.tell()
        f.seek(current_pos)  # Restore position
        return size
    
    def _read_tag_value(self, f: BinaryIO, field_type: int, data_size: int, tag: int) -> Any:
        """Read the value of a tag based on its field type."""
        if data_size == 0:
            return None
            
        try:
            if field_type in [const.CHAR, const.UCHAR]:
                return struct.unpack('<B', f.read(1))[0]
            elif field_type in [const.SHORT, const.USHORT]:
                return struct.unpack('<H', f.read(2))[0]
            elif field_type in [const.INT, const.UINT, const.DWORD]:
                return struct.unpack('<I', f.read(4))[0]
            elif field_type in [const.LONG, const.ULONG]:
                return struct.unpack('<Q', f.read(8))[0]
            elif field_type == const.FLOAT:
                return struct.unpack('<f', f.read(4))[0]
            elif field_type == const.DOUBLE:
                return struct.unpack('<d', f.read(8))[0]
            elif field_type == const.BOOLEAN:
                return struct.unpack('<B', f.read(1))[0] != 0
            elif field_type in [const.TCHAR, const.UNICODE_TCHAR]:
                data = f.read(data_size)
                if field_type == const.UNICODE_TCHAR:
                    # Unicode string
                    return data.decode('utf-16le', errors='ignore').rstrip('\x00')
                else:
                    # ASCII string
                    return data.decode('ascii', errors='ignore').rstrip('\x00')
            elif field_type in [const.INT_2, const.INT_3, const.INT_4, const.INT_RECT,
                               const.INT_ARRAY_2, const.INT_ARRAY_3, const.INT_ARRAY_4, const.INT_ARRAY_5]:
                n_values = data_size // 4
                values = struct.unpack(f'<{n_values}I', f.read(data_size))
                return values
            elif field_type in [const.DOUBLE_2, const.DOUBLE_3, const.DOUBLE_4, const.DOUBLE_RECT,
                               const.DOUBLE_ARRAY_2, const.DOUBLE_ARRAY_3]:
                n_values = data_size // 8
                values = struct.unpack(f'<{n_values}d', f.read(data_size))
                return values
            elif field_type == const.RGB:
                r, g, b = struct.unpack('<BBB', f.read(3))
                return (r, g, b)
            elif field_type == const.BGR:
                b, g, r = struct.unpack('<BBB', f.read(3))
                return (r, g, b)
            else:
                # Unknown field type, read as raw bytes
                return f.read(data_size)
                
        except struct.error as e:
            logger.warning(f"Error reading tag {tag} with field type {field_type}: {e}")
            f.read(data_size)  # Skip the data
            return None
    
    def _process_tag(self, tag: int, value: Any, tag_prefix: str, populate_metadata: bool) -> None:
        """Process a parsed tag and update metadata."""
        if value is None:
            return

        # Store previous tag for context
        self.metadata.previous_tag = tag

        # Handle volume tags that create new pyramids
        if tag in [const.MULTIDIM_IMAGE_VOLUME, const.IMAGE_FRAME_VOLUME, const.COLLECTION_VOLUME]:
            # Only create a new pyramid if we don't have one yet or if this is a new volume
            if self._current_pyramid is None or tag != const.COLLECTION_VOLUME:
                logger.debug(f"Creating new pyramid for tag {tag}")
                self._current_pyramid = Pyramid()
                self.metadata.pyramids.append(self._current_pyramid)
                self.metadata.metadata_index = len(self.metadata.pyramids) - 1

                # Initialize tile structures for this pyramid
                self.metadata.tile_offsets.append([])
                self.metadata.rows.append(0)
                self.metadata.cols.append(0)
                self.metadata.compression_type.append(const.RAW)
                self.metadata.tile_x.append(0)
                self.metadata.tile_y.append(0)
                self.metadata.tile_map.append([])
                self.metadata.n_dimensions.append(0)
                self.metadata.bgr.append(False)

                logger.debug(f"Created pyramid {len(self.metadata.pyramids)}, total pyramids: {len(self.metadata.pyramids)}")

        # Handle tile system tags
        elif tag == const.TILE_SYSTEM:
            self._in_tile_system = True

        # Handle external data tags
        elif tag == const.EXTERNAL_DATA_VOLUME:
            self._in_external_data = True

        # Handle dimension properties
        elif tag in [const.Z_START, const.Z_INCREMENT, const.Z_VALUE,
                    const.TIME_START, const.TIME_INCREMENT, const.TIME_VALUE,
                    const.LAMBDA_START, const.LAMBDA_INCREMENT, const.LAMBDA_VALUE]:
            self.metadata.in_dimension_properties = True
            self.metadata.dimension_tag = tag

        # Handle tile coordinates and offsets
        elif tag in [const.DIM_INDEX_1, const.DIM_INDEX_2]:
            if self._current_pyramid and isinstance(value, (list, tuple)):
                self._process_tile_coordinate(tag, value)

        # Handle TIFF IFD tags (embedded image data)
        elif tag == const.TIFF_IFD:
            if self._current_pyramid and isinstance(value, int):
                self._process_tiff_ifd(value)

        # Process specific tags
        if self._current_pyramid is not None:
            self._process_pyramid_tag(tag, value)

        # Handle global metadata
        self._process_global_tag(tag, value, tag_prefix, populate_metadata)

    def _process_tile_coordinate(self, tag: int, value: Any) -> None:
        """Process tile coordinate information."""
        if not self._current_pyramid:
            return

        pyramid_index = self.metadata.metadata_index
        if pyramid_index < 0 or pyramid_index >= len(self.metadata.tile_map):
            return

        try:
            if tag == const.DIM_INDEX_1:
                # Single dimension coordinate
                if isinstance(value, (int, float)):
                    coord = TileCoordinate(1)
                    coord.coordinate[0] = int(value)
                    self._current_tile_coordinate = coord

            elif tag == const.DIM_INDEX_2:
                # Two dimension coordinate
                if isinstance(value, (list, tuple)) and len(value) >= 2:
                    coord = TileCoordinate(2)
                    coord.coordinate[0] = int(value[0])
                    coord.coordinate[1] = int(value[1])
                    self._current_tile_coordinate = coord

            # Add coordinate to tile map
            if self._current_tile_coordinate:
                self.metadata.tile_map[pyramid_index].append(self._current_tile_coordinate)

        except (ValueError, TypeError, IndexError) as e:
            logger.debug(f"Error processing tile coordinate: {e}")

    def _process_tiff_ifd(self, offset: int) -> None:
        """Process TIFF IFD offset for embedded image data."""
        if not self._current_pyramid:
            return

        pyramid_index = self.metadata.metadata_index
        if pyramid_index < 0 or pyramid_index >= len(self.metadata.tile_offsets):
            return

        # Store the TIFF IFD offset
        self.metadata.tile_offsets[pyramid_index].append(offset)

        # Update tile count
        tile_count = len(self.metadata.tile_offsets[pyramid_index])

        # Estimate grid dimensions (this is a simplification)
        if tile_count == 1:
            self.metadata.rows[pyramid_index] = 1
            self.metadata.cols[pyramid_index] = 1
        else:
            # Try to determine grid layout from tile coordinates
            if self.metadata.tile_map[pyramid_index]:
                max_x = max(coord.coordinate[0] for coord in self.metadata.tile_map[pyramid_index] if len(coord.coordinate) > 0)
                max_y = max(coord.coordinate[1] for coord in self.metadata.tile_map[pyramid_index] if len(coord.coordinate) > 1)
                self.metadata.cols[pyramid_index] = max_x + 1
                self.metadata.rows[pyramid_index] = max_y + 1
            else:
                # Fallback: assume square grid
                grid_size = int(tile_count ** 0.5) + 1
                self.metadata.rows[pyramid_index] = grid_size
                self.metadata.cols[pyramid_index] = grid_size
    
    def _process_pyramid_tag(self, tag: int, value: Any) -> None:
        """Process tags that belong to the current pyramid."""
        pyramid = self._current_pyramid
        if pyramid is None:
            return
            
        try:
            if tag == const.STACK_NAME and value != "0":
                if pyramid.name is None:
                    pyramid.name = str(value)

                    # Check for common label naming patterns
                    value_lower = str(value).lower()
                    if any(pattern in value_lower for pattern in ['label', 'barcode', 'slide id', 'specimen']):
                        pyramid.name = "Label"
            elif tag == const.CHANNEL_NAME:
                pyramid.channel_names.append(str(value))
            elif tag == const.IMAGE_BOUNDARY and isinstance(value, tuple) and len(value) >= 4:
                if pyramid.width is None:
                    pyramid.width = value[2]
                    pyramid.height = value[3]
            elif tag == const.TILE_ORIGIN and isinstance(value, tuple) and len(value) >= 2:
                pyramid.tile_origin_x = value[0]
                pyramid.tile_origin_y = value[1]
            elif tag == const.RWC_FRAME_SCALE and isinstance(value, tuple) and len(value) >= 2:
                if pyramid.physical_size_x is None:
                    pyramid.physical_size_x = value[0]
                    pyramid.physical_size_y = value[1]
            elif tag == const.RWC_FRAME_ORIGIN and isinstance(value, tuple) and len(value) >= 2:
                if pyramid.origin_x is None:
                    pyramid.origin_x = value[0]
                    pyramid.origin_y = value[1]
            elif tag == const.OBJECTIVE_MAG:
                pyramid.magnification = float(value)
            elif tag == const.NUMERICAL_APERTURE:
                pyramid.numerical_aperture = float(value)
            elif tag == const.WORKING_DISTANCE:
                pyramid.working_distance = float(value)
            elif tag == const.OBJECTIVE_NAME:
                pyramid.objective_names.append(str(value))
            elif tag == const.OBJECTIVE_TYPE:
                pyramid.objective_types.append(int(value))
            elif tag == const.BIT_DEPTH:
                pyramid.bit_depth = int(value)
            elif tag == const.X_BINNING:
                pyramid.binning_x = int(value)
            elif tag == const.Y_BINNING:
                pyramid.binning_y = int(value)
            elif tag == const.CAMERA_GAIN:
                pyramid.gain = float(value)
            elif tag == const.CAMERA_OFFSET:
                pyramid.offset = float(value)
            elif tag == const.RED_GAIN:
                pyramid.red_gain = float(value)
            elif tag == const.GREEN_GAIN:
                pyramid.green_gain = float(value)
            elif tag == const.BLUE_GAIN:
                pyramid.blue_gain = float(value)
            elif tag == const.RED_OFFSET:
                pyramid.red_offset = float(value)
            elif tag == const.GREEN_OFFSET:
                pyramid.green_offset = float(value)
            elif tag == const.BLUE_OFFSET:
                pyramid.blue_offset = float(value)
            elif tag == const.EXPOSURE_TIME:
                pyramid.exposure_times.append(int(value))
            elif tag == const.CREATION_TIME:
                if pyramid.acquisition_time is None:
                    pyramid.acquisition_time = int(value)
            elif tag == const.REFRACTIVE_INDEX:
                pyramid.refractive_index = float(value)
            elif tag == const.DEVICE_NAME:
                pyramid.device_names.append(str(value))
            elif tag == const.DEVICE_ID:
                pyramid.device_ids.append(str(value))
            elif tag == const.DEVICE_MANUFACTURER:
                pyramid.device_manufacturers.append(str(value))
            elif tag == const.Z_START:
                pyramid.z_start = float(value)
            elif tag == const.Z_INCREMENT:
                pyramid.z_increment = float(value)
            elif tag == const.Z_VALUE:
                pyramid.z_values.append(float(value))
            elif tag == const.LAMBDA_VALUE:
                pyramid.channel_wavelengths.append(float(value))
            elif tag == const.STACK_TYPE:
                # Store stack type information
                stack_type = int(value)
                if stack_type == const.OVERVIEW_IMAGE:
                    pyramid.name = "Overview"
                elif stack_type == const.MACRO_IMAGE:
                    pyramid.name = "Macro"
                elif stack_type == const.SAMPLE_MASK:
                    pyramid.name = "Mask"
                elif stack_type == const.FOCUS_IMAGE:
                    pyramid.name = "Focus"
                elif stack_type == const.DEFAULT_IMAGE:
                    if pyramid.name is None:
                        pyramid.name = "Main"
            elif tag == const.DISPLAY_COLOR and isinstance(value, (list, tuple)) and len(value) >= 3:
                # Store channel display color
                if len(pyramid.channel_names) > 0:
                    # Associate color with the last added channel
                    channel_idx = len(pyramid.channel_names) - 1
                    color_key = f"channel_{channel_idx}_color"
                    pyramid.original_metadata[color_key] = f"rgb({value[0]},{value[1]},{value[2]})"
            elif tag == const.FRAME_ORIGIN and isinstance(value, (list, tuple)) and len(value) >= 2:
                # Physical origin in micrometers
                if pyramid.origin_x is None:
                    pyramid.origin_x = float(value[0])
                    pyramid.origin_y = float(value[1])
            elif tag == const.FRAME_SCALE and isinstance(value, (list, tuple)) and len(value) >= 2:
                # Physical scale in micrometers per pixel
                if pyramid.physical_size_x is None:
                    pyramid.physical_size_x = float(value[0])
                    pyramid.physical_size_y = float(value[1])
            elif tag == const.TILE_ORIGIN and isinstance(value, (list, tuple)) and len(value) >= 2:
                # Tile origin coordinates
                pyramid.tile_origin_x = int(value[0])
                pyramid.tile_origin_y = int(value[1])
            elif tag == const.EXTERNAL_FILE_PROPERTIES:
                # Mark that this pyramid has external ETS files
                pyramid.has_associated_ets_file = True

        except (ValueError, TypeError) as e:
            logger.debug(f"Error processing pyramid tag {tag}: {e}")
    
    def _process_global_tag(self, tag: int, value: Any, tag_prefix: str, populate_metadata: bool) -> None:
        """Process global tags that affect the entire file."""
        try:
            if tag == const.HAS_EXTERNAL_FILE:
                self.metadata.expect_ets = int(value) == 1

            elif tag == const.VERSION_NUMBER:
                # Store version information
                if populate_metadata and tag_prefix:
                    key = f"{tag_prefix}.version"
                else:
                    key = "vsi.version"
                if self._current_pyramid:
                    self._current_pyramid.original_metadata[key] = str(value)

            elif tag == const.DEFAULT_BACKGROUND_COLOR:
                # Store background color
                pyramid_index = self.metadata.metadata_index
                if pyramid_index >= 0 and isinstance(value, (list, tuple, bytes)):
                    self.metadata.background_color[pyramid_index] = bytes(value) if not isinstance(value, bytes) else value

            elif tag in [const.DOCUMENT_NAME, const.DOCUMENT_NOTE, const.DOCUMENT_AUTHOR,
                        const.DOCUMENT_COMPANY, const.DOCUMENT_CREATOR_NAME]:
                # Store document metadata
                if populate_metadata and self._current_pyramid:
                    tag_name = self._get_tag_name(tag)
                    if tag_name:
                        key = f"document.{tag_name}"
                        self._current_pyramid.original_metadata[key] = str(value)

            elif tag == const.JPEG:
                # Set JPEG flag
                self.metadata.jpeg = True

            elif tag in [const.COARSE_FRAME_IFD, const.DEFAULT_SAMPLE_IFD]:
                # Handle IFD references
                if isinstance(value, int) and value > 0:
                    self._process_tiff_ifd(value)

        except (ValueError, TypeError) as e:
            logger.debug(f"Error processing global tag {tag}: {e}")

    def _get_tag_name(self, tag: int) -> Optional[str]:
        """Get a human-readable name for a tag."""
        tag_names = {
            const.DOCUMENT_NAME: "name",
            const.DOCUMENT_NOTE: "note",
            const.DOCUMENT_AUTHOR: "author",
            const.DOCUMENT_COMPANY: "company",
            const.DOCUMENT_CREATOR_NAME: "creator_name",
            const.STACK_NAME: "stack_name",
            const.CHANNEL_NAME: "channel_name",
            const.OBJECTIVE_NAME: "objective_name",
            const.DEVICE_NAME: "device_name",
        }
        return tag_names.get(tag)

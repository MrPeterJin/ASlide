"""
IBL format reader for ASlide.

IBL Format Structure (苏州秉理 BingLi WSI format):
- SQLite 3.x database
- Magic number: "ibl" in tbl_base_info.magicNo
- tbl_base_info: Basic slide information (dimensions, tile size, layers)
- tbl_tile_info: Tile data (JPEG compressed)
  - Layer 0: 4x4 sub-tiles per image block (612x512 each, total 2448x2048)
  - Layer 1: 1 tile per image block (612x512, 4x downsample)
- tbl_shrink_info: Shrink layer tiles (layer 2, 16x downsample)
- tbl_img_info: Image block index (maps img_id to grid position)
- tbl_ext_info: Associated images (thumbnail, label, macro)
  - type 1: macro image (JPEG)
  - type 2: label image (JPEG)
  - type 3: thumbnail image (JPEG)
  - type 4: ROI data (JSON)
  - type 6: scan parameters (JSON)
"""

import sqlite3
import io
import os
from typing import Tuple, Dict, Optional, Any
from PIL import Image


class IblSlide:
    """
    IBL slide reader for 苏州秉理 (BingLi) WSI files.

    Supports:
    - Reading header information (dimensions, tile size)
    - Extracting thumbnail, label, and macro images
    - read_region for reading arbitrary regions
    - Multiple pyramid levels (layer 0, 1, 2)
    """

    # Sub-tile size (individual JPEG tiles in database)
    SUB_TILE_WIDTH = 612
    SUB_TILE_HEIGHT = 512
    
    # Sub-tiles per image block (4x4 grid)
    SUB_TILES_X = 4
    SUB_TILES_Y = 4
    
    # Image block size (composed of 4x4 sub-tiles)
    BLOCK_WIDTH = SUB_TILE_WIDTH * SUB_TILES_X   # 2448
    BLOCK_HEIGHT = SUB_TILE_HEIGHT * SUB_TILES_Y  # 2048

    # Associated image types in tbl_ext_info
    EXT_TYPE_MACRO = 1
    EXT_TYPE_LABEL = 2
    EXT_TYPE_THUMBNAIL = 3

    def __init__(self, filename: str):
        """Initialize IBL slide reader.

        Args:
            filename: Path to the IBL file
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"IBL file not found: {filename}")
        
        self._filename = filename
        self._closed = False
        
        # Open SQLite connection
        self._conn = sqlite3.connect(filename)
        self._conn.row_factory = sqlite3.Row
        self._cursor = self._conn.cursor()
        
        # Parse base info
        self._parse_base_info()
        
        # Build image block index
        self._build_img_index()
        
        # Cache properties
        self._init_properties()

    def _parse_base_info(self):
        """Parse basic slide information from tbl_base_info."""
        self._cursor.execute("SELECT * FROM tbl_base_info LIMIT 1")
        row = self._cursor.fetchone()
        
        if not row:
            raise ValueError("Invalid IBL file: no base info found")
        
        # Verify magic number
        if row['magicNo'] != 'ibl':
            raise ValueError(f"Invalid IBL file: expected magic 'ibl', got '{row['magicNo']}'")
        
        self._version = row['version']
        self._layer_count = row['layer_size']  # Usually 3
        self._ratio_step = row['ratio_step']   # Usually 4 (downsample factor between layers)
        self._total_width = int(row['total_img_width'])
        self._total_height = int(row['total_img_height'])
        self._tile_width = row['tile_width']   # 612
        self._tile_height = row['tile_height'] # 512
        self._img_width = row['img_width']     # 2448 (block width)
        self._img_height = row['img_height']   # 2048 (block height)
        self._img_col = row['img_col']         # Grid columns
        self._img_row = row['img_row']         # Grid rows
        self._pixel_size = float(row['pixel_size']) if row['pixel_size'] else 0.00025
        self._max_zoom = row['max_zoom_rate']
        
        # Calculate MPP (microns per pixel)
        # pixel_size is in mm, convert to microns
        self._mpp = self._pixel_size * 1000 if self._pixel_size > 0 else 0.25

    def _build_img_index(self):
        """Build image block index from tbl_img_info."""
        self._img_index = {}  # {img_id: {'col': col, 'row': row, 'nX': nX, 'nY': nY}}
        
        self._cursor.execute("""
            SELECT id, col, row, nX, nY 
            FROM tbl_img_info 
            WHERE layer = 0
        """)
        
        for row in self._cursor.fetchall():
            self._img_index[row['id']] = {
                'col': row['col'],
                'row': row['row'],
                'nX': row['nX'],
                'nY': row['nY']
            }

    def _init_properties(self):
        """Initialize cached properties."""
        self._properties = {
            'openslide.vendor': 'BingLi',
            'openslide.level-count': str(self.level_count),
            'openslide.mpp-x': str(self._mpp),
            'openslide.mpp-y': str(self._mpp),
            'openslide.objective-power': str(self._max_zoom),
            'ibl.version': self._version,
            'ibl.tile_width': str(self._tile_width),
            'ibl.tile_height': str(self._tile_height),
            'ibl.img_col': str(self._img_col),
            'ibl.img_row': str(self._img_row),
        }
        
        # Add level info
        for i, (w, h) in enumerate(self.level_dimensions):
            self._properties[f'openslide.level[{i}].width'] = str(w)
            self._properties[f'openslide.level[{i}].height'] = str(h)
            self._properties[f'openslide.level[{i}].downsample'] = str(self.level_downsamples[i])

    def _check_closed(self):
        """Check if slide is closed."""
        if self._closed:
            raise RuntimeError("Slide has been closed")

    @classmethod
    def detect_format(cls, filename: str) -> Optional[str]:
        """Detect if file is IBL format."""
        try:
            conn = sqlite3.connect(filename)
            cursor = conn.cursor()
            cursor.execute("SELECT magicNo FROM tbl_base_info LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row and row[0] == 'ibl':
                return "ibl"
        except Exception:
            pass
        return None

    @property
    def level_count(self) -> int:
        """Number of pyramid levels."""
        # IBL has 3 layers: layer 0 (full), layer 1 (4x), layer 2 (16x in shrink_info)
        return 3

    @property
    def dimensions(self) -> Tuple[int, int]:
        """Dimensions of level 0 (width, height)."""
        return (self._total_width, self._total_height)

    @property
    def level_dimensions(self) -> Tuple[Tuple[int, int], ...]:
        """Dimensions at each level."""
        return (
            (self._total_width, self._total_height),
            (self._total_width // self._ratio_step, self._total_height // self._ratio_step),
            (self._total_width // (self._ratio_step ** 2), self._total_height // (self._ratio_step ** 2)),
        )

    @property
    def level_downsamples(self) -> Tuple[float, ...]:
        """Downsample factor for each level."""
        return (1.0, float(self._ratio_step), float(self._ratio_step ** 2))

    @property
    def properties(self) -> Dict[str, Any]:
        """Slide properties."""
        return self._properties.copy()

    @property
    def associated_images(self) -> Dict[str, Image.Image]:
        """Associated images (thumbnail, label, macro)."""
        self._check_closed()
        result = {}

        for name, ext_type in [('thumbnail', self.EXT_TYPE_THUMBNAIL),
                                ('label', self.EXT_TYPE_LABEL),
                                ('macro', self.EXT_TYPE_MACRO)]:
            try:
                self._cursor.execute(
                    "SELECT data FROM tbl_ext_info WHERE type = ?", (ext_type,)
                )
                row = self._cursor.fetchone()
                if row and row['data']:
                    result[name] = Image.open(io.BytesIO(row['data']))
            except Exception:
                pass

        return result

    def get_thumbnail(self, size: Tuple[int, int]) -> Image.Image:
        """Get a thumbnail of the slide."""
        self._check_closed()

        # Try to get pre-stored thumbnail
        try:
            self._cursor.execute(
                "SELECT data FROM tbl_ext_info WHERE type = ?",
                (self.EXT_TYPE_THUMBNAIL,)
            )
            row = self._cursor.fetchone()
            if row and row['data']:
                thumb = Image.open(io.BytesIO(row['data']))
                thumb.thumbnail(size, Image.Resampling.LANCZOS)
                return thumb
        except Exception:
            pass

        # Fallback: read from lowest resolution level
        level = self.level_count - 1
        dims = self.level_dimensions[level]
        img = self.read_region((0, 0), level, dims)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        return img

    def get_best_level_for_downsample(self, downsample: float) -> int:
        """Get the best level for a given downsample factor."""
        for level, ds in enumerate(self.level_downsamples):
            if ds >= downsample:
                return level
        return self.level_count - 1

    def _get_tile_layer0(self, img_id: int, sub_col: int, sub_row: int) -> Optional[Image.Image]:
        """Get a sub-tile from layer 0.

        Args:
            img_id: Image block ID from tbl_img_info
            sub_col: Sub-tile column within the block (0-3)
            sub_row: Sub-tile row within the block (0-3)

        Returns:
            PIL Image of the sub-tile, or None if not found
        """
        self._cursor.execute("""
            SELECT data FROM tbl_tile_info
            WHERE layer = 0 AND id = ? AND col = ? AND row = ?
        """, (img_id, sub_col, sub_row))

        row = self._cursor.fetchone()
        if row and row['data']:
            try:
                return Image.open(io.BytesIO(row['data']))
            except Exception:
                pass
        return None

    def _get_tile_layer1(self, img_id: int) -> Optional[Image.Image]:
        """Get a tile from layer 1 (4x downsample).

        Args:
            img_id: Image block ID from tbl_img_info

        Returns:
            PIL Image of the tile, or None if not found
        """
        self._cursor.execute("""
            SELECT data FROM tbl_tile_info
            WHERE layer = 1 AND id = ?
        """, (img_id,))

        row = self._cursor.fetchone()
        if row and row['data']:
            try:
                return Image.open(io.BytesIO(row['data']))
            except Exception:
                pass
        return None

    def _get_tile_layer2(self, x: int, y: int) -> Optional[Image.Image]:
        """Get a tile from layer 2 (shrink layer, 16x downsample).

        Args:
            x: X coordinate in layer 2 coordinates
            y: Y coordinate in layer 2 coordinates

        Returns:
            PIL Image of the tile, or None if not found
        """
        self._cursor.execute("""
            SELECT data FROM tbl_shrink_info
            WHERE layerNo = 2 AND x = ? AND y = ?
        """, (x, y))

        row = self._cursor.fetchone()
        if row and row['data']:
            try:
                return Image.open(io.BytesIO(row['data']))
            except Exception:
                pass
        return None

    def _find_img_id_for_position(self, grid_col: int, grid_row: int) -> Optional[int]:
        """Find the image block ID for a given grid position.

        Args:
            grid_col: Column in the image grid
            grid_row: Row in the image grid

        Returns:
            Image block ID, or None if not found
        """
        for img_id, info in self._img_index.items():
            if info['col'] == grid_col and info['row'] == grid_row:
                return img_id
        return None

    def read_region(self, location: Tuple[int, int], level: int,
                    size: Tuple[int, int]) -> Image.Image:
        """Read a region from the slide.

        Args:
            location: (x, y) tuple of top-left corner in level 0 coordinates
            level: pyramid level to read from (0, 1, or 2)
            size: (width, height) tuple of the region size at the specified level

        Returns:
            PIL Image of the requested region (RGBA)
        """
        self._check_closed()

        if level < 0 or level >= self.level_count:
            raise ValueError(f"Invalid level: {level}")

        req_x, req_y = location
        width, height = size
        downsample = int(self.level_downsamples[level])

        # Create output image
        result = Image.new('RGBA', (width, height), (255, 255, 255, 0))

        if level == 0:
            self._read_region_layer0(result, req_x, req_y, width, height)
        elif level == 1:
            self._read_region_layer1(result, req_x, req_y, width, height, downsample)
        else:  # level == 2
            self._read_region_layer2(result, req_x, req_y, width, height, downsample)

        return result

    def _read_region_layer0(self, result: Image.Image, req_x: int, req_y: int,
                            width: int, height: int):
        """Read region from layer 0 (full resolution)."""
        # Calculate which image blocks and sub-tiles we need
        start_grid_col = req_x // self.BLOCK_WIDTH
        start_grid_row = req_y // self.BLOCK_HEIGHT
        end_grid_col = (req_x + width - 1) // self.BLOCK_WIDTH
        end_grid_row = (req_y + height - 1) // self.BLOCK_HEIGHT

        for grid_row in range(start_grid_row, end_grid_row + 1):
            for grid_col in range(start_grid_col, end_grid_col + 1):
                img_id = self._find_img_id_for_position(grid_col, grid_row)
                if img_id is None:
                    continue

                # Block top-left in level 0 coordinates
                block_x = grid_col * self.BLOCK_WIDTH
                block_y = grid_row * self.BLOCK_HEIGHT

                # Process each sub-tile in this block
                for sub_row in range(self.SUB_TILES_Y):
                    for sub_col in range(self.SUB_TILES_X):
                        # Sub-tile top-left in level 0 coordinates
                        tile_x = block_x + sub_col * self.SUB_TILE_WIDTH
                        tile_y = block_y + sub_row * self.SUB_TILE_HEIGHT

                        # Check if this tile overlaps with our request
                        if (tile_x + self.SUB_TILE_WIDTH <= req_x or
                            tile_x >= req_x + width or
                            tile_y + self.SUB_TILE_HEIGHT <= req_y or
                            tile_y >= req_y + height):
                            continue

                        # Load the sub-tile
                        tile_img = self._get_tile_layer0(img_id, sub_col, sub_row)
                        if tile_img is None:
                            continue

                        if tile_img.mode != 'RGBA':
                            tile_img = tile_img.convert('RGBA')

                        # Calculate intersection
                        inter_left = max(tile_x, req_x)
                        inter_top = max(tile_y, req_y)
                        inter_right = min(tile_x + self.SUB_TILE_WIDTH, req_x + width)
                        inter_bottom = min(tile_y + self.SUB_TILE_HEIGHT, req_y + height)

                        # Crop from tile
                        crop_left = inter_left - tile_x
                        crop_top = inter_top - tile_y
                        crop_right = inter_right - tile_x
                        crop_bottom = inter_bottom - tile_y
                        cropped = tile_img.crop((crop_left, crop_top, crop_right, crop_bottom))

                        # Paste to result
                        paste_x = inter_left - req_x
                        paste_y = inter_top - req_y
                        result.paste(cropped, (paste_x, paste_y))

    def _read_region_layer1(self, result: Image.Image, req_x: int, req_y: int,
                            width: int, height: int, downsample: int):
        """Read region from layer 1 (4x downsample)."""
        # Layer 1 tiles are 612x512, covering BLOCK_WIDTH x BLOCK_HEIGHT in level 0
        tile_coverage_x = self.BLOCK_WIDTH  # Area covered in level 0 coords
        tile_coverage_y = self.BLOCK_HEIGHT

        # Calculate grid range
        start_grid_col = req_x // tile_coverage_x
        start_grid_row = req_y // tile_coverage_y
        end_grid_col = (req_x + width * downsample - 1) // tile_coverage_x
        end_grid_row = (req_y + height * downsample - 1) // tile_coverage_y

        for grid_row in range(start_grid_row, end_grid_row + 1):
            for grid_col in range(start_grid_col, end_grid_col + 1):
                img_id = self._find_img_id_for_position(grid_col, grid_row)
                if img_id is None:
                    continue

                # Block top-left in level 0 coordinates
                block_x = grid_col * tile_coverage_x
                block_y = grid_row * tile_coverage_y

                # Load the tile
                tile_img = self._get_tile_layer1(img_id)
                if tile_img is None:
                    continue

                if tile_img.mode != 'RGBA':
                    tile_img = tile_img.convert('RGBA')

                # Calculate intersection in level 0 coords
                inter_left = max(block_x, req_x)
                inter_top = max(block_y, req_y)
                inter_right = min(block_x + tile_coverage_x, req_x + width * downsample)
                inter_bottom = min(block_y + tile_coverage_y, req_y + height * downsample)

                # Convert to tile-local coordinates (divide by downsample)
                crop_left = (inter_left - block_x) // downsample
                crop_top = (inter_top - block_y) // downsample
                crop_right = (inter_right - block_x) // downsample
                crop_bottom = (inter_bottom - block_y) // downsample

                # Clamp to tile size
                crop_right = min(crop_right, tile_img.width)
                crop_bottom = min(crop_bottom, tile_img.height)

                if crop_right <= crop_left or crop_bottom <= crop_top:
                    continue

                cropped = tile_img.crop((crop_left, crop_top, crop_right, crop_bottom))

                # Paste position in result
                paste_x = (inter_left - req_x) // downsample
                paste_y = (inter_top - req_y) // downsample
                result.paste(cropped, (paste_x, paste_y))

    def _read_region_layer2(self, result: Image.Image, req_x: int, req_y: int,
                            width: int, height: int, downsample: int):
        """Read region from layer 2 (shrink layer, 16x downsample)."""
        # Get all shrink tiles
        self._cursor.execute("SELECT x, y, data FROM tbl_shrink_info WHERE layerNo = 2")

        for row in self._cursor.fetchall():
            tile_x_level0 = row['x']  # These are level 0 coordinates
            tile_y_level0 = row['y']
            tile_data = row['data']

            if not tile_data:
                continue

            try:
                tile_img = Image.open(io.BytesIO(tile_data))
            except Exception:
                continue

            # Tile coverage in level 0 coords
            tile_coverage_x = tile_img.width * downsample
            tile_coverage_y = tile_img.height * downsample

            # Check overlap
            if (tile_x_level0 + tile_coverage_x <= req_x or
                tile_x_level0 >= req_x + width * downsample or
                tile_y_level0 + tile_coverage_y <= req_y or
                tile_y_level0 >= req_y + height * downsample):
                continue

            if tile_img.mode != 'RGBA':
                tile_img = tile_img.convert('RGBA')

            # Calculate intersection in level 0 coords
            inter_left = max(tile_x_level0, req_x)
            inter_top = max(tile_y_level0, req_y)
            inter_right = min(tile_x_level0 + tile_coverage_x, req_x + width * downsample)
            inter_bottom = min(tile_y_level0 + tile_coverage_y, req_y + height * downsample)

            # Convert to tile-local coordinates
            crop_left = (inter_left - tile_x_level0) // downsample
            crop_top = (inter_top - tile_y_level0) // downsample
            crop_right = (inter_right - tile_x_level0) // downsample
            crop_bottom = (inter_bottom - tile_y_level0) // downsample

            # Clamp to tile size
            crop_right = min(crop_right, tile_img.width)
            crop_bottom = min(crop_bottom, tile_img.height)

            if crop_right <= crop_left or crop_bottom <= crop_top:
                continue

            cropped = tile_img.crop((crop_left, crop_top, crop_right, crop_bottom))

            # Paste position in result
            paste_x = (inter_left - req_x) // downsample
            paste_y = (inter_top - req_y) // downsample
            result.paste(cropped, (paste_x, paste_y))

    def close(self):
        """Close the slide and free resources."""
        if self._closed:
            return

        try:
            if self._cursor:
                self._cursor.close()
                self._cursor = None
            if self._conn:
                self._conn.close()
                self._conn = None
        except Exception:
            pass
        finally:
            self._closed = True

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def __del__(self):
        """Destructor."""
        try:
            if not self._closed:
                self.close()
        except Exception:
            pass

    def __repr__(self):
        return f"IblSlide({self._filename!r})"
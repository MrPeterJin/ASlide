"""
Clean and efficient DeepZoom implementation for SDPC using the native SDPC SDK
"""

from io import BytesIO
import math
from PIL import Image
from xml.etree.ElementTree import ElementTree, Element, SubElement
try:
    from .sdpc_slide import SdpcSlide
except ImportError:
    from sdpc_slide import SdpcSlide


class DeepZoomGenerator:
    """
    Clean DeepZoom generator for SDPC slides using the new SDK.
    
    This implementation leverages the new SDK's:
    - Better memory management
    - Thread-safe operations
    - Efficient tile reading
    - Built-in level optimization
    """

    def __init__(self, slide, tile_size=254, overlap=1, limit_bounds=False):
        """
        Create a DeepZoomGenerator wrapping an SDPC slide.

        Args:
            slide: SdpcSlide object
            tile_size: Width and height of a single tile
            overlap: Extra pixels to add to each interior edge of a tile
            limit_bounds: True to render only the non-empty slide region
        """
        self.slide = slide
        self._tile_size = tile_size
        self._overlap = overlap
        self._limit_bounds = limit_bounds
        
        # Get slide dimensions
        self._l0_dimensions = slide.dimensions
        
        # Build DeepZoom pyramid
        self._build_pyramid()
        
        # Background color
        self._bg_color = '#ffffff'

    def _build_pyramid(self):
        """Build the DeepZoom level pyramid"""
        self._l_dimensions = self.slide.level_dimensions
        self._l0_offset = (0, 0)  # No offset for now
        self._l0_dimensions = self._l_dimensions[0]

        z_size = self._l0_dimensions
        z_dimensions = [z_size]
        while z_size[0] > 1 or z_size[1] > 1:
            z_size = tuple(max(1, int(math.ceil(z / 2))) for z in z_size)
            z_dimensions.append(z_size)

        # Reverse to get pyramid from small to large
        self._z_dimensions = tuple(reversed(z_dimensions))
        self._dz_levels = len(self._z_dimensions)

        # Tile counts (OpenSlide's method)
        def tiles(z_lim):
            return int(math.ceil(z_lim / self._tile_size))

        self._t_dimensions = tuple(
            (tiles(z_w), tiles(z_h)) for z_w, z_h in self._z_dimensions
        )

        # Total downsamples for each Deep Zoom level (OpenSlide's exact calculation)
        l0_z_downsamples = tuple(
            2 ** (self._dz_levels - dz_level - 1) for dz_level in range(self._dz_levels)
        )

        # Preferred slide levels for each Deep Zoom level
        self._slide_from_dz_level = tuple(
            self.slide.get_best_level_for_downsample(d) for d in l0_z_downsamples
        )

        # Piecewise downsamples (OpenSlide's exact calculation)
        self._l0_l_downsamples = self.slide.level_downsamples
        self._l_z_downsamples = tuple(
            l0_z_downsamples[dz_level]
            / self._l0_l_downsamples[self._slide_from_dz_level[dz_level]]
            for dz_level in range(self._dz_levels)
        )

    @property
    def level_count(self):
        """Number of DeepZoom levels"""
        return self._dz_levels

    @property
    def level_tiles(self):
        """List of (tiles_x, tiles_y) tuples for each level"""
        return self._t_dimensions

    @property
    def level_dimensions(self):
        """List of (pixels_x, pixels_y) tuples for each level"""
        return self._z_dimensions

    @property
    def tile_count(self):
        """Total number of tiles in the image"""
        return sum(t_cols * t_rows for t_cols, t_rows in self._t_dimensions)

    def _get_tile_info(self, dz_level, t_location):
        """
        Calculate tile parameters using OpenSlide's EXACT approach.

        Returns:
            tuple: ((l0_location, slide_level, l_size), z_size)
        """
        # Check parameters (exactly like OpenSlide)
        if dz_level < 0 or dz_level >= self._dz_levels:
            raise ValueError("Invalid level")
        for t, t_lim in zip(t_location, self._t_dimensions[dz_level]):
            if t < 0 or t >= t_lim:
                raise ValueError("Invalid address")

        # Get preferred slide level
        slide_level = self._slide_from_dz_level[dz_level]

        # Calculate top/left and bottom/right overlap (OpenSlide's exact logic)
        z_overlap_tl = tuple(self._overlap * int(t != 0) for t in t_location)
        z_overlap_br = tuple(
            self._overlap * int(t != t_lim - 1)
            for t, t_lim in zip(t_location, self.level_tiles[dz_level])
        )

        # Get final size of the tile (OpenSlide's exact calculation)
        z_size = tuple(
            min(self._tile_size, z_lim - self._tile_size * t) + z_tl + z_br
            for t, z_lim, z_tl, z_br in zip(
                t_location, self._z_dimensions[dz_level], z_overlap_tl, z_overlap_br
            )
        )

        # Obtain the region coordinates (OpenSlide's exact method)
        z_location = [self._z_from_t(t) for t in t_location]
        l_location = [
            self._l_from_z(dz_level, z - z_tl)
            for z, z_tl in zip(z_location, z_overlap_tl)
        ]
        # Round location down and size up, and add offset of active area
        l0_location = tuple(
            int(self._l0_from_l(slide_level, l) + l0_off)
            for l, l0_off in zip(l_location, self._l0_offset)
        )
        l_size = tuple(
            max(1, int(min(math.ceil(self._l_from_z(dz_level, dz)), l_lim - math.ceil(l))))
            for l, dz, l_lim in zip(l_location, z_size, self._l_dimensions[slide_level])
        )

        # Return read_region() parameters plus tile size for final scaling
        return ((l0_location, slide_level, l_size), z_size)

    def _l0_from_l(self, slide_level, l):
        """Convert slide level coordinate to level 0 coordinate"""
        return self.slide.level_downsamples[slide_level] * l

    def _l_from_z(self, dz_level, z):
        """Convert DeepZoom coordinate to slide level coordinate"""
        return self._l_z_downsamples[dz_level] * z

    def _z_from_t(self, t):
        """Convert tile coordinate to DeepZoom coordinate"""
        return self._tile_size * t

    def get_tile(self, level, address):
        """
        Get a tile as PIL Image using OpenSlide's standard approach.

        Args:
            level: DeepZoom level
            address: (col, row) tuple

        Returns:
            PIL Image
        """
        try:
            # Get tile parameters
            (l0_location, slide_level, l_size), z_size = self._get_tile_info(level, address)

            # Read the tile from slide
            tile = self.slide.read_region(l0_location, slide_level, l_size)

            # Apply on solid background (handle transparency safely)
            if tile.mode in ('RGBA', 'LA') or 'transparency' in tile.info:
                # Handle transparency properly
                bg = Image.new('RGB', tile.size, self._bg_color)
                if tile.mode == 'RGBA':
                    # Use alpha channel as mask
                    tile = Image.composite(tile.convert('RGB'), bg, tile.split()[-1])
                elif tile.mode == 'LA':
                    # Luminance + Alpha
                    rgb_tile = tile.convert('RGB')
                    tile = Image.composite(rgb_tile, bg, tile.split()[-1])
                else:
                    # Has transparency info but not RGBA/LA
                    tile = tile.convert('RGB')
            else:
                # No transparency, just ensure RGB mode
                tile = tile.convert('RGB')

            # Scale to correct size using thumbnail (more memory efficient)
            if tile.size != z_size:
                # Use thumbnail method like OpenSlide does
                tile.thumbnail(z_size, Image.Resampling.LANCZOS)

            return tile

        except Exception as e:
            # For any error (including transparency issues), return white tile
            print(f"Warning: Error getting tile at level {level}, address {address}: {e}")
            print(f"Returning white background tile instead.")
            return Image.new('RGB', (self._tile_size, self._tile_size), '#ffffff')



    def get_dzi(self, format='jpeg'):
        """
        Return XML metadata for the .dzi file.
        
        Args:
            format: Tile format ('png' or 'jpeg')
            
        Returns:
            str: DZI XML content
        """
        image = Element('Image', 
                       TileSize=str(self._tile_size),
                       Overlap=str(self._overlap), 
                       Format=format,
                       xmlns='http://schemas.microsoft.com/deepzoom/2008')
        
        w, h = self._l0_dimensions
        SubElement(image, 'Size', Width=str(w), Height=str(h))
        
        tree = ElementTree(element=image)
        buf = BytesIO()
        tree.write(buf, encoding='UTF-8', xml_declaration=True)
        return buf.getvalue().decode('UTF-8')

    def __repr__(self):
        return f'{self.__class__.__name__}({self.slide!r}, tile_size={self._tile_size}, overlap={self._overlap})'


def main():
    """Test the new DeepZoom implementation"""
    import sys
    import os
    
    if len(sys.argv) != 2:
        print('Usage: python sdpc_deepzoom_new.py <sdpc-file>')
        sys.exit(1)
    
    sdpc_path = sys.argv[1]
    
    if not os.path.exists(sdpc_path):
        print(f'Error: File not found: {sdpc_path}')
        sys.exit(1)
    
    try:
        print(f"Testing new DeepZoom implementation with: {os.path.basename(sdpc_path)}")
        
        with SdpcSlide(sdpc_path) as slide:
            print(f"Slide dimensions: {slide.dimensions}")
            print(f"Slide levels: {slide.level_count}")
            
            # Create DeepZoom generator
            dzg = DeepZoomGenerator(slide, tile_size=254, overlap=1)
            
            print(f"\nDeepZoom levels: {dzg.level_count}")
            print(f"DeepZoom dimensions: {dzg.level_dimensions}")
            print(f"Total tiles: {dzg.tile_count}")
            
            # Test tiles from different levels
            test_levels = [0, dzg.level_count // 2, dzg.level_count - 1]
            
            for level in test_levels:
                if level < dzg.level_count:
                    print(f"\nTesting level {level}...")
                    tile = dzg.get_tile(level, (0, 0))
                    filename = f"new_deepzoom_tile_level_{level}.jpg"
                    tile.save(filename)
                    print(f"Saved tile: {filename} (size: {tile.size})")
            
            # Generate DZI
            dzi_content = dzg.get_dzi('jpeg')
            with open('new_deepzoom_test.dzi', 'w') as f:
                f.write(dzi_content)
            print(f"\nSaved DZI metadata: new_deepzoom_test.dzi")
            
        print("\n✓ New DeepZoom implementation test completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

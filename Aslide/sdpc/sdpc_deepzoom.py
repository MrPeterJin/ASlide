from io import BytesIO
import math
from PIL import Image
from xml.etree.ElementTree import ElementTree, Element, SubElement
from Aslide.sdpc.sdpc_slide import SdpcSlide


class DeepZoomGenerator(object):
    """Generates Deep Zoom tiles and metadata for SDPC format slides."""

    def __init__(self, osr, tile_size=254, overlap=1, limit_bounds=False):
        """Create a DeepZoomGenerator wrapping an SDPC slide object.

        osr:          a slide object.
        tile_size:    the width and height of a single tile.  For best viewer
                      performance, tile_size + 2 * overlap should be a power
                      of two.
        overlap:      the number of extra pixels to add to each interior edge
                      of a tile.
        limit_bounds: True to render only the non-empty slide region."""

        self.slide = osr
        self._osr = osr

        # Store parameters
        self._z_t_downsample = tile_size
        self._z_overlap = overlap
        self._limit_bounds = limit_bounds

        # Get slide dimensions - SDPC stores dimensions in level_dimensions
        self._l0_dimensions = self._osr.level_dimensions[0]

        # Deep Zoom level dimensions and tiles
        z_dimensions = [self._l0_dimensions]
        z_size = tuple(self._l0_dimensions)

        # Build the Deep Zoom pyramid
        while z_size[0] > 1 or z_size[1] > 1:
            z_size = tuple(max(1, int(math.ceil(z / 2))) for z in z_size)
            z_dimensions.append(z_size)
        self._z_dimensions = tuple(reversed(z_dimensions))

        # Tile calculations
        tiles = lambda z_lim: int(math.ceil(z_lim / self._z_t_downsample))
        self._t_dimensions = tuple((tiles(z_w), tiles(z_h))
                    for z_w, z_h in self._z_dimensions)

        # Deep Zoom level count
        self._dz_levels = len(self._z_dimensions)

        # Total downsamples for each Deep Zoom level
        l0_z_downsamples = tuple(2 ** (self._dz_levels - dz_level - 1)
                    for dz_level in range(self._dz_levels))

        # Preferred slide levels for each Deep Zoom level
        # SDPC has its own get_best_level_for_downsample method
        self._slide_from_dz_level = tuple(
                    self._osr.get_best_level_for_downsample(d)
                    for d in l0_z_downsamples)

        # Piecewise downsamples
        self._l0_l_downsamples = self._osr.level_downsamples
        self._l_z_downsamples = tuple(
                    l0_z_downsamples[dz_level] /
                    self._l0_l_downsamples[self._slide_from_dz_level[dz_level]]
                    for dz_level in range(self._dz_levels))

        # Background color - use white as default
        self._bg_color = '#ffffff'

    def __repr__(self):
        return '%s(%r, tile_size=%r, overlap=%r, limit_bounds=%r)' % (
                self.__class__.__name__, self._osr, self._z_t_downsample,
                self._z_overlap, self._limit_bounds)

    @property
    def level_count(self):
        """The number of Deep Zoom levels in the image."""
        return self._dz_levels

    @property
    def level_tiles(self):
        """A list of (tiles_x, tiles_y) tuples for each Deep Zoom level."""
        return self._t_dimensions

    @property
    def level_dimensions(self):
        """A list of (pixels_x, pixels_y) tuples for each Deep Zoom level."""
        return self._z_dimensions

    @property
    def tile_count(self):
        """The total number of Deep Zoom tiles in the image."""
        return sum(t_cols * t_rows for t_cols, t_rows in self._t_dimensions)

    def _get_tile_info(self, level, address):
        """Calculate the appropriate tile information for a given level and address."""
        # Get preferred slide level
        slide_level = self._slide_from_dz_level[level]

        # Calculate tile position and size
        x, y = address
        tile_size = self._z_t_downsample

        # Calculate pixel offset for this tile
        z_overlap = self._z_overlap
        tile_x = (x * tile_size) - (x * z_overlap)
        tile_y = (y * tile_size) - (y * z_overlap)

        # Calculate pixel size for this tile
        z_size = self._z_dimensions[level]
        z_x = min(tile_size + (2 * z_overlap), z_size[0] - tile_x)
        z_y = min(tile_size + (2 * z_overlap), z_size[1] - tile_y)

        # Calculate downsampling factor
        l0_z_downsample = 2 ** (self._dz_levels - level - 1)

        # Calculate region in base level coordinates
        l0_x = int(tile_x * l0_z_downsample)
        l0_y = int(tile_y * l0_z_downsample)
        l0_z_x = int(z_x * l0_z_downsample)
        l0_z_y = int(z_y * l0_z_downsample)

        # Return location, level, size
        return (l0_x, l0_y), slide_level, (l0_z_x, l0_z_y), (z_x, z_y)

    def get_tile(self, level, address):
        """Return an RGB PIL.Image for a tile.

        level:     the Deep Zoom level.
        address:   the address of the tile within the level as a (col, row)
                   tuple."""

        # Get tile information
        (l0_x, l0_y), slide_level, (l0_z_x, l0_z_y), (z_x, z_y) = self._get_tile_info(level, address)

        try:
            # Read region from slide - SDPC's read_region already returns RGB images
            tile = self._osr.read_region((l0_x, l0_y), slide_level, (l0_z_x, l0_z_y))

            # Scale to the correct size if needed
            if tile.size != (z_x, z_y):
                tile = tile.resize((z_x, z_y), Image.LANCZOS)

            return tile
        except Exception as e:
            # If reading fails, return a blank tile
            print(f"Error reading tile at level {level}, address {address}: {e}")
            return Image.new('RGB', (z_x, z_y), self._bg_color)

    def get_dzi(self, format):
        """Return a string containing the XML metadata for the .dzi file.

        format:    the format of the individual tiles ('png' or 'jpeg')"""
        image = Element('Image', TileSize=str(self._z_t_downsample),
                        Overlap=str(self._z_overlap), Format=format,
                        xmlns='http://schemas.microsoft.com/deepzoom/2008')
        w, h = self._l0_dimensions
        SubElement(image, 'Size', Width=str(w), Height=str(h))
        tree = ElementTree(element=image)
        buf = BytesIO()
        tree.write(buf, encoding='UTF-8')
        return buf.getvalue().decode('UTF-8')


def main():
    """Test function for the SDPC DeepZoomGenerator."""
    import sys
    if len(sys.argv) != 2:
        print('Usage: %s <sdpc-file>' % sys.argv[0])
        sys.exit(1)

    sdpc_path = sys.argv[1]
    try:
        slide = SdpcSlide(sdpc_path)

        print("SDPC Slide Information:")
        print("Level count:", slide.level_count)
        print("Level dimensions:", slide.level_dimensions)
        print("Level downsamples:", slide.level_downsamples)

        dzg = DeepZoomGenerator(slide)
        print("\nDeepZoom Generator Information:")
        print("DeepZoom level count:", dzg.level_count)
        print("DeepZoom level tiles:", dzg.level_tiles)
        print("DeepZoom level dimensions:", dzg.level_dimensions)
        print("DeepZoom tile count:", dzg.tile_count)
        print("\nDZI XML:")
        print(dzg.get_dzi('jpeg'))

        # Get sample tiles from different levels
        if dzg.level_count > 0:
            # Get the lowest resolution tile (highest level)
            highest_level = dzg.level_count - 1
            tile_highest = dzg.get_tile(highest_level, (0, 0))
            tile_highest.save('sdpc_tile_highest.jpg')
            print(f"Sample tile from highest level ({highest_level}) saved as 'sdpc_tile_highest.jpg'")

            # Get a mid-resolution tile if available
            if dzg.level_count > 2:
                mid_level = dzg.level_count // 2
                tile_mid = dzg.get_tile(mid_level, (0, 0))
                tile_mid.save('sdpc_tile_mid.jpg')
                print(f"Sample tile from mid level ({mid_level}) saved as 'sdpc_tile_mid.jpg'")

            # Get the highest resolution tile (lowest level) if not too large
            if dzg.level_count > 1:
                tile_lowest = dzg.get_tile(0, (0, 0))
                tile_lowest.save('sdpc_tile_lowest.jpg')
                print(f"Sample tile from lowest level (0) saved as 'sdpc_tile_lowest.jpg'")
    except Exception as e:
        print(f"Error testing SDPC DeepZoom: {e}")
    finally:
        if 'slide' in locals():
            slide.close()
            print("SDPC slide closed")


if __name__ == '__main__':
    main()

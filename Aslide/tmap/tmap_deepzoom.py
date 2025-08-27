from io import BytesIO

from Aslide.tmap import tmap_lowlevel, tmap_slide
from PIL import Image

from xml.etree.ElementTree import ElementTree, Element, SubElement


class DeepZoomGenerator(object):

    def __init__(self, slide, tile_size=254, overlap=1, limit_bounds=False):
        self.slide = slide
        self._osr = slide._osr

        self._z_t_downsample = tile_size
        self._z_overlap = overlap
        self._limit_bounds = limit_bounds

        # Calculate DeepZoom levels based on slide dimensions
        self._calculate_levels()

    def _calculate_levels(self):
        """Calculate DeepZoom levels and dimensions"""
        import math

        # Get slide dimensions
        slide_width, slide_height = self.slide.dimensions

        # Calculate the number of levels needed
        max_dimension = max(slide_width, slide_height)
        self._level_count = int(math.ceil(math.log(max_dimension, 2))) + 1

        # Calculate level dimensions and tiles
        self._level_dimensions = []
        self._level_tiles = []

        for level in range(self._level_count):
            scale = 2 ** (self._level_count - level - 1)
            level_width = max(1, int(math.ceil(slide_width / scale)))
            level_height = max(1, int(math.ceil(slide_height / scale)))

            self._level_dimensions.append((level_width, level_height))

            # Calculate tiles for this level
            tiles_x = int(math.ceil(level_width / self._z_t_downsample))
            tiles_y = int(math.ceil(level_height / self._z_t_downsample))
            self._level_tiles.append((tiles_x, tiles_y))

    @property
    def level_count(self):
        """The number of Deep Zoom levels in the image."""
        return self._level_count

    @property
    def level_dimensions(self):
        """A list of (pixels_x, pixels_y) tuples for each Deep Zoom level."""
        return self._level_dimensions

    @property
    def level_tiles(self):
        """A list of (tiles_x, tiles_y) tuples for each Deep Zoom level."""
        return self._level_tiles

    @property
    def tile_count(self):
        """The total number of Deep Zoom tiles in the image."""
        return sum(tiles_x * tiles_y for tiles_x, tiles_y in self._level_tiles)

    @property
    def tile_size(self):
        """The tile size for this Deep Zoom generator."""
        return self._z_t_downsample

    def get_tile(self, level, address):
        """Return an RGB PIL.Image for a tile.

        level:     the Deep Zoom level.
        address:   the address of the tile within the level as a (col, row)
                   tuple."""

        # Debug output like SDPC
        print(f"TMAP _get_tile_info: level={level}, address={address}")

        # Calculate tile position and size
        scale = 2 ** (self._level_count - level - 1)

        # Calculate tile position in slide coordinates
        tile_x = address[0] * self._z_t_downsample * scale
        tile_y = address[1] * self._z_t_downsample * scale

        # Calculate tile size in slide coordinates
        tile_width = min(self._z_t_downsample * scale, self.slide.dimensions[0] - tile_x)
        tile_height = min(self._z_t_downsample * scale, self.slide.dimensions[1] - tile_y)

        print(f"  tile_size={self._z_t_downsample}, z_overlap={self._z_overlap}")
        print(f"  tile_x={tile_x}, tile_y={tile_y}")
        print(f"  z_size=({tile_width}, {tile_height}), z_x={self._z_t_downsample}, z_y={self._z_t_downsample}")
        print(f"  scale={scale}, slide_dimensions={self.slide.dimensions}")

        # Use similar optimization strategy as SDPC
        if level >= 13:
            print(f"  High resolution level {level} >= 13, using read_region method")
            # High resolution - use read_region method
            try:
                print(f"  Using read_region: coordinates=({int(tile_x)}, {int(tile_y)}), size=({int(tile_width)}, {int(tile_height)})")
                region = self.slide.read_region((int(tile_x), int(tile_y)), 0, (int(tile_width), int(tile_height)))

                print(f"  Read region size: {region.size}")

                # Resize to tile size if needed
                if region.size != (self._z_t_downsample, self._z_t_downsample):
                    region = region.resize((self._z_t_downsample, self._z_t_downsample), Image.LANCZOS)
                    print(f"  Resized to: {region.size}")

                print(f"  Returning high-res tile: {region.size}")
                return region
            except Exception as e:
                print(f"  Read_region failed: {e}, falling back to thumbnail method")
                # Fallback to thumbnail method
                pass
        else:
            print(f"  Low resolution level {level} < 13, using thumbnail method")

        # For lower resolution levels, use thumbnail-based method (like SDPC)
        try:
            # Get thumbnail and crop/resize appropriately
            thumbnail_size = max(512, self._z_t_downsample * 4)  # Ensure thumbnail is large enough
            print(f"  Getting thumbnail, target size: {thumbnail_size}x{thumbnail_size}")
            thumbnail = self.slide.get_thumbnail((thumbnail_size, thumbnail_size))
            print(f"  Got thumbnail, actual size: {thumbnail.size}")

            # Calculate crop area in thumbnail coordinates
            thumb_scale_x = thumbnail.size[0] / self.slide.dimensions[0]
            thumb_scale_y = thumbnail.size[1] / self.slide.dimensions[1]

            crop_x = int(tile_x * thumb_scale_x)
            crop_y = int(tile_y * thumb_scale_y)
            crop_w = max(1, int(tile_width * thumb_scale_x))
            crop_h = max(1, int(tile_height * thumb_scale_y))

            # Ensure crop area is within thumbnail bounds
            crop_x = max(0, min(crop_x, thumbnail.size[0] - 1))
            crop_y = max(0, min(crop_y, thumbnail.size[1] - 1))
            crop_w = min(crop_w, thumbnail.size[0] - crop_x)
            crop_h = min(crop_h, thumbnail.size[1] - crop_y)

            print(f"  Thumbnail scale: x={thumb_scale_x:.6f}, y={thumb_scale_y:.6f}")
            print(f"  Crop area: ({crop_x}, {crop_y}, {crop_x + crop_w}, {crop_y + crop_h})")

            # Crop and resize
            if crop_w > 0 and crop_h > 0:
                cropped = thumbnail.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
                print(f"  Cropped size: {cropped.size}")

                # Resize to final tile size
                if cropped.size != (self._z_t_downsample, self._z_t_downsample):
                    cropped = cropped.resize((self._z_t_downsample, self._z_t_downsample), Image.LANCZOS)
                    print(f"  Final resized size: {cropped.size}")

                print(f"  Returning thumbnail-based tile: {cropped.size}")
                return cropped
            else:
                print(f"  Invalid crop dimensions: w={crop_w}, h={crop_h}")

        except Exception as e:
            print(f"  Thumbnail method failed: {e}")

        # Final fallback - return a blank tile
        print(f"  Using fallback: blank tile {self._z_t_downsample}x{self._z_t_downsample}")
        return Image.new('RGB', (self._z_t_downsample, self._z_t_downsample), (255, 255, 255))

    def get_dzi(self, format):
        """Return a string containing the XML metadata for the .dzi file.

        format:    the format of the individual tiles ('png' or 'jpeg')"""
        image = Element('Image', TileSize=str(self._z_t_downsample),
                        Overlap=str(self._z_overlap), Format=format,
                        xmlns='http://schemas.microsoft.com/deepzoom/2008')

        w, h = self.slide.dimensions
        SubElement(image, 'Size', Width=str(w), Height=str(h))
        tree = ElementTree(element=image)
        buf = BytesIO()
        tree.write(buf, encoding='UTF-8')

        return buf.getvalue().decode('UTF-8')


def main():
    slide = tmap_slide.TmapSlide('path/to/your/slide')
    dzg = DeepZoomGenerator(slide)
    img = dzg.get_tile_data((110, 100))
    img.show()
    slide.close()


if __name__ == '__main__':
    main()

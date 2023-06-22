from io import BytesIO

from Aslide.tmap import tmap_lowlevel, tmap_slide

from xml.etree.ElementTree import ElementTree, Element, SubElement


class DeepZoomGenerator(object):

    def __init__(self, slide, tile_size=254, overlap=1, limit_bounds=False):
        self.slide = slide
        self._osr = slide._osr

        self._z_t_downsample = tile_size
        self._z_overlap = overlap
        self._limit_bounds = limit_bounds

    def get_tile(self, level, address):
        """Return an RGB PIL.Image for a tile.

        level:     the Deep Zoom level.
        address:   the address of the tile within the level as a (col, row)
                   tuple."""

        level = reversed(self.slide.level_downsamples)[level]
        return tmap_lowlevel.get_tile_data(self._osr._osr, level, address[1], address[0])

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

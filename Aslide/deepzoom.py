from openslide.deepzoom import DeepZoomGenerator as OpenSlideDZG

from Aslide.kfb.kfb_deepzoom import DeepZoomGenerator as KfbDZG
from Aslide.tmap.tmap_deepzoom import DeepZoomGenerator as TmapDZG


class ADeepZoomGenerator(object):
    def __init__(self, osr, tile_size=254, overlap=1, limit_bounds=False):
        if osr.format in ['.kfb', '.KFB']:
            self._dzg = KfbDZG(osr, tile_size, overlap, limit_bounds)
        elif osr.format in ['.sdpc', '.SDPC']:
            raise NotImplementedError("UnsupportedFormat or Missing File => %s" % osr.filepath)
        elif osr.format in ['.tmap', '.TMAP']:
            self._dzg = TmapDZG(osr, 256, overlap, limit_bounds)
        else:
            self._dzg = OpenSlideDZG(osr, tile_size, overlap, limit_bounds)

    @property
    def level_count(self):
        """The number of Deep Zoom levels in the image."""
        return self._dzg.level_count

    @property
    def level_tiles(self):
        """A list of (tiles_x, tiles_y) tuples for each Deep Zoom level."""
        return self._dzg.level_tiles

    @property
    def level_dimensions(self):
        """A list of (pixels_x, pixels_y) tuples for each Deep Zoom level."""
        return self._dzg.level_dimensions

    @property
    def tile_count(self):
        """The total number of Deep Zoom tiles in the image."""
        return self._dzg.tile_count

    def get_dzi(self, format):
        """

        :param format: the format of the individual tiles ('png' or 'jpeg')
        :return: a string containing the XML metadata for the .dzi file.
        """
        return self._dzg.get_dzi(format)

    def get_tile(self, level, address):
        """

        :param level: the Deep Zoom level
        :param address:  the address of the tile within the level as a (col, row) tuple.
        :return: Return an RGB PIL.Image for a tile
        """
        return self._dzg.get_tile(level, address)


if __name__ == '__main__':
    filepath = "path-to-file"

    from aslide import Aslide
    slide = Aslide(filepath)

    dzg = ADeepZoomGenerator(slide)
    print("level_count : ", dzg.level_count)
    print("level_tiles : ", dzg.level_tiles)
    print("level_dimensions : ", dzg.level_dimensions)
    print("tile count : ", dzg.tile_count)
    print("dzi : \n")
    print(dzg.get_dzi('jpeg'))
    tile = dzg.get_tile(13, (0, 0))
    import matplotlib.pyplot as plt

    plt.imshow(tile)
    plt.show()
    plt.savefig('result.png')

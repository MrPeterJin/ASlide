from openslide.deepzoom import DeepZoomGenerator as OpenSlideDZG

from Aslide.kfb.kfb_deepzoom import DeepZoomGenerator as KfbDZG
from Aslide.tmap.tmap_deepzoom import DeepZoomGenerator as TmapDZG
from Aslide.sdpc.sdpc_deepzoom import DeepZoomGenerator as SdpcDZG
from Aslide.dyj.dyj_deepzoom import DeepZoomGenerator as DyjDZG
from Aslide.ibl.ibl_deepzoom import DeepZoomGenerator as IblDZG

try:
    from Aslide.mds.mds_deepzoom import DeepZoomGenerator as MdsDZG
except ImportError:
    MdsDZG = None

try:
    from Aslide.vsi.vsi_deepzoom import VsiDeepZoomGenerator as VsiDZG
except ImportError:
    VsiDZG = None

try:
    from Aslide.qptiff.qptiff_deepzoom import QptiffDeepZoomGenerator as QptiffDZG
except ImportError:
    QptiffDZG = None

try:
    from Aslide.tron.deepzoom import TronDeepZoomGenerator as TronDZG
except ImportError:
    TronDZG = None

try:
    from Aslide.isyntax.isyntax_deepzoom import IsyntaxDeepZoomGenerator as IsyntaxDZG
except ImportError:
    IsyntaxDZG = None


class ADeepZoomGenerator(object):
    def __init__(self, osr, tile_size=254, overlap=1, limit_bounds=False, max_level_size=10000):
        if osr.format in ['.kfb', '.KFB']:
            self._dzg = KfbDZG(osr, tile_size, overlap, limit_bounds)
        elif osr.format in ['.sdpc', '.SDPC']:
            # SDPC DeepZoomGenerator only accepts 4 parameters
            self._dzg = SdpcDZG(osr, tile_size, overlap, limit_bounds)
        elif osr.format in ['.dyj', '.DYJ']:
            # DYJ format uses specialized DeepZoom generator
            self._dzg = DyjDZG(osr, tile_size, overlap, limit_bounds)
        elif osr.format in ['.tmap', '.TMAP']:
            self._dzg = TmapDZG(osr, 256, overlap, limit_bounds)
        elif osr.format in ['.mds', '.MDS', '.mdsx', '.MDSX'] and MdsDZG:
            # MDS format uses specialized DeepZoom generator
            self._dzg = MdsDZG(osr, tile_size, overlap, limit_bounds)
        elif osr.format in ['.vsi', '.VSI'] and VsiDZG:
            # VSI format uses specialized DeepZoom generator
            self._dzg = VsiDZG(osr, tile_size, overlap, limit_bounds)
        elif osr.format in ['.qptiff', '.QPTIFF'] and QptiffDZG:
            # QPTiff format uses specialized DeepZoom generator
            self._dzg = QptiffDZG(osr, tile_size, overlap, limit_bounds)
        elif osr.format in ['.tron', '.TRON'] and TronDZG:
            # TRON format uses specialized DeepZoom generator - native tile support
            self._dzg = TronDZG(osr, tile_size, overlap, limit_bounds)
        elif osr.format in ['.isyntax', '.ISYNTAX'] and IsyntaxDZG:
            # iSyntax format uses specialized DeepZoom generator
            self._dzg = IsyntaxDZG(osr, tile_size, overlap, limit_bounds)
        elif osr.format in ['.ibl', '.IBL']:
            # IBL format (苏州秉理 BingLi) uses specialized DeepZoom generator
            self._dzg = IblDZG(osr, tile_size, overlap, limit_bounds)
        else:
            self._dzg = OpenSlideDZG(osr, tile_size, overlap, limit_bounds)

    @property
    def tile_size(self):
        """The tile size for this Deep Zoom generator."""
        return getattr(self._dzg, 'tile_size', 254)

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

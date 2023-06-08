import io
from PIL import Image
from kfb.utils import *
import numpy as np
from openslide import AbstractSlide, _OpenSlideMap

class TSlide(AbstractSlide):
    def __init__(self, filename):
        AbstractSlide.__init__(self)
        self.__filename = filename
        self._osr = kfbslide_open(filename)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__filename)

    @classmethod
    def detect_format(cls, filename):
        return detect_vendor(filename)

    def close(self):
        kfbslide_close(self._osr)

    @property
    def level_count(self):
        return kfbslide_get_level_count(self._osr)

    @property
    def level_dimensions(self):
        return tuple(kfbslide_get_level_dimensions(self._osr, i)
                     for i in range(self.level_count))

    @property
    def level_downsamples(self):
        return tuple(kfbslide_get_level_downsample(self._osr, i)
                     for i in range(self.level_count))

    @property
    def properties(self):
        return _KfbPropertyMap(self._osr)

    @property
    def associated_images(self):
        return _AssociatedImageMap(self._osr)

    def get_best_level_for_downsample(self, downsample):
        return kfbslide_get_best_level_for_downsample(self._osr, downsample)

    def read_region(self, location, level, size):
        # import pdb

        x = int(location[0])
        y = int(location[1])
        width = int(size[0])
        height = int(size[1])
        img_index = kfbRef.img_count
        kfbRef.img_count += 1

        return Image.open(io.BytesIO(kfbslide_read_roi_region(self._osr, level, x, y, width, height)))

    def get_thumbnail(self, size):
        """Return a PIL.Image containing an RGB thumbnail of the image.

        size:     the maximum size of the thumbnail."""

        thumb = self.associated_images[b'thumbnail']
        return thumb
    
class kfbRef:
    img_count = 0    

class _KfbPropertyMap(_OpenSlideMap):
    def _keys(self):
        return kfbslide_property_names(self._osr)

    def __getitem__(self, key):
        v = kfbslide_property_value(self._osr, key)
        if v is None:
            raise KeyError()
        return v


class _AssociatedImageMap(_OpenSlideMap):
    def _keys(self):
        return kfbslide_get_associated_image_names(self._osr)

    def __getitem__(self, key):
        if key not in self._keys():
            raise KeyError()
        return kfbslide_read_associated_image(self._osr, key)

class KfbSlide:
    def __init__(self,path):
        self.slide = TSlide(path)
        self.level_count = self.slide.level_count
        self.level_dimensions = self.slide.level_dimensions
        self.level_downsamples = self.slide.level_downsamples
        
    def header(self):
        header = {}
        for key, val in self.slide.associated_images.items():
            print(key, " --> ", val.size)
            header[key] = np.array(val)
        return header
    
    def get_best_level_for_downsample(self, downsample):
        return self.slide.get_best_level_for_downsample(downsample)
    
    def read_reigon(self, location, level, size):
        return self.slide.read_region(location, level, size)


if __name__ == '__main__':
    slide = KfbSlide('path-to-kfb-file')
    header = slide.header()
    print(slide.level_count)
    print(slide.level_dimensions)
    print(slide.level_downsamples)
    print(slide.get_best_level_for_downsample(64))
    print(slide.read_reigon((0,0),0,(1000,1000)))

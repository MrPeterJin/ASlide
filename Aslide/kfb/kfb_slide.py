import io
from Aslide.kfb import kfb_lowlevel
from PIL import Image
from openslide import AbstractSlide, _OpenSlideMap


class kfbRef:
    img_count = 0


class KfbSlide(AbstractSlide):
    def __init__(self, filename):
        AbstractSlide.__init__(self)
        self.__filename = filename
        self._osr = kfb_lowlevel.kfbslide_open(filename)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__filename)

    @classmethod
    def detect_format(cls, filename):
        return kfb_lowlevel.detect_vendor(filename)

    def close(self):
        kfb_lowlevel.kfbslide_close(self._osr)

    @property
    def level_count(self):
        return kfb_lowlevel.kfbslide_get_level_count(self._osr)

    @property
    def level_dimensions(self):
        return tuple(kfb_lowlevel.kfbslide_get_level_dimensions(self._osr, i)
                     for i in range(self.level_count))

    @property
    def level_downsamples(self):
        return tuple(kfb_lowlevel.kfbslide_get_level_downsample(self._osr, i)
                     for i in range(self.level_count))

    @property
    def properties(self):
        return _KfbPropertyMap(self._osr)

    @property
    def associated_images(self):
        return _AssociatedImageMap(self._osr)

    def get_best_level_for_downsample(self, downsample):
        return kfb_lowlevel.kfbslide_get_best_level_for_downsample(self._osr, downsample)

    def read_fixed_region(self, location, level, size):
        # import pdb
        #pdb.set_trace()
        x = int(location[0])
        y = int(location[1])
        img_index = kfbRef.img_count
        kfbRef.img_count += 1
        print("img_index : ", img_index, "Level : ", level, "Location : ", x , y)
        return kfb_lowlevel.kfbslide_read_region(self._osr, level, x, y)

    def read_region(self, location, level, size):
        x = int(location[0])
        y = int(location[1])
        width = int(size[0])
        height = int(size[1])
        img_index = kfbRef.img_count
        kfbRef.img_count += 1

        return kfb_lowlevel.kfbslide_read_roi_region(self._osr, level, x, y, width, height)

    def get_thumbnail(self, size):
        """Return a PIL.Image containing an RGB thumbnail of the image.

        size:     the maximum size of the thumbnail."""

        thumb = self.associated_images[b'thumbnail']
        return thumb


class _KfbPropertyMap(_OpenSlideMap):
    def _keys(self):
        return kfb_lowlevel.kfbslide_property_names(self._osr)

    def __getitem__(self, key):
        v = kfb_lowlevel.kfbslide_property_value(self._osr, key)
        if v is None:
            raise KeyError()
        return v


class _AssociatedImageMap(_OpenSlideMap):
    def _keys(self):
        return kfb_lowlevel.kfbslide_get_associated_image_names(self._osr)

    def __getitem__(self, key):
        if key not in self._keys():
            raise KeyError()
        return kfb_lowlevel.kfbslide_read_associated_image(self._osr, key)


def open_kfbslide(filename):
    try:
        return KfbSlide(filename)
    except Exception:
        return None


def main():
    kfb_file_path = "path/to/kfb/file"
    slide = KfbSlide(kfb_file_path)
    print("Format : ", slide.detect_format(kfb_file_path))
    print("level_count : ", slide.level_count)
    print("level_dimensions : ", slide.level_dimensions)
    print("level_downsamples : ", slide.level_downsamples)
    print("properties : ", slide.properties)
    print("Associated Images : ")
    for key, val in slide.associated_images.items():
        print(key, " --> ", val)

    print("best level for downsample 20 : ", slide.get_best_level_for_downsample(20))
    im = slide.read_region((1000, 1000), 4, (1000, 1000))
    print(im.mode)
    im.show()
    im.close()

if __name__ == '__main__':
    main()

from __future__ import division
import sys
import os
from ctypes import *
from itertools import count

from openslide import lowlevel


dirname, _ = os.path.split(os.path.abspath(__file__))
sys.path.append(os.path.join(dirname, 'so'))
soPath = os.path.join(dirname, 'so/libkfbslide.so')
print(os.getcwd())

_lib = cdll.LoadLibrary(soPath)


class KFBSlideError(Exception):
    """docstring for KFBSlideError"""


class _KfbSlide(object):
    def __init__(self, ptr):
        self._as_parameter_ = ptr
        self._valid = True
        self._close = kfbslide_close

    def __del__(self):
        if self._valid:
            self._close(self)

    def invalidate(self):
        self._valid = False

    @classmethod
    def from_param(cls, obj):
        if obj.__class__ != cls:
            raise ValueError("Not an KfbSlide reference")
        if not obj._as_parameter_:
            raise ValueError("Passing undefined slide object")
        if not obj._valid:
            raise ValueError("Passing closed kfbSlide object")
        return obj


# check for errors opening an image file and wrap the resulting handle
def _check_open(result, _func, _args):
    if result is None:
        raise lowlevel.OpenSlideUnsupportedFormatError(
            "Unsupported or missing image file")
    slide = _KfbSlide(c_void_p(result))
    # err = get_error(slide)
    # if err is not None:
    #     raise lowlevel.OpenSlideError(err)
    return slide


# prevent further operations on slide handle after it is closed
def _check_close(_result, _func, args):
    args[0].invalidate()


# check if the library got into an error state after each library call
def _check_error(result, func, args):
    # err = get_error(args[0])
    # if err is not None:
    #     raise lowlevel.OpenSlideError(err)
    return lowlevel._check_string(result, func, args)


# Convert returned NULL-terminated char** into a list of strings
def _check_name_list(result, func, args):
    _check_error(result, func, args)
    names = []
    for i in count():
        name = result[i]
        if not name:
            break
        names.append(name.decode('UTF-8', 'replace'))
    return names


# resolve and return an OpenSlide function with the specified properties
def _func(name, restype, argtypes, errcheck=_check_error):
    func = getattr(_lib, name)
    func.argtypes = argtypes
    func.restype = restype
    if errcheck is not None:
        func.errcheck = errcheck
    return func


detect_vendor = _func("kfbslide_detect_vendor", c_char_p, [lowlevel._utf8_p],
                      lowlevel._check_string)

_kfbslide_open = _func("kfbslide_open", c_void_p, [lowlevel._utf8_p], _check_open)


# _kfbslide_set_attrs = _func("kfbslide_set_attrs", None, [_KfbSlide, c_int, c_int, c_int, c_float, c_double, c_float, c_int])

def kfbslide_open(name):
    osr = _kfbslide_open(name)
    # height, width, scale, spendTime, scanTime, imgCapRes, blkSize = kfbHeaderInfo.GetHeaderInfo(name)
    # _kfbslide_set_attrs(osr, height, width, scale, spendTime, scanTime, imgCapRes, blkSize)
    return osr


kfbslide_close = _func("kfbslide_close", None, [_KfbSlide], lowlevel._check_close)

kfbslide_get_level_count = _func("kfbslide_get_level_count", c_int32, [_KfbSlide])

_kfbslide_get_level_dimensions = _func("kfbslide_get_level_dimensions", None,
                                       [_KfbSlide, c_int32, POINTER(c_int64), POINTER(c_int64)])


def kfbslide_get_level_dimensions(osr, level):
    w, h = c_int64(), c_int64()
    _kfbslide_get_level_dimensions(osr, level, byref(w), byref(h))
    return (w.value, h.value)


kfbslide_get_level_downsample = _func("kfbslide_get_level_downsample",
                                      c_double, [_KfbSlide, c_int32])

kfbslide_get_best_level_for_downsample = _func(
    "kfbslide_get_best_level_for_downsample", c_int32, [_KfbSlide, c_double])

_kfbslide_read_region = _func("kfbslide_read_region", c_bool,
                              [_KfbSlide, c_int32, c_int64, c_int64, POINTER(c_int), POINTER(POINTER(c_ubyte))])

_kfbslide_read_roi_region = _func("kfbslide_get_image_roi_stream", c_bool,
                                  [_KfbSlide, c_int32, c_int64, c_int64, c_int64, c_int64, POINTER(c_int),
                                   POINTER(POINTER(c_ubyte))])


def kfbslide_read_region(osr, level, pos_x, pos_y):
    data_length = c_int()
    pixel = POINTER(c_ubyte)()
    if not _kfbslide_read_region(osr, level, pos_x, pos_y, byref(data_length), byref(pixel)):
        raise ValueError("Fail to read region")
    import numpy as np
    return np.ctypeslib.as_array(pixel, shape=(data_length.value,))


def kfbslide_read_roi_region(osr, level, pos_x, pos_y, width, height):
    data_length = c_int()
    pixel = POINTER(c_ubyte)()
    if not _kfbslide_read_roi_region(osr, level, pos_x, pos_y, width, height, byref(data_length), byref(pixel)):
        raise ValueError("Fail to read roi region")
    # img = PIL.Image.frombuffer('RGBA', (width, height), pixel, 'raw', 'RGBA', 0, 1)
    import numpy as np
    return np.ctypeslib.as_array(pixel, shape=(data_length.value,))


kfbslide_property_names = _func("kfbslide_get_property_names", POINTER(c_char_p),
                                [_KfbSlide], _check_name_list)

kfbslide_property_value = _func("kfbslide_get_property_value", c_char_p,
                                [_KfbSlide, lowlevel._utf8_p])

_kfbslide_get_associated_image_names = _func("kfbslide_get_associated_image_names", POINTER(c_char_p), [_KfbSlide],
                                             _check_name_list)


def kfbslide_get_associated_image_names(osr):
    names = _kfbslide_get_associated_image_names(osr)
    rtn = []
    for name in names:
        if name is None:
            break
        rtn.append(name)
    return rtn


_kfbslide_get_associated_image_dimensions = _func("kfbslide_get_associated_image_dimensions", c_void_p,
                                                  [_KfbSlide, lowlevel._utf8_p, POINTER(c_int64), POINTER(c_int64),
                                                   POINTER(c_int)])


def kfbslide_get_associated_image_dimensions(osr, name):
    w, h = c_int64(), c_int64()
    data_length = c_int()
    _kfbslide_get_associated_image_dimensions(osr, name, byref(w), byref(h), byref(data_length))
    return (w.value, h.value), data_length.value


_kfbslide_read_associated_image = _func("kfbslide_read_associated_image", c_void_p,
                                        [_KfbSlide, lowlevel._utf8_p, POINTER(POINTER(c_ubyte))])


def kfbslide_read_associated_image(osr, name):
    data_length = kfbslide_get_associated_image_dimensions(osr, name)[1]
    pixel = POINTER(c_ubyte)()
    _kfbslide_read_associated_image(osr, name, byref(pixel))
    import numpy as np
    narray = np.ctypeslib.as_array(pixel, shape=(data_length,))
    from io import BytesIO
    buf = BytesIO(narray)
    from PIL import Image
    return Image.open(buf)

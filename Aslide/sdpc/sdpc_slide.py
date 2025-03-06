import numpy.ctypeslib as npCtypes
import ctypes
from ctypes import *
import gc
import os
import sys
from PIL import Image
from .Sdpc_struct import SqSdpcInfo


# import dll file
dirname, _ = os.path.split(os.path.abspath(__file__))
sys.path.append(os.path.join(dirname, 'so'))
soPath = os.path.join(dirname, 'so/libDecodeSdpc.so')

# load dll
so = ctypes.CDLL(soPath)
so.GetLayerInfo.restype = POINTER(c_char)
so.SqGetRoiRgbOfSpecifyLayer.argtypes = [POINTER(SqSdpcInfo), POINTER(POINTER(c_uint8)),
                                             c_int, c_int, c_uint, c_uint, c_int]
so.SqGetRoiRgbOfSpecifyLayer.restype = c_int
so.SqOpenSdpc.restype = POINTER(SqSdpcInfo)
so.GetLabelJpeg.argtypes = [POINTER(SqSdpcInfo), POINTER(c_uint), POINTER(c_uint), POINTER(c_size_t)]
so.GetLabelJpeg.restype = POINTER(c_uint8)


class SdpcSlide:

    def __init__(self, sdpcPath):
        self.sdpc = self.readSdpc(sdpcPath)
        self.level_count = self.getLevelCount()
        self.level_downsamples = self.getLevelDownsamples()
        self.level_dimensions = self.getLevelDimensions()
        self.scan_magnification = self.readSdpc(sdpcPath).contents.picHead.contents.rate
        self.sampling_rate = self.readSdpc(sdpcPath).contents.picHead.contents.scale
        self.properties = {'openslide.mpp-t': self.sampling_rate, 'openslide.mpp-x': self.sampling_rate, 'openslide.vendor': 'TEKSQRAY'} # maintain consistency with openslide API

    def getRgb(self, rgbPos, width, height):

        intValue = npCtypes.as_array(rgbPos, (height, width, 3))
        return intValue

    def readSdpc(self, fileName):

        sdpc = so.SqOpenSdpc(c_char_p(bytes(fileName, 'gbk')))
        sdpc.contents.fileName = bytes(fileName, 'gbk')

        return sdpc

    def getLevelCount(self):

        return self.sdpc.contents.picHead.contents.hierarchy

    def getLevelDownsamples(self):

        levelCount = self.getLevelCount()
        rate = self.sdpc.contents.picHead.contents.scale
        rate = 1 / rate
        _list = []
        for i in range(levelCount):
            _list.append(rate ** i)
        return tuple(_list)
    
    def get_best_level_for_downsample(self, downsample):
      
        preset = [i*i for i in self.level_downsamples]
        err = [abs(i-downsample) for i in preset]
        level = err.index(min(err))
        return level

    def read_region(self, location, level, size):

        startX, startY = location
        scale = self.level_downsamples[level]
        startX = int(startX / scale)
        startY = int(startY / scale)

        width, height = size

        rgbPos = POINTER(c_uint8)()
        rgbPosPointer = byref(rgbPos)
        so.SqGetRoiRgbOfSpecifyLayer(self.sdpc, rgbPosPointer, width, height, startX, startY, level)
        rgb = self.getRgb(rgbPos, width, height)[..., ::-1]
        rgbCopy = rgb.copy()

        so.Dispose(rgbPos)
        del rgbPos
        del rgbPosPointer
        gc.collect()

        return Image.fromarray(rgbCopy)

    def get_thumbnail(self, thumbnail_level):
        thumbnail = np.array(self.read_region((0, 0), thumbnail_level, self.level_dimensions[thumbnail_level]))
        return thumbnail

    def getLevelDimensions(self):

        def findStrIndex(subStr, str):
            index1 = str.find(subStr)
            index2 = str.find(subStr, index1 + 1)
            index3 = str.find(subStr, index2 + 1)
            index4 = str.find(subStr, index3 + 1)
            return index1, index2, index3, index4

        levelCount = self.getLevelCount()
        levelDimensions = []
        for level in range(levelCount):
            layerInfo = so.GetLayerInfo(self.sdpc, level)
            count = 0
            byteList = []
            while (ord(layerInfo[count]) != 0):
                byteList.append(layerInfo[count])
                count += 1

            strList = [byteValue.decode('utf-8') for byteValue in byteList]
            str = ''.join(strList)

            equal1, equal2, equal3, equal4 = findStrIndex("=", str)
            line1, line2, line3, line4 = findStrIndex("|", str)

            rawWidth = int(str[equal1 + 1:line1])
            rawHeight = int(str[equal2 + 1:line2])
            boundWidth = int(str[equal3 + 1:line3])
            boundHeight = int(str[equal4 + 1:line4])
            w, h = rawWidth - boundWidth, rawHeight - boundHeight
            levelDimensions.append((w, h))

        return tuple(levelDimensions)

    def close(self):

        so.SqCloseSdpc(self.sdpc)

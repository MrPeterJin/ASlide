import ctypes
from ctypes import *

class SqPicHead(Structure):
    _pack_ = 1
    _fields_ = [
        ('flag', c_ushort),
        ('version', c_ubyte*16),
        ('headSize', c_uint32),
        ('fileSize', c_int64),

        ('macrograph', c_uint32),
        ('personInfor', c_uint32),
        ('hierarchy', c_uint32),
        ('srcWidth', c_uint32),
        ('srcHeight', c_uint32),
        ('sliceWidth', c_uint32),
        ('sliceHeight', c_uint32),
        ('thumbnailWidth', c_uint32),
        ('thumbnailHeight', c_uint32),

        ('bpp', c_ubyte),
        ('quality', c_ubyte),
        ('colrSpace', c_ubyte*4),
        ('scale', c_float),
        ('ruler', c_double),
        ('rate', c_uint32),
        ('extraOffset', c_int64),
        ('tileOffset', c_int64),
        ('sliceFormat', c_ubyte),
        ('headSpace', c_ubyte*48)
    ]

class SqPersonInfo(Structure):
    _pack_ = 1
    _fields_ = [
        ('flag', c_ushort),
        ('inforSize', c_uint),
        ('pathologyID', c_ubyte*64),
        ('name', c_ubyte*64),
        ('sex', c_ubyte),
        ('age', c_ubyte),
        ('departments', c_ubyte * 64),
        ('hospital', c_ubyte * 64),
        ('submittedSamples', c_ubyte*1024),
        ('clinicalDiagnosis', c_ubyte*2048),
        ('pathologicalDiagnosis', c_ubyte * 2048),
        ('reportDate', c_ubyte * 64),
        ('attendingDoctor', c_ubyte * 64),
        ('remark', c_ubyte * 1024),
        ('nexOffset', c_int64),
        ('reserved_1', c_uint),
        ('reserved_2', c_uint),
        ('reserved', c_ubyte*256)
    ]

class SqExtraInfo(Structure):
    _pack_ = 1
    _fields_ = [
        ('flag', c_short),
        ('inforSize', c_uint),
        ('nextOffset', c_int64),
        ('model', c_ubyte*20),
        ('ccmGamma', c_float),
        ('ccmRgbRate', c_float*3),
        ('ccmHsvRate', c_float*3),
        ('ccm', c_float*9),
        ('timeConsuming', c_ubyte*32),
        ('scanTime', c_uint),
        ('stepTime', c_ushort*10),
        ('serial', c_ubyte*32),
        ('fusionLayer', c_ubyte),
        ('step', c_float),
        ('focusPoint', c_ushort),
        ('validFocusPoint', c_ushort),
        ('barCode', c_ubyte*128),
        ('cameraGamma', c_float),
        ('cameraExposure', c_float),
        ('cameraGain', c_float),
        ('reserved', c_ubyte*433)
    ]

class SqImageInfo(Structure):
    _pack_ = 1
    _fileds_ = [
        ('stream', c_char_p), #unsigned char *
        ('bgr', c_char_p), #unsigned char *
        ('width', c_int),
        ('height', c_int),
        ('channel', c_int),
        ('format', c_ubyte),
        ('colorSpace', c_ubyte*4),
        ('streamSize', c_int)
    ]

class SqPicInfo(Structure):
    _pack_ = 1
    _fields_ = [
        ('flag', c_ushort),
        ('infoSize', c_uint),
        ('layer', c_uint),
        ('sliceNum', c_uint),
        ('sliceNumX', c_uint),
        ('slideNumY', c_uint),
        ('layerSize', c_int64),
        ('nextLayerOffset', c_int64),
        ('curScale', c_float),
        ('ruler', c_double),
        ('defaultX', c_uint),
        ('defaultY', c_uint),
        ('format', c_ubyte),
        ('headSpace', c_ubyte*63)
    ]

class SqSliceInfo(Structure):
    _pack_ = 1
    _fileds_ = [
        ('sliceOffset', POINTER(c_uint64)),
        ('sliceSize', POINTER(c_uint))
    ]

class SqSdpcInfo(Structure):
    _pack_ = 1
    _fields_ = [
        ('fileName', c_char_p),
        ('picHead', POINTER(SqPicHead)),
        ('personInfo', POINTER(SqPersonInfo)),
        ('extra', POINTER(SqExtraInfo)),
        ('macrograph', POINTER(POINTER(SqImageInfo))),
        ('thmbnail', POINTER(SqImageInfo)),
        ('sliceLayerInfo', POINTER(POINTER(SqPicInfo))),
        ('sliceInfo', POINTER(POINTER(SqSliceInfo)))
    ]
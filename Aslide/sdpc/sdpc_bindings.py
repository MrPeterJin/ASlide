"""Python bindings for the native SDPC SDK."""
from __future__ import annotations

import ctypes
from ctypes import *
import os

# Load the SDPC SDK shared library bundled with Aslide
dirname = os.path.dirname(os.path.abspath(__file__))
sdk_lib_path = os.path.join(dirname, 'lib', 'libsqrayslideservice.so')

if not os.path.exists(sdk_lib_path):
    raise RuntimeError(f"SDPC SDK library not found at: {sdk_lib_path}")

# Load the library
sdpc_sdk = ctypes.CDLL(sdk_lib_path)

# Backwards compatibility alias for legacy imports
sqrayslide = sdpc_sdk  # type: ignore

# Define basic types
SlideImage = c_void_p
c_int32 = c_int32
c_uint32 = c_uint32

# Define structures
class SDPCChannelInfo(Structure):
    _pack_ = 1
    _fields_ = [
        ('ID', c_int32),
        ('Nickname', c_ubyte * 64),
        ('Cube', c_ubyte * 64),
        ('CWL', c_int32),
        ('EXWL', c_int32),
        ('CWL_BW', c_int32),
    ]


# Legacy export names preserved for compatibility
SqChannelInfo = SDPCChannelInfo

class ReadingOptions(Structure):
    _pack_ = 1
    _fields_ = [
        ('mode', c_int32),
    ]

class TileRect(Structure):
    _pack_ = 1
    _fields_ = [
        ('X', c_int32),
        ('Y', c_int32),
        ('Width', c_int32),
        ('Height', c_int32),
        ('Level', c_int32),
    ]

# Basic interfaces
sdpc_sdk.sqrayslide_always_true.restype = c_bool

sdpc_sdk.sqrayslide_open.argtypes = [c_char_p, POINTER(c_int)]
sdpc_sdk.sqrayslide_open.restype = SlideImage

sdpc_sdk.sqrayslide_open2.argtypes = [c_char_p, POINTER(c_int), c_int]
sdpc_sdk.sqrayslide_open2.restype = SlideImage

sdpc_sdk.sqrayslide_free_memory.argtypes = [POINTER(c_ubyte)]
sdpc_sdk.sqrayslide_free_memory.restype = None

sdpc_sdk.sqrayslide_close.argtypes = [SlideImage]
sdpc_sdk.sqrayslide_close.restype = None

# Label interfaces
sdpc_sdk.sqrayslide_read_label_jpeg.argtypes = [
    SlideImage, c_int, POINTER(c_int32), POINTER(c_int32), 
    POINTER(POINTER(c_ubyte)), POINTER(c_int32)
]
sdpc_sdk.sqrayslide_read_label_jpeg.restype = c_bool

# Properties interfaces
sdpc_sdk.sqrayslide_get_type.argtypes = [SlideImage]
sdpc_sdk.sqrayslide_get_type.restype = c_int  # WSI_TYPE

sdpc_sdk.sqrayslide_get_tile_size.argtypes = [SlideImage, POINTER(c_int32), POINTER(c_int32)]
sdpc_sdk.sqrayslide_get_tile_size.restype = None

sdpc_sdk.sqrayslide_get_mpp.argtypes = [SlideImage, POINTER(c_double), POINTER(c_double)]
sdpc_sdk.sqrayslide_get_mpp.restype = None

sdpc_sdk.sqrayslide_get_magnification.argtypes = [SlideImage, POINTER(c_float)]
sdpc_sdk.sqrayslide_get_magnification.restype = None

sdpc_sdk.sqrayslide_get_barcode.argtypes = [SlideImage]
sdpc_sdk.sqrayslide_get_barcode.restype = c_char_p

# Level interfaces
sdpc_sdk.sqrayslide_get_level_count.argtypes = [SlideImage]
sdpc_sdk.sqrayslide_get_level_count.restype = c_int32

sdpc_sdk.sqrayslide_get_level_size.argtypes = [SlideImage, c_int32, POINTER(c_int32), POINTER(c_int32)]
sdpc_sdk.sqrayslide_get_level_size.restype = None

sdpc_sdk.sqrayslide_get_level_right_buttom_bounds_size.argtypes = [
    SlideImage, c_int32, POINTER(c_int32), POINTER(c_int32)
]
sdpc_sdk.sqrayslide_get_level_right_buttom_bounds_size.restype = None

sdpc_sdk.sqrayslide_get_level_tile_count.argtypes = [
    SlideImage, c_int32, POINTER(c_int32), POINTER(c_int32)
]
sdpc_sdk.sqrayslide_get_level_tile_count.restype = None

sdpc_sdk.sqrayslide_get_level_downsample.argtypes = [SlideImage, c_int32]
sdpc_sdk.sqrayslide_get_level_downsample.restype = c_double

sdpc_sdk.sqrayslide_get_best_level_for_downsample.argtypes = [SlideImage, c_double]
sdpc_sdk.sqrayslide_get_best_level_for_downsample.restype = c_int32

# Reading image data interfaces
sdpc_sdk.sqrayslide_read_region_bgra.argtypes = [
    SlideImage, POINTER(c_ubyte), c_int32, c_int32, c_int32, c_int32, c_int32
]
sdpc_sdk.sqrayslide_read_region_bgra.restype = c_bool

sdpc_sdk.sqrayslide_read_tile_bgra.argtypes = [
    SlideImage, POINTER(c_ubyte), c_int32, c_int32, c_int32
]
sdpc_sdk.sqrayslide_read_tile_bgra.restype = c_bool

sdpc_sdk.sqrayslide_read_tile_jpeg.argtypes = [
    SlideImage, POINTER(POINTER(c_ubyte)), c_int32, c_int32, c_int32
]
sdpc_sdk.sqrayslide_read_tile_jpeg.restype = c_int32

# Extended interfaces
sdpc_sdk.sqrayslide_bgra_to_jpeg.argtypes = [
    POINTER(c_ubyte), POINTER(c_int32), c_int32, c_int32, c_int32
]
sdpc_sdk.sqrayslide_bgra_to_jpeg.restype = POINTER(c_ubyte)

sdpc_sdk.sqrayslide_set_jpeg_quality.argtypes = [SlideImage, c_int32]
sdpc_sdk.sqrayslide_set_jpeg_quality.restype = None

# Color correction interfaces
sdpc_sdk.sqrayslide_apply_color_correction.argtypes = [SlideImage, c_bool, c_int]
sdpc_sdk.sqrayslide_apply_color_correction.restype = None

# Channel interfaces
sdpc_sdk.sqrayslide_get_channel_count.argtypes = [SlideImage]
sdpc_sdk.sqrayslide_get_channel_count.restype = c_int32

sdpc_sdk.sqrayslide_get_channel_Info.argtypes = [SlideImage, c_int32, POINTER(SDPCChannelInfo)]
sdpc_sdk.sqrayslide_get_channel_Info.restype = c_bool

# Focal plane interfaces
sdpc_sdk.sqrayslide_get_plane_count.argtypes = [SlideImage]
sdpc_sdk.sqrayslide_get_plane_count.restype = c_int32

sdpc_sdk.sqrayslide_get_plane_space_between.argtypes = [SlideImage]
sdpc_sdk.sqrayslide_get_plane_space_between.restype = c_float

# Error codes (from vendor headers)
class SDPCError:
    SqSuccess = 0
    SqFileFormatError = -1
    SqOpenFileError = -2
    SqReadFileError = -3
    SqWriteFileError = -4
    SqJpegFormatError = -5
    SqEncodeJpegError = -6
    SqDecodeJpegError = -7
    # ... more error codes as needed

# Legacy alias
SqError = SDPCError

# WSI Types
class SDPCWSIType:
    Brightfield = 0
    Fluorescence = 1

# Legacy alias
WSI_TYPE = SDPCWSIType

# Color styles
class ColorStyle:
    Real = 1
    Gorgeous = 2

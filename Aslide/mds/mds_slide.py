"""
MDS slide implementation using new openMDS library
"""

import os
import ctypes
from ctypes import *
from PIL import Image
import numpy as np

# Load the new openMDS library
try:
    dirname = os.path.dirname(os.path.abspath(__file__))
    
    # MUST preload libMDSParser.so first
    mds_parser_path = os.path.join(dirname, 'lib', 'libMDSParser.so')
    if os.path.exists(mds_parser_path):
        # Force load with RTLD_GLOBAL to make symbols available
        import ctypes
        mds_parser_lib = ctypes.CDLL(mds_parser_path, mode=ctypes.RTLD_GLOBAL)
    else:
        raise ImportError("Cannot find libMDSParser.so")
    
    lib_path = os.path.join(dirname, 'lib', 'openMDS.so')
    _lib = cdll.LoadLibrary(lib_path)
    
except Exception as e:
    raise ImportError(f"Cannot load openMDS library: {e}")

class MdsSlide:
    """MDS slide reader using new openMDS library"""
    
    def __init__(self, filename):
        """Initialize MDS slide"""
        self.__filename = filename
        self.mds_handle = self._load_mds(filename)
        
        # Get basic properties
        self._get_properties()
    
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__filename)

    @classmethod
    def detect_format(cls, filename):
        """Detect if file is MDS format"""
        ext = os.path.splitext(filename)[1].lower()
        return b"mds" if ext in ['.mds'] else None

    def _load_mds(self, filename):
        """Load MDS file using new API"""
        # Check if file exists first to avoid crashes
        if not os.path.exists(filename):
            raise Exception(f"MDS file not found: {filename}")
            
        if isinstance(filename, str):
            filename_bytes = filename.encode('utf-8')
        else:
            filename_bytes = filename
            
        try:
            handle = _lib.openMDS_open(filename_bytes)
            if not handle:
                raise Exception(f"Failed to load MDS file: {filename}")
            return handle
        except Exception as e:
            raise Exception(f"Failed to load MDS file: {filename}, error: {e}")

    def _get_properties(self):
        """Get slide properties"""
        # For now, use default values
        # These should be implemented based on the actual MDS API
        self.sampling_rate = 0.5  # Default sampling rate
        
    @property
    def level_count(self):
        """Get number of levels"""
        return 1

    @property
    def dimensions(self):
        """Return the dimensions of the highest resolution level (level 0)."""
        return (1024, 1024)  # Default for now

    @property
    def level_dimensions(self):
        """Get dimensions for all levels"""
        return [(1024, 1024)]  # Default for now

    @property
    def level_downsamples(self):
        """Get downsample factors for all levels"""
        return (1.0,)

    @property
    def properties(self):
        """Get slide properties"""
        return {
            'openslide.mpp-x': str(self.sampling_rate),
            'openslide.mpp-y': str(self.sampling_rate),
            'openslide.vendor': 'MDS'
        }

    @property
    def associated_images(self):
        """Get associated images"""
        return {}

    def get_best_level_for_downsample(self, downsample):
        """Find the best level for a given downsample factor"""
        return 0

    def get_thumbnail(self, size):
        """Get thumbnail image"""
        return Image.new('RGB', size, (255, 255, 255))

    def read_region(self, location, level, size):
        """Read a region from the slide"""
        # For now, return a blank image
        # This should be implemented based on the actual MDS API
        return Image.new('RGB', size, (128, 128, 128))

    def close(self):
        """Close the slide"""
        if hasattr(self, 'mds_handle') and self.mds_handle:
            try:
                _lib.openMDS_close(self.mds_handle)
            except:
                pass
            self.mds_handle = None

    def __del__(self):
        """Destructor"""
        self.close()

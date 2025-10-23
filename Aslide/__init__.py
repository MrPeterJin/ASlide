# First set up environment variables
import os
import sys
import ctypes

# Set up environment variables directly in __init__.py
def setup_environment():
    """Set up environment variables for Aslide."""
    current_path = os.path.dirname(os.path.abspath(__file__))
    lib_paths = [
        os.path.join(current_path, 'opencv', 'lib'),  # OpenCV must be loaded first
        os.path.join(current_path, 'sdpc', 'lib'),
        os.path.join(current_path, 'kfb', 'lib'),
        os.path.join(current_path, 'tmap', 'lib')
        # MDS uses pure Python olefile, no native libraries needed
    ]

    # Include optional subdirectories if they exist
    optional_subdirs = [
        os.path.join(current_path, 'sdpc', 'lib', 'ffmpeg'),
        os.path.join(current_path, 'sdpc', 'so', 'ffmpeg')
    ]

    for subdir in optional_subdirs:
        if os.path.isdir(subdir):
            lib_paths.append(subdir)

    # Add to LD_LIBRARY_PATH
    current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
    new_ld_path = ":".join(lib_paths + [current_ld_path]) if current_ld_path else ":".join(lib_paths)
    os.environ["LD_LIBRARY_PATH"] = new_ld_path

    # Directly load libraries using ctypes to ensure they are found
    try:
        # Preload OpenCV libraries first in the correct order
        # Only load essential libraries to avoid conflicts with conda/system libraries
        opencv_lib_path = os.path.join(current_path, 'opencv', 'lib')
        if os.path.exists(opencv_lib_path):
            # Only load core libraries that are actually needed
            # Skip highgui and other GUI-related libraries that may conflict with conda
            opencv_libs_order = [
                'libopencv_core.so.3.4',
                'libopencv_imgproc.so.3.4',
                'libopencv_imgcodecs.so.3.4',
            ]
            for lib_name in opencv_libs_order:
                lib_file = os.path.join(opencv_lib_path, lib_name)
                if os.path.exists(lib_file):
                    try:
                        ctypes.CDLL(lib_file, mode=ctypes.RTLD_GLOBAL)
                    except Exception as e:
                        # If loading fails, it might be due to conda conflicts
                        # Try to continue anyway as the system might have compatible versions
                        pass

        # Try to preload other critical libraries
        for lib_path in lib_paths:
            if os.path.exists(lib_path) and 'opencv' not in lib_path:
                for lib_file in os.listdir(lib_path):
                    if lib_file.endswith(".so"):
                        try:
                            full_path = os.path.join(lib_path, lib_file)
                            ctypes.CDLL(full_path)
                        except Exception as e:
                            pass  # Silently continue if a library fails to load
    except Exception as e:
        print(f"Warning: Error preloading libraries: {e}")

    # Also add to system path for ctypes to find libraries
    for path in lib_paths:
        if path not in sys.path:
            sys.path.append(path)

# Run setup before importing submodules
setup_environment()

# Now import submodules - keep original imports to maintain compatibility
from . import kfb
from . import tmap
from . import sdpc
from . import vsi
from . import mds

try:
    from . import qptiff
except ImportError:
    print("Warning: QPTiff module not available (qptifffile library required)")

try:
    from . import isyntax
except ImportError:
    print("Warning: iSyntax module not available (pyisyntax library required)")

from . import aslide

# Export the main Slide class for easy access
from .aslide import Slide
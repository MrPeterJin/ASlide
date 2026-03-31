# First set up environment variables
import os
import sys
import ctypes


# Set up environment variables directly in __init__.py
def setup_environment():
    """Set up environment variables for Aslide."""
    current_path = os.path.dirname(os.path.abspath(__file__))
    lib_paths = [
        os.path.join(current_path, "opencv", "lib"),  # OpenCV must be loaded first
        os.path.join(current_path, "sdpc", "lib"),
        os.path.join(current_path, "kfb", "lib"),
        os.path.join(current_path, "tmap", "lib"),
        # MDS uses pure Python olefile, no native libraries needed
    ]

    # Include optional subdirectories if they exist
    optional_subdirs = [
        os.path.join(current_path, "sdpc", "lib", "ffmpeg"),
        os.path.join(current_path, "sdpc", "so", "ffmpeg"),
    ]

    for subdir in optional_subdirs:
        if os.path.isdir(subdir):
            lib_paths.append(subdir)

    # Add to LD_LIBRARY_PATH
    current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
    new_ld_path = (
        ":".join(lib_paths + [current_ld_path])
        if current_ld_path
        else ":".join(lib_paths)
    )
    os.environ["LD_LIBRARY_PATH"] = new_ld_path

    # Directly load libraries using ctypes to ensure they are found
    try:
        # Preload dependencies and OpenCV libraries in the correct order
        opencv_lib_path = os.path.join(current_path, "opencv", "lib")
        if os.path.exists(opencv_lib_path):
            # First, load all dependencies (image format libs, OpenEXR, compression libs)
            # These must be loaded before OpenCV imgcodecs and TMAP
            dependency_libs = [
                # Image format libraries (for OpenCV imgcodecs)
                "libjpeg.so.8",
                "libpng16.so.16",
                "libwebp.so.7",
                # Compression libraries (for libtiff)
                "libjbig.so.0",
                "liblzma.so.5",
                "libzstd.so.1",
                "libdeflate.so.0",
                # TIFF (depends on compression libs)
                "libtiff.so.5",
                # OpenEXR libraries (for TMAP)
                "libImath-2_5.so.25",
                "libHalf-2_5.so.25",
                "libIex-2_5.so.25",
                "libIlmThread-2_5.so.25",
                "libIlmImf-2_5.so.25",
            ]

            for lib_name in dependency_libs:
                lib_file = os.path.join(opencv_lib_path, lib_name)
                if os.path.exists(lib_file):
                    try:
                        ctypes.CDLL(lib_file, mode=ctypes.RTLD_GLOBAL)
                    except Exception:
                        # Silently ignore - may already be loaded from system
                        pass

            # Now load OpenCV libraries in order
            # Only load essential libraries to avoid conflicts with conda/system libraries
            opencv_libs_order = [
                "libopencv_core.so.3.4",
                "libopencv_imgproc.so.3.4",
                "libopencv_imgcodecs.so.3.4",
            ]
            opencv_loaded = []
            for lib_name in opencv_libs_order:
                lib_file = os.path.join(opencv_lib_path, lib_name)
                if os.path.exists(lib_file):
                    try:
                        ctypes.CDLL(lib_file, mode=ctypes.RTLD_GLOBAL)
                        opencv_loaded.append(lib_name)
                    except Exception as e:
                        # Print warning but don't fail - some environments may have system OpenCV
                        import warnings

                        warnings.warn(f"Failed to load bundled {lib_name}: {e}")

            # Verify at least core libraries loaded
            if len(opencv_loaded) < 3:
                import warnings

                warnings.warn(
                    f"Only {len(opencv_loaded)}/3 core OpenCV libraries loaded. "
                    f"This may cause issues with KFB/TMAP/SDPC formats. "
                    f"Loaded: {opencv_loaded}"
                )

        # Load bundled FFmpeg libs in dependency order with RTLD_GLOBAL.
        # Order matters: libavutil must be registered under its soname before libavcodec
        # is loaded, or the linker will resolve libavutil.so.56 from the system path
        # (potentially an older version missing av_film_grain_params_create_side_data).
        sdpc_lib_path = os.path.join(current_path, "sdpc", "lib")
        if os.path.exists(sdpc_lib_path):
            _ffmpeg_load_order = [
                "libavutil.so.56.60.100",
                "libswresample.so.3.8.100",
                "libswscale.so.5.8.100",
                "libx264.so.148",
                "libx265.so.79",
                "libavcodec.so.58.111.100",
                "libavformat.so.58.62.100",
                "libavfilter.so.7.87.100",
            ]
            for _lib_name in _ffmpeg_load_order:
                _lib_file = os.path.join(sdpc_lib_path, _lib_name)
                if os.path.exists(_lib_file):
                    try:
                        ctypes.CDLL(_lib_file, mode=ctypes.RTLD_GLOBAL)
                    except Exception:
                        pass
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

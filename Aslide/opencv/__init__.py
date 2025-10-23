"""
OpenCV 3.4.2 bundled libraries for ASlide.

This module provides OpenCV 3.4.2 shared libraries bundled with ASlide
to avoid requiring system-wide OpenCV installation.
"""
import os
import sys
import ctypes

def setup_opencv_environment():
    """
    Set up environment to use bundled OpenCV libraries.
    This function should be called before importing any modules that depend on OpenCV.
    """
    # Get the directory containing this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    lib_dir = os.path.join(current_dir, 'lib')
    
    if not os.path.exists(lib_dir):
        raise RuntimeError(f"OpenCV library directory not found at: {lib_dir}")
    
    # Add to LD_LIBRARY_PATH
    current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    if lib_dir not in current_ld_path:
        if current_ld_path:
            os.environ['LD_LIBRARY_PATH'] = f"{lib_dir}:{current_ld_path}"
        else:
            os.environ['LD_LIBRARY_PATH'] = lib_dir
    
    # Add to sys.path for ctypes to find libraries
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    
    # Preload OpenCV libraries in the correct order
    # Only load essential core libraries to avoid conflicts with conda/system libraries
    # GUI-related libraries (highgui, videoio) are skipped as they often conflict with conda's glib
    opencv_libs = [
        'libopencv_core.so.3.4',
        'libopencv_imgproc.so.3.4',
        'libopencv_imgcodecs.so.3.4',
        # Skip GUI and video libraries that may conflict with conda environment:
        # 'libopencv_highgui.so.3.4',
        # 'libopencv_videoio.so.3.4',
        # 'libopencv_video.so.3.4',
        # Optional libraries - only load if needed:
        'libopencv_flann.so.3.4',
        'libopencv_features2d.so.3.4',
        'libopencv_calib3d.so.3.4',
        'libopencv_objdetect.so.3.4',
        'libopencv_photo.so.3.4',
        'libopencv_ml.so.3.4',
        'libopencv_dnn.so.3.4',
        'libopencv_shape.so.3.4',
        'libopencv_stitching.so.3.4',
        'libopencv_superres.so.3.4',
        # 'libopencv_videostab.so.3.4',
    ]
    
    loaded_libs = []
    for lib_name in opencv_libs:
        lib_path = os.path.join(lib_dir, lib_name)
        if os.path.exists(lib_path):
            try:
                # Use RTLD_GLOBAL to make symbols available to subsequently loaded libraries
                lib = ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)
                loaded_libs.append(lib_name)
            except Exception as e:
                # Don't fail if optional libraries can't be loaded
                pass
    
    return loaded_libs

# Auto-setup when importing this module
try:
    loaded = setup_opencv_environment()
    # print(f"Loaded bundled OpenCV libraries: {', '.join(loaded)}")
except Exception as e:
    import warnings
    warnings.warn(f"Failed to setup bundled OpenCV environment: {e}")

__all__ = ['setup_opencv_environment']


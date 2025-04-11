# First set up environment variables
import os
import sys
import ctypes

# Set up environment variables directly in __init__.py
def setup_environment():
    """Set up environment variables for Aslide."""
    current_path = os.path.dirname(os.path.abspath(__file__))
    lib_paths = [
        os.path.join(current_path, 'sdpc', 'so'),
        os.path.join(current_path, 'sdpc', 'so', 'ffmpeg'),
        os.path.join(current_path, 'kfb', 'lib'),
        os.path.join(current_path, 'tmap', 'lib')
    ]

    # Add to LD_LIBRARY_PATH
    current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
    new_ld_path = ":".join(lib_paths + [current_ld_path]) if current_ld_path else ":".join(lib_paths)
    os.environ["LD_LIBRARY_PATH"] = new_ld_path

    # Directly load libraries using ctypes to ensure they are found
    try:
        # Try to preload critical libraries
        for lib_path in lib_paths:
            if os.path.exists(lib_path):
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
from . import aslide
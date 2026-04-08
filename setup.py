#!/usr/bin/env python
# coding: utf-8

from setuptools import setup, find_packages
from setuptools.command.install import install
import os
import sys
import site
import subprocess


class CustomInstall(install):
    def run(self):
        install.run(self)
        # Handle OpenCV and dependency files
        opencv_lib_dir = os.path.join(
            os.path.dirname(__file__), "Aslide", "opencv", "lib"
        )
        if os.path.exists(opencv_lib_dir):
            target_dir = os.path.join(self.install_lib, "Aslide", "opencv", "lib")
            self.mkpath(target_dir)
            for lib_file in os.listdir(opencv_lib_dir):
                # Copy all .so files (OpenCV + dependencies like libjpeg, libpng, etc.)
                # RPATH is already set in source files and will be preserved during copy
                if ".so" in lib_file:
                    src_file = os.path.join(opencv_lib_dir, lib_file)
                    self.copy_file(src_file, target_dir)
        else:
            print(
                f"Warning: OpenCV library directory {opencv_lib_dir} not found. Skipping."
            )

        # Handle KFB files
        kfb_so_files = [
            "libcurl.so",
            "libImageOperationLib.so",
            "libjpeg.so.9",
            "libkfbslide.so",
        ]
        target_dir = os.path.join(self.install_lib, "Aslide", "kfb", "lib")
        self.mkpath(target_dir)
        for so_file in kfb_so_files:
            src_file = os.path.join(
                os.path.dirname(__file__), "Aslide", "kfb", "lib", so_file
            )
            if os.path.exists(src_file):
                self.copy_file(src_file, target_dir)
            else:
                print(f"Warning: Source file {src_file} not found. Skipping.")

        # Handle TRON files
        target_dir = os.path.join(self.install_lib, "Aslide", "tron", "lib")
        self.mkpath(target_dir)
        tron_files = ["libtronc.so", "tronc.h"]
        for tron_file in tron_files:
            src_file = os.path.join(
                os.path.dirname(__file__), "Aslide", "tron", "lib", tron_file
            )
            if os.path.exists(src_file):
                self.copy_file(src_file, target_dir)
            else:
                print(f"Warning: Source file {src_file} not found. Skipping.")

        # Handle SDPC files (native SDPC SDK)
        src_base_dir = os.path.join(os.path.dirname(__file__), "Aslide", "sdpc", "lib")
        dst_base_dir = os.path.join(self.install_lib, "Aslide", "sdpc", "lib")

        if not os.path.exists(src_base_dir):
            print(
                f"Warning: Source directory {src_base_dir} not found. Skipping SDPC files."
            )
            return

        self.mkpath(dst_base_dir)

        for root, dirs, files in os.walk(src_base_dir):
            rel_path = os.path.relpath(root, src_base_dir)
            if rel_path == ".":
                target_subdir = dst_base_dir
            else:
                target_subdir = os.path.join(dst_base_dir, rel_path)
                self.mkpath(target_subdir)

            for file in files:
                src_file = os.path.join(root, file)
                self.copy_file(src_file, target_subdir)

        # Copy SDPC headers (include directory)
        include_src_dir = os.path.join(
            os.path.dirname(__file__), "Aslide", "sdpc", "include"
        )
        include_dst_dir = os.path.join(self.install_lib, "Aslide", "sdpc", "include")

        if not os.path.exists(include_src_dir):
            print(
                f"Warning: Source directory {include_src_dir} not found. Skipping SDPC headers."
            )
        else:
            self.mkpath(include_dst_dir)
            for root, dirs, files in os.walk(include_src_dir):
                rel_path = os.path.relpath(root, include_src_dir)
                if rel_path == ".":
                    target_subdir = include_dst_dir
                else:
                    target_subdir = os.path.join(include_dst_dir, rel_path)
                self.mkpath(target_subdir)

                for file in files:
                    src_file = os.path.join(root, file)
                    self.copy_file(src_file, target_subdir)

        sdpc_lib_dst = os.path.join(self.install_lib, "Aslide", "sdpc", "lib")
        self._patch_rpath_origin(sdpc_lib_dst)
        self.setup_environment_variables()

    def _patch_rpath_origin(self, lib_dir):
        if not os.path.isdir(lib_dir):
            return
        try:
            if (
                subprocess.run(["which", "patchelf"], capture_output=True).returncode
                != 0
            ):
                print(
                    "Warning: patchelf not found — bundled libs may pick up system FFmpeg. "
                    "Install patchelf (apt install patchelf) and reinstall Aslide."
                )
                return
            count = 0
            for root, _, files in os.walk(lib_dir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    if (
                        ".so" in fname
                        and os.path.isfile(fpath)
                        and not os.path.islink(fpath)
                    ):
                        if (
                            subprocess.run(
                                ["patchelf", "--set-rpath", "$ORIGIN", fpath],
                                capture_output=True,
                            ).returncode
                            == 0
                        ):
                            count += 1
            print(f"Patched RUNPATH for {count} bundled libraries.")
        except Exception as e:
            print(f"Warning: patchelf RUNPATH patching failed: {e}")

    def _collect_library_paths(self, install_dir):
        """Collect all directories that contain shared libraries for runtime loading."""
        vendors = [("opencv", "lib"), ("sdpc", "lib"), ("kfb", "lib"), ("tron", "lib")]

        lib_paths = []
        seen = set()

        def add_path(path):
            if path not in seen and os.path.isdir(path):
                seen.add(path)
                lib_paths.append(path)

        for vendor in vendors:
            base_dir = os.path.join(install_dir, "Aslide", *vendor)
            if not os.path.isdir(base_dir):
                continue

            # Always include the base directory even if shared libraries are nested
            add_path(base_dir)

            for root, _, files in os.walk(base_dir):
                if any(file.endswith(".so") for file in files):
                    add_path(root)

        return lib_paths

    def setup_environment_variables(self):
        """Set up environment variables for the installed libraries."""
        # Get the installation directory
        install_dir = os.path.abspath(self.install_lib)

        # Paths to add to LD_LIBRARY_PATH (including nested directories with shared libs)
        lib_paths = self._collect_library_paths(install_dir)

        # Create a setup script that can be sourced
        setup_script_path = os.path.join(install_dir, "Aslide", "setup_env.sh")
        with open(setup_script_path, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("# Aslide environment setup script\n\n")

            # Add the library paths to LD_LIBRARY_PATH
            lib_paths_str = ":".join(lib_paths)
            if lib_paths_str:
                f.write(f"export LD_LIBRARY_PATH={lib_paths_str}:$LD_LIBRARY_PATH\n")
            else:
                f.write("export LD_LIBRARY_PATH=$LD_LIBRARY_PATH\n")
            f.write('echo "Aslide environment variables have been set up."\n')

        os.chmod(setup_script_path, 0o755)  # Make it executable

        # Create a Python module to set up environment in code
        env_module_path = os.path.join(install_dir, "Aslide", "set_env.py")
        with open(env_module_path, "w") as f:
            f.write("import os\n")
            f.write("import sys\n")
            f.write("import ctypes\n\n")
            f.write("def setup_environment():\n")
            f.write('    """Set up environment variables for Aslide.\n')
            f.write("    Call this function before importing Aslide components.\n")
            f.write('    """\n')
            f.write("    current_path = os.path.dirname(os.path.abspath(__file__))\n")
            f.write("    lib_paths = [\n")
            aslide_root = os.path.join(install_dir, "Aslide")
            for path in lib_paths:
                rel_path = os.path.relpath(path, aslide_root)
                f.write(f'        os.path.join(current_path, "{rel_path}"),\n')
            f.write("    ]\n\n")
            f.write("    # Add to LD_LIBRARY_PATH\n")
            f.write('    current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")\n')
            f.write("    lib_entries = [path for path in lib_paths if path]\n")
            f.write("    if current_ld_path:\n")
            f.write("        lib_entries.append(current_ld_path)\n")
            f.write('    os.environ["LD_LIBRARY_PATH"] = ":".join(lib_entries)\n\n')
            f.write(
                "    # Directly load libraries using ctypes to ensure they are found\n"
            )
            f.write("    try:\n")
            f.write("        # Try to preload critical libraries\n")
            f.write("        for lib_path in lib_paths:\n")
            f.write("            if os.path.exists(lib_path):\n")
            f.write("                for lib_file in os.listdir(lib_path):\n")
            f.write('                    if lib_file.endswith(".so"):\n')
            f.write("                        try:\n")
            f.write(
                "                            full_path = os.path.join(lib_path, lib_file)\n"
            )
            f.write("                            ctypes.CDLL(full_path)\n")
            f.write("                        except Exception as e:\n")
            f.write(
                "                            pass  # Silently continue if a library fails to load\n"
            )
            f.write("    except Exception as e:\n")
            f.write('        print(f"Warning: Error preloading libraries: {e}")\n\n')
            f.write("    # Also add to system path for ctypes to find libraries\n")
            f.write("    for path in lib_paths:\n")
            f.write("        if path not in sys.path:\n")
            f.write("            sys.path.append(path)\n")
            f.write("\n# Auto-setup when importing this module\n")
            f.write("setup_environment()\n")

        # Create a ldconfig configuration file
        ldconfig_dir = "/etc/ld.so.conf.d"
        if os.path.isdir(ldconfig_dir) and os.access(ldconfig_dir, os.W_OK):
            try:
                ldconfig_file = os.path.join(ldconfig_dir, "aslide.conf")
                with open(ldconfig_file, "w") as f:
                    for path in lib_paths:
                        f.write(f"{path}\n")
                # Run ldconfig to update the cache
                try:
                    subprocess.run(["ldconfig"], check=True)
                    print("\nSuccessfully created system-wide library configuration.")
                except subprocess.CalledProcessError:
                    print(
                        "\nWarning: Failed to run ldconfig. Libraries may not be found system-wide."
                    )
            except Exception as e:
                print(f"\nWarning: Could not create ldconfig file: {e}")

        # We'll skip modifying the __init__.py file since we've already added the environment setup code directly
        # This avoids potential import conflicts

        # Create a .pth file to add library paths to LD_LIBRARY_PATH
        # This is a more reliable approach than modifying Python imports
        site_packages = site.getsitepackages()
        for site_pkg in site_packages:
            if os.path.exists(site_pkg) and os.access(site_pkg, os.W_OK):
                pth_file = os.path.join(site_pkg, "aslide-paths.pth")
                try:
                    with open(pth_file, "w") as f:
                        # Just add the library paths to sys.path
                        for path in lib_paths:
                            f.write(f"{path}\n")
                    print(f"\nCreated library paths .pth file at {pth_file}")
                    break
                except Exception as e:
                    print(f"\nWarning: Could not create .pth file in {site_pkg}: {e}")

        # Print instructions for the user
        print("\n" + "=" * 80)
        print("Aslide has been successfully installed!")
        print("=" * 80)
        print("\nTo set up the environment variables for Aslide, you can:")
        print("\n1. Source the setup script before running your Python code:")
        print(f"   $ source {setup_script_path}")
        print(
            "\n2. Or call Aslide.bootstrap.setup_runtime_environment() explicitly in Python."
        )

        print("\nInstallation directory: " + install_dir)
        print("=" * 80 + "\n")


setup(
    name="Aslide",
    version="1.5.5",
    author="MrPeterJin",
    author_email="petergamsing@gmail.com",
    url="https://github.com/MrPeterJin/ASlide",
    description="A comprehensive package to read whole-slide image (WSI) files supporting Openslide, KFB, SDPC, DYQX, TMAP, MDS, VSI, QPTiff, TRON, iSyntax, DYJ, IBL, ZYP and BIF formats with full DeepZoom support.",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "Aslide": ["*.py"],
        "Aslide.opencv": ["lib/*"],
        "Aslide.kfb": ["*.py", "lib/*"],
        "Aslide.kfb.icc": ["*.icm"],
        "Aslide.tmap": ["*.py"],
        "Aslide.tmap.icc": ["*.icm"],
        "Aslide.sdpc": ["*.py", "lib/**/*", "include/**/*"],
        "Aslide.vsi": ["*.py", "**/*.py"],
        "Aslide.mds": ["*.py"],
        "Aslide.mds.icc": ["*.icm"],
        "Aslide.qptiff": ["*.py"],
        "Aslide.tron": ["*.py", "lib/*"],
        "Aslide.isyntax": ["*.py"],
        "Aslide.dyj": ["*.py"],
        "Aslide.dyj.lut": ["*.lut"],
        "Aslide.ibl": ["*.py"],
        "Aslide.zyp": ["*.py"],
        "Aslide.bif": ["*.py"],
        "Aslide.ome_tiff": ["*.py"],
        "Aslide.generic_tiff": ["*.py"],
        "Aslide.mcd": ["*.py"],
    },
    cmdclass={"install": CustomInstall},
    platforms="linux",
    install_requires=[
        "numpy",
        "Pillow",
        "openslide-bin",
        "openslide-python",
        "qptifffile",
        "tifffile",
        "readimc",
        "pyisyntax",
        "olefile",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
    ],
)

#!/usr/bin/env python
# coding: utf-8

from setuptools import setup, find_packages
from setuptools.command.install import install
import os
import sys
import site
import subprocess
from pathlib import Path

class CustomInstall(install):
    def run(self):
        install.run(self)
        # Handle OpenCV and dependency files
        opencv_lib_dir = os.path.join(os.path.dirname(__file__), 'Aslide', 'opencv', 'lib')
        if os.path.exists(opencv_lib_dir):
            target_dir = os.path.join(self.install_lib, 'Aslide', 'opencv', 'lib')
            self.mkpath(target_dir)
            for lib_file in os.listdir(opencv_lib_dir):
                # Copy all .so files (OpenCV + dependencies like libjpeg, libpng, etc.)
                # RPATH is already set in source files and will be preserved during copy
                if '.so' in lib_file:
                    src_file = os.path.join(opencv_lib_dir, lib_file)
                    self.copy_file(src_file, target_dir)
        else:
            print(f"Warning: OpenCV library directory {opencv_lib_dir} not found. Skipping.")

        # Handle KFB files
        kfb_so_files = ['libcurl.so', 'libImageOperationLib.so', 'libjpeg.so.9', 'libkfbslide.so']
        target_dir = os.path.join(self.install_lib, 'Aslide', 'kfb', 'lib')
        self.mkpath(target_dir)
        for so_file in kfb_so_files:
            src_file = os.path.join(os.path.dirname(__file__), 'Aslide', 'kfb', 'lib', so_file)
            if os.path.exists(src_file):
                self.copy_file(src_file, target_dir)
            else:
                print(f"Warning: Source file {src_file} not found. Skipping.")

        # Handle TRON files
        target_dir = os.path.join(self.install_lib, 'Aslide', 'tron', 'lib')
        self.mkpath(target_dir)
        tron_files = ['libtronc.so', 'tronc.h']
        for tron_file in tron_files:
            src_file = os.path.join(os.path.dirname(__file__), 'Aslide', 'tron', 'lib', tron_file)
            if os.path.exists(src_file):
                self.copy_file(src_file, target_dir)
            else:
                print(f"Warning: Source file {src_file} not found. Skipping.")

        # Handle SDPC files (native SDPC SDK)
        src_base_dir = os.path.join(os.path.dirname(__file__), 'Aslide', 'sdpc', 'lib')
        dst_base_dir = os.path.join(self.install_lib, 'Aslide', 'sdpc', 'lib')

        if not os.path.exists(src_base_dir):
            print(f"Warning: Source directory {src_base_dir} not found. Skipping SDPC files.")
            return

        self.mkpath(dst_base_dir)

        for root, dirs, files in os.walk(src_base_dir):
            rel_path = os.path.relpath(root, src_base_dir)
            if rel_path == '.':
                target_subdir = dst_base_dir
            else:
                target_subdir = os.path.join(dst_base_dir, rel_path)
                self.mkpath(target_subdir)

            for file in files:
                src_file = os.path.join(root, file)
                self.copy_file(src_file, target_subdir)

        # Copy SDPC headers (include directory)
        include_src_dir = os.path.join(os.path.dirname(__file__), 'Aslide', 'sdpc', 'include')
        include_dst_dir = os.path.join(self.install_lib, 'Aslide', 'sdpc', 'include')

        if not os.path.exists(include_src_dir):
            print(f"Warning: Source directory {include_src_dir} not found. Skipping SDPC headers.")
        else:
            self.mkpath(include_dst_dir)
            for root, dirs, files in os.walk(include_src_dir):
                rel_path = os.path.relpath(root, include_src_dir)
                if rel_path == '.':
                    target_subdir = include_dst_dir
                else:
                    target_subdir = os.path.join(include_dst_dir, rel_path)
                self.mkpath(target_subdir)

                for file in files:
                    src_file = os.path.join(root, file)
                    self.copy_file(src_file, target_subdir)

        self.setup_environment_variables()

    def _collect_library_paths(self, install_dir):
        """Collect all directories that contain shared libraries for runtime loading."""
        vendors = [
            ('opencv', 'lib'),
            ('sdpc', 'lib'),
            ('kfb', 'lib'),
            ('tron', 'lib')
        ]

        lib_paths = []
        seen = set()

        def add_path(path):
            if path not in seen and os.path.isdir(path):
                seen.add(path)
                lib_paths.append(path)

        for vendor in vendors:
            base_dir = os.path.join(install_dir, 'Aslide', *vendor)
            if not os.path.isdir(base_dir):
                continue

            # Always include the base directory even if shared libraries are nested
            add_path(base_dir)

            for root, _, files in os.walk(base_dir):
                if any(file.endswith('.so') for file in files):
                    add_path(root)

        return lib_paths

    def setup_environment_variables(self):
        """Set up environment variables for the installed libraries."""
        # Get the installation directory
        install_dir = os.path.abspath(self.install_lib)

        # Paths to add to LD_LIBRARY_PATH (including nested directories with shared libs)
        lib_paths = self._collect_library_paths(install_dir)

        # Create a setup script that can be sourced
        setup_script_path = os.path.join(install_dir, 'Aslide', 'setup_env.sh')
        with open(setup_script_path, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('# Aslide environment setup script\n\n')

            # Add the library paths to LD_LIBRARY_PATH
            lib_paths_str = ':'.join(lib_paths)
            if lib_paths_str:
                f.write(f'export LD_LIBRARY_PATH={lib_paths_str}:$LD_LIBRARY_PATH\n')
            else:
                f.write('export LD_LIBRARY_PATH=$LD_LIBRARY_PATH\n')
            f.write('echo "Aslide environment variables have been set up."\n')

        os.chmod(setup_script_path, 0o755)  # Make it executable

        # Create a Python module to set up environment in code
        env_module_path = os.path.join(install_dir, 'Aslide', 'set_env.py')
        with open(env_module_path, 'w') as f:
            f.write('import os\n')
            f.write('import sys\n')
            f.write('import ctypes\n\n')
            f.write('def setup_environment():\n')
            f.write('    """Set up environment variables for Aslide.\n')
            f.write('    Call this function before importing Aslide components.\n')
            f.write('    """\n')
            f.write('    current_path = os.path.dirname(os.path.abspath(__file__))\n')
            f.write('    lib_paths = [\n')
            aslide_root = os.path.join(install_dir, 'Aslide')
            for path in lib_paths:
                rel_path = os.path.relpath(path, aslide_root)
                f.write(f'        os.path.join(current_path, "{rel_path}"),\n')
            f.write('    ]\n\n')
            f.write('    # Add to LD_LIBRARY_PATH\n')
            f.write('    current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")\n')
            f.write('    lib_entries = [path for path in lib_paths if path]\n')
            f.write('    if current_ld_path:\n')
            f.write('        lib_entries.append(current_ld_path)\n')
            f.write('    os.environ["LD_LIBRARY_PATH"] = ":".join(lib_entries)\n\n')
            f.write('    # Directly load libraries using ctypes to ensure they are found\n')
            f.write('    try:\n')
            f.write('        # Try to preload critical libraries\n')
            f.write('        for lib_path in lib_paths:\n')
            f.write('            if os.path.exists(lib_path):\n')
            f.write('                for lib_file in os.listdir(lib_path):\n')
            f.write('                    if lib_file.endswith(".so"):\n')
            f.write('                        try:\n')
            f.write('                            full_path = os.path.join(lib_path, lib_file)\n')
            f.write('                            ctypes.CDLL(full_path)\n')
            f.write('                        except Exception as e:\n')
            f.write('                            pass  # Silently continue if a library fails to load\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"Warning: Error preloading libraries: {e}")\n\n')
            f.write('    # Also add to system path for ctypes to find libraries\n')
            f.write('    for path in lib_paths:\n')
            f.write('        if path not in sys.path:\n')
            f.write('            sys.path.append(path)\n')
            f.write('\n# Auto-setup when importing this module\n')
            f.write('setup_environment()\n')

        # Create a ldconfig configuration file
        ldconfig_dir = '/etc/ld.so.conf.d'
        if os.path.isdir(ldconfig_dir) and os.access(ldconfig_dir, os.W_OK):
            try:
                ldconfig_file = os.path.join(ldconfig_dir, 'aslide.conf')
                with open(ldconfig_file, 'w') as f:
                    for path in lib_paths:
                        f.write(f"{path}\n")
                # Run ldconfig to update the cache
                try:
                    subprocess.run(['ldconfig'], check=True)
                    print("\nSuccessfully created system-wide library configuration.")
                except subprocess.CalledProcessError:
                    print("\nWarning: Failed to run ldconfig. Libraries may not be found system-wide.")
            except Exception as e:
                print(f"\nWarning: Could not create ldconfig file: {e}")

        # We'll skip modifying the __init__.py file since we've already added the environment setup code directly
        # This avoids potential import conflicts

        # Create a .pth file to add library paths to LD_LIBRARY_PATH
        # This is a more reliable approach than modifying Python imports
        site_packages = site.getsitepackages()
        for site_pkg in site_packages:
            if os.path.exists(site_pkg) and os.access(site_pkg, os.W_OK):
                pth_file = os.path.join(site_pkg, 'aslide-paths.pth')
                try:
                    with open(pth_file, 'w') as f:
                        # Just add the library paths to sys.path
                        for path in lib_paths:
                            f.write(f"{path}\n")
                    print(f"\nCreated library paths .pth file at {pth_file}")
                    break
                except Exception as e:
                    print(f"\nWarning: Could not create .pth file in {site_pkg}: {e}")

        # Try to update the user's shell profile
        home = Path.home()
        shell_config_files = [
            home / '.bashrc',
            home / '.zshrc',
            home / '.bash_profile',
            home / '.profile'
        ]

        # Create a dynamic shell script that finds Aslide installation at runtime
        # This avoids hardcoding temporary build paths
        shell_script = '''
# Added by Aslide installation
# Dynamically find Aslide installation directory
_aslide_site_packages=$(python3 -c "import site; print(':'.join(site.getsitepackages()))" 2>/dev/null)
if [ -n "$_aslide_site_packages" ]; then
    IFS=':' read -ra _site_dirs <<< "$_aslide_site_packages"
    for _site_dir in "${_site_dirs[@]}"; do
        if [ -d "$_site_dir/Aslide" ]; then
            _aslide_paths=""
            for _vendor_lib in "$_site_dir/Aslide/opencv/lib" "$_site_dir/Aslide/sdpc/lib" "$_site_dir/Aslide/kfb/lib" "$_site_dir/Aslide/tron/lib"; do
                if [ -d "$_vendor_lib" ]; then
                    _aslide_paths="${_aslide_paths}:${_vendor_lib}"
                fi
            done
            if [ -n "$_aslide_paths" ]; then
                export LD_LIBRARY_PATH="${_aslide_paths#:}:$LD_LIBRARY_PATH"
            fi
            break
        fi
    done
fi
unset _aslide_site_packages _site_dirs _site_dir _vendor_lib _aslide_paths
'''

        shell_updated = False
        for config_file in shell_config_files:
            if config_file.exists() and os.access(config_file, os.W_OK):
                try:
                    # Check if the line already exists
                    with open(config_file, 'r') as f:
                        content = f.read()

                    # Remove old Aslide configuration if it exists
                    if 'Added by Aslide installation' in content:
                        lines = content.split('\n')
                        new_lines = []
                        skip_until_blank = False
                        for line in lines:
                            if 'Added by Aslide installation' in line:
                                skip_until_blank = True
                                continue
                            if skip_until_blank:
                                if line.strip() == '' or (not line.startswith('export LD_LIBRARY_PATH=') and
                                                          not line.startswith('_aslide') and
                                                          not line.startswith('if [') and
                                                          not line.startswith('    ') and
                                                          not line.startswith('fi') and
                                                          not line.startswith('done') and
                                                          not line.startswith('for ') and
                                                          not line.startswith('IFS=') and
                                                          not line.startswith('unset ')):
                                    skip_until_blank = False
                                    if line.strip() != '':
                                        new_lines.append(line)
                                continue
                            new_lines.append(line)
                        content = '\n'.join(new_lines)

                        # Write back the cleaned content
                        with open(config_file, 'w') as f:
                            f.write(content)

                    # Add the new dynamic configuration
                    with open(config_file, 'a') as f:
                        f.write(shell_script)
                    shell_updated = True
                    print(f"\nUpdated shell configuration file: {config_file}")
                    break
                except Exception as e:
                    print(f"\nWarning: Could not update shell config file {config_file}: {e}")

        # Print instructions for the user
        print("\n" + "="*80)
        print("Aslide has been successfully installed!")
        print("="*80)
        print("\nTo set up the environment variables for Aslide, you can:")

        if shell_updated:
            print("\n1. Restart your shell or run:")
            print(f"   $ source {config_file}")
            print("\n2. The LD_LIBRARY_PATH will be automatically set when you start a new shell session.")
        else:
            print("\n1. Import Aslide directly (environment will be set up automatically):")
            print("   >>> import Aslide")
            print("\n2. Source the setup script before running your Python code:")
            print(f"   $ source {setup_script_path}")
            print("\n3. Or manually add Aslide environment setup to your shell configuration file.")
            print("   The setup script will automatically find the Aslide installation directory.")

        print("\nInstallation directory: " + install_dir)
        print("="*80 + "\n")

setup(
    name='Aslide',
    version='1.5.4',
    author='MrPeterJin',
    author_email='petergamsing@gmail.com',
    url='https://github.com/MrPeterJin/ASlide',
    description='A comprehensive package to read whole-slide image (WSI) files supporting Openslide, KFB, SDPC, DYQX, TMAP, MDS, VSI, QPTiff, TRON, iSyntax, DYJ, IBL, ZYP and BIF formats with full DeepZoom support.',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'Aslide': ['*.py'],
        'Aslide.opencv': ['lib/*'],
        'Aslide.kfb': ['lib/*', 'icc/*.icm'],
        'Aslide.tmap': ['*.py', 'icc/*.icm'],
        'Aslide.sdpc': ['lib/**/*', 'include/**/*', '*.py'],
        'Aslide.vsi': ['*.py', '**/*.py'],
        'Aslide.mds': ['*.py', 'icc/*.icm'],
        'Aslide.qptiff': ['*.py'],
        'Aslide.tron': ['*.py', 'lib/*'],
        'Aslide.isyntax': ['*.py'],
        'Aslide.dyj': ['*.py', 'lut/*.lut'],
        'Aslide.ibl': ['*.py'],
        'Aslide.zyp': ['*.py'],
        'Aslide.bif': ['*.py'],
    },
    cmdclass={'install': CustomInstall},
    platforms='linux',
    install_requires=[
        'numpy',
        'Pillow',
        'openslide-bin',
        'openslide-python',
        'qptifffile',  # For QPTiff format support
        'tifffile',    # For QPTiff format support
        'pyisyntax',   # For iSyntax format support
        'olefile',     # For MDS format support
    ],
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: POSIX :: Linux',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
    ],
)
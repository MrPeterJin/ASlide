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
        
        # Handle TMAP files
        target_dir = os.path.join(self.install_lib, 'Aslide', 'tmap', 'lib')
        self.mkpath(target_dir)
        tmap_files = ['iViewerInterface.h', 'libiViewerSDK.so']
        for tmap_file in tmap_files:
            src_file = os.path.join(os.path.dirname(__file__), 'Aslide', 'tmap', 'lib', tmap_file)
            if os.path.exists(src_file):
                self.copy_file(src_file, target_dir)
            else:
                print(f"Warning: Source file {src_file} not found. Skipping.")
            
        # Handle SDPC files
        src_base_dir = os.path.join(os.path.dirname(__file__), 'Aslide', 'sdpc', 'so')
        dst_base_dir = os.path.join(self.install_lib, 'Aslide', 'sdpc', 'so')
        
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
        
        self.setup_environment_variables()
    
    def setup_environment_variables(self):
        """Set up environment variables for the installed libraries."""
        # Get the installation directory
        install_dir = os.path.abspath(self.install_lib)
        
        # Paths to add to LD_LIBRARY_PATH
        lib_paths = [
            os.path.join(install_dir, 'Aslide', 'sdpc', 'so'),
            os.path.join(install_dir, 'Aslide', 'sdpc', 'so', 'ffmpeg'),
            os.path.join(install_dir, 'Aslide', 'kfb', 'lib'),
            os.path.join(install_dir, 'Aslide', 'tmap', 'lib')
        ]
        
        # Create a setup script that can be sourced
        setup_script_path = os.path.join(install_dir, 'Aslide', 'setup_env.sh')
        with open(setup_script_path, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('# Aslide environment setup script\n\n')
            
            # Add the library paths to LD_LIBRARY_PATH
            lib_paths_str = ':'.join(lib_paths)
            f.write(f'export LD_LIBRARY_PATH={lib_paths_str}:$LD_LIBRARY_PATH\n')
            f.write('echo "Aslide environment variables have been set up."\n')
        
        os.chmod(setup_script_path, 0o755)  # Make it executable
        
        # Create a Python module to set up environment in code
        env_module_path = os.path.join(install_dir, 'Aslide', 'set_env.py')
        with open(env_module_path, 'w') as f:
            f.write('import os\n')
            f.write('import sys\n\n')
            f.write('def setup_environment():\n')
            f.write('    """Set up environment variables for Aslide.\n')
            f.write('    Call this function before importing Aslide components.\n')
            f.write('    """\n')
            f.write('    current_path = os.path.dirname(os.path.abspath(__file__))\n')
            f.write('    lib_paths = [\n')
            for path in lib_paths:
                rel_path = os.path.relpath(path, os.path.join(install_dir, 'Aslide'))
                f.write(f'        os.path.join(current_path, "{rel_path}"),\n')
            f.write('    ]\n\n')
            f.write('    # Add to LD_LIBRARY_PATH\n')
            f.write('    current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")\n')
            f.write('    os.environ["LD_LIBRARY_PATH"] = ":".join(lib_paths + [current_ld_path]) if current_ld_path else ":".join(lib_paths)\n\n')
            f.write('    # Also add to system path for ctypes to find libraries\n')
            f.write('    for path in lib_paths:\n')
            f.write('        if path not in sys.path:\n')
            f.write('            sys.path.append(path)\n')
            f.write('\n# Auto-setup when importing this module\n')
            f.write('setup_environment()\n')
        
        # Try to update the user's shell profile
        home = Path.home()
        shell_config_files = [
            home / '.bashrc',
            home / '.zshrc',
            home / '.bash_profile',
            home / '.profile'
        ]
        
        # Create an init file that auto-loads the environment
        init_path = os.path.join(install_dir, 'Aslide', '__init__.py')
        if os.path.exists(init_path):
            with open(init_path, 'r') as f:
                init_content = f.read()
            
            env_import = 'from .set_env import setup_environment\n'
            if env_import not in init_content:
                with open(init_path, 'w') as f:
                    f.write(env_import)
                    f.write('setup_environment()  # Auto-setup environment variables\n\n')
                    f.write(init_content)
        else:
            with open(init_path, 'w') as f:
                f.write('from .set_env import setup_environment\n')
                f.write('setup_environment()  # Auto-setup environment variables\n')
        
        # Print instructions for the user
        print("\n" + "="*80)
        print("Aslide has been successfully installed!")
        print("="*80)
        print("\nTo set up the environment variables automatically when using Aslide, you can:")
        print("\n1. Import Aslide directly (environment will be set up automatically):")
        print("   >>> import Aslide")
        print("\n2. Source the setup script before running your Python code:")
        print(f"   $ source {setup_script_path}")
        print("\n3. Add the following line to your shell configuration file (.bashrc, .zshrc, etc.):")
        
        # Create the export line with actual paths
        export_line = f'export LD_LIBRARY_PATH={lib_paths_str}:$LD_LIBRARY_PATH'
        print(f"   {export_line}")
        
        print("\nInstallation directory: " + install_dir)
        print("="*80 + "\n")

setup(
    name='Aslide',
    version='1.1.1',
    author='MrPeterJin',
    author_email='petergamsing@gmail.com',
    url='https://github.com/MrPeterJin/ASlide',
    description='A package to read whole-slide image (WSI) files',
    packages=find_packages(),
    package_data={
        'Aslide': ['*.py'],
        'Aslide.kfb': ['lib/*'],
        'Aslide.tmap': ['lib/*'],
        'Aslide.sdpc': ['so/**/*'],
    },
    cmdclass={'install': CustomInstall},
    platforms='linux',
    install_requires=['numpy', 'Pillow', 'openslide-python'],
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Operating System :: POSIX :: Linux',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
    ],
)
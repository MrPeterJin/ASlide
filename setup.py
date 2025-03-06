#!/usr/bin/env python
# coding: utf-8

from setuptools import setup, find_packages
from setuptools.command.install import install
import os
import shutil

class CustomInstall(install):
    def run(self):
        install.run(self)
        # Handle KFB files
        kfb_so_files = ['libcurl.so', 'libImageOperationLib.so', 'libjpeg.so.9', 'libkfbslide.so']
        target_dir = os.path.join(self.install_lib, 'Aslide', 'kfb', 'lib')
        self.mkpath(target_dir)
        for so_file in kfb_so_files:
            src_file = os.path.join(os.path.dirname(__file__), 'Aslide', 'kfb', 'lib', so_file)
            self.copy_file(src_file, target_dir)
        
        # Handle TMAP files
        target_dir = os.path.join(self.install_lib, 'Aslide', 'tmap', 'lib')
        self.mkpath(target_dir)
        tmap_files = ['iViewerInterface.h', 'libiViewerSDK.so']
        for tmap_file in tmap_files:
            src_file = os.path.join(os.path.dirname(__file__), 'Aslide', 'tmap', 'lib', tmap_file)
            self.copy_file(src_file, target_dir)
            
        # Handle SDPC files
        src_base_dir = os.path.join(os.path.dirname(__file__), 'Aslide', 'sdpc', 'so')
        dst_base_dir = os.path.join(self.install_lib, 'Aslide', 'sdpc', 'so')
        
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

setup(
    name='Aslide',
    version='1.1.1',
    author='MrPeterJin',
    author_email='petergamsing@gmail.com',
    url='https://github.com/MrPeterJin/ASlide',
    description=u'A package to read whole-slide image (WSI) files',
    packages=find_packages(),
    package_data={
        'Aslide': ['*.py'],
        'Aslide.kfb': ['*.py', 'lib/*'],
        'Aslide.tmap': ['*.py', 'lib/*'],
        'Aslide.sdpc': ['*.py', 'so/**/*'],
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
    ],
)

#!/usr/bin/env python
# coding: utf-8

from setuptools import setup, find_packages
from setuptools.command.install import install
import os

class CustomInstall(install):
    def run(self):
        install.run(self)
        kfb_so_files = ['libcurl.so', 'libImageOperationLib.so', 'libjpeg.so.9', 'libkfbslide.so']
        target_dir = os.path.join(self.install_lib, 'Aslide', 'kfb', 'lib')
        self.mkpath(target_dir)
        for so_file in kfb_so_files:
            src_file = os.path.join(os.path.dirname(__file__), 'Aslide', 'kfb', 'lib/', so_file)
            self.copy_file(src_file, target_dir)
        
        target_dir = os.path.join(self.install_lib, 'Aslide', 'tmap', 'lib')
        self.mkpath(target_dir)
        tmap_files = ['iViewerInterface.h', 'libiViewerSDK.so']
        for tmap_file in tmap_files:
            src_file = os.path.join(os.path.dirname(__file__), 'Aslide', 'tmap', 'lib/', tmap_file)
            self.copy_file(src_file, target_dir)
            
        target_dir = os.path.join(self.install_lib, 'Aslide', 'sdpc', 'so')
        self.mkpath(target_dir)
        self.mkpath(target_dir + '/ffmpeg')
        self.mkpath(target_dir + '/jpeg')
        sdpc_file_path = os.path.dirname(__file__) + '/Aslide/sdpc/so/'
        for r,d,f in os.walk(sdpc_file_path):
            for file in f:
                src_file = os.path.abspath(os.path.join(r, file))
                target_dir = os.path.join(self.install_lib, 'Aslide', 'sdpc', 'so', r.split('/')[-1]) + '/'
                self.copy_file(src_file, target_dir)

setup(
    name='Aslide',
    version='1.0.1',
    author='MrPeterJin',
    author_email='petergamsing@gmail.com',
    url='https://github.com/MrPeterJin/ASlide',
    description=u'A package to read whole-slide image (WSI) files',
    packages=find_packages(),
    package_data={'Aslide': ['*.py'], 'kfb': ['*.py', 'lib/*'], 'tmap': ['*.py', 'lib/*'], 'sdpc': ['*.py', 'so/*']},
    cmdclass={'install': CustomInstall},
    platforms='linux',
    install_requires=['numpy', 'Pillow', 'openslide-python'],
)
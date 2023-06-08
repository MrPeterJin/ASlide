#!/usr/bin/env python
# coding: utf-8

from setuptools import setup, find_packages

setup(
    name='kfb',
    version='1.0.0',
    author='MrPeterJin',
    author_email='petergamsing@gmail.com',
    url='https://github.com/MrPeterJin/kfb-reader/',
    description=u'A package to read whole-slide image (WSI) file in .kfb format',
    packages=['kfb'],
    package_dir={'kfb': 'kfb'},
    package_data={'kfb': ['*.py', 'so/*']},
    platforms='linux',
    install_requires=['numpy', 'Pillow', 'openslide-python'],
)

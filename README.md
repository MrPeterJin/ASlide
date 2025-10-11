# Aslide

This is an integrated Pathology Image (a.k.a. Whole-slide image) reading library.

Current support format:

- .bif
- .isyntax
- .ndpi
- .mrxs
- .qptiff
- .tif
- .tiff
- .tron
- .scn
- .svs
- .svslide
- .sdpc
- .TMAP
- .vms
- .vmu
- .vsi

This package currently tested and worked on:

- Ubuntu 22.04 LTS, Python 3.11
- Ubuntu 22.04 LTS, Python 3.10
- Ubuntu 22.04 LTS, Python 3.9
- Ubuntu 22.04 LTS, Python 3.8
- Ubuntu 22.04 LTS, Python 3.7
- Ubuntu 20.04 LTS, Python 3.8

## Pre-requisite

You should have [openslide-python](https://pypi.org/project/openslide-python/), [python-bioformats](https://pypi.org/project/bioformats/), [qptifffile](https://pypi.org/project/qptifffile/), and [pyisyntax](https://pypi.org/project/pyisyntax/) installed as a prerequisite package.

## Installation

Since the package is not uploaded to PyPI, you need to install it from source code.

```bash
python setup.py install
```

## Usage

Just import the package and use it as follows:

```python
from Aslide.aslide import Slide

slide = Slide('path/to/your/slide')
```

For more details, please refer to the `example_test_case.py` file.

## Troubleshooting

If you encounter the following error:

```bash
ImportError: *.so.0: cannot open shared object file: No such file or directory
```

You may check the detail installation path, for instance, if you use conda, it would be put in the following path (denoted as `Aslide-path` from hereon):

```bash
/home/<username>/anaconda3/lib/python3.x/site-packages/Aslide
```

Make sure the following files are in the folder:

```bash
Aslide-path/sdpc/lib
Aslide-path/tmap/lib
Aslide-path/kfb/lib
```

If not, you may need to re-install the package.

Another possible reason is that the shared library path is not set correctly. To solve this, you need to open your the config file of your python environment (e.g. `~/.bashrc`), add the following lines to the environment variable:

```bash
export LD_LIBRARY_PATH=Aslide-path/sdpc/lib/:Aslide-path/kfb/lib/:Aslide-path/tmap/lib:$LD_LIBRARY_PATH
```

Then, after sourcing the config file, and you are good to go:

```bash
source ~/.bashrc
```


## Projects Using This Package

- [Smart-CCS](https://github.com/hjiangaz/Smart-CCS) - A Generalizable Cervical Cancer Screening System.
- [PrePATH](https://github.com/birkhoffkiki/PrePATH) - A pre-processing tool for Pathology Image.
- You can add your project here by submitting a pull request!

## Credits

This package is based on the following projects and licensed under GPL 3.0 License:  

[Openslide](https://github.com/openslide/openslide)  
[opensdpc](https://github.com/WonderLandxD/opensdpc)  
[tct](https://github.com/liyu10000/tct)  
[WSI-SDK](https://github.com/yasohasakii/WSI-SDK)   
[bioformats](https://github.com/ome/bioformats)   
[vsi2tif](https://github.com/andreped/vsi2tif)   
[pyisyntax](https://github.com/anibali/pyisyntax)

Many thanks to the authors of these projects.

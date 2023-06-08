This repo is a python library for processing whole slide images (WSIs) in .kfb format. To read WSIs in .kfb format in Windows platform, download the [KFBio reading software](https://www.kfbio.cn/k-viewer). This package is in heavy beta testing and is not recommended for production use.

## Installation
```bash
git clone 
python setup.py install
```

## Usage
### Read a .kfb file
```python
from kfb import KfbSlide
slide = KfbSlide('path/to/kfb/file')
```

### Read a .kfb file with a specified region at a specified level
```python
from kfb import KfbSlide
slide = KfbSlide('path/to/kfb/file', level=0)
region = slide.read_region((x, y), level, (w, h))
```

### Obtain .kfb file information
```python
from kfb import KfbSlide
slide = KfbSlide('path/to/kfb/file')
print(slide.level_count)
print(slide.level_dimensions)
print(slide.level_downsamples)

# Sample output: 
# 6
# ((48000, 48128), (24000, 24064), (12000, 12032), (6000, 6016), (3000, 3008), (1500, 1504))
# (1.0, 2.0, 4.0, 8.0, 16.0, 32.0)
```
## Trouble Shooting
If you encounter errors when using this package, feel free to open an issue or contact me via email: [petergamsing@gmail.com](mailto:petergamsing@gmail.com)
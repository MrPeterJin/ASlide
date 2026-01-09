# ASlide

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)](https://www.linux.org/)
[![License](https://img.shields.io/badge/license-GPL%203.0-green.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)

> A comprehensive Python library for reading whole-slide images (WSI) in digital pathology with a unified API and extensive format support.

## Overview

**ASlide** is an integrated whole-slide image (WSI) reading library designed for digital pathology applications. It provides a unified interface to read various proprietary and open-source WSI formats, eliminating the need to work with multiple vendor-specific SDKs.

### Key Features

- **Unified API**: Single interface for all supported formats
- **Comprehensive Format Support**: 20+ WSI formats from major vendors
- **DeepZoom Support**: Built-in tile server capabilities for web-based viewers
- **Extensible Architecture**: Easy to add new format support
- **Pure Python Interface**: Simple integration with existing Python workflows
- **Performance Optimized**: Efficient memory management for large WSI files

## Supported Formats

ASlide supports the following whole-slide image formats:

| Format | Extension | Vendor/Source | Backend |
|--------|-----------|---------------|---------|
| Aperio SVS | `.svs`, `.svslide` | Leica Biosystems | OpenSlide |
| DYJ | `.dyj` | DPT | Native SDK |
| DYQX | `.dyqx` | SQRAY | Native SDK |
| Generic TIFF | `.tif`, `.tiff` | Various | OpenSlide |
| Hamamatsu NDPI | `.ndpi` | Hamamatsu | OpenSlide |
| Hamamatsu VMS/VMU | `.vms`, `.vmu` | Hamamatsu | OpenSlide |
| iSyntax | `.isyntax` | Philips | pyisyntax |
| iBL | `.ibl` | iBingLi | Native SDK |
| KFB | `.kfb` | KFBio | Native SDK |
| Leica SCN | `.scn` | Leica Biosystems | OpenSlide |
| MIRAX | `.mrxs` | 3DHISTECH | OpenSlide |
| MDS | `.mds`, `.mdsx` | Motic | Native SDK |
| Olympus VSI | `.vsi` | Olympus | Bio-Formats |
| QPTiff | `.qptiff` | Akoya | qptifffile |
| SDPC | `.sdpc` | SQRAY | Native SDK |
| TMAP | `.TMAP` | UNIC | Native SDK |
| TRON | `.tron` | InteMedic | Native SDK |
| Ventana BIF | `.bif` | Roche Ventana | OpenSlide |
| ZYP | `.zyp` | WinMedic | Native SDK |

## Installation

### Prerequisites

- **Operating System**: Linux (> Ubuntu 22.04 LTS)
- **Python**: 3.10 or higher
- **System Libraries**: OpenSlide library (for OpenSlide-based formats)


### Install from Source

```bash
# Clone the repository
git clone https://github.com/MrPeterJin/ASlide.git
cd ASlide

# Install the package (dependencies will be installed automatically)
python setup.py install
```

or use the following one-liner:

```bash
pip install git+https://github.com/MrPeterJin/ASlide.git
```

The installation script will automatically:
- Install required Python packages (numpy, Pillow, openslide-python, qptifffile, tifffile, pyisyntax)
- Bundle OpenCV 3.4.2 and all dependencies
- Copy vendor-specific shared libraries to the appropriate locations
- Set up environment variables for library paths
- Create helper scripts for environment configuration

### Post-Installation Setup

After installation, you may need to set up environment variables for shared libraries:

**Option 1: Automatic (Recommended)**
```python
# Environment is set up automatically when importing
import Aslide
```

**Option 2: Manual Shell Configuration**
```bash
# Add to your ~/.bashrc or ~/.zshrc
export LD_LIBRARY_PATH=/path/to/site-packages/Aslide/sdpc/lib:/path/to/site-packages/Aslide/kfb/lib:$LD_LIBRARY_PATH

# Reload your shell configuration
source ~/.bashrc
```

**Option 3: Use the Generated Setup Script**
```bash
# Source the auto-generated setup script
source /path/to/site-packages/Aslide/setup_env.sh
```

## Quick Start

### Basic Usage

```python
from Aslide import Slide

# Open a whole-slide image
slide = Slide('path/to/your/slide.svs')

# Get slide properties
print(f"Dimensions: {slide.dimensions}")
print(f"Level count: {slide.level_count}")
print(f"Level dimensions: {slide.level_dimensions}")
print(f"Level downsamples: {slide.level_downsamples}")

# Read a region from the slide
region = slide.read_region((0, 0), 0, (1000, 1000))

# Get thumbnail
thumbnail = slide.get_thumbnail((500, 500))

# Close the slide
slide.close()
```

### Advanced Usage

For more advanced usage examples, including:
- Multi-resolution image reading
- Tile extraction for deep learning
- DeepZoom tile server integration
- Batch processing workflows

Please refer to the `example_test_case.py` file in the repository.

## API Reference

### Main Classes

#### `Slide`

The main class for reading whole-slide images.

**Methods:**
- `__init__(filename)`: Open a slide file
- `read_region(location, level, size)`: Read a region from the slide
- `get_thumbnail(size)`: Get a thumbnail of the slide
- `close()`: Close the slide and free resources

**Properties:**
- `dimensions`: Slide dimensions at level 0 (width, height)
- `level_count`: Number of pyramid levels
- `level_dimensions`: Dimensions at each level
- `level_downsamples`: Downsample factor for each level
- `properties`: Dictionary of slide metadata

## Troubleshooting

### Common Issues

#### 1. Shared Library Not Found Error

**Error:**
```
ImportError: *.so.0: cannot open shared object file: No such file or directory
```

**Solution:**

Check that the shared libraries are correctly installed:

```bash
# Find your installation path (example for conda)
ASLIDE_PATH=/home/<username>/anaconda3/lib/python3.x/site-packages/Aslide

# Verify library directories exist
ls $ASLIDE_PATH/sdpc/lib
ls $ASLIDE_PATH/kfb/lib
ls $ASLIDE_PATH/tron/lib
```

If directories are missing, reinstall the package:
```bash
python setup.py install --force
```

#### 2. Environment Variables Not Set

If libraries are installed but not found at runtime, manually set `LD_LIBRARY_PATH`:

```bash
export LD_LIBRARY_PATH=$ASLIDE_PATH/sdpc/lib:$ASLIDE_PATH/kfb/lib:$ASLIDE_PATH/tron/lib:$LD_LIBRARY_PATH
```

#### 3. Permission Issues

If you encounter permission errors during installation, try:

```bash
# Install with user permissions
python setup.py install --user

# Or use sudo (not recommended for conda environments)
sudo python setup.py install
```

## Testing

The package has been tested on:

- Red Hat 9.6 with Python 3.10
- Ubuntu 24.04 LTS with Python 3.10
- Ubuntu 22.04 LTS with Python 3.13
- Ubuntu 22.04 LTS with Python 3.11
- Ubuntu 22.04 LTS with Python 3.10

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## Projects Using ASlide

- [**Smart-CCS**](https://github.com/hjiangaz/Smart-CCS) - A Generalizable Cervical Cancer Screening System
- [**PrePATH**](https://github.com/birkhoffkiki/PrePATH) - A Pre-processing Tool for Pathology Images

*Using ASlide in your project? Add it here by submitting a pull request!*

## Legal Notice

This repository is not associated with or endorsed by providers of the SDKs or file formats contained in this GitHub repository. This project is intended for educational purposes only. Vendors may contact me to improve their security or request the removal of their format support from this repository.

Please note the following:

**Disclaimer**: The SDKs, file formats, services, and trademarks mentioned in this repository belong to their respective owners. This project is not claiming any right over them nor is it affiliated with or endorsed by any of the providers mentioned.

**Responsibility**: The author of this repository is not responsible for any consequences, damages, or losses arising from the use or misuse of this repository or the content provided by the third-party repositories. Users are solely responsible for their actions and any repercussions that may follow. We strongly recommend users to follow the terms of service of each vendor.

**Educational Purposes Only**: This repository and its content are provided strictly for educational purposes. By using the information and code provided, users acknowledge that they are using the SDKs and libraries at their own risk and agree to comply with any applicable laws and regulations.

**Copyright**: All content in this repository, including but not limited to code, images, and documentation, is the intellectual property of the repository author, unless otherwise stated. Unauthorized copying, distribution, or use of any content in this repository is strictly prohibited without the express written consent of the repository author.

**Indemnification**: Users agree to indemnify, defend, and hold harmless the author of this repository from and against any and all claims, liabilities, damages, losses, or expenses, including legal fees and costs, arising out of or in any way connected with their use or misuse of this repository, its content, or related third-party SDKs.

**Updates and Changes**: The author reserves the right to modify, update, or remove any content, information, or features in this repository at any time without prior notice. Users are responsible for regularly reviewing the content and any changes made to this repository.

By using this repository or any code related to it, you agree to these terms. The author is not responsible for any copies, forks, or reuploads made by other users. This is the author's only account and repository. To prevent impersonation or irresponsible actions, you may comply with the GNU GPL license this Repository uses.

## License

This project is licensed under the **GPL 3.0 License** - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

ASlide builds upon and integrates several excellent open-source projects:

- [**opencv**](https://github.com/opencv/opencv) - A computer vision library used for image processing
- [**OpenSlide**](https://github.com/openslide/openslide) - A C library for reading whole-slide images
- [**opensdpc**](https://github.com/WonderLandxD/opensdpc) - SDPC format support
- [**tct**](https://github.com/liyu10000/tct) - TCT slide processing utilities
- [**WSI-SDK**](https://github.com/yasohasakii/WSI-SDK) - Whole-slide image SDK
- [**Bio-Formats**](https://github.com/ome/bioformats) - Java library for reading life sciences image formats
- [**vsi2tif**](https://github.com/andreped/vsi2tif) - VSI format conversion tools
- [**pyisyntax**](https://github.com/anibali/pyisyntax) - Python library for reading Philips iSyntax images
- [**olefile**](https://github.com/decalage2/olefile) - Python library for parsing OLE2 files

Many thanks to the authors and contributors of these projects for their invaluable work.

## Contact

**Author**: MrPeterJin
**Email**: petergamsing@gmail.com
**GitHub**: [@MrPeterJin](https://github.com/MrPeterJin)

---

<p align="center">
  <i>If you find ASlide useful, please consider giving it a star on GitHub!</i>
</p>

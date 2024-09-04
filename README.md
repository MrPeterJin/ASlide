# Aslide
This is an integrated Pathology Image (a.k.a. Whole-slide image) reading library.

Current support format:   
* .svs   
* .tif    
* .ndpi     
* .vms      
* .vmu     
* .scn       
* .mrxs        
* .tiff           
* .kfb          
* .svslide         
* .sdpc         
* .TMAP        
* .bif        

This package currently tested and worked on:               
Ubuntu 22.04 LTS

## Pre-requisite
Installing these pre-requisites need a super user privilege on a workstation/server. If you do not have this, please contact your administrator.
You should have opencv 3.4.2 (you need to build it from source code, please make sure the version number is 3.4.2) and ffmpeg. If you don't have it, you can install it by the following commands:

### OpenCV
Before installing opencv, a super user privilege is required to install the following pacakges:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install gcc cmake git pkg-config libavcodec-dev libavformat-dev libswscale-dev libtbb2 libtbb-dev libjpeg-dev libpng-dev libtiff-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libgstreamer-plugins-bad1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 gstreamer1.0-qt5 gstreamer1.0-pulseaudio libgtk-3-dev
```

Then you can proceed to download and complie OpenCV 3.4.2 by the following code snippet:

```bash
wget https://github.com/opencv/opencv/archive/3.4.2.zip
unzip ./3.4.2.zip
cd ./opencv3.4.2  
mkdir build
cd build 

# Complie
cmake -D CMAKE_BUILD_TYPE=RELEASE -D CMAKE_INSTALL_PREFIX=/usr/local -D WITH_TBB=OFF -D BUILD_NEW_PYTHON_SUPPORT=ON -D WITH_V4L=ON -D WITH_QT=OFF -D WITH_OPENGL=ON .. 

# Install (use -j option to enable multi-core processing)
sudo make install
```

Please refer to [this](https://docs.opencv.org/3.4.2/d7/d9f/tutorial_linux_install.html) for more details.

### ffmpeg
```bash
sudo apt-get install ffmpeg
```

## Installation
Since the package is not uploaded to PyPI, you need to install it from source code.

```bash
python setup.py install
```

After installation, you may check the detail installation path, for instance, if you use conda, it would be put in the following path (denoted as `Aslide-path` from hereon):

```bash
/home/username/anaconda3/lib/python3.x/site-packages/Aslide
```

Make sure the following files are in the folder:

```bash
Aslide-path/sdpc/so
Aslide-path/tmap/lib
Aslide-path/kfb/lib
```

After checking, open your the config file of your python environment (e.g. `~/.bashrc`), add the following lines to the environment variable:

```bash
export LD_LIBRARY_PATH=Aslide-path/sdpc/so/:Aslide-path/sdpc/so/ffmpeg/:Aslide-path/kfb/lib/:Aslide-path/tmap/lib:$LD_LIBRARY_PATH
```

Then, you need to source the config file, and you are good to go:

```bash
source ~/.bashrc
```

## Usage
Just import the package and use it as follows:

```python
from Aslide.aslide import Slide

slide = Slide('path/to/your/slide')
```

For more details, please refer to the `example_test_case.py` file.

## Credits
This package is based on the following projects:       
[Openslide](https://github.com/openslide/openslide)         
[sdpc-python](https://github.com/WonderLandxD/sdpc-for-python)          
[tct](https://github.com/liyu10000/tct)       
[WSI-SDK](https://github.com/yasohasakii/WSI-SDK)

Many thanks to the authors of these projects.

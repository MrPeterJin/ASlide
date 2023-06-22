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

## Pre-requisite
You should have opencv 3.4.2 (you need to build it from source code, please make sure the version number is 3.4.2) and ffmpeg. If you don't have it, you can download it by the following commands:

```bash
wget https://github.com/opencv/opencv/archive/3.4.2.zip
```

```bash
sudo apt-get install ffmpeg
```

For opencv, you need to unzip it and build it from source code:

```bash
cd ./opencv3.4.2  
mkdir release  
cd release
  
#**Compile**  
cmake -D CMAKE_BUILD_TYPE=RELEASE -D CMAKE_INSTALL_PREFIX=/usr/local -D WITH_TBB=OFF -D BUILD_NEW_PYTHON_SUPPORT=ON -D WITH_V4L=ON -D WITH_QT=OFF -D WITH_OPENGL=ON .. 

#**Make and install** (long time waiting)  -j4 is for compiling using 4 cores of CPU
sudo make -j4
sudo make install
```

Please refer to [this](https://docs.opencv.org/3.4.2/d7/d9f/tutorial_linux_install.html) for more details.



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
export LD_LIBRARY_PATH=Aslide-path/sdpc/so/:Aslide-path/sdpc/ffmpeg/:Aslide-path/kfb/lib/:Aslide-path/tmap/lib:$LD_LIBRARY_PATH
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

Many thanks to the authors of these projects.
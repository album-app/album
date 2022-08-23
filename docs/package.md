# Album Package
**An Album plugin for packaging solutions into executables**

This plugin is used to create executables from solutions, so a solution can be installed with a simple
double click. The executable creates a shortcut for running the solution and a shortcut for uninstalling the solution on the desktop of the user.
The executables can be distributed to a different system running the same operating system.
To create executables for different operating systems, run this plugin on a system running the target operating system.
If the the target system runs Windows or MacOS it doesn't need to have anything preinstalled, the executable will install every 
needed component (Miniconda and album) into the ~/.album directory if they are not already
installed on the system. If the source and/or target system is a Linux system the user needs to have the binutils package installed 
before building/running the executable.


## Installation:
1. [Install Album](https://docs.album.solutions/en/latest/installation-instructions.html#)
2. Activate the Album environment:

   1. If you installed Album with the Album installation wizard use one of the following commands to activate your 
   Album environment:
      1. Linux and MacOS:
         ```
         ~/.album/activate_album
         ```
         or
         ```
         ~/.album/Miniconda/condabin/conda activate -p /~/.album/envs/album
         ```
      2. Windows:
         ```
         ~/.album/activate_album.bat
         ```
         or
         ```
         ~/.album/Miniconda/condabin/conda.bat activate -p /~/.album/envs/album
         ```
   2. If you installed Album manually use following command:
      ```
      conda activate album
      ```
    

3. Install the Album package plugin:
```
pip install album-package
```
4. If you are using a linux system, make sure the source and the target system got the binutils package installed.
For example on ubuntu it can be installed with the following command:
```
apt-get update && apt-get install binutils
```

## Usage:
To create an executable which installs the solution run following command:
```
album package /path/to/your/solution.py /your/output/path
```

### Input parameter:
- solution: The Album solution.py file which should be packed into an executable. <br>
  If you provide the path to a directory containing a solution.py all files in the directory will be
  packaged into the solution executable. If you provide the direct path to a solution.py only the solution will
  packaged. If your solution contains local imports, make sure all imported files lie in the same directory as the solution
  and you provide the path containing the solution.py.
- output_path: The path where the executable should be saved

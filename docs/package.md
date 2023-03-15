# Album Package
**An Album plugin for packaging solutions into executables**

This plugin is used to create executables from solutions, so a solution and Album can be installed with a simple
double click. This plugin also offers the option to create executables which only install Album. 
The executables create a shortcut for running the Album UI on the desktop of the user.
The executables can be distributed to a different system running the same operating system.
To create executables for different operating systems, run this plugin on a system running the target operating system.
If the target system runs Windows or MacOS it doesn't need to have anything preinstalled, the executable will install every 
needed component (Micromamba and Album) into the ~/.album directory if they are not already
installed on the system. If the source and/or target system is a Linux system the user needs to have the binutils package installed 
before building/running the executable.


## Installation:
1. [Install Album](https://docs.album.solutions/en/latest/installation-instructions.html#)
2. Activate the Album environment:
If you installed Album with the Album installation wizard use one of the following commands to activate your 
Album environment:
      ```
      micromamba activate -p ~/.album/envs/album
      ```
   If you installed Album manually use following command:
      ```
      conda activate album
      ```
    

3. Install the Album package plugin:
```
pip install album-package
```
4. If you are using a linux system, make sure the source and the target system have the binutils package installed.
For example on ubuntu it can be installed with the following command:
```
apt-get update && apt-get install binutils
```

## Usage:
To create an executable which only installs Album run the following command:
```
album package --output_path /your/output/path
```
To create an executable which installs the solution run the following command:
```
album package --solution /path/to/your/solution.py --output_path /your/output/path
```

## Input parameter:
- solution: The Album solution.py file which should be packed into an executable. 
  If you provide the path to a directory containing a solution.py all files in the directory will be
  packaged into the solution executable. If you provide the direct path to a solution.py only the solution will be
  packaged. If your solution contains local imports, make sure all imported files lie in the same directory as the solution
  and you pass the path to the directory containing the solution.py not to the solution.py directly.
- output_path: The path where the executable will be saved.

## Output
In your output path you will now find an executable which can be executed with a double click. It will install Album
into the .album directory in your home directory. If you passed a solution when creating the executable the solution 
will also be installed. In the .album directory there will also be directory containing the
micromamba installation. After the installation is finished there will be a shortcut for the Album UI on your Desktop 
which allows you to use Album and execute solutions.

**Windows disclaimer:** On some windows systems guarded by a institute controlled antivirus software, it can happen that 
the antivirus software blocks the correct build of an executable. Created installers will not work correctly and will
not install Album. If you encounter this problem, please disable your antivirus software if possible and try again or 
request admin rights from your institute IT department.
# Plugins

Album provides some functionalities which are separated from the Album core.

## Album Package
**An Album plugin for packaging solutions into executables**

This plugin is used to create executables from solutions, so a solution and Album can be installed with a simple
double click. This plugin also offer the option to create executables which only install Album. 
The executables create a shortcut for running the Album UI on the desktop of the user.
The executables can be distributed to a different system running the same operating system.
To create executables for different operating systems, run this plugin on a system running the target operating system.
If the target system runs Windows or MacOS it doesn't need to have anything preinstalled, the executable will install every 
needed component (Micromamba and Album) into the ~/.album directory if they are not already
installed on the system. If the source and/or target system is a Linux system the user needs to have the binutils package installed 
before building/running the executable.


### Installation:
1. [Install Album](https://docs.album.solutions/en/latest/installation-instructions.html#)
2. Activate the Album environment: <br>
If you installed Album with the Album installation wizard use one of the following commands to activate your 
Album environment:
      ```
      micromamba activate -p /~/.album/envs/album
      ```
   If you installed Album manually use following command:
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

### Usage:
To create an executable which only installs Album run following command:
```
album package --output_path /your/output/path
```
To create an executable which installs the solution run following command:
```
album package --solution /path/to/your/solution.py --output_path /your/output/path
```

### Input parameter:
- solution: The Album solution.py file which should be packed into an executable. <br>
  If you provide the path to a directory containing a solution.py all files in the directory will be
  packaged into the solution executable. If you provide the direct path to a solution.py only the solution will
  packaged. If your solution contains local imports, make sure all imported files lie in the same directory as the solution
  and you pass the path to the directory containing the solution.py not to the solution.py directly.
- output_path: The path where the executable will be saved.

###Output
In your output path you will now find an executable which can be executed with a double click. It will install Album
into the .album directory in your home directory and if you passed a solution when creating the executable the solution 
will also be installed in the .album directory. In the .album directory there will also be directory containing the
micromamba installation. After the installation is finished there will be a shortcut for the Album UI on your Desktop 
which allows you to use Album and execute solutions.

##Album Docker
**Containerize your Album solutions**

This plugin is used to create docker images from solutions. The images can be used to run Album solutions in a docker 
container.

### Installation:
1. Install Docker on your system. For more information see the [Docker documentation](https://docs.docker.com/get-docker/).
2. [Install Album.](https://docs.album.solutions/en/latest/installation-instructions.html#)
3. Activate the Album environment: <br>
If you installed Album with the Album installation wizard use one of the following commands to activate your 
Album environment:
      ```
      micromamba activate -p /~/.album/envs/album
      ```
   If you installed Album manually use following command:
      ```
      conda activate album
      ```
     

4. Install the Album docker plugin:
```
pip install https://gitlab.com/album-app/plugins/album-docker/-/archive/main/album-docker-main.zip
```

### Usage:
To create a docker image from a solution run following command:
```
album docker --solution /path/to/your/solution.py  --output /your/output/path
```
or:
```
album docker --solution your:Solution:coordinates --output_path /your/output/path
```

### Input parameter:
- solution: The Album solution.py file which should be run inside a container. <br>
  If you provide the path to a solution.py all files in the directory will be
  packaged into the docker image and therefore will be available inside a container created by this image. 
- output: The path where the solution_name_image.tar archive will be saved. 

###Output
In your output path you will now find an solution_name_image.tar archive which can be loaded into a docker container 
with the following command:
  ```
  docker load -i /path/to/image.tar
  ```

## Album distributed
**An Album plugin for distributed calls**
This is an early version of enhancing album with calls for batch and distributed processing.

### Installation
1. [Install Album](https://docs.album.solutions/en/latest/installation-instructions.html#)
2. Activate the Album environment: <br>
If you installed Album with the Album installation wizard use one of the following commands to activate your 
Album environment:
      ```
      micromamba activate -p /~/.album/envs/album
      ```
   If you installed Album manually use following command:
      ```
      conda activate album
      ```
   
3. Install this plugin:
```
pip install https://gitlab.com/album-app/plugins/album-distributed/-/archive/main/album-distributed-main.zip
```

### Usage
Fist, install a solution - replace `solution.py` with the path to your solution / solution folder or with the `group:name:version` coordinates of your solution.
```
album install solution.py
```
Now you can use the plugin:
```
album run-distributed solution.py
```
The plugin does two things:
1. It figures out if the input arguments match multiple tasks - in this case, it generates the different task arguments.
2. It runs all matching tasks, the mode for running these tasks can be chosen.  

Since the matching part can be tricky, please use the `--dry-run` argument to first print a list of matched tasks:
```
album run-distributed solution.py --dry-run
```

On Windows, replace the slashes with backslashes in the examples on this page. 

Please let us know if you run into issues.

### Matching input arguments
To generate multiple tasks, patterns in file name arguments can be used to match multiple files.

#### Using patterns in a single argument

You should be able to use all [`glob`](https://docs.python.org/3/library/glob.html) features when using it in a single argument. Here are some examples:

In the following scenarios `solution.py` has an argument called `input_data`.

Match all `.tif` files in the current folder:
```
album run-distributed solution.py --input_data *.tif
```

Match all `.tif` files in a specific folder where the file name starts with `input`:
```
album run-distributed solution.py --input_data /data/input*.tif
```

Match all `.tif` files recursively, starting from the current folder:
```
album run-distributed solution.py --input_data **/*.tif
```

#### Using patterns in multiple arguments

When using patterns in multiple arguments, this plugin will try to figure out the corresponding argument values based on which of the patterns match with existing files.
This is likely to fail in a bunch of situations - please use the `--dry-run` argument to test if the matched tasks correspond with your expectation.

In the following scenarios `solution.py` has two arguments called `input_data` and `output_data`.

Use all `.tif` files in the current folder and append `_out` to the file name for the output argument.
```
album run-distributed solution.py --input_data *.tif --output_data *_out.tif
```

Do the same thing recursively:
```
album run-distributed solution.py --input_data **/*.tif --output_data **/*_out.tif
```

Let the output argument values live in a different folder:
```
album run-distributed solution.py --input_data *.tif --output_data output/*.tif
```

Since Album does not yet distinguish between input and output arguments, be aware that if the `output_data` argument in these scenarios matches existing files, the plugin will also try to generate corresponding `input_file` values. We will work on improving this.

### Modes
You can set the mode by using the `--mode` argument:
```
album run-distributed solution.py --mode queue
```
By default, the plugin will use the `basic` mode.

#### Basic
In this mode, all tasks will be performed one after each other. The console output of each task will be printed.
#### Queue
In this mode, a set of thread workers will be created to process tasks in parallel. The console output of each task will not be printed.
You can control how many threads should be created with the `--threads` argument:
```
album run-distributed solution.py --mode queue --threads 16
```

## Album server
**An Album plugin for launching a server which provides a REST API for all command line calls**

For further information please visit the [Album server documentation](https://docs.album.solutions/en/latest/server.html).
# Album distributed
**An Album plugin for distributed calls**
This is an early version of enhancing album with calls for batch and distributed processing.

## Installation
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
   
3. Install this plugin:
```
pip install https://gitlab.com/album-app/plugins/album-distributed/-/archive/main/album-distributed-main.zip
```

## Usage
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

## Matching input arguments
To generate multiple tasks, patterns in file name arguments can be used to match multiple files.

### Using patterns in a single argument

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

### Using patterns in multiple arguments

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

## Modes
You can set the mode by using the `--mode` argument:
```
album run-distributed solution.py --mode queue
```
By default, the plugin will use the `basic` mode.

### Basic
In this mode, all tasks will be performed one after each other. The console output of each task will be printed.
### Queue
In this mode, a set of thread workers will be created to process tasks in parallel. The console output of each task will not be printed.
You can control how many threads should be created with the `--threads` argument:
```
album run-distributed solution.py --mode queue --threads 16
```

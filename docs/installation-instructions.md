# Installing Album

Album can be installed in two different ways:

## Automated installation with Album installation wizard:

You can install Album by simply downloading the installation wizard for your operating system and executing it.

- [Windows install wizard](https://gitlab.com/album-app/plugins/album-package/-/jobs/3941084419/artifacts/raw/installer/album_installer.exe?inline=false)


- [MacOS install wizard](https://gitlab.com/album-app/plugins/album-package/-/jobs/3941084416/artifacts/raw/installer/album_installer?inline=false)


- [Linux install wizard](https://gitlab.com/album-app/plugins/album-package/-/jobs/3941084414/artifacts/raw/installer/album_installer?inline=false)


The installation wizards will create a new directory called .album inside your home directory.
Into this directory the installer installs Micromamba version 1.0.0 and creates the Album environment for you.
On your Desktop you will find a link called Album which will start the Album graphical user interface.

**Windows disclaimer:** On some windows systems, especially virtual maschines, the installer will trigger a request 
for admin rights. This is because the installer of micromamba needs to edit the powershell profile. 
The installer will only edit the profile of the current user and not the system profile. 
The installer will not install anything on your system without your permission. If you deny the request for
admin rights the installer will install album in a GUI only mode. This means that you can only use Album in the graphical
user interface and not in the commandline/powershell since they cannot be initialised without admin rights.

**Manually activating the environment for commandline usage**

To activate the Album environment for commandline use one of the following commands:

```
micromamba activate -p ~/.album/envs/album
```
**Uninstallation**

To uninstall everything, simply delete the .album directory in your home directory.

## Manual Installation:

### Installation using conda:

Prerequisites:

- an Anaconda installation, i.e. [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

**Install the Album environment:**

For the most recently released Album version, run this command:

```
conda env create -n album album python=3.10 -c conda-forge
```

**Activate the environment:**

```
conda activate album
```

### Installation using micromamba:

Prerequisites:

- a Micromamba installation, [Micromamba](https://mamba.readthedocs.io/en/latest/installation.html)

**Install the Album environment:**

For the most recently released Album version, run this command:

```
micromamba env create -n album album python=3.10 -c conda-forge
```

**Activate the environment:**

```
micromamba activate album
```

#### Windows notes
**If after installing Anaconda, the Conda command is not found.**
Use the Anaconda Command Prompt or add these to the PATH variable of your system:
- C:\\Users\USERNAME\Anaconda-dir\condabin
- C:\\Users\USERNAME\Anaconda-dir\Scripts
- C:\\Users\USERNAME\Anaconda-dir\Library\bin

## Conda vs mamba
Album is working with conda and mamba, which are both open source package and environment management systems. 
The main difference is, that mamba is faster than conda and can in some cases resolve environments which conda cannot. 
If you want to use mamba you can install mamba in the base environment and then create the Album environment with mamba,
or you can use the micromamba installer to avoid conda all together.

## Conda using mamba
If  you are already using conda and want to profit mamba, you can install mamba in the base environment and use it to 
create environments. Conda can then still be used to activate the environments.

```
conda install mamba -c conda-forge
```

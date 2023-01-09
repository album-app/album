# Installing Album

Album can be installed in two different ways:

## Automated installation with Album installation wizard:

You can install Album by simply downloading the installation wizard for your operating system and executing it.

- [Windows install wizard](https://gitlab.com/album-app/plugins/album-package/-/jobs/3574343115/artifacts/raw/installer/album_installer.exe?inline=false)


- [MacOS install wizard](https://gitlab.com/album-app/plugins/album-package/-/jobs/3574343110/artifacts/raw/installer/album_installer?inline=false)


- [Linux install wizard](https://gitlab.com/album-app/plugins/album-package/-/jobs/3574343105/artifacts/raw/installer/album_installer?inline=false)


The installation wizards will create a new directory called .album inside your home directory.
Into this directory the installer installs Micromamba version 1.0.0 and creates the Album environment for you.

**Activate the environment**

To activate the Album simply double click the activate_album file inside your home directory. (activate_album.bat for windows)

**Uninstallation**

To uninstall everything, simply delete the .album directory in your home directory.

## Manual Installation:

Prerequisites:

- an Anaconda installation, i.e. [Miniconda](https://docs.conda.io/en/latest/miniconda.html) <br>
or
- a Micromamba installation, [Micromamba](https://mamba.readthedocs.io/en/latest/installation.html)

**Install the Album environment:**

For the most recently released Album version, run this command:

```
conda env create -f https://gitlab.com/album-app/album/-/raw/main/album.yml
```
or
```
micromamba env create -f https://gitlab.com/album-app/album/-/raw/main/album.yml
```
 
In order to install a specific fixed version, run this command (replace `v0.2.0` with the version of choice):

```
conda env create -f https://gitlab.com/album-app/album/-/raw/v0.2.0/album.yml
```
or
```
micromamba env create -f https://gitlab.com/album-app/album/-/raw/v0.2.0/album.yml
```

**Activate the environment:**

```
conda activate album
```
or
```
micromamba activate album
```

### Windows notes
**If after installing Anaconda, the Conda command is not found.**
Use the Anaconda Command Prompt or add these to the PATH variable of your system:
- C:\\Users\USERNAME\Anaconda-dir\condabin
- C:\\Users\USERNAME\Anaconda-dir\Scripts
- C:\\Users\USERNAME\Anaconda-dir\Library\bin

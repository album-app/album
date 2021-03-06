# Installing album

album can be installed with the following instructions:

Prerequisites:

- a Conda installation, i.e. [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

**Install the album conda environment:**

For the most recently released album version, run this command:

```
conda env create -f https://gitlab.com/album-app/album/-/raw/main/album.yml
```
 
In order to install a specific fixed version, run this command (replace `v0.2.0` with the version of choice):

```
conda env create -f https://gitlab.com/album-app/album/-/raw/v0.2.0/album.yml
```

**Activate the environment:**

```
conda activate album
```

## Windows notes
**After installing Conda, the Conda command is not found.**
Use the Anaconda Command Prompt or add these to the PATH variable of your system:
- C:\\Users\USERNAME\Anaconda-dir
- C:\\Users\USERNAME\Anaconda-dir\Scripts

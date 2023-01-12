#Album Docker
**Containerize your Album solutions**

This plugin is used to create docker images from solutions. The images can be used to run Album solutions in a docker 
container.

## Installation:
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

## Usage:
To create a docker image from a solution run following command:
```
album docker --solution /path/to/your/solution.py  --output /your/output/path
```
or:
```
album docker --solution your:Solution:coordinates --output_path /your/output/path
```

## Input parameter:
- solution: The Album solution.py file which should be run inside a container. <br>
  If you provide the path to a solution.py all files in the directory will be
  packaged into the docker image and therefore will be available inside a container created by this image. 
- output: The path where the solution_name_image.tar archive will be saved. 

##Output
In your output path you will now find an solution_name_image.tar archive which can be loaded into a docker container 
with the following command:
  ```
  docker load -i /path/to/image.tar
  ```

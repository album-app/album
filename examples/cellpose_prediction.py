# Copyright 2021 Kyle Harrington

import subprocess
import os
import sys
import hips

global args, python_path, module_name, deployment_path


def hips_init():
    """
    Initialization to setup this HIPS
    """
    global args, python_path, module_name, deployment_path

    active_hips = hips.get_active_hips()

    # determine python executable
    environment_name = hips.get_environment_name(active_hips)
    environment = hips.get_environment_path(environment_name)
    python_path = os.path.join(environment, 'bin', 'python')

    # download repo
    deployment_path = hips.download_repository()

    # change into to deployment_path
    os.chdir(deployment_path)

    # set module name to hips name
    module_name = active_hips['name']


def cellpose_prediction():
    """
    This is the main entry point of this HIPS
    """
    global args, python_path, module_name

    subprocess_args = [
        python_path, '-m', module_name
    ] + sys.argv[1:]
    subprocess.run(subprocess_args)


hips.setup(
    name="cellpose",
    version="0.1.0",
    description="Cellpose Prediction HIP Solution",
    git_repo="https://github.com/MouseLand/cellpose.git",
    license="BSD-3-Clause License",
    min_hips_version="0.1.0",
    tested_hips_version="0.1.0",
    args="pass-through",
    init=hips_init,
    main=cellpose_prediction,
    dependencies={'environment_name': 'hips_full'}
)

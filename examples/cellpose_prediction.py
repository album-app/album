# Copyright 2021 Kyle Harrington

import subprocess
import os
import sys
import hips.run

global args, python_path, module_name, deployment_path


def hips_init():
    """
    Initialization to setup this HIPS
    """
    global args, python_path, module_name, deployment_path

    active_hips = hips.get_active_hips()

    # determine python executable and create environment - ToDo: should migrate to pathlib?
    python_path = os.path.join(hips.run.get_environment_path(active_hips), 'bin', 'python')

    # repository path
    deployment_path = hips.run.get_deployment_path(active_hips)

    # change into to deployment_path
    os.chdir(deployment_path)

    # set module name
    module_name = "cellpose"


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
    dependencies={
        'download_repo': True,
        'environment_name': "cellpose",  # ToDo: parse this from environment_file file
        # could also be a stream
        'environment_file': 'https://raw.githubusercontent.com/MouseLand/cellpose/master/environment.yml',
    }
)

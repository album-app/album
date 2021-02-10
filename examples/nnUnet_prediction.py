# Copyright 2021 Kyle Harrington

import subprocess
import os
import sys
import tempfile
import hips.run

global args, python_path, module_name


def hips_init():
    """
    Initialization to setup this HIPS
    """
    global args, module_name

    # set module name to hips name
    module_name = "nnUNet_predict"


def cellpose_prediction():
    """
    This is the main entry point of this HIPS
    """
    global args, module_name

    subprocess_args = [
        module_name
    ] + sys.argv[1:]
    subprocess.run(subprocess_args)


hips.setup(
    name="nnUNet_predict",  # Note: must be same as python module/file to run!
    version="0.1.0",
    description="Cellpose Prediction HIP Solution",
    git_repo="https://github.com/MouseLand/cellpose.git",
    license="BSD-3-Clause License",
    min_hips_version="0.1.0",
    tested_hips_version="0.1.0",
    args="pass-through",
    init=hips_init,
    main=cellpose_prediction,
    dependencies={  # ToDo: Discuss: how to handle pip installable solutions without yaml in their repo?
        'environment_name': "nnunet",
        'environment_file': tempfile.SpooledTemporaryFile(max_size=1000, mode='w+').write("""
name:nnunet
dependencies:
    - python>3.4,<3.8
    - pip
    - pip:
        - nnunet 
"""),
    }
)

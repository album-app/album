# Copyright 2021 Kyle Harrington

import subprocess
import sys
import hips

global args, python_path, module_name, active_hips


def hips_init():
    """
    Initialization to setup this HIPS
    """
    global args, python_path, module_name, active_hips

    # set module name
    module_name = "cellpose"


# ToDo: setup install routine in the hips environment
def install_routine():
    """Installation routine of the hips solution. Does not run in the target environment,
    but expects target environment to be already created.
    Can only call methods in the source environment."""
    import install_helper.modules

    install_helper.modules.download_repository(hips.get_active_hips())


def cellpose_prediction():
    """
    This is the main entry point of this HIPS
    """
    global args, python_path, module_name

    subprocess_args = [
        'python', '-m', module_name
    ] + sys.argv[1:]
    subprocess.run(subprocess_args)


hips.setup(
    name="cellpose",
    version="0.1.0",
    description="Cellpose Prediction HIP Solution",
    git_repo="https://github.com/MouseLand/cellpose.git",  # ToDo: specific githash -> no version slip!
    license="BSD-3-Clause License",
    min_hips_version="0.1.0",
    tested_hips_version="0.1.0",
    args="pass-through",
    install=install_routine,  # in the source environment
    init=hips_init,  # in the target environment
    main=cellpose_prediction,
    dependencies={
        # could also be a stream
        'environment_file': 'https://raw.githubusercontent.com/MouseLand/cellpose/2447cfeb266185c0de9ff4a800a8f61d8ac42226/environment.yml',
    }
)

# Copyright 2021 Kyle Harrington

import hips
import subprocess
import sys

global args


def hips_init():
    """
    Initialization to setup this HIPS
    """
    global args
    args = {}
    # trying to create environment via cli - cannot switch environement within this process
    # also Command "conda env create -f yamlfile.yaml" is not possible via cli
    # one could run the cellpose_prediction() with the python env created here ???...

    # import conda.cli.python_api as conda
    # conda.run_command(conda.Commands.CREATE, ["-n", "cellpose"])


def cellpose_prediction():
    """
    This is the main entry point of this HIPS
    """
    global args
    import runpy

    # hardcoded path to cellpose repo - needs to be downloaded in init process?
    sys.path.insert(0, '/home/jpa/PycharmProjects/cellpose/')

    # run the cellpose module
    # gennot get the arguments to work here - will switch to subprocess now
    #runpy.run_module('cellpose')

    # not the best solution to run a module...
    subprocess.run([
        'python', '-m', 'cellpose.cellpose', '--dir', '/home/jpa/tmp/', '--pretrained_model', 'cyto', '--save_png'
    ])


hips.setup(
    name="cellpose",
    version="0.1.0",
    description="Cellpose Prediction HIP Solution",
    git_repo="https://github.com/MouseLand/cellpose.git",
    license="BSD-3-Clause License",
    min_hips_version="0.1.0",
    tested_hips_version="0.1.0",
    args=[],
    init=hips_init,
    main=cellpose_prediction
)

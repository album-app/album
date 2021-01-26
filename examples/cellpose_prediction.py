# Copyright 2021 Kyle Harrington

import subprocess
import os
import sys
import hips

global args


def hips_init():
    """
    Initialization to setup this HIPS
    """
    global args

    # name = str(hips.get_active_hips()['name']),
    #
    # sys.path.insert(0, get_deployment_path())
    # exec("import {} as hips_module".format(name[0]))
    # argument_parsing()

    # trying to create environment via cli - cannot switch environement within this process
    # also Command "conda env create -f yamlfile.yaml" is not possible via cli
    # one could run the cellpose_prediction() with the python env created here ???...

    # import conda.cli.python_api as conda
    # conda.run_command(conda.Commands.CREATE, ["-n", "cellpose"])


def get_deployment_path():
    return "/home/jpa/PycharmProjects/cellpose-git/"


def cellpose_prediction():
    """
    This is the main entry point of this HIPS
    """
    global args

    import importlib
    import importlib.abc
    import runpy
    #
    #name = str(hips.get_active_hips()['name']),
    #name = name[0]
    sys.path.insert(0, os.path.join(get_deployment_path()))
    #
    #
    # #runpy.run_module(name)
    #
    #
    #importlib.import_module(name)
    #
    # y = importlib.abc.Loader()
    # y.exec_module()
    #
    # print(type(x))
#     # #sys.modules[name].__main__()
#     # print(help(sys.modules[name]))
#     environment_system = {**os.environ.copy(), **{'PYTHONPATH': get_deployment_path()}}
#
# # /home/jpa/PycharmProjects/cellpose/cellpose/t.py
#     subprocess.run([
#         'python', '/home/jpa/t/t.py', '--dir', '/home/jpa/tmp/', '--pretrained_model', 'cyto', '--save_png'
#     ], env=environment_system)
#
#     os.chdir(get_deployment_path())
#     subprocess.run([
#         'python', '-m', 'cellpose', '--dir', '/home/jpa/tmp/', '--pretrained_model', 'cyto', '--save_png'
#     ])
    os.chdir(get_deployment_path())
    print(os.getcwd())
    runpy.run_module('cellpose')

    #exec("cellpose.main()")
    #
    # environment_name = hips.get_environment_name(hips.get_active_hips())
    # environment = os.path.join(os.path.expanduser('~/'), 'anaconda3',
    #                            'envs', environment_name)
    #
    # subprocess_args = [
    #     'conda', 'run', '--no-capture-output', '--prefix', environment,
    #     'python', '-m', name[0],
    # ]
    #
    # environment_system = {**os.environ.copy(), **{'PYTHONPATH': get_deployment_path()}}
    # name = str(hips.get_active_hips()['name']),
    #
    # sys.path.insert(0, get_deployment_path())
    # exec("import {} as hips_module".format(name[0]))
    # exec("hips_module.__main__.py")

    # not the best solution to run a module...
    #subprocess.run(subprocess_args, env=environment_system)


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

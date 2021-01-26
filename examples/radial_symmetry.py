# Copyright 2021 Kyle Harrington

import hips

global ij, args


def hips_init():
    """
    Initialization to setup this HIPS
    """
    global ij, args

    from scyjava import config, jimport
    config.add_repositories({'jitpack': 'https://jitpack.io'})
    import imagej
    # Create an ImageJ gateway (this should be run within the main function)
    ij = imagej.init([
        'net.imagej:imagej:2.1.0',
        'com.github.PreibischLab:RadialSymmetryLocalization:05e39f6',
        'net.imagej:imagej-legacy:0.37.4'
    ],
                     headless=True)
    ImageJFunctions = jimport("net.imglib2.img.display.imagej.ImageJFunctions")
    HashMap = jimport("java.util.HashMap")
    IJ = jimport("ij.IJ")
    args = HashMap()
    args.put("parameterType", "Advanced")  # Hard coded for this plugin


def radial_symmetry():
    """
    This is the main entry point of this HIPS
    """
    global ij, args

    ij.command().run("gui.radial.symmetry.plugin.Radial_Symmetry", True, args)


# Read the README.md as the long description
with open("README.md") as f:
    long_description = f.read()

hips.setup(name="radial-symmetry",
           version="0.1.0",
           description="Radial symmetry HIP Solution",
           git_repo="https://github.com/ida-mdc/hips",
           license="MIT License",
           min_hips_version="0.1.0",
           tested_hips_version="0.1.0",
           args=[{
               "name": "imp",
               "default": "https://someimage.com/imageStack.tif",
               "description": "Path to a 2D or 3D image stack",
               "action": lambda path: args.put("imp", IJ.openImage(path))
           }, {
               "name": "anisotropy",
               "default": 1.0,
               "description": "Anisotropy of voxels in the 3D image",
               "action": lambda v: args.put("anisotropy", v)
           }, {
               "name": "RANSAC",
               "default": True,
               "description": "Use RANSAC",
               "action": lambda v: args.put("RANSAC", v)
           }, {
               "name": "sigma",
               "default": 2.0,
               "description": "Sigma value for radial symmetry",
               "action": lambda v: args.put("sigma", v)
           }, {
               "name": "threshold",
               "default": 0.01,
               "description": "Threshold for radial symmetry",
               "action": lambda v: args.put("threshold", v)
           }, {
               "name": "supportRegion",
               "default": 1,
               "description":
               "Support region around the point for radial symmetry",
               "action": lambda v: args.put("supportRegion", v)
           }, {
               "name": "inlierRatio",
               "default": 0.3,
               "description": "Inlier ratio for determining points",
               "action": lambda v: args.put("inlierRatio", v)
           }, {
               "name": "maxError",
               "default": 0.75,
               "description": "Maximum error",
               "action": lambda v: args.put("maxError", v)
           }, {
               "name": "resultsPath",
               "default": "./radial_symmetry_results.txt",
               "description": "Results file for saving all detected points",
               "action": lambda path: args.put("resultsFilePath", path)
           }],
           init=hips_init,
           main=radial_symmetry,
           dependencies={'environment_name': 'hips_full'})

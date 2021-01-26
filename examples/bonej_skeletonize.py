# Copyright 2021 Kyle Harrington

import hips

global ij, args, output_path, IJ


def init():
    """
    Initialization to setup this HIPS
    """
    global ij, args, IJ

    from scyjava import jimport

    import imagej
    # Create an ImageJ gateway (this should be run within the main function)
    ij = imagej.init([
        'net.imagej:imagej:2.1.0', 'org.bonej:bonej-plugins:7.0.9',
        'net.imagej:imagej-legacy:0.37.4'
    ],
                     headless=True)
    ImageJFunctions = jimport("net.imglib2.img.display.imagej.ImageJFunctions")
    HashMap = jimport("java.util.HashMap")
    IJ = jimport("ij.IJ")
    args = HashMap()


def run():
    """
    This is the main entry point of this HIPS
    """
    global ij, args, output_path

    # Hard coding for testing
    args.put(
        "inputImage",
        IJ.openImage(
            "/mnt/data/hips/bonej_skeletonize/bat-cochlea-volume.tif"))
    output_path = "/mnt/data/hips/bonej_skeletonize/bat-cochlea-volume_skeleton_test.tif"

    future = ij.command().run("org.bonej.wrapperPlugins.SkeletoniseWrapper",
                              True, args)

    command_module = future.get()
    output = command_module.getOutput("skeleton")
    IJ.saveAsTiff(output, output_path)


# Read the README.md as the long description
with open("README.md") as f:
    long_description = f.read()

hips.setup(name="bonej-skeletonize",
           version="0.1.0",
           description="BoneJ2-based skeletonize HIP Solution",
           git_repo="https://github.com/ida-mdc/hips",
           license="MIT License",
           min_hips_version="0.1.0",
           tested_hips_version="0.1.0",
           args=[{
               "name":
               "inputImage",
               "default":
               "https://someimage.com/imageStack.tif",
               "description":
               "Path an image stack",
               "action":
               lambda path: args.put("inputImage", IJ.openImage(path))
           }, {
               "name": "outputImage",
               "default": "./output.tif",
               "description": "Path for output image",
               "action": lambda path: (output_path := path)
           }],
           init=init,
           main=run,
           dependencies={'environment_name': 'hips_full'})

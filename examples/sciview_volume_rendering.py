# Copyright 2021 Deborah Schmidt
# example usage: python -m hips run examples/mask_to_mesh.py

import hips

global ij, args


def hips_init():
    """
    Initialization to setup this HIPS
    """
    global ij, args

    from scyjava import config, jimport
    config.add_repositories({'scijava.public': 'https://maven.scijava.org/content/groups/public'})
    config.add_repositories({'jitpack': 'https://jitpack.io'})
    import imagej
    # Create an ImageJ gateway (this should be run within the main function)
    ij = imagej.init([
        'net.imagej:imagej:2.2.0',
        'net.imagej:imagej-legacy:0.37.4',
        'sc.iview:sciview:311d92a2cf'
    ], headless=False)

    HashMap = jimport("java.util.HashMap")
    args = HashMap()


def sciview_volume_rendering():
    """
    This is the main entry point of this HIPS
    """
    global ij, args
    #
    # ij.command().run("sc.iview.commands.demo.basic.MeshDemo", True, args)


# Read the README.md as the long description
with open("README.md") as f:
    long_description = f.read()
hips.setup(
    name="sciview-volume-rendering",
    version="0.1.0",
    doi="coming soon",
    format_version="0.3.0",
    timestamp="2021-02-08T22:16:03.331998",
    description="sciview volume rendering HIP Solution",
    authors="Deborah Schmidt",
    cite="Günther, U., & Harrington, K. I. (2020). Tales from the Trenches: Developing sciview, a new 3D viewer "
         + "for the ImageJ community. VisGap @ EuroGraphics. arXiv preprint "
         + "[arXiv:2004.11897](https://arxiv.org/abs/2004.11897).",
    git_repo="https://github.com/scenerygraphics/sciview",
    tags=["volumetric viewer", "VR", "sciview", "scenery"],
    license="not specified",
    documentation="",
    covers=[
        {"source": "/assets/images/solutions/sciview-volume-rendering/cover.png",
         "description": "Cover created based on data from [MICCAI Challenge on "
         + "Circuit Reconstruction from Electron Microscopy Images](https://cremi.org/data/)"}
    ],
    sample_inputs=[],
    sample_outputs=[],
    min_hips_version="0.1.0",
    tested_hips_version="0.1.0",
    args=[{
        "name": "input",
        "description": "Path to 3D image stack"
    }],
    init=hips_init,
    main=sciview_volume_rendering,
    dependencies={'environment_name': 'hips_full'})


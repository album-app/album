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
    config.add_endpoints('sc.iview:sciview:311d92a2cf')
    HashMap = jimport("java.util.HashMap")
    args = HashMap()


def sciview_volume_rendering():
    """
    This is the main entry point of this HIPS
    """
    from scyjava import config, jimport
    SciView = jimport("sc.iview.SciView")
    sciView = SciView.create()
    sciView.open(args["input"])


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
        "default": "",
        "description": "Path to 3D image stack",
        "action":  lambda v: args.put("input", v)
    }],
    init=hips_init,
    main=sciview_volume_rendering,
    dependencies={'environment_name': 'hips_full'})


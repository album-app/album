from hips.core import setup


def hips_init():
    pass


def hips_run():
    pass

setup(
    group="group",
    name="name",
    title="name",
    version="0.1.0",

    format_version="0.3.0",
    timestamp="",
    description="",
    authors="",
    cite="",
    git_repo="",
    tags=[],
    license="license",
    documentation="",
    covers=[],
    sample_inputs=[],
    sample_outputs=[],
    min_hips_version="0.1.0",
    tested_hips_version="0.1.0",
    args=[],
    init=hips_init,
    run=hips_run,
    dependencies={
        'environment_name': 'hips'
    })


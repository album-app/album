import hips


def hips_init():
    pass


def hips_run():
    pass


hips.setup(
    group="group",
    name="name",
    version="0.1.0",
    doi="",
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
    main=hips_run,
    dependencies={
        'environment_name': 'hips'
    })


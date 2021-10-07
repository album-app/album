from album.runner import setup


def album_init():
    pass


def album_run():
    pass


def album_install():
    pass


setup(
    group="group",
    name="name",
    title="name",
    version="0.1.0",
    doi="",
    deposit_id="",
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
    min_album_version="0.1.1",
    tested_album_version="0.1.1",
    args=[
        {
            "name": "testArg1",
            "description": "testArg1Description",
            "type": "string",
            "default": "Useless callable",
        }
    ],
    init=album_init,
    run=album_run,
    install=album_install,
    dependencies={
        'environment_name': 'album'
    })

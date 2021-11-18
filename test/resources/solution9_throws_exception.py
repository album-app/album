from album.runner import setup


def album_run():
    raise RuntimeError("Error in the run method")


def album_install():
    pass


setup(
    group="group",
    name="solution9_throws_exception",
    title="solution9_throws_exception",
    version="0.1.0",
    doi="",
    deposit_id="",
    timestamp="",
    description="",
    authors="",
    cite=[],
    git_repo="",
    tags=[],
    license="license",
    documentation=[""],
    covers=[],
    sample_inputs=[],
    sample_outputs=[],
    album_version="0.1.1",
    album_api_version="0.1.1",
    args=[
        {
            "name": "testArg1",
            "description": "testArg1Description",
            "type": "string",
            "default": "Useless callable",
        }
    ],
    run=album_run,
    install=album_install,
    dependencies={
        'environment_name': 'album'
    })

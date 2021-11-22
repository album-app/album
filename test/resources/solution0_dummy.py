from album.runner import setup


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
    timestamp="",
    description="",
    authors=[],
    cite=[],
    acknowledgement="",
    tags=[],
    license="license",
    documentation=[""],
    covers=[],
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
    dependencies={}
)

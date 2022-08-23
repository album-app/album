from album.runner.api import setup


def album_run():
    pass


def album_install():
    pass


setup(
    group="group",
    name="name",
    title="name",
    version="0.1.0",
    doi="a/doi",
    description="A description",
    solution_creators=["Me"],
    cite=[],
    acknowledgement="Hi mom",
    tags=["tag1", "tag2"],
    license="license",
    covers=[],
    documentation=["file.md"],
    album_api_version="0.5.1",
    args=[
        {
            "name": "testArg1",
            "description": "testArg1Description",
            "type": "string",
        }
    ],
    run=album_run,
    install=album_install,
    dependencies={},
)

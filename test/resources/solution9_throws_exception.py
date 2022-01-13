from album.runner.api import setup


def album_run():
    raise RuntimeError("Error in the run method")


def album_install():
    pass


setup(
    group="group",
    name="solution9_throws_exception",
    version="0.1.0",
    album_api_version="0.3.1",
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

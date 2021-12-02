from album.runner.api.runner import setup


setup(
    group="group",
    name="name",
    version="0.1.0",
    album_api_version="0.1.1",
    args=[
        {
            "name": "testArg1",
            "description": "testArg1Description",
        }
    ],
    dependencies={}
)

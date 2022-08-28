from album.runner.api import setup


def album_run():
    from album.runner.api import get_active_solution

    print(get_active_solution().setup().authors)


setup(
    group="group",
    name="name",
    title="name",
    version="0.1.0",
    doi="a/doi",
    description="A description",
    authors=["Me"],
    cite=[],
    acknowledgement="Hi mom",
    tags=["tag1", "tag2"],
    license="license",
    covers=[],
    album_api_version="0.4.1",
    args=[
        {
            "name": "testArg1",
            "description": "testArg1Description",
            "type": "string",
            "default": "defaultValue",
        }
    ],
    run=album_run,
    dependencies={},
)

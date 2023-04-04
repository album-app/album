from album.runner.api import setup

env_file = """name: Dummy-Solution-Lock
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.8
  - pip
"""

def album_run():
    pass


def album_install():
    pass


setup(
    group="group",
    name="Dummy-Solution-Lock",
    title="Dummy-Solution-Lock",
    version="0.1.0",
    doi="a/doi",
    description="A description",
    solution_creators=["Me"],
    cite=[],
    acknowledgement="Hi mom",
    tags=["tag1", "tag2"],
    license="license",
    covers=[],
    album_api_version="0.5.1",
    args=[
        {
            "name": "testArg1",
            "description": "testArg1Description",
            "type": "string",
            "default": "defaultValue",
        }
    ],
    run=album_run,
    install=album_install,
    dependencies={'environment_file': env_file},
)

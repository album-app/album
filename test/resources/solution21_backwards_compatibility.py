from album.runner.api import setup

env_file = """name: backwards_compatibility
channels:
    - conda-forge
dependencies:
    - python=3.8.5
    - pip
    - pip:
        - git+https://gitlab.com/album-app/album-runner.git
"""


def album_run():
    print("Run backwards compatibility solution")


def album_uninstall():
    print("Uninstall backwards compatibility solution")


def album_pre_test():
    print("Pre test backwards compatibility solution")


def album_test():
    print("Test backwards compatibility solution")


setup(
    group="group",
    name="solution21_backwards_compatibility",
    version="0.1.0",
    album_api_version="0.5.5",
    args=[
        {
            "name": "testArg1",
            "description": "testArg1Description",
            "type": "string",
            "default": "Useless callable",
        }
    ],
    run=album_run,
    uninstall=album_uninstall,
    pre_test=album_pre_test,
    test=album_test,
    dependencies={"environment_file": env_file},
)

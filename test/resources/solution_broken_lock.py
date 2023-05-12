from album.runner.api import setup, get_args


env_file = """name: Dummy-Solution
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.8
  - pip
  - maven=3.8.1

"""


def install():
    from album.runner.api import setup, get_args , get_package_path
    print("HI I AM A DUMMY INSTALL FUNCTION")


def run():
    from album.runner.api import setup, get_args , get_package_path
    from pathlib import Path
    import os
    print("HI I AM A DUMMY RUN FUNCTION of the version 0.1.0")


def prepare_test():
    return {}


def test():
    from album.runner.api import setup, get_args
    import os
    print("TEST")

def close():
    from album.runner.api import setup, get_args
    print("closing")


setup(
    group="album",
    name="CONDA_LOCK_ERROR_SOLUTION",
    version="0.1.0",
    title="A Dummy Solution to fail when using conda lock.",
    description="A Dummy Solution to fail when using conda lock.",
    authors=["Lucas Rieckert"],
    cite=[{
        "text": "Your first citation text",
        "doi": "your first citation doi"
    }],
    tags=["conda_lock", "test"],
    license="UNLICENSE",
    documentation="",
    covers=[{
        "description": "Dummy cover image.",
        "source": "cover.png"
    }],
    album_api_version="0.4.1",
    args=[],
    install=install,
    run=run,
    close=close,
    pre_test=prepare_test,
    test=test,
    dependencies={'environment_file': env_file}
)
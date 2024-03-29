from album.runner.api import setup, get_cache_path
from io import StringIO

env_file = StringIO(
    """channels:
  - defaults
  - conda-forge
dependencies:
  - python=3.7
  - pip
  - git
  - pip:
    - https://gitlab.com/album-app/album/-/archive/dev/album-dev.zip
"""
)


def album_run():
    from album.api import Album
    import tempfile
    import os
    from album.runner.album_logging import get_active_logger

    print("print something")
    get_active_logger().info("logging info")
    get_active_logger().warning("logging warning")
    get_active_logger().error("logging error")

    get_cache_path().mkdir(exist_ok=True, parents=True)

    with tempfile.TemporaryDirectory(dir=get_cache_path()) as album_cache:
        album = Album.Builder().base_cache_path(album_cache).build()
        album.load_or_create_collection()

        with tempfile.NamedTemporaryFile(
            dir=get_cache_path(), mode="w", delete=False
        ) as solution_file:
            solution_file.write(get_solution_content())

        solution_file = str(solution_file.name)
        if album.is_installed(solution_file):
            album.uninstall(solution_file)
        album.install(solution_file)
        album.run(solution_file)
        os.remove(solution_file)


def get_solution_content():
    return '''from album.runner.api import setup
from io import StringIO

env_file = StringIO("""channels:
  - defaults
dependencies:
  - python=3.7
  - pip
""")

def run():
    from album.runner.album_logging import get_active_logger
    print("album in album: print something")
    get_active_logger().info("album in album: logging info")
    get_active_logger().warning("album in album: logging warning")
    get_active_logger().error("album in album: logging error")
    raise RuntimeError("Error in run method")

setup(
    group="group",
    name="solution9_throws_exception",
    version="0.1.0",
    album_api_version="0.5.1",
    run=run,
    dependencies={
        'environment_file': env_file
    }
)
'''


setup(
    group="group",
    name="solution15_run_album_throw_error",
    version="0.1.0",
    album_api_version="0.3.1",
    run=album_run,
    dependencies={"environment_file": env_file},
)

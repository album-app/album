from io import StringIO

from album.runner.api import setup, get_cache_path

env_file = StringIO("""name: template-album
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.7
  - pip:
    - https://gitlab.com/album-app/album/-/archive/release-0.3.0/album-release-0.3.0.zip
    - album-runner==0.3.1
""")

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

        with tempfile.NamedTemporaryFile(dir=get_cache_path(), mode='w', delete=False) as solution_file:
            solution_file.write(get_solution_content())

        solution = album.resolve(solution_file.name)
        if album.is_installed(solution):
            album.uninstall(solution)
        album.install(solution)
        album.run(solution)
        os.remove(solution_file.name)


def get_solution_content():
    return """from album.runner.api import setup


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
    album_api_version="0.3.1",
    run=run
)
"""


setup(
    group="group",
    name="solution15_run_album_throw_error",
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
    dependencies={'environment_file': env_file}
)

from io import StringIO

from album.runner.api import setup, get_cache_path

env_file = StringIO("""name: template-album
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.6
  - pip:
    - https://gitlab.com/album-app/album/-/archive/fix-subprocess-logging/album-fix-subprocess-logging.zip
    - album-runner==0.2.1
""")

def album_run():
    from album.api import Album
    import tempfile

    with tempfile.TemporaryDirectory(dir=get_cache_path()) as album_cache:
        album = Album.Builder().base_cache_path(album_cache.name).build()
        album.load_or_create_collection()

        with tempfile.NamedTemporaryFile(dir=get_cache_path()) as solution_file:
            solution_file.write("""from album.runner.api import setup

def run():
    raise RuntimeError("Error in the run method")

setup(
    group="group",
    name="solution9_throws_exception",
    version="0.1.0",
    album_api_version="0.3.0",
    run=run
)
            """)
            solution = album.resolve(solution_file.name)
            if album.is_installed(solution):
                album.uninstall(solution)
            album.install(solution)
            album.run(solution)


setup(
    group="group",
    name="solution15_run_album_throw_error",
    version="0.1.0",
    album_api_version="0.2.1",
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

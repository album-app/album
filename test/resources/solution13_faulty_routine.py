from album.runner.api import setup


def album_install():
    import notExistandLibraryRaisingAnUglyError

setup(
    group="group",
    name="faultySolution",
    title="name",
    version="0.1.0",
    album_api_version="0.2.1",
    install=album_install,
)

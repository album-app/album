from album.runner.api.runner import setup


def album_install():
    import notExistandLibraryRaisingAnUglyError

setup(
    group="group",
    name="faultySolution",
    title="name",
    version="0.1.0",
    album_api_version="0.1.1",
    install=album_install,
)

from album.runner.api import setup


def album_install():
    pass

setup(
    group="group",
    name="faultySolution",
    title="name",
    version="0.1.0",
    album_api_version="0.4.1",
    install=album_install,
)

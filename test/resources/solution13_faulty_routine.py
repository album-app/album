from album.runner.api import setup


def album_install():
    raise RuntimeError("Faulty install routine")  # deliberately faulty — do not fix!


setup(
    group="group",
    name="faultySolution",
    title="name",
    version="0.1.0",
    album_api_version="0.7.1",
    install=album_install,
)

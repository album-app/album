import time

from album.runner import setup


def album_run():
    pass


def album_uninstall():
    print("solution10_uninstall_album_uninstall_start")
    time.sleep(5)
    print("solution10_uninstall_album_uninstall_end")


def album_install():
    pass


def album_remove():
    pass


def album_pre_test():
    pass


def album_test():
    pass


setup(
    group="group",
    name="solution10_uninstall",
    title="solution10",
    version="0.1.0",
    timestamp="",
    description="",
    authors=[],
    cite=[],
    acknowledgement="",
    tags=[],
    license="license",
    documentation=[],
    covers=[],
    album_version="0.1.1",
    album_api_version="0.1.1",
    args=[
        {
            "name": "testArg1",
            "description": "testArg1Description",
            "type": "string",
            "default": "Useless callable",
        }
    ],
    run=album_run,
    install=album_install,
    uninstall=album_uninstall,
    pre_test=album_pre_test,
    test=album_test,
    dependencies={}
)

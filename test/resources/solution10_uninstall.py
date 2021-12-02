import time

from album.runner.album_logging import get_active_logger
from album.runner.api.runner import setup


def album_run():
    pass


def album_uninstall():
    get_active_logger().info("solution10_uninstall_album_uninstall_start")
    time.sleep(5)
    get_active_logger().info("solution10_uninstall_album_uninstall_end")


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
    version="0.1.0",
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

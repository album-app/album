import time

from album.runner.album_logging import get_active_logger
from album.runner.api import setup

global args


def album_run():
    get_active_logger().info("solution7_long_routines_run_start")
    time.sleep(5)
    get_active_logger().info("solution7_long_routines_run_end")


def album_install():
    get_active_logger().info("solution7_long_routines_install_start")
    time.sleep(5)
    get_active_logger().info("solution7_long_routines_install_end")


def album_pre_test():
    get_active_logger().info("solution7_long_routines_pre_test_start")
    get_active_logger().info("solution7_long_routines_pre_test_end")
    return {}


def album_test():
    get_active_logger().info("solution7_long_routines_test_start")
    time.sleep(5)
    get_active_logger().info("solution7_long_routines_test_end")


setup(
    group="group",
    name="solution7_long_routines",
    title="solution7",
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
    install=album_install,
    pre_test=album_pre_test,
    test=album_test,
    dependencies={}
)

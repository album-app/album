import time

from album.runner import setup

global args


def album_init():
    pass


def album_run():
    print("solution7_long_routines_run_start")
    time.sleep(5)
    print("solution7_long_routines_run_end")


def album_install():
    print("solution7_long_routines_install_start")
    time.sleep(5)
    print("solution7_long_routines_install_end")


def album_pre_test():
    print("solution7_long_routines_pre_test_start")
    print("solution7_long_routines_pre_test_end")
    return {}


def album_test():
    print("solution7_long_routines_test_start")
    time.sleep(5)
    print("solution7_long_routines_test_end")


setup(
    group="group",
    name="solution7_long_routines",
    title="solution7",
    version="0.1.0",
    format_version="0.3.0",
    timestamp="",
    description="",
    authors="",
    cite="",
    git_repo="",
    tags=[],
    license="license",
    documentation="",
    covers=[],
    sample_inputs=[],
    sample_outputs=[],
    min_album_version="0.1.1",
    tested_album_version="0.1.1",
    args=[
        {
            "name": "testArg1",
            "description": "testArg1Description",
            "type": "string",
            "default": "Useless callable",
        }
    ],
    init=album_init,
    run=album_run,
    install=album_install,
    pre_test=album_pre_test,
    test=album_test,
    dependencies={}
)

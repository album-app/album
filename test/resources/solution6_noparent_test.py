import sys

from album_runner import setup
import tempfile

global args


def album_init():
    print("solution6_noparent_test_init")

    global args
    args = {}
    pass


def album_run():
    # log-output
    print("solution6_noparent_test_run")

    # log output in file passed as argument
    file = open(args.get("file"), "a")
    file.write("solution6_noparent_test_run\n")
    file.close()


def album_close():
    # log-output
    print("solution6_noparent_test_close")

    # log output in file passed as argument
    file = open(args.get("file"), "a")
    file.write("solution6_noparent_test_close\n")
    file.close()


def album_prepare_test():
    # log-output
    print("solution6_noparent_test_pre_test")

    # here we prepare the arguments for run() during testing
    file = tempfile.NamedTemporaryFile(delete=False, mode="w+")
    file.write("File created in album_prepare_test\n")
    file.close()

    # and we set the arguments
    return {
        "--file": file.name
    }


def album_test():
    # log-output
    print("solution6_noparent_test_test")

    # here we load sys.argv
    file = open(args.get("file"), "r")
    file_content = file.readlines()
    file.close()
    # and we do a test
    expected_result = [
        "File created in album_prepare_test\n", "solution6_noparent_test_run\n", "solution6_noparent_test_close\n"
    ]
    assert expected_result == file_content


setup(
    group="group",
    name="solution6_noparent_test",
    title="solution six, no parent, nice test routine",
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
    min_album_version="0.1.0",
    tested_album_version="0.1.0",
    args=[{
        "name": "file",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"file": path})
    }],
    init=album_init,
    run=album_run,
    close=album_close,
    pre_test=album_prepare_test,
    test=album_test,
    dependencies={
        'environment_name': 'solution6_noparent_test'
    })

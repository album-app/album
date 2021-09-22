from album_runner import setup
import tempfile

from album_runner.api.run_helper import get_args


def album_init():
    print("solution6_noparent_test_init")


def album_run():
    args = get_args()

    # log-output
    print("solution6_noparent_test_run")

    # log output in file passed as argument
    file = open(args.file, "a")
    file.write("solution6_noparent_test_run\n")
    file.close()


def album_close():
    args = get_args()

    # log-output
    print("solution6_noparent_test_close")

    # log output in file passed as argument
    file = open(args.file, "a")
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
    args = get_args()

    # log-output
    print("solution6_noparent_test_test")

    # here we load sys.argv
    file = open(args.file, "r")
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
    min_album_version="0.1.1",
    tested_album_version="0.1.1",
    args=[{
        "name": "file",
        "description": "",
    }],
    init=album_init,
    run=album_run,
    close=album_close,
    pre_test=album_prepare_test,
    test=album_test,
    dependencies={
        'environment_name': 'solution6_noparent_test'
    })

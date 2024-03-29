import tempfile

from album.runner.album_logging import get_active_logger
from album.runner.api import get_args
from album.runner.api import setup


def album_run():
    args = get_args()

    # log-output
    get_active_logger().info("solution6_noparent_test_run")

    # log output in file passed as argument
    file = open(args.file, "a")
    file.write("solution6_noparent_test_run\n")
    file.close()


def album_close():
    args = get_args()

    # log-output
    get_active_logger().info("solution6_noparent_test_close")

    # log output in file passed as argument
    file = open(args.file, "a")
    file.write("solution6_noparent_test_close\n")
    file.close()


def album_prepare_test():
    # log-output
    get_active_logger().info("solution6_noparent_test_pre_test")

    # here we prepare the arguments for run() during testing
    file = tempfile.NamedTemporaryFile(delete=False, mode="w+")
    file.write("File created in album_prepare_test\n")
    file.close()

    # and we set the arguments
    return {"--file": file.name}


def album_test():
    args = get_args()

    # log-output
    get_active_logger().info("solution6_noparent_test_test")

    # here we load sys.argv
    file = open(args.file, "r")
    file_content = file.readlines()
    file.close()
    # and we do a test
    expected_result = [
        "File created in album_prepare_test\n",
        "solution6_noparent_test_run\n",
        "solution6_noparent_test_close\n",
    ]
    assert expected_result == file_content


setup(
    group="group",
    name="solution6_noparent_test",
    title="solution six, no parent, nice test routine",
    version="0.1.0",
    album_api_version="0.5.1",
    args=[
        {
            "name": "file",
            "description": "",
        }
    ],
    run=album_run,
    close=album_close,
    pre_test=album_prepare_test,
    test=album_test,
    dependencies={},
)

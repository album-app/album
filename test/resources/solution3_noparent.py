from album.runner.api import get_args
from album.runner.api import setup


def album_run():
    args = get_args()

    file = open(args.file, "a")
    file.write("solution3_noparent_run\n")
    file.close()


def album_close():
    args = get_args()

    file = open(args.file, "a")
    file.write("solution3_noparent_close\n")
    file.close()


setup(
    group="group",
    name="solution3_noparent",
    title="solution three, no parent",
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
    dependencies={},
)

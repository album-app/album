from album.runner import setup
from album.runner.api import get_args


def album_init():
    pass


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
    format_version="0.3.0",
    timestamp="",
    description="",
    authors="",
    cite=[],
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
    dependencies={}
)

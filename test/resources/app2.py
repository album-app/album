from album.runner import setup
from album.runner.api import get_args


def album_run():
    args = get_args()

    file = open(args.file, "a")
    file.write("app2_run\n")
    file.write(f"app2_param={args.app2_param}\n")
    file.close()


def album_close():
    args = get_args()

    file = open(args.file, "a")
    file.write("app2_close\n")
    file.close()


setup(
    group="group",
    name="app2",
    title="app two",
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
    args=[{
        "name": "file",
        "description": "",
    }, {
        "name": "app2_param",
        "description": "",
    }],
    run=album_run,
    close=album_close,
    dependencies={}
)


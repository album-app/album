from album_runner import setup
from album_runner.api.run_helper import get_args


def album_init():
    pass


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
    }, {
        "name": "app2_param",
        "description": "",
    }],
    init=album_init,
    run=album_run,
    close=album_close,
    dependencies={
        'environment_name': 'app2'
    })


from album.runner import setup
from album.runner.api import get_args


def album_init():
    pass


def album_run():
    args = get_args()

    file = open(args.file_solution5_app2, "a")
    file.write("solution5_app2_run\n")
    file.close()


def album_close():
    args = get_args()

    file = open(args.file_solution5_app2, "a")
    file.write("solution5_app2_close\n")
    file.close()


setup(
    group="group",
    name="solution5_app2",
    title="solution five on app two",
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
        "name": "file_solution5_app2",
        "description": "",
    }],
    init=album_init,
    run=album_run,
    close=album_close,
    parent={
        'name': 'app2',
        'group': 'group',
        'version': '0.1.0',
        'args': [
            {
                "name": "app2_param",
                "value": "app2_param_value"
            }
        ]
    })


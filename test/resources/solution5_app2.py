from album.runner.api import get_args
from album.runner.api import setup


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
    album_api_version="0.4.0",
    args=[{
        "name": "file_solution5_app2",
        "description": "",
    }],
    run=album_run,
    close=album_close,
    dependencies={
        'parent': {
            'name': 'app2',
            'group': 'group',
            'version': '0.1.0',
            'args': [
                {
                    "name": "app2_param",
                    "value": "app2_param_value"
                }
            ]
        }
    }
)


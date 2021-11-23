from album.runner import setup
from album.runner.api import get_args


def album_run():
    args = get_args()

    file = open(args.file_solution4_app2, "a")
    file.write("solution4_app2_run\n")
    file.close()


def album_close():
    args = get_args()

    file = open(args.file_solution4_app2, "a")
    file.write("solution4_app2_close\n")
    file.close()


setup(
    group="group",
    name="solution4_app2",
    title="solution four on app two",
    version="0.1.0",
    album_api_version="0.1.1",
    args=[{
        "name": "file_solution4_app2",
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


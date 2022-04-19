from album.runner.api import get_args
from album.runner.api import setup


def album_run():
    args = get_args()

    file = open(args.file_solution2_app1, "a")
    file.write("solution2_app1_run\n")
    file.close()


def album_close():
    args = get_args()

    file = open(args.file_solution2_app1, "a")
    file.write("solution2_app1_close\n")
    file.close()


setup(
    group="group",
    name="solution2_app1",
    title="solution two on app one",
    version="0.1.0",
    album_api_version="0.4.0",
    args=[{
        "name": "file_solution2_app1",
        "description": "",
    }],
    run=album_run,
    close=album_close,
    dependencies={
        'parent': {
            'name': 'app1',
            'group': 'group',
            'version': '0.1.0',
            'args': [
                {
                    "name": "app1_param",
                    "value": "app1_param_other_value"
                }
            ]
        }
    }
    )


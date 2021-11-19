from album.runner import setup
from album.runner.api import get_args, get_cache_path


def album_init():
    pass


def album_install():
    print(get_cache_path().absolute())


def album_run():
    args = get_args()

    file = open(args.file_solution1_app1, "a")
    file.write("solution1_app1_run\n")
    file.close()
    print("A nice log run message!")
    print(get_cache_path().absolute())


def album_close():
    args = get_args()

    file = open(args.file_solution1_app1, "a")
    file.write("solution1_app1_close\n")
    file.close()
    print("A nice log close message!")


setup(
    group="group",
    name="solution1_app1",
    title="solution one on app one",
    version="0.1.0",
    timestamp="",
    description="",
    authors="",
    cite=[],
    git_repo="",
    tags=[],
    license="license",
    documentation=[""],
    covers=[],
    sample_inputs=[],
    sample_outputs=[],
    album_version="0.1.1",
    album_api_version="0.1.1",
    args=[{
        "name": "file_solution1_app1",
        "description": "",
    }],
    init=album_init,
    run=album_run,
    close=album_close,
    install=album_install,
    parent={
        'name': 'app1',
        'group': 'group',
        'version': '0.1.0',
        'args': [
            {
                "name": "app1_param",
                "value": "app1_param_value"
            }
        ]
    })


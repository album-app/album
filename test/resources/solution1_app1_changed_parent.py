from album.runner.album_logging import get_active_logger
from album.runner.api import get_args, get_cache_path
from album.runner.api import setup


def album_install():
    get_active_logger().info(get_cache_path().absolute())


def album_run():
    args = get_args()

    file = open(args.file_solution1_app1, "a")
    file.write("solution1_app1_run\n")
    file.close()
    get_active_logger().info("A nice log run message!")
    get_active_logger().info(get_cache_path().absolute())


def album_close():
    args = get_args()

    file = open(args.file_solution1_app1, "a")
    file.write("solution1_app1_close\n")
    file.close()
    get_active_logger().info("A nice log close message!")


setup(
    group="group",
    name="solution1_app1",
    title="solution one on app one",
    version="0.1.0",
    album_api_version="0.4.0",
    args=[{
        "name": "file_solution1_app1",
        "description": "",
    }],
    run=album_run,
    close=album_close,
    install=album_install,
    dependencies={
        'parent': {
            'name': 'app2',
            'group': 'group',
            'version': '0.1.0'
        }
    }
    )

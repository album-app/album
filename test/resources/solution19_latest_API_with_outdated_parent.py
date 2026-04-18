from album.runner.api import setup


def album_run():
    pass


def album_uninstall():
    pass


def album_install():
    pass


def album_remove():
    pass


def album_pre_test():
    pass


def album_test():
    pass


setup(
    group="group",
    name="solution19_latest_API",
    version="0.1.0",
    album_api_version="0.7.1",
    args=[
        {
            "name": "testArg1",
            "description": "testArg1Description",
            "type": "string",
            "default": "Useless callable",
        }
    ],
    run=album_run,
    install=album_install,
    uninstall=album_uninstall,
    pre_test=album_pre_test,
    test=album_test,
    dependencies={
        "parent": {"name": "app1", "group": "group", "version": "0.1.0"}
    },  # deliberately outdated parent
)

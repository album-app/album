from album.runner.api import setup


def album_run():
    print("Run backwards compatibility solution with parent")


def album_uninstall():
    print("Uninstall backwards compatibility solution with parent")


def album_install():
    print("Install backwards compatibility solution with parent")


def album_pre_test():
    print("Pre test backwards compatibility solution with parent")


def album_test():
    print("Test backwards compatibility solution with parent")


setup(
    group="group",
    name="solution21_backwards_compatibility_with_parent",
    version="0.1.0",
    album_api_version="0.5.5",  # deliberately set to 0.5.5, do not change
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
        "parent": {
            "name": "solution21_backwards_compatibility_parent",
            "group": "group",
            "version": "0.1.0",
        }
    },
)

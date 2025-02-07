from album.runner.api import (
    download_if_not_exists,
    extract_tar,
    get_active_logger,
    get_active_solution,
    get_app_path,
    get_args,
    get_cache_path,
    get_data_path,
    get_environment_name,
    get_environment_path,
    get_package_path,
    in_target_environment,
    setup,
)

env_file = """name: backwards_compatibility
channels:
    - conda-forge
dependencies:
    - python=3.8.5
    - pip
    - pip:
        - git+https://gitlab.com/album-app/album-runner.git
"""


def album_run():
    print("Run backwards compatibility solution")
    print(get_args())
    print(in_target_environment())
    print(get_environment_name())
    print(get_environment_path())
    print(get_data_path())
    print(get_package_path())
    print(get_app_path())
    print(get_cache_path())
    print(get_active_solution())
    print(download_if_not_exists)
    print(extract_tar)
    print(get_active_logger())


def album_install():
    print("Install backwards compatibility solution")


def album_uninstall():
    print("Uninstall backwards compatibility solution")


def album_pre_test():
    print("Pre test backwards compatibility solution")


def album_test():
    print("Test backwards compatibility solution")


setup(
    group="group",
    name="solution21_backwards_compatibility",
    version="0.1.0",
    album_api_version="0.0.0",  # deliberately set to 0.0.0, do not change, install framework via pip, see above!
    args=[
        {
            "name": "testArg1",
            "description": "testArg1Description",
            "type": "string",
            "default": "Useless callable",
        }
    ],
    run=album_run,
    uninstall=album_uninstall,
    install=album_install,
    pre_test=album_pre_test,
    test=album_test,
    dependencies={"environment_file": env_file},
)

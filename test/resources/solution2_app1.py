from album_runner import setup

global args


def album_init():
    global args
    args = {}
    pass


def album_run():
    file = open(args.get("file"), "a")
    file.write("solution2_app1_run\n")
    file.close()


def album_close():
    file = open(args.get("file"), "a")
    file.write("solution2_app1_close\n")
    file.close()


setup(
    group="group",
    name="solution2_app1",
    title="solution two on app one",
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
        "name": "file_solution2_app1",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"file": path})
    }],
    init=album_init,
    run=album_run,
    close=album_close,
    parent={
        'name': 'app1',
        'group': 'group',
        'version': '0.1.0',
        'args': [
            {
                "name": "app1_param",
                "value": "app1_param_other_value"
            }
        ]
    })


from album_runner import setup

global args


def album_init():
    global args
    args = {}
    pass


def album_run():
    global args
    file = open(args.get("file"), "a")
    file.write("solution4_app2_run\n")
    file.close()


def album_close():
    global args
    file = open(args.get("file"), "a")
    file.write("solution4_app2_close\n")
    file.close()


setup(
    group="group",
    name="solution4_app2",
    title="solution four on app two",
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
        "name": "file_solution4_app2",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"file": path})
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


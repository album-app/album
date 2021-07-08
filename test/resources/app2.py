from album_runner import setup

global args


def album_init():
    global args
    args = {}
    pass


def album_run():
    global args
    file = open(args.get("file"), "a")
    file.write("app2_run\n")
    file.write(f"app2_param={args.get('app2_param')}\n")
    file.close()
    pass


def album_close():
    global args
    file = open(args.get("file"), "a")
    file.write("app2_close\n")
    file.close()
    pass


setup(
    group="group",
    name="app2",
    title="app two",
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
    min_album_version="0.1.0",
    tested_album_version="0.1.0",
    args=[{
        "name": "file",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"file": path})
    }, {
        "name": "app2_param",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"app2_param": path})
    }],
    init=album_init,
    run=album_run,
    close=album_close,
    dependencies={
        'environment_name': 'app2'
    })


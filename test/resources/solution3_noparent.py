from album_runner import setup
global args


def album_init():
    global args
    args = {}
    pass


def album_run():
    file = open(args.get("file"), "a")
    file.write("solution3_noparent_run\n")
    file.close()


def album_close():
    file = open(args.get("file"), "a")
    file.write("solution3_noparent_close\n")
    file.close()


setup(
    group="group",
    name="solution3_noparent",
    title="solution three, no parent",
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
        "name": "file",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"file": path})
    }],
    init=album_init,
    run=album_run,
    close=album_close,
    dependencies={
        'environment_name': 'solution3_noparent'
    })


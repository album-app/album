from hips.core import setup

global args


def hips_init():
    global args
    args = {}
    pass


def hips_run():
    file = open(args.get("file"), "a")
    file.write("solution3_noparent_run\n")
    file.close()


def hips_close():
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
    min_hips_version="0.1.0",
    tested_hips_version="0.1.0",
    args=[{
        "name": "file",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"file": path})
    }],
    init=hips_init,
    run=hips_run,
    close=hips_close,
    dependencies={
        'environment_name': 'solution3_noparent'
    })


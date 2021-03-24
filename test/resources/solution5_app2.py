import hips

global args


def hips_init():
    global args
    args = {}
    pass


def hips_run():
    global args
    file = open(args.get("file"), "a")
    file.write("solution5_app2_run\n")
    file.close()


def hips_close():
    global args
    file = open(args.get("file"), "a")
    file.write("solution5_app2_close\n")
    file.close()


hips.setup(
    group="group",
    name="solution5_app2",
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
        "name": "file_solution5_app2",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"file": path})
    }],
    init=hips_init,
    run=hips_run,
    close=hips_close,
    parent={
        'name': 'app2',
        'args': [
            {
                "name": "app2_param",
                "value": "app2_param_value"
            }
        ]
    })


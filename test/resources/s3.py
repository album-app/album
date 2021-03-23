import hips

global args


def hips_init():
    global args
    args = {}
    pass


def hips_run():
    file = open(args.get("file"), "a")
    file.write("s3_run\n")
    file.close()


def hips_close():
    file = open(args.get("file"), "a")
    file.write("s3_close\n")
    file.close()


hips.setup(
    group="group",
    name="s3",
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
        "name": "file_s3",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"file": path})
    }],
    init=hips_init,
    run=hips_run,
    close=hips_close,
    parent={
        'name': 's2_app',
        'args': [
            {
                "name": "s2_app_param",
                "value": "s2_app_param_other_value"
            }
        ]
    })


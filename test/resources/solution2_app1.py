import hips

global args


def hips_init():
    global args
    args = {}
    pass


def hips_run():
    file = open(args.get("file"), "a")
    file.write("solution2_app1_run\n")
    file.close()


def hips_close():
    file = open(args.get("file"), "a")
    file.write("solution2_app1_close\n")
    file.close()


hips.setup(
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
    min_hips_version="0.1.0",
    tested_hips_version="0.1.0",
    args=[{
        "name": "file_solution2_app1",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"file": path})
    }],
    init=hips_init,
    run=hips_run,
    close=hips_close,
    parent={
        'name': 'app1',
        'args': [
            {
                "name": "app1_param",
                "value": "app1_param_other_value"
            }
        ]
    })


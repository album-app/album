import hips

global args


def hips_init():
    global args
    args = {}
    pass


hips.setup(
    group="group",
    name="s3_steps",
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
    steps=[{
        'name': 's2',
        'args': [
            {
                "name": "file",
                "value": lambda: args.get("file")
            }, {
                "name": "file_s2",
                "value": lambda: args.get("file")
            }, {
                "name": "s2_app_param",
                "value": lambda: "s2_app_param_value"
            }
        ]
    }, {
        'name': 's3',
        'args': [
            {
                "name": "file",
                "value": lambda: args.get("file")
            }, {
                "name": "file_s3",
                "value": lambda: args.get("file")
            }, {
                "name": "s2_app_param",
                "value": lambda: "s2_app_param_other_value"
            }
        ]
    }, {
        'name': 's3_noparent',
        'args': [
            {
                "name": "file",
                "value": lambda: args.get("file")
            }
        ]
    }])


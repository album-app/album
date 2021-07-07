from hips_runner import setup

global args


def hips_init():
    global args
    args = {}
    pass


setup(
    group="group",
    name="hips_with_steps_grouped",
    title="hips with steps grouped",
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
    steps=[
        [
            {
                'name': 'solution1_app1',
                'group': 'group',
                'version': '0.1.0',
                'args': [
                    {
                        "name": "file",
                        "value": lambda: args.get("file")
                    }, {
                        "name": "file_solution1_app1",
                        "value": lambda: args.get("file")
                    }, {
                        "name": "app1_param",
                        "value": lambda: "app1_param_value"
                    }
                ]
            }, {
                'name': 'solution2_app1',
                'group': 'group',
                'version': '0.1.0',
                'args': [
                    {
                        "name": "file",
                        "value": lambda: args.get("file")
                    }, {
                        "name": "file_solution2_app1",
                        "value": lambda: args.get("file")
                    }, {
                        "name": "app1_param",
                        "value": lambda: "app1_param_other_value"
                    }
                ]
            },
            {
                'name': 'solution3_noparent',
                'group': 'group',
                'version': '0.1.0',
                'args': [
                    {
                        "name": "file",
                        "value": lambda: args.get("file")
                    }
                ]
            },
            {
                'name': 'solution4_app2',
                'group': 'group',
                'version': '0.1.0',
                'args': [
                    {
                        "name": "file",
                        "value": lambda: args.get("file")
                    }, {
                        "name": "file_solution4_app2",
                        "value": lambda: args.get("file")
                    }, {
                        "name": "app2_param",
                        "value": lambda: "app2_param_value"
                    }
                ]
            }, {
                'name': 'solution5_app2',
                'group': 'group',
                'version': '0.1.0',
                'args': [
                    {
                        "name": "file",
                        "value": lambda: args.get("file")
                    }, {
                        "name": "file_solution5_app2",
                        "value": lambda: args.get("file")
                    }, {
                        "name": "app2_param",
                        "value": lambda: "app2_param_other_value"
                    }
                ]
            }
        ],
        {
            'name': 'solution3_noparent',
            'group': 'group',
            'version': '0.1.0',
            'args': [
                {
                    "name": "file",
                    "value": lambda: args.get("file")
                }
            ]
        }])

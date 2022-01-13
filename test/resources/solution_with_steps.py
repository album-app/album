from album.runner.api import setup


setup(
    group="group",
    name="solution_with_steps",
    title="album with steps",
    version="0.1.0",
    album_api_version="0.3.1",
    args=[{
        "name": "file",
        "description": "myfile",
    }],
    steps=[
        {
            'name': 'solution1_app1',
            'group': 'group',
            'version': '0.1.0',
            'args': [
                {
                    "name": "file",
                    "value": lambda args: args.file
                }, {
                    "name": "file_solution1_app1",
                    "value": lambda args: args.file
                }, {
                    "name": "app1_param",
                    "value": lambda args: "app1_param_value"
                }
            ]
        },
        {
            'name': 'solution2_app1',
            'group': 'group',
            'version': '0.1.0',
            'args': [
                {
                    "name": "file",
                    "value": lambda args: args.file
                }, {
                    "name": "file_solution2_app1",
                    "value": lambda args: args.file
                }, {
                    "name": "app1_param",
                    "value": lambda args: "app1_param_other_value"
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
                    "value": lambda args: args.file
                }
            ]
        }
    ]
)

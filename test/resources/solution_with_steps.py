from album_runner import setup


def album_init():
    pass


setup(
    group="group",
    name="solution_with_steps",
    title="album with steps",
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
        "description": "myfile",
    }],
    init=album_init,
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

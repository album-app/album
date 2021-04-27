import hips

global args


def hips_init():
    global args
    args = {}
    pass


def hips_run():
    global args
    file = open(args.get("file"), "a")
    file.write("app1_run\n")
    file.write(f"app1_param={args.get('app1_param')}\n")
    file.close()
    pass


def hips_close():
    global args
    file = open(args.get("file"), "a")
    file.write("app1_close\n")
    file.close()
    pass


hips.setup(
    group="group",
    name="app1",
    title="app one",
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
    }, {
        "name": "app1_param",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"app1_param": path})
    }],
    init=hips_init,
    run=hips_run,
    close=hips_close,
    dependencies={
        'environment_name': 'app1'
    })


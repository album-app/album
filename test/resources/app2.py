import hips

global args


def hips_init():
    global args
    args = {}
    pass


def hips_run():
    global args
    file = open(args.get("file"), "a")
    file.write("app2_run\n")
    file.write(f"app2_param={args.get('app2_param')}\n")
    file.close()
    print("app2_run")
    pass


def hips_close():
    global args
    file = open(args.get("file"), "a")
    file.write("app2_close\n")
    file.close()
    print("app2_close")
    pass


hips.setup(
    group="group",
    name="app2",
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
        "name": "app2_param",
        "default": "",
        "description": "",
        "action": lambda path: args.update({"app2_param": path})
    }],
    init=hips_init,
    run=hips_run,
    close=hips_close,
    dependencies={
        'environment_name': 'app2'
    })


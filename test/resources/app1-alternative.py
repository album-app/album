from album.runner.api import get_args


def album_run():
    args = get_args()

    file = open(args.file, "a")
    file.write("app1_run\n")
    file.write(f"app1_param={args.app1_param}\n")
    file.close()


def album_close():
    args = get_args()

    file = open(args.file, "a")
    file.write("app1_close\n")
    file.close()


def setup():
    return {
        "group": "group",
        "name": "app1",
        "title": "app one",
        "version": "0.1.0",
        "album_api_version": "0.5.1",
        "args": [
            {
                "name": "file",
                "description": "",
            },
            {
                "name": "app1_param",
                "description": "",
            },
        ],
        "run": album_run,
        "close": album_close,
        "dependencies": {},
    }


if __name__ == "__main__":
    from album.runner.api import load_solution

    solution = load_solution(setup())
    solution.run()

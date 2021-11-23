from album.runner import setup
from album.runner.api import get_args


def album_run():
    print("solution8_arguments_run_start")

    args = get_args()

    ia1 = args.integer_arg1
    ia2 = args.integer_arg2
    sa1 = args.string_arg1

    la1 = args.lambda_arg1
    la2 = args.lambda_arg2

    print("integer_arg1")
    print(type(ia1))
    print(ia1)

    print("integer_arg2")
    print(type(ia2))
    print(ia2)

    print("string_arg1")
    print(type(sa1))
    print(sa1)

    print("lambda_arg1")
    print(type(la1))
    print(la1)

    print("lambda_arg2")
    print(type(la2))
    print(la2)

    print("solution8_arguments_run_end")


def album_install():
    pass


def album_pre_test():
    pass


def album_test():
    pass


setup(
    group="group",
    name="solution8_arguments",
    title="solution7",
    version="0.1.0",
    album_api_version="0.1.1",
    args=[
        {
            "name": "integer_arg1",
            "default": 1,
            "description": "PositiveIntegerValue",
            "type": "int"
        },
        {
            "name": "integer_arg2",
            "required": False,
            "default": -1000,
            "description": "NegativeIntegerValue",
            "type": "int"
        },
        {
            "name": "string_arg1",
            "default": "DefaultStringValue",
            "description": "MyStringValue",
            "type": "str"
        },
        {
            "name": "lambda_arg1",
            "required": True,
            "description": "MyArgumentWithAction1",
            "action": lambda sa1: sa1 + ".txt"
        },
        {
            "name": "lambda_arg2",
            "required": False,
            "description": "MyArgumentWithAction2",
            "action": lambda sa1: sa1 + ".gz" if sa1 else None
        }
    ],
    run=album_run,
    install=album_install,
    pre_test=album_pre_test,
    test=album_test,
    dependencies={}
)

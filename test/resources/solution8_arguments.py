from album.runner.album_logging import get_active_logger
from album.runner.api import get_args
from album.runner.api import setup


def album_run():
    get_active_logger().info("solution8_arguments_run_start")

    args = get_args()

    ia1 = args.integer_arg1
    ia2 = args.integer_arg2
    sa1 = args.string_arg1

    la1 = args.lambda_arg1
    la2 = args.lambda_arg2

    get_active_logger().info("integer_arg1")
    get_active_logger().info(type(ia1))
    get_active_logger().info(ia1)

    get_active_logger().info("integer_arg2")
    get_active_logger().info(type(ia2))
    get_active_logger().info(ia2)

    get_active_logger().info("string_arg1")
    get_active_logger().info(type(sa1))
    get_active_logger().info(sa1)

    get_active_logger().info("lambda_arg1")
    get_active_logger().info(type(la1))
    get_active_logger().info(la1)

    get_active_logger().info("lambda_arg2")
    get_active_logger().info(type(la2))
    get_active_logger().info(la2)

    get_active_logger().info("solution8_arguments_run_end")


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
    album_api_version="0.3.1",
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

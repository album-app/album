from album.runner.album_logging import get_active_logger
from album.runner.api import get_args
from album.runner.api import setup


def album_run():
    get_active_logger().info("solution8_arguments_run_start")

    args = get_args()

    ia1 = args.integer_arg1
    ia2 = args.integer_arg2
    sa1 = args.string_arg1
    fa1 = args.file_arg1
    da1 = args.directory_arg1
    ba1 = args.boolean_arg1

    la1 = args.lambda_arg1
    la2 = args.lambda_arg2

    get_active_logger().info("integer_arg1: %s %s" % (type(ia1), ia1))

    get_active_logger().info("integer_arg2: %s %s" % (type(ia2), ia2))

    get_active_logger().info("string_arg1: %s %s" % (type(sa1), sa1))

    get_active_logger().info("file_arg1: %s %s" % (type(fa1), fa1))

    get_active_logger().info("directory_arg1: %s %s" % (type(da1), da1))

    get_active_logger().info("boolean_arg1: %s %s" % (type(ba1), ba1))

    get_active_logger().info("lambda_arg1: %s %s" % (type(la1), la1))

    get_active_logger().info("lambda_arg2: %s %s" % (type(la2), la2))

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
    album_api_version="0.4.0",
    args=[
        {
            "name": "integer_arg1",
            "default": 1,
            "description": "PositiveIntegerValue",
            "type": "integer"
        },
        {
            "name": "integer_arg2",
            "required": False,
            "default": -1000,
            "description": "NegativeIntegerValue",
            "type": "integer"
        },
        {
            "name": "string_arg1",
            "default": "DefaultStringValue",
            "description": "MyStringValue",
            "type": "string"
        },
        {
            "name": "file_arg1",
            "default": "DefaultFileValue.txt",
            "description": "MyFileValue",
            "type": "file"
        },
        {
            "name": "directory_arg1",
            "default": "DefaultDirectoryValue.txt",
            "description": "MyDirectoryValue",
            "type": "directory"
        },
        {
            "name": "boolean_arg1",
            "default": "DefaultBooleanValue.txt",
            "description": "MyBooleanValue",
            "type": "boolean"
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

from hips.core import get_active_hips, hips_debug
from hips.core.model.environment import run_in_environment, set_environment_name
from hips.core.model import logging

module_logger = logging.get_active_logger


def repl(args):
    """Function corresponding to the `repl` subcommand of `hips`."""
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)

    hips = get_active_hips()

    if hips_debug():
        module_logger().debug('hips loaded locally: ' + str(hips))

    # Get environment name
    environment_name = set_environment_name(hips)

    script = """from code import InteractiveConsole
"""

    script += hips_script

    # Create an interactive console with our globals and locals
    script += """
console = InteractiveConsole(locals={
    **globals(),
    **locals()
},
                             filename="<console>")
console.interact()
"""
    run_in_environment(environment_name, script)

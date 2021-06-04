from hips.core import get_active_hips
from hips_runner import logging
from hips_runner.logging import hips_debug

module_logger = logging.get_active_logger


def repl(args):
    """Function corresponding to the `repl` subcommand of `hips`."""
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)

    hips = get_active_hips()

    if hips_debug():
        module_logger().debug('hips loaded locally: %s...' % str(hips))

    # Get environment name
    environment_name = hips.environment_name

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
    hips.run_script(script)

from hips import get_active_hips, hips_debug
from utils.environment import run_in_environment, set_environment_name


def repl(args):
    """Function corresponding to the `repl` subcommand of `hips`."""
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)

    hips = get_active_hips()

    if hips_debug():
        print('hips loaded locally: ' + str(hips))

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

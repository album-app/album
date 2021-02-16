import os
import subprocess
import tempfile
import sys
from code import InteractiveConsole
from hips import Hips, get_active_hips, set_environment_name, hips_debug, run_in_environment


def repl(args):
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

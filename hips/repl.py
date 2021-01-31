import os
import subprocess
import tempfile
import sys
from code import InteractiveConsole
from hips import Hips, get_active_hips, get_environment_name, hips_debug


def repl(args):
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)

    # Create an interactive console with our globals and locals
    console = InteractiveConsole(locals={
        **globals(),
        **locals()
    },
                                 filename="<console>")
    console.interact()

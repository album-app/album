import logging
import os
import sys
import tempfile

import hips
from utils.environment import set_environment_path, set_environment_name, run_in_environment
from utils.hips_resolve import resolve_hips
from utils.hips_script import create_script

# ToDo: environment purge method
# ToDo: reusable versioned environments?
# ToDo: test for windows
# ToDo: subprocess logging (https://www.endpoint.com/blog/2015/01/28/getting-realtime-output-using-python)
# ToDo: solutions should not run in hips.yml for comp. reasons. Maybe check that?


module_logger = logging.getLogger('hips')


def run(args):
    """Function corresponding to the `run` subcommand of `hips`."""
    hips.load_and_push_hips(args.path)
    active_hips = hips.get_active_hips()
    if hasattr(active_hips, "parent"):
        __handle_hips_with_parent(active_hips)
    else:
        __handle_standalone_hips(active_hips)
    module_logger.info(f"Successfully ran {hips.get_active_hips()['name']}.")
    hips.pop_active_hips()


def __handle_standalone_hips(active_hips):
    set_environment_name(active_hips)
    set_environment_path(active_hips)
    script = create_script(active_hips, "\nhips.get_active_hips().run()\n", sys.argv)
    run_in_environment(active_hips["_environment_path"], script)


def __handle_hips_with_parent(active_hips):
    parent_hips = __load_and_push_parent(active_hips)
    set_environment_name(parent_hips)
    set_environment_path(parent_hips)
    script_parent = create_script(parent_hips,
                                  "\nhips.get_active_hips()['_app'] = hips.get_active_hips().run()\n",
                                  [parent_hips['_script']])
    script_main = create_script(active_hips,
                                "\nhips.get_active_hips()['_app'] = hips.get_parent_hips()['_app']" +
                                "\nhips.get_active_hips().run()\n",
                                sys.argv)
    script = __aggregate(script_parent, script_main)
    run_in_environment(parent_hips["_environment_path"], script)
    hips.pop_active_hips()


def __load_and_push_parent(active_hips):
    parent_script = resolve_hips(active_hips["parent"])
    hips.load_and_push_hips(parent_script)
    return hips.get_active_hips()


def __aggregate(*scripts):
    res = ""
    for script in scripts:
        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        fp.write(script)
        fp.flush()
        os.fsync(fp)
        script_name = fp.name
        res += f"\nexec(open('{script_name}').read())\n"
        fp.close()
    return res

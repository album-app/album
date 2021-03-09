import hips
from utils.environment import set_environment_path, set_environment_name, run_in_environment
from utils.hips_script import create_script

# ToDo: environment purge method
# ToDo: reusable versioned environments?
# ToDo: test for windows
# ToDo: subprocess logging (https://www.endpoint.com/blog/2015/01/28/getting-realtime-output-using-python)
# ToDo: solutions should not run in hips.yml for comp. reasons. Maybe check that?


def run(args):
    """Function corresponding to the `run` subcommand of `hips`."""

    hips.load_and_push_hips(args.path)

    active_hips = hips.get_active_hips()
    set_environment_name(active_hips)
    set_environment_path(active_hips)
    script = create_script(active_hips, "\nhips.get_active_hips().run()\n")
    run_in_environment(active_hips, script)

    hips.pop_active_hips()

import json
import subprocess
import sys
import urllib.request
import validators
from argparse import ArgumentError
from pathlib import Path

import git
from xdg import xdg_data_dirs, xdg_cache_home

from hips import get_active_hips, hips_debug, run_in_environment, get_environment_name


# ToDo: maybe find a nice way than extracting stuff from some console output?
#  The current solution might be highly risky...
def _get_environment_dict():
    """
    Returns the conda environments available for the conda installation
    """
    environment_dict = dict()

    # remove empty lines and preceded information
    def _split_and_clean(bytes_str):
        return None if bytes_str == b'' or bytes_str.startswith(
            b'#') else bytes_str.split(b' ')

    # list environments via conda info command - Note: conda.cli.python_api support missing
    output = subprocess.check_output(['conda', 'info', '--envs'])
    lines = output.split(b"\n")

    # extract name and path
    for line in lines:
        parsed_line = _split_and_clean(line)
        if parsed_line:
            # name is first split in line, path last
            environment_dict[parsed_line[0]] = parsed_line[-1]

    return environment_dict


# ToDo: get rid of all the encoding decoding stuff and format nicely
def get_environment_path(hips):
    """
    Returns the full environment path
    """
    environment_name = get_environment_name(hips)
    environment_dict = _get_environment_dict()
    if bytes(environment_name, 'utf-8') in environment_dict.keys():
        return _get_environment_dict()[bytes(environment_name,
                                             'utf-8')].decode("utf-8")

    raise RuntimeError('Could not find environment!')


def download_environment_yaml(hips):
    """
    Downloads a environment_file. URL is specified in hips['dependencies']['environment_file']
    """
    # ToDo: get_environment_name() currently can also read from a yaml file specified as `environment_path`.
    #  This is NOT the same as `environment_file`. Currently, to determine a environment_name from the yaml
    #  the file must already be downloaded. We can definitely change this.
    environment_name = get_environment_name(hips)
    environment_file = xdg_cache_home().joinpath(environment_name + '.yml')
    urllib.request.urlretrieve(hips['dependencies']['environment_file'],
                               environment_file)
    # ToDo: proper checking
    return environment_file


# ToDo: decide where to put create_environment method
def create_environment(hips):
    environment_name = get_environment_name(hips)

    if environment_exists(environment_name):  # updates environment
        pass
    elif 'environment_file' in hips['dependencies']:
        if validators.url(hips['dependencies']['environment_file']):
            file = download_environment_yaml(hips)
        else:  # ToDo: proper exception, proper checking
            file = hips['dependencies']['environment_file']
        subprocess_args = ['conda', 'env', 'create', '-f', file]
        subprocess.run(subprocess_args)

        # update environment to fit hips needs
        install_hips_in_environment(hips)
    else:
        subprocess_args = ['conda', 'env', 'create', '-f', 'hips_full.yml']
        subprocess.run(subprocess_args)

        # update environment to fit hips needs
        install_hips_in_environment(hips)

    return get_environment_path(hips)


# ToDo: use explicit versioning of hips
def install_hips_in_environment(hips):
    environment_path = get_environment_path(hips)
    subprocess_args = [
        'conda', 'run', '--no-capture-output', '--prefix', environment_path,
        'pip', 'install', 'git+https://gitlab.com/ida-mdc/hips.git'
    ]
    subprocess.run(subprocess_args)


# ToDo: decide where to put environment_exists method
# ToDo: get rid of all the encoding decoding stuff?
def environment_exists(environment_name):
    """
    Returns True when the given environment name exists for the conda installation else False
    """
    environment_dict = _get_environment_dict()
    return True if bytes(environment_name,
                         'utf-8') in environment_dict.keys() else False


# ToDo: proper logging system for hips?
def download_repository(hips):
    """
    Downloads the repository if needed, returns deployment_path on success
    """
    if 'download_repo' in hips['dependencies']:
        # ToDo: discuss: which of the dataDirs to take - since it is a git do we need this extra folder `hips['name'}`?...
        download_path = xdg_data_dirs()[0].joinpath(hips['name'])
        Path.mkdir(download_path, parents=True, exist_ok=True)

        # update existing repo or clone new repo
        if Path.exists(download_path.joinpath(".git")):
            repo = git.Repo(download_path)
            try:
                repo.remote().fetch()
            except AssertionError as err:
                print(err)
                pass
            git.refs.head.HEAD(repo, path='HEAD').reset(commit='HEAD',
                                                        index=True,
                                                        working_tree=False)
        else:
            repo = git.Repo.clone_from(hips['dependencies']['git_repo'],
                                       download_path)

        return repo.working_tree_dir
    return None


# ToDo: discuss: rather than having to initialize the repo every time to get the deployment path,
#  rather add attributes to the hips holding these information?
def get_deployment_path(hips):
    return git.Repo(xdg_data_dirs()[0].joinpath(hips['name'])).working_tree_dir


def run(args):
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)
    hips = get_active_hips()

    if hips_debug():
        print('hips loaded locally: ' + str(hips))

    # update or create environment
    create_environment(hips)

    # download git if needed ToDo: discuss - download here? or in run_in_environment? Download necessary at all?
    download_repository(hips)

    # Create script to run within target environment
    script = """import sys
import json
import argparse
from hips import get_active_hips
"""

    # This could have an issue with nested quotes
    script += "sys.argv = json.loads('%s')\n" % json.dumps(sys.argv)

    # Evaluate the path
    # If the path is a file
    script += hips_script

    # Add the init code
    script += """
hips.get_active_hips().init()
"""

    args = get_active_hips()['args']

    # special argument parsing cases
    if isinstance(args, str):
        # pass through to module
        if args == 'pass-through':
            pass
        # read arguments from file
        elif args == 'read-from-file':
            pass  # ToDo: discuss if we want this!
        else:
            raise ArgumentError('Argument keyword \'%s\' not supported!' %
                                args)
    else:
        # Add the argument handling
        script += """
parser = argparse.ArgumentParser(description='HIPS Run %s')
""" % hips['name']

        for arg in args:
            class_name = '%sAction' % arg['name'].capitalize()

            # Create an action
            script += """
class {class_name}(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super({class_name}, self).__init__(option_strings, dest, **kwargs)
        
    def __call__(self, parser, namespace, values, option_string=None):
        get_active_hips().get_arg(self.dest)['action'](values)
""".format(class_name=class_name)

            # Add an argument
            script += """
parser.add_argument('--{name}',
                    default='{default}',
                    help='{description}',
                    action={class_name})
""".format(name=arg['name'],
            default=arg['default'],
            description=arg['description'],
            class_name=class_name)

        script += """
parser.parse_args()
"""

    # Add the run code
    script += """
hips.get_active_hips().main()"""

    # ToDo: discuss: rather pass the name only and handle everything else in `run_in_environment` method???
    environment_path = get_environment_path(get_active_hips())

    run_in_environment(environment_path, script)

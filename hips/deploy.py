import yaml
from hips import Hips, get_active_hips


def hips_deploy_dict(hips):
    """Return a dictionary with the relevant deployment key/values for a given hips."""
    d = {}

    deploy_keys = [
        'name', 'description', 'timestamp', 'version', 'format_version', 'tested_hips_version',
        'min_hips_version', 'license', 'git_repo', 'authors', 'cite', 'tags', 'documentation',
        'covers', 'sample_inputs', 'sample_outputs', 'args', 'doi'
    ]

    for k in deploy_keys:
        d[k] = hips[k]

    return d


def deploy(args):
    """Function corresponding to the `deploy` subcommand of `hips`.

    Generates the yml for a hips.
    """
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)
    active_hips = get_active_hips()
    d = hips_deploy_dict(active_hips)

    yaml_str = yaml.dump(d, Dumper=yaml.Dumper)

    yaml_path = '_solutions/%s.md' % active_hips['name']

    print('writing to: %s' % yaml_path)

    with open(yaml_path, 'w') as f:
        f.write("---\n" + yaml_str + "\n---")

    # TODO fix these commands for proper paths in the catalog
    print("""
Run these commands:
git clone https://github.com/ida-mdc/hips-catalog.git
git branch %s
git checkout %s
git add %s
git add %s
git commit -m \"Adding updated %s\"""" %
          (active_hips['name'], active_hips['name'], args.path, yaml_path, active_hips['name']))




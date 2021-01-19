class Hips:
    """
    Encapsulates a HIPS
    """
    setup_keywords = ('name', 'version', 'description', 'url', 'license',
                      'min_hips_version', 'tested_hips_version', 'args',
                      'init', 'main', 'author', 'author_email', 'long_description',
                      'git_repo')

    def __init__(self, attrs=None):
        for attr in self.setup_keywords:
            if attr in attrs:
                setattr(self, attr, attrs[attr])

    def __str__(self):
        s = ''
        for attr in self.setup_keywords:
            if attr in dir(self):
                s += (attr + '\t' + str(getattr(self, attr))) + '\n'
        return s

global _active_hips

def setup(**attrs):
    """
    This configures a HIPS to for use by the main HIPS tool
    """
    global _active_hips
    _active_hips = Hips(attrs)

def get_active_hips():
    global _active_hips

    return _active_hips

def run(args):
    # Evaluate the path
    # If the path is a file
    exec(open(args.path).read())

    # If the path is a directory
    # If the path is a URL
    # If the path is the base of a git repo

    print('run: ' + str(_active_hips))
    _active_hips.init()
    # now parse the HIPS, then run
    _active_hips.main()

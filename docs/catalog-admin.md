catalog administration
================================

Catalogs hold the solutions to a specific problem.
Before solutions are usable from the catalog they need to be registered to it. That process is called `deployed`.

The album framework offers a suit of commands to handle the deployment requests to a catalog, provided the catalog is 
a git repository living in [gitlab](https://gitlab.com/).

You can use this suite to administrate your catalog.  It basically works as a git extension. A solution deployment ends
with a merge request on a new branch for your catalog. All is left to do is to review the request, provide a DOI for
the new solution and add it to the database index. 

In the section [manually administration](#manually-administration) everything is explained you need to know to
administrate your catalog. The section [automatic administration](#automatic-administration) shows you how to use
the command suite within a [gitlab-ci](https://docs.gitlab.com/ee/ci/) environment. 
 
## manually administration
As a catalog administrator you first clone your catalog repository to you local disk. You use git or the 
album-catalog-admin suite to setup your repository - whether to use ssh, which commit username and email you like, and so on.
You then checkout the new merge request of the new solution and review it. Eventually you decide it is worth living
in your catalog so you manually assign a DOI (e.g. by uploading the solution to zenodo), publish the deposit and change your
catalog index to include the new solution. 

To support you with this tim expensive procedure we developed the `album-catalog-admin` command suite providing the 
following commands:
 
* `configure-repo` - Configures the git configuration for the catalog repository. Sets an name and an email.
* `configure-ssh` - Configures the git push option for the catalog repository to use the ssh protocol instead of https. 
CAUTION: only works if the system git is configured for ssh usage! 
* `publish` - Publishes the corresponding zenodo deposit of a catalog repository deployment branch.
* `upload` - Uploads solution of a catalog repository deployment branch to zenodo.
* `update` - Updates the index of the catalog repository to include the solution of a catalog repository deployment branch.
* `push` - Pushes all changes to catalog repository deployment branch to the branch origin.


## automatic administration
Instead of manually execute all necessary/desired steps to include a new solution in your catalog you can configure 
your catalog gitlab-ci to automatically perform the catalog update cycle. 
When or if a certain command/step is executed depends of course on your gitlab-ci configuration and you are free to 
change the configuration to fit your needs. We here only show one possible configuration you are free to copy.


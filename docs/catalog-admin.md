catalog administration
================================

Catalogs hold the solutions to a specific problem.
Before solutions are usable from the catalog they need to be registered to it. That process is called `deployed`.

The album framework offers a suit of commands to handle the deployment requests to a catalog, provided the catalog is 
a git repository living in [gitlab](https://gitlab.com/).

You can use this suite to administrate your catalog.  It basically works as a git extension. When a solution gets 
deployed to a git based catalog, a merge request will be created to include the solution in your catalog. 
All that is left to do is to review the request, provide a DOI for
the new solution (if desired) and add it to the database index. 

The administrative tool `album-catalog-admin` helps you with all of that. Just type `album-catalog-admin -h` to receive 
help.

In the section [manually administration](#manually-administration) everything is explained you need to know to
administrate your catalog. The section [automatic administration](#automatic-administration) shows you how to use
the command suite within a [gitlab-ci](https://docs.gitlab.com/ee/ci/) environment. 
 
## manually administration
As a catalog administrator you first clone your catalog repository to you local disk. 
You usually use git to setup your repository - whether to use ssh or http, what username and email you commit with, and
maybe even more.
You then checkout the new merge request of the new solution and review it. Eventually you decide it is worth living
in your catalog so you manually assign a DOI (e.g. by uploading the solution to [zenodo](https://zenodo.org/), publish the deposit to 
receive a DOI) and change your catalog index to include the new solution. 

To support you with this tim expensive procedure we developed the `album-catalog-admin` command suite providing the 
following commands:
 
* `configure-repo` - Configures the git configuration for the catalog repository. Sets an name and an email.
* `configure-ssh` - Configures the git push option for the catalog repository to use the ssh protocol instead of https. 
CAUTION: only works if the system git is configured for ssh usage! 
* `publish` - Publishes the corresponding zenodo deposit of a catalog repository deployment branch.
* `upload` - Uploads solution of a catalog repository deployment branch to zenodo.
* `update` - Updates the index of the catalog repository to include the solution of a catalog repository deployment branch.
* `push` - Pushes all changes to catalog repository deployment branch to the branch origin.

### steps to add a solution to your git based catalog
The following steps need to be done to add a solution to your git based catalog:
- download your catalog from gitlab/github:
`album-catalog-admin configure-repo mycatalog /path/to/mycatalog https://gitlab.com/mycatalog --ci-user-name=catalog-admin --ci-user-email=catalog@adm.in --force-retrieve=True`
*Note that with `--force-retrieve=True` the folder `/path/to/mycatalog` will be deleted if it already exists.*

- configure ssh protocol to be used to commit changes:
`album-catalog-admin configure-ssh mycatalog /path/to/mycatalog https://gitlab.com/mycatalog`

- upload the solution behind a Merge Request to [zenodo](https://zenodo.org/) to receive a DOI:
`album-catalog-admin upload mycatalog /path/to/mycatalog https://gitlab.com/mycatalog --branch-name=my_new_solution_0.1.0`
*Note that zenodo differentiate between "upload" and "publish". So your upload is not yet published!*

- push the changes that are locally made to the merge request to the origin:
`album-catalog-admin push mycatalog /path/to/mycatalog https://gitlab.com/mycatalog --branch-name=my_new_solution_0.1.0`

- update the database of the catalog to now include the solution of the MR with the DOI from zenodo:
`album-catalog-admin update mycatalog /path/to/mycatalog https://gitlab.com/mycatalog --branch-name=my_new_solution_0.1.0`

- publish your zenodo repository to receive the DOI permanently:
`album-catalog-admin publish mycatalog /path/to/mycatalog https://gitlab.com/mycatalog --branch-name=my_new_solution_0.1.0`

- finally merge the Merge Request in your main catalog repository branch to make it available to everyone 
having your catalog configured in `album`:
`album-catalog-admin merge mycatalog /path/to/mycatalog https://gitlab.com/mycatalog --branch-name=my_new_solution_0.1.0`

This process can be quite demanding at some point. So there is a way to configure a Continuous Integration pipeline 
([gitlab-ci](https://docs.gitlab.com/ee/ci/)) for your git based catalog to automate the process.  

## automatic administration on gitlab
Instead of manually execute all necessary steps to include a new solution in your catalog (as shown above) you 
can configure your catalog gitlab-ci to automatically perform the steps. 
When or if a certain command/step is executed depends of course on your gitlab-ci configuration and you are free to 
change the configuration to fit your needs. We here only show one possible configuration you are free to copy.

To use a gitlab CI you configure the `.gitlab-ci.yml` file which is included in every gitlab repository.
 
In this file you define jobs hierarchically associated with stages. Each
job definition includes a part which can be executed under conditions which are also defined in the context of the job.
Execution of the executive part of a job happens on a so called [GitLab Runner](https://docs.gitlab.com/runner/). 
You can choose publicly available runners or set up your own runner, usable only from your project.
To use your own runners you have to configure these as docker-executors to work with the example blow.


When a job runs on such a gitlab-runner the runner additionally gets provided with (environment) 
[variables](https://docs.gitlab.com/ee/ci/variables/) describing the context of the job.

### Define variables for your CI

For the automatic administration of your catalog on gitlab the following variables need to be defined **additional** to the 
predefined variables gitlab provides:

Variable| Descrription
-------- | -------- 
SSH_PRIVATE_KEY_FILE    | The ssh key file to allow the CI to push to your repository.
ZENODO_ACCESS_TOKEN     | The zenodo access token linking to your zenodo user account.
ZENODO_BASE_URL         | The zenodo base URL to use. Either `https://sandbox.zenodo.org/` or `https://zenodo.org/`. The former can be used for testing scenarios.

*Note that you cannot use the same access token for both, sandbox and non-sandbox base url!*
 
To set these variables please follow the description form [here](https://docs.gitlab.com/ee/ci/variables/#add-a-cicd-variable-to-an-instance).
Please make sure that the ssh key provided for the ci also has **write permission** to the catalog repository!
Follow the instruction [here](https://docs.gitlab.com/ee/user/project/deploy_keys/).

### Define your .gitlab-ci.yml
Copy paste the part below in your `.gitlab-ci.yml` of your catalog git repository.

This `.gitlab-ci.yml` defines two jobs. The first one uploads the solution behind a deployment branch to zenodo thereby
preserving a DOI, the second one updates the database of your catalog and publishes the deposit to permanently
receive a DOI. 

The second job will not be executed automatically, but needs an manual approval of the catalog administrator. 
This is done deliberately to be able to reject deployment requests to your catalog.

The `.gitlab-ci.yml` will look like this:
```
#----------------------------
# stages
#----------------------------

stages:
  - upload_publish

#----------------------------
# templates
#----------------------------

# Linux base template
#
# Uses a docker image where conda is already installed.
# Creates a album environment.
#
.linux_base_template:
  image: continuumio/miniconda3:4.9.2
  before_script:
    # install or update openssh, git + tools
    - apt-get update -y && apt-get install -yqqf openssh-client git unzip sshpass rsync --fix-missing
    - 'which ssh-agent || ( apt-get update -y && apt-get install openssh-client git -y )'
    # check if ssh agent is running
    - eval $(ssh-agent -s)
    # install private deploy key from file
    - cat $SSH_PRIVATE_KEY_FILE | tr -d '\r' | ssh-add - > /dev/null

    # prepare .ssh folder
    - mkdir -p ~/.ssh
    - chmod 700 ~/.ssh

    # add gitlab.com to known hosts
    - ssh-keyscan gitlab.com >> ~/.ssh/known_hosts
    - chmod 644 ~/.ssh/known_hosts

    # setup conda & album
    - python -V  # Print out python version for debugging
    - pwd
    - which python
    - conda create -n album python pip
    - conda init bash
    - source ~/.bashrc
    - conda activate album
    - pip install album
  variables:
    PIP_CACHE_DIR: $CI_PROJECT_DIR/.cache/pip
    CONDA_ENV_NAME: album
    CONDA_PREFIX: /opt/conda
    PREFIX: $CONDA_PREFIX/envs/$CONDA_ENV_NAME
  cache:
    key: one-key-to-rule-them-all-linux
    paths:
      - ${CONDA_PREFIX}/pkgs/*.tar.bz2
      - ${CONDA_PREFIX}/pkgs/urls.txt

#----------------------------
# jobs
#----------------------------

upload:
  extends: .linux_base_template
  stage: upload_publish
  script:
    - album-catalog-admin configure-repo $CI_PROJECT_NAME /opt/catalog $CI_PROJECT_URL --ci-user-name=gitlab-ci --ci-user-email=gitlab-ci@catal.og --force-retrieve=True
    - album-catalog-admin configure-ssh $CI_PROJECT_NAME /opt/catalog  $CI_PROJECT_URL
    - album-catalog-admin upload $CI_PROJECT_NAME /opt/catalog $CI_PROJECT_URL --branch-name=$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME
    - album-catalog-admin push $CI_PROJECT_NAME /opt/catalog $CI_PROJECT_URL --branch-name=$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      changes:
        - "solutions/**/*"

publish:
  extends: .linux_base_template
  stage: upload_publish
  needs:
  - job: upload
  script:
    - album-catalog-admin configure-repo $CI_PROJECT_NAME /opt/catalog $CI_PROJECT_URL --ci-user-name=gitlab-ci --ci-user-email=gitlab-ci@catal.og --force-retrieve=True
    - album-catalog-admin configure-ssh $CI_PROJECT_NAME /opt/catalog  $CI_PROJECT_URL
    - album-catalog-admin update $CI_PROJECT_NAME /opt/catalog $CI_PROJECT_URL --branch-name=$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME
    - album-catalog-admin publish $CI_PROJECT_NAME /opt/catalog $CI_PROJECT_URL --branch-name=$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME
    - album-catalog-admin merge $CI_PROJECT_NAME /opt/catalog $CI_PROJECT_URL --branch-name=$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME --ci-user-name=gitlab-ci --ci-user-email=gitlab-ci@catal.og
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      changes:
        - "solutions/**/*"
      when: manual

```


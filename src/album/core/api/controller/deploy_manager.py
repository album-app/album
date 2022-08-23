from abc import ABCMeta, abstractmethod


class IDeployManager:
    """Class handling the deployment process.

    During deployment, a solution file will be requested to be added to a catalog. This catalog must be configured or
    specified in the solution file.
    When deploying to a remote catalog, deployment happens via a merge request to the git repository of the catalog.
    A deployment can also be requested to a catalog only existing locally.
    In this case, no merge request will be created!

    Notes:
        Git credentials required when deploying to a remote catalog!

    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def deploy(
        self,
        deploy_path: str,
        catalog_name: str,
        dry_run: bool,
        push_options=None,
        git_email: str = None,
        git_name: str = None,
        force_deploy: bool = False,
        changelog: str = "",
    ):
        """Function corresponding to the `deploy` subcommand of `album`.

        Generates the yml for a album and creates a merge request to the catalog only
        including the yaml and solution file.

        Args:
            force_deploy:
                Force overwrites a existing solution during deployment. Only for local catalogs.
            deploy_path:
                Path to a directory or a file.
                If directory: Must contain "solution.py" file.
            catalog_name:
                The catalog to deploy to. Either specify via argument in deploy-call, via url in solution or use
                default catalog.
            dry_run:
                When set, prepares deployment in local src of the catlog (creating zip, docker, yml),
                but not adding to the catalog src.
            push_options:
                Push options for the catalog repository.
            git_email:
                The git email to use. (Default: systems git configuration)
            git_name:
                The git user to use. (Default: systems git configuration)
            changelog:
                The change associated with this version of a solution compared to the last version.

        """
        raise NotImplementedError

    @abstractmethod
    def undeploy(
        self,
        solution_to_resolve: str,
        catalog_name: str,
        dry_run: bool,
        push_options=None,
        git_email: str = None,
        git_name: str = None,
    ):
        """Function corresponding to the `deploy` subcommand of `album`.

        Generates the yml for a album and creates a merge request to the catalog only
        including the yaml and solution file.

        Args:
            solution_to_resolve:
                Solution identifier which should be removed (group:name:version).
            catalog_name:
                The catalog to deploy to. Either specify via argument in deploy-call, via url in solution or use
                default catalog.
            dry_run:
                When set, prepares deployment in local src of the catlog (creating zip, docker, yml),
                but not adding to the catalog src.
            push_options:
                Push options for the catalog repository.
            git_email:
                The git email to use. (Default: systems git configuration)
            git_name:
                The git user to use. (Default: systems git configuration)

        """
        raise NotImplementedError

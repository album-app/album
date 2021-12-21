from album.ci.controller.release_manager import ReleaseManager


def configure_repo(release_manager: ReleaseManager, args):
    release_manager.configure_repo(args.ci_user_name, args.ci_user_email)


def configure_ssh(release_manager: ReleaseManager, args):
    release_manager.configure_ssh(args.ci_project_path)


def zenodo_publish(release_manager: ReleaseManager, args):
    release_manager.zenodo_publish(args.branch_name, args.zenodo_base_url, args.zenodo_access_token)


def zenodo_upload(release_manager: ReleaseManager, args):
    release_manager.zenodo_upload(args.branch_name, args.zenodo_base_url, args.zenodo_access_token)


def update_index(release_manager: ReleaseManager, args):
    release_manager.update_index(args.branch_name)


def push_changes(release_manager: ReleaseManager, args):
    release_manager.push_changes(
        args.branch_name, args.dry_run, args.push_option, args.ci_user_name, args.ci_user_email
    )


def merge(release_manager: ReleaseManager, args):
    release_manager.merge(args.branch_name, args.dry_run, args.push_option, args.ci_user_name, args.ci_user_email)

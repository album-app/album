from album.ci.controller.release_manager import ReleaseManager


def configure_repo(args):
    ReleaseManager(args.name, args.path, args.src).configure_repo(args.ci_user_name, args.ci_user_email)


def configure_ssh(args):
    ReleaseManager(args.name, args.path, args.src).configure_ssh(args.ci_project_path)


def zenodo_publish(args):
    ReleaseManager(args.name, args.path, args.src).zenodo_publish(
        args.branch_name, args.zenodo_base_url, args.zenodo_access_token
    )


def zenodo_upload(args):
    ReleaseManager(args.name, args.path, args.src).zenodo_upload(
        args.branch_name, args.zenodo_base_url, args.zenodo_access_token
    )


def update_index(args):
    ReleaseManager(args.name, args.path, args.src).update_index(args.branch_name)


def push_changes(args):
    ReleaseManager(args.name, args.path, args.src).push_changes(
        args.branch_name, args.dry_run, args.trigger_pipeline, args.ci_user_name, args.ci_user_email
    )

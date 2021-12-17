from album.ci.controller.release_manager import ReleaseManager
from album.core.api.album import IAlbum


def configure_repo(album_instance: IAlbum, args):
    ReleaseManager(album_instance, args.name, args.path, args.src, args.force_retrieve).configure_repo(
        args.ci_user_name, args.ci_user_email)


def configure_ssh(album_instance: IAlbum, args):
    ReleaseManager(album_instance, args.name, args.path, args.src, args.force_retrieve).configure_ssh(
        args.ci_project_path)


def zenodo_publish(album_instance: IAlbum, args):
    ReleaseManager(album_instance, args.name, args.path, args.src, args.force_retrieve).zenodo_publish(
        args.branch_name, args.zenodo_base_url, args.zenodo_access_token
    )


def zenodo_upload(album_instance: IAlbum, args):
    ReleaseManager(album_instance, args.name, args.path, args.src, args.force_retrieve).zenodo_upload(
        args.branch_name, args.zenodo_base_url, args.zenodo_access_token
    )


def update_index(album_instance: IAlbum, args):
    ReleaseManager(album_instance, args.name, args.path, args.src, args.force_retrieve).update_index(args.branch_name)


def push_changes(album_instance: IAlbum, args):
    ReleaseManager(album_instance, args.name, args.path, args.src, args.force_retrieve).push_changes(
        args.branch_name, args.dry_run, args.push_option, args.ci_user_name, args.ci_user_email
    )


def merge(album_instance: IAlbum, args):
    ReleaseManager(album_instance, args.name, args.path, args.src, args.force_retrieve).merge(
        args.branch_name, args.dry_run, args.push_option, args.ci_user_name, args.ci_user_email
    )

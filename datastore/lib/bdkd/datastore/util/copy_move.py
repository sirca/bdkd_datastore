"""
Utility library for copying and moving resources.
"""

import argparse
import bdkd.datastore
import bdkd.datastore.util.common as util_common


def _repository_resource_from_to_parser():
    """
    Parser for various options related to adding
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('from_repository', action=util_common.RepositoryAction,
            help='Name of the source repository')
    parser.add_argument('from_resource_name',
            help='Name of the source Resource (exists)')
    parser.add_argument('to_repository', nargs='?', default=None,
            action=util_common.OptionalRepositoryAction,
            help='Name of the destination repository (default source)')
    parser.add_argument('to_resource_name',
            help='Name of the destination Resource')
    return parser


def copy_parser():
    """
    Parser for the 'datastore-copy' utility
    """
    parser = argparse.ArgumentParser(prog='datastore-copy',
            description="Copy a resource",
            parents=[
                _repository_resource_from_to_parser(),
            ])
    return parser


def _copy_move(copy_move_args, do_move=False):
    to_repository = copy_move_args.to_repository
    if not to_repository:
        to_repository = copy_move_args.from_repository
    from_resource = copy_move_args.from_repository.get(
            copy_move_args.from_resource_name)
    if not from_resource:
        raise ValueError("From resource '{0}' does not exist!"
                .format(copy_move_args.from_resource_name))
    if do_move:
        to_repository.move(from_resource, copy_move_args.to_resource_name)
    else:
        to_repository.copy(from_resource, copy_move_args.to_resource_name)


def copy_util(argv=None):
    """
    Copy a Resource either within or between repositories.
    """
    _copy_move(copy_parser().parse_args(argv), do_move=False)


def move_parser():
    """
    Parser for the 'datastore-move' utility
    """
    parser = argparse.ArgumentParser(prog='datastore-move',
            description="Move a resource",
            parents=[
                _repository_resource_from_to_parser(),
            ])
    return parser


def move_util(argv=None):
    """
    Copy a Resource either within or between repositories.
    """
    _copy_move(move_parser().parse_args(argv), do_move=True)
